#!/usr/bin/env python3
"""Test du système RAG sur VPS"""
import os
import sys
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

print("Construction de l'index BM25...")
try:
    all_docs = qdrant_client.scroll(collection_name=COLLECTION_NAME, limit=10000)[0]
    retriever.build_bm25_index(all_docs)
    print("Index BM25 construit !")
except Exception as e:
    print(f"Erreur BM25 : {e}")

print("\n" + "="*70)
print("TEST 1 : Requete simple")
print("="*70)

query = "Je veux un programme pour renforcer le bas du corps sans materiel"
monitor.start_timer()

retrieved = retriever.retrieve(query, top_k=10)
print(f"Documents trouves : {len(retrieved)}")

if retrieved:
    result = generator.generate(query, retrieved)
    latency = monitor.measure_latency()
    
    print(f"\nLatence : {latency:.2f} ms")
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
filters = {"type": "exercise"}

retrieved2 = retriever.retrieve(query2, top_k=10, filters=filters)
print(f"Documents trouves : {len(retrieved2)}")

if retrieved2:
    result2 = generator.generate(query2, retrieved2)
    print(f"\nReponse :\n{result2['answer']}")
    if result2.get('sources'):
        print(f"\nSources ({len(result2['sources'])}):")
        for source in result2['sources']:
            score = source.get('score', 0.0)
            print(f"  - Document {source.get('index')}: {source.get('source')} (type: {source.get('type')}, score: {score:.4f})")
else:
    print("Aucun document trouve")

print("\nTests termines !")

