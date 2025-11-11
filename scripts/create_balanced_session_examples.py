"""
Crée des exemples de séances équilibrées pour différentes zones.
Utilise OpenAI pour générer des exemples réalistes.
"""

import json
from pathlib import Path
from openai import OpenAI
import os
from tqdm import tqdm
import time
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path("data/processed/raw_v2/logic_jsonl_v2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_balanced_session_example(zone: str, niveau: str):
    """
    Crée un exemple de séance équilibrée pour une zone donnée.
    """
    prompt = f"""Tu es un expert en planification d'entraînement. Crée un exemple de séance équilibrée pour :

Zone : {zone}
Niveau : {niveau}

Règles d'équilibrage OBLIGATOIRES :
1. Inclure les muscles antagonistes (ex: Biceps ET Triceps pour "bras")
2. Varier les familles d'exercices (Curl, Extension, Press, Row, etc.)
3. Adapter au niveau ({niveau}) : nombre de séries, répétitions, charge
4. Ratio 1:1 pour les antagonistes (même nombre d'exercices pour chaque)

Réponds en JSON avec cette structure EXACTE :
{{
  "zone": "{zone}",
  "niveau": "{niveau}",
  "exercises": [
    {{
      "name": "nom de l'exercice",
      "target_muscle_group": "groupe musculaire principal",
      "exercise_family": "famille (Curl, Extension, Press, etc.)",
      "series": "nombre de séries",
      "reps": "nombre de répétitions ou durée",
      "rest": "temps de repos en secondes",
      "equipment": "équipement nécessaire"
    }}
  ],
  "balance_explanation": "explication de l'équilibrage (antagonistes inclus, variété des familles)"
}}

Important :
- Minimum 4 exercices pour montrer l'équilibrage
- Inclure au moins 2 familles d'exercices différentes
- Pour "bras" : inclure Biceps ET Triceps
- Pour "jambes" : inclure Quadriceps ET Ischio-jambiers
- Adapter les séries/reps au niveau ({niveau})

Réponds UNIQUEMENT en JSON valide."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es un expert en planification d'entraînement. Tu réponds UNIQUEMENT en JSON valide."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        
        example = json.loads(response.choices[0].message.content)
        
        return {
            "id": f"balanced_session_{zone.lower().replace(' ', '_')}_{niveau.lower()}",
            "source": "generated",
            "type": "balanced_session_example",
            "zone": zone,
            "niveau": niveau,
            "example": example,
            "structured": {
                "muscle_groups_included": list(set([ex.get("target_muscle_group") for ex in example.get("exercises", [])])),
                "exercise_families_included": list(set([ex.get("exercise_family") for ex in example.get("exercises", [])])),
                "balance_ratio": "1:1 pour antagonistes"
            }
        }
        
    except Exception as e:
        print(f"❌ Erreur pour {zone}/{niveau}: {e}")
        return None

def main():
    """
    Crée des exemples pour différentes zones et niveaux.
    """
    zones = ["bras", "jambes", "haut du corps", "bas du corps", "tronc", "dos", "épaules"]
    niveaux = ["Débutant", "Intermédiaire", "Avancé"]
    
    examples = []
    
    print(f"Création de {len(zones) * len(niveaux)} exemples de séances équilibrées...")
    
    for zone in tqdm(zones, desc="Zones"):
        for niveau in niveaux:
            example = create_balanced_session_example(zone, niveau)
            if example:
                examples.append(example)
            
            # Rate limiting
            time.sleep(0.2)
    
    # Sauvegarder
    output_file = OUTPUT_DIR / "balanced_session_examples.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    print(f"\n✅ {len(examples)} exemples de séances équilibrées créés dans {output_file}")

if __name__ == "__main__":
    main()

