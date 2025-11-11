"""
Crée des règles d'équilibrage musculaire génériques (pas juste biceps/triceps).
Crée data/processed/raw_v2/logic_jsonl_v2/muscle_balance_rules.jsonl
"""

import json
from pathlib import Path

OUTPUT_DIR = Path("data/processed/raw_v2/logic_jsonl_v2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Paires de muscles antagonistes (génériques)
ANTAGONIST_PAIRS = [
    ["Biceps", "Triceps"],
    ["Quadriceps", "Ischio-jambiers"],
    ["Pectoraux", "Dos"],
    ["Épaules", "Dos"],
    ["Abdominaux", "Lombaires"],
    ["Fessiers", "Psoas"],
    ["Deltoïdes antérieurs", "Deltoïdes postérieurs"],
    ["Fléchisseurs de hanche", "Extenseurs de hanche"],
    ["Avant-bras fléchisseurs", "Avant-bras extenseurs"]
]

# Zones du corps avec groupes musculaires associés
ZONE_TO_MUSCLE_GROUPS = {
    "bras": {
        "primary": ["Biceps", "Triceps"],
        "secondary": ["Avant-bras"],
        "antagonist_pairs": [["Biceps", "Triceps"]]
    },
    "jambes": {
        "primary": ["Quadriceps", "Ischio-jambiers", "Fessiers"],
        "secondary": ["Mollets"],
        "antagonist_pairs": [["Quadriceps", "Ischio-jambiers"]]
    },
    "haut du corps": {
        "primary": ["Pectoraux", "Dos", "Épaules", "Biceps", "Triceps"],
        "secondary": ["Avant-bras"],
        "antagonist_pairs": [["Pectoraux", "Dos"], ["Biceps", "Triceps"]]
    },
    "bas du corps": {
        "primary": ["Quadriceps", "Ischio-jambiers", "Fessiers"],
        "secondary": ["Mollets"],
        "antagonist_pairs": [["Quadriceps", "Ischio-jambiers"]]
    },
    "tronc": {
        "primary": ["Abdominaux", "Lombaires"],
        "secondary": ["Obliques"],
        "antagonist_pairs": [["Abdominaux", "Lombaires"]]
    },
    "dos": {
        "primary": ["Dos", "Lombaires", "Trapèzes"],
        "secondary": ["Rhomboides"],
        "antagonist_pairs": [["Dos", "Pectoraux"]]
    },
    "épaules": {
        "primary": ["Épaules", "Deltoïdes"],
        "secondary": ["Trapèzes"],
        "antagonist_pairs": [["Deltoïdes antérieurs", "Deltoïdes postérieurs"]]
    }
}

def create_muscle_balance_rules():
    """
    Crée des règles génériques d'équilibrage musculaire.
    """
    rules = []
    
    # Règle 1 : Équilibrage automatique des antagonistes (GÉNÉRIQUE)
    rules.append({
        "id": "muscle_balance_antagonist_auto",
        "source": "generated",
        "type": "muscle_balance_rule",
        "applies_to": "exercise_selection",
        "rule_text": "Lorsqu'un utilisateur demande une zone du corps ou un groupe musculaire, équilibrer automatiquement les muscles antagonistes. Si un muscle est ciblé, inclure son antagoniste dans la séance. Ratio recommandé : 1:1 pour les antagonistes.",
        "structured": {
            "balance_required": True,
            "antagonist_pairs": ANTAGONIST_PAIRS,
            "auto_balance": True,
            "ratio": "1:1"
        },
        "keywords": ["antagoniste", "équilibrage", "ratio", "muscle opposé"],
        "conditions_parsed": {
            "applies_when": "zone_musculaire ou groupe_musculaire demandé par l'utilisateur",
            "exceptions": "si l'utilisateur spécifie explicitement un seul muscle (ex: 'seulement biceps')"
        }
    })
    
    # Règle 2 : Équilibrage par zone (GÉNÉRIQUE)
    for zone, muscle_info in ZONE_TO_MUSCLE_GROUPS.items():
        rules.append({
            "id": f"muscle_balance_zone_{zone.lower().replace(' ', '_')}",
            "source": "generated",
            "type": "muscle_balance_rule",
            "applies_to": "exercise_selection",
            "zone": zone,
            "rule_text": f"Pour une séance '{zone}', inclure des exercices pour : {', '.join(muscle_info['primary'])}. Équilibrer les antagonistes avec un ratio 1:1. Inclure aussi les groupes secondaires si pertinent : {', '.join(muscle_info.get('secondary', []))}.",
            "structured": {
                "muscle_groups_required": muscle_info["primary"],
                "muscle_groups_optional": muscle_info.get("secondary", []),
                "balance_required": True,
                "antagonist_pairs": muscle_info.get("antagonist_pairs", []),
                "ratio": "1:1 pour antagonistes"
            },
            "keywords": [zone, "équilibrage", "antagoniste"] + muscle_info["primary"],
            "conditions_parsed": {
                "applies_when": f"zone demandée = '{zone}'"
            }
        })
    
    # Règle 3 : Variété des exercices (GÉNÉRIQUE)
    rules.append({
        "id": "exercise_variety_rule",
        "source": "generated",
        "type": "exercise_variety_rule",
        "applies_to": "exercise_selection",
        "rule_text": "Dans une séance, varier les familles d'exercices. Éviter de répéter le même type d'exercice (ex: 3 curls similaires). Mélanger les familles : Curl, Extension, Press, Row, Squat, Lunge, Deadlift, Pull, Push, Isolation, Compound, etc. Maximum 2 exercices de la même famille par séance.",
        "structured": {
            "variety_required": True,
            "max_same_family": 2,
            "exercise_families_allowed": ["Curl", "Extension", "Press", "Row", "Squat", "Lunge", "Deadlift", "Pull", "Push", "Isolation", "Compound", "Plank", "Crunch", "Raise", "Fly", "Kickback", "Dip", "Pull-up", "Chin-up"]
        },
        "keywords": ["variété", "famille", "exercice", "diversité"],
        "conditions_parsed": {
            "applies_when": "sélection d'exercices pour une séance",
            "exceptions": "si l'utilisateur demande explicitement un seul type d'exercice"
        }
    })
    
    # Règle 4 : Équilibrage par groupe musculaire individuel
    for pair in ANTAGONIST_PAIRS:
        if len(pair) == 2:
            rules.append({
                "id": f"muscle_balance_pair_{pair[0].lower().replace(' ', '_')}_{pair[1].lower().replace(' ', '_')}",
                "source": "generated",
                "type": "muscle_balance_rule",
                "applies_to": "exercise_selection",
                "muscle_pair": pair,
                "rule_text": f"Si l'utilisateur demande '{pair[0]}', inclure aussi '{pair[1]}' (antagoniste). Ratio 1:1.",
                "structured": {
                    "muscle_groups_required": pair,
                    "balance_required": True,
                    "antagonist_pairs": [pair],
                    "ratio": "1:1"
                },
                "keywords": pair + ["antagoniste", "équilibrage"],
                "conditions_parsed": {
                    "applies_when": f"groupe musculaire demandé = '{pair[0]}' ou '{pair[1]}'"
                }
            })
    
    # Sauvegarder
    output_file = OUTPUT_DIR / "muscle_balance_rules.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for rule in rules:
            f.write(json.dumps(rule, ensure_ascii=False) + '\n')
    
    print(f"✅ {len(rules)} règles d'équilibrage créées dans {output_file}")

if __name__ == "__main__":
    create_muscle_balance_rules()

