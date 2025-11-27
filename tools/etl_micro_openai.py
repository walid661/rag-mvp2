#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extraction micro-cycles depuis micro.pdf -> JSONL via OpenAI.
Ce script lit le PDF micro.pdf et génère data2/micro_catalog.jsonl avec la clé OpenAI (.env)
Gère automatiquement les PDFs longs en découpant en sections si nécessaire.
"""
from openai import OpenAI
import json
import re
from pathlib import Path
from pdfminer.high_level import extract_text
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

# Configuration
MAX_CHARS_PER_CHUNK = 100000  # Limite par chunk (GPT-4o peut gérer jusqu'à 128k tokens)
CHUNK_OVERLAP = 2000  # Chevauchement entre chunks pour éviter de couper un micro-cycle

def split_text_by_sections(text: str) -> list:
    """
    Découpe le texte par sections (A, B, C, etc.) pour traiter chaque section séparément
    """
    # Cherche les séparateurs de groupes : "A. ", "B. ", "C. " etc.
    # Pattern simple: lettre majuscule + point + espace
    section_pattern = re.compile(r'\b([A-Z])\.\s+', re.IGNORECASE)
    matches = list(section_pattern.finditer(text))
    
    if len(matches) <= 1:
        # Pas de sections claires, retourne tout le texte
        return [text]
    
    chunks = []
    for i, match in enumerate(matches):
        section_start = match.start()
        # Section suivante ou fin du texte
        if i + 1 < len(matches):
            section_end = matches[i + 1].start()
        else:
            section_end = len(text)
        
        chunk = text[section_start:section_end].strip()
        if chunk:
            chunks.append(chunk)
    
    return chunks

def extract_jsonl_from_text(text_chunk: str, chunk_num: int = None, total_chunks: int = None) -> str:
    """
    Extrait le JSONL d'un chunk de texte via OpenAI
    """
    chunk_info = ""
    if chunk_num is not None and total_chunks is not None:
        chunk_info = f"\n⚠️ ATTENTION : Ceci est le chunk {chunk_num}/{total_chunks} du document complet. Traite uniquement les micro-cycles présents dans ce chunk.\n"
    
    prompt = f"""
Tu es un expert en préparation physique.
Lis le texte suivant (issu d'un PDF de micro-cycles d'entraînement) et convertis-le en un fichier JSONL.

⚠️ IMPORTANT : Tu DOIS extraire TOUS les micro-cycles présents dans le texte, de TOUTES les sections (A, B, C, D, E, F, G, etc.).
Ne saute AUCUN micro-cycle. Chaque ligne commençant par "mc" suivi de lettres et chiffres (ex: mcA01, mcB05, mcC12) doit être convertie en un objet JSON.

Chaque micro-cycle doit être un objet JSON structuré ainsi :

{{
  "type": "micro_ref",
  "micro_id": "mcA01" (format exact : mc + lettre section + numéro à 2 chiffres),
  "groupe": "A. Fondations & relance" (garde le nom complet de la section),
  "sous_groupe": "A1. Réactivation fonctionnelle" ou "N/A",
  "niveau": "Débutant" | "Intermédiaire" | "Confirmé" (déduit du contexte),
  "nom": "Titre du micro-cycle",
  "objectif": "But principal du micro-cycle",
  "methode": "Méthode(s) d'entraînement ou format",
  "variables": {{
    "I": "intensité (% ou qualitative)",
    "T": "temps de repos ou effort",
    "S": "nombre de séries",
    "RE": "nombre de répétitions",
    "RY": "tempo ou rythme"
  }},
  "sollicitation_neuromusculaire": "Ce qui est activé (fibres, coordination...)",
  "systeme_energetique": "aérobie / anaérobie lactique / alactique",
  "intention": "Effet recherché",
  "text": "Résumé naturel en français, 3 à 5 phrases : explique à l'élève ce qu'il fera concrètement, avec les durées, intensité (en mots), nombre de séries, et effets recherchés."
}}

