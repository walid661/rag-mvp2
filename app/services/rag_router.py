# app/services/rag_router.py
from typing import Dict, Any, Optional, List, Set
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

# ============================================================================
# MAPPING EXHAUSTIF : Intentions (taxonomy.json) → Valeurs réelles (documents)
# ============================================================================

# Mapping des objectifs taxonomy → objectifs réels dans les documents
TAXONOMY_OBJECTIF_TO_DOC_OBJECTIF: Dict[str, List[str]] = {
    "Hypertrophie fonctionnelle": [
        "renforcement contrôlé",
        "hypertrophie ciblée",
        "2 groupes / séance",
        "split alterné haut/bas",
        "force contrôlée avec charge modérée",
        "routine structurée mixte",
    ],
    "Mobilité active guidée": [
        "mobilité active guidée",
        "mobilité active évoluée",
        "mobilité active sous charge légère",
        "mobilité fonctionnelle sous charge",
    ],
    "Conditionnement métabolique": [
        "TABATA modifié",
        "circuits training continu / fractionné lent",
        "cardio continu à intensité basse à moyenne",
        "AMRAP + HIIT combiné",
        "brûlage profond",
    ],
}

# Mapping des objectifs taxonomy → groupes fonctionnels dans les documents
TAXONOMY_OBJECTIF_TO_DOC_GROUPE: Dict[str, List[str]] = {
    "Hypertrophie fonctionnelle": [
        "Tonification & Renforcement",
        "Hypertrophie",
    ],
    "Mobilité active guidée": [
        "Mobilité & Souplesse",
        "Reconditionnement général",  # Contient aussi de la mobilité
    ],
    "Conditionnement métabolique": [
        "Métabolique & Dépense",
        "Cardio & Endurance",
        "Reconditionnement général",  # Contient aussi du cardio
    ],
}

# Mapping des zones taxonomy → groupes fonctionnels dans les documents
TAXONOMY_ZONE_TO_DOC_GROUPE: Dict[str, List[str]] = {
    "Haut du corps": [
        "Tonification & Renforcement",  # Contient exercices haut du corps
        "Hypertrophie",  # Contient exercices haut du corps
        "Reconditionnement général",  # Full body par défaut
    ],
    "Bas du corps": [
        "Tonification & Renforcement",  # Contient exercices bas du corps
        "Hypertrophie",  # Contient exercices bas du corps
        "Reconditionnement général",  # Full body par défaut
    ],
    "Chaîne postérieure": [
        "Tonification & Renforcement",  # Dos, ischios, fessiers
        "Hypertrophie",  # Dos, ischios, fessiers
        "Fonctionnel & Prévention",  # Prévention dos
    ],
    "Full body": [
        "Reconditionnement général",  # Full body par défaut
        "Tonification & Renforcement",  # Full body possible
        "Métabolique & Dépense",  # Full body cardio
        "Cardio & Endurance",  # Full body cardio
    ],
}

# Mapping des groupes musculaires taxonomy → groupes fonctionnels dans les documents
TAXONOMY_GROUPE_TO_DOC_GROUPE: Dict[str, List[str]] = {
    # Haut du corps
    "Biceps": [
        "Tonification & Renforcement",  # Contient exercices biceps
        "Hypertrophie",  # Contient exercices biceps
    ],
    "Triceps": [
        "Tonification & Renforcement",  # Contient exercices triceps
        "Hypertrophie",  # Contient exercices triceps
    ],
    "Pectoraux": [
        "Tonification & Renforcement",  # Contient exercices pectoraux
        "Hypertrophie",  # Contient exercices pectoraux
    ],
    "Épaules": [
        "Tonification & Renforcement",  # Contient exercices épaules
        "Hypertrophie",  # Contient exercices épaules
    ],
    "Dos": [
        "Tonification & Renforcement",  # Contient exercices dos
        "Hypertrophie",  # Contient exercices dos
        "Fonctionnel & Prévention",  # Prévention dos
    ],
    # Bas du corps
    "Quadriceps": [
        "Tonification & Renforcement",  # Contient exercices quadriceps
        "Hypertrophie",  # Contient exercices quadriceps
    ],
    "Ischio-jambiers": [
        "Tonification & Renforcement",  # Contient exercices ischio-jambiers
        "Hypertrophie",  # Contient exercices ischio-jambiers
    ],
    "Fessiers": [
        "Tonification & Renforcement",  # Contient exercices fessiers
        "Hypertrophie",  # Contient exercices fessiers
    ],
    "Mollets": [
        "Tonification & Renforcement",  # Contient exercices mollets
        "Hypertrophie",  # Contient exercices mollets
    ],
}

