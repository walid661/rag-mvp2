#!/usr/bin/env python3
"""Script de diagnostic pour vérifier les données dans Qdrant"""
import os
import sys
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "coach_mike")

print(f"Connexion à Qdrant: {QDRANT_URL}")
client = QdrantClient(url=QDRANT_URL)

# Vérifier si la collection existe
if not client.collection_exists(COLLECTION_NAME):
    print(f"❌ La collection '{COLLECTION_NAME}' n'existe pas !")
    sys.exit(1)

collection_info = client.get_collection(COLLECTION_NAME)
print(f"\n✅ Collection '{COLLECTION_NAME}' trouvée")
print(f"   Points totaux: {collection_info.points_count}")
print(f"   Vecteurs indexés: {collection_info.indexed_vectors_count}")

if collection_info.points_count == 0:
    print("\n⚠️  La collection est vide ! Il faut ingérer les données.")
    print("   Exécutez: python -m app.services.ingest_logic_jsonl")
    sys.exit(1)

# Récupérer quelques exemples de documents
print("\n📊 Analyse des documents...")
results, _ = client.scroll(
    collection_name=COLLECTION_NAME,
    limit=10,
    with_payload=True,
    with_vectors=False
)

print(f"\n📝 Exemples de documents (premiers {len(results)}):")
for i, point in enumerate(results[:5], 1):
    payload = point.payload
    print(f"\n   Document {i}:")
    print(f"      ID: {point.id}")
    print(f"      Domain: {payload.get('domain', 'N/A')}")
    print(f"      Type: {payload.get('type', 'N/A')}")
    print(f"      Niveau: {payload.get('niveau', 'N/A')}")
    print(f"      Groupe: {payload.get('groupe', 'N/A')}")
    print(f"      Objectif: {payload.get('objectif', 'N/A')}")
    print(f"      Source: {payload.get('source', 'N/A')}")
    text_preview = payload.get('text', '')[:100] if payload.get('text') else 'N/A'
    print(f"      Text: {text_preview}...")

# Compter par domain et type
print("\n📈 Statistiques par domain et type:")
all_results, _ = client.scroll(
    collection_name=COLLECTION_NAME,
    limit=10000,
    with_payload=True,
    with_vectors=False
)

domain_counts = {}
type_counts = {}
niveau_counts = {}
groupe_counts = {}

for point in all_results:
    payload = point.payload
    domain = payload.get('domain', 'unknown')
    typ = payload.get('type', 'unknown')
    niveau = payload.get('niveau', 'unknown')
    groupe = payload.get('groupe', 'unknown')
    
    domain_counts[domain] = domain_counts.get(domain, 0) + 1
    type_counts[typ] = type_counts.get(typ, 0) + 1
    niveau_counts[niveau] = niveau_counts.get(niveau, 0) + 1
    groupe_counts[groupe] = groupe_counts.get(groupe, 0) + 1

print("\n   Par domain:")
for domain, count in sorted(domain_counts.items()):
    print(f"      {domain}: {count}")

print("\n   Par type:")
for typ, count in sorted(type_counts.items()):
    print(f"      {typ}: {count}")

print("\n   Par niveau:")
for niveau, count in sorted(niveau_counts.items()):
    print(f"      {niveau}: {count}")

print("\n   Par groupe:")
for groupe, count in sorted(groupe_counts.items()):
    print(f"      {groupe}: {count}")

# Tester les filtres utilisés
print("\n🔍 Test des filtres utilisés:")
test_filters = {
    'domain': 'program',
    'type': 'meso_ref',
    'niveau': 'Débutant',
    'groupe': 'Reconditionnement général',
    'objectif': 'mobilité active guidée'
}

print(f"   Filtres: {test_filters}")

# Construire le filtre Qdrant
from qdrant_client.models import Filter, FieldCondition, MatchValue

conditions = []
for key, value in test_filters.items():
    if value:
        conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

if conditions:
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    qdrant_filter = Filter(must=conditions)
    
    # Test de recherche avec filtres
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2"))
    query_vector = model.encode("programme mobilité débutant").tolist()
    
    search_results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        query_filter=qdrant_filter,
        limit=5
    )
    
    print(f"   Résultats avec filtres: {len(search_results)}")
    if search_results:
        print("   ✅ Des documents correspondent aux filtres")
        for i, result in enumerate(search_results[:3], 1):
            print(f"      {i}. Score: {result.score:.4f}, ID: {result.id}")
            print(f"         Domain: {result.payload.get('domain')}, Type: {result.payload.get('type')}")
    else:
        print("   ❌ Aucun document ne correspond aux filtres")
        print("\n   💡 Suggestions:")
        print("      - Vérifiez que les données ont été ingérées avec les bons domain/type")
        print("      - Vérifiez que les valeurs de niveau/groupe/objectif correspondent exactement")
        print("      - Essayez de rechercher sans filtres pour voir si des documents existent")

print("\n✅ Diagnostic terminé")

