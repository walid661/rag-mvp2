"""
Structure les règles textuelles en JSON structuré avec OpenAI.
Crée les versions structurées dans data/processed/raw_v2/logic_jsonl_v2/
"""

import json
from pathlib import Path
from openai import OpenAI
import os
from tqdm import tqdm
import time
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = Path("data/raw/logic_jsonl")
OUTPUT_DIR = Path("data/processed/raw_v2/logic_jsonl_v2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def structurize_rule_with_openai(rule_data: dict) -> dict:
    """
    Structure une règle textuelle en JSON structuré.
    """
    rule_type = rule_data.get("type", "")
    rule_text = rule_data.get("rule_text", "")
    applies_to = rule_data.get("applies_to", "")
    
    prompt = f"""Tu es un expert en structuration de règles d'entraînement. Analyse cette règle et structure-la en JSON.

Type de règle : {rule_type}
S'applique à : {applies_to}
Texte de la règle :
{rule_text}

Extrais et structure les informations suivantes en JSON :
{{
  "structured_fields": {{
    "muscle_groups_required": ["liste des groupes musculaires obligatoires mentionnés"],
    "muscle_groups_optional": ["liste des groupes musculaires optionnels mentionnés"],
    "exercise_families_allowed": ["liste des familles d'exercices autorisées (Curl, Extension, Press, etc.)"],
    "equipment_required": ["liste des équipements obligatoires"],
    "equipment_optional": ["liste des équipements optionnels"],
    "intensity_range": "plage d'intensité mentionnée (ex: faible-modérée) ou null",
    "volume_range": "plage de volume mentionnée (ex: 3-5 séries) ou null",
    "rest_range": "plage de repos mentionnée (ex: 60-90 sec) ou null",
    "balance_required": true/false - si équilibrage musculaire requis,
    "antagonist_pairs": [["muscle1", "muscle2"], ...] - paires antagonistes mentionnées,
    "variety_required": true/false - si variété d'exercices requise
  }},
  "extracted_keywords": ["mots-clés importants extraits du texte"],
  "conditions": {{
    "applies_when": "conditions d'application extraites",
    "exceptions": "exceptions éventuelles mentionnées"
  }}
}}

Si un champ n'est pas applicable ou non mentionné, utilise null ou [].
Réponds UNIQUEMENT en JSON valide."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es un expert en structuration de règles. Tu réponds UNIQUEMENT en JSON valide."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        structured = json.loads(response.choices[0].message.content)
        
        # Fusionner avec la règle originale
        rule_v2 = {
            **rule_data,
            "structured": structured.get("structured_fields", {}),
            "keywords": structured.get("extracted_keywords", []),
            "conditions_parsed": structured.get("conditions", {})
        }
        
        return rule_v2
        
    except Exception as e:
        print(f"Erreur pour règle {rule_data.get('id')}: {e}")
        # Retourner la règle originale si erreur
        return {
            **rule_data,
            "structured": {},
            "keywords": [],
            "conditions_parsed": {}
        }

def process_rules_file(input_file: Path, output_file: Path):
    """
    Traite un fichier JSONL de règles.
    """
    rules_v2 = []
    rules = []
    
    # Charger toutes les règles
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rules.append(json.loads(line))
    
    print(f"  Traitement de {len(rules)} règles...")
    
    for rule in tqdm(rules, desc=f"  Structuration {input_file.name}", leave=False):
        # Vérifier si déjà structuré
        if "structured" in rule:
            rules_v2.append(rule)
            continue
        
        rule_v2 = structurize_rule_with_openai(rule)
        rules_v2.append(rule_v2)
        
        # Rate limiting
        time.sleep(0.1)
    
    # Sauvegarder
    with open(output_file, 'w', encoding='utf-8') as f:
        for rule in rules_v2:
            f.write(json.dumps(rule, ensure_ascii=False) + '\n')
    
    print(f"  ✅ {len(rules_v2)} règles structurées dans {output_file.name}")

def main():
    """
    Traite tous les fichiers JSONL de règles.
    """
    jsonl_files = sorted(RAW_DIR.glob("*.jsonl"))
    
    if not jsonl_files:
        print(f"❌ Aucun fichier JSONL trouvé dans {RAW_DIR}")
        return
    
    print(f"Traitement de {len(jsonl_files)} fichiers de règles...")
    
    for jsonl_file in jsonl_files:
        output_file = OUTPUT_DIR / jsonl_file.name
        process_rules_file(jsonl_file, output_file)
    
    print(f"\n✅ Tous les fichiers traités dans {OUTPUT_DIR}")

if __name__ == "__main__":
    main()

