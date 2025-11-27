#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, json, unicodedata, argparse
from pathlib import Path

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("'","'").replace(""",'"').replace(""",'"')
    s = re.sub(r"\s+"," ", s).strip()
    return s

# Détection rubriques, niveaux et MC en une ligne (format du TXT)
RUB_RE = re.compile(r"^\s*\d+\.\s*(.+)$")
NIV_RE = re.compile(r"^\s*(Débutant|Intermédiaire|Confirmé)\s*$", re.IGNORECASE)
# Pattern flexible : accepte avec ou sans champ "objectif" explicite
MC_RE_WITH_OBJ = re.compile(
    r"^\s*(MC(?P<id>\d+\.\d+))\s*[–—-]\s*(?P<nom>.+?)\s*[–—-]\s*(?P<objectif>.+?)\s*[–—-]\s*(?P<methode>.+?)\s*[–—-]\s*(?P<vars>.+?)\s*[–—-]\s*(?P<neuro>.+?)\s*[–—-]\s*(?P<energy>.+?)\s*[–—-]\s*(?P<intention>.+?)\s*$"
)
# Pattern pour capturer les variables jusqu'au prochain tiret (en évitant les tirets dans les parenthèses)
# On utilise un lookahead pour s'arrêter au prochain " – " suivi d'un mot (pas dans une parenthèse)
MC_RE_WITHOUT_OBJ = re.compile(
    r"^\s*(MC(?P<id>\d+\.\d+))\s*[–—-]\s*(?P<nom>.+?)\s*[–—-]\s*(?P<methode>.+?)\s*[–—-]\s*(?P<vars>.+?)\s*[–—-]\s*(?P<neuro>.+?)\s*[–—-]\s*(?P<energy>.+?)\s*[–—-]\s*(?P<intention>.+?)\s*$"
)

