import json
import os
import random

# Paths
BASE_DIR = r"c:\Dossier Walid\rag-mvp2\data\processed\raw_v2\logic_jsonl_v2"
MESO_PATH = os.path.join(BASE_DIR, "meso_catalog_v2.jsonl")
MICRO_PATH = os.path.join(BASE_DIR, "micro_catalog_v2.jsonl")
PLANNER_PATH = os.path.join(BASE_DIR, "planner_schema.jsonl")

# User Profile
USER_PROFILE = {
    "level": "Intermédiaire",
    "goal": "Perte de poids",
    "schedule": 3,
    "equipment": ["bodyweight", "resistance_band", "elastique", "autochargé"], # Normalized
    "psychology": "Challengeant"
}

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
    # Simplified logic based on planner_schema.jsonl and user request
    if days == 3:
        return {
            "split_type": "Haut / Bas / Full Body",
            "sessions": ["Haut du Corps", "Bas du Corps", "Full Body"]
        }
    return {"split_type": "Custom", "sessions": ["Full Body"] * days}

def find_meso(catalog, level, goal):
    # Map goal to keywords
    keywords = []
    if "perte de poids" in goal.lower():
        keywords = ["métabolique", "metcon", "cardio", "affinement", "perte de poids"]
    
    candidates = []
    for meso in catalog:
        # Check Level
        if meso.get("niveau", "").lower() != level.lower():
            continue
            
        # Check Goal Match (in Objectif, Groupe, Nom, or Text)
        text_dump = json.dumps(meso, ensure_ascii=False).lower()
        if any(k in text_dump for k in keywords):
            candidates.append(meso)
    
    if not candidates:
        print(f"Warning: No exact Meso match found for {level} / {goal}. Returning random Intermédiaire.")
        # Fallback: just level
        candidates = [m for m in catalog if m.get("niveau", "").lower() == level.lower()]
        
    return candidates[0] if candidates else None

def find_micro(catalog, theme, allowed_equipment):
    candidates = []
    
    # Define filters based on theme
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
        
        # 1. Equipment Filter
        # Micro equipment must be a SUBSET of allowed equipment
        # If micro requires nothing (empty), it's OK.
        # If micro requires 'dumbbell', and user doesn't have it, SKIP.
        micro_eq = structured.get("equipment_detected", [])
        # Normalize micro_eq
        normalized_micro_eq = []
        for eq in micro_eq:
            if eq in ["bodyweight", "autochargé"]: normalized_micro_eq.append("bodyweight")
            elif eq in ["resistance_band", "élastique", "bande"]: normalized_micro_eq.append("resistance_band")
            else: normalized_micro_eq.append(eq) # e.g. dumbbell
            
        # Check if all required are in allowed
        # Allowed map
        allowed_map = []
        for eq in allowed_equipment:
            if eq in ["bodyweight", "autochargé"]: allowed_map.append("bodyweight")
            elif eq in ["resistance_band", "elastique"]: allowed_map.append("resistance_band")
            
        if not set(normalized_micro_eq).issubset(set(allowed_map)):
            continue
            
        # 2. Focus Filter
        if target_focus and structured.get("focus_detected") not in target_focus:
            continue
            
        # 3. Text Keyword Filter (Soft filter? Or Hard?)
        # Let's try hard filter first, if no results, relax.
        text_dump = json.dumps(micro, ensure_ascii=False).lower()
        if text_keywords:
            if not any(k in text_dump for k in text_keywords):
                continue
        
        candidates.append(micro)
        
    if not candidates:
        # Relax text filter
        print(f"Warning: No strict match for {theme}. Relaxing text filter.")
        for micro in catalog:
            structured = micro.get("structured", {})
            micro_eq = structured.get("equipment_detected", [])
            # Normalize and check equipment again (same logic)
            normalized_micro_eq = []
            for eq in micro_eq:
                if eq in ["bodyweight", "autochargé"]: normalized_micro_eq.append("bodyweight")
                elif eq in ["resistance_band", "élastique", "bande"]: normalized_micro_eq.append("resistance_band")
                else: normalized_micro_eq.append(eq)
            
            allowed_map = []
            for eq in allowed_equipment:
                if eq in ["bodyweight", "autochargé"]: allowed_map.append("bodyweight")
                elif eq in ["resistance_band", "elastique"]: allowed_map.append("resistance_band")

            if not set(normalized_micro_eq).issubset(set(allowed_map)):
                continue
                
            if target_focus and structured.get("focus_detected") not in target_focus:
                continue
            
            candidates.append(micro)
            
    return candidates[0] if candidates else None

def main():
    # Load Data
    meso_catalog = load_jsonl(MESO_PATH)
    micro_catalog = load_jsonl(MICRO_PATH)
    
    # Step 1: Split
    split = get_split_strategy(USER_PROFILE["schedule"])
    
    # Step 2: Meso
    meso = find_meso(meso_catalog, USER_PROFILE["level"], USER_PROFILE["goal"])
    if not meso:
        print("Critical Error: No Meso found.")
        return

    meso_constraints = meso.get("constraints", {})
    
    # Step 3: Assemble Sessions
    sessions = []
    days = [1, 3, 5] # Example days
    
    for i, theme in enumerate(split["sessions"]):
        micro = find_micro(micro_catalog, theme, USER_PROFILE["equipment"])
        
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
        
    # Step 4: Generate JSON
    output = {
        "weekly_plan_id": "plan_001",
        "user_summary": f"{USER_PROFILE['level']} / {USER_PROFILE['goal']} / {USER_PROFILE['schedule']}x",
        "strategy": {
            "split_type": split["split_type"],
            "meso_focus": meso.get("objectif", "General"),
            "meso_id_ref": meso["meso_id"]
        },
        "sessions": sessions
    }
    
    print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
