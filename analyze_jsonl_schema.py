#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyse exhaustive des fichiers JSONL pour comprendre la structure exacte des données.
Extrait tous les champs, leurs valeurs uniques, et leur distribution.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter

DATA_ROOT = Path("data/raw/logic_jsonl")

def analyze_jsonl_files():
    """Analyse exhaustive de tous les fichiers JSONL."""
    print("="*80)
    print("📊 ANALYSE EXHAUSTIVE DES FICHIERS JSONL")
    print("="*80)
    
    # Analyser meso_catalog.jsonl en détail
    meso_file = DATA_ROOT / "meso_catalog.jsonl"
    if meso_file.exists():
        print(f"\n📋 Analyse de {meso_file.name}...")
        analyze_meso_catalog(meso_file)
    
    # Analyser micro_catalog.jsonl
    micro_file = DATA_ROOT / "micro_catalog.jsonl"
    if micro_file.exists():
        print(f"\n📋 Analyse de {micro_file.name}...")
        analyze_micro_catalog(micro_file)
    
    # Analyser les autres fichiers
    for jsonl_file in DATA_ROOT.glob("*.jsonl"):
        if jsonl_file.name not in ["meso_catalog.jsonl", "micro_catalog.jsonl"]:
            print(f"\n📋 Analyse de {jsonl_file.name}...")
            analyze_generic_jsonl(jsonl_file)

def analyze_meso_catalog(file_path: Path):
    """Analyse détaillée de meso_catalog.jsonl."""
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                records.append(rec)
            except json.JSONDecodeError:
                continue
    
    print(f"  Total: {len(records)} documents")
    
    # Tous les champs
    all_fields = set()
    for rec in records:
        all_fields.update(rec.keys())
    
    print(f"\n  📌 Tous les champs: {sorted(all_fields)}")
    
    # Valeurs uniques par champ
    print("\n  📌 Valeurs uniques par champ:")
    
    # Objectif
    objectifs = Counter(rec.get("objectif", "") for rec in records if rec.get("objectif"))
    print(f"\n    Objectif ({len(objectifs)} valeurs uniques):")
    for obj, count in objectifs.most_common():
        print(f"      '{obj}': {count}")
    
    # Groupe
    groupes = Counter(rec.get("groupe", "") for rec in records if rec.get("groupe"))
    print(f"\n    Groupe ({len(groupes)} valeurs uniques):")
    for grp, count in groupes.most_common():
        print(f"      '{grp}': {count}")
    
    # Niveau
    niveaux = Counter(rec.get("niveau", "") for rec in records if rec.get("niveau"))
    print(f"\n    Niveau ({len(niveaux)} valeurs uniques):")
    for niv, count in niveaux.most_common():
        print(f"      '{niv}': {count}")
    
    # Méthode (premiers exemples)
    methodes = Counter(rec.get("methode", "") for rec in records if rec.get("methode"))
    print(f"\n    Méthode ({len(methodes)} valeurs uniques, premiers 10):")
    for meth, count in methodes.most_common(10):
        meth_short = meth[:80] + "..." if len(meth) > 80 else meth
        print(f"      '{meth_short}': {count}")
    
    # Matériel/Equipment
    materiel_all = Counter()
    equipment_all = Counter()
    for rec in records:
        if rec.get("materiel"):
            mat = rec["materiel"]
            if isinstance(mat, list):
                for m in mat:
                    materiel_all[m] += 1
            else:
                materiel_all[mat] += 1
        if rec.get("equipment"):
            eq = rec["equipment"]
            if isinstance(eq, list):
                for e in eq:
                    equipment_all[e] += 1
            else:
                equipment_all[eq] += 1
    
    if materiel_all:
        print(f"\n    Matériel ({len(materiel_all)} valeurs uniques):")
        for mat, count in materiel_all.most_common():
            print(f"      '{mat}': {count}")
    
    if equipment_all:
        print(f"\n    Equipment ({len(equipment_all)} valeurs uniques):")
        for eq, count in equipment_all.most_common():
            print(f"      '{eq}': {count}")
    
    # Zones
    zones_all = Counter()
    for rec in records:
        if rec.get("zones"):
            zones = rec["zones"]
            if isinstance(zones, list):
                for z in zones:
                    zones_all[z] += 1
            else:
                zones_all[zones] += 1
    
    if zones_all:
        print(f"\n    Zones ({len(zones_all)} valeurs uniques):")
        for zone, count in zones_all.most_common():
            print(f"      '{zone}': {count}")
    
    # Analyse croisée: Groupe × Objectif
    print("\n  🔍 Analyse croisée: Groupe × Objectif")
    groupe_objectif = defaultdict(Counter)
    for rec in records:
        grp = rec.get("groupe", "N/A")
        obj = rec.get("objectif", "N/A")
        groupe_objectif[grp][obj] += 1
    
    for grp in sorted(groupe_objectif.keys()):
        print(f"\n    Groupe: '{grp}'")
        for obj, count in groupe_objectif[grp].most_common(10):
            print(f"      → '{obj}': {count}")
    
    # Analyse croisée: Groupe × Niveau
    print("\n  🔍 Analyse croisée: Groupe × Niveau")
    groupe_niveau = defaultdict(Counter)
    for rec in records:
        grp = rec.get("groupe", "N/A")
        niv = rec.get("niveau", "N/A")
        groupe_niveau[grp][niv] += 1
    
    for grp in sorted(groupe_niveau.keys()):
        print(f"\n    Groupe: '{grp}'")
        for niv, count in groupe_niveau[grp].most_common():
            print(f"      → '{niv}': {count}")
    
    # Exemples de documents pour "bras" (chercher dans le texte)
    print("\n  🔍 Recherche de documents pertinents pour 'bras':")
    bras_docs = []
    for rec in records:
        text = rec.get("text", "").lower()
        nom = rec.get("nom", "").lower()
        if "bras" in text or "biceps" in text or "triceps" in text or "bras" in nom or "biceps" in nom or "triceps" in nom:
            bras_docs.append(rec)
    
    print(f"    Trouvé {len(bras_docs)} documents potentiellement pertinents pour 'bras'")
    for i, doc in enumerate(bras_docs[:5], 1):
        print(f"\n    Document {i}:")
        print(f"      meso_id: {doc.get('meso_id', 'N/A')}")
        print(f"      nom: {doc.get('nom', 'N/A')}")
        print(f"      groupe: {doc.get('groupe', 'N/A')}")
        print(f"      objectif: {doc.get('objectif', 'N/A')}")
        print(f"      niveau: {doc.get('niveau', 'N/A')}")
        print(f"      methode: {doc.get('methode', 'N/A')[:60]}...")
    
    # Recherche de documents pour "Tonification & Renforcement" niveau "Débutant"
    print("\n  🔍 Documents 'Tonification & Renforcement' niveau 'Débutant':")
    tonif_debutant = [
        rec for rec in records
        if rec.get("groupe") == "Tonification & Renforcement"
        and rec.get("niveau") == "Débutant"
    ]
    print(f"    Trouvé {len(tonif_debutant)} documents")
    for i, doc in enumerate(tonif_debutant[:5], 1):
        print(f"\n    Document {i}:")
        print(f"      meso_id: {doc.get('meso_id', 'N/A')}")
        print(f"      nom: {doc.get('nom', 'N/A')}")
        print(f"      objectif: {doc.get('objectif', 'N/A')}")
        print(f"      methode: {doc.get('methode', 'N/A')[:60]}...")

def analyze_micro_catalog(file_path: Path):
    """Analyse de micro_catalog.jsonl."""
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                records.append(rec)
            except json.JSONDecodeError:
                continue
    
    print(f"  Total: {len(records)} documents")
    
    # Champs principaux
    groupes = Counter(rec.get("groupe", "") for rec in records if rec.get("groupe"))
    niveaux = Counter(rec.get("niveau", "") for rec in records if rec.get("niveau"))
    objectifs = Counter(rec.get("objectif", "") for rec in records if rec.get("objectif"))
    
    print(f"\n  Groupes: {len(groupes)} valeurs uniques")
    print(f"  Niveaux: {len(niveaux)} valeurs uniques")
    print(f"  Objectifs: {len(objectifs)} valeurs uniques")

def analyze_generic_jsonl(file_path: Path):
    """Analyse générique d'un fichier JSONL."""
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                records.append(rec)
            except json.JSONDecodeError:
                continue
    
    print(f"  Total: {len(records)} documents")
    
    # Champs
    all_fields = set()
    for rec in records:
        all_fields.update(rec.keys())
    
    print(f"  Champs: {sorted(all_fields)}")

if __name__ == "__main__":
    analyze_jsonl_files()

