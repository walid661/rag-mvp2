#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, argparse, unicodedata
from pathlib import Path
from collections import Counter, defaultdict

def norm(s:str)->str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("'","'").replace(""",'"').replace(""",'"')
    s = re.sub(r"\s+"," ", s).strip()
    return s

# Règles de diagnostic rapides : on tag les causes probables
CHECKS = [
  ("double_I_paren", lambda t: bool(re.search(r"I\s*\(\s*I\s*\(", t))),
  ("suffix_arrow",   lambda t: bool(re.search(r"\s*(?:–|—|-)?\s*>\s*.+$", t))),
  ("missing_vars",   lambda t: not re.search(r"I\s*\([^)]*\)\s*;\s*T\s*\([^)]*\)\s*;\s*S\s*\([^)]*\)\s*;\s*RE\s*\([^)]*\)\s*;\s*RY\s*\([^)]*\)", t)),
  ("bad_separators", lambda t: not bool(re.search(r"\s[–—-]\s", t))),  # aucun tiret normalisé
  ("extra_semicol",  lambda t: bool(re.search(r";\s*;", t))),
  ("trailing_noise", lambda t: bool(re.search(r"(?:_{3,}|\.{3,})\s*$", t))),
]

def diagnose(block:str):
    tags = [name for name, fn in CHECKS if fn(block)]
    if not tags:
        tags = ["other_pattern_mismatch"]
    return tags

def extract_mc_id(block:str):
    m = re.match(r"^\s*(MC\d+(?:\.\d+)?)\b", block)
    return m.group(1) if m else ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="data2/meso_debug_unmatched.txt")
    ap.add_argument("--out", dest="outp", required=True, help="TSV de rapport")
    ap.add_argument("--samples", type=int, default=5, help="Nb d'extraits par catégorie")
    args = ap.parse_args()

    inp = Path(args.inp)
    raw = inp.read_text(encoding="utf-8", errors="ignore")
    blocks = [b.strip() for b in re.split(r"\n\s*---\s*\n", raw) if b.strip()]

    counts = Counter()
    by_tag = defaultdict(list)
    for b in blocks:
        t = norm(b)
        tags = diagnose(t)
        for tag in tags:
            counts[tag] += 1
            by_tag[tag].append(t)

    # Résumé console
    total = sum(counts.values())
    print(f"Total unmatched blocks: {total}")
    for tag, c in counts.most_common():
        pct = (100*c/total) if total else 0
        print(f" - {tag:20s}: {c:4d}  ({pct:.1f}%)")

    # Rapport TSV (tag \t mc_id \t extrait)
    outp = Path(args.outp)
    with outp.open("w", encoding="utf-8") as f:
        f.write("tag\tmc_id\textract\n")
        for tag, items in by_tag.items():
            for s in items[:args.samples]:
                mc = extract_mc_id(s)
                # Raccourcir l'extrait pour lisibilité
                short = s if len(s) < 300 else s[:297] + "..."
                f.write(f"{tag}\t{mc}\t{short}\n")
    print(f"Rapport detaille -> {outp}")

if __name__ == "__main__":
    main()

