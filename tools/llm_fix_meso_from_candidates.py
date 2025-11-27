#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lit data2/meso_debug_candidates.txt (1 bloc/MC séparé par ---),
demande à OpenAI d'extraire un JSON STRICT champ par champ, applique
les règles "groupe + niveau" d'après meso_id, et écrit data2/meso_catalog.jsonl.

Requis:
- OPENAI_API_KEY défini dans l'env (ton .env est suffisant)
- pip install openai (SDK >= 1.0)
"""
import os, re, json, unicodedata, argparse
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# ---------------- Config OpenAI ----------------
OPENAI_MODEL   = os.getenv("OPENAI_MESO_EXTRACT_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini"))
TEMPERATURE    = float(os.getenv("LLM_TEMPERATURE", "0.0"))
MAX_TOKENS_OUT = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "500"))

# -------------- Aides & règles ----------------
SEP = r"\s*[–—-]\s*"
MC_HEAD = re.compile(r"^MC(?P<id>\d+\.\d+)\s*[–—-]\s*")

GROUP_TITLES = {
  1:"Reconditionnement général", 2:"Tonification & Renforcement",
  3:"Hypertrophie", 4:"Mobilité & Souplesse", 5:"Métabolique & Dépense",
  6:"Cardio & Endurance", 7:"Puissance & Explosivité", 8:"Bien-être & Vitalité",
  9:"Récupération & Respiration", 10:"Préparation spécifique",
  11:"Fonctionnel & Prévention", 12:"Maintenance & Reset",
}

def infer_level(meso_id: str) -> str:
    try:
        n = int(meso_id.split(".")[1])
        if 1 <= n <= 4: return "Débutant"
        if 5 <= n <= 8: return "Intermédiaire"
        return "Confirmé"
    except: return ""

def infer_group(meso_id: str) -> str:
    try: return GROUP_TITLES.get(int(meso_id.split(".")[0]), "")
    except: return ""

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("'","'").replace(""",'"').replace(""",'"')
    s = re.sub(r"\s+"," ", s).strip()
    return s

SYSTEM_INSTRUCTIONS = """You extract structured data from ONE meso-cycle text block.
Return a SINGLE JSON OBJECT with EXACTLY these keys (omit missing ones; no null/empty strings):

{
  "type": "meso_ref",
  "meso_id": "1.1",                       // digits.dot.digits (no 'MC')
  "nom": "...",                           // text before the first separator
  "objectif": "...",                      // after first separator
  "methode": "...",                       // after second separator
  "variables": { "I":"...", "T":"...", "S":"...", "RE":"...", "RY":"..." }, // parsed from I(...); T(...); ...
  "sollicitation_neuromusculaire": "...", // after variables block
  "systeme_energetique": "...",           // after previous field
  "intention": "..."                      // last part
}

Rules:
- Input looks like: "MC1.5 – Nom – Objectif – Méthode – I(...); T(...); S(...); RE(...); RY(...) – Neuro – Energy – Intention".
- Keep punctuation and ranges (%, '', etc.). Trim extra spaces.
- NEVER invent content. If a field is clearly absent, OMIT THE KEY.
- "meso_id" MUST be "x.y" (no 'MC').
- Output MUST be STRICT JSON (no markdown, no comments)."""

def get_client():
    try:
        from openai import OpenAI
        return OpenAI()
    except Exception as e:
        raise RuntimeError("pip install openai (>=1.0)") from e

def llm_extract(client, raw_block: str) -> dict:
    raw_block = norm(raw_block)
    m = MC_HEAD.match(raw_block)
    if not m: return {}
    meso_id = m.group("id")
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=TEMPERATURE,
            messages=[
                {"role":"system","content": SYSTEM_INSTRUCTIONS},
                {"role":"user","content": raw_block}
            ],
            max_tokens=MAX_TOKENS_OUT,
            response_format={"type":"json_object"},
        )
        obj = json.loads(resp.choices[0].message.content)
        # Corrections minimales
        obj["type"] = "meso_ref"
        obj["meso_id"] = meso_id  # force sans 'MC'
        for k in ["nom","objectif","methode","sollicitation_neuromusculaire","systeme_energetique","intention"]:
            if k in obj and obj[k] is not None:
                obj[k] = norm(obj[k])
                if obj[k] == "": obj.pop(k, None)
        # Variables: supprimer clés vides si présentes
        if "variables" in obj and isinstance(obj["variables"], dict):
            obj["variables"] = {kk:norm(vv) for kk,vv in obj["variables"].items() if vv not in (None,"")}
            if not obj["variables"]: obj.pop("variables", None)
        return obj
    except Exception:
        return {}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", default="data2/meso_debug_candidates.txt")
    ap.add_argument("--out", dest="out_path", default="data2/meso_catalog.jsonl")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    src = Path(args.in_path)
    if not src.exists():
        raise SystemExit(f"Source introuvable: {src}")

    raw = src.read_text(encoding="utf-8", errors="replace")
    blocks = [b.strip() for b in re.split(r"\n-{3,}\n", raw) if b.strip()]
    blocks = [b for b in blocks if b.startswith("MC")]
    if args.limit > 0:
        blocks = blocks[:args.limit]

    client = get_client()
    ok, fail = 0, 0
    out_lines = []

    MUST = ["meso_id","nom","methode","sollicitation_neuromusculaire","systeme_energetique","intention"]

    for b in blocks:
        obj = llm_extract(client, b)
        if not obj:
            fail += 1
            continue

        # enrichir avec groupe/niveau si absents
        obj.setdefault("groupe", infer_group(obj["meso_id"]))
        obj.setdefault("niveau", infer_level(obj["meso_id"]))

        # prune: ne garder que l'essentiel + variables si présentes
        pruned = {
            "type": "meso_ref",
            "meso_id": obj["meso_id"],
            "groupe": obj.get("groupe"),
            "niveau": obj.get("niveau"),
            "nom": obj.get("nom"),
            "objectif": obj.get("objectif"),
            "methode": obj.get("methode"),
            "sollicitation_neuromusculaire": obj.get("sollicitation_neuromusculaire"),
            "systeme_energetique": obj.get("systeme_energetique"),
            "intention": obj.get("intention"),
        }
        if "variables" in obj:
            pruned["variables"] = obj["variables"]

        # validations minimales
        if any(pruned.get(k) in (None,"") for k in MUST):
            fail += 1
            continue
        if pruned.get("groupe") in (None,""): pruned["groupe"] = infer_group(pruned["meso_id"])
        if pruned.get("niveau") in (None,""): pruned["niveau"] = infer_level(pruned["meso_id"])

        out_lines.append(json.dumps(pruned, ensure_ascii=False))
        ok += 1

    Path(args.out_path).write_text("\n".join(out_lines)+("\n" if out_lines else ""), encoding="utf-8")
    print(f"OK: {ok} | FAIL: {fail} | -> {args.out_path}")

if __name__ == "__main__":
    main()

