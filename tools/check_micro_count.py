#!/usr/bin/env python3
# Script pour compter les micro-cycles dans le PDF
from pathlib import Path
from pdfminer.high_level import extract_text
import re

pdf_path = Path("data/raw/pdfs/micro.pdf")
text = extract_text(str(pdf_path))

# Cherche tous les patterns de micro-cycles possibles
patterns = [
    r'\b(mc|MC)[A-Z]?\d+',  # mcA01, MC01, etc.
    r'\b(micro|Micro)[\s-]?cycle[\s-]?\d+',  # micro-cycle 1, etc.
    r'\b[A-Z]\.\d+',  # A.1, B.2, etc.
]

all_matches = set()
for pattern in patterns:
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        all_matches.update([m[0] if isinstance(m, tuple) else m for m in matches])

print(f"📊 Analyse du PDF micro.pdf")
print(f"   Longueur du texte : {len(text)} caractères")
print(f"   Nombre de lignes : {len(text.splitlines())}")

# Cherche aussi les sections A, B, C, etc.
sections = re.findall(r'\b([A-Z])\.\s+[A-Z]', text)
print(f"   Sections trouvées (A, B, C...) : {len(set(sections))}")

# Cherche les patterns MC ou mc suivis de lettres/chiffres
mc_pattern = re.compile(r'\b(mc|MC)([A-Z]?\d+)', re.IGNORECASE)
mc_matches = mc_pattern.findall(text)
print(f"\n🔍 Micro-cycles trouvés avec pattern 'mc/MC + lettres/chiffres':")
if mc_matches:
    unique_mc = set([f"{m[0]}{m[1]}" for m in mc_matches])
    print(f"   Total unique : {len(unique_mc)}")
    print(f"   Exemples : {sorted(list(unique_mc))[:20]}")
else:
    print("   Aucun trouvé avec ce pattern")

# Cherche aussi les numéros de micro-cycles dans le JSONL généré
print(f"\n📄 Micro-cycles dans le JSONL généré:")
try:
    import json
    with open("data2/micro_catalog.jsonl", "r", encoding="utf-8") as f:
        jsonl_lines = [json.loads(l) for l in f if l.strip()]
    print(f"   Total : {len(jsonl_lines)}")
    micro_ids = [obj.get("micro_id", "") for obj in jsonl_lines]
    print(f"   IDs : {sorted(micro_ids)}")
except Exception as e:
    print(f"   Erreur : {e}")

# Affiche un extrait du texte pour voir la structure
print(f"\n📝 Extrait du texte (premiers 2000 caractères):")
print(text[:2000])
print("\n...")


