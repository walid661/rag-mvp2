import json
import os

MESO_PATH = r"c:\Dossier Walid\rag-mvp2\data\processed\raw_v2\logic_jsonl_v2\meso_catalog_v2.jsonl"
MICRO_PATH = r"c:\Dossier Walid\rag-mvp2\data\processed\raw_v2\logic_jsonl_v2\micro_catalog_v2.jsonl"

def inspect_meso():
    print("--- Inspecting Meso Catalog ---")
    if not os.path.exists(MESO_PATH):
        print(f"File not found: {MESO_PATH}")
        return

    unique_objectifs = set()
    matches_perte = []
    matches_metabolic = []

    with open(MESO_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            unique_objectifs.add(data.get('objectif', ''))
            
            text_dump = json.dumps(data, ensure_ascii=False).lower()
            if "perte de poids" in text_dump:
                matches_perte.append(data['meso_id'])
            if "metabolic" in text_dump:
                matches_metabolic.append(data['meso_id'])

    print(f"Unique Objectifs (first 10): {list(unique_objectifs)[:10]}")
    print(f"Matches 'Perte de poids': {matches_perte}")
    print(f"Matches 'Metabolic': {matches_metabolic}")

def inspect_micro():
    print("\n--- Inspecting Micro Catalog ---")
    if not os.path.exists(MICRO_PATH):
        print(f"File not found: {MICRO_PATH}")
        return

    unique_focus = set()
    unique_equipment = set()

    with open(MICRO_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            structured = data.get('structured', {})
            if structured:
                unique_focus.add(structured.get('focus_detected'))
                for eq in structured.get('equipment_detected', []):
                    unique_equipment.add(eq)

    print(f"Unique Focus: {unique_focus}")
    print(f"Unique Equipment: {unique_equipment}")

if __name__ == "__main__":
    inspect_meso()
    inspect_micro()
