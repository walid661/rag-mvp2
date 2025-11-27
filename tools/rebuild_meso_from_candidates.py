#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, json, unicodedata
from pathlib import Path

# Séparateur: en dash (U+2013), em dash (U+2014), ou tiret simple (-)
SEP = r"\s*[–—-]\s*"
MC_HEAD = re.compile(r"^MC(?P<id>\d+\.\d+)\s*[–—-]\s*", re.UNICODE)

GROUP_TITLES = {
  1:"Reconditionnement général", 2:"Tonification & Renforcement",
  3:"Hypertrophie", 4:"Mobilité & Souplesse", 5:"Métabolique & Dépense",
  6:"Cardio & Endurance", 7:"Puissance & Explosivité", 8:"Bien-être & Vitalité",
  9:"Récupération & Respiration", 10:"Préparation spécifique",
  11:"Fonctionnel & Prévention", 12:"Maintenance & Reset",
}

def norm(s:str)->str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("'","'").replace(""",'"').replace(""",'"')
    return re.sub(r"\s+"," ", s).strip()

def infer_level(mid:str)->str:
    try:
        n=int(mid.split(".")[1])
        return "Débutant" if n<=4 else "Intermédiaire" if n<=8 else "Confirmé"
    except: return ""

def infer_group(mid:str)->str:
    try: return GROUP_TITLES.get(int(mid.split(".")[0]), "")
    except: return ""

def parse_vars(s:str)->dict:
    out={}
    for k in ["I","T","S","RE","RY"]:
        m=re.search(rf"{k}\s*\((.*?)\)", s)
        if m: out[k]=norm(m.group(1))
    return out

def split_block(line:str):
    raw = norm(line)
    m = MC_HEAD.match(raw)
    if not m: return None
    mid = m.group("id")
    rest = raw[m.end():]
    parts = re.split(SEP, rest)
    if len(parts) < 7: return None
    nom = norm(parts[0]); objectif = norm(parts[1]); methode = norm(parts[2])
    vars_block = norm(parts[3]); neuro = norm(parts[4]); energy = norm(parts[5])
    intention = norm(" – ".join(parts[6:]))
    if ";" in intention and " ;" not in intention:
        intention = intention.replace(";", " ;")
    return mid, nom, objectif, methode, vars_block, neuro, energy, intention

def main():
    src = Path("data2/meso_debug_candidates.txt").read_text(encoding="utf-8", errors="replace")
    blocks = [b.strip() for b in re.split(r"\n-{3,}\n", src) if b.strip() and b.strip().startswith("MC")]
    # Filtrer uniquement les blocs MCx.y (pas MC1 qui est un en-tête)
    blocks = [b for b in blocks if re.match(r"^MC\d+\.\d+", b)]
    out=[]
    ok=0
    for b in blocks:
        sp = split_block(b)
        if not sp: continue
        mid, nom, obj, meth, vblock, neuro, energy, intent = sp
        rec = {
          "type":"meso_ref",
          "meso_id": mid,
          "groupe": infer_group(mid),
          "niveau": infer_level(mid),
          "nom": nom,
          "objectif": obj,
          "methode": meth,
          "variables": parse_vars(vblock),
          "sollicitation_neuromusculaire": neuro,
          "systeme_energetique": energy,
          "intention": intent,
        }
        out.append(json.dumps(rec, ensure_ascii=False))
        ok+=1
    Path("data2/meso_catalog.fixed.jsonl").write_text("\n".join(out)+"\n", encoding="utf-8")
    print(f"OK={ok} -> data2/meso_catalog.fixed.jsonl")

if __name__ == "__main__":
    main()

