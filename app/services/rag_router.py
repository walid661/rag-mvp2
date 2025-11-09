# app/services/rag_router.py
from typing import Dict, Any, Optional

def _normalize_niveau(niveau: str) -> str:
    """
    Normalise le niveau : "débutant" → "Débutant", "intermédiaire" → "Intermédiaire", etc.
    """
    if not niveau:
        return ""
    niveau_lower = niveau.lower().strip()
    # Mapping des variations
    niveau_map = {
        "debutant": "Débutant",
        "débutant": "Débutant",
        "beginner": "Débutant",
        "intermediaire": "Intermédiaire",
        "intermédiaire": "Intermédiaire",
        "intermediate": "Intermédiaire",
        "confirme": "Confirmé",
        "confirmé": "Confirmé",
        "avance": "Confirmé",
        "avancé": "Confirmé",
        "advanced": "Confirmé",
        "expert": "Confirmé",
    }
    return niveau_map.get(niveau_lower, niveau.capitalize())

def _normalize_objectif_to_groupe(obj: str) -> Optional[str]:
    """
    Mappe les synonymes d'objectifs utilisateur vers les groupes réels dans les données.
    Retourne le groupe canonique ou None si pas de correspondance claire.
    """
    if not obj:
        return None
    
    obj_lower = obj.lower().strip()
    
    # Mapping intelligent : synonymes → groupes
    # "perte de poids", "minceur", "cardio", "sèche" → "Reconditionnement général"
    if any(kw in obj_lower for kw in ["perte de poids", "perte poids", "minceur", "sèche", "seche", "cardio", "brûlage", "brulage", "métabolique", "metabolique"]):
        return "Reconditionnement général"
    
    # "mobilité", "souplesse", "flexibilité" → groupe avec mobilité (peut être Reconditionnement ou Mobilité)
    if any(kw in obj_lower for kw in ["mobilité", "mobilite", "souplesse", "flexibilité", "flexibilite"]):
        return "Reconditionnement général"  # Par défaut, la plupart des mobilités sont en Reconditionnement
    
    # "force", "renforcement", "tonification", "muscle" → "Tonification & Renforcement"
    if any(kw in obj_lower for kw in ["force", "renforcement", "tonification", "tonicité", "tonicite", "muscle", "musculation"]):
        return "Tonification & Renforcement"
    
    # "endurance", "cardio", "respiration" → "Cardio & Endurance"
    if any(kw in obj_lower for kw in ["endurance", "cardio", "respiration", "souffle", "aérobie", "aerobie"]):
        return "Cardio & Endurance"
    
    # "puissance", "explosivité", "explosivite", "vitesse" → "Puissance & Explosivité"
    if any(kw in obj_lower for kw in ["puissance", "explosivité", "explosivite", "vitesse", "rapidité", "rapidite"]):
        return "Puissance & Explosivité"
    
    # "hypertrophie", "volume", "masse" → "Tonification & Renforcement" (sous-groupe hypertrophie)
    if any(kw in obj_lower for kw in ["hypertrophie", "volume", "masse musculaire"]):
        return "Tonification & Renforcement"
    
    return None

def _normalize_objectif_to_objectif(obj: str) -> Optional[str]:
    """
    Mappe les synonymes d'objectifs utilisateur vers les objectifs réels dans les données.
    Retourne l'objectif canonique ou None si pas de correspondance claire.
    """
    if not obj:
        return None
    
    obj_lower = obj.lower().strip()
    
    # Mapping intelligent : synonymes → objectifs réels
    # "mobilité", "souplesse" → "mobilité active guidée"
    if any(kw in obj_lower for kw in ["mobilité", "mobilite", "souplesse", "flexibilité", "flexibilite"]):
        return "mobilité active guidée"
    
    # "force", "renforcement", "gainage" → "gainage postural statique contrôlé" ou "renforcement contrôlé"
    if any(kw in obj_lower for kw in ["force", "renforcement", "gainage", "tonification"]):
        return "renforcement contrôlé"  # Plus générique
    
    # "endurance", "cardio" → "circuits training continu / fractionné lent" ou "cardio continu modéré"
    if any(kw in obj_lower for kw in ["endurance", "cardio", "respiration", "souffle"]):
        return "circuits training continu / fractionné lent"
    
    # "perte de poids", "minceur" → pas d'objectif spécifique, on filtre par groupe
    if any(kw in obj_lower for kw in ["perte de poids", "perte poids", "minceur", "sèche", "seche"]):
        return None  # On filtre par groupe uniquement
    
    return None

