#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

# Les 4 lignes JSONL à ajouter
new_lines = [
    {"type":"meso_ref","meso_id":"MC3.6","objectif":"Hypertrophie structurelle","niveau":"Intermédiaire","nom":"Contrôle & tempo : excentriques lents puis volume dégressif","methode":"Tempo training + Dead Set","variables":{"I":"70%->60%->45%->30%","T":"2'30/3'","S":"1 par enchaînement","RE":"6->8->10->12","RY":"excentrique lent puis fluide"},"sollicitation_neuromusculaire":"fibres IIa, tempo lent contrôlé, amplitude complète","systeme_energetique":"anaérobie lactique","intention":"Hypertrophie combinant tension mécanique initiale et accumulation de fatigue ; progression par baisse de charge et hausse du volume intra-série.","groupe":"Hypertrophie structurelle","niveau_bloc":"Intermédiaire","text":"Hypertrophie structurelle – Intermédiaire – Tempo training + Dead Set – I:70%->60%->45%->30% T:2'30/3' S:1 par enchaînement RE:6->8->10->12 RY:excentrique lent puis fluide – fibres IIa – anaérobie lactique – Combiner tension initiale et fatigue progressive."},
    {"type":"meso_ref","meso_id":"MC7.7","objectif":"Performance & intensification","niveau":"Intermédiaire","nom":"Intervalles de puissance : sprints courts / rameur / vélocité","methode":"intervalles de puissance (1:3 / 1:4)","variables":{"I":"70–90%","T":"15–30'' effort / 45–90'' récup","S":"3–4","RE":"4–6","RY":"décharge / récupération"},"sollicitation_neuromusculaire":"fibres IIx/IIa, vitesse maximale, effort cyclique","systeme_energetique":"anaérobie alactique","intention":"Améliorer la puissance anaérobie ; progression via distance, charge ou vitesse.","groupe":"Performance & intensification","niveau_bloc":"Intermédiaire","text":"Performance & intensification – Intermédiaire – Intervalles de puissance – I:70–90% T:15–30''/45–90'' S:3–4 RE:4–6 RY:décharge/récup – IIx/IIa – anaérobie alactique – Puissance anaérobie par sprints/rameur/vélocité."},
    {"type":"meso_ref","meso_id":"MC9.12","objectif":"Préparation mentale & récupération","niveau":"Confirmé","nom":"Régénération holistique : combinaison sommeil / respiration / récupération","methode":"protocole de régénération guidée","variables":{"I":"autogéré","T":"15–20'","S":"1","RE":"selon séquence","RY":"enchaînement fluide, relâchement type Jacobson"},"sollicitation_neuromusculaire":"régulation globale, amplitude douce, respiration guidée","systeme_energetique":"aérobie","intention":"Restaurer l'équilibre intérieur ; progression par cohérence entre séquences.","groupe":"Préparation mentale & récupération","niveau_bloc":"Confirmé","text":"Préparation mentale & récupération – Confirmé – Régénération guidée – I:autogéré T:15–20' S:1 RE:selon séquence RY:enchaînement fluide/Jacobson – régulation globale – aérobie – Rééquilibrage par respiration/sommeil/récupération."},
    {"type":"meso_ref","meso_id":"MC10.2","objectif":"Préparation à un objectif","niveau":"Débutant","nom":"Progression structurée : alternance cardio / renfo","methode":"split spécifique mixte","variables":{"I":"45–60%","T":"30–60''","S":"3–4","RE":"10–12","RY":"30/30 > 40/20 > 45/15 (selon adaptation)"},"sollicitation_neuromusculaire":"fibres mixtes, alternance filières, symétrie fonctionnelle","systeme_energetique":"mixte","intention":"Créer une base polyvalente ; progression via structuration alternée et montée d'intensité.","groupe":"Préparation à un objectif","niveau_bloc":"Débutant","text":"Préparation à un objectif – Débutant – Split spécifique mixte – I:45–60% T:30–60'' S:3–4 RE:10–12 RY:30/30>40/20>45/15 – fibres mixtes – mixte – Base polyvalente par alternance cardio/renfo."}
]

# Lire le fichier actuel (sans les 4 dernières lignes mal encodées)
with open('data2/meso_catalog.jsonl', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Garder seulement les 140 premières lignes (les bonnes)
lines = lines[:140]

# Ajouter les 4 nouvelles lignes
with open('data2/meso_catalog.jsonl', 'w', encoding='utf-8') as f:
    for line in lines:
        f.write(line.rstrip() + '\n')
    for rec in new_lines:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')

print(f"4 lignes ajoutees. Total: {140 + 4} lignes")





