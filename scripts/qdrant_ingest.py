import json
from pathlib import Path
from typing import Iterable
import uuid
from urllib.parse import urlparse

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

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
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    if host is None or port is None:
        parsed = urlparse(qdrant_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6333
    
    client = QdrantClient(host=host, port=port)

    # Create or recreate collection
    try:
        client.get_collection(COLLECTION_NAME)
    except Exception:
        client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )

    # Load embedding model
    model = get_embedding_model()

    def prepare_points(path: str, domain: str):
        for record in load_jsonl(path):
            emb = model.encode(record["text"]).tolist()
            pid = uuid.uuid4().hex
            payload = {**record["meta"], "domain": domain}
            payload["text"] = record["text"]  # store raw text for BM25
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