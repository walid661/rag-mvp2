# Journal de décision – Choix d’architecture pour Coach Mike

La mission consistait à construire une interface chat multi‑utilisateur
connectée à un backend RAG, avec onboarding et mémoire, en choisissant
l’option « chemin le plus simple ». Trois options étaient proposées :

1. **Option A : SQL minimaliste**
   - Next.js + NextAuth (Credentials)
   - Prisma + SQLite en dev, PostgreSQL en prod
   - Profils et messages stockés en tables SQL
2. **Option B : NoSQL plug‑and‑play**
   - Auth + Firestore/Firebase ou Appwrite/Supabase
   - Profils dans des documents, messages dans des sous‑collections
3. **Option C : Dev ultra‑léger (démo uniquement)**
   - Utilisateur anonyme via cookie signé
   - Stockage local (LowDB/SQLite) côté serveur
   - Non adapté à la production et déconseillé pour le multi‑utilisateur

## Critères d’évaluation

1. **Simplicité de mise en œuvre** : temps nécessaire pour coder et tester
   l’intégration complète (authentification, persistance, API internes).
2. **Coût et dépendances** : gratuit ou niveau « free tier » ; nombre
   minimal de services externes.
3. **Capacité multi‑utilisateur** : chaque utilisateur doit avoir son
   propre profil et historique sans fuite de données.
4. **Facilité de déploiement** : compatibilité avec Vercel/Render et
   portabilité entre environnement de dev et production.

## Analyse des options

### Option A : SQL minimaliste

Cette option repose sur des briques bien connues (Next.js, NextAuth,
Prisma) et ne nécessite aucun service tiers. Prisma permet de démarrer
rapidement avec SQLite en développement puis de migrer vers PostgreSQL en
production sans changer de code. NextAuth est facile à configurer avec un
fournisseur « Credentials » minimal (simple nom d’utilisateur). Les tables
`users`, `profiles`, `chat_sessions` et `messages` couvrent tous les
besoins du projet. L’isolation des données est assurée par l’ID
d’utilisateur. Le coût est nul et la base reste locale tant que l’on ne
passe pas à un Postgres managé.

### Option B : NoSQL plug‑and‑play

Firebase Auth + Firestore (ou Appwrite) apportent une authentification
prête à l’emploi et un stockage flexible. Toutefois, l’intégration
nécessite la configuration d’un projet Firebase, la gestion des règles de
sécurité et la prise en main des SDK. Pour un prototype simple, cela
ajoute de la complexité et dépend d’un service externe (potentiellement
payant au‑delà du free tier). Supabase est similaire mais requiert
l’utilisation d’un back‑end Postgres, ce qui revient à Option A sans en
offrir la simplicité locale.

### Option C : Dev ultra‑léger (démo)

Cette option minimise le code en utilisant un cookie anonyme et un
fichier JSON ou SQLite local. Elle convient aux prototypes ou à une page
`/sandbox`, mais ne répond pas aux exigences d’une application
multi‑utilisateur stable : aucune authentification réelle, risque de
collision de sessions et pas de transition aisée vers la production. Elle
était explicitement déconseillée pour l’application principale.

## Décision

Après avoir évalué les trois options sur la base des critères ci‑dessus,
**l’Option A a été retenue**. Elle présente la meilleure combinaison de
simplicité et de robustesse : l’utilisation de Prisma et d’une base SQL
locale permet de développer et de tester rapidement sans dépendre d’un
service externe. La migration vers un Postgres managé en production se
fait simplement en changeant les variables d’environnement. L’intégration
de NextAuth avec un fournisseur « Credentials » offre un mécanisme
d’authentification minimaliste mais suffisant pour la plupart des
scénarios de ce projet. Enfin, l’abstraction `ProfileStore`/`ChatStore`
prévoit la possibilité de remplacer facilement l’implémentation par
Firestore ou une autre solution si les besoins évoluent.