# app/services/rag_router.py
from typing import Dict, Any, Optional, List
import os
from dotenv import load_dotenv

load_dotenv()

# --- TASK 3: SIMPLIFICATION ---
# Suppression de tous les dictionnaires géants (TAXONOMY_*, USER_KEYWORDS_*)
# Suppression des fonctions de mapping complexes  (_map_intent_*, _normalize_*, etc.)

def _normalize_niveau(niveau: str) -> str:
    """Normalise le niveau basique."""
    if not niveau:
        return ""
    niveau_lower = niveau.lower().strip()
    if "debutant" in niveau_lower or "débutant" in niveau_lower or "beginner" in niveau_lower:
        return "Débutant"
    if "intermediaire" in niveau_lower or "intermédiaire" in niveau_lower:
        return "Intermédiaire"
    if "expert" in niveau_lower or "avancé" in niveau_lower or "confirmé" in niveau_lower:
        return "Expert"
    return niveau.capitalize()

def build_filters(
    stage: str, 
    profile: Optional[Dict[str, Any]] = None, 
    extra: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Construit des filtres simplifiés pour Qdrant.
    Priorise la sécurité (Niveau) et le domaine, laisse le reste à la sémantique.
    """
    profile = profile or {}
    extra = extra or {}
    
    # Structure de filtre compatible avec le nouveau retriever (Pre-filtering)
    # On retourne un dictionnaire qui sera converti en Filter Qdrant
    f = {
        "must": [],
        "should": [],
        "must_not": []
    }

    # 1. Filtre de Domaine (Program vs Exercice)
    # Si la query demande explicitement un programme
    query = extra.get("query", "").lower()
    is_program_request = any(kw in query for kw in ["programme", "plan", "semaine", "planning"])
    
    if is_program_request:
        f["must"].append({"key": "domain", "match": {"value": "program"}})

    # 2. Sécurité Niveau (Hard Filter)
    # On empêche un débutant de voir du contenu expert, mais c'est tout.
    niveau_val = profile.get("level") or profile.get("niveau") or profile.get("niveau_sportif")
    if niveau_val:
        niveau_norm = _normalize_niveau(str(niveau_val))
        if niveau_norm == "Débutant":
            f["must_not"].append({"key": "difficulty_level", "match": {"value": "Expert"}})
            f["must_not"].append({"key": "difficulty_level", "match": {"value": "Avancé"}})
            # Boost sémantique (Should)
            f["should"].append({"key": "difficulty_level", "match": {"value": "Débutant"}})

    # 3. Matériel (Hard Filter - Optionnel mais recommandé)
    # On garde une logique simple : si equipment spécifié, on l'utilise en filtre permissif
    equipment = profile.get("equipment") or profile.get("materiel")
    if equipment:
        if isinstance(equipment, list):
            # L'utilisateur a une liste d'équipements. 
            # On pourrait filtrer strict, mais pour MVP "Simplicité", on laisse la recherche sémantique 
            # gérer la pertinence sauf si on veut être strict.
            pass

    # Nettoyage si listes vides
    final_filter = {}
    if f["must"]: final_filter["must"] = f["must"]
    if f["should"]: final_filter["should"] = f["should"]
    if f["must_not"]: final_filter["must_not"] = f["must_not"]

    return final_filter if final_filter else None