def parse_txt_truth(txt_path: Path):
    truth = {}  # "MC1.1" -> dict(fields)
    cur_group, cur_level = None, None

    raw_lines = [l for l in txt_path.read_text(encoding="utf-8", errors="replace").splitlines()]
    lines = [norm(l) for l in raw_lines if norm(l)]

    buf = []
    
    def flush_buffer():
        nonlocal buf
        if not buf:
            return None
        joined = " ".join(buf)
        buf.clear()
        return norm(joined)
    
    def is_mc_start(ln: str) -> bool:
        return bool(re.match(r"^MC\d+\.\d+", ln))
    
    for ln in lines:
        if re.fullmatch(r"_+", ln):  # barres de séparation
            continue
        
        m_r = RUB_RE.match(ln)
        if m_r:
            # flush buffer avant nouvelle rubrique
            block = flush_buffer()
            if block:
                # traiter le bloc MC précédent
                m_mc = MC_RE_WITH_OBJ.match(block) or MC_RE_WITHOUT_OBJ.match(block)
                if m_mc:
                    gd = m_mc.groupdict()
                    mid = gd["id"]
                    vars_str = gd["vars"]
                    var_map = {}
                    for k in ["I","T","S","RE","RY"]:
                        mv = re.search(rf"{k}\s*\((.*?)\)", vars_str)
                        if mv: var_map[k] = norm(mv.group(1))
                    # objectif peut être absent, on le dérive du groupe si nécessaire
                    obj = norm(gd.get("objectif", ""))
                    if not obj and cur_group:
                        # dériver objectif du groupe
                        gl = (cur_group or "").lower()
                        if "reconditionnement" in gl: obj = "reconditionnement"
                        elif "tonification" in gl or "renforcement" in gl: obj = "renforcement"
                        elif "hypertrophie" in gl: obj = "hypertrophie"
                        elif "mobilité" in gl or "mobilite" in gl: obj = "mobilite"
                        elif "perte de masse" in gl: obj = "perte_de_masse"
                        elif "endurance" in gl or "cardio" in gl: obj = "endurance_cardio"
                        elif "performance" in gl or "intensification" in gl: obj = "performance"
                        elif "santé" in gl or "longévité" in gl or "longevite" in gl: obj = "sante_longevite"
                        elif "récupération" in gl or "recuperation" in gl: obj = "recuperation"
                        elif "objectif" in gl: obj = "preparation_objectif"
                        elif "fonctionnel" in gl: obj = "fonctionnel"
                        elif "maintenance" in gl: obj = "maintenance"
                        else: obj = "autre"
                    truth[f"MC{mid}"] = {
                        "groupe": cur_group,
                        "niveau": cur_level,
                        "nom": norm(gd["nom"]),
                        "objectif": obj,
                        "methode": norm(gd["methode"]),
                        "variables": var_map,
                        "neuro": norm(gd["neuro"]),
                        "energy": norm(gd["energy"]),
                        "intention": norm(gd["intention"]),
                    }
            # extrait le titre de rubrique sans emojis
            g = re.sub(r"[\u2600-\u27BF\U0001F300-\U0001FAFF]", "", m_r.group(1)).strip(" -—–_")
            cur_group = g
            continue
        
        m_n = NIV_RE.match(ln)
        if m_n:
            # flush buffer avant nouveau niveau
            block = flush_buffer()
            if block:
                m_mc = MC_RE_WITH_OBJ.match(block) or MC_RE_WITHOUT_OBJ.match(block)
                if m_mc:
                    gd = m_mc.groupdict()
                    mid = gd["id"]
                    vars_str = gd["vars"]
                    var_map = {}
                    for k in ["I","T","S","RE","RY"]:
                        mv = re.search(rf"{k}\s*\((.*?)\)", vars_str)
                        if mv: var_map[k] = norm(mv.group(1))
                    obj = norm(gd.get("objectif", ""))
                    if not obj and cur_group:
                        gl = (cur_group or "").lower()
                        if "reconditionnement" in gl: obj = "reconditionnement"
                        elif "tonification" in gl or "renforcement" in gl: obj = "renforcement"
                        elif "hypertrophie" in gl: obj = "hypertrophie"
                        elif "mobilité" in gl or "mobilite" in gl: obj = "mobilite"
                        elif "perte de masse" in gl: obj = "perte_de_masse"
                        elif "endurance" in gl or "cardio" in gl: obj = "endurance_cardio"
                        elif "performance" in gl or "intensification" in gl: obj = "performance"
                        elif "santé" in gl or "longévité" in gl or "longevite" in gl: obj = "sante_longevite"
                        elif "récupération" in gl or "recuperation" in gl: obj = "recuperation"
                        elif "objectif" in gl: obj = "preparation_objectif"
                        elif "fonctionnel" in gl: obj = "fonctionnel"
                        elif "maintenance" in gl: obj = "maintenance"
                        else: obj = "autre"
                    truth[f"MC{mid}"] = {
                        "groupe": cur_group,
                        "niveau": cur_level,
                        "nom": norm(gd["nom"]),
                        "objectif": obj,
                        "methode": norm(gd["methode"]),
                        "variables": var_map,
                        "neuro": norm(gd["neuro"]),
                        "energy": norm(gd["energy"]),
                        "intention": norm(gd["intention"]),
                    }
            cur_level = m_n.group(1).capitalize()
            continue
        
        if is_mc_start(ln):
            # flush buffer avant nouveau MC
            block = flush_buffer()
            if block:
                m_mc = MC_RE_WITH_OBJ.match(block) or MC_RE_WITHOUT_OBJ.match(block)
                if m_mc:
                    gd = m_mc.groupdict()
                    mid = gd["id"]
                    vars_str = gd["vars"]
                    var_map = {}
                    for k in ["I","T","S","RE","RY"]:
                        mv = re.search(rf"{k}\s*\((.*?)\)", vars_str)
                        if mv: var_map[k] = norm(mv.group(1))
                    obj = norm(gd.get("objectif", ""))
                    if not obj and cur_group:
                        gl = (cur_group or "").lower()
                        if "reconditionnement" in gl: obj = "reconditionnement"
                        elif "tonification" in gl or "renforcement" in gl: obj = "renforcement"
                        elif "hypertrophie" in gl: obj = "hypertrophie"
                        elif "mobilité" in gl or "mobilite" in gl: obj = "mobilite"
                        elif "perte de masse" in gl: obj = "perte_de_masse"
                        elif "endurance" in gl or "cardio" in gl: obj = "endurance_cardio"
                        elif "performance" in gl or "intensification" in gl: obj = "performance"
                        elif "santé" in gl or "longévité" in gl or "longevite" in gl: obj = "sante_longevite"
                        elif "récupération" in gl or "recuperation" in gl: obj = "recuperation"
                        elif "objectif" in gl: obj = "preparation_objectif"
                        elif "fonctionnel" in gl: obj = "fonctionnel"
                        elif "maintenance" in gl: obj = "maintenance"
                        else: obj = "autre"
                    truth[f"MC{mid}"] = {
                        "groupe": cur_group,
                        "niveau": cur_level,
                        "nom": norm(gd["nom"]),
                        "objectif": obj,
                        "methode": norm(gd["methode"]),
                        "variables": var_map,
                        "neuro": norm(gd["neuro"]),
                        "energy": norm(gd["energy"]),
                        "intention": norm(gd["intention"]),
                    }
            buf = [ln]
        else:
            if buf:
                buf.append(ln)
    
    # flush dernier buffer
    block = flush_buffer()
    if block:
        m_mc = MC_RE_WITH_OBJ.match(block) or MC_RE_WITHOUT_OBJ.match(block)
        if m_mc:
            gd = m_mc.groupdict()
            mid = gd["id"]
            vars_str = gd["vars"]
            var_map = {}
            for k in ["I","T","S","RE","RY"]:
                mv = re.search(rf"{k}\s*\((.*?)\)", vars_str)
                if mv: var_map[k] = norm(mv.group(1))
            obj = norm(gd.get("objectif", ""))
            if not obj and cur_group:
                gl = (cur_group or "").lower()
                if "reconditionnement" in gl: obj = "reconditionnement"
                elif "tonification" in gl or "renforcement" in gl: obj = "renforcement"
                elif "hypertrophie" in gl: obj = "hypertrophie"
                elif "mobilité" in gl or "mobilite" in gl: obj = "mobilite"
                elif "perte de masse" in gl: obj = "perte_de_masse"
                elif "endurance" in gl or "cardio" in gl: obj = "endurance_cardio"
                elif "performance" in gl or "intensification" in gl: obj = "performance"
                elif "santé" in gl or "longévité" in gl or "longevite" in gl: obj = "sante_longevite"
                elif "récupération" in gl or "recuperation" in gl: obj = "recuperation"
                elif "objectif" in gl: obj = "preparation_objectif"
                elif "fonctionnel" in gl: obj = "fonctionnel"
                elif "maintenance" in gl: obj = "maintenance"
                else: obj = "autre"
            truth[f"MC{mid}"] = {
                "groupe": cur_group,
                "niveau": cur_level,
                "nom": norm(gd["nom"]),
                "objectif": obj,
                "methode": norm(gd["methode"]),
                "variables": var_map,
                "neuro": norm(gd["neuro"]),
                "energy": norm(gd["energy"]),
                "intention": norm(gd["intention"]),
            }
    
    return truth

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--txt", required=True)   # data/raw/meso.txt
    ap.add_argument("--in-jsonl", required=True)  # data2/meso_catalog.jsonl
    ap.add_argument("--out-jsonl", required=True) # data2/meso_catalog.fixed.jsonl
    args = ap.parse_args()

    truth = parse_txt_truth(Path(args.txt))
    src_lines = Path(args.in_jsonl).read_text(encoding="utf-8").splitlines()

    out = []
    fixed, total = 0, 0
    for line in src_lines:
        if not line.strip():
            continue
        obj = json.loads(line)
        total += 1
        mid = obj.get("meso_id")
        # tolère "1.1" vs "MC1.1"
        key = mid if isinstance(mid, str) and mid.startswith("MC") else f"MC{mid}"

        if key in truth:
            t = truth[key]
            # Remplacer les champs par la vérité source
            obj["groupe"] = t["groupe"]
            obj["niveau"] = t["niveau"]
            obj["nom"] = t["nom"]
            obj["objectif"] = t["objectif"]
            obj["methode"] = t["methode"]
            obj["variables"] = t["variables"]
            obj["sollicitation_neuromusculaire"] = t["neuro"]
            obj["systeme_energetique"] = t["energy"]
            # Normalise ponctuation de l'intention
            intent = t["intention"]
            if ";" in intent and " ;" not in intent:
                intent = intent.replace(";", " ;")
            obj["intention"] = intent
            fixed += 1

            # (optionnel) régénérer "text" compact pour embedding
            v = obj["variables"]
            text = f"{obj['groupe']} – {obj['niveau']} – {obj['methode']} – I:{v.get('I','')} T:{v.get('T','')} S:{v.get('S','')} RE:{v.get('RE','')} RY:{v.get('RY','')} – {obj['sollicitation_neuromusculaire']} – {obj['systeme_energetique']} – {obj['intention']}"
            obj["text"] = norm(text)

        out.append(json.dumps(obj, ensure_ascii=False))

    Path(args.out_jsonl).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"OK reconciled: {fixed}/{total} rows from source {args.txt}")
    print(f"-> {args.out_jsonl}")

if __name__ == "__main__":
    main()

