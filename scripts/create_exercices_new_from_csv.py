#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crée des JSON d'exercices à partir du CSV source avec traduction complète en français.
- Lit: Copy of BIG DATA base fitness exercices.xlsx - Exercises (2).csv
- Crée: data/raw/exercices_new/*.json
- Traduit toutes les valeurs des champs en français via OpenAI
- Génère un texte structuré incluant EXACTEMENT tous les champs
"""
import os
import sys
import json
import csv
from pathlib import Path
from typing import Dict, Any, Set, List
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm
import re
from collections import defaultdict

# Charger .env
load_dotenv()

# Configuration OpenAI
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("ERREUR: OPENAI_API_KEY manquant dans .env", file=sys.stderr)
    sys.exit(1)

MODEL = os.getenv("LLM_MODEL_FOR_TEXT", "gpt-4o-mini")
client = OpenAI(api_key=API_KEY)

# Chemins
CSV_FILE = Path("Copy of BIG DATA base fitness exercices.xlsx - Exercises (2).csv")
OUTPUT_DIR = Path("data/raw/exercices_new")
MAPPING_FILE = Path("data/raw/exercices_new_translation_mapping.json")

# Créer le dossier de sortie
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def sanitize_filename(name: str) -> str:
    """Nettoie le nom de l'exercice pour créer un nom de fichier valide."""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    if len(name) > 100:
        name = name[:100]
    return name.strip('_')

def translate_values_batch(values: Set[str], field_name: str) -> Dict[str, str]:
    """
    Traduit un batch de valeurs en français via OpenAI.
    Retourne un dictionnaire {valeur_anglaise: valeur_française}
    """
    if not values:
        return {}
    
    # Filtrer les valeurs vides et "Unsorted*"
    clean_values = {v for v in values if v and v.strip() and v != "Unsorted*"}
    
    if not clean_values:
        return {}
    
    # Créer le prompt pour traduire toutes les valeurs
    values_list = sorted(list(clean_values))
    values_text = "\n".join([f"- {v}" for v in values_list])
    
    prompt = f"""Tu es un expert en fitness et musculation. Traduis les valeurs suivantes du champ "{field_name}" en français, en conservant le contexte sportif/fitness.

Valeurs à traduire:
{values_text}

Important:
- Traduis chaque valeur de manière précise et naturelle en français
- Conserve le contexte technique et sportif
- Pour les termes techniques (ex: "Compound", "Isolation"), utilise les termes français standards du fitness
- Retourne UNIQUEMENT un JSON avec le format: {{"valeur_anglaise": "valeur_française"}}
- Ne retourne rien d'autre que le JSON

JSON de traduction:"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Tu es un expert en fitness qui traduit des termes techniques en français."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Extraire le JSON (peut être entouré de markdown)
        result_text = re.sub(r'```json\s*', '', result_text)
        result_text = re.sub(r'```\s*', '', result_text)
        result_text = result_text.strip()
        
        translation_map = json.loads(result_text)
        
        # Vérifier que toutes les valeurs ont été traduites
        missing = clean_values - set(translation_map.keys())
        if missing:
            print(f"  ⚠️  Valeurs non traduites pour {field_name}: {missing}")
            # Ajouter les valeurs manquantes avec leur valeur originale
            for val in missing:
                translation_map[val] = val
        
        return translation_map
    except Exception as e:
        print(f"  ⚠️  Erreur traduction pour {field_name}: {e}")
        # Fallback: retourner un mapping identité
        return {v: v for v in clean_values}

def build_translation_mapping(csv_file: Path) -> Dict[str, Dict[str, str]]:
    """
    Analyse le CSV et crée un mapping de traduction pour toutes les valeurs uniques.
    Retourne: {nom_colonne: {valeur_anglaise: valeur_française}}
    """
    print("📊 Analyse du CSV pour identifier toutes les valeurs uniques...")
    
    # Charger le mapping existant s'il existe
    if MAPPING_FILE.exists():
        print(f"📖 Chargement du mapping existant: {MAPPING_FILE}")
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            existing_mapping = json.load(f)
    else:
        existing_mapping = {}
    
    # Collecter toutes les valeurs uniques par colonne
    column_values = defaultdict(set)
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for col_name, value in row.items():
                if value and value.strip() and value != "Unsorted*":
                    column_values[col_name].add(value.strip())
    
    print(f"📋 Colonnes trouvées: {len(column_values)}")
    for col_name, values in column_values.items():
        print(f"  - {col_name}: {len(values)} valeurs uniques")
    
    # Traduire chaque colonne
    translation_mapping = {}
    
    for col_name, values in tqdm(column_values.items(), desc="Traduction des valeurs"):
        # Vérifier si on a déjà traduit cette colonne
        if col_name in existing_mapping:
            # Vérifier si de nouvelles valeurs ont été ajoutées
            existing_values = set(existing_mapping[col_name].keys())
            new_values = values - existing_values
            
            if new_values:
                print(f"  🔄 Nouvelles valeurs pour {col_name}: {len(new_values)}")
                new_translations = translate_values_batch(new_values, col_name)
                # Fusionner avec l'existant
                translation_mapping[col_name] = {**existing_mapping[col_name], **new_translations}
            else:
                print(f"  ✅ {col_name}: mapping déjà complet")
                translation_mapping[col_name] = existing_mapping[col_name]
        else:
            print(f"  🌐 Traduction de {col_name} ({len(values)} valeurs)...")
            translation_mapping[col_name] = translate_values_batch(values, col_name)
    
    # Sauvegarder le mapping
    print(f"\n💾 Sauvegarde du mapping: {MAPPING_FILE}")
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(translation_mapping, f, ensure_ascii=False, indent=2)
    
    return translation_mapping

def generate_structured_text(exercise_data: Dict[str, Any], translation_mapping: Dict[str, Dict[str, str]]) -> str:
    """
    Génère un texte structuré qui inclut EXACTEMENT tous les champs du JSON
    avec un format de phrase prédéfini.
    """
    # Template de phrase pour chaque champ
    field_templates = {
        'exercise': 'Exercice: {value}',
        'difficulty_level': 'Difficulté: {value}',
        'target_muscle_group': 'Muscles ciblés: {value}',
        'primary_equipment': 'Équipement: {value}',
        'posture': 'Posture: {value}',
        'single_or_double_arm': 'Bras: {value}',
        'continuous_or_alternating_arms': 'Mouvement des bras: {value}',
        'grip': 'Prise: {value}',
        'continuous_or_alternating_legs': 'Mouvement des jambes: {value}',
        'foot_elevation': 'Élévation des pieds: {value}',
        'combination_exercises': 'Type d\'exercice: {value}',
        'movement_pattern': 'Modèle de mouvement: {value}',
        'body_region': 'Région du corps: {value}',
        'force_type': 'Type de force: {value}',
        'mechanics': 'Mécanique: {value}',
        'laterality': 'Latéralité: {value}',
        'primary_exercise_classification': 'Classification: {value}'
    }
    
    # Construire le texte avec TOUS les champs
    text_parts = []
    
    for field_name, template in field_templates.items():
        value = exercise_data.get(field_name)
        
        if value and str(value).strip() and str(value) != "Unsorted*":
            # La valeur est déjà traduite dans exercise_data
            text_parts.append(template.format(value=value))
    
    # Joindre toutes les parties avec des points
    structured_text = ". ".join(text_parts) + "."
    
    # Enrichir avec OpenAI pour un texte plus naturel tout en gardant toutes les infos
    prompt = f"""Tu es un expert en fitness. À partir de cette description structurée d'un exercice, génère un texte descriptif en français, naturel et fluide, qui inclut TOUTES les informations suivantes de manière intégrée et naturelle.

Description structurée:
{structured_text}

Important:
- Le texte doit inclure TOUTES les informations de la description structurée
- Utilise un langage naturel et fluide
- Optimise pour la recherche sémantique (mots-clés pertinents)
- Fait environ 100-150 mots
- Conserve tous les détails techniques (difficulté, muscles, équipement, posture, etc.)

Texte descriptif:"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Tu es un expert en fitness qui génère des descriptions d'exercices complètes et naturelles."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  ⚠️  Erreur OpenAI pour {exercise_data.get('exercise', 'unknown')}: {e}")
        # Fallback: retourner le texte structuré
        return structured_text

def process_csv_to_json():
    """Lit le CSV et crée les JSON correspondants avec traduction complète."""
    if not CSV_FILE.exists():
        print(f"❌ Fichier CSV introuvable: {CSV_FILE}", file=sys.stderr)
        sys.exit(1)
    
    print(f"📖 Lecture du CSV: {CSV_FILE}")
    
    # Étape 1: Construire le mapping de traduction
    print("\n" + "="*60)
    print("ÉTAPE 1: Construction du mapping de traduction")
    print("="*60)
    translation_mapping = build_translation_mapping(CSV_FILE)
    
    # Étape 2: Traiter chaque ligne du CSV
    print("\n" + "="*60)
    print("ÉTAPE 2: Création des JSON avec valeurs traduites")
    print("="*60)
    
    exercises_created = 0
    exercises_skipped = 0
    
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Compter le nombre total de lignes
        total_lines = sum(1 for _ in reader)
        f.seek(0)
        reader = csv.DictReader(f)
        
        print(f"📊 {total_lines} exercices à traiter\n")
        
        for idx, row in enumerate(tqdm(reader, total=total_lines, desc="Création des JSON")):
            # Nettoyer les valeurs
            exercise_data = {}
            
            for key, value in row.items():
                if value and value.strip() and value != "Unsorted*":
                    # Traduire la valeur
                    if key in translation_mapping:
                        translated_value = translation_mapping[key].get(value.strip(), value.strip())
                        exercise_data[key] = translated_value
                        # Garder aussi la valeur originale pour référence
                        exercise_data[f"{key}_en"] = value.strip()
                    else:
                        exercise_data[key] = value.strip()
                else:
                    exercise_data[key] = None
            
            # Ignorer les lignes sans nom d'exercice
            if not exercise_data.get('exercise'):
                exercises_skipped += 1
                continue
            
            exercise_name = exercise_data['exercise']
            
            # Générer le texte structuré avec OpenAI
            if (idx + 1) % 10 == 0:  # Afficher tous les 10 exercices
                print(f"  [{idx+1}/{total_lines}] Génération texte pour: {exercise_name[:50]}...")
            
            text = generate_structured_text(exercise_data, translation_mapping)
            exercise_data['text'] = text
            
            # Créer le nom de fichier
            filename = sanitize_filename(exercise_name)
            json_filename = f"{idx:04d}_{filename}.json"
            json_path = OUTPUT_DIR / json_filename
            
            # Sauvegarder le JSON
            with open(json_path, 'w', encoding='utf-8') as json_file:
                json.dump(exercise_data, json_file, ensure_ascii=False, indent=2)
            
            exercises_created += 1
            
            # Afficher un résumé tous les 100 exercices
            if (idx + 1) % 100 == 0:
                print(f"\n  ✅ {exercises_created} exercices créés jusqu'à présent\n")
    
    print(f"\n{'='*60}")
    print(f"✅ Terminé!")
    print(f"  - Exercices créés: {exercises_created}")
    print(f"  - Exercices ignorés: {exercises_skipped}")
    print(f"  - Dossier de sortie: {OUTPUT_DIR}")
    print(f"  - Mapping de traduction: {MAPPING_FILE}")
    print(f"{'='*60}")

if __name__ == "__main__":
    process_csv_to_json()


