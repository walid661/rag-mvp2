import json
from pathlib import Path
from typing import Iterable
import uuid
from urllib.parse import urlparse

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    OptimizersConfigDiff, HnswConfigDiff,
    ScalarQuantization, ScalarQuantizationConfig
)

from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os

load_dotenv()

# Collection and model configuration
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "coach_mike")
VECTOR_SIZE = 768  # default embedding size for all-mpnet-base-v2
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")

def load_jsonl(path: str) -> Iterable[dict]:
    """Yield JSON objects from a JSONL file."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

def get_embedding_model(model_name: str = MODEL_NAME) -> SentenceTransformer:
    return SentenceTransformer(model_name)

def upsert_batch(client: QdrantClient, collection: str, points: list):
    if points:
        client.upsert(collection_name=collection, points=points)

def main(
    host: str = None,
    port: int = None,
    exercises_path: str = "data/processed/exercises.jsonl",
    micro_path: str = "data/processed/microcycles.jsonl",
    meso_path: str = "data/processed/mesocycles.jsonl",
    batch_size: int = 100,
):
    # Parse QDRANT_URL if provided, otherwise use host/port defaults
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6335")
    if host is None or port is None:
        parsed = urlparse(qdrant_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6335
    
    client = QdrantClient(host=host, port=port)

    # Create or recreate collection
    if client.collection_exists(COLLECTION_NAME):
        print(f"Suppression de la collection existante '{COLLECTION_NAME}'...")
        client.delete_collection(COLLECTION_NAME)
    
    print(f"Creation de la collection '{COLLECTION_NAME}'...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
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
    client.update_collection(
        collection_name=COLLECTION_NAME,
        hnsw_config=HnswConfigDiff(
            full_scan_threshold=int(os.getenv("FULL_SCAN_THRESHOLD", "500")),
            max_indexing_threads=int(os.getenv("MAX_INDEXING_THREADS", "0"))
        )
    )
    print(f"Collection '{COLLECTION_NAME}' creee avec succes !")

    # Load embedding model
    model = get_embedding_model()

    def prepare_points(path: str, domain: str):
        for record in load_jsonl(path):
            emb = model.encode(record["text"]).tolist()
            pid = uuid.uuid4().hex
            
            # Normalisation du payload avant upsert
            meta = record.get("meta") or record.get("metadata") or {}
            
            payload = {
                # Texte principal (clé canonique attendue côté retrieval/BM25)
                "text": (
                    record.get("text")
                    or meta.get("text")
                    or record.get("content")
                ),
                
                # Provenance du document (chemin fichier, URL, titre…)
                "source": (
                    record.get("source")
                    or meta.get("source")
                    or "json"
                ),
                
                # Page, si applicable (PDF)
                "page": (
                    record.get("page")
                    or meta.get("page")
                ),
                
                # Typologie fonctionnelle (exercise, micro, meso, taxonomy…)
                "type": (
                    record.get("type")
                    or meta.get("type")
                    or record.get("domain")
                    or domain
                    or "exercise"
                ),
                
                # Horodatage utile pour l'audit/tri
                "timestamp": (
                    record.get("updated_at")
                    or record.get("created_at")
                    or meta.get("updated_at")
                    or meta.get("created_at")
                    or meta.get("timestamp")
                ),
                
                # Fusion intégrale des métadonnées existantes
                **meta,
            }
            
            # Optionnel : préserver des identifiants s'ils existent déjà dans le record
            if record.get("doc_id"):
                payload["doc_id"] = record["doc_id"]
            if record.get("chunk_id"):
                payload["chunk_id"] = record["chunk_id"]
            
            # Ajouter domain si pas déjà présent
            if "domain" not in payload:
                payload["domain"] = domain
            
            yield PointStruct(
                id=pid,
                vector=emb,
                payload=payload
            )

    # Ingest all domains
    for path, domain in [
        (exercises_path, "exercise"),
        (micro_path, "micro"),
        (meso_path, "meso")
    ]:
        batch = []
        for point in prepare_points(path, domain):
            batch.append(point)
            if len(batch) >= batch_size:
                upsert_batch(client, COLLECTION_NAME, batch)
                batch = []
        if batch:
            upsert_batch(client, COLLECTION_NAME, batch)

if __name__ == "__main__":
    main()