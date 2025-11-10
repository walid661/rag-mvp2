#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compte les exercices JSON qui n'ont pas de texte (description, consignes, name).
"""

import json
from pathlib import Path
from collections import defaultdict

EXO_DIR = Path("data/raw/exercises_json")

def check_empty_exercises():
    """Compte les exercices sans texte."""
    if not EXO_DIR.exists():
        print(f"❌ Dossier {EXO_DIR} non trouvé")
        return
    
    total = 0
    empty = 0
    empty_details = []
    
    # Statistiques par type de champ manquant
    missing_description = 0
    missing_consignes = 0
    missing_name = 0
    missing_all = 0
    
    # Statistiques par structure
    has_id = 0
    has_groupe_musculaire = 0
    has_zone = 0
    has_equipment = 0
    
    print(f"📊 Analyse des exercices dans {EXO_DIR}...")
    print("="*80)
    
    for exo_path in sorted(EXO_DIR.glob("*.json")):
        total += 1
        try:
            with open(exo_path, "r", encoding="utf-8") as f:
                exo = json.load(f)
        except Exception as e:
            print(f"⚠️  Erreur lecture {exo_path.name}: {e}")
            continue
        
        # Vérifier si le texte est vide
        text = (
            exo.get("description") 
            or exo.get("consignes") 
            or exo.get("name", "")
        )
        
        # Vérifier les champs manquants
        has_desc = bool(exo.get("description"))
        has_cons = bool(exo.get("consignes"))
        has_nom = bool(exo.get("name"))
        
        if not has_desc:
            missing_description += 1
        if not has_cons:
            missing_consignes += 1
        if not has_nom:
            missing_name += 1
        if not has_desc and not has_cons and not has_nom:
            missing_all += 1
        
        # Vérifier si le texte est vide ou très court
        if not text or text.strip() == "" or len(text.strip()) < 10:
            empty += 1
            empty_details.append({
                "file": exo_path.name,
                "id": exo.get("id", "N/A"),
                "name": exo.get("name", "N/A"),
                "description": bool(exo.get("description")),
                "consignes": bool(exo.get("consignes")),
                "text_length": len(text) if text else 0,
                "has_groupe": bool(exo.get("groupe_musculaire")),
                "has_zone": bool(exo.get("zone")),
                "has_equipment": bool(exo.get("equipment") or exo.get("materiel")),
            })
        
        # Statistiques générales
        if exo.get("id"):
            has_id += 1
        if exo.get("groupe_musculaire"):
            has_groupe_musculaire += 1
        if exo.get("zone"):
            has_zone += 1
        if exo.get("equipment") or exo.get("materiel"):
            has_equipment += 1
    
    # Afficher les résultats
    print(f"\n📈 RÉSULTATS")
    print("="*80)
    print(f"Total exercices analysés: {total}")
    print(f"Exercices sans texte (ou texte < 10 caractères): {empty} ({empty/total*100:.1f}%)")
    print(f"Exercices avec texte: {total - empty} ({(total-empty)/total*100:.1f}%)")
    
    print(f"\n📋 CHAMPS MANQUANTS")
    print("="*80)
    print(f"Sans description: {missing_description} ({missing_description/total*100:.1f}%)")
    print(f"Sans consignes: {missing_consignes} ({missing_consignes/total*100:.1f}%)")
    print(f"Sans name: {missing_name} ({missing_name/total*100:.1f}%)")
    print(f"Sans aucun des trois: {missing_all} ({missing_all/total*100:.1f}%)")
    
    print(f"\n📊 STATISTIQUES GÉNÉRALES")
    print("="*80)
    print(f"Avec ID: {has_id} ({has_id/total*100:.1f}%)")
    print(f"Avec groupe_musculaire: {has_groupe_musculaire} ({has_groupe_musculaire/total*100:.1f}%)")
    print(f"Avec zone: {has_zone} ({has_zone/total*100:.1f}%)")
    print(f"Avec equipment/materiel: {has_equipment} ({has_equipment/total*100:.1f}%)")
    
    if empty > 0:
        print(f"\n🔍 EXEMPLES D'EXERCICES SANS TEXTE (10 premiers)")
        print("="*80)
        for i, detail in enumerate(empty_details[:10], 1):
            print(f"\n  {i}. {detail['file']}")
            print(f"     ID: {detail['id']}")
            print(f"     Name: {detail['name']}")
            print(f"     Description: {detail['description']}, Consignes: {detail['consignes']}")
            print(f"     Texte: {detail['text_length']} caractères")
            print(f"     Métadonnées: groupe={detail['has_groupe']}, zone={detail['has_zone']}, equipment={detail['has_equipment']}")
    
    # Statistiques sur les exercices vides
    if empty > 0:
        empty_with_metadata = sum(1 for d in empty_details if d['has_groupe'] or d['has_zone'] or d['has_equipment'])
        print(f"\n💡 EXERCICES VIDES AVEC MÉTADONNÉES")
        print("="*80)
        print(f"Exercices vides avec métadonnées (groupe/zone/equipment): {empty_with_metadata} ({empty_with_metadata/empty*100:.1f}% des vides)")
        print(f"Exercices vides sans métadonnées: {empty - empty_with_metadata} ({(empty-empty_with_metadata)/empty*100:.1f}% des vides)")
    
    print("\n✅ Analyse terminée")

if __name__ == "__main__":
    check_empty_exercises()

