#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

with open('data2/meso_catalog.jsonl', 'r', encoding='utf-8') as f:
    lines = [json.loads(l) for l in f]

print(f'Total: {len(lines)} lignes')
print(f'\nExemple (premiere ligne):')
rec = lines[0]
print(f'  meso_id: {rec.get("meso_id")}')
print(f'  groupe: {rec.get("groupe")}')
print(f'  niveau: {rec.get("niveau")}')
print(f'  objectif: {rec.get("objectif")}')

print(f'\nVerification des corrections:')
groupes = set(r.get("groupe") for r in lines if r.get("groupe"))
niveaux = set(r.get("niveau") for r in lines if r.get("niveau"))
objectifs = set(r.get("objectif") for r in lines if r.get("objectif"))

print(f'  Groupes uniques: {len(groupes)}')
print(f'  Niveaux uniques: {sorted(niveaux)}')
print(f'  Objectifs uniques: {sorted(objectifs)}')





