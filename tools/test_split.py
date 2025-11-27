#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, unicodedata
from pathlib import Path

SEP = r"\s+[–—-]\s+"
MC_HEAD = re.compile(r"^MC(?P<id>\d+\.\d+)\s+" + SEP)

def norm(s:str)->str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("'","'").replace(""",'"').replace(""",'"')
    return re.sub(r"\s+"," ", s).strip()

def split_block(line:str):
    raw = norm(line)
    print(f"Raw: {raw[:100]}")
    m = MC_HEAD.match(raw)
    print(f"Match: {m is not None}")
    if not m: return None
    mid = m.group("id")
    print(f"ID: {mid}")
    rest = raw[m.end():]
    print(f"Rest: {rest[:100]}")
    parts = re.split(SEP, rest)
    print(f"Parts count: {len(parts)}")
    for i, p in enumerate(parts[:7]):
        print(f"  Part {i}: {p[:50]}")
    if len(parts) < 7: return None
    nom = norm(parts[0]); objectif = norm(parts[1]); methode = norm(parts[2])
    vars_block = norm(parts[3]); neuro = norm(parts[4]); energy = norm(parts[5])
    intention = norm(" – ".join(parts[6:]))
    return mid, nom, objectif, methode, vars_block, neuro, energy, intention

# Test avec un bloc réel
src = Path("data2/meso_debug_candidates.txt").read_text(encoding="utf-8", errors="replace")
blocks = [b.strip() for b in re.split(r"\n-{3,}\n", src) if b.strip() and b.strip().startswith("MC")]
blocks = [b for b in blocks if re.match(r"^MC\d+\.\d+", b)]
print(f"Blocs trouves: {len(blocks)}")
if blocks:
    print(f"\nTest premier bloc:")
    result = split_block(blocks[0])
    print(f"Result: {result is not None}")





