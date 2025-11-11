# Guide d'utilisation des données enrichies (v2)

## Structure

Les données enrichies sont dans `data/processed/raw_v2/` :
- `exercices_new_v2/` : Exercices enrichis avec `antagonist_muscle_group`, `secondary_muscle_groups`, `exercise_family`
- `logic_jsonl_v2/` : Règles structurées avec champs JSON structurés

Les données originales dans `data/raw/` restent intactes.

## Scripts disponibles

### 1. Enrichir les exercices

```bash
# Enrichir tous les exercices (3078 exercices)
python scripts/enrich_exercises_v2.py

# Mode test : enrichir seulement 10 exercices
python scripts/enrich_exercises_v2.py 10
```

**Coût estimé OpenAI** : ~$0.50-1.00 pour 3078 exercices (gpt-4o-mini)

### 2. Structurer les règles

```bash
python scripts/structurize_rules_v2.py
```

**Coût estimé OpenAI** : ~$0.10-0.20 pour toutes les règles

### 3. Créer les règles d'équilibrage musculaire

```bash
python scripts/create_muscle_balance_rules.py
```

**Pas d'OpenAI** : Génération locale basée sur les paires antagonistes connues

### 4. Créer des exemples de séances équilibrées

```bash
python scripts/create_balanced_session_examples.py
```

**Coût estimé OpenAI** : ~$0.20-0.30 pour 21 exemples (7 zones × 3 niveaux)

## Activation de v2

Une fois les données enrichies créées, pour activer v2 :

1. Ouvrir `app/services/ingest_logic_jsonl.py`
2. Commenter les lignes 14-16 (version originale)
3. Décommenter les lignes 22-24 (version v2)
4. Relancer l'ingestion : `python -m app.services.ingest_logic_jsonl --reload`

## Nouveaux champs dans les exercices

- `antagonist_muscle_group` : Muscle antagoniste (ex: "Triceps" pour "Biceps")
- `secondary_muscle_groups` : Liste des muscles secondaires (ex: ["Avant-bras"])
- `exercise_family` : Famille d'exercice (ex: "Curl", "Extension", "Press")

## Nouveaux fichiers de règles

- `muscle_balance_rules.jsonl` : Règles génériques d'équilibrage musculaire
- `balanced_session_examples.jsonl` : Exemples de séances équilibrées

## Améliorations du générateur

Le prompt du générateur (`app/services/generator.py`) a été amélioré pour :
- Utiliser automatiquement `antagonist_muscle_group` pour équilibrer les séances
- Varier les familles d'exercices avec `exercise_family`
- Appliquer ces règles de manière générique (pas juste biceps/triceps)

## Coût total estimé

- Enrichissement exercices : ~$0.50-1.00
- Structuration règles : ~$0.10-0.20
- Exemples séances : ~$0.20-0.30
- **Total : ~$0.80-1.50**