# Mapping des synonymes utilisateur → groupes fonctionnels dans les documents
USER_KEYWORDS_TO_DOC_GROUPE: Dict[str, List[str]] = {
    # Perte de poids / Cardio
    "perte de poids": ["Métabolique & Dépense", "Cardio & Endurance", "Reconditionnement général"],
    "perte poids": ["Métabolique & Dépense", "Cardio & Endurance", "Reconditionnement général"],
    "minceur": ["Métabolique & Dépense", "Cardio & Endurance"],
    "sèche": ["Métabolique & Dépense", "Cardio & Endurance"],
    "seche": ["Métabolique & Dépense", "Cardio & Endurance"],
    "cardio": ["Cardio & Endurance", "Métabolique & Dépense", "Reconditionnement général"],
    "brûlage": ["Métabolique & Dépense"],
    "brulage": ["Métabolique & Dépense"],
    "métabolique": ["Métabolique & Dépense"],
    "metabolique": ["Métabolique & Dépense"],
    
    # Mobilité / Souplesse
    "mobilité": ["Mobilité & Souplesse", "Reconditionnement général"],
    "mobilite": ["Mobilité & Souplesse", "Reconditionnement général"],
    "souplesse": ["Mobilité & Souplesse", "Reconditionnement général"],
    "flexibilité": ["Mobilité & Souplesse", "Reconditionnement général"],
    "flexibilite": ["Mobilité & Souplesse", "Reconditionnement général"],
    
    # Force / Renforcement / Tonification
    "force": ["Tonification & Renforcement", "Hypertrophie"],
    "renforcement": ["Tonification & Renforcement"],
    "tonification": ["Tonification & Renforcement"],
    "tonicité": ["Tonification & Renforcement"],
    "tonicite": ["Tonification & Renforcement"],
    "muscle": ["Tonification & Renforcement", "Hypertrophie"],
    "musculation": ["Tonification & Renforcement", "Hypertrophie"],
    
    # Hypertrophie / Volume
    "hypertrophie": ["Hypertrophie", "Tonification & Renforcement"],
    "volume": ["Hypertrophie", "Tonification & Renforcement"],
    "masse musculaire": ["Hypertrophie", "Tonification & Renforcement"],
    "prise de muscle": ["Hypertrophie", "Tonification & Renforcement"],
    
    # Endurance
    "endurance": ["Cardio & Endurance", "Reconditionnement général"],
    "respiration": ["Cardio & Endurance", "Récupération & Respiration"],
    "souffle": ["Cardio & Endurance", "Récupération & Respiration"],
    "aérobie": ["Cardio & Endurance", "Reconditionnement général"],
    "aerobie": ["Cardio & Endurance", "Reconditionnement général"],
    
    # Puissance / Explosivité
    "puissance": ["Puissance & Explosivité"],
    "explosivité": ["Puissance & Explosivité"],
    "explosivite": ["Puissance & Explosivité"],
    "vitesse": ["Puissance & Explosivité"],
    "rapidité": ["Puissance & Explosivité"],
    "rapidite": ["Puissance & Explosivité"],
    
    # Bien-être
    "bien-être": ["Bien-être & Vitalité"],
    "bien-etre": ["Bien-être & Vitalité"],
    "vitalité": ["Bien-être & Vitalité"],
    "vitalite": ["Bien-être & Vitalité"],
    "stress": ["Bien-être & Vitalité", "Récupération & Respiration"],
    
    # Récupération
    "récupération": ["Récupération & Respiration"],
    "recuperation": ["Récupération & Respiration"],
    "repos": ["Récupération & Respiration"],
    
    # Préparation
    "préparation": ["Préparation spécifique"],
    "preparation": ["Préparation spécifique"],
    
    # Fonctionnel
    "fonctionnel": ["Fonctionnel & Prévention"],
    "prévention": ["Fonctionnel & Prévention"],
    "prevention": ["Fonctionnel & Prévention"],
    
    # Maintenance
    "maintenance": ["Maintenance & Reset"],
    "reset": ["Maintenance & Reset"],
}

# Mapping des synonymes utilisateur → objectifs réels dans les documents
USER_KEYWORDS_TO_DOC_OBJECTIF: Dict[str, List[str]] = {
    # Mobilité
    "mobilité": ["mobilité active guidée", "mobilité active évoluée", "mobilité active sous charge légère"],
    "mobilite": ["mobilité active guidée", "mobilité active évoluée", "mobilité active sous charge légère"],
    "souplesse": ["mobilité active guidée", "mobilité active évoluée"],
    "flexibilité": ["mobilité active guidée", "mobilité active évoluée"],
    "flexibilite": ["mobilité active guidée", "mobilité active évoluée"],
    
    # Renforcement / Force
    "force": ["renforcement contrôlé", "force contrôlée avec charge modérée"],
    "renforcement": ["renforcement contrôlé"],
    "gainage": ["gainage postural statique contrôlé", "stabilité fonctionnelle simple"],
    "tonification": ["renforcement contrôlé"],
    
    # Cardio / Endurance
    "endurance": ["circuits training continu / fractionné lent", "cardio continu à intensité basse à moyenne"],
    "cardio": ["circuits training continu / fractionné lent", "cardio continu à intensité basse à moyenne", "TABATA modifié"],
    "respiration": ["circuits training continu / fractionné lent"],
    "souffle": ["circuits training continu / fractionné lent"],
    
    # Métabolique / Perte de poids
    "perte de poids": ["TABATA modifié", "AMRAP + HIIT combiné", "brûlage profond"],
    "perte poids": ["TABATA modifié", "AMRAP + HIIT combiné", "brûlage profond"],
    "minceur": ["TABATA modifié", "AMRAP + HIIT combiné"],
    "sèche": ["TABATA modifié", "AMRAP + HIIT combiné"],
    "seche": ["TABATA modifié", "AMRAP + HIIT combiné"],
    "brûlage": ["AMRAP + HIIT combiné", "brûlage profond"],
    "brulage": ["AMRAP + HIIT combiné", "brûlage profond"],
    "métabolique": ["TABATA modifié", "AMRAP + HIIT combiné"],
    "metabolique": ["TABATA modifié", "AMRAP + HIIT combiné"],
    
    # Hypertrophie
    "hypertrophie": ["hypertrophie ciblée", "2 groupes / séance"],
    "volume": ["hypertrophie ciblée", "2 groupes / séance"],
    "masse musculaire": ["hypertrophie ciblée", "2 groupes / séance"],
    "prise de muscle": ["hypertrophie ciblée", "2 groupes / séance"],
}

# Tous les groupes fonctionnels valides dans les documents
VALID_DOC_GROUPES: Set[str] = {
    "Reconditionnement général",
    "Tonification & Renforcement",
    "Hypertrophie",
    "Mobilité & Souplesse",
    "Métabolique & Dépense",
    "Cardio & Endurance",
    "Puissance & Explosivité",
    "Bien-être & Vitalité",
    "Récupération & Respiration",
    "Préparation spécifique",
    "Fonctionnel & Prévention",
    "Maintenance & Reset",
}

# ============================================================================
# FONCTIONS DE NORMALISATION AMÉLIORÉES
# ============================================================================

def _normalize_niveau(niveau: str) -> str:
    """
    Normalise le niveau : "débutant" → "Débutant", "intermédiaire" → "Intermédiaire", etc.
    """
    if not niveau:
        return ""
    niveau_lower = niveau.lower().strip()
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

def _map_intent_objectif_to_doc_values(intent_objectif: str) -> Dict[str, List[str]]:
    """
    Mappe un objectif de taxonomy vers les valeurs réelles dans les documents.
    Retourne un dict avec 'objectif' et 'groupe' contenant les listes de valeurs possibles.
    """
    result = {"objectif": [], "groupe": []}
    
    # Mapping direct objectif → objectif
    if intent_objectif in TAXONOMY_OBJECTIF_TO_DOC_OBJECTIF:
        result["objectif"] = TAXONOMY_OBJECTIF_TO_DOC_OBJECTIF[intent_objectif]
    
    # Mapping objectif → groupe
    if intent_objectif in TAXONOMY_OBJECTIF_TO_DOC_GROUPE:
        result["groupe"] = TAXONOMY_OBJECTIF_TO_DOC_GROUPE[intent_objectif]
    
    return result

def _map_intent_zone_to_doc_groupe(intent_zone: str) -> List[str]:
    """
    Mappe une zone de taxonomy vers les groupes fonctionnels dans les documents.
    """
    return TAXONOMY_ZONE_TO_DOC_GROUPE.get(intent_zone, [])

