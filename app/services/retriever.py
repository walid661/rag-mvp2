from typing import List, Tuple, Dict, Optional
import numpy as np
import os
import pickle
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue, SearchParams
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
from dotenv import load_dotenv

load_dotenv()

RRF_K = int(os.getenv("RRF_K", "60"))
ENABLE_RERANK = os.getenv("ENABLE_RERANK", "false").lower() == "true"
RERANK_MODEL = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
BM25_STATE_PATH = "data/processed/bm25.pkl"

class HybridRetriever:
    """Combine dense vector search with BM25 and optional cross-encoder reranking."""

    def __init__(self, qdrant_client: QdrantClient, collection_name: str, embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")):
        self.qdrant = qdrant_client
        self.collection_name = collection_name
        self.model = SentenceTransformer(embedding_model)
        self.bm25 = None
        self.doc_cache: Dict[str, str] = {}        # id -> text
        self.payload_cache: Dict[str, Dict] = {}   # id -> payload minimal (filtres)
        self._reranker = None

    def _get_reranker(self):
        """Lazy load reranker if enabled."""
        if ENABLE_RERANK and self._reranker is None:
            self._reranker = CrossEncoder(RERANK_MODEL)
        return self._reranker

    def load_bm25_state_if_any(self) -> bool:
        """
        Charge BM25/doc_cache/payload_cache depuis le pickle s'il existe.
        Retourne True si chargé, False sinon.
        """
        try:
            if os.path.exists(BM25_STATE_PATH):
                with open(BM25_STATE_PATH, "rb") as f:
                    state = pickle.load(f)
                self.doc_cache = state.get("doc_cache", {})
                self.payload_cache = state.get("payload_cache", {})
                self.bm25 = state.get("bm25")
                return True
        except Exception:
            # En cas de corruption, on laissera le caller reconstruire.
            pass
        return False

    def _load_or_build_bm25(self, docs_as_tokens: List[List[str]]):
        """Load BM25 from pickle if exists, otherwise build and save."""
        Path(BM25_STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
        if os.path.exists(BM25_STATE_PATH):
            with open(BM25_STATE_PATH, "rb") as f:
                state = pickle.load(f)
                self.doc_cache = state.get("doc_cache", {})
                self.payload_cache = state.get("payload_cache", {})
                self.bm25 = state.get("bm25")
                return
        # Build and persist
        self.bm25 = BM25Okapi(docs_as_tokens)
        with open(BM25_STATE_PATH, "wb") as f:
            pickle.dump({"doc_cache": self.doc_cache, "payload_cache": self.payload_cache, "bm25": self.bm25}, f)

    def build_bm25_index(self, documents: List[Dict]) -> None:
        """Build a BM25 index from the provided documents (list of Qdrant points)."""
        corpus = []
        for doc in documents:
            # Handle both dict and Record objects
            if hasattr(doc, 'payload'):
                # Record object
                text = doc.payload.get("text", "")
                doc_id = doc.id
                payload = dict(doc.payload or {})
            else:
                # Dict object
                text = doc.get("payload", {}).get("text", "")
                doc_id = doc.get("id")
                payload = dict((doc.get("payload") or {}))
            
            if text:
                corpus.append(text)
                self.doc_cache[doc_id] = text
                # Conserver un sous-ensemble de clés utiles au filtrage
                if payload:
                    self.payload_cache[doc_id] = {
                        k: payload.get(k) for k in ("type", "equipment", "domain", "source", "page")
                        if k in payload
                    }
        
        docs_as_tokens = [text.split() for text in corpus]
        self._load_or_build_bm25(docs_as_tokens)

    def _embed(self, query: str) -> List[float]:
        return self.model.encode(query).tolist()

    def _bm25_search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(query.split())
        ranked_indices = np.argsort(scores)[::-1][:top_k]
        doc_ids = list(self.doc_cache.keys())
        results = []
        for idx in ranked_indices:
            doc_id = doc_ids[idx]
            results.append((doc_id, scores[idx]))
        return results

    def _build_filter(self, filters: Optional[Dict]) -> Optional[Filter]:
        """Build Qdrant filter from dict."""
        if not filters:
            return None
        must = []
        for key, val in filters.items():
            if isinstance(val, list):
                must.append(FieldCondition(key=key, match=MatchAny(any=val)))
            else:
                must.append(FieldCondition(key=key, match=MatchValue(value=val)))
        return Filter(must=must) if must else None

    def _reciprocal_rank_fusion(self, dense, sparse: List[Tuple[str, float]], k: int = RRF_K) -> List[Tuple[str, float]]:
        scores: Dict[str, float] = {}
        for rank, result in enumerate(dense, 1):
            doc_id = result.id
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
        for rank, (doc_id, _) in enumerate(sparse, 1):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked

    def _cross_encode_rerank(self, query: str, candidates: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        reranker = self._get_reranker()
        if not reranker:
            return candidates
        # Prefetch en batch pour éviter N requêtes
        ids = [doc_id for doc_id, _ in candidates]
        recs = self.qdrant.retrieve(self.collection_name, ids)
        payload_by_id = {r.id: r for r in recs}
        texts = []
        for doc_id in ids:
            r = payload_by_id.get(doc_id)
            txt = r.payload.get("text", "") if r else ""
            texts.append(txt)
        pairs = [[query, t] for t in texts]
        scores = reranker.predict(pairs)
        final_scores = [(doc_id, 0.7 * ce_score + 0.3 * fusion_score)
                        for (doc_id, fusion_score), ce_score in zip(candidates, scores)]
        return sorted(final_scores, key=lambda x: x[1], reverse=True)

    def _get_document(self, doc_id: str) -> str:
        if doc_id in self.doc_cache:
            return self.doc_cache[doc_id]
        result = self.qdrant.retrieve(self.collection_name, [doc_id])
        return result[0].payload.get("text", "")

    def retrieve(self, query: str, top_k: int = 10, filters: Optional[Dict] = None, use_rerank: bool = None) -> List[Dict]:
        """Retrieve top documents for the query using hybrid search."""
        if use_rerank is None:
            use_rerank = ENABLE_RERANK
        
        qdrant_filter = self._build_filter(filters)
        
        # Dense vector search
        query_vector = self._embed(query)
        dense_results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=top_k * 2,
            search_params=SearchParams(hnsw_ef=int(os.getenv("HNSW_EF", "128")))
        )
        
        # Sparse BM25 results (post-filter if needed)
        sparse_results = self._bm25_search(query, top_k * 2)
        if filters:
            # Filter BM25 results via payload_cache (0 requête Qdrant)
            filtered_sparse = []
            for doc_id, score in sparse_results:
                p = self.payload_cache.get(doc_id, {})
                ok = True
                for key, val in filters.items():
                    if isinstance(val, list):
                        if p.get(key) not in val:
                            ok = False
                            break
                    else:
                        if p.get(key) != val:
                            ok = False
                            break
                if ok:
                    filtered_sparse.append((doc_id, score))
            sparse_results = filtered_sparse[:top_k * 2]
        
        # Fuse
        fused = self._reciprocal_rank_fusion(dense_results, sparse_results, k=RRF_K)
        candidates = fused[:max(top_k * 2, 20)]
        
        if use_rerank and candidates:
            reranked = self._cross_encode_rerank(query, candidates)[:top_k]
        else:
            reranked = candidates[:top_k]
        
        # Batch retrieve pour limiter à 1 appel réseau
        ids = [doc_id for doc_id, _ in reranked]
        recs = self.qdrant.retrieve(self.collection_name, ids)
        payload_by_id = {r.id: r for r in recs}
        docs: List[Dict] = []
        for doc_id, score in reranked:
            r = payload_by_id.get(doc_id)
            if not r:
                continue
            docs.append({
                "id": doc_id,
                "text": r.payload.get("text", ""),
                "score": score,
                "payload": r.payload,
            })
        return docs