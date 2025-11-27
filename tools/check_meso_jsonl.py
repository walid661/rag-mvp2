#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

with open('data2/meso_catalog.jsonl', 'r', encoding='utf-8') as f:
    lines = [json.loads(l) for l in f if l.strip()]

print(f'Total: {len(lines)} lignes')
print(f'\nExemple 1:')
r = lines[0]
print(f'  meso_id: {r.get("meso_id")}')
print(f'  groupe: {r.get("groupe")}')
print(f'  niveau: {r.get("niveau")}')
print(f'  variables: {list(r.get("variables", {}).keys())}')
print(f'  methode: {r.get("methode", "")[:80]}')

bad = []
for i, l in enumerate(lines, 1):
    o = json.loads(json.dumps(l))  # copy
    if "I(" in o.get("methode", "") or "T(" in o.get("methode", ""):
        bad.append(("methode_has_vars", i, o.get("meso_id")))
    if "variables" not in o or set(o.get("variables", {}).keys()) != {"I","T","S","RE","RY"}:
        bad.append(("variables_incomplete", i, o.get("meso_id")))

print(f'\nProblemes detectes: {len(bad)}')
for x in bad[:10]:
    print(f'  {x}')





