#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')
from etl_meso_txt_to_jsonl import collapse_block, _preclean_candidate, MC_PATTERNS
import re

# Simuler le flux complet
lines = [
    "MC1.1 – (Re)mise en mouvement : mobilité douce – mobilité active guidée",
    "- I(amplitude libre, autochargé); T(30''); S(2); RE(10 – 12); RY(moderato) – mixte, amplitude complète, symétrie bilatérale – aérobie – Reconnecter corps et esprit par des mouvements amples; progression douce par répétition motrice."
]

print("Original lines:")
for l in lines:
    print(f"  {l[:80]}...")

collapsed = collapse_block(lines)
print(f"\nAfter collapse_block: {collapsed[:150]}...")

cleaned = _preclean_candidate(collapsed)
print(f"\nAfter _preclean_candidate: {cleaned[:150]}...")

mobj = None
for pat in MC_PATTERNS:
    mobj = pat.match(cleaned)
    if mobj:
        print("\nMATCH!")
        print(f"Groups: {mobj.groupdict()}")
        break

if not mobj:
    print("\nNO MATCH")
    print(f"Full cleaned: {cleaned}")

