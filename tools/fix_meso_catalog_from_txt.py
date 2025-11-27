#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, json, argparse, unicodedata
from pathlib import Path

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("'","'").replace(""",'"').replace(""",'"')
    s = re.sub(r"\s+"," ", s).strip()
    return s

def is_rubrique_line(l: str) -> bool:
    return bool(re.match(r"^\s*\d+\.\s+", l))

def normalize_rubrique_title(line: str) -> str:
    s = unicodedata.normalize("NFKC", line or "")
    s = re.sub(r"^\s*\d+\.\s*","", s)
    s = re.sub(r"[\u2600-\u27BF\U0001F300-\U0001FAFF]", "", s)  # emoji
    return s.strip(" _-—–").strip()

NIV_SET = {"Débutant","Intermédiaire","Confirmé","Avancé","Intermediaire","Confirme","Avance"}
def is_niveau_line(l: str) -> bool:
    return any(l.strip().startswith(n) for n in NIV_SET)

def objective_from_group(g: str) -> str:
    gl = (g or "").lower()
    if "reconditionnement" in gl: return "reconditionnement"
    if "tonification" in gl or "renforcement" in gl: return "renforcement"
    if "hypertrophie" in gl: return "hypertrophie"
    if "mobilité" in gl or "mobilite" in gl: return "mobilite"
    if "perte de masse" in gl: return "perte_de_masse"
    if "endurance" in gl or "cardio" in gl: return "endurance_cardio"
    if "performance" in gl or "intensification" in gl: return "performance"
    if "santé" in gl or "longévité" in gl or "longevite" in gl: return "sante_longevite"
    if "récupération" in gl or "recuperation" in gl: return "recuperation"
    if "objectif" in gl: return "preparation_objectif"
    if "fonctionnel" in gl: return "fonctionnel"
    if "maintenance" in gl: return "maintenance"
    return "autre"

# Parse source TXT -> mapping meso_id -> (groupe, niveau, objectif)
def build_ctx_from_txt(txt_path: Path):
    raw_lines = [l for l in txt_path.read_text(encoding="utf-8").splitlines()]
    lines = [norm(l) for l in raw_lines if l.strip()]
    groupe, niveau = None, None
    buf = []
    out = {}
    def flush():
        nonlocal buf
        if not buf: return
        text = " ".join(buf); buf.clear()
        text = norm(text)
        # match id
        m = re.match(r"^MC(?P<id>\d+(?:\.\d+)?)\b", text)
        if not m: return
        meso_id = m.group("id")
        out[meso_id] = {"groupe":groupe, "niveau":niveau, "objectif": objective_from_group(groupe)}
    for l in lines:
        if re.fullmatch(r"_+", l): 
            continue
        if is_rubrique_line(l):
            flush()
            groupe = normalize_rubrique_title(l)
            continue
        if is_niveau_line(l):
            flush()
            # normalisation du label
            lv = l.strip()
            if lv.lower().startswith("intermediaire"): lv = "Intermédiaire"
            if lv.lower().startswith("confirme"): lv = "Confirmé"
            if lv.lower().startswith("avance"): lv = "Avancé"
            niveau = lv
            continue
        if re.match(r"^MC\d+(?:\.\d+)?\b", l):
            flush()
            buf = [l]
        else:
            if buf: buf.append(l)
    flush()
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--txt", required=True)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="outp", required=True)
    args = ap.parse_args()

    ctx = build_ctx_from_txt(Path(args.txt))  # e.g., {"1.1": {"groupe": "...", "niveau":"...", "objectif":"..."}}

    # corrige JSONL
    out_lines = []
    with open(args.inp, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            mid = str(obj.get("meso_id",""))
            pid = mid.replace("MC","")
            if pid in ctx:
                # remplace groupe/niveau/objectif
                true_grp = ctx[pid]["groupe"] or obj.get("groupe")
                true_niv = ctx[pid]["niveau"] or obj.get("niveau")
                true_obj = ctx[pid]["objectif"] or obj.get("objectif")
                if true_grp: obj["groupe"] = true_grp
                if true_niv: obj["niveau"] = true_niv
                if true_obj: obj["objectif"] = true_obj
            # intention : espace avant ';' si manquant
            if "intention" in obj and ";" in obj["intention"] and " ;" not in obj["intention"]:
                obj["intention"] = obj["intention"].replace(";", " ;")
            out_lines.append(json.dumps(obj, ensure_ascii=False))

    Path(args.outp).write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"OK corrections ecrites -> {args.outp} (lignes: {len(out_lines)})")

if __name__ == "__main__":
    main()

