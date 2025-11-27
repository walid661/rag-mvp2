import json
import os
import uuid
from typing import Iterable
from urllib.parse import urlparse
from dotenv import load_dotenv

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    OptimizersConfigDiff, ScalarQuantization, ScalarQuantizationConfig
)
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

# Configuration
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "coach_mike")
# Force local model for SentenceTransformer to avoid OpenAI model names from env
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
VECTOR_SIZE = 768 

# Paths to the new V2 Data
BASE_DATA_DIR = r"data/processed/raw_v2/logic_jsonl_v2"
MESO_PATH = os.path.join(BASE_DATA_DIR, "meso_catalog_v2.jsonl")
MICRO_PATH = os.path.join(BASE_DATA_DIR, "micro_catalog_v2.jsonl")

def get_qdrant_client() -> QdrantClient:
    """Initialize Qdrant Client from Env Vars."""
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY", None)
    
    print(f"🔌 Connecting to Qdrant at {url}...")
    return QdrantClient(url=url, api_key=api_key)

def get_embedding_model() -> SentenceTransformer:
    """Load the embedding model."""
    print(f"🧠 Loading embedding model: {MODEL_NAME}...")
    return SentenceTransformer(MODEL_NAME)

def load_jsonl(path: str) -> Iterable[dict]:
    """Yield JSON objects from a JSONL file safely."""
    print(f"📂 Reading file: {path}")
    if not os.path.exists(path):
        print(f"❌ ERROR: File not found at {path}")
        return []
        
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    print(f"⚠️ Skipping invalid JSON line in {path}")

def recreate_collection(client: QdrantClient):
    """Delete and recreate the collection to ensure a clean V2 schema."""
    if client.collection_exists(COLLECTION_NAME):
        print(f"♻️  Deleting existing collection '{COLLECTION_NAME}'...")
        client.delete_collection(COLLECTION_NAME)
    
    print(f"🆕 Creating collection '{COLLECTION_NAME}' with size {VECTOR_SIZE}...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE,
            on_disk=True
        ),
        # Optimize for speed
        optimizers_config=OptimizersConfigDiff(indexing_threshold=1000),
        quantization_config=ScalarQuantization(
            scalar=ScalarQuantizationConfig(
                type="int8",
                quantile=0.99,
                always_ram=True
            )
        )
    )
    print("✅ Collection created successfully.")

def process_and_ingest(client: QdrantClient, model: SentenceTransformer):
    """Read V2 files, vectorize text, and upload structured payloads."""
    
    # Define the files to ingest and their domain tags
    files_map = [
        (MESO_PATH, "program", "meso_ref"),
        (MICRO_PATH, "program", "micro_ref")
    ]
    
    batch = []
    batch_size = 100
    total_points = 0

    for file_path, domain, doc_type in files_map:
        for record in load_jsonl(file_path):
            
            # 1. Construct the Text for Embedding (The "Vibe")
            # Combine relevant text fields to ensure semantic search works
            parts = [
                record.get("nom", ""),
                record.get("objectif", ""),
                record.get("intention", ""),
                record.get("text", "")
            ]
            text_for_vector = " ".join([p for p in parts if p])
            
            if not text_for_vector.strip():
                continue

            # 2. Create Vector
            vector = model.encode(text_for_vector).tolist()
            
            # 3. Prepare Payload (The Logic)
            # Store the ENTIRE record so 'constraints' and 'structured' are available
            payload = record.copy()
            payload["text"] = text_for_vector # Ensure text is searchable
            payload["domain"] = domain
            payload["type"] = doc_type
            
            # 4. Generate Deterministic ID
            # Uses the ID from the file (e.g., "mcA01") to create a UUID
            record_id = record.get("id") or record.get("meso_id") or record.get("micro_id")
            if record_id:
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(record_id)))
            else:
                point_id = uuid.uuid4().hex

            # 5. Add to Batch
            batch.append(PointStruct(id=point_id, vector=vector, payload=payload))

            if len(batch) >= batch_size:
                client.upsert(collection_name=COLLECTION_NAME, points=batch)
                total_points += len(batch)
                print(f"   -> Upserted {len(batch)} points from {os.path.basename(file_path)}")
                batch = []

    # Final flush
    if batch:
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        total_points += len(batch)
        print(f"   -> Upserted final {len(batch)} points.")

    print(f"\n🎉 Ingestion Complete! Total documents in '{COLLECTION_NAME}': {total_points}")

def test_query(client: QdrantClient, model: SentenceTransformer):
    """Perform a quick sanity check query."""
    print("\n🔎 Running Sanity Check Query: 'Perte de poids'...")
    vector = model.encode("Je veux perdre du poids et sécher").tolist()
    
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=vector,
        limit=1
    )
    
    if results:
        hit = results[0]
        print(f"✅ Top Hit: {hit.payload.get('nom')} (Score: {hit.score:.3f})")
        print(f"   Logic Data Present: {'constraints' in hit.payload or 'structured' in hit.payload}")
    else:
        print("⚠️ No results found. Ingestion might have failed.")

if __name__ == "__main__":
    print("🚀 Starting V2 Ingestion Pipeline...")
    client = get_qdrant_client()
    model = get_embedding_model()
    
    recreate_collection(client)
    process_and_ingest(client, model)
    test_query(client, model)