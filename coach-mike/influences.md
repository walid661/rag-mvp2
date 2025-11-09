# Influences tirées du PDF « Building Your First AI Chatbot with Ollama and Gradio »

Ce fichier synthétise dix idées clés du PDF fourni et explique comment
elles ont été adaptées à l’application Coach Mike. Les citations
référencées entre crochets renvoient aux passages du document d’origine.

## 1. Mettre l’accent sur la simplicité et le local

L’article montre qu’il est possible de construire un chatbot complet en
utilisant uniquement un outil d’exécution local (Ollama) et une
bibliothèque d’interface légère (Gradio)【948476518596150†L9-L19】. Ce
principe a inspiré le choix d’une architecture minimaliste : une base
SQLite en développement et un proxy HTTP qui appelle directement votre
backend RAG sans passer par des services cloud coûteux. Cela rend le
prototype rapide à mettre en place et facile à déployer.

## 2. Conserver l’historique des conversations

La version 2 du chatbot introduit la mémoire en construisant un tableau
de messages contenant toutes les paires utilisateur/assistant【948476518596150†L186-L219】.
Nous avons repris cette idée en créant des tables `chat_sessions` et
`messages` et en envoyant l’historique complet de la session à l’API
RAG pour chaque requête. Ainsi, Coach Mike connaît le contexte de
l’utilisateur et peut adapter ses réponses.

## 3. Exposer des paramètres de contrôle

L’article explique comment ajuster le comportement du modèle grâce à des
paramètres tels que la température ou le nombre maximum de tokens【948476518596150†L318-L334】.
Même si notre backend RAG ne supporte pas ces options, nous avons
prévu un endroit pour intégrer de futurs réglages (par exemple, un
curseur “intensité” qui pourrait influencer la sélection de sources ou
le style d’entraînement). Le formulaire d’onboarding possède un champ
`preferences.style` où l’utilisateur peut indiquer le style
d’accompagnement souhaité.

## 4. Personnaliser le ton avec des « personas »

La version 4 du chatbot permet de choisir une personnalité (pirate,
poète, enseignant, etc.) en utilisant des prompts système【948476518596150†L360-L373】.
Nous avons transposé cette idée en ajoutant au profil utilisateur un
champ « style d’entraînement » qui pourrait à terme sélectionner un
prompt système différent côté RAG (“coach bienveillant”, “coach
militaire”, etc.). Cela ouvre la voie à des interactions plus
personnalisées sans changer le code de l’interface.

## 5. Afficher les réponses en flux continu

L’article recommande de diffuser les réponses mot par mot pour
améliorer l’expérience utilisateur【948476518596150†L490-L549】. Comme notre
backend RAG n’implémente pas encore le streaming, nous avons simulé un
effet “machine à écrire” côté client. La logique de streaming est
factorisée dans le composant `ChatWindow` et pourra être remplacée
facilement lorsque l’API supportera la diffusion de tokens en temps
réel.

## 6. Proposer des tests rapides et des suggestions

Les auteurs proposent différentes invites pour tester la mémoire, la
créativité ou le raisonnement du modèle【948476518596150†L562-L571】. Nous avons
introduit des boutons de suggestions rapides (“Plan hebdomadaire”,
“Séance 30 min”, “Full body”) sous le champ de saisie afin d’aider
l’utilisateur à démarrer. Cela permet d’évaluer rapidement la qualité
des réponses et de guider les débutants.

## 7. Gérer les erreurs et les limites matérielles

Le PDF fournit un guide de dépannage expliquant comment résoudre les
problèmes de connexion, la lenteur des réponses ou l’épuisement de la
mémoire【948476518596150†L573-L599】. Dans l’application Coach Mike, nous
affichons des messages d’erreur clairs lorsque l’API renvoie un code
d’erreur (ex. : « API down », « profil manquant »). Un système de logs
pourrait être ajouté ultérieurement afin de diagnostiquer des
problèmes de performance liés au back‑end.

## 8. Structurer le projet par versions

Le dépôt de démonstration suit un découpage par fichiers (v1, v2, etc.)
pour illustrer chaque ajout de fonctionnalité【948476518596150†L623-L630】.
Dans notre code, nous avons séparé clairement les couches : fichiers
`lib/` pour l’accès aux données et aux API, `components/` pour l’UI,
`app/api/` pour les proxys serveur et les accès aux stores. Cette
architecture modulaire facilite l’évolution (ajout d’une nouvelle
implémentation de `ChatStore`, page `/sandbox`, etc.).

## 9. S’inspirer des exercices proposés

L’auteur suggère des améliorations comme un bouton « Save Chat » ou un
sélecteur de modèle【948476518596150†L658-L663】. Nous avons retenu l’idée du
“Save Chat” en prévoyant une route API pour récupérer l’historique des
messages. Le stockage étant centralisé, il est trivial d’ajouter un
bouton qui exporte la session au format texte ou JSON. Un sélecteur
“modèle” pourrait quant à lui permettre de basculer entre différents
profils RAG (force, mobilité, cardio) en utilisant une colonne
supplémentaire dans la table `chat_sessions`.

## 10. Préparer la transition vers un assistant RAG complet

Enfin, l’article annonce que la suite abordera le RAG pour charger des
documents personnels【948476518596150†L640-L649】. Nous avons donc conçu
l’application de manière à envoyer le profil utilisateur (au format JSON)
avec chaque requête vers `/chat`. Cela permettra au backend de filtrer
et de récupérer les documents pertinents pour générer des réponses
adaptées. Le panneau « Sources » rend visible cette fonctionnalité en
affichant les liens ou les références des documents utilisés.