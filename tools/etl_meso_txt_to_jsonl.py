#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETL: meso.txt -> meso_catalog.jsonl
- Entrée: texte brut exporté du PDF, placé en data/raw/meso.txt
- Sortie: JSONL minimal, exploitable par le RAG (1 méso-cycle / ligne)
- Zéro dépendance externe (std lib)
- Tolérant aux multi-lignes, tirets – — -, espaces, ; optionnels
- Ecrit un fichier debug des blocs non matchés si --debug
"""
import re, json, argparse, unicodedata
from pathlib import Path

RUBRIQUES = [
    "Reconditionnement général","Tonification et Renforcement","Hypertrophie structurelle",
    "Mobilité","Perte de masse grasse","Endurance & capacité cardio",
    "Performance & intensification","Santé & longévité active",
    "Préparation mentale & récupération","Préparation à un objectif",
    "Entraînement fonctionnel polyvalent","Routine de maintenance",
]
NIV_MARKERS = ["Débutant","Intermédiaire","Confirmé"]

def norm(s:str)->str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("'","'").replace(""",'"').replace(""",'"')
    s = re.sub(r"\s+"," ", s)
    return s.strip()

def map_niveau(n:str)->str:
    n = (n or "").lower()
    if "débutant" in n or "debutant" in n: return "debutant"
    if "intermédiaire" in n or "intermediaire" in n: return "intermediaire"
    if "confirmé" in n or "confirme" in n: return "avance"
    return "intermediaire"

def derive_objectif_from_groupe(g: str) -> str:
    g = (g or "").lower()
    if "reconditionnement" in g: return "reconditionnement"
    if "renforcement" in g or "tonification" in g: return "renforcement"
    if "hypertrophie" in g: return "hypertrophie"
    if "mobilité" in g or "mobilite" in g: return "mobilite"
    if "perte de masse" in g: return "perte_de_masse"
    if "endurance" in g or "cardio" in g: return "endurance_cardio"
    if "performance" in g or "intensification" in g: return "performance"
    if "santé" in g or "longévité" in g or "longevité" in g: return "sante_longevite"
    if "récupération" in g or "recuperation" in g: return "recuperation"
    if "objectif" in g: return "preparation_objectif"
    if "fonctionnel" in g: return "fonctionnel"
    if "maintenance" in g: return "maintenance"
    return "autre"

# Patterns plus souples (tirets – — -, espaces, ; optionnels)
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
    re.compile(
        r"^(MC(?P<id>\d+(?:\.\d+)?))\s*[–—-]\s*"
        r"(?P<nom>.+?)\s*[–—-]\s*"
        r"(?P<methode>.+?)\s*[–—-]\s*"
        r"I\s*\(\s*(?P<I>[^)]*?)\s*\)\s*;\s*"
        r"T\s*\(\s*(?P<T>[^)]*?)\s*\)\s*;\s*"
        r"S\s*\(\s*(?P<S>[^)]*?)\s*\)\s*;\s*"
        r"RE\s*\(\s*(?P<RE>[^)]*?)\s*\)\s*;\s*"
        r"RY\s*\(\s*(?P<RY>[^)]*?)\s*\)\s*(?:[–—-]\s*)?"
        r"(?P<neuro>.+?)\s*[–—-]\s*"
        r"(?P<energy>.+?)\s*[–—-]\s*"
        r"(?P<intention>.+?)\s*$"
    ),
]

def collapse_block(lines:list[str])->str:
    joined = " ".join(lines)
    joined = unicodedata.normalize("NFKC", joined)
    joined = re.sub(r"\s*[–—-]\s*"," – ", joined)
    joined = re.sub(r"\s*;\s*","; ", joined)
    joined = re.sub(r"\s+"," ", joined)
    return joined.strip()

def parse_txt(txt_path:Path, debug=False):
    raw = txt_path.read_text(encoding="utf-8", errors="ignore")
    lines = [l for l in raw.splitlines() if l.strip()]
    lines = [norm(l) for l in lines]

    groupe = None
    niveau_bloc = None
    records = []
    candidates = []
    unmatched = []

    buf = []
    def flush():
        nonlocal buf
        if not buf: return None
        c = collapse_block(buf)
        buf = []
        return c

    def is_mc_start(l:str): return re.match(r"^MC\d+(?:\.\d+)?\b", l) is not None
    def is_rubrique(l:str): return any(l.startswith(r) for r in RUBRIQUES)
    def is_niveau(l:str): return any(l.strip().startswith(n) for n in NIV_MARKERS)

    for l in lines:
        if is_rubrique(l):
            j = flush()
            if j: candidates.append(j)
            groupe = l.split("–")[0].strip()
            continue
        if is_niveau(l):
            j = flush()
            if j: candidates.append(j)
            niveau_bloc = next(n for n in NIV_MARKERS if l.strip().startswith(n))
            continue
        if is_mc_start(l):
            j = flush()
            if j: candidates.append(j)
            buf = [l]
        else:
            if buf: buf.append(l)

    j = flush()
    if j: candidates.append(j)

    for cand in candidates:
        mobj = None
        for pat in MC_PATTERNS:
            mobj = pat.match(cand)
            if mobj: break
        if not mobj:
            unmatched.append(cand)
            continue
        if not groupe or not niveau_bloc:
            unmatched.append(cand)
            continue

        gd = mobj.groupdict()
        variables = {k: norm(gd.get(k)) for k in ["I","T","S","RE","RY"]}
        niveau = map_niveau(niveau_bloc)
        objectif = derive_objectif_from_groupe(groupe)
        rec = {
            "type":"meso_ref",
            "meso_id": norm(gd.get("id")),
            "objectif": objectif,
            "niveau": niveau,
            "nom": norm(gd.get("nom")),
            "methode": norm(gd.get("methode")),
            "variables": variables,
            "sollicitation_neuromusculaire": norm(gd.get("neuro")),
            "systeme_energetique": norm(gd.get("energy")),
            "intention": norm(gd.get("intention")),
            "groupe": groupe,
            "niveau_bloc": niveau_bloc,
            "text": f"{objectif} {niveau} {norm(gd.get('methode'))} I:{variables['I']} T:{variables['T']} S:{variables['S']} RE:{variables['RE']} RY:{variables['RY']} – {norm(gd.get('neuro'))} – {norm(gd.get('energy'))} – {norm(gd.get('intention'))}"
        }
        records.append(rec)

    if debug:
        dbg_dir = Path("data2"); dbg_dir.mkdir(parents=True, exist_ok=True)
        (dbg_dir/"meso_debug_unmatched.txt").write_text("\n\n---\n\n".join(unmatched), encoding="utf-8")
        (dbg_dir / "meso_debug_candidates.txt").write_text("\n\n---\n\n".join(candidates), encoding="utf-8")
        import sys
        print(f"Debug: {len(candidates)} blocs candidats, {len(records)} matchés, {len(unmatched)} non-matchés", file=sys.stderr)

    return records

def strip_empty(d):
    if isinstance(d, dict):
        return {k: strip_empty(v) for k,v in d.items() if v not in (None,"",[],{})}
    if isinstance(d, list):
        return [strip_empty(x) for x in d if x not in (None,"",[],{})]
    return d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--txt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    txt_path = Path(args.txt)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    recs = parse_txt(txt_path, debug=args.debug)
    if not recs:
        print("Aucun meso detecte. Verifie le TXT (titres rubriques, niveaux, blocs MC...).")

    wrote = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for r in recs:
            r = strip_empty(r)
            needed = ["type","meso_id","objectif","niveau","nom","methode","variables","sollicitation_neuromusculaire","systeme_energetique","intention","groupe","niveau_bloc","text"]
            if all(k in r for k in needed) and all(r[k] for k in needed):
                f.write(json.dumps(r, ensure_ascii=False)+"\n")
                wrote += 1
    print(f"OK — {wrote} meso-cycles ecrits -> {out_path}")

if __name__ == "__main__":
    main()

