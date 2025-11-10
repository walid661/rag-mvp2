# intent.py
import json
import os
from functools import lru_cache
from typing import Dict, List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()
TAXONOMY_PATH = os.getenv("INTENT_TAXONOMY_PATH", "./data/taxonomy.json")
TOPK = int(os.getenv("INTENT_TOPK", "3"))
THRESH_PRIMARY = float(os.getenv("INTENT_THRESHOLD_PRIMARY", "0.45"))
THRESH_SECONDARY = float(os.getenv("INTENT_THRESHOLD_SECONDARY", "0.35"))

@lru_cache(maxsize=1)
def _model():
    return SentenceTransformer(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2"))

@lru_cache(maxsize=1)
def _taxonomy() -> Dict:
    if not os.path.exists(TAXONOMY_PATH):
        print(f"[INTENT] WARNING: Taxonomy file not found at {TAXONOMY_PATH}, returning empty taxonomy.")
        return {}
    with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@lru_cache(maxsize=1)
def _catalog_embeddings():
    """Encode pour chaque entrée: name + synonyms + description (si présente)."""
    cat = _taxonomy()
    if not cat:
        return {}
    mdl = _model()
    catalog = {}
    for field, items in cat.items():
        entries = []
        for it in items:
            variants = [it["name"]]
            variants += it.get("synonyms", [])
            if it.get("description"):
                variants.append(it["description"])
            vecs = mdl.encode(variants, normalize_embeddings=True)
            entries.append({
                "name": it["name"],
                "synonyms": it.get("synonyms", []),
                "description": it.get("description", ""),
                "vectors": vecs,  # np.ndarray
            })
        catalog[field] = entries
    return catalog

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))

def classify_query(query: str) -> Dict[str, List[Tuple[str, float]]]:
    """Pour chaque champ, TOPK labels (name, score) triés par similarité."""
    if not query:
        return {}
    mdl = _model()
    qv = mdl.encode([query], normalize_embeddings=True)[0]
    catalog = _catalog_embeddings()
    if not catalog:
        return {}
    ranked: Dict[str, List[Tuple[str, float]]] = {}
    for field, entries in catalog.items():
        scores = []
        for e in entries:
            best = max(_cosine(qv, v) for v in e["vectors"])
            scores.append((e["name"], best))
        scores.sort(key=lambda x: x[1], reverse=True)
        ranked[field] = scores[:TOPK]
    return ranked

# Groupes par zone pour re-rank
UPPER_GROUPS = {"Biceps", "Triceps", "Pectoraux", "Épaules", "Dos"}
LOWER_GROUPS = {"Quadriceps", "Ischio-jambiers", "Fessiers", "Mollets"}

def reweight_groups_by_zone(ranked: Dict[str, List[Tuple[str, float]]]) -> Dict[str, List[Tuple[str, float]]]:
    """Booste les groupes cohérents avec la zone principale, et pénalise les autres."""
    if not ranked or "groupe" not in ranked or "zone" not in ranked:
        return ranked
    zone_top = ranked["zone"][0][0] if ranked["zone"] else None
    if not zone_top:
        return ranked

    boosted = []
    for label, score in ranked["groupe"]:
        new_score = score
        if zone_top == "Haut du corps":
            if label in UPPER_GROUPS:
                new_score += 0.15  # Boost plus fort (au lieu de 0.08)
            if label in LOWER_GROUPS:
                new_score -= 0.10  # Pénalité plus forte (au lieu de 0.05)
        elif zone_top == "Bas du corps":
            if label in LOWER_GROUPS:
                new_score += 0.15
            if label in UPPER_GROUPS:
                new_score -= 0.10
        # sinon, pas d'ajustement
        boosted.append((label, new_score))

    boosted.sort(key=lambda x: x[1], reverse=True)
    ranked["groupe"] = boosted
    print(f"[INTENT] Re-rank groupes par zone '{zone_top}': {ranked['groupe'][:3]}")
    return ranked

def expand_query_for_bm25(ranked: Dict[str, List[Tuple[str, float]]]) -> List[str]:
    """Expansion lexicale à partir des labels + descriptions (1–2 tokens discriminants)."""
    cat = _taxonomy()
    if not cat:
        return []
    expansions = []
    for field, candidates in ranked.items():
        for label, score in candidates:
            if score >= THRESH_SECONDARY:
                expansions.append(label)
                it = next((x for x in cat[field] if x["name"] == label), None)
                if it and it.get("description"):
                    tokens = [t.strip(",.;:() ").lower() for t in it["description"].split() if len(t) > 3]
                    for tok in tokens:
                        if tok not in expansions:
                            expansions.append(tok)
                        if len(expansions) >= 10:
                            break
    # dédoublonner (case-insensitive) en conservant l'ordre
    seen, out = set(), []
    for e in expansions:
        if e.lower() not in seen:
            out.append(e)
            seen.add(e.lower())
    return out

