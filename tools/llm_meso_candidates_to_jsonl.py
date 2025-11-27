#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convertit data2/meso_debug_candidates.txt -> data2/meso_catalog.jsonl
en s'appuyant sur OpenAI pour l'extraction robuste champ par champ.

Prérequis:
- OPENAI_API_KEY dans l'environnement (.env déjà présent)
- Fichier source: data2/meso_debug_candidates.txt (séparateur: lignes '---')

Sortie:
- data2/meso_catalog.jsonl (1 objet JSON par ligne, sans champs inutiles/vides)
"""

import os, json, re, unicodedata, argparse
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# --- Paramètres modèles ---
OPENAI_MODEL = os.getenv("OPENAI_MESO_EXTRACT_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini"))
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
MAX_TOKENS  = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "500"))

# --- Mapping des groupes (rubriques haut-niveau) par préfixe MCx ---
# Ajustable facilement si tu veux des libellés différents.
GROUP_TITLES = {
  1: "Reconditionnement général",
  2: "Tonification & Renforcement",
  3: "Hypertrophie",
  4: "Mobilité & Souplesse",
  5: "Métabolique & Dépense",
  6: "Cardio & Endurance",
  7: "Puissance & Explosivité",
  8: "Bien-être & Vitalité",
  9: "Récupération & Respiration",
  10: "Préparation spécifique",
  11: "Fonctionnel & Prévention",
  12: "Maintenance & Reset",
}

def infer_level(meso_id: str) -> str:
    """
    Règle simple conforme au PDF:
      .1-.4   -> Débutant
      .5-.8   -> Intermédiaire
      .9-.12  -> Confirmé
    """
    try:
        main, sub = meso_id.split(".")
        n = int(sub)
        if 1 <= n <= 4:
            return "Débutant"
        if 5 <= n <= 8:
            return "Intermédiaire"
        return "Confirmé"
    except Exception:
        return ""

def infer_group(meso_id: str) -> str:
    try:
        main = int(meso_id.split(".")[0])
        return GROUP_TITLES.get(main, "")
    except Exception:
        return ""

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("'","'").replace(""",'"').replace(""",'"')
    s = re.sub(r"\s+"," ", s).strip()
    return s

SYSTEM_INSTRUCTIONS = """You extract structured data from one meso-cycle text block.
Return a SINGLE compact JSON object with these keys only (no null/empty):
{
  "type": "meso_ref",
  "meso_id": "1.1",                # ex: "1.1" (no 'MC' prefix)
  "nom": "...",                    # the meso cycle name/title before the first ' – '
  "objectif": "...",               # the goal after the first separator
  "methode": "...",                # training method after the second separator
  "variables": {                   # parsed from I(...);T(...);S(...);RE(...);RY(...)
     "I": "...", "T": "...", "S": "...", "RE": "...", "RY": "..."
  },
  "sollicitation_neuromusculaire": "...",  # text after variables block
  "systeme_energetique": "...",            # energy system after previous field
  "intention": "..."                        # final pedagogical intention/sentence
}
Notes:
- Input is a single-line block like "MC1.1 – Nom – Objectif – Méthode – I(...); T(...); S(...); RE(...); RY(...) – Neuro – Energy – Intention".
- Keep punctuation and ranges (%, '', etc.) but remove extra spaces.
- NEVER invent content; if something is clearly missing, set that key absent (DO NOT return empty strings).
- "meso_id" MUST be digits-dot-digits (e.g., "1.1") without "MC".
- Output must be STRICT JSON, no code fences, no comments.
"""

# OpenAI client (new SDK)
def get_client():
    try:
        from openai import OpenAI
        return OpenAI()
    except Exception as e:
        raise RuntimeError("openai package (>=1.0) is required. pip install openai") from e

def llm_extract_one_block(client, text_block: str) -> dict:
    """
    Appelle le LLM pour extraire les champs. Renvoie {} si parsing impossible.
    """
    text_block = norm(text_block)
    # quick sanity: doit commencer par MCx.y
    m = re.match(r"^MC(\d+\.\d+)\s*[–—-]\s*", text_block)
    if not m:
        return {}
    meso_id = m.group(1)  # "x.y"
    # Envoie le bloc brut au modèle
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=TEMPERATURE,
            messages=[
                {"role":"system","content": SYSTEM_INSTRUCTIONS},
                {"role":"user","content": text_block}
            ],
            max_tokens=MAX_TOKENS,
            response_format={"type":"json_object"},
        )
        content = resp.choices[0].message.content
        obj = json.loads(content)
        # Validations minimales
        if obj.get("type") != "meso_ref": obj["type"] = "meso_ref"
        if obj.get("meso_id") != meso_id:
            # rattrapage si le modèle a mis "MCx.y"
            obj["meso_id"] = meso_id
        # Variables: s'assure uniquement des clés présentes
        if "variables" in obj:
            for k in ["I","T","S","RE","RY"]:
                if k in obj["variables"] and (obj["variables"][k] is None or obj["variables"][k]=="" ):
                    obj["variables"].pop(k, None)
            if not obj["variables"]:
                obj.pop("variables", None)
        # Normalisation légère
        for k in ["nom","objectif","methode","sollicitation_neuromusculaire","systeme_energetique","intention"]:
            if k in obj: obj[k] = norm(obj[k])
        return obj
    except Exception:
        return {}

def post_enrich(obj: dict) -> dict:
    """
    Ajoute groupe + niveau (déduits de meso_id).
    Ne crée PAS de champs vides ; ne touche pas aux champs déjà fournis par le modèle.
    """
    mid = obj.get("meso_id","")
    if mid:
        obj.setdefault("groupe", infer_group(mid))
        obj.setdefault("niveau", infer_level(mid))
    return obj

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", default="data2/meso_debug_candidates.txt")
    ap.add_argument("--out", dest="out_path", default="data2/meso_catalog.jsonl")
    ap.add_argument("--limit", type=int, default=0, help="Limiter le nb de blocs pour test (0 = tous)")
    args = ap.parse_args()

    src = Path(args.in_path)
    if not src.exists():
        raise SystemExit(f"Source introuvable: {src}")

    raw = src.read_text(encoding="utf-8", errors="replace")
    # On split sur lignes '---' (isolées) – le fichier est déjà formaté ainsi
    blocks = [b.strip() for b in re.split(r"\n-{3,}\n", raw) if b.strip()]
    # Retire le tout premier bloc de description s'il ne commence pas par MC
    blocks = [b for b in blocks if b.startswith("MC")]
    if args.limit > 0:
        blocks = blocks[:args.limit]

    client = get_client()
    out_lines = []
    ok, fail = 0, 0

    for b in blocks:
        obj = llm_extract_one_block(client, b)
        if not obj:
            fail += 1
            continue
        obj = post_enrich(obj)
        # On garde uniquement les champs utiles (et non vides)
        pruned = {
            "type": "meso_ref",
            "meso_id": obj.get("meso_id"),
            "groupe": obj.get("groupe"),
            "niveau": obj.get("niveau"),
        }
        # Champs essentiels si présents
        for k in ["nom","objectif","methode","variables","sollicitation_neuromusculaire","systeme_energetique","intention"]:
            if k in obj and obj[k] not in (None,"",{}):
                pruned[k] = obj[k]

        # Sécurité: must-have
        must = ["meso_id","groupe","niveau","nom","methode","sollicitation_neuromusculaire","systeme_energetique","intention"]
        if any(pruned.get(m) in (None,"") for m in must):
            fail += 1
            continue

        out_lines.append(json.dumps(pruned, ensure_ascii=False))
        ok += 1

    Path(args.out_path).write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
    print(f"OK: {ok} | FAIL: {fail} | -> {args.out_path}")

if __name__ == "__main__":
    main()





