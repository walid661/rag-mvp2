from typing import List, Dict
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    OptimizersConfigDiff, HnswConfigDiff,
    ScalarQuantization, ScalarQuantizationConfig
)
from dotenv import load_dotenv
import os

load_dotenv()

class DocumentIndexer:
    """Create a Qdrant collection and index documents with embeddings."""

    def __init__(self, qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6335"), collection_name: str = os.getenv("QDRANT_COLLECTION", "coach_mike")):
        self.client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name

    def create_collection(self, vector_size: int = 768) -> None:
        """Recreate the collection with given vector size and cosine distance."""
        # Supprimer la collection existante si elle existe
        if self.client.collection_exists(self.collection_name):
            print(f"Suppression de la collection existante '{self.collection_name}'...")
            self.client.delete_collection(self.collection_name)
        
        print(f"Creation de la collection '{self.collection_name}'...")
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
                on_disk=True
            ),
            optimizers_config=OptimizersConfigDiff(
                indexing_threshold=int(os.getenv("INDEXING_THRESHOLD", "1000"))
            ),
            quantization_config=ScalarQuantization(
                scalar=ScalarQuantizationConfig(
                    type="int8",
                    quantile=0.99,
                    always_ram=True
                )
            )
        )

        # Réduire le full_scan_threshold et éventuellement limiter les threads d'indexation
        self.client.update_collection(
            collection_name=self.collection_name,
            hnsw_config=HnswConfigDiff(
                full_scan_threshold=int(os.getenv("FULL_SCAN_THRESHOLD", "500")),
                max_indexing_threads=int(os.getenv("MAX_INDEXING_THREADS", "0"))
            )
        )
        print(f"Collection '{self.collection_name}' creee avec succes !")

    def index_documents(self, documents: List[Dict], batch_size: int = 100) -> None:
        """Insert documents into the collection in batches."""
        points: List[PointStruct] = []
        for doc in documents:
            pid = uuid.uuid4().hex
            
            # Normalisation du payload avant upsert
            # doc["metadata"] peut contenir les métadonnées directement
            # ou doc peut avoir des champs au niveau racine
            meta = doc.get("metadata") or doc.get("meta") or {}
            record = doc  # Le document entier sert de record
            
            payload = {
                # Texte principal (clé canonique attendue côté retrieval/BM25)
                "text": (
                    record.get("text")
                    or meta.get("text")
                    or record.get("content")
                    or doc.get("text")
                ),
                
                # Provenance du document (chemin fichier, URL, titre…)
                "source": (
                    record.get("source")
                    or meta.get("source")
                    or doc.get("source")
                ),
                
                # Page, si applicable (PDF)
                "page": (
                    record.get("page")
                    or meta.get("page")
                    or doc.get("page")
                ),
                
                # Typologie fonctionnelle (exercise, micro, meso, taxonomy…)
                "type": (
                    record.get("type")
                    or meta.get("type")
                    or record.get("domain")
                    or meta.get("domain")
                    or doc.get("type")
                    or doc.get("domain")
                    or "exercise"
                ),
                
                # Horodatage utile pour l'audit/tri
                "timestamp": (
                    record.get("updated_at")
                    or record.get("created_at")
                    or meta.get("updated_at")
                    or meta.get("created_at")
                    or meta.get("timestamp")
                    or doc.get("updated_at")
                    or doc.get("created_at")
                ),
                
                # Fusion intégrale des métadonnées existantes
                **meta,
            }
            
            # Optionnel : préserver des identifiants s'ils existent déjà
            if record.get("doc_id") or doc.get("doc_id"):
                payload["doc_id"] = record.get("doc_id") or doc.get("doc_id")
            if record.get("chunk_id") or doc.get("chunk_id"):
                payload["chunk_id"] = record.get("chunk_id") or doc.get("chunk_id")
            
            # Préserver l'embedding si présent dans metadata (ne pas l'ajouter au payload)
            # Le vector est passé séparément
            
            point = PointStruct(
                id=pid,
                vector=doc["embedding"],
                payload=payload
            )
            points.append(point)
            if len(points) >= batch_size:
                self.client.upsert(collection_name=self.collection_name, points=points)
                points = []
        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)