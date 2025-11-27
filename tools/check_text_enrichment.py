#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

with open('data2/meso_catalog.jsonl', 'r', encoding='utf-8') as f:
    lines = [json.loads(l) for l in f if l.strip()]

print(f'Total: {len(lines)} lignes')
print(f'Lignes avec text: {sum(1 for l in lines if l.get("text"))}')
print(f'\nPremieres 3 lignes:')
for i, l in enumerate(lines[:3], 1):
    print(f'\n{i}. meso_id={l.get("meso_id")}')
    text = l.get("text", "[MANQUANT]")
    print(f'   text: {text[:150]}...' if len(text) > 150 else f'   text: {text}')





