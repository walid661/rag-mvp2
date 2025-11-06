import json
import uuid
import hashlib
import unicodedata
import re
from pathlib import Path

# Mapping dictionaries for normalising metadata fields
LEVEL_MAP = {
    "debutant": "beginner",
    "débutant": "beginner",
    "beginner": "beginner",
    "intermediaire": "intermediate",
    "intermédiaire": "intermediate",
    "intermediate": "intermediate",
    "avance": "advanced",
    "avancé": "advanced",
    "advanced": "advanced",
}

EQUIPMENT_MAP = {
    "body weight": "bodyweight",
    "bodyweight": "bodyweight",
    "poids du corps": "bodyweight",
    "haltère": "dumbbells",
    "haltères": "dumbbells",
    "dumbell": "dumbbells",
    "dumbbells": "dumbbells",
    "barre": "barbell",
    "barbells": "barbell",
}

def normalise_text(text: str) -> str:
    """Strip accents, lower case, and collapse whitespace"""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text

def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def canonicalise_exercise(exo: dict) -> dict:
    # Extract text and basic info
    text = exo.get("text") or exo.get("content") or ""
    text = text.strip()
    metadata = exo.get("metadata", {})

    title = metadata.get("title") or text.split("\n", 1)[0][:120]

    # Normalize level
    level_raw = metadata.get("difficulty_level", "")
    level_norm = LEVEL_MAP.get(normalise_text(level_raw), level_raw)

    # Normalize equipment into list
    equipment = metadata.get("equipment", [])
    if isinstance(equipment, str):
        equipment_list = [equipment]
    else:
        equipment_list = list(equipment)
    equipment_norm = []
    for eq in equipment_list:
        mapped = EQUIPMENT_MAP.get(normalise_text(str(eq)), str(eq))
        equipment_norm.append(mapped)

    muscles = metadata.get("muscles") or []
    mechanics = metadata.get("mechanics") or "compound"
    body_region = metadata.get("body_region") or "full"
    force_type = metadata.get("force_type") or "unsorted"
    laterality = metadata.get("laterality") or "bilateral"

    payload = {
        "doc_id": str(uuid.uuid4()),
        "title": title.strip(),
        "lang": "fr",
        "difficulty_level": level_norm,
        "equipment": equipment_norm,
        "muscles": muscles if isinstance(muscles, list) else [muscles],
        "mechanics": mechanics,
        "body_region": body_region,
        "force_type": force_type,
        "laterality": laterality,
        "tags": metadata.get("tags", []),
        "source": "json",
        "created_at": metadata.get("created_at"),
        "updated_at": metadata.get("updated_at"),
        "content_hash": compute_hash(text),
    }
    return {
        "doc_id": payload["doc_id"],
        "chunk_id": f"{payload['doc_id']}#0001",
        "text": text,
        "meta": payload,
    }

def main(in_dir="data/raw/exercises_json", out_path="data/processed/exercises.jsonl"):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as out_f:
        for json_path in Path(in_dir).glob("*.json"):
            try:
                exo = json.loads(json_path.read_text(encoding="utf-8"))
                row = canonicalise_exercise(exo)
                out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"Skipping {json_path}: {e}")

if __name__ == "__main__":
    main()