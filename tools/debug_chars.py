#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import re

src = Path("data2/meso_debug_candidates.txt").read_text(encoding="utf-8", errors="replace")
blocks = [b.strip() for b in re.split(r"\n-{3,}\n", src) if b.strip() and b.strip().startswith("MC")]
blocks = [b for b in blocks if re.match(r"^MC\d+\.\d+", b)]

if blocks:
    line = blocks[0]
    print(f"Premier bloc (100 premiers chars): {line[:100]}")
    print(f"\nCaracteres autour de MC1.1:")
    idx = line.find("MC1.1")
    if idx >= 0:
        print(f"  Avant: {repr(line[idx-5:idx])}")
        print(f"  MC1.1: {repr(line[idx:idx+5])}")
        print(f"  Apres: {repr(line[idx+5:idx+20])}")
    # Chercher tous les séparateurs
    separators = re.findall(r'[–—-]', line[:200])
    print(f"\nSeparateurs trouves: {set(separators)}")
    print(f"Codes Unicode: {[ord(c) for c in set(separators)]}")





