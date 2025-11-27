import json
import os
import random

# Paths (Dynamic based on current file location)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(CURRENT_DIR, "..", "data", "processed", "raw_v2", "logic_jsonl_v2")
MESO_PATH = os.path.join(BASE_DIR, "meso_catalog_v2.jsonl")
MICRO_PATH = os.path.join(BASE_DIR, "micro_catalog_v2.jsonl")
PLANNER_PATH = os.path.join(BASE_DIR, "planner_schema.jsonl")

def load_jsonl(path):
    data = []
    if not os.path.exists(path):
        print(f"Error: File not found {path}")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def get_split_strategy(days):
    if days == 3:
        return {
            "split_type": "Haut / Bas / Full Body",
            "sessions": ["Haut du Corps", "Bas du Corps", "Full Body"]
        }
    return {"split_type": "Custom", "sessions": ["Full Body"] * days}

def find_meso(catalog, level, goal):
    keywords = []
    if "perte de poids" in goal.lower():
        keywords = ["métabolique", "metcon", "cardio", "affinement", "perte de poids"]
    
    candidates = []
    for meso in catalog:
        if meso.get("niveau", "").lower() != level.lower():
            continue
            
        text_dump = json.dumps(meso, ensure_ascii=False).lower()
        if any(k in text_dump for k in keywords):
            candidates.append(meso)
    
    if not candidates:
        # Fallback: just level
        candidates = [m for m in catalog if m.get("niveau", "").lower() == level.lower()]
        
    return candidates[0] if candidates else None

def find_micro(catalog, theme, allowed_equipment):
    candidates = []
    
    target_focus = []
    text_keywords = []
    
    if "Haut" in theme:
        target_focus = ["hypertrophy", "strength", "power"]
        text_keywords = ["haut", "upper", "push", "pull", "bras", "épaules", "pectoraux", "dos"]
    elif "Bas" in theme:
        target_focus = ["hypertrophy", "strength", "power"]
        text_keywords = ["bas", "lower", "jambes", "squat", "fentes", "legs"]
    elif "Full Body" in theme:
        target_focus = ["general", "endurance", "metcon", "hypertrophy", "strength"]
        text_keywords = ["full body", "global", "total"]
    
    for micro in catalog:
        structured = micro.get("structured", {})
        micro_eq = structured.get("equipment_detected", [])
        
        normalized_micro_eq = []
        for eq in micro_eq:
            if eq in ["bodyweight", "autochargé"]: normalized_micro_eq.append("bodyweight")
            elif eq in ["resistance_band", "élastique", "bande"]: normalized_micro_eq.append("resistance_band")
            else: normalized_micro_eq.append(eq)
            
        allowed_map = []
        for eq in allowed_equipment:
            if eq in ["bodyweight", "autochargé"]: allowed_map.append("bodyweight")
            elif eq in ["resistance_band", "elastique"]: allowed_map.append("resistance_band")
            else: allowed_map.append(eq)
            
        if not set(normalized_micro_eq).issubset(set(allowed_map)):
            continue
            
        if target_focus and structured.get("focus_detected") not in target_focus:
            continue
            
        text_dump = json.dumps(micro, ensure_ascii=False).lower()
        if text_keywords:
            if not any(k in text_dump for k in text_keywords):
                continue
        
        candidates.append(micro)
        
    if not candidates:
        # Relax text filter
        for micro in catalog:
            structured = micro.get("structured", {})
            micro_eq = structured.get("equipment_detected", [])
            normalized_micro_eq = []
            for eq in micro_eq:
                if eq in ["bodyweight", "autochargé"]: normalized_micro_eq.append("bodyweight")
                elif eq in ["resistance_band", "élastique", "bande"]: normalized_micro_eq.append("resistance_band")
                else: normalized_micro_eq.append(eq)
            
            allowed_map = []
            for eq in allowed_equipment:
                if eq in ["bodyweight", "autochargé"]: allowed_map.append("bodyweight")
                elif eq in ["resistance_band", "elastique"]: allowed_map.append("resistance_band")
                else: allowed_map.append(eq)

            if not set(normalized_micro_eq).issubset(set(allowed_map)):
                continue
                
            if target_focus and structured.get("focus_detected") not in target_focus:
                continue
            
            candidates.append(micro)
            
    return candidates[0] if candidates else None

def generate_weekly_plan(profile):
    """
    Generates a weekly plan based on the user profile.
    profile: dict with keys 'level', 'goal', 'schedule', 'equipment'
    """
    meso_catalog = load_jsonl(MESO_PATH)
    micro_catalog = load_jsonl(MICRO_PATH)
    
    # Map frontend levels (English) to Catalog levels (French)
    level_map = {
        "beginner": "Débutant",
        "intermediate": "Intermédiaire",
        "advanced": "Confirmé"
    }
    
    user_level = profile.get("level", "intermediate").lower()
    target_level = level_map.get(user_level, "Intermédiaire")
    
    split = get_split_strategy(profile.get("schedule", 3))
    meso = find_meso(meso_catalog, target_level, profile.get("goal", "Renforcement"))
    
    if not meso:
        return {"error": "No suitable Meso-cycle found."}

    meso_constraints = meso.get("constraints", {})
    
    sessions = []
    days = [1, 3, 5] 
    
    for i, theme in enumerate(split["sessions"]):
        micro = find_micro(micro_catalog, theme, profile.get("equipment", []))
        
        session = {
            "day": days[i] if i < len(days) else i+1,
            "theme": theme,
            "micro_id_ref": micro["micro_id"] if micro else "N/A",
            "logic_override": {
                "intensity": meso_constraints.get("intensity_pct"),
                "rest_time": meso_constraints.get("rest_sec")
            }
        }
        sessions.append(session)
        
    return {
        "weekly_plan_id": f"plan_{random.randint(1000, 9999)}",
        "user_summary": f"{profile.get('level')} / {profile.get('goal')} / {profile.get('schedule')}x",
        "strategy": {
            "split_type": split["split_type"],
            "meso_focus": meso.get("objectif", "General"),
            "meso_id_ref": meso["meso_id"]
        },
        "sessions": sessions
    }

if __name__ == "__main__":
    # Test run
    test_profile = {
        "level": "Intermédiaire",
        "goal": "Perte de poids",
        "schedule": 3,
        "equipment": ["bodyweight", "resistance_band"]
    }
    print(json.dumps(generate_weekly_plan(test_profile), indent=2, ensure_ascii=False))
