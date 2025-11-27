#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "type", "meso_id", "objectif", "niveau", "nom", "methode",
    "variables", "sollicitation_neuromusculaire", "systeme_energetique",
    "intention", "groupe", "niveau_bloc", "text"
]

REQUIRED_VARIABLES = ["I", "T", "S", "RE", "RY"]

VALID_OBJECTIFS = [
    "reconditionnement", "renforcement", "hypertrophie", "mobilite",
    "perte_de_masse", "endurance_cardio", "performance",
    "sante_longevite", "recuperation", "preparation_objectif",
    "fonctionnel", "maintenance", "autre"
]

VALID_NIVEAUX = ["debutant", "intermediaire", "avance", "Débutant", "Intermédiaire", "Confirmé", "Avancé"]

def validate_record(rec: dict, line_num: int) -> list:
    errors = []
    
    # Vérifier les champs requis
    for field in REQUIRED_FIELDS:
        if field not in rec:
            errors.append(f"Ligne {line_num}: champ manquant '{field}'")
        elif not rec[field]:
            errors.append(f"Ligne {line_num}: champ vide '{field}'")
    
    # Vérifier type
    if "type" in rec and rec["type"] != "meso_ref":
        errors.append(f"Ligne {line_num}: type doit etre 'meso_ref', trouve '{rec.get('type')}'")
    
    # Vérifier meso_id format (accepte "MC1.1" ou "1.1")
    if "meso_id" in rec:
        mid = rec["meso_id"]
        # Accepter format avec ou sans préfixe MC
        if mid.startswith("MC"):
            mid_clean = mid[2:]
        else:
            mid_clean = mid
        if not mid_clean.replace(".", "").isdigit():
            errors.append(f"Ligne {line_num}: meso_id invalide '{mid}'")
    
    # Vérifier objectif
    if "objectif" in rec:
        obj = rec["objectif"]
        if obj not in VALID_OBJECTIFS:
            errors.append(f"Ligne {line_num}: objectif invalide '{obj}' (attendu: {VALID_OBJECTIFS})")
    
    # Vérifier niveau
    if "niveau" in rec:
        niv = rec["niveau"]
        niv_lower = niv.lower()
        if niv_lower not in [v.lower() for v in VALID_NIVEAUX]:
            errors.append(f"Ligne {line_num}: niveau invalide '{niv}'")
    
    # Vérifier variables
    if "variables" in rec:
        vars = rec["variables"]
        if not isinstance(vars, dict):
            errors.append(f"Ligne {line_num}: variables doit etre un objet")
        else:
            for var in REQUIRED_VARIABLES:
                if var not in vars:
                    errors.append(f"Ligne {line_num}: variable manquante '{var}'")
                elif not vars[var]:
                    errors.append(f"Ligne {line_num}: variable vide '{var}'")
    
    return errors

def main():
    jsonl_path = Path("data2/meso_catalog.jsonl")
    
    if not jsonl_path.exists():
        print(f"ERREUR: fichier introuvable: {jsonl_path}")
        sys.exit(1)
    
    all_errors = []
    valid_count = 0
    total_count = 0
    
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                rec = json.loads(line)
                total_count += 1
                errors = validate_record(rec, line_num)
                if errors:
                    all_errors.extend(errors)
                else:
                    valid_count += 1
            except json.JSONDecodeError as e:
                all_errors.append(f"Ligne {line_num}: JSON invalide: {e}")
    
    # Rapport
    print(f"Total: {total_count} lignes")
    print(f"Valides: {valid_count}")
    print(f"Erreurs: {len(all_errors)}")
    
    if all_errors:
        print("\nERREURS DETECTEES:")
        for err in all_errors[:20]:  # Limiter à 20 erreurs
            print(f"  - {err}")
        if len(all_errors) > 20:
            print(f"\n... et {len(all_errors) - 20} autres erreurs")
        sys.exit(1)
    else:
        print("\nOK: Tous les enregistrements sont valides!")
        sys.exit(0)

if __name__ == "__main__":
    main()

