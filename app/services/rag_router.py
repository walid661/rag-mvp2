# app/services/rag_router.py
from typing import Dict, Any, Optional

def build_filters(
    stage: str, 
    profile: Optional[Dict[str, Any]] = None, 
    extra: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Construit des filtres standards pour le retriever selon l'étape du pipeline.
    
    Args:
        stage: Étape du pipeline (ex: "select_meso", "select_micro_patterns", etc.)
        profile: Profil utilisateur (niveau_sportif, objectif_principal, equipment, etc.)
        extra: Paramètres supplémentaires (methode, role_micro, rule_type, etc.)
    
    Returns:
        Dictionnaire de filtres compatible avec HybridRetriever.retrieve()
    """
    profile = profile or {}
    extra = extra or {}
    f: Dict[str, Any] = {}

    if stage == "select_meso":
        f.update({"domain": "program", "type": "meso_ref"})
        if "niveau_sportif" in profile:
            # Normalisation : Débutant/Intermédiaire/Confirmé
            niveau = str(profile["niveau_sportif"]).capitalize()
            f["niveau"] = niveau
        if "objectif_principal" in profile:
            f["objectif"] = profile["objectif_principal"]
    
    elif stage == "select_micro_patterns":
        f.update({"domain": "program", "type": "micro_ref"})
        if "niveau_sportif" in profile:
            niveau = str(profile["niveau_sportif"]).capitalize()
            f["niveau"] = niveau
        if extra.get("methode"):
            f["methode"] = extra["methode"]
    
    elif stage == "micro_generation_rules":
        f.update({"domain": "logic"})
        if extra.get("role_micro"):
            f["role_micro"] = extra["role_micro"]
        # Le caller peut appeler plusieurs fois avec type différents
        if extra.get("rule_type"):
            f["type"] = extra["rule_type"]  # ex: "micro_format_spec" ou "progression_rule"
    
    elif stage == "planner_rules":
        f.update({"domain": "logic", "type": "planner_rule"})
        if extra.get("driver"):
            # "niveau_utilisateur" | "nb_seances_semaine" | "macro_cycle" | "micro_cycle"
            # Note: Qdrant supporte les clés imbriquées via "conditions.driver"
            # Mais on ajoute aussi un fallback plat pour le filtrage BM25
            f["conditions.driver"] = extra["driver"]
            f["conditions_driver"] = extra["driver"]  # fallback si nested non indexé
    
    elif stage == "planner_schema":
        f.update({"domain": "logic", "type": "planner_week_schema"})
    
    elif stage == "session_schema":
        f.update({"domain": "logic", "type": "session_schema"})
    
    elif stage == "weekly_split":
        f.update({"domain": "logic", "type": "weekly_split_rule"})
    
    elif stage == "exercise_rules":
        f.update({"domain": "logic", "type": "exercise_choice_rule"})
    
    elif stage == "equipment_rules":
        f.update({"domain": "logic", "type": "equipment_rule"})
    
    elif stage == "objective_priority":
        f.update({"domain": "logic", "type": "objective_priority"})
        if extra.get("group") is not None:
            f["group"] = extra["group"]
    
    elif stage == "pick_exercises":
        f.update({"domain": "exercise", "type": "exercise"})
        if "equipment" in profile:
            f["equipment"] = profile["equipment"]
        if extra.get("zone"):
            f["zone"] = extra["zone"]
    
    else:
        # Fallback : ne filtre que par domain si fourni
        if extra.get("domain"):
            f["domain"] = extra["domain"]

    # Nettoyage: supprime les clés vides
    return {k: v for k, v in f.items() if v not in (None, "", [])}

