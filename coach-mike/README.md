# Coach Mike – Application Web RAG Personnalisée

Bienvenue dans l’application Coach Mike, une interface web permettant aux
utilisateurs de discuter avec votre backend RAG personnalisé. Chaque
utilisateur dispose d’un profil d’onboarding qui permet de créer des séances
d’entraînement adaptées et la mémoire des conversations est conservée dans
une base de données. L’application est construite avec Next.js (App Router)
en TypeScript et utilise Prisma et NextAuth pour l’authentification et la
persistance.

## 🧰 Fonctionnalités

- **Multi‑utilisateur** : chaque utilisateur se connecte (simplement via un nom
  d’utilisateur) et possède ses propres sessions de chat et profil.
- **Onboarding personnalisé** : à la première connexion, un formulaire
  recueille l’âge, le sexe, l’objectif principal, etc., et stocke ces
  informations au format JSON.
- **Chat** : l’interface affiche l’historique des messages, permet de
  sélectionner ou créer des sessions, d’envoyer des requêtes au backend RAG
  (`/chat`) et d’afficher les sources retournées.
- **Persistance** : toutes les données (profils, sessions, messages) sont
  stockées via Prisma dans une base SQLite (en développement) ou PostgreSQL
  (en production). Les messages peuvent être récupérés ou ajoutés via les
  routes API internes.
- **Proxy API** : une route `/api/chat` renvoie les requêtes au backend RAG
  configuré en ajoutant éventuellement un jeton API secret. Les sources
  retournées sont affichées dans un panneau latéral.
- **Tests** : quelques tests unitaires avec Vitest et React Testing
  Library assurent que le formulaire d’onboarding et l’affichage des
  messages fonctionnent correctement.

## 🏗️ Architecture

Cette application implémente **l’Option A (SQL minimaliste)** décrite dans le
prompt. Nous utilisons Prisma avec SQLite pour le développement et
PostgreSQL en production. NextAuth avec un fournisseur « Credentials » basé
sur un simple nom d’utilisateur gère les sessions. Le schéma de base de
données est défini dans `prisma/schema.prisma`.

Le stockage des profils et des messages est abstrait via les interfaces
`ProfileStore` et `ChatStore` (voir `lib/store/sql.ts`). Cela permet de
changer facilement de back‑end à l’avenir (Firestore, LowDB, etc.).

## 🚀 Installation et exécution

1. **Cloner le dépôt** et installer les dépendances :

   ```bash
   npm install
   ```

2. **Configurer les variables d’environnement**. Créez un fichier
   `.env.local` à la racine avec les variables suivantes :

   ```env
   # URL publique du site (utile pour NextAuth)
   NEXT_PUBLIC_SITE_URL=http://localhost:3000

   # URL du backend RAG (ne doit pas inclure /chat)
   API_URL=http://localhost:8000

   # Jeton secret optionnel à envoyer dans l’en-tête Authorization pour
   # accéder à l’API RAG. Laisser vide si non requis.
   RAG_API_TOKEN=

   # Type de base de données : sqlite ou postgresql
   DATABASE_PROVIDER=sqlite

   # URL de connexion Prisma. Par défaut une base SQLite sera créée dans
   # prisma/dev.db. Pour PostgreSQL : postgres://user:pass@host:5432/db
   DATABASE_URL=file:./prisma/dev.db

   # Secret pour NextAuth (générer une chaîne aléatoire)
   NEXTAUTH_SECRET=changemeplease
   ```

3. **Générer le client Prisma et créer la base** :

   ```bash
   npx prisma generate
   npx prisma db push
   ```

4. **Lancer le serveur de développement** :

   ```bash
   npm run dev
   ```

   L’application sera disponible sur http://localhost:3000.

5. **Exécuter les tests** :

   ```bash
   npm test
   ```

## 🧪 Utilisation

1. Ouvrez la page d’accueil ; si vous n’êtes pas connecté, vous serez redirigé
   vers `/login`. Entrez simplement un nom d’utilisateur.
2. Lors de la première connexion, vous serez redirigé vers `/onboarding` pour
   compléter votre profil. Ces informations seront enregistrées et utilisées
   pour personnaliser les requêtes envoyées à votre backend RAG.
3. Après l’onboarding, la page `/chat` s’ouvre. Vous y trouverez :
   - Un panneau latéral listant vos sessions de conversation. Vous pouvez en
     créer une nouvelle ou sélectionner une session existante.
   - L’historique des messages pour la session courante.
   - Un champ de saisie avec des suggestions rapides (plan hebdomadaire,
     séance de 30 minutes, full body).
   - Un panneau « Sources » pour consulter les documents ayant alimenté la
     réponse générée (si fournis par le backend RAG).
4. Chaque message envoyé est enregistré dans la base avec le rôle (user ou
   assistant) et la date. Les réponses du backend sont également
   enregistrées.

## 📄 Inspirations (PDF joint)

Cette application a été inspirée par l’article « Building Your First AI
Chatbot with Ollama and Gradio » de Yunus Kılıç, analysé dans le fichier
`influences.md`. Ce fichier dresse la liste de dix idées clés extraites du
PDF et explique leur adaptation à notre stack Next.js/RAG. Vous y
trouverez, par exemple, l’importance de conserver un historique des
conversations, d’offrir un streaming de réponses pour améliorer
l’expérience utilisateur ou encore de proposer des personas pour varier
les styles de réponses【948476518596150†L186-L219】.

## 📚 Décision d’architecture

Le fichier `decision_log.md` détaille la comparaison des options proposées
(SQL, Firestore, LowDB) et justifie le choix de l’Option A (Prisma +
SQLite/PostgreSQL) comme étant la plus simple et la plus robuste pour
déployer rapidement une application multi‑utilisateur avec mémoire.

## 📦 Déploiement

Pour déployer l’application sur Vercel ou un autre hébergeur :

- Configurez les variables d’environnement (comme ci‑dessus) dans les
  paramètres du projet.
- Utilisez une base PostgreSQL managée et ajustez `DATABASE_PROVIDER` et
  `DATABASE_URL` en conséquence.
- Exécutez `npx prisma migrate deploy` lors du déploiement pour appliquer
  les migrations (ou continuez à utiliser `db push` si vous préférez une
  approche sans historique).

## 🛠️ Scripts utiles

- `npm run dev` : démarre le serveur Next.js en mode développement.
- `npm run build` : compile l’application pour la production.
- `npm start` : lance l’application Next.js construite.
- `npm test` : exécute les tests unitaires avec Vitest.

## 🙏 Remerciements

Merci d’utiliser Coach Mike. N’hésitez pas à étendre cette base pour ajouter
de nouvelles fonctionnalités telles qu’un enregistrement des transcriptions,
des personas d’entraînement ou un streaming des réponses en temps réel !