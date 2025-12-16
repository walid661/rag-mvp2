from typing import List, Tuple, Dict, Optional
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue, SearchParams
from sentence_transformers import SentenceTransformer, CrossEncoder
from dotenv import load_dotenv

load_dotenv()

# --- TASK 2: SUPPRESSION BM25 LOCAL ---
# Suppression des imports pickle, rank_bm25 et constantes associées
ENABLE_RERANK = os.getenv("ENABLE_RERANK", "false").lower() == "true"
RERANK_MODEL = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

class HybridRetriever:
    """
    Retrieves documents using Qdrant Hybrid Search (Dense + Sparse capability).
    Fully Stateless.
    """

    def __init__(self, qdrant_client: QdrantClient, collection_name: str, embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")):
        self.qdrant = qdrant_client
        self.collection_name = collection_name
        self.model = SentenceTransformer(embedding_model)
        self._reranker = None

    def _get_reranker(self):
        if ENABLE_RERANK and self._reranker is None:
            self._reranker = CrossEncoder(RERANK_MODEL)
        return self._reranker

    def _embed(self, query: str) -> List[float]:
        return self.model.encode(query).tolist()

    # --- TASK 4: PRE-FILTERING ---
    def _build_filter(self, filters: Optional[Dict]) -> Optional[Filter]:
        """Build Qdrant native Filter object from simplified dictionary."""
        if not filters:
            return None
        
        q_must = []
        q_should = []
        q_must_not = []

        # Helper pour traiter une condition
        def process_conditions(cond_list, target_list):
            for cond in cond_list:
                key = cond.get("key")
                match = cond.get("match", {})
                if "value" in match:
                    target_list.append(FieldCondition(key=key, match=MatchValue(value=match["value"])))
                elif "any" in match:
                    target_list.append(FieldCondition(key=key, match=MatchAny(any=match["any"])))

        if "must" in filters: process_conditions(filters["must"], q_must)
        if "should" in filters: process_conditions(filters["should"], q_should)
        if "must_not" in filters: process_conditions(filters["must_not"], q_must_not)

        if not q_must and not q_should and not q_must_not:
            return None

        return Filter(must=q_must if q_must else None, 
                      should=q_should if q_should else None, 
                      must_not=q_must_not if q_must_not else None)

    def retrieve(self, query: str, top_k: int = 10, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Retrieve documents using Qdrant Search with Pre-Filtering.
        """
        query_vector = self._embed(query)
        qdrant_filter = self._build_filter(filters)

        # --- TASK 2 & 4: HYBRID SEARCH NATIVE & PRE-FILTERING ---
        # Note: Pour l'instant, nous utilisons la recherche Dense pure avec filtre.
        # Si des vecteurs sparse sont ajoutés plus tard, on passera à search_batch ou hybrid.
        # Ici on simplifie pour le MVP2 robuste : Dense + Filter natif (très rapide).
        
        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=qdrant_filter, # PRE-FILTERING: Filtrage côté DB
            limit=top_k,
            with_payload=True,
            search_params=SearchParams(hnsw_ef=128)
        )

        # Reranking optionnel (reste en Python mais sur moins de docs grâce au pre-filtering)
        if ENABLE_RERANK and results:
            # Conversion format simple pour reranker
            candidates = [(r.id, r.score, r.payload.get("text", "")) for r in results]
            reranked = self._cross_encode_rerank(query, candidates)
            
            # Reconstruit la liste finale
            final_docs = []
            for doc_id, score, text in reranked:
                # Retrouver le payload original (optimisation possible: map)
                original = next((r for r in results if r.id == doc_id), None)
                if original:
                    final_docs.append({
                        "id": doc_id,
                        "text": text,
                        "score": score,
                        "payload": original.payload
                    })
            return final_docs
        
        # Format de sortie standard sans rerank
        return [{
            "id": r.id,
            "text": r.payload.get("text", ""),
            "score": r.score,
            "payload": r.payload
        } for r in results]

    def _cross_encode_rerank(self, query: str, candidates: List[Tuple]) -> List[Tuple]:
        reranker = self._get_reranker()
        if not reranker:
            return [(c[0], c[1], c[2]) for c in candidates]
        
        pairs = [[query, c[2]] for c in candidates]
        scores = reranker.predict(pairs)
        
        # Combine scores (0.7 rerank + 0.3 original dense)
        final_results = []
        for i, (doc_id, dense_score, text) in enumerate(candidates):
            final_score = 0.7 * scores[i] + 0.3 * dense_score
            final_results.append((doc_id, final_score, text))
            
        return sorted(final_results, key=lambda x: x[1], reverse=True)