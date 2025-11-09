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

# Optionnel : import du router et de l'ingestion
try:
    from app.services.rag_router import build_filters
    ROUTER_AVAILABLE = True
except ImportError:
    ROUTER_AVAILABLE = False
    print("[test] rag_router non disponible, filtres manuels uniquement")

try:
    from app.services.ingest_logic_jsonl import ingest_logic_and_program_jsonl
    INGEST_AVAILABLE = True
except ImportError:
    INGEST_AVAILABLE = False

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

# --- Optionnel : ingestion si demandée ---
if "--ingest" in sys.argv:
    if INGEST_AVAILABLE:
        print("\n" + "="*70)
        print("INGESTION DES JSONL")
        print("="*70)
        ingest_logic_and_program_jsonl()
        print("\nReconstruction de l'index BM25 après ingestion...")
        try:
            all_docs = qdrant_client.scroll(collection_name=COLLECTION_NAME, limit=10000)[0]
            retriever.build_bm25_index(all_docs)
            print("Index BM25 reconstruit !\n")
        except Exception as e:
            print(f"Erreur lors de la reconstruction BM25 : {e}\n")
    else:
        print("[test] Module d'ingestion non disponible\n")

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
    if k == "equipment":
        continue  # on n'injecte pas 'equipment' pour éviter 0 résultat
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
    if k == "equipment":
        continue  # on n'injecte pas 'equipment' pour éviter 0 résultat
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

# Tests avec router (si disponible)
if ROUTER_AVAILABLE:
    print("\n" + "="*70)
    print("TEST 3 : Méso pour perte de poids débutant (avec router)")
    print("="*70)
    
    profile = {"niveau_sportif": "débutant", "objectif_principal": "perte de poids"}
    filters = build_filters("select_meso", profile=profile)
    query3 = "programme pour débutant"
    
    print(f"Filtres appliqués: {filters}")
    t0_3 = time.time()
    retrieved3 = retriever.retrieve(query3, top_k=5, filters=filters)
    t1_3 = time.time()
    
    print(f"Documents trouvés avec filtres {filters}: {len(retrieved3)}")
    if retrieved3:
        for i, doc in enumerate(retrieved3[:3], 1):
            payload = doc.get("payload", {})
            print(f"  {i}. {payload.get('type')} - {payload.get('meso_id', 'N/A')} - {payload.get('nom', 'N/A')[:50]}")
            print(f"     Domain: {payload.get('domain')}, Niveau: {payload.get('niveau')}, Objectif: {payload.get('objectif')}")
    else:
        print("Aucun document trouvé")
    
    print("\n" + "="*70)
    print("TEST 4 : Règles mc3 (avec router)")
    print("="*70)
    
    filters4 = build_filters("micro_generation_rules", extra={"role_micro": "mc3", "rule_type": "progression_rule"})
    query4 = "règles de progression pour micro-cycle mc3"
    
    print(f"Filtres appliqués: {filters4}")
    t0_4 = time.time()
    retrieved4 = retriever.retrieve(query4, top_k=5, filters=filters4)
    t1_4 = time.time()
    
    print(f"Documents trouvés avec filtres {filters4}: {len(retrieved4)}")
    if retrieved4:
        for i, doc in enumerate(retrieved4[:3], 1):
            payload = doc.get("payload", {})
            print(f"  {i}. {payload.get('type')} - {payload.get('id', 'N/A')}")
            print(f"     Domain: {payload.get('domain')}, Role: {payload.get('role_micro')}")
            rule_text = payload.get('rule_text', '')[:80]
            print(f"     Texte: {rule_text}...")
    else:
        print("Aucun document trouvé")
    
    print("\n" + "="*70)
    print("TEST 5 : Schéma séance (5 blocs)")
    print("="*70)
    
    filters5 = build_filters("session_schema")
    query5 = "structure d'une séance"
    
    print(f"Filtres appliqués: {filters5}")
    t0_5 = time.time()
    retrieved5 = retriever.retrieve(query5, top_k=3, filters=filters5)
    t1_5 = time.time()
    
    print(f"Documents trouvés avec filtres {filters5}: {len(retrieved5)}")
    if retrieved5:
        for i, doc in enumerate(retrieved5[:2], 1):
            payload = doc.get("payload", {})
            print(f"  {i}. {payload.get('type')} - {payload.get('id', 'N/A')}")
            print(f"     Domain: {payload.get('domain')}")
            if "blocks" in payload:
                print(f"     Blocs: {payload['blocks']}")
            rule_text = payload.get('rule_text', '')[:100]
            print(f"     Texte: {rule_text}...")
    else:
        print("Aucun document trouvé")

print("\nTests termines !")