def _normalize_profile_key(key: str, profile: Dict[str, Any]) -> Any:
    """
    Normalise les clés alternatives du profil (niveau_sportif → niveau, objectif_principal → objectif, etc.)
    """
    # Mapping des clés alternatives
    key_map = {
        "niveau_sportif": "niveau",
        "niveau": "niveau",
        "objectif_principal": "objectif",
        "objectif": "objectif",
        "materiel": "equipment",
        "matériel": "equipment",
        "equipment": "equipment",
    }
    
    # Cherche la clé normalisée
    normalized_key = key_map.get(key, key)
    
    # Cherche dans le profil avec les clés alternatives
    for alt_key in [key, normalized_key, key_map.get(key, key)]:
        if alt_key in profile:
            return profile[alt_key]
    
    return None

def build_filters(
    stage: str, 
    profile: Optional[Dict[str, Any]] = None, 
    extra: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Construit des filtres standards pour le retriever selon l'étape du pipeline.
    Router intelligent avec tolérance sémantique et normalisation.
    
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
        
        # Normalisation du niveau (accepte niveau_sportif ou niveau)
        niveau_val = _normalize_profile_key("niveau_sportif", profile) or _normalize_profile_key("niveau", profile)
        if niveau_val:
            f["niveau"] = _normalize_niveau(str(niveau_val))
        
        # Normalisation de l'objectif (accepte objectif_principal ou objectif)
        obj_val = _normalize_profile_key("objectif_principal", profile) or _normalize_profile_key("objectif", profile)
        if obj_val:
            # Mapping intelligent vers groupe
            groupe = _normalize_objectif_to_groupe(str(obj_val))
            if groupe:
                f["groupe"] = groupe
            
            # Mapping intelligent vers objectif (si disponible)
            objectif = _normalize_objectif_to_objectif(str(obj_val))
            if objectif:
                f["objectif"] = objectif
    
    elif stage == "select_micro_patterns":
        f.update({"domain": "program", "type": "micro_ref"})
        
        # Normalisation du niveau
        niveau_val = _normalize_profile_key("niveau_sportif", profile) or _normalize_profile_key("niveau", profile)
        if niveau_val:
            f["niveau"] = _normalize_niveau(str(niveau_val))
        
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
        # Normalisation des clés alternatives (equipment, materiel, matériel)
        equipment_val = _normalize_profile_key("equipment", profile) or _normalize_profile_key("materiel", profile) or _normalize_profile_key("matériel", profile)
        if equipment_val:
            f["equipment"] = str(equipment_val)
        if extra.get("zone"):
            f["zone"] = extra["zone"]
    
    else:
        # Généralisation : si stage inconnu, construire un filtre minimal basé sur extra
        if extra.get("domain"):
            f["domain"] = extra["domain"]
        if extra.get("type"):
            f["type"] = extra["type"]
        # Appliquer aussi les normalisations de profil si présentes
        niveau_val = _normalize_profile_key("niveau_sportif", profile) or _normalize_profile_key("niveau", profile)
        if niveau_val:
            f["niveau"] = _normalize_niveau(str(niveau_val))
        obj_val = _normalize_profile_key("objectif_principal", profile) or _normalize_profile_key("objectif", profile)
        if obj_val:
            groupe = _normalize_objectif_to_groupe(str(obj_val))
            if groupe:
                f["groupe"] = groupe

    # Nettoyage: supprime les clés vides et les valeurs complexes (listes, dicts)
    # Qdrant n'accepte que des valeurs simples (str, int, float, bool)
    cleaned = {}
    for k, v in f.items():
        if v is None or v == "" or v == []:
            continue
        # Ne garder que les types simples compatibles Qdrant
        if isinstance(v, (str, int, float, bool)):
            cleaned[k] = v
        elif isinstance(v, (list, dict)):
            # Ignorer les structures complexes (Qdrant ne les supporte pas directement dans les filtres)
            continue
    
    return cleaned