def _map_intent_groupe_to_doc_groupe(intent_groupe: str) -> List[str]:
    """
    Mappe un groupe musculaire de taxonomy vers les groupes fonctionnels dans les documents.
    """
    return TAXONOMY_GROUPE_TO_DOC_GROUPE.get(intent_groupe, [])

def _map_user_keywords_to_doc_groupe(query: str) -> List[str]:
    """
    Mappe les mots-clés de la requête utilisateur vers les groupes fonctionnels dans les documents.
    """
    query_lower = query.lower()
    matched_groupes: Set[str] = set()
    
    for keyword, groupes in USER_KEYWORDS_TO_DOC_GROUPE.items():
        if keyword in query_lower:
            matched_groupes.update(groupes)
    
    return list(matched_groupes)

def _map_user_keywords_to_doc_objectif(query: str) -> List[str]:
    """
    Mappe les mots-clés de la requête utilisateur vers les objectifs réels dans les documents.
    """
    query_lower = query.lower()
    matched_objectifs: Set[str] = set()
    
    for keyword, objectifs in USER_KEYWORDS_TO_DOC_OBJECTIF.items():
        if keyword in query_lower:
            matched_objectifs.update(objectifs)
    
    return list(matched_objectifs)

def _normalize_objectif_to_groupe(obj: str) -> Optional[str]:
    """
    Mappe les synonymes d'objectifs utilisateur vers les groupes réels dans les données.
    Retourne le groupe canonique ou None si pas de correspondance claire.
    """
    if not obj:
        return None
    
    # Utiliser le mapping exhaustif
    groupes = _map_user_keywords_to_doc_groupe(obj)
    if groupes:
        return groupes[0]  # Retourner le premier groupe trouvé
    
    return None

def _normalize_objectif_to_objectif(obj: str) -> Optional[str]:
    """
    Mappe les synonymes d'objectifs utilisateur vers les objectifs réels dans les données.
    Retourne l'objectif canonique ou None si pas de correspondance claire.
    """
    if not obj:
        return None
    
    # Utiliser le mapping exhaustif
    objectifs = _map_user_keywords_to_doc_objectif(obj)
    if objectifs:
        return objectifs[0]  # Retourner le premier objectif trouvé
    
    return None

def _normalize_profile_key(key: str, profile: Dict[str, Any]) -> Any:
    """
    Normalise les clés alternatives du profil (niveau_sportif → niveau, objectif_principal → objectif, etc.)
    """
    key_map = {
        "niveau_sportif": "niveau",
        "niveau": "niveau",
        "objectif_principal": "objectif",
        "objectif": "objectif",
        "materiel": "equipment",
        "matériel": "equipment",
        "equipment": "equipment",
    }
    
    normalized_key = key_map.get(key, key)
    
    for alt_key in [key, normalized_key, key_map.get(key, key)]:
        if alt_key in profile:
            return profile[alt_key]
    
    return None

def _normalize_materiel(materiel: Any) -> List[str]:
    """
    Normalise le matériel utilisateur vers les valeurs attendues dans les documents.
    """
    if not materiel:
        return []
    
    if isinstance(materiel, list):
        materiel_list = materiel
    else:
        materiel_list = [str(materiel)]
    
    normalized = []
    for m in materiel_list:
        m_lower = str(m).lower().strip()
        
        # Mapping exhaustif
        if any(kw in m_lower for kw in ["barre", "rack", "machine", "machines", "full gym", "full_gym"]):
            normalized.append("full_gym")
        elif any(kw in m_lower for kw in ["haltère", "haltères", "dumbbell", "dumbbells"]):
            normalized.append("dumbbell")
        elif any(kw in m_lower for kw in ["kettlebell", "kb"]):
            normalized.append("kettlebell")
        elif any(kw in m_lower for kw in ["élastique", "élastiques", "band", "bands", "bande", "bandes"]):
            normalized.append("bands")
        elif any(kw in m_lower for kw in ["aucun", "poids du corps", "bodyweight", "sans matériel", "sans materiel"]):
            normalized.append("none")
        elif any(kw in m_lower for kw in ["tapis", "mat", "matelas"]):
            normalized.append("mat")
        else:
            # Par défaut, garder la valeur originale
            normalized.append(m_lower)
    
    return list(set(normalized))  # Dédupliquer

# ============================================================================
# FONCTION PRINCIPALE : build_filters
# ============================================================================

