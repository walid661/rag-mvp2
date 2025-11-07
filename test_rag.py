#!/usr/bin/env python3
"""Test du système RAG sur VPS"""
import os
import sys
import re
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from qdrant_client import QdrantClient
from app.services.retriever import HybridRetriever
from app.services.generator import RAGGenerator
from app.services.monitor import RAGMonitor
from dotenv import load_dotenv

load_dotenv()

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "coach_mike")

print("Connexion a Qdrant...")
try:
    qdrant_client = QdrantClient(url=QDRANT_URL)
    collection_info = qdrant_client.get_collection(COLLECTION_NAME)
    print(f"Collection '{COLLECTION_NAME}' trouvee !")
    print(f"Points dans la collection : {collection_info.points_count}")
    print(f"Vecteurs indexes : {collection_info.indexed_vectors_count}")
except Exception as e:
    print(f"Erreur : {e}")
    sys.exit(1)

print("\nInitialisation du systeme RAG...")
retriever = HybridRetriever(qdrant_client=qdrant_client, collection_name=COLLECTION_NAME)
generator = RAGGenerator()
monitor = RAGMonitor()

# --- Chargement BM25 sans rebalayer Qdrant ---
print("Chargement de l'index BM25...")
loaded = retriever.load_bm25_state_if_any()
if not loaded:
    print("Index BM25 non trouve, construction depuis Qdrant...")
    try:
        all_docs = qdrant_client.scroll(collection_name=COLLECTION_NAME, limit=10000)[0]
        retriever.build_bm25_index(all_docs)
        print("Index BM25 construit !")
    except Exception as e:
        print(f"Erreur BM25 : {e}")
else:
    print("Index BM25 charge depuis le pickle (pas de scan Qdrant) !")

# --- Mini-heuristique de filtres depuis l'intention ---
def infer_filters_from_query(q: str) -> dict:
    """Infère des filtres basiques depuis la requête."""
    ql = q.lower()
    f = {}
    if re.search(r"\b(sans matériel|sans materiel|poids du corps|bodyweight)\b", ql):
        f.setdefault("equipment", "none")
    if re.search(r"\b(haltère|halteres?|dumbbell)\b", ql):
        f.setdefault("equipment", "dumbbell")
    return f

print("\n" + "="*70)
print("TEST 1 : Requete simple")
print("="*70)

query = "Je veux un programme pour renforcer le bas du corps sans materiel"
base_filters = {}
inferred = infer_filters_from_query(query)
for k, v in inferred.items():
    base_filters.setdefault(k, v)

t0 = time.time()
t_search0 = time.time()
retrieved = retriever.retrieve(query, top_k=10, filters=base_filters if base_filters else None)
t_search1 = time.time()
print(f"Documents trouves : {len(retrieved)}")

if retrieved:
    t_llm0 = time.time()
    result = generator.generate(query, retrieved)
    t_llm1 = time.time()
    t1 = time.time()
    
    search_ms = round((t_search1 - t_search0) * 1000, 2)
    llm_ms = round((t_llm1 - t_llm0) * 1000, 2)
    total_ms = round((t1 - t0) * 1000, 2)
    
    print(f"\nLatence totale : {total_ms} ms")
    print(f"  - search_ms: {search_ms} ms")
    print(f"  - llm_ms   : {llm_ms} ms")
    print(f"\nReponse :\n{result['answer']}")
    if result.get('sources'):
        print(f"\nSources ({len(result['sources'])}):")
        for source in result['sources']:
            score = source.get('score', 0.0)
            print(f"  - Document {source.get('index')}: {source.get('source')} (type: {source.get('type')}, score: {score:.4f})")
else:
    print("Aucun document trouve")

print("\n" + "="*70)
print("TEST 2 : Avec filtres")
print("="*70)

query2 = "exercices pour quadriceps avec halteres"
base_filters2 = {"type": "exercise"}
inferred2 = infer_filters_from_query(query2)
for k, v in inferred2.items():
    base_filters2.setdefault(k, v)

t0_2 = time.time()
t_search0_2 = time.time()
retrieved2 = retriever.retrieve(query2, top_k=10, filters=base_filters2)
t_search1_2 = time.time()
print(f"Documents trouves : {len(retrieved2)}")

if retrieved2:
    t_llm0_2 = time.time()
    result2 = generator.generate(query2, retrieved2)
    t_llm1_2 = time.time()
    t1_2 = time.time()
    
    search_ms_2 = round((t_search1_2 - t_search0_2) * 1000, 2)
    llm_ms_2 = round((t_llm1_2 - t_llm0_2) * 1000, 2)
    total_ms_2 = round((t1_2 - t0_2) * 1000, 2)
    
    print(f"\nLatence totale : {total_ms_2} ms")
    print(f"  - search_ms: {search_ms_2} ms")
    print(f"  - llm_ms   : {llm_ms_2} ms")
    print(f"\nReponse :\n{result2['answer']}")
    if result2.get('sources'):
        print(f"\nSources ({len(result2['sources'])}):")
        for source in result2['sources']:
            score = source.get('score', 0.0)
            print(f"  - Document {source.get('index')}: {source.get('source')} (type: {source.get('type')}, score: {score:.4f})")
else:
    print("Aucun document trouve")

print("\nTests termines !")



