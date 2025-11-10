#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic des points non indexés dans Qdrant.
"""

import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "coach_mike")

def diagnose_unindexed_points():
    """Diagnostique les points non indexés."""
    print(f"Connexion à Qdrant: {QDRANT_URL}")
    client = QdrantClient(url=QDRANT_URL)
    
    if not client.collection_exists(COLLECTION_NAME):
        print(f"❌ Collection '{COLLECTION_NAME}' non trouvée")
        return
    
    collection_info = client.get_collection(COLLECTION_NAME)
    print(f"\n✅ Collection '{COLLECTION_NAME}'")
    print(f"   Points totaux: {collection_info.points_count}")
    print(f"   Vecteurs indexés: {collection_info.indexed_vectors_count}")
    print(f"   Points non indexés: {collection_info.points_count - collection_info.indexed_vectors_count}")
    
    # Récupérer tous les points
    print(f"\n📊 Analyse des points...")
    all_points = []
    next_page = None
    
    while True:
        points, next_page = client.scroll(
            collection_name=COLLECTION_NAME,
            with_payload=True,
            with_vectors=True,  # IMPORTANT : récupérer les vecteurs
            limit=1000,
            offset=next_page
        )
        if not points:
            break
        all_points.extend(points)
        if next_page is None:
            break
    
    print(f"   Total points récupérés: {len(all_points)}")
    
    # Analyser les points sans vecteurs
    points_without_vectors = []
    points_with_empty_vectors = []
    points_with_vectors = []
    
    for point in all_points:
        if point.vector is None:
            points_without_vectors.append(point)
        elif isinstance(point.vector, dict):
            # Vecteur nommé (peu probable ici)
            if not point.vector:
                points_with_empty_vectors.append(point)
            else:
                points_with_vectors.append(point)
        elif isinstance(point.vector, list):
            if len(point.vector) == 0:
                points_with_empty_vectors.append(point)
            else:
                points_with_vectors.append(point)
        else:
            points_with_vectors.append(point)
    
    print(f"\n📋 ANALYSE DES VECTEURS")
    print("="*80)
    print(f"Points avec vecteurs: {len(points_with_vectors)}")
    print(f"Points sans vecteurs (None): {len(points_without_vectors)}")
    print(f"Points avec vecteurs vides: {len(points_with_empty_vectors)}")
    
    if points_without_vectors:
        print(f"\n🔍 EXEMPLES DE POINTS SANS VECTEURS (10 premiers)")
        print("="*80)
        for i, point in enumerate(points_without_vectors[:10], 1):
            print(f"\n  {i}. ID: {point.id}")
            print(f"     Domain: {point.payload.get('domain', 'N/A')}")
            print(f"     Type: {point.payload.get('type', 'N/A')}")
            print(f"     Source: {point.payload.get('source', 'N/A')}")
            text = point.payload.get('text', 'N/A')
            if text and text != 'N/A':
                text_preview = text[:100] + "..." if len(text) > 100 else text
                print(f"     Text: {text_preview}")
            else:
                print(f"     Text: {text}")
    
    if points_with_empty_vectors:
        print(f"\n🔍 EXEMPLES DE POINTS AVEC VECTEURS VIDES (10 premiers)")
        print("="*80)
        for i, point in enumerate(points_with_empty_vectors[:10], 1):
            print(f"\n  {i}. ID: {point.id}")
            print(f"     Domain: {point.payload.get('domain', 'N/A')}")
            print(f"     Type: {point.payload.get('type', 'N/A')}")
            print(f"     Source: {point.payload.get('source', 'N/A')}")
            text = point.payload.get('text', 'N/A')
            if text and text != 'N/A':
                text_preview = text[:100] + "..." if len(text) > 100 else text
                print(f"     Text: {text_preview}")
            else:
                print(f"     Text: {text}")
    
    # Analyser par domain/type
    print(f"\n📊 RÉPARTITION PAR DOMAIN/TYPE")
    print("="*80)
    domain_type_stats = {}
    for point in all_points:
        domain = point.payload.get('domain', 'unknown')
        typ = point.payload.get('type', 'unknown')
        key = f"{domain}/{typ}"
        if key not in domain_type_stats:
            domain_type_stats[key] = {"total": 0, "with_vector": 0, "without_vector": 0}
        domain_type_stats[key]["total"] += 1
        if point.vector is not None and (not isinstance(point.vector, list) or len(point.vector) > 0):
            domain_type_stats[key]["with_vector"] += 1
        else:
            domain_type_stats[key]["without_vector"] += 1
    
    for key, stats in sorted(domain_type_stats.items()):
        print(f"\n  {key}:")
        print(f"    Total: {stats['total']}")
        print(f"    Avec vecteur: {stats['with_vector']}")
        print(f"    Sans vecteur: {stats['without_vector']}")
    
    # Vérifier les points avec texte vide
    print(f"\n📋 POINTS AVEC TEXTE VIDE")
    print("="*80)
    points_with_empty_text = [p for p in all_points if not p.payload.get('text') or p.payload.get('text', '').strip() == '']
    print(f"Points avec texte vide: {len(points_with_empty_text)}")
    
    if points_with_empty_text:
        print(f"\n🔍 EXEMPLES DE POINTS AVEC TEXTE VIDE (10 premiers)")
        print("="*80)
        for i, point in enumerate(points_with_empty_text[:10], 1):
            print(f"\n  {i}. ID: {point.id}")
            print(f"     Domain: {point.payload.get('domain', 'N/A')}")
            print(f"     Type: {point.payload.get('type', 'N/A')}")
            print(f"     Source: {point.payload.get('source', 'N/A')}")
            print(f"     Has vector: {point.vector is not None}")
    
    # Recommandations
    print(f"\n💡 RECOMMANDATIONS")
    print("="*80)
    if points_without_vectors or points_with_empty_vectors:
        print("❌ Des points n'ont pas de vecteurs. Il faut :")
        print("   1. Vérifier que l'ingestion génère bien les embeddings")
        print("   2. Ré-ingérer les points sans vecteurs")
        print("   3. Vérifier que le champ 'text' n'est pas vide")
    elif len(points_with_vectors) < collection_info.points_count:
        print("⚠️  Certains points ont des vecteurs mais ne sont pas indexés.")
        print("   Cela peut être normal si l'indexation est en cours.")
        print("   Essayez de forcer l'indexation avec :")
        print("   client.update_collection(collection_name=COLLECTION_NAME, optimizer_config=...)")
    else:
        print("✅ Tous les points ont des vecteurs.")
        print("   Si l'indexation ne progresse pas, vérifiez les logs Qdrant.")
    
    print("\n✅ Diagnostic terminé")

if __name__ == "__main__":
    diagnose_unindexed_points()

