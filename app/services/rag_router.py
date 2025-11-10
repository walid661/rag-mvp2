# app/services/rag_router.py
from typing import Dict, Any, Optional
import os
import sys
from dotenv import load_dotenv

# Ajouter le chemin racine pour importer intent.py
sys.path.insert(0, os.path.abspath('.'))

try:
    from intent import classify_query
except ImportError:
    print("[RAG_ROUTER] WARNING: intent module not found, falling back to keyword-based mapping.")
    classify_query = None

load_dotenv()

THRESH_PRIMARY = float(os.getenv("INTENT_THRESHOLD_PRIMARY", "0.45"))
THRESH_SECONDARY = float(os.getenv("INTENT_THRESHOLD_SECONDARY", "0.35"))
MIN_SHOULD = int(os.getenv("INTENT_MIN_SHOULD", "1"))

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
        # Filtres souples avec must + should + min_should
        f = {
            "must": [
                {"key": "domain", "match": {"value": "program"}},
                {"key": "type", "match": {"value": "meso_ref"}}
            ],
            "should": [],
            "must_not": []
        }
        
        # Classification sémantique de la requête
        q = (extra or {}).get("query", "")
        ranked = {}
        if q and classify_query:
            ranked = classify_query(q)
            print(f"[MAPPING] Intentions détectées: {ranked}")
        
        # objectif (plus discriminant) - THRESH_PRIMARY
        for label, score in ranked.get("objectif", []):
            if score >= THRESH_PRIMARY:
                f["should"].append({"key": "objectif", "match": {"value": label}})
                print(f"[MAPPING] objectif={label} (score={score:.3f})")
        
        # zone et groupe (complémentaires) - THRESH_SECONDARY
        for label, score in ranked.get("zone", []):
            if score >= THRESH_SECONDARY:
                f["should"].append({"key": "zones", "match": {"value": label}})
                print(f"[MAPPING] zone={label} (score={score:.3f})")
        
        for label, score in ranked.get("groupe", []):
            if score >= THRESH_SECONDARY:
                f["should"].append({"key": "groupe", "match": {"value": label}})
                print(f"[MAPPING] groupe={label} (score={score:.3f})")
        
        # profil utilisateur (niveau & matériel)
        if profile:
            niveau_val = _normalize_profile_key("niveau_sportif", profile) or _normalize_profile_key("niveau", profile)
            if niveau_val:
                niveau_norm = _normalize_niveau(str(niveau_val))
                f["should"].append({"key": "niveau", "match": {"value": niveau_norm}})
            
            # Matériel depuis le profil
            materiel_val = profile.get("materiel_disponible") or profile.get("materiel") or profile.get("equipment")
            if materiel_val:
                if isinstance(materiel_val, list):
                    for m in materiel_val:
                        f["should"].append({"key": "materiel", "match": {"value": str(m)}})
                else:
                    f["should"].append({"key": "materiel", "match": {"value": str(materiel_val)}})
        
        # min_should dynamique
        f["min_should"] = max(MIN_SHOULD, 1)
        
        # Si pas de should, retourner un format simple pour compatibilité
        if not f["should"]:
            # Fallback : format simple pour compatibilité avec retriever actuel
            simple_f = {"domain": "program", "type": "meso_ref"}
            niveau_val = _normalize_profile_key("niveau_sportif", profile) or _normalize_profile_key("niveau", profile)
            if niveau_val:
                simple_f["niveau"] = _normalize_niveau(str(niveau_val))
            return simple_f
        
        return f
    
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
        # Support multi-valeurs : equipment peut être une liste
        equipment_val = _normalize_profile_key("equipment", profile) or _normalize_profile_key("materiel", profile) or _normalize_profile_key("matériel", profile)
        if equipment_val:
            # Si c'est une liste, la garder telle quelle, sinon convertir en liste
            if isinstance(equipment_val, list):
                f["equipment"] = equipment_val
            else:
                f["equipment"] = [str(equipment_val)]
        # Support multi-valeurs pour les zones
        zones_val = profile.get("zones_ciblees") or extra.get("zones") or extra.get("zone")
        if zones_val:
            if isinstance(zones_val, list):
                f["zone"] = zones_val  # Support multi-valeurs
            else:
                f["zone"] = [str(zones_val)]
    
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

    # Nettoyage: supprime les clés vides mais GARDE les listes pour support multi-valeurs
    # Qdrant supporte MatchAny pour les listes via FieldCondition(key=key, match=MatchAny(any=val))
    cleaned = {}
    for k, v in f.items():
        if v is None or v == "" or (isinstance(v, list) and len(v) == 0):
            continue
        # Garder les types simples ET les listes (pour support multi-valeurs)
        if isinstance(v, (str, int, float, bool)):
            cleaned[k] = v
        elif isinstance(v, list):
            # Garder les listes pour support multi-valeurs (Qdrant les supporte via MatchAny)
            cleaned[k] = v
        elif isinstance(v, dict):
            # Ignorer les dicts (Qdrant ne les supporte pas directement dans les filtres)
            continue
    
    return cleaned

