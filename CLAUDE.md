# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projet

Dashboard web multi-utilisateurs pour visualiser les données Garmin Connect. Le backend synchronise périodiquement les données via `python-garminconnect` et les stocke dans SQLite. Le frontend les affiche avec des graphiques ApexCharts. Chaque utilisateur s'inscrit, se connecte (JWT), et saisit ses identifiants Garmin dans son profil.

## Commandes

### Backend (depuis `backend/`)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py                    # lance FastAPI sur :8000 avec reload

pip install -r requirements-dev.txt
pytest -q                         # suite complète
pytest tests/test_isolation.py    # un seul fichier
pytest -q --cov=. --cov-report=term   # avec couverture
```

### Frontend (depuis `frontend/`)

```bash
npm install
npm run dev                       # Vite dev server sur :5173
npm run build                     # build prod (type-check + vite build)
npm run type-check                # vue-tsc uniquement
```

### Docker

```bash
docker compose up                 # lance backend + frontend
```

## Architecture

Monorepo à deux dossiers : `backend/` (Python/FastAPI) et `frontend/` (Vue 3/Vite/TypeScript).

### Backend

- **`main.py`** — Point d'entrée FastAPI. Le `lifespan` initialise la DB, crée le `GarminManager`, et lance le scheduler.
- **`auth.py`** — Utilitaires d'authentification : JWT (python-jose HS256), hachage bcrypt (passlib), chiffrement Fernet des mots de passe Garmin, dépendance `get_current_user`.
- **`garmin_client.py`** — Wrapper `python-garminconnect` avec reconnexion automatique et cooldown de 5 min après échec. Reprend les jetons de session mémorisés pour éviter un login SSO (et un MFA) à chaque redémarrage ; expose `demarrer_login_mfa()` / `terminer_login_mfa()`.
- **`mailer.py`** — Envoi SMTP (stdlib). Sans `SMTP_HOST`, les messages partent dans les logs.
- **`garmin_manager.py`** — Pool de `GarminClient` par utilisateur. Cache les instances, les invalide au changement de credentials.
- **`database.py`** — Modèles SQLAlchemy (User, Activity, DailyHealth, Sleep, HRV, BodyComposition, TrainingReadiness, RacePrediction, Goal, PasswordResetToken, SyncLog) et session SQLite. Toutes les tables de données ont un `user_id` FK vers `users`. La DB est `backend/garmin.db`.
- **`scheduler.py`** — `sync_all_users()` itère les utilisateurs avec credentials Garmin et appelle `sync_user()` pour chacun. APScheduler le relance toutes les N minutes.
- **`routes/`** — Chaque fichier est un `APIRouter` monté dans `main.py` :
  - `auth.py` (`/auth`) — inscription, connexion, `/auth/me`, mot de passe (changement, oubli, réinitialisation), credentials Garmin (PUT/DELETE) et code MFA (`/auth/garmin-mfa`)
  - `activities.py` (`/activities`) — liste paginée, filtre par type, détail avec zones FC/splits (protégé, filtré par user_id)
  - `health.py` (`/health`) — santé quotidienne, sommeil, HRV (protégé, filtré par user_id)
  - `stats.py` (`/stats`) — résumé global, stats hebdomadaires, charge d'entraînement (protégé, filtré par user_id)
  - `profile.py` (`/profile`) — score de forme composite, historique VO2max, CTL/ATL, records perso, streak (protégé, filtré par user_id)
  - `preferences.py` (`/preferences`) — préférences de navigation, masquage des onglets (protégé, filtré par user_id)
  - `goals.py` (`/goals`) — objectifs hebdomadaires et progression sur la semaine calendaire (lundi → dimanche)
  - `export.py` (`/export`) — export CSV des activités et de la santé, GPX par activité (protégé ; le front télécharge en blob, un lien direct n'enverrait pas le Bearer)

### Frontend

- **`api.ts`** — Instance axios partagée avec intercepteurs : ajoute le Bearer token, redirige vers `/login` si 401.
- **Stores Pinia** : `auth.ts` (inscription, connexion, gestion credentials Garmin), `garmin.ts` (store principal), `profile.ts`, `nav.ts` (masquage des onglets), `notifications.ts`. Tous utilisent l'instance `api` partagée.
- **Router** : lazy-loaded views avec guard `beforeEach` — redirige vers `/login` si pas de token. Route `/login` marquée `meta: { public: true }`.
- **Composants** : `components/charts/` (AreaChart, BarChart, DonutChart, LineChart wrappant ApexCharts), `components/cards/` (MetricCard, ActivityRow), SkeletonLoader, EmptyState.
- **Alias** : `@` → `frontend/src/` (configuré dans vite.config.ts).

### Flux de données

Inscription → JWT → Saisie credentials Garmin (chiffrés Fernet) → `GarminManager` → `scheduler.py` (parse + upsert avec user_id) → SQLite → routes FastAPI (protégées, filtrées par user) → stores Pinia (axios + Bearer) → composants Vue.

## Variables d'environnement (backend/.env)

- `JWT_SECRET_KEY` — clé secrète pour signer les tokens JWT (générer avec `openssl rand -hex 32`)
- `GARMIN_CREDENTIAL_KEY` — clé Fernet pour chiffrer les mots de passe Garmin en DB
- `RUN_SCHEDULER` — lancer le scheduler dans ce process (défaut `true` ; mettre `false` sur les workers secondaires, sinon chaque worker synchronise en parallèle)
- `ALLOW_REGISTRATION` — ouvrir les inscriptions (défaut `true`)
- `FRONTEND_URL` — base des liens de réinitialisation de mot de passe
- `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` — envoi d'e-mails ; sans `SMTP_HOST`, les liens sont journalisés
- `SYNC_INTERVAL_MINUTES` — intervalle de synchro auto (défaut 60)
- `INITIAL_SYNC_DAYS` — profondeur d'historique au premier démarrage (défaut 90)
- `HOST` / `PORT` — serveur uvicorn (défaut 0.0.0.0:8000)

## Conventions

- Langue du code et des messages : français (logs, commentaires, noms d'endpoints descriptifs).
- Chaque payload Garmin brut est stocké dans une colonne `raw` JSON pour pouvoir extraire de nouvelles métriques sans re-synchro.
- Les routes retournent des dicts sérialisés manuellement (pas de schemas Pydantic en réponse, sauf pour les inputs POST).
- Toutes les routes de données sont protégées par `Depends(get_current_user)` et filtrées par `user_id`.
- Les dates ne se comparent jamais à une chaîne ISO : passer par `date_utils.day_start` / `day_after` (une colonne DateTime comparée à `'2026-08-19'` vaut minuit et perd la journée).
- Toute synchro passe par `scheduler.sync_user`, qui déporte les appels Garmin bloquants dans un thread et journalise le résultat dans `SyncLog`.
- Les appels Garmin coûtent du quota : les pesées et les prédictions de course se récupèrent par plage (un appel par synchro), et la disponibilité à l'entraînement est limitée aux `JOURS_READINESS` derniers jours puisqu'elle coûte un appel par jour.
- Garmin exprime les poids et masses corporelles **en grammes** : `_parse_body_composition` convertit en kilos.
- Les tests vivent dans `backend/tests/`. `conftest.py` fixe l'environnement (base temporaire, quotas désactivés, webhook Discord neutralisé) **avant** tout import applicatif : `database.py` lit `DATABASE_URL` à l'import pour construire son engine.
- Toute route de données doit être couverte par `tests/test_isolation.py`, qui vérifie qu'un utilisateur ne voit jamais les données d'un autre.
- CORS autorise `localhost:5173` et `localhost:3000`.

## Spec-Driven Development (spec-kit)

Le projet utilise [spec-kit](https://github.com/github/spec-kit) pour développer les nouvelles fonctionnalités à partir de spécifications.

- **`.specify/`** — templates, scripts bash et `memory/constitution.md` (principes du projet, à remplir).
- **`.claude/skills/speckit-*/`** — skills installées, invocables en slash commands.
- **`specs/`** — un dossier par fonctionnalité (spec, plan, tasks), créé par `/speckit-specify`.

Workflow type : `/speckit-constitution` (une fois) → `/speckit-specify` → `/speckit-clarify` (optionnel) → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`.

Mise à jour de l'outil : `uv tool upgrade specify-cli` puis `specify init --here --integration claude --script sh --force`.
