#!/usr/bin/env python3
# Analyse du PDF pour voir toutes les sections
from pathlib import Path
from pdfminer.high_level import extract_text
import re

pdf_path = Path("data/raw/pdfs/micro.pdf")
text = extract_text(str(pdf_path))
normalized = re.sub(r"\s+", " ", text).strip()

# Cherche les sections (A., B., C., etc.)
section_pattern = re.compile(r'\b([A-Z])\.\s+[A-Z][a-z]', re.IGNORECASE)
sections = section_pattern.findall(normalized)
unique_sections = sorted(set(sections))

print(f"📊 Sections trouvées dans le PDF:")
print(f"   Sections uniques : {unique_sections}")
print(f"   Nombre de sections : {len(unique_sections)}")

# Cherche les micro-cycles par section
for section in unique_sections:
    # Cherche les patterns mc + section + numéro
    pattern = re.compile(rf'\b(mc|MC){re.escape(section)}\d+', re.IGNORECASE)
    matches = pattern.findall(normalized)
    print(f"\n   Section {section}: {len(set([m[0] + section for m in matches]))} micro-cycles trouvés")

# Affiche un extrait autour de chaque section pour voir la structure
print(f"\n📝 Extrait autour de chaque section:")
for i, section in enumerate(unique_sections[:5]):  # Limite à 5 pour ne pas surcharger
    pattern = re.compile(rf'\b{re.escape(section)}\.\s+[A-Z][a-z].{{0,200}}', re.IGNORECASE)
    match = pattern.search(normalized)
    if match:
        print(f"\n   Section {section}: {match.group()[:200]}...")

# Compte total estimé
print(f"\n📈 Estimation totale:")
total_mc = 0
for section in unique_sections:
    pattern = re.compile(rf'\b(mc|MC){re.escape(section)}\d+', re.IGNORECASE)
    matches = pattern.findall(normalized)
    section_count = len(set([m[0] + section for m in matches]))
    total_mc += section_count
    print(f"   Section {section}: ~{section_count} micro-cycles")
print(f"   TOTAL ESTIMÉ: ~{total_mc} micro-cycles")


