#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyse exhaustive de la base Qdrant pour comprendre la structure exacte des données.
Extrait tous les champs, leurs valeurs uniques, et leur distribution.
"""

import os
import json
from collections import defaultdict, Counter
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "coach_mike")

def analyze_qdrant_schema():
    """Analyse exhaustive de la collection Qdrant."""
    print(f"Connexion à Qdrant: {QDRANT_URL}")
    client = QdrantClient(url=QDRANT_URL)
    
    if not client.collection_exists(COLLECTION_NAME):
        print(f"❌ Collection '{COLLECTION_NAME}' non trouvée")
        return
    
    print(f"✅ Collection '{COLLECTION_NAME}' trouvée")
    
    # Récupérer tous les documents
    print("\n📊 Récupération de tous les documents...")
    all_points = []
    next_page = None
    batch = 1000
    
    while True:
        points, next_page = client.scroll(
            collection_name=COLLECTION_NAME,
            with_payload=True,
            with_vectors=False,
            limit=batch,
            offset=next_page
        )
        if not points:
            break
        all_points.extend(points)
        print(f"  Récupéré {len(all_points)} documents...")
        if next_page is None:
            break
    
    print(f"\n✅ Total: {len(all_points)} documents")
    
    # Analyser les champs et leurs valeurs
    print("\n📋 Analyse des champs et valeurs...")
    
    # Par domain/type
    by_domain_type = defaultdict(int)
    by_domain = defaultdict(int)
    by_type = defaultdict(int)
    
    # Champs spécifiques
    objectif_values = Counter()
    groupe_values = Counter()
    niveau_values = Counter()
    methode_values = Counter()
    materiel_values = Counter()
    equipment_values = Counter()
    zones_values = Counter()
    
    # Structure complète des payloads
    all_fields = set()
    field_value_examples = defaultdict(set)  # Exemples de valeurs pour chaque champ
    
    # Documents par type
    meso_ref_docs = []
    micro_ref_docs = []
    exercise_docs = []
    logic_docs = []
    
    for point in all_points:
        payload = point.payload or {}
        all_fields.update(payload.keys())
        
        # Domain/Type
        domain = payload.get("domain", "unknown")
        doc_type = payload.get("type", "unknown")
        by_domain[domain] += 1
        by_type[doc_type] += 1
        by_domain_type[f"{domain}/{doc_type}"] += 1
        
        # Collecter des exemples de valeurs pour chaque champ
        for key, value in payload.items():
            if value is not None and value != "":
                if isinstance(value, (str, int, float, bool)):
                    field_value_examples[key].add(str(value))
                elif isinstance(value, list):
                    for v in value:
                        if v:
                            field_value_examples[key].add(str(v))
        
        # Champs spécifiques
        if payload.get("objectif"):
            obj = payload["objectif"]
            objectif_values[obj] += 1
        
        if payload.get("groupe"):
            grp = payload["groupe"]
            groupe_values[grp] += 1
        
        if payload.get("niveau"):
            niv = payload["niveau"]
            niveau_values[niv] += 1
        
        if payload.get("methode"):
            meth = payload["methode"]
            methode_values[meth] += 1
        
        if payload.get("materiel"):
            mat = payload["materiel"]
            if isinstance(mat, list):
                for m in mat:
                    materiel_values[m] += 1
            else:
                materiel_values[mat] += 1
        
        if payload.get("equipment"):
            eq = payload["equipment"]
            if isinstance(eq, list):
                for e in eq:
                    equipment_values[e] += 1
            else:
                equipment_values[eq] += 1
        
        if payload.get("zones"):
            zones = payload["zones"]
            if isinstance(zones, list):
                for z in zones:
                    zones_values[z] += 1
            else:
                zones_values[zones] += 1
        
        # Séparer par type pour analyse détaillée
        if domain == "program" and doc_type == "meso_ref":
            meso_ref_docs.append(payload)
        elif domain == "program" and doc_type == "micro_ref":
            micro_ref_docs.append(payload)
        elif domain == "exercise" and doc_type == "exercise":
            exercise_docs.append(payload)
        elif domain == "logic":
            logic_docs.append(payload)
    
    # Afficher les résultats
    print("\n" + "="*80)
    print("📊 RÉSUMÉ PAR DOMAIN/TYPE")
    print("="*80)
    for key, count in sorted(by_domain_type.items(), key=lambda x: x[1], reverse=True):
        print(f"  {key}: {count}")
    
    print("\n" + "="*80)
    print("📋 TOUS LES CHAMPS TROUVÉS DANS LES PAYLOADS")
    print("="*80)
    for field in sorted(all_fields):
        examples = list(field_value_examples[field])[:10]  # 10 premiers exemples
        print(f"  {field}: {len(field_value_examples[field])} valeurs uniques")
        if examples:
            print(f"    Exemples: {', '.join(examples[:5])}")
    
    print("\n" + "="*80)
    print("🎯 MESO_REF - VALEURS UNIQUES PAR CHAMP")
    print("="*80)
    print(f"Total meso_ref: {len(meso_ref_docs)}")
    
    if meso_ref_docs:
        print("\n📌 Objectif (toutes les valeurs):")
        meso_objectifs = Counter(d.get("objectif", "") for d in meso_ref_docs if d.get("objectif"))
        for obj, count in meso_objectifs.most_common():
            print(f"  '{obj}': {count}")
        
        print("\n📌 Groupe (toutes les valeurs):")
        meso_groupes = Counter(d.get("groupe", "") for d in meso_ref_docs if d.get("groupe"))
        for grp, count in meso_groupes.most_common():
            print(f"  '{grp}': {count}")
        
        print("\n📌 Niveau (toutes les valeurs):")
        meso_niveaux = Counter(d.get("niveau", "") for d in meso_ref_docs if d.get("niveau"))
        for niv, count in meso_niveaux.most_common():
            print(f"  '{niv}': {count}")
        
        print("\n📌 Méthode (premiers exemples):")
        meso_methodes = Counter(d.get("methode", "") for d in meso_ref_docs if d.get("methode"))
        for meth, count in meso_methodes.most_common(10):
            print(f"  '{meth[:80]}...': {count}")
        
        print("\n📌 Matériel (toutes les valeurs):")
        meso_materiel = Counter()
        for d in meso_ref_docs:
            mat = d.get("materiel") or d.get("equipment")
            if mat:
                if isinstance(mat, list):
                    for m in mat:
                        meso_materiel[m] += 1
                else:
                    meso_materiel[mat] += 1
        for mat, count in meso_materiel.most_common():
            print(f"  '{mat}': {count}")
        
        print("\n📌 Zones (toutes les valeurs):")
        meso_zones = Counter()
        for d in meso_ref_docs:
            zones = d.get("zones")
            if zones:
                if isinstance(zones, list):
                    for z in zones:
                        meso_zones[z] += 1
                else:
                    meso_zones[zones] += 1
        for zone, count in meso_zones.most_common():
            print(f"  '{zone}': {count}")
        
        # Afficher quelques exemples complets
        print("\n📄 Exemples de documents meso_ref (3 premiers):")
        for i, doc in enumerate(meso_ref_docs[:3], 1):
            print(f"\n  Document {i}:")
            print(f"    meso_id: {doc.get('meso_id', 'N/A')}")
            print(f"    nom: {doc.get('nom', 'N/A')}")
            print(f"    groupe: {doc.get('groupe', 'N/A')}")
            print(f"    objectif: {doc.get('objectif', 'N/A')}")
            print(f"    niveau: {doc.get('niveau', 'N/A')}")
            print(f"    methode: {doc.get('methode', 'N/A')[:60]}...")
            print(f"    materiel: {doc.get('materiel', 'N/A')}")
            print(f"    equipment: {doc.get('equipment', 'N/A')}")
            print(f"    zones: {doc.get('zones', 'N/A')}")
    
    print("\n" + "="*80)
    print("🔍 ANALYSE CROISÉE: GROUPES × OBJECTIFS")
    print("="*80)
    if meso_ref_docs:
        groupe_objectif = defaultdict(Counter)
        for doc in meso_ref_docs:
            grp = doc.get("groupe", "N/A")
            obj = doc.get("objectif", "N/A")
            groupe_objectif[grp][obj] += 1
        
        for grp in sorted(groupe_objectif.keys()):
            print(f"\n  Groupe: '{grp}'")
            for obj, count in groupe_objectif[grp].most_common(5):
                print(f"    → '{obj}': {count}")
    
    print("\n" + "="*80)
    print("🔍 ANALYSE CROISÉE: GROUPES × NIVEAUX")
    print("="*80)
    if meso_ref_docs:
        groupe_niveau = defaultdict(Counter)
        for doc in meso_ref_docs:
            grp = doc.get("groupe", "N/A")
            niv = doc.get("niveau", "N/A")
            groupe_niveau[grp][niv] += 1
        
        for grp in sorted(groupe_niveau.keys()):
            print(f"\n  Groupe: '{grp}'")
            for niv, count in groupe_niveau[grp].most_common():
                print(f"    → '{niv}': {count}")
    
    print("\n" + "="*80)
    print("✅ Analyse terminée")
    print("="*80)

if __name__ == "__main__":
    analyze_qdrant_schema()

