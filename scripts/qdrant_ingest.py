import json
import os
import uuid
import glob
import argparse  # <--- TASK 5
from typing import Iterable, Dict, Any
from dotenv import load_dotenv

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    OptimizersConfigDiff, ScalarQuantization, ScalarQuantizationConfig,
    SparseVectorParams  # <--- TASK 2
)
from sentence_transformers import SentenceTransformer

# --- CONFIGURATION ---
load_dotenv()

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "coach_mike")

# MULTILINGUAL UPGRADE: Using a model that understands French queries better
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
VECTOR_SIZE = 384  # CRITICAL: This model outputs 384 dim vectors

# --- PATHS (Based on your file structure) ---
# Logic: Single JSONL files
LOGIC_DIR = os.path.join("data", "processed", "raw_v2", "logic_jsonl_v2")
# Exercises: Folder containing individual JSON files
EXERCISES_DIR = os.path.join("data", "processed", "raw_v2", "exercices_new_v2")

def get_qdrant_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY", None)
    print(f"🔌 Connecting to Qdrant at {url}...")
    return QdrantClient(url=url, api_key=api_key)

def get_embedding_model() -> SentenceTransformer:
    print(f"🧠 Loading Multilingual model: {MODEL_NAME}...")
    return SentenceTransformer(MODEL_NAME)

def load_jsonl(path: str) -> Iterable[dict]:
    """Reads a single JSONL file."""
    if not os.path.exists(path):
        print(f"   ⚠️ Logic file not found: {path}")
        return []
    print(f"   📖 Reading Logic: {os.path.basename(path)}")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    pass

def load_json_directory(directory: str) -> Iterable[dict]:
    """Iterates over all .json files in the exercise directory."""
    print(f"   📂 Scanning Exercise Folder: {directory}")
    if not os.path.exists(directory):
        print(f"   ❌ Directory not found: {directory}")
        return []
    
    # Use glob to find all .json files
    json_pattern = os.path.join(directory, "*.json")
    files = glob.glob(json_pattern)
    print(f"   🏋️ Found {len(files)} exercise files.")
    
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data: yield item
                elif isinstance(data, dict):
                    yield data
        except Exception as e:
            print(f"   ⚠️ Error reading {os.path.basename(file_path)}")

def recreate_collection(client: QdrantClient):
    """Resets the collection to fit the new Vector Size (384) AND Sparse config."""
    if client.collection_exists(COLLECTION_NAME):
        print(f"♻️  Deleting old collection '{COLLECTION_NAME}'...")
        client.delete_collection(COLLECTION_NAME)
    
    print(f"🆕 Creating collection '{COLLECTION_NAME}' (Size: {VECTOR_SIZE})...")
    
    # --- TASK 2: CONFIGURATION SPARSE ---
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE, on_disk=True),
        sparse_vectors_config={
            "sparse": SparseVectorParams()
        },
        optimizers_config=OptimizersConfigDiff(indexing_threshold=1000),
        quantization_config=ScalarQuantization(
            scalar=ScalarQuantizationConfig(type="int8", quantile=0.99, always_ram=True)
        )
    )

def construct_vector_text(record: Dict[str, Any], domain: str) -> str:
    """Builds the string to be embedded based on domain context."""
    parts = []
    if domain == "exercise":
        parts = [
            record.get("exercise", ""),
            record.get("target_muscle_group", ""),
            record.get("movement_pattern", ""),
            record.get("primary_equipment", ""),
            record.get("text", "")
        ]
    else:
        # Logic / Program domain
        parts = [
            record.get("rule_text", ""),
            record.get("nom", ""),
            record.get("objectif", ""),
            record.get("intention", ""),
            record.get("text", "")
        ]
    return " ".join([str(p) for p in parts if p]).strip()

def process_and_ingest(client: QdrantClient, model: SentenceTransformer):
    
    # 1. Define Logic Files to Ingest (The Brain)
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
            
            text_vector = construct_vector_text(record, domain)
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
    
    if batch:
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        total_points += len(batch)
        batch = []

    # --- STEP B: INGEST EXERCISES (FOLDER OF JSONs) ---
    print("\n--- PHASE 2: INGESTING EXERCISES ---")
    for record in load_json_directory(EXERCISES_DIR):
        
        text_vector = construct_vector_text(record, "exercise")
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

    if batch:
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        total_points += len(batch)

    print(f"\n\n🎉 INGESTION COMPLETE! Total documents in '{COLLECTION_NAME}': {total_points}")
    print("You can now use the Planner Agent.")

if __name__ == "__main__":
    # --- TASK 5: LOGIQUE NON-DESTRUCTIVE ---
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Recreate collection (WARNING: deletes all)")
    args = parser.parse_args()

    client = get_qdrant_client()
    model = get_embedding_model()
    
    if args.force:
        print("⚠️  FORCE MODE: Recreating collection...")
        recreate_collection(client)
    else:
        if not client.collection_exists(COLLECTION_NAME):
            print(f"Collection '{COLLECTION_NAME}' not found, creating...")
            recreate_collection(client)
        else:
            print(f"✅ Collection '{COLLECTION_NAME}' exists. Switching to UPSERT mode (Non-destructive).")

    process_and_ingest(client, model)