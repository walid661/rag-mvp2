"""
Enrichit les exercices avec OpenAI pour ajouter :
- antagonist_muscle_group
- secondary_muscle_groups
- exercise_family

Utilise les exercices de data/raw/exercices_new/ et crée les versions enrichies
dans data/processed/raw_v2/exercices_new_v2/
"""

import json
import os
from pathlib import Path
from openai import OpenAI
from tqdm import tqdm
import time
from dotenv import load_dotenv

load_dotenv()

# Configuration
RAW_DIR = Path("data/raw/exercices_new")
OUTPUT_DIR = Path("data/processed/raw_v2/exercices_new_v2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def enrich_exercise_with_openai(exercise_data: dict) -> dict:
    """
    Enrichit un exercice avec OpenAI pour ajouter les champs manquants.
    """
    # Construire le prompt pour OpenAI
    prompt = f"""Tu es un expert en anatomie et musculation. Analyse cet exercice et réponds en JSON strict :

Exercice : {exercise_data.get('exercise', '')}
Groupe musculaire principal : {exercise_data.get('target_muscle_group', '')}
Pattern de mouvement : {exercise_data.get('movement_pattern', '')}
Type de force : {exercise_data.get('force_type', '')}
Mécanique : {exercise_data.get('mechanics', '')}
Région du corps : {exercise_data.get('body_region', '')}

Réponds avec un JSON contenant EXACTEMENT ces champs :
{{
  "antagonist_muscle_group": "nom du muscle antagoniste (ex: si Biceps alors Triceps, si Quadriceps alors Ischio-jambiers, null si aucun antagoniste clair)",
  "secondary_muscle_groups": ["liste des groupes musculaires secondaires sollicités (ex: Avant-bras pour curl biceps)"],
  "exercise_family": "famille d'exercice (Curl, Extension, Press, Row, Squat, Lunge, Deadlift, Pull, Push, Isolation, Compound, Plank, Crunch, etc.)"
}}

Règles :
- antagonist_muscle_group : le muscle qui fait le mouvement opposé (flexion vs extension, poussée vs tirage). Utilise null si aucun antagoniste clair.
- secondary_muscle_groups : muscles sollicités mais pas principalement (ex: avant-bras pour curl biceps, épaules pour développé couché)
- exercise_family : catégorie fonctionnelle de l'exercice. Choisis parmi : Curl, Extension, Press, Row, Squat, Lunge, Deadlift, Pull, Push, Isolation, Compound, Plank, Crunch, Raise, Fly, Kickback, Dip, Pull-up, Chin-up, ou autre si nécessaire.

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Plus économique
            messages=[
                {"role": "system", "content": "Tu es un expert en anatomie et musculation. Tu réponds UNIQUEMENT en JSON valide."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Plus déterministe
            response_format={"type": "json_object"}
        )
        
        enriched = json.loads(response.choices[0].message.content)
        
        # Valider et nettoyer
        result = {
            "antagonist_muscle_group": enriched.get("antagonist_muscle_group") if enriched.get("antagonist_muscle_group") != "null" else None,
            "secondary_muscle_groups": enriched.get("secondary_muscle_groups", []),
            "exercise_family": enriched.get("exercise_family", "Unknown")
        }
        
        return result
        
    except Exception as e:
        print(f"Erreur OpenAI pour {exercise_data.get('exercise')}: {e}")
        return {
            "antagonist_muscle_group": None,
            "secondary_muscle_groups": [],
            "exercise_family": "Unknown"
        }

def process_all_exercises(limit: int = None):
    """
    Traite tous les exercices et les enrichit.
    
    Args:
        limit: Limite le nombre d'exercices à traiter (pour tests). None = tous.
    """
    exercise_files = sorted(RAW_DIR.glob("*.json"))
    
    if limit:
        exercise_files = exercise_files[:limit]
        print(f"⚠️  Mode test : traitement de {limit} exercices seulement")
    
    print(f"Traitement de {len(exercise_files)} exercices...")
    
    errors = 0
    for ex_file in tqdm(exercise_files, desc="Enrichissement"):
        try:
            # Charger l'exercice original
            with open(ex_file, 'r', encoding='utf-8') as f:
                exercise = json.load(f)
            
            # Vérifier si déjà enrichi (éviter de re-traiter)
            if "antagonist_muscle_group" in exercise:
                print(f"⚠️  {ex_file.name} déjà enrichi, skip")
                # Copier quand même pour cohérence
                output_file = OUTPUT_DIR / ex_file.name
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(exercise, f, ensure_ascii=False, indent=2)
                continue
            
            # Enrichir avec OpenAI
            enriched_fields = enrich_exercise_with_openai(exercise)
            
            # Fusionner avec l'exercice original
            exercise_v2 = {**exercise, **enriched_fields}
            
            # Sauvegarder dans v2
            output_file = OUTPUT_DIR / ex_file.name
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(exercise_v2, f, ensure_ascii=False, indent=2)
            
            # Rate limiting (OpenAI) - 10 requêtes/seconde max
            time.sleep(0.1)
            
        except Exception as e:
            errors += 1
            print(f"❌ Erreur pour {ex_file.name}: {e}")
    
    print(f"\n✅ {len(exercise_files) - errors} exercices enrichis dans {OUTPUT_DIR}")
    if errors > 0:
        print(f"❌ {errors} erreurs rencontrées")

if __name__ == "__main__":
    import sys
    
    # Permettre de limiter pour les tests
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("Usage: python enrich_exercises_v2.py [limit]")
            sys.exit(1)
    
    process_all_exercises(limit=limit)

