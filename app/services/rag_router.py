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
# IMPORTANT: Utiliser uniquement les valeurs qui existent vraiment dans les documents
TAXONOMY_OBJECTIF_TO_DOC_OBJECTIF: Dict[str, List[str]] = {
    "Hypertrophie fonctionnelle": [
        "renforcement contrôlé",
        "2 groupes / séance",
        "split alterné haut/bas",
        "split alterné haut bas",
        "force contrôlée avec charge modérée",
        "routine structurée mixte",
        "Classique",
        "Pumping",
        "Tempo training",
        "Tempo training + Dead Set",
        "Tempo training évolutif",
        "Tri – set / Bi – set / Drop Set",
        "Pumping + Split précis",
        "Dead set / Bi – set volumique",
    ],
    "Mobilité active guidée": [
        "mobilité active guidée",
        "mobilité active évoluée",
        "mobilité active sous charge légère",
        "mobilité d'entretien",
        "mobilité sous résistance",
        "mobilité sous résistance / contracté/relâché sous tension",
        "mobilité sous charge",
        "mobility flow",
        "mobility flow avancé",
        "mobility flow lent guidé",
    ],
    "Conditionnement métabolique": [
        "TABATA modifié (20''/20'' ou 20''/30'')",
        "TABATA modifié (30''/20'' ou 40''/20'')",
        "circuits training continu / fractionné lent",
        "cardio continu à intensité basse à moyenne",
        "AMRAP + HIIT combiné",
        "HIIT progressif débutant",
        "HIIT explosif + renfo ciblée",
        "metcon modéré + cardio fonctionnel",
        "metcon cardio modéré",
        "metcon cardio/renfo combiné",
        "metcon renfo (charges modérées, récup courte)",
        "tonification + cardio combiné",
        "Atteindre un pic de dépense énergétique; progression via volume extrême et récupération courte.",
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
    "endurance": [
        "circuits training continu / fractionné lent",
        "cardio continu à intensité basse à moyenne",
        "cardio continu modéré",
        "cardio continu léger",
    ],
    "cardio": [
        "circuits training continu / fractionné lent",
        "cardio continu à intensité basse à moyenne",
        "cardio continu modéré",
        "cardio continu léger",
        "TABATA modifié (20''/20'' ou 20''/30'')",
        "TABATA modifié (30''/20'' ou 40''/20'')",
    ],
    "respiration": ["circuits training continu / fractionné lent", "étirements + respiration"],
    "souffle": ["circuits training continu / fractionné lent", "étirements + respiration"],
    
    # Métabolique / Perte de poids
    "perte de poids": [
        "TABATA modifié (20''/20'' ou 20''/30'')",
        "TABATA modifié (30''/20'' ou 40''/20'')",
        "AMRAP + HIIT combiné",
        "HIIT progressif débutant",
        "HIIT explosif + renfo ciblée",
    ],
    "perte poids": [
        "TABATA modifié (20''/20'' ou 20''/30'')",
        "TABATA modifié (30''/20'' ou 40''/20'')",
        "AMRAP + HIIT combiné",
        "HIIT progressif débutant",
    ],
    "minceur": [
        "TABATA modifié (20''/20'' ou 20''/30'')",
        "TABATA modifié (30''/20'' ou 40''/20'')",
        "AMRAP + HIIT combiné",
    ],
    "sèche": [
        "TABATA modifié (20''/20'' ou 20''/30'')",
        "TABATA modifié (30''/20'' ou 40''/20'')",
        "AMRAP + HIIT combiné",
    ],
    "seche": [
        "TABATA modifié (20''/20'' ou 20''/30'')",
        "TABATA modifié (30''/20'' ou 40''/20'')",
        "AMRAP + HIIT combiné",
    ],
    "brûlage": ["AMRAP + HIIT combiné", "HIIT explosif + renfo ciblée"],
    "brulage": ["AMRAP + HIIT combiné", "HIIT explosif + renfo ciblée"],
    "métabolique": [
        "TABATA modifié (20''/20'' ou 20''/30'')",
        "TABATA modifié (30''/20'' ou 40''/20'')",
        "AMRAP + HIIT combiné",
    ],
    "metabolique": [
        "TABATA modifié (20''/20'' ou 20''/30'')",
        "TABATA modifié (30''/20'' ou 40''/20'')",
        "AMRAP + HIIT combiné",
    ],
    
    # Hypertrophie
    "hypertrophie": ["2 groupes / séance", "Classique", "Pumping", "Tempo training"],
    "volume": ["2 groupes / séance", "Classique", "Pumping"],
    "masse musculaire": ["2 groupes / séance", "Classique", "Pumping"],
    "prise de muscle": ["2 groupes / séance", "Classique", "Pumping"],
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

# Objectifs réels qui existent dans les documents (basé sur l'analyse de meso_catalog.jsonl)
# Ces valeurs sont utilisées pour valider les filtres objectif avant de les ajouter
VALID_DOC_OBJECTIFS: Set[str] = {
    # Mobilité
    "mobilité active guidée",
    "mobilité active évoluée",
    "mobilité active sous charge légère",
    "mobilité d'entretien",
    "mobilité sous résistance",
    "mobilité sous résistance / contracté/relâché sous tension",
    "mobilité sous charge",
    "mobility flow",
    "mobility flow avancé",
    "mobility flow lent guidé",
    
    # Renforcement / Force
    "renforcement contrôlé",
    "renforcement structuré : circuits poids du corps + élastiques",
    "renforcement postural léger",
    "force",
    "force contrôlée avec charge modérée",
    
    # Gainage / Stabilité
    "gainage postural statique contrôlé",
    "gainage fonctionnel instable / stabilité dynamique unilatérale",
    "gainage dynamique instable",
    "gainage dynamique avec charge ou instabilité + surcharge",
    "gainage fonctionnel guidé",
    "gainage léger & respiration",
    "gainage léger & cardio doux",
    "gainage léger et cardio doux",
    "stabilité fonctionnelle simple",
    "instabilité contrôlée",
    
    # Split / Routine
    "split alterné haut/bas",
    "split alterné haut bas",
    "Split push/pull ou haut/bas progressif",
    "split spécifique mixte",
    "split hebdo léger",
    "routine structurée mixte",
    "routine fonctionnelle douce",
    "routine métabolique hebdomadaire",
    "routine vitalité",
    "routine légère full body",
    "routine de mise en route spécifique",
    
    # Hypertrophie
    "Classique",
    "Pumping",
    "Tempo training",
    "Tempo training + Dead Set",
    "Tempo training évolutif",
    "2 groupes / séance",
    "Tri – set / Bi – set / Drop Set",
    "Pumping + Split précis",
    "Dead set / Bi – set volumique",
    
    # Cardio / Endurance
    "cardio continu à intensité basse à moyenne",
    "cardio continu modéré",
    "cardio continu léger",
    "cardio fonctionnel doux",
    "cardio",
    "tempo continu contrôlé",
    "tempo run soutenu",
    "intervalles classiques",
    "intervalles intensifs (VO2max)",
    "fartlek structuré",
    
    # Métabolique / HIIT
    "TABATA modifié (20''/20'' ou 20''/30'')",
    "TABATA modifié (30''/20'' ou 40''/20'')",
    "circuits training continu / fractionné lent",
    "circuits fractionnés (intermittent structuré)",
    "circuits cardio modéré par intervalles lactiques",
    "circuits fonctionnels",
    "circuit complet multi – dimensionnel",
    "circuit full body dynamique doux",
    "HIIT progressif débutant",
    "HIIT explosif + renfo ciblée",
    "AMRAP + HIIT combiné",
    "metcon modéré + cardio fonctionnel",
    "metcon cardio modéré",
    "metcon cardio/renfo combiné",
    "metcon renfo (charges modérées, récup courte)",
    "tonification + cardio combiné",
    "Atteindre un pic de dépense énergétique; progression via volume extrême et récupération courte.",
    
    # Puissance / Explosivité
    "circuits dynamiques simples",
    "musculaire : activation nerf/muscle",
    "pliométrie douce guidée (basse, moyenne)",
    "contractions rapides au poids du corps",
    "pliométrie légère + coordination",
    "intervalles de puissance (1:3 / 1:4)",
    "mix explosivité + gainage actif",
    "Max effort (3 – 5 reps lourdes, récup complète)",
    "cycles élastiques",
    "complexes dynamiques",
    
    # Récupération / Respiration
    "mobility flow lent guidé",
    "contracté / relâché passif",
    "séance guidée lente",
    "cohérence cardiaque",
    "étirements + respiration",
    "effort : respiration",
    "auto",
    "surcharge : programme hebdo",
    "récupération systémique structurée",
    
    # Bien-être
    "full body doux structuré",
    "routine fonctionnelle douce",
    "raideur : mobilisation lente",
    "stimulation complète combinée",
    
    # Préparation
    "simulation type",
    "simulation compétition",
    "effort proche des conditions réelles",
    "charges spécifiques : formats très ciblés",
    "tapering structuré",
    
    # Fonctionnel
    "mouvements fonctionnels guidés, gestes fonctionnels unilatéraux",
    "contrôle latéralisé",
    "agilité / motricité",
    
    # Autres
    "postures statiques guidées",
    "maintien postural + respiration diaphragmatique lente",
    "contracté / relâché",
    "libération myofasciale : foam roller / balles",
    "reset physique",
    "plans",
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
    Normalise le matériel utilisateur vers les valeurs françaises attendues dans les nouveaux exercices.
    Retourne les valeurs françaises correspondantes pour filtrage dans Qdrant.
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
        
        # Mapping vers les valeurs françaises des nouveaux exercices
        if any(kw in m_lower for kw in ["barre", "barbell", "rack", "machine", "machines", "full gym", "full_gym"]):
            normalized.append("Barre")  # Valeur française dans les exercices
        elif any(kw in m_lower for kw in ["haltère", "haltères", "dumbbell", "dumbbells"]):
            normalized.append("Haltère")  # Valeur française dans les exercices
        elif any(kw in m_lower for kw in ["kettlebell", "kb"]):
            normalized.append("Kettlebell")  # Même valeur en français et anglais
        elif any(kw in m_lower for kw in ["câble", "cable"]):
            normalized.append("Câble")  # Valeur française dans les exercices
        elif any(kw in m_lower for kw in ["élastique", "élastiques", "band", "bands", "bande", "bandes", "miniband"]):
            normalized.append("Élastique")  # Valeur française approximative
        elif any(kw in m_lower for kw in ["aucun", "poids du corps", "bodyweight", "sans matériel", "sans materiel"]):
            normalized.append("Poids du corps")  # Valeur française dans les exercices
        elif any(kw in m_lower for kw in ["tapis", "mat", "matelas"]):
            normalized.append("Tapis")  # Valeur française approximative
        elif any(kw in m_lower for kw in ["balle", "stability ball", "ball"]):
            normalized.append("Balle de stabilité")  # Valeur française dans les exercices
        elif any(kw in m_lower for kw in ["disque", "plate", "weight plate"]):
            normalized.append("Disque de poids")  # Valeur française dans les exercices
        elif any(kw in m_lower for kw in ["sandbag", "sac", "sable"]):
            normalized.append("Sandbag")  # Même valeur en français et anglais
        elif any(kw in m_lower for kw in ["suspension", "trx", "anneaux", "ring"]):
            normalized.append("Suspension")  # Valeur française approximative
        else:
            # Par défaut, garder la valeur originale (capitalisée pour correspondre au format français)
            normalized.append(str(m).capitalize())
    
    return list(set(normalized))  # Dédupliquer

def _get_antagonist_muscle_group(muscle_group: str) -> Optional[str]:
    """
    Retourne le muscle antagoniste d'un groupe musculaire donné.
    Utilise les paires antagonistes connues (alignées avec muscle_balance_rules.jsonl).
    
    Args:
        muscle_group: Groupe musculaire (ex: "Biceps", "Quadriceps")
    
    Returns:
        Muscle antagoniste ou None si aucun antagoniste connu
    """
    muscle_lower = muscle_group.lower()
    
    # Paires antagonistes (alignées avec muscle_balance_rules.jsonl)
    antagonist_pairs = {
        "biceps": "Triceps",
        "triceps": "Biceps",
        "quadriceps": "Ischio-jambiers",
        "ischio-jambiers": "Quadriceps",
        "ischio": "Quadriceps",
        "pectoraux": "Dos",
        "dos": "Pectoraux",
        "épaules": "Dos",  # Épaules → Dos (antagoniste général)
        "abdominaux": "Lombaires",
        "abdos": "Lombaires",
        "lombaires": "Abdominaux",
        "fessiers": "Psoas",
        "psoas": "Fessiers",
        "deltoïdes antérieurs": "Deltoïdes postérieurs",
        "deltoïdes postérieurs": "Deltoïdes antérieurs",
    }
    
    # Chercher une correspondance (exacte ou partielle)
    for key, antagonist in antagonist_pairs.items():
        if key in muscle_lower or muscle_lower in key:
            return antagonist
    
    return None

def _map_zone_to_muscle_group(zone: str) -> List[str]:
    """
    Mappe une zone du corps vers les groupes musculaires français des nouveaux exercices.
    """
    zone_lower = zone.lower()
    mapping = {
        "bras": ["Biceps", "Triceps", "Avant-bras"],
        "biceps": ["Biceps"],
        "triceps": ["Triceps"],
        "épaules": ["Épaules", "Deltoïdes"],
        "pectoraux": ["Pectoraux", "Poitrine"],
        "dos": ["Dos", "Lombaires", "Trapèzes", "Rhomboides"],
        "abdominaux": ["Abdominaux", "Core"],
        "abdos": ["Abdominaux", "Core"],
        "tronc": ["Abdominaux", "Core", "Lombaires"],
        "jambes": ["Quadriceps", "Ischio-jambiers", "Mollets"],
        "cuisses": ["Quadriceps", "Ischio-jambiers"],
        "quadriceps": ["Quadriceps"],
        "ischio": ["Ischio-jambiers"],
        "fessiers": ["Fessiers", "Glutes"],
        "mollets": ["Mollets"],
        "haut du corps": ["Biceps", "Triceps", "Épaules", "Pectoraux", "Dos"],
        "bas du corps": ["Quadriceps", "Ischio-jambiers", "Fessiers", "Mollets"],
    }
    
    # Chercher une correspondance exacte ou partielle
    for key, values in mapping.items():
        if key in zone_lower:
            return values
    
    # Par défaut, retourner la zone telle quelle (si elle correspond déjà à un groupe)
    return [zone]

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

    if stage == "auto":
        # Mode RAG sémantique pur : pas de filtres restrictifs sur domain/type
        # Laisser l'embedding trouver les meilleurs documents, peu importe leur type
        f = {
            "should": [],  # Filtres optionnels pour affiner
            "must": [],    # Filtres obligatoires pour critères essentiels
            "must_not": []
        }
        
        query = extra.get("query", "").lower() if extra else ""
        
        # Détection du type de requête : programme vs exercices
        is_program_request = any(kw in query for kw in [
            "programme", "plan", "semaine", "semaines", "cycle", "meso", "micro",
            "planning", "plan d'entraînement", "programme d'entraînement", "4 semaines", "3 semaines"
        ])
        
        # Si c'est une requête de programme, privilégier les documents de type program
        if is_program_request:
            f["should"].append({"key": "domain", "match": {"value": "program"}})
            print(f"[MAPPING] Détection requête 'programme' → filtre should domain=program")
        
        # Filtres d'affinage optionnels (should) pour aider sans restreindre
        # 1. Niveau / Difficulty level
        if profile:
            niveau_val = _normalize_profile_key("niveau_sportif", profile) or _normalize_profile_key("niveau", profile)
            if niveau_val:
                niveau_norm = _normalize_niveau(str(niveau_val))
                # Pour les meso/micro
                f["should"].append({"key": "niveau", "match": {"value": niveau_norm}})
                # Pour les exercices (mapping vers difficulty_level)
                difficulty_mapping = {
                    "débutant": "Débutant",
                    "intermédiaire": "Intermédiaire",
                    "avancé": "Avancé",
                    "expert": "Expert"
                }
                difficulty = difficulty_mapping.get(niveau_norm.lower(), niveau_norm)
                f["should"].append({"key": "difficulty_level", "match": {"value": difficulty}})
                print(f"[MAPPING] filtre niveau={niveau_norm} (optionnel)")
            
            # 2. Équipement (optionnel)
            equipment_val = _normalize_profile_key("equipment", profile) or _normalize_profile_key("materiel", profile) or _normalize_profile_key("matériel", profile)
            if equipment_val:
                if isinstance(equipment_val, list):
                    equipment_normalized = []
                    for eq in equipment_val:
                        normalized = _normalize_materiel(eq)
                        equipment_normalized.extend(normalized)
                    equipment_normalized = list(set(equipment_normalized))
                else:
                    equipment_normalized = list(set(_normalize_materiel(equipment_val)))
                
                for eq in equipment_normalized:
                    # Pour les exercices (nouveau format)
                    f["should"].append({"key": "primary_equipment", "match": {"value": eq}})
                    # Pour compatibilité (ancien format)
                    f["should"].append({"key": "equipment", "match": {"value": eq}})
                    f["should"].append({"key": "materiel", "match": {"value": eq}})
                print(f"[MAPPING] filtres équipement={equipment_normalized} (optionnels)")
        
        # 3. Détection sémantique des groupes musculaires depuis la query
        # IMPORTANT : Si on détecte un groupe musculaire spécifique, le rendre OBLIGATOIRE (must)
        # AMÉLIORATION : Utiliser _get_antagonist_muscle_group() pour équilibrer automatiquement
        if query:
            query_lower = query.lower()
            
            # Bras → Biceps + Triceps (OBLIGATOIRE)
            if "bras" in query_lower or ("muscler" in query_lower and "bras" in query_lower):
                # Utiliser MatchAny pour permettre Biceps OU Triceps
                f["must"].append({"key": "target_muscle_group", "match": {"any": ["Biceps", "Triceps"]}})
                print(f"[MAPPING] détection 'bras' → filtre MUST Biceps/Triceps (obligatoire)")
            elif "biceps" in query_lower:
                # AMÉLIORATION : Inclure aussi l'antagoniste (Triceps) pour équilibrage
                antagonist = _get_antagonist_muscle_group("Biceps")
                if antagonist:
                    f["must"].append({"key": "target_muscle_group", "match": {"any": ["Biceps", antagonist]}})
                    print(f"[MAPPING] détection 'biceps' → filtre MUST Biceps/{antagonist} (obligatoire, équilibré)")
                else:
                    f["must"].append({"key": "target_muscle_group", "match": {"value": "Biceps"}})
                    print(f"[MAPPING] détection 'biceps' → filtre MUST Biceps (obligatoire)")
            elif "triceps" in query_lower:
                # AMÉLIORATION : Inclure aussi l'antagoniste (Biceps) pour équilibrage
                antagonist = _get_antagonist_muscle_group("Triceps")
                if antagonist:
                    f["must"].append({"key": "target_muscle_group", "match": {"any": ["Triceps", antagonist]}})
                    print(f"[MAPPING] détection 'triceps' → filtre MUST Triceps/{antagonist} (obligatoire, équilibré)")
                else:
                    f["must"].append({"key": "target_muscle_group", "match": {"value": "Triceps"}})
                    print(f"[MAPPING] détection 'triceps' → filtre MUST Triceps (obligatoire)")
            
            # Autres groupes musculaires spécifiques → must aussi
            # AMÉLIORATION : Inclure automatiquement les antagonistes pour équilibrage
            elif "jambes" in query_lower or "cuisses" in query_lower or "quadriceps" in query_lower:
                muscle_groups = _map_zone_to_muscle_group(query)
                # Pour jambes/cuisses, inclure Quadriceps ET Ischio-jambiers (antagonistes)
                if "quadriceps" in query_lower:
                    antagonist = _get_antagonist_muscle_group("Quadriceps")
                    if antagonist and antagonist not in muscle_groups:
                        muscle_groups.append(antagonist)
                elif "ischio" in query_lower:
                    antagonist = _get_antagonist_muscle_group("Ischio-jambiers")
                    if antagonist and antagonist not in muscle_groups:
                        muscle_groups.append(antagonist)
                
                if len(muscle_groups) > 1:
                    f["must"].append({"key": "target_muscle_group", "match": {"any": muscle_groups}})
                else:
                    f["must"].append({"key": "target_muscle_group", "match": {"value": muscle_groups[0]}})
                print(f"[MAPPING] détection jambes → filtre MUST {muscle_groups} (obligatoire)")
            elif "abdos" in query_lower or "abdominaux" in query_lower or ("tronc" in query_lower and "core" not in query_lower):
                # AMÉLIORATION : Inclure aussi Lombaires (antagoniste)
                antagonist = _get_antagonist_muscle_group("Abdominaux")
                if antagonist:
                    f["must"].append({"key": "target_muscle_group", "match": {"any": ["Abdominaux", antagonist]}})
                    print(f"[MAPPING] détection abdominaux → filtre MUST Abdominaux/{antagonist} (obligatoire, équilibré)")
                else:
                    f["must"].append({"key": "target_muscle_group", "match": {"value": "Abdominaux"}})
                    print(f"[MAPPING] détection abdominaux → filtre MUST Abdominaux (obligatoire)")
            elif "fessiers" in query_lower or "glutes" in query_lower:
                f["must"].append({"key": "target_muscle_group", "match": {"value": "Fessiers"}})
                print(f"[MAPPING] détection fessiers → filtre MUST Fessiers (obligatoire)")
            elif "épaules" in query_lower or "deltoides" in query_lower or "deltoïdes" in query_lower:
                f["must"].append({"key": "target_muscle_group", "match": {"value": "Épaules"}})
                print(f"[MAPPING] détection épaules → filtre MUST Épaules (obligatoire)")
            elif "pectoraux" in query_lower or "pecs" in query_lower:
                # AMÉLIORATION : Inclure aussi Dos (antagoniste)
                antagonist = _get_antagonist_muscle_group("Pectoraux")
                if antagonist:
                    f["must"].append({"key": "target_muscle_group", "match": {"any": ["Pectoraux", antagonist]}})
                    print(f"[MAPPING] détection pectoraux → filtre MUST Pectoraux/{antagonist} (obligatoire, équilibré)")
                else:
                    f["must"].append({"key": "target_muscle_group", "match": {"value": "Pectoraux"}})
                    print(f"[MAPPING] détection pectoraux → filtre MUST Pectoraux (obligatoire)")
            elif "dos" in query_lower and "quadriceps" not in query_lower:  # Éviter conflit avec "dos de la cuisse"
                # AMÉLIORATION : Inclure aussi Pectoraux (antagoniste)
                antagonist = _get_antagonist_muscle_group("Dos")
                if antagonist:
                    f["must"].append({"key": "target_muscle_group", "match": {"any": ["Dos", antagonist]}})
                    print(f"[MAPPING] détection dos → filtre MUST Dos/{antagonist} (obligatoire, équilibré)")
                else:
                    f["must"].append({"key": "target_muscle_group", "match": {"value": "Dos"}})
                    print(f"[MAPPING] détection dos → filtre MUST Dos (obligatoire)")
            
            # Zones du corps → body_region (should, optionnel)
            if any(kw in query for kw in ["tronc", "midsection", "core", "abdos", "abdominaux"]):
                f["should"].append({"key": "body_region", "match": {"value": "Tronc"}})
            elif any(kw in query for kw in ["haut du corps", "upper body", "bras", "épaules", "dos", "pectoraux"]):
                f["should"].append({"key": "body_region", "match": {"value": "Membre supérieur"}})
            elif any(kw in query for kw in ["bas du corps", "lower body", "jambes", "cuisses", "fessiers"]):
                f["should"].append({"key": "body_region", "match": {"value": "Membre inférieur"}})
        
        # 4. Zones ciblées du profil (should, optionnel seulement si pas de must depuis query)
        if not f["must"]:  # Seulement si on n'a pas déjà de must depuis la query
            zones_val = profile.get("zones_ciblees") or extra.get("zones") or extra.get("zone")
            if zones_val:
                if isinstance(zones_val, list):
                    # NE PAS mapper "Full body" vers target_muscle_group pour les exercices
                    # "Full body" est une zone, pas un groupe musculaire
                    filtered_zones = [z for z in zones_val if z.lower() != "full body"]
                    
                    if filtered_zones:  # Si on a d'autres zones que "Full body"
                        muscle_groups = []
                        for zone in filtered_zones:
                            mapped = _map_zone_to_muscle_group(zone)
                            muscle_groups.extend(mapped)
                        muscle_groups = list(set(muscle_groups))
                        
                        for mg in muscle_groups:
                            f["should"].append({"key": "target_muscle_group", "match": {"value": mg}})
                        print(f"[MAPPING] zones profil → filtres {muscle_groups} (optionnels)")
                    
                    # Si "Full body" est présent, utiliser body_region ou groupe pour programmes
                    if "Full body" in zones_val or "full body" in [z.lower() for z in zones_val]:
                        # Pour les exercices : utiliser body_region (optionnel)
                        f["should"].append({"key": "body_region", "match": {"any": ["Membre supérieur", "Membre inférieur", "Tronc"]}})
                        # Pour les programmes : utiliser groupe (optionnel)
                        f["should"].append({"key": "groupe", "match": {"any": ["Tonification & Renforcement", "Reconditionnement général", "Hypertrophie"]}})
                        print(f"[MAPPING] zone 'Full body' → filtres body_region/groupe (optionnels)")
                else:
                    zone_str = str(zones_val)
                    if zone_str.lower() != "full body":
                        muscle_groups = list(set(_map_zone_to_muscle_group(zone_str)))
                        for mg in muscle_groups:
                            f["should"].append({"key": "target_muscle_group", "match": {"value": mg}})
                        print(f"[MAPPING] zones profil → filtres {muscle_groups} (optionnels)")
                    else:
                        # "Full body" seul : utiliser body_region/groupe
                        f["should"].append({"key": "body_region", "match": {"any": ["Membre supérieur", "Membre inférieur", "Tronc"]}})
                        f["should"].append({"key": "groupe", "match": {"any": ["Tonification & Renforcement", "Reconditionnement général", "Hypertrophie"]}})
                        print(f"[MAPPING] zone 'Full body' → filtres body_region/groupe (optionnels)")
        
        # min_should = 1 si on a des filtres should, 0 sinon
        if f["should"]:
            f["min_should"] = 1
        else:
            f["min_should"] = 0
        
        # Si on a des must, les garder même si should est vide
        if f["must"]:
            print(f"[MAPPING] Mode auto : {len(f['must'])} filtres MUST (obligatoires), {len(f['should'])} filtres should (optionnels)")
        elif f["should"]:
            print(f"[MAPPING] Mode auto : {len(f['should'])} filtres should, min_should=1 (au moins 1 doit correspondre)")
        else:
            print(f"[MAPPING] Mode auto : aucun filtre, recherche sémantique pure")
            return None
        
        return f

    elif stage == "select_meso":
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
        # IMPORTANT: Ne filtrer par objectif que si la valeur existe vraiment dans les documents
        # Les objectifs sont très variés (108 valeurs uniques), donc on les utilise comme filtre optionnel
        objectif_filters_added = 0
        for obj in matched_objectifs:
            # Vérifier que l'objectif existe vraiment dans les documents
            if obj in VALID_DOC_OBJECTIFS:
                f["should"].append({"key": "objectif", "match": {"value": obj}})
                objectif_filters_added += 1
                print(f"[MAPPING] filtre objectif={obj} (validé)")
            else:
                print(f"[MAPPING] filtre objectif={obj} IGNORÉ (n'existe pas dans les documents)")
        
        # 6. Ajouter les filtres should pour les groupes (valeurs réelles)
        # PRIORITÉ: Les groupes sont plus stables et fiables que les objectifs
        groupe_filters_added = 0
        for groupe in matched_groupes:
            if groupe in VALID_DOC_GROUPES:  # Vérifier que c'est une valeur valide
                f["should"].append({"key": "groupe", "match": {"value": groupe}})
                groupe_filters_added += 1
                print(f"[MAPPING] filtre groupe={groupe}")
        
        # Log pour diagnostic
        print(f"[MAPPING] Filtres ajoutés: {objectif_filters_added} objectifs, {groupe_filters_added} groupes")
        
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
        # Prioriser groupe + niveau (plus stables) plutôt que objectif (trop varié)
        # Si on a des filtres groupe, on peut être plus strict
        # Si on n'a que des filtres objectif, on doit être plus permissif
        if groupe_filters_added > 0:
            # Si on a des groupes, on peut exiger au moins 1 filtre groupe OU niveau
            f["min_should"] = max(MIN_SHOULD, 1)
        elif objectif_filters_added > 0:
            # Si on n'a que des objectifs, être plus permissif (min_should=1)
            f["min_should"] = 1
        else:
            # Si on n'a ni groupe ni objectif, au moins niveau ou matériel
            f["min_should"] = 1
        
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
        
        # NOUVEAU : Utiliser les champs français des nouveaux exercices
        # Support multi-valeurs pour l'équipement
        equipment_val = _normalize_profile_key("equipment", profile) or _normalize_profile_key("materiel", profile) or _normalize_profile_key("matériel", profile)
        if equipment_val:
            # Normaliser les valeurs d'équipement vers les valeurs françaises
            if isinstance(equipment_val, list):
                equipment_normalized = []
                for eq in equipment_val:
                    normalized = _normalize_materiel(eq)
                    equipment_normalized.extend(normalized)
                f["primary_equipment"] = list(set(equipment_normalized))  # Dédupliquer
            else:
                normalized = _normalize_materiel(equipment_val)
                f["primary_equipment"] = list(set(normalized))
            # Compatibilité : aussi mettre dans equipment pour anciens exercices
            f["equipment"] = f["primary_equipment"]
        
        # NOUVEAU : Utiliser target_muscle_group (français) au lieu de zone
        zones_val = profile.get("zones_ciblees") or extra.get("zones") or extra.get("zone")
        if zones_val:
            if isinstance(zones_val, list):
                # Mapper les zones vers les groupes musculaires français
                muscle_groups = []
                for zone in zones_val:
                    # Mapping zones → groupes musculaires (ex: "Bras" → "Biceps", "Triceps")
                    mapped = _map_zone_to_muscle_group(zone)
                    muscle_groups.extend(mapped)
                f["target_muscle_group"] = list(set(muscle_groups))
            else:
                mapped = _map_zone_to_muscle_group(str(zones_val))
                f["target_muscle_group"] = list(set(mapped))
            # Compatibilité : aussi mettre dans zone pour anciens exercices
            f["zone"] = f["target_muscle_group"]
        
        # NOUVEAU : Utiliser difficulty_level (français) au lieu de niveau
        niveau_val = _normalize_profile_key("niveau_sportif", profile) or _normalize_profile_key("niveau", profile)
        if niveau_val:
            niveau_norm = _normalize_niveau(str(niveau_val))
            # Mapping vers les valeurs françaises des nouveaux exercices
            difficulty_mapping = {
                "débutant": "Débutant",
                "intermédiaire": "Intermédiaire",
                "avancé": "Avancé",
                "expert": "Expert"
            }
            difficulty = difficulty_mapping.get(niveau_norm.lower(), niveau_norm)
            f["difficulty_level"] = difficulty
            # Compatibilité : aussi mettre dans niveau
            f["niveau"] = difficulty
        
        # NOUVEAU : Filtrer par body_region si disponible dans la query
        query = extra.get("query", "").lower() if extra else ""
        if any(kw in query for kw in ["tronc", "midsection", "core", "abdos", "abdominaux"]):
            f["body_region"] = "Tronc"
        elif any(kw in query for kw in ["haut du corps", "upper body", "bras", "épaules", "dos"]):
            f["body_region"] = "Membre supérieur"
        elif any(kw in query for kw in ["bas du corps", "lower body", "jambes", "cuisses"]):
            f["body_region"] = "Membre inférieur"
        
        # NOUVEAU : Filtrer par movement_pattern si détecté dans la query
        if any(kw in query for kw in ["anti-extension", "anti extension"]):
            f["movement_pattern"] = "Anti-extension"
        elif any(kw in query for kw in ["flexion", "squat"]):
            f["movement_pattern"] = "Squat"
        elif any(kw in query for kw in ["traction", "row", "pull"]):
            f["movement_pattern"] = "Pull"
        elif any(kw in query for kw in ["poussée", "push", "press"]):
            f["movement_pattern"] = "Push"
    
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