Contraintes STRICTES :
- EXTRAIS TOUS les micro-cycles de TOUTES les sections (A, B, C, D, E, F, G, etc.)
- Le micro_id doit suivre exactement le format du texte source (ex: mcA01, mcB05, mcC12)
- Garde les catégories A, B, C, etc. dans le champ 'groupe' avec leur nom complet
- Si un sous-groupe (A1, A2, etc.) est présent, ajoute-le dans 'sous_groupe'
- Ne laisse aucun champ vide (mets "N/A" si manquant)
- Le champ "text" doit reformuler les variables dans un français fluide
- N'utilise jamais les notations I(), T(), S() dans "text"
- Rends UNIQUEMENT les objets JSONL, un par ligne, sans commentaire, sans texte avant/après

{chunk_info}
Voici le texte source (extrait TOUS les micro-cycles présents) :
{text_chunk}
"""
    
    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=16000,  # Augmenté pour permettre plus de micro-cycles
    )
    
    content = resp.choices[0].message.content
    # Retire les blocs ```jsonl ou ``` si présents
    content = re.sub(r"^```(?:jsonl|json)?\s*\n", "", content, flags=re.MULTILINE)
    content = re.sub(r"\n```\s*$", "", content, flags=re.MULTILINE)
    return content.strip()

# 1. Extraction brute du texte PDF
pdf_path = Path("data/raw/pdfs/micro.pdf")
raw_text = extract_text(str(pdf_path))

# 2. Normalisation du texte
text = re.sub(r"\s+", " ", raw_text).strip()

print(f"📄 Texte extrait : {len(text)} caractères")

# 3. Découpage par sections (A, B, C, etc.) pour traiter chaque section séparément
chunks = split_text_by_sections(text)
print(f"📦 Nombre de sections/chunks : {len(chunks)}")
for i, chunk in enumerate(chunks, 1):
    # Affiche la première ligne de chaque chunk pour identifier la section
    first_line = chunk[:100].split('\n')[0] if '\n' in chunk[:100] else chunk[:100]
    print(f"   Chunk {i}: {len(chunk)} caractères - {first_line[:50]}...")

# 4. Traitement de chaque chunk
all_jsonl_lines = []
for i, chunk in enumerate(chunks, 1):
    print(f"🔄 Traitement du chunk {i}/{len(chunks)} ({len(chunk)} caractères)...")
    jsonl_content = extract_jsonl_from_text(chunk, chunk_num=i, total_chunks=len(chunks))
    
    # Parse les lignes JSONL
    lines = [l.strip() for l in jsonl_content.split("\n") if l.strip()]
    for line in lines:
        try:
            json.loads(line)  # Validation
            all_jsonl_lines.append(line)
        except json.JSONDecodeError:
            print(f"   ⚠️  Ligne JSON invalide ignorée dans le chunk {i}")

# 5. Déduplication par micro_id (au cas où il y aurait des doublons aux frontières)
seen_ids = set()
unique_lines = []
for line in all_jsonl_lines:
    try:
        obj = json.loads(line)
        micro_id = obj.get("micro_id")
        if micro_id and micro_id not in seen_ids:
            seen_ids.add(micro_id)
            unique_lines.append(line)
        elif not micro_id:
            unique_lines.append(line)  # Garde les lignes sans micro_id
    except:
        unique_lines.append(line)  # Garde les lignes invalides pour debug

# 6. Sauvegarde
out_path = Path("data2/micro_catalog.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for line in unique_lines:
        f.write(line + "\n")

# 7. Validation finale
valid_count = 0
for line in unique_lines:
    try:
        json.loads(line)
        valid_count += 1
    except json.JSONDecodeError:
        pass

print(f"\n✅ JSONL généré : {out_path}")
print(f"   {valid_count} micro-cycles détectés sur {len(unique_lines)} lignes")
if len(all_jsonl_lines) > len(unique_lines):
    print(f"   ({len(all_jsonl_lines) - len(unique_lines)} doublons supprimés)")

