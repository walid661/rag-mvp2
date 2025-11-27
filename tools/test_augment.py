#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from pathlib import Path

# Test simple : lire une ligne et voir si on peut générer un text
src = Path("data2/meso_catalog.jsonl")
if src.exists():
    with open(src, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        if first_line.strip():
            obj = json.loads(first_line)
            print(f"Premier objet: meso_id={obj.get('meso_id')}")
            print(f"Has text: {'text' in obj}")
            if 'text' in obj:
                print(f"Text: {obj['text'][:100]}")
            else:
                print("Pas de champ text - le script n'a pas encore tourne")
else:
    print("Fichier introuvable")





