#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ajoute un champ 'text' en français naturel à chaque enregistrement meso_ref du JSONL,
sans modifier les autres champs. Utilise OpenAI pour formuler proprement.
- Lit:      data2/meso_catalog.jsonl
- Sauvegarde une copie: data2/meso_catalog.jsonl.bak
- Écrit:    data2/meso_catalog.jsonl (enrichi)

Requiert:
- OPENAI_API_KEY dans l'environnement (.env accepté)
- pip install openai python-dotenv
"""
import os, re, json, math, unicodedata, sys
from pathlib import Path

# Charger .env si présent
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# OpenAI SDK v1
try:
    from openai import OpenAI
except Exception as e:
    print("Le package 'openai' v1 est requis: pip install openai python-dotenv", file=sys.stderr)
    raise

MODEL = os.getenv("LLM_MODEL_FOR_TEXT", os.getenv("LLM_MODEL", "gpt-4o-mini"))
API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_APIKEY") or os.getenv("OPENAI_KEY")
if not API_KEY:
    print("ERREUR: OPENAI_API_KEY manquant (mets la clé dans .env)", file=sys.stderr)
    sys.exit(1)

client = OpenAI(api_key=API_KEY)

SRC = Path("data2/meso_catalog.jsonl")
BAK = Path("data2/meso_catalog.jsonl.bak")
DST = Path("data2/meso_catalog.jsonl")

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("'","'").replace(""",'"').replace(""",'"')
    s = re.sub(r"\s+"," ", s).strip()
    return s

def parse_percent_any(s: str) -> float | None:
    """Renvoie un pourcentage moyen s'il y a '20 – 30%' ou '70 %', sinon None."""
    if not s: return None
    # capturer intervalles '20 – 30%' / '20-30 %'
    m = re.findall(r"(\d{1,3})\s*[–\-]\s*(\d{1,3})\s*%", s)
    if m:
        a,b = map(int, m[0])
        return (a+b)/2
    # simple '70 %' ou '70%'
    m = re.search(r"(\d{1,3})\s*%", s)
    if m:
        return float(m.group(1))
    return None

def intensity_label(I: str) -> str:
    """Mappe I -> difficulté lisible."""
    I = (I or "").lower()
    # cas verbaux
    if any(k in I for k in ["autocharg", "amplitude libre", "mobilité active", "gainage au poids du corps", "poids du corps"]):
        # autochargé = bas/contrôlé
        return "très faible à faible (autochargé / amplitude libre)"
    if any(k in I for k in ["élastique léger", "elastique leger", "charge légère", "charge legere"]):
        return "faible (charge légère/élastique)"
    # pourcentages
    p = parse_percent_any(I)
    if p is None:
        return "variable/contrôlée" if I else "non précisée"
    if p <= 30:  return f"{p:.0f}% — très faible"
    if p <= 50:  return f"{p:.0f}% — faible"
    if p <= 65:  return f"{p:.0f}% — modérée"
    if p <= 80:  return f"{p:.0f}% — soutenue"
    if p <= 90:  return f"{p:.0f}% — élevée"
    return f"{p:.0f}% — maximale"

def tempo_label(ry: str) -> str:
    ry = (ry or "").lower()
    if "lent" in ry or "maîtrisé" in ry or "maitrise" in ry: return "tempo lent et maîtrisé"
    if "moderato" in ry: return "tempo modéré (moderato)"
    if "soutenu" in ry: return "tempo soutenu"
    if "explosif" in ry: return "tempo explosif"
    return ry or "tempo non précisé"

def build_llm_prompt(rec: dict) -> str:
    """
    On donne au LLM toutes les infos + des dérivés calculés (étiquette d'intensité),
    et on lui demande un paragraphe FR concis (3–5 phrases) en langue humaine.
    """
    I = (rec.get("variables") or {}).get("I", "")
    T = (rec.get("variables") or {}).get("T", "")
    S = (rec.get("variables") or {}).get("S", "")
    REp = (rec.get("variables") or {}).get("RE", "")
    RY = (rec.get("variables") or {}).get("RY", "")

    diff = intensity_label(I)
    tempo = tempo_label(RY)

    # Certains jeux de données ont "nom" (ancienne version) ou "titre/sous_titre" (version v2).
    nom = rec.get("nom")
    if not nom:
        titre = rec.get("titre","")
        sous = rec.get("sous_titre")
        nom = f"{titre}{' : '+sous if sous else ''}"

    bloc = {
        "meso_id": rec.get("meso_id"),
        "groupe": rec.get("groupe"),
        "niveau": rec.get("niveau"),
        "nom": nom,
        "methode": rec.get("methode"),
        "variables": {"intensite": I, "repos": T, "series": S, "repetitions": REp, "tempo": RY},
        "derives": {"difficulte_estimee": diff, "tempo_label": tempo},
        "sollicitation_neuromusculaire": rec.get("sollicitation_neuromusculaire"),
        "systeme_energetique": rec.get("systeme_energetique"),
        "intention": rec.get("intention"),
    }

    return (
        "Rédige un court texte en FR (3–5 phrases), sans jargon I/T/S/RE/RY.\n"
        "Transforme les variables en langage naturel (intensité, séries, répétitions, temps de repos, tempo).\n"
        "Conserve les chiffres (durées, reps), mais exprime l'intensité avec l'étiquette fournie ('difficulte_estimee').\n"
        "Mentionne brièvement la méthode, la sollicitation neuromusculaire, le système énergétique et l'intention pédagogique.\n"
        "Ton : clair, coach sportif.\n"
        "IMPORTANT:\n"
        "- Utilise des espaces après les point-virgules (; ) pour la ponctuation française.\n"
        "- Si les répétitions sont spécifiques 'par exercice' ou 'par exo', garde cette précision dans le texte.\n"
        "- Structure type: 'Réalisez S séries de RE répétitions, avec T de repos, à un tempo...'\n"
        "- Mentionne l'intensité avec l'étiquette fournie (ex: 'très faible à faible', 'modérée', etc.).\n\n"
        f"DONNÉES:\n{json.dumps(bloc, ensure_ascii=False)}"
    )

def llm_summarize(rec: dict) -> str:
    prompt = build_llm_prompt(rec)
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        max_tokens=220,
        messages=[
            {"role":"system","content":"Tu es un coach sportif francophone. Tu écris des synthèses claires et concises."},
            {"role":"user","content": prompt}
        ]
    )
    txt = resp.choices[0].message.content.strip()
    # nettoyage doux
    txt = norm(txt)
    # éviter de réintroduire 'I(' etc.
    txt = re.sub(r"\bI\(|\bT\(|\bS\(|\bRE\(|\bRY\(", "", txt)
    # Corriger la ponctuation FR : point-virgule sans espace -> avec espace
    txt = re.sub(r";([^ ])", r"; \1", txt)
    return txt

def main():
    if not SRC.exists():
        print(f"ERREUR: Introuvable: {SRC}", file=sys.stderr)
        sys.exit(1)

    lines = [l for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
    BAK.write_text("\n".join(lines) + "\n", encoding="utf-8")

    out = []
    for i, line in enumerate(lines, 1):
        obj = json.loads(line)
        if obj.get("type") != "meso_ref":
            out.append(line)  # on ne touche pas les autres types
            continue

        # si déjà enrichi, on laisse (ou on force si REGENERATE=1)
        if "text" in obj and not os.getenv("REGENERATE", "0") == "1":
            out.append(json.dumps(obj, ensure_ascii=False))
            continue

        try:
            txt = llm_summarize(obj)
            obj["text"] = txt
        except Exception as e:
            # en cas d'échec, on met un text minimal
            obj["text"] = f"{obj.get('groupe','')} — {obj.get('niveau','')}: {obj.get('methode','')}"
        out.append(json.dumps(obj, ensure_ascii=False))

        if i % 20 == 0:
            print(f"… enrichis {i} lignes")

    DST.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"OK Enrichissement termine. Sauvegarde: {BAK} | Mis a jour: {DST}")

if __name__ == "__main__":
    main()

