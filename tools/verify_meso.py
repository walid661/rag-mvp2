#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

with open('data2/meso_catalog.jsonl', 'r', encoding='utf-8') as f:
    lines = [json.loads(l) for l in f]

print(f'Total: {len(lines)} lignes')
print(f'Derniers meso_id: {[l["meso_id"] for l in lines[-4:]]}')

# Vérifier les 4 derniers
for i, rec in enumerate(lines[-4:], 1):
    print(f'\n{i}. meso_id={rec["meso_id"]}, objectif={rec["objectif"]}, niveau={rec["niveau"]}')