def build_filters(
    stage: str, 
    profile: Optional[Dict[str, Any]] = None, 
    extra: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Construit des filtres standards pour le retriever selon l'étape du pipeline.
    Router intelligent avec tolérance sémantique et normalisation renforcée.
    
    Args:
        stage: Étape du pipeline (ex: "select_meso", "select_micro_patterns", etc.)
        profile: Profil utilisateur (niveau_sportif, objectif_principal, equipment, etc.)
        extra: Paramètres supplémentaires (query, methode, role_micro, rule_type, etc.)
    
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
            from intent import reweight_groups_by_zone
            ranked = classify_query(q)
            ranked = reweight_groups_by_zone(ranked, query=q)
            print(f"[MAPPING] Intentions détectées: {ranked}")
        
        # Mapping des intentions vers les valeurs réelles dans les documents
        matched_objectifs: Set[str] = set()
        matched_groupes: Set[str] = set()
        
        # 1. Mapper les objectifs de taxonomy vers les valeurs réelles
        for label, score in ranked.get("objectif", []):
            if score >= THRESH_PRIMARY:
                mapped = _map_intent_objectif_to_doc_values(label)
                matched_objectifs.update(mapped.get("objectif", []))
                matched_groupes.update(mapped.get("groupe", []))
                print(f"[MAPPING] objectif taxonomy '{label}' → objectifs docs: {mapped.get('objectif', [])}, groupes: {mapped.get('groupe', [])}")
        
        # 2. Mapper les zones de taxonomy vers les groupes fonctionnels
        for label, score in ranked.get("zone", []):
            if score >= THRESH_SECONDARY:
                groupes = _map_intent_zone_to_doc_groupe(label)
                matched_groupes.update(groupes)
                print(f"[MAPPING] zone taxonomy '{label}' → groupes docs: {groupes}")
        
        # 3. Mapper les groupes musculaires de taxonomy vers les groupes fonctionnels
        for label, score in ranked.get("groupe", []):
            if score >= THRESH_SECONDARY:
                groupes = _map_intent_groupe_to_doc_groupe(label)
                matched_groupes.update(groupes)
                print(f"[MAPPING] groupe taxonomy '{label}' → groupes docs: {groupes}")
        
        # 4. Mapper les mots-clés de la requête vers les valeurs réelles
        if q:
            # Mots-clés → groupes
            keyword_groupes = _map_user_keywords_to_doc_groupe(q)
            matched_groupes.update(keyword_groupes)
            if keyword_groupes:
                print(f"[MAPPING] mots-clés query → groupes docs: {keyword_groupes}")
            
            # Mots-clés → objectifs
            keyword_objectifs = _map_user_keywords_to_doc_objectif(q)
            matched_objectifs.update(keyword_objectifs)
            if keyword_objectifs:
                print(f"[MAPPING] mots-clés query → objectifs docs: {keyword_objectifs}")
        
        # 5. Ajouter les filtres should pour les objectifs (valeurs réelles)
        for obj in matched_objectifs:
            f["should"].append({"key": "objectif", "match": {"value": obj}})
            print(f"[MAPPING] filtre objectif={obj}")
        
        # 6. Ajouter les filtres should pour les groupes (valeurs réelles)
        for groupe in matched_groupes:
            if groupe in VALID_DOC_GROUPES:  # Vérifier que c'est une valeur valide
                f["should"].append({"key": "groupe", "match": {"value": groupe}})
                print(f"[MAPPING] filtre groupe={groupe}")
        
        # 7. Profil utilisateur (niveau & matériel)
        if profile:
            niveau_val = _normalize_profile_key("niveau_sportif", profile) or _normalize_profile_key("niveau", profile)
            if niveau_val:
                niveau_norm = _normalize_niveau(str(niveau_val))
                f["should"].append({"key": "niveau", "match": {"value": niveau_norm}})
                print(f"[MAPPING] filtre niveau={niveau_norm}")
            
            # Matériel depuis le profil (normalisé)
            materiel_val = profile.get("materiel_disponible") or profile.get("materiel") or profile.get("equipment")
            if materiel_val:
                materiel_normalized = _normalize_materiel(materiel_val)
                for m in materiel_normalized:
                    f["should"].append({"key": "materiel", "match": {"value": m}})
                    print(f"[MAPPING] filtre materiel={m}")
        
        # min_should dynamique
        f["min_should"] = max(MIN_SHOULD, 1)
        
        # Si pas de should, retourner un format simple pour compatibilité
        if not f["should"]:
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
