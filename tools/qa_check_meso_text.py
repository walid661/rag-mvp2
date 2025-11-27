#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, re
from pathlib import Path

bad = []
for i, line in enumerate(Path("data2/meso_catalog.jsonl").read_text(encoding="utf-8").splitlines(), 1):
    if not line.strip(): continue
    o = json.loads(line)
    if o.get("type") != "meso_ref": continue
    txt = (o.get("text") or "").strip()
    if not txt: 
        bad.append((i, o.get("meso_id"), "missing_text"))
        continue
    if re.search(r"\b(I|T|S|RE|RY)\(", txt): 
        bad.append((i, o.get("meso_id"), "raw_vars_in_text"))
    if len(txt.split(".")) < 2: 
        bad.append((i, o.get("meso_id"), "too_short"))
    # Vérifier la ponctuation (; sans espace)
    if re.search(r";[^ ]", txt):
        bad.append((i, o.get("meso_id"), "semicolon_no_space"))

print("Problemes:", len(bad))
for b in bad[:20]: 
    print(b)

if len(bad) == 0:
    print("\nOK: Tous les textes sont valides!")





