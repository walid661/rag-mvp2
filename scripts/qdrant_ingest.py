import json
import os
import uuid
import glob
from typing import Iterable, List, Dict, Any
from dotenv import load_dotenv

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    OptimizersConfigDiff, ScalarQuantization, ScalarQuantizationConfig
)
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "coach_mike")
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
VECTOR_SIZE = 768 

# Define absolute or relative paths based on your workspace
# logic_jsonl_v2 contains the BRAIN (Rules, Mesos, Micros)
LOGIC_DIR = r"data/processed/raw_v2/logic_jsonl_v2"
# exercices_new_v2 contains the MUSCLE (3000+ JSON files)
EXERCISES_DIR = r"data/processed/raw_v2/exercices_new_v2"

def get_qdrant_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY", None)
    print(f"🔌 Connecting to Qdrant at {url}...")
    return QdrantClient(url=url, api_key=api_key)

def get_embedding_model() -> SentenceTransformer:
    print(f"🧠 Loading embedding model: {MODEL_NAME}...")
    return SentenceTransformer(MODEL_NAME)

def load_jsonl(path: str) -> Iterable[dict]:
    """Reads a single JSONL file."""
    print(f"   📄 Reading JSONL: {os.path.basename(path)}")
    if not os.path.exists(path):
        print(f"   ❌ File not found: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    pass

def load_json_directory(directory: str) -> Iterable[dict]:
    """Iterates over all .json files in a directory."""
    print(f"   📂 Scanning folder: {directory}")
    if not os.path.exists(directory):
        print(f"   ❌ Directory not found: {directory}")
        return []
    
    # Find all .json files
    json_files = glob.glob(os.path.join(directory, "*.json"))
    print(f"   found {len(json_files)} JSON files to ingest.")
    
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Sometimes the file contains a single dict, sometimes a list
                if isinstance(data, dict):
                    yield data
                elif isinstance(data, list):
                    for item in data:
                        yield item
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

def recreate_collection(client: QdrantClient):
    if client.collection_exists(COLLECTION_NAME):
        print(f"♻️  Deleting existing collection '{COLLECTION_NAME}'...")
        client.delete_collection(COLLECTION_NAME)
    
    print(f"🆕 Creating collection '{COLLECTION_NAME}'...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
        optimizers_config=OptimizersConfigDiff(indexing_threshold=1000),
        quantization_config=ScalarQuantization(
            scalar=ScalarQuantizationConfig(type="int8", quantile=0.99, always_ram=True)
        )
    )

def process_and_ingest(client: QdrantClient, model: SentenceTransformer):
    
    # 1. Define Logic Files to Ingest (The Brain)
    # We explicitly list the important ones or iterate the whole folder
    logic_files = [
        ("planner_schema.jsonl", "logic", "planner_rule"),
        ("macro_to_micro_rules.jsonl", "logic", "micro_rule"),
        ("muscle_balance_rules.jsonl", "logic", "balance_rule"),
        ("generation_spec.jsonl", "logic", "spec_rule"),
        ("objective_priority.jsonl", "logic", "priority_rule"),
        ("meso_catalog_v2.jsonl", "program", "meso_ref"),
        ("micro_catalog_v2.jsonl", "program", "micro_ref"),
        ("balanced_session_examples.jsonl", "example", "session_example")
    ]

    total_points = 0
    batch = []
    batch_size = 100

    # --- STEP A: INGEST LOGIC (JSONL) ---
    print("\n--- PHASE 1: INGESTING LOGIC ---")
    for filename, domain, doc_type in logic_files:
        path = os.path.join(LOGIC_DIR, filename)
        for record in load_jsonl(path):
            
            # Construct Text for Vector
            # Prioritize specific fields, fallback to generic 'text'
            parts = [
                record.get("rule_text", ""),
                record.get("nom", ""),
                record.get("objectif", ""),
                record.get("intention", ""),
                record.get("text", "")
            ]
            text_vector = " ".join([str(p) for p in parts if p]).strip()
            
            if not text_vector: continue

            # Prepare Point
            vector = model.encode(text_vector).tolist()
            payload = record.copy()
            payload["text"] = text_vector
            payload["domain"] = domain
            payload["type"] = doc_type
            
            # ID Generation
            rec_id = record.get("id") or record.get("meso_id") or record.get("micro_id")
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(rec_id) if rec_id else text_vector))

            batch.append(PointStruct(id=point_id, vector=vector, payload=payload))

            if len(batch) >= batch_size:
                client.upsert(collection_name=COLLECTION_NAME, points=batch)
                total_points += len(batch)
                batch = []
    
    # Flush remaining logic
    if batch:
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        total_points += len(batch)
        batch = []

    # --- STEP B: INGEST EXERCISES (FOLDER OF JSONs) ---
    print("\n--- PHASE 2: INGESTING EXERCISES ---")
    for record in load_json_directory(EXERCISES_DIR):
        
        # Construct Text for Vector (Rich context for exercises)
        parts = [
            record.get("exercise", ""),
            record.get("target_muscle_group", ""),
            record.get("movement_pattern", ""),
            record.get("primary_equipment", ""),
            record.get("text", "")
        ]
        text_vector = " ".join([str(p) for p in parts if p]).strip()

        if not text_vector: continue

        vector = model.encode(text_vector).tolist()
        payload = record.copy()
        payload["text"] = text_vector
        payload["domain"] = "exercise"
        payload["type"] = "exercise_ref"
        
        # Use Exercise Name as stable ID source
        ex_name = record.get("exercise", "unknown")
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, ex_name))

        batch.append(PointStruct(id=point_id, vector=vector, payload=payload))

        if len(batch) >= batch_size:
            client.upsert(collection_name=COLLECTION_NAME, points=batch)
            total_points += len(batch)
            print(f"   -> Processed {total_points} total items...", end="\r")
            batch = []

    # Flush remaining exercises
    if batch:
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        total_points += len(batch)

    print(f"\n\n🎉 INGESTION COMPLETE! Total documents in '{COLLECTION_NAME}': {total_points}")
    print("You can now use the Planner Agent.")

if __name__ == "__main__":
    client = get_qdrant_client()
    model = get_embedding_model()
    recreate_collection(client)
    process_and_ingest(client, model)