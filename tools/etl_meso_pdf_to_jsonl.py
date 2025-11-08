#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extraction méso-cycles depuis meso.pdf -> JSONL propre pour RAG.
- Étape A (obligatoire) : extraction déterministe (pdfminer + regex) -> enregistrements bruts
- Étape B (optionnelle via --use-openai) : normalisation/francisation stricte sous schéma JSON (temperature=0)
- Validation jsonschema -> on écrit uniquement des lignes valides
- Aucune clé vide n'est écrite; on filtre les champs vides

Usage:
    python etl_meso_pdf_to_jsonl.py --pdf meso.pdf --out meso_catalog.jsonl [--use-openai] [--model gpt-4o-mini]

Dépendances:
    pip install pdfminer.six jsonschema openai
"""
import os
import re
import sys
import json
import argparse
import hashlib
import unicodedata
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

try:
    from pdfminer.high_level import extract_text
except ImportError:
    print("Veuillez installer pdfminer.six : pip install pdfminer.six", file=sys.stderr)
    sys.exit(1)
try:
    from jsonschema import validate, Draft202012Validator
except ImportError:
    print("Veuillez installer jsonschema : pip install jsonschema", file=sys.stderr)
    sys.exit(1)
USE_OPENAI = False
try:
    from openai import OpenAI
except Exception:
    OpenAI = None
MESO_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "type", "meso_id", "objectif", "niveau", "nom", "methode",
        "variables", "systeme_energetique", "intention", "groupe",
        "niveau_bloc", "text", "source_pdf", "source_hash"
    ],
    "properties": {
        "type": {"type": "string", "const": "meso_ref"},
        "meso_id": {"type": "string", "pattern": r"^MC\d+(\.\d+)?$"},
        "objectif": {
            "type": "string",
            "enum": [
                "reconditionnement","renforcement","hypertrophie","mobilite",
                "perte_de_masse","endurance_cardio","performance",
                "sante_longevite","recuperation","preparation_objectif",
                "fonctionnel","maintenance","autre"
            ]
        },
        "niveau": {"type": "string", "enum": ["debutant","intermediaire","avance"]},
        "nom": {"type": "string", "minLength": 1},
        "methode": {"type": "string", "minLength": 1},
        "variables": {
            "type": "object",
            "additionalProperties": False,
            "required": ["I","T","S","RE","RY"],
            "properties": {
                "I": {"type": "string", "minLength": 1},
                "T": {"type": "string", "minLength": 1},
                "S": {"type": "string", "minLength": 1},
                "RE": {"type": "string", "minLength": 1},
                "RY": {"type": "string", "minLength": 1}
            }
        },
        "sollicitation_neuromusculaire": {"type": "string", "minLength": 1},
        "systeme_energetique": {"type": "string", "minLength": 1},
        "intention": {"type": "string", "minLength": 1},
        "groupe": {"type": "string", "minLength": 1},
        "niveau_bloc": {"type": "string", "minLength": 1},
        "text": {"type": "string", "minLength": 1},
        "source_pdf": {"type": "string", "minLength": 1},
        "source_hash": {"type": "string", "minLength": 1}
    }
}
RUBRIQUES = [
    "Reconditionnement général","Tonification et Renforcement","Hypertrophie structurelle",
    "Mobilité","Perte de masse grasse","Endurance & capacité cardio",
    "Performance & intensification","Santé & longévité active",
    "Préparation mentale & récupération","Préparation à un objectif",
    "Entraînement fonctionnel polyvalent","Routine de maintenance",
]
NIV_MARKERS = ["Débutant","Intermédiaire","Confirmé"]
# Tolère différents tirets (– — -), espaces multiples, points-virgules optionnels,
# et variations d'espacement autour des parenthèses.
MC_PATTERNS = [
    re.compile(
        r"^(MC(?P<id>\d+(?:\.\d+)?))\s*[–—-]\s*"
        r"(?P<nom>.+?)\s*[–—-]\s*"
        r"(?P<methode>.+?)\s*[–—-]\s*"
        r"I\s*\(\s*(?P<I>[^)]*?)\s*\)\s*;\s*"
        r"T\s*\(\s*(?P<T>[^)]*?)\s*\)\s*;\s*"
        r"S\s*\(\s*(?P<S>[^)]*?)\s*\)\s*;\s*"
        r"RE\s*\(\s*(?P<RE>[^)]*?)\s*\)\s*;\s*"
        r"RY\s*\(\s*(?P<RY>[^)]*?)\s*\)\s*[–—-]\s*"
        r"(?P<neuro>.+?)\s*[–—-]\s*"
        r"(?P<energy>.+?)\s*[–—-]\s*"
        r"(?P<intention>.+?)\s*$"
    ),
    # Variante : points-virgules sans espace après (format PDF réel)
    # Pattern plus souple : accepte ; avec ou sans espace
    re.compile(
        r"^(MC(?P<id>\d+(?:\.\d+)?))\s*[–—-]\s*"
        r"(?P<nom>.+?)\s*[–—-]\s*"
        r"(?P<methode>.+?)\s*[–—-]\s*"
        r"I\s*\(\s*(?P<I>[^)]*?)\s*\)\s*;\s*"
        r"T\s*\(\s*(?P<T>[^)]*?)\s*\)\s*;\s*"
        r"S\s*\(\s*(?P<S>[^)]*?)\s*\)\s*;\s*"
        r"RE\s*\(\s*(?P<RE>[^)]*?)\s*\)\s*;\s*"
        r"RY\s*\(\s*(?P<RY>[^)]*?)\s*\)\s*[–—-]\s*"
        r"(?P<neuro>.+?)\s*[–—-]\s*"
        r"(?P<energy>.+?)\s*[–—-]\s*"
        r"(?P<intention>.+?)\s*$"
    ),
]
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").strip()
    s = s.replace("'","'").replace(""",'"').replace(""",'"')
    s = re.sub(r"\s+"," ", s)
    return s
def derive_objectif_from_groupe(g: str) -> str:
    g = (g or "").lower()
    if "reconditionnement" in g: return "reconditionnement"
    if "renforcement" in g or "tonification" in g: return "renforcement"
    if "hypertrophie" in g: return "hypertrophie"
    if "mobilité" in g or "mobilite" in g: return "mobilite"
    if "perte de masse" in g or "séchage" in g or "sechage" in g: return "perte_de_masse"
    if "endurance" in g or "cardio" in g: return "endurance_cardio"
    if "performance" in g or "intensification" in g: return "performance"
    if "santé" in g or "longevité" in g or "longévité" in g: return "sante_longevite"
    if "récupération" in g or "recuperation" in g: return "recuperation"
    if "objectif" in g: return "preparation_objectif"
    if "fonctionnel" in g: return "fonctionnel"
    if "maintenance" in g: return "maintenance"
    return "autre"
def map_niveau(n: str) -> str:
    n = (n or "").lower()
    if "débutant" in n or "debutant" in n: return "debutant"
    if "intermédiaire" in n or "intermediaire" in n: return "intermediaire"
    if "confirmé" in n or "confirme" in n: return "avance"
    return "intermediaire"
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()
def _is_rubrique_line(l: str) -> bool:
    return any(l.startswith(r) for r in RUBRIQUES)

def _is_niveau_line(l: str) -> bool:
    return any(l.strip().startswith(n) for n in NIV_MARKERS)

def _is_mc_start(l: str) -> bool:
    return bool(re.match(r"^MC\d+(?:\.\d+)?\b", l))

def _collapse(s: str) -> str:
    # Normalise espaces, tirets, apostrophes, guillemets
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("'","'").replace(""",'"').replace(""",'"')
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*[–—-]\s*", " – ", s)  # harmonise les tirets
    s = re.sub(r"\s*;\s*", "; ", s)       # spaces after semicolons
    return s.strip()

def extract_meso_records(pdf_path: Path, debug: bool = False):
    text = extract_text(str(pdf_path))
    raw_lines = [l for l in text.splitlines()]
    lines = [norm(l) for l in raw_lines if l.strip()]

    groupe = None
    niveau_bloc = None
    records = []
    candidates = []     # blocs textuels "MC…" collapsés pour debug
    unmatched = []      # blocs non matchés (pour debug)

    buffer = []
    def flush_buffer():
        if not buffer:
            return None
        joined = " ".join(buffer)
        joined = _collapse(joined)
        buffer.clear()
        return joined

    for l in lines:
        if _is_rubrique_line(l):
            # flush bloc précédent
            joined = flush_buffer()
            if joined:
                candidates.append(joined)
            groupe = l.split("–")[0].strip()
            continue

        if _is_niveau_line(l):
            # flush bloc précédent
            joined = flush_buffer()
            if joined:
                candidates.append(joined)
            niveau_bloc = next(n for n in NIV_MARKERS if l.strip().startswith(n))
            continue

        if _is_mc_start(l):
            # nouveau bloc : flush précédent
            joined = flush_buffer()
            if joined:
                candidates.append(joined)
            buffer = [l]
        else:
            # continuation de bloc MC courant ?
            if buffer:
                buffer.append(l)
            else:
                # lignes hors-bloc : ignorer
                pass

    # dernier bloc
    joined = flush_buffer()
    if joined:
       candidates.append(joined)

    # Matching
    for cand in candidates:
        mobj = None
        for PAT in MC_PATTERNS:
            mobj = PAT.match(cand)
            if mobj:
                break
        if not mobj:
            unmatched.append(cand)
            continue

        gd = mobj.groupdict()
        meso_id = norm(gd.get("id"))
        nom = norm(gd.get("nom"))
        methode = norm(gd.get("methode"))
        variables = {k: norm(gd.get(k)) for k in ["I","T","S","RE","RY"]}
        neuro = norm(gd.get("neuro"))
        energy = norm(gd.get("energy"))
        intention = norm(gd.get("intention"))

        # Contexte requis : groupe/niveau_bloc doivent avoir été vus avant
        if not groupe or not niveau_bloc:
            unmatched.append(cand)
            continue

        niveau = map_niveau(niveau_bloc or "")
        objectif = derive_objectif_from_groupe(groupe or "")
        text_summary = f"{objectif} {niveau} {methode} I:{variables['I']} T:{variables['T']} S:{variables['S']} RE:{variables['RE']} RY:{variables['RY']} – {neuro} – {energy} – {intention}"

        rec = {
            "type": "meso_ref",
            "meso_id": meso_id,
            "objectif": objectif,
            "niveau": niveau,
            "nom": nom,
            "methode": methode,
            "variables": variables,
            "sollicitation_neuromusculaire": neuro,
            "systeme_energetique": energy,
            "intention": intention,
            "groupe": groupe,
            "niveau_bloc": niveau_bloc,
            "text": text_summary,
            "source_pdf": pdf_path.name,
            # "source_hash" ajouté plus tard
        }
        records.append(rec)

    return records, unmatched, candidates
def strip_empty(d: dict):
    if isinstance(d, dict):
        return {k: strip_empty(v) for k, v in d.items() if v not in (None,"",[],{})}
    if isinstance(d, list):
        return [strip_empty(x) for x in d if x not in (None,"",[],{})]
    return d
LLM_SYSTEM_PROMPT = (
    "Tu es un post-processeur strict. "
    "Tu reçois un record JSON représentant un méso-cycle extrait par regex. "
    "Normalise UNIQUEMENT la casse et les libellés (objectif, niveau) selon les énumérations fournies. "
    "N'invente rien, ne rajoute pas de champs, ne déduis pas de valeurs. "
    "Respecte la structure cible exactement."
)
NORMALIZATION_HINT = {
    "objectif_enum": [
        "reconditionnement","renforcement","hypertrophie","mobilite",
        "perte_de_masse","endurance_cardio","performance",
        "sante_longevite","recuperation","preparation_objectif",
        "fonctionnel","maintenance","autre"
    ],
    "niveau_enum": ["debutant","intermediaire","avance"]
}
def openai_normalize(records, model_name: str):
    if not OpenAI:
        return records
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_APIKEY") or os.getenv("OPENAI_KEY"))
    out = []
    for r in records:
        payload = strip_empty(r)
        try:
            completion = client.chat.completions.create(
                model=model_name,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": LLM_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps({
                            "schema_keys": list(MESO_SCHEMA["properties"].keys()),
                            "enums": NORMALIZATION_HINT,
                            "record": payload
                        }, ensure_ascii=False)
                    },
                    {
                        "role": "user",
                        "content": (
                            "Renvoie le même record, champs identiques, "
                            "avec 'objectif' et 'niveau' mappés aux enums si besoin. "
                            "Ne supprime pas de champs présents et non vides. "
                            "Ne crée pas de nouveaux champs."
                        )
                    }
                ],
                max_tokens=400
            )
            fixed = json.loads(completion.choices[0].message.content)
            out.append(fixed)
        except Exception:
            out.append(payload)
    return out
def is_valid(record: dict) -> bool:
    try:
        Draft202012Validator(MESO_SCHEMA).validate(record)
        return True
    except Exception:
        return False
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, help="Chemin vers meso.pdf")
    parser.add_argument("--out", required=True, help="Chemin de sortie JSONL")
    parser.add_argument("--use-openai", action="store_true", help="Activer la normalisation OpenAI (strict JSON)")
    parser.add_argument("--model", default=os.getenv("LLM_MODEL","gpt-4o-mini"), help="Modèle OpenAI pour la normalisation")
    parser.add_argument("--debug", action="store_true", help="Dump lignes non matchées et échantillons de records")
    args = parser.parse_args()
    pdf_path = Path(args.pdf).resolve()
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    raw_records, unmatched, candidates = extract_meso_records(pdf_path, debug=args.debug)
    if not raw_records:
        print("Aucun meso detecte. Verifie le PDF, les reperes de rubrique/niveau, ou lance avec --debug.", file=sys.stderr)
        # continue quand même pour écrire les fichiers debug si besoin
    source_hash = sha256_file(pdf_path)
    cleaned = []
    for r in raw_records:
        r["source_hash"] = source_hash
        r = strip_empty(r)
        cleaned.append(r)
    global USE_OPENAI
    USE_OPENAI = bool(args.use_openai)
    if USE_OPENAI:
        if not OpenAI:
            print("OpenAI non disponible, normalisation ignoree.", file=sys.stderr)
        else:
            cleaned = openai_normalize(cleaned, model_name=args.model)
    
    if args.debug:
        debug_dir = Path("data2")
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / "meso_debug_unmatched.txt").write_text("\n\n---\n\n".join(unmatched), encoding="utf-8")
        sample = cleaned[: min(5, len(cleaned))]
        (debug_dir / "meso_debug_sample.json").write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Debug: {len(candidates)} blocs candidats, {len(raw_records)} matchés, {len(unmatched)} non-matchés -> data2/meso_debug_unmatched.txt", file=sys.stderr)
    
    written = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in cleaned:
            rec = strip_empty(rec)
            rec["type"] = "meso_ref"
            if is_valid(rec):
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                written += 1
    print(f"OK — {written} meso-cycles ecrits -> {out_path}")
    if written == 0:
        print("Aucun record valide ecrit. Verifie le PDF ou le regex.", file=sys.stderr)
        sys.exit(3)
if __name__ == "__main__":
    main()

