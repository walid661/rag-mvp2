#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import unicodedata

def _preclean_candidate(cand: str) -> str:
    s = cand
    # 0) Unicode & espaces
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"\s+", " ", s).strip()

    # 1) Corrige "I(I(" imbriqué
    s = re.sub(r"I\s*\(\s*I\s*\(", "I(", s)

    # 2) Coupe tout ce qui suit un long séparateur d'underscores
    #    ex: "... ) – ... – intention. ________________ 2. Tonification ..."
    s = re.sub(r"\s*_{6,}.*$", "", s)

    # 3) Coupe tout suffixe fléché (ex: " – > progression ...", " -> ...")
    s = re.sub(r"\s*(?:[–—-]\s*)?>\s*.*$", "", s)

    # 4) Harmonise ponctuation
    s = s.replace(" ;", ";")
    s = re.sub(r";\s*;", "; ", s)          # double point-virgule
    s = re.sub(r"\s*[–—-]\s*", " – ", s)   # unifie les tirets en " – "
    s = re.sub(r"\s+"," ", s).strip()
    return s

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
        r"(?P<intention>.+?)\s*(?:_{2,}.*)?\s*$"
    ),
]

line = "MC1.1 – (Re)mise en mouvement : mobilité douce – mobilité active guidée – I(amplitude libre, autochargé); T(30''); S(2); RE(10 – 12); RY(moderato) – mixte, amplitude complète, symétrie bilatérale – aérobie – Reconnecter corps et esprit par des mouvements amples; progression douce par répétition motrice."

cleaned = _preclean_candidate(line)
print(f"Cleaned: {cleaned[:100]}...")
print()

mobj = None
for pat in MC_PATTERNS:
    mobj = pat.match(cleaned)
    if mobj:
        print("MATCH!")
        print(f"Groups: {mobj.groupdict()}")
        break

if not mobj:
    print("NO MATCH")
    print(f"First 200 chars: {cleaned[:200]}")





