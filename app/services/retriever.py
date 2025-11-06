from typing import List, Tuple, Dict
import numpy as np
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os

load_dotenv()

class HybridRetriever:
    """Combine dense vector search with BM25 and optional cross-encoder reranking."""

    def __init__(self, qdrant_client: QdrantClient, collection_name: str, embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")):
        self.qdrant = qdrant_client
        self.collection_name = collection_name
        self.model = SentenceTransformer(embedding_model)
        self.bm25 = None
        self.doc_cache: Dict[str, str] = {}

    def build_bm25_index(self, documents: List[Dict]) -> None:
        """Build a BM25 index from the provided documents (list of Qdrant points)."""
        corpus = [doc["payload"]["text"] for doc in documents]
        self.bm25 = BM25Okapi([text.split() for text in corpus])
        for doc in documents:
            self.doc_cache[doc["id"]] = doc["payload"]["text"]

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

    def _reciprocal_rank_fusion(self, dense, sparse: List[Tuple[str, float]], k: int = 60) -> List[Tuple[str, float]]:
        scores: Dict[str, float] = {}
        for rank, result in enumerate(dense, 1):
            doc_id = result.id
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
        for rank, (doc_id, _) in enumerate(sparse, 1):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked

    def _cross_encode_rerank(self, query: str, candidates: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        texts = [self._get_document(doc_id) for doc_id, _ in candidates]
        pairs = [[query, text] for text in texts]
        scores = model.predict(pairs)
        final_scores = [(doc_id, 0.7 * ce_score + 0.3 * fusion_score)
                        for (doc_id, fusion_score), ce_score in zip(candidates, scores)]
        return sorted(final_scores, key=lambda x: x[1], reverse=True)

    def _get_document(self, doc_id: str) -> str:
        if doc_id in self.doc_cache:
            return self.doc_cache[doc_id]
        result = self.qdrant.retrieve(self.collection_name, [doc_id])
        return result[0].payload.get("text", "")

    def retrieve(self, query: str, top_k: int = 10, use_rerank: bool = False) -> List[Dict]:
        """Retrieve top documents for the query using hybrid search."""
        # Dense vector search
        query_vector = self._embed(query)
        dense_results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k * 2
        )
        # Sparse BM25 results
        sparse_results = self._bm25_search(query, top_k * 2)
        # Fuse
        fused = self._reciprocal_rank_fusion(dense_results, sparse_results, k=60)
        candidates = fused[:max(top_k * 2, 20)]
        if use_rerank and candidates:
            reranked = self._cross_encode_rerank(query, candidates)[:top_k]
        else:
            reranked = candidates[:top_k]
        docs: List[Dict] = []
        for doc_id, score in reranked:
            doc = self.qdrant.retrieve(self.collection_name, [doc_id])[0]
            docs.append({
                "id": doc_id,
                "text": doc.payload.get("text", ""),
                "score": score,
                "payload": doc.payload,
            })
        return docs