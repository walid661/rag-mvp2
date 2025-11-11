"""Test rapide de l'enrichissement pour un exercice biceps."""
import json
from pathlib import Path

# Trouver un exercice biceps
bicep_files = list(Path("data/raw/exercices_new").glob("*Bicep*.json"))
if bicep_files:
    original = json.loads(bicep_files[0].read_text())
    print(f"Exercice original: {original['exercise']}")
    print(f"Target: {original['target_muscle_group']}")
    
    # Vérifier si enrichi
    enriched_path = Path("data/processed/raw_v2/exercices_new_v2") / bicep_files[0].name
    if enriched_path.exists():
        enriched = json.loads(enriched_path.read_text())
        print(f"\n✅ Enrichi:")
        print(f"  Antagoniste: {enriched.get('antagonist_muscle_group')}")
        print(f"  Secondaires: {enriched.get('secondary_muscle_groups')}")
        print(f"  Famille: {enriched.get('exercise_family')}")
    else:
        print(f"\n❌ Pas encore enrichi: {enriched_path.name}")
        print("   Lancer: python scripts/enrich_exercises_v2.py")
else:
    print("Aucun exercice biceps trouvé")

