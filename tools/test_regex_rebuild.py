#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

# Test avec un exemple réel
test = "MC1.1 – (Re)mise en mouvement : mobilité douce – mobilité active guidée – I(amplitude libre, autochargé) ; T(30'') ; S(2) ; RE(10–12) ; RY(moderato) – mixte, amplitude complète, symétrie bilatérale – aérobie – Reconnecter corps et esprit par des mouvements amples ; progression douce par répétition motrice."

MC_RE_WITHOUT_OBJ = re.compile(
    r"^\s*(MC(?P<id>\d+\.\d+))\s*[–—-]\s*(?P<nom>.+?)\s*[–—-]\s*(?P<methode>.+?)\s*[–—-]\s*(?P<vars>.+?)\s*[–—-]\s*(?P<neuro>.+?)\s*[–—-]\s*(?P<energy>.+?)\s*[–—-]\s*(?P<intention>.+?)\s*$"
)

m = MC_RE_WITHOUT_OBJ.match(test)
if m:
    print("Match OK")
    print(f"id: {m.group('id')}")
    print(f"nom: {m.group('nom')}")
    print(f"methode: {m.group('methode')}")
    print(f"vars: {m.group('vars')[:80]}")
    print(f"neuro: {m.group('neuro')}")
    print(f"energy: {m.group('energy')}")
    print(f"intention: {m.group('intention')[:80]}")
else:
    print("No match!")





