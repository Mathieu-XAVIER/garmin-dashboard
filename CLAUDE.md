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
- **`garmin_client.py`** — Wrapper `python-garminconnect` avec reconnexion automatique et cooldown de 5 min après échec.
- **`garmin_manager.py`** — Pool de `GarminClient` par utilisateur. Cache les instances, les invalide au changement de credentials.
- **`database.py`** — Modèles SQLAlchemy (User, Activity, DailyHealth, Sleep, HRV, PrepExerciseLog) et session SQLite. Toutes les tables de données ont un `user_id` FK vers `users`. La DB est `backend/garmin.db`.
- **`scheduler.py`** — `sync_all_users()` itère les utilisateurs avec credentials Garmin et appelle `sync_user()` pour chacun. APScheduler le relance toutes les N minutes.
- **`routes/`** — Chaque fichier est un `APIRouter` monté dans `main.py` :
  - `auth.py` (`/auth`) — inscription, connexion, `/auth/me`, gestion credentials Garmin (PUT/DELETE)
  - `activities.py` (`/activities`) — liste paginée, filtre par type, détail avec zones FC/splits (protégé, filtré par user_id)
  - `health.py` (`/health`) — santé quotidienne, sommeil, HRV (protégé, filtré par user_id)
  - `stats.py` (`/stats`) — résumé global, stats hebdomadaires, charge d'entraînement (protégé, filtré par user_id)
  - `profile.py` (`/profile`) — score de forme composite, historique VO2max, CTL/ATL, records perso, streak (protégé, filtré par user_id)
  - `handball.py` (`/handball`) — suivi prépa physique handball (protégé, filtré par user_id)

### Frontend

- **`api.ts`** — Instance axios partagée avec intercepteurs : ajoute le Bearer token, redirige vers `/login` si 401.
- **Stores Pinia** : `auth.ts` (inscription, connexion, gestion credentials Garmin), `garmin.ts` (store principal), `profile.ts`, `handball.ts`. Tous utilisent l'instance `api` partagée.
- **Router** : lazy-loaded views avec guard `beforeEach` — redirige vers `/login` si pas de token. Route `/login` marquée `meta: { public: true }`.
- **Composants** : `components/charts/` (AreaChart, BarChart, DonutChart, LineChart wrappant ApexCharts), `components/cards/` (MetricCard, ActivityRow), SkeletonLoader, EmptyState.
- **Alias** : `@` → `frontend/src/` (configuré dans vite.config.ts).

### Flux de données

Inscription → JWT → Saisie credentials Garmin (chiffrés Fernet) → `GarminManager` → `scheduler.py` (parse + upsert avec user_id) → SQLite → routes FastAPI (protégées, filtrées par user) → stores Pinia (axios + Bearer) → composants Vue.

## Variables d'environnement (backend/.env)

- `JWT_SECRET_KEY` — clé secrète pour signer les tokens JWT (générer avec `openssl rand -hex 32`)
- `GARMIN_CREDENTIAL_KEY` — clé Fernet pour chiffrer les mots de passe Garmin en DB
- `SYNC_INTERVAL_MINUTES` — intervalle de synchro auto (défaut 60)
- `INITIAL_SYNC_DAYS` — profondeur d'historique au premier démarrage (défaut 90)
- `HOST` / `PORT` — serveur uvicorn (défaut 0.0.0.0:8000)

## Conventions

- Langue du code et des messages : français (logs, commentaires, noms d'endpoints descriptifs).
- Chaque payload Garmin brut est stocké dans une colonne `raw` JSON pour pouvoir extraire de nouvelles métriques sans re-synchro.
- Les routes retournent des dicts sérialisés manuellement (pas de schemas Pydantic en réponse, sauf pour les inputs POST).
- Toutes les routes de données sont protégées par `Depends(get_current_user)` et filtrées par `user_id`.
- Pas de tests automatisés pour l'instant.
- CORS autorise `localhost:5173` et `localhost:3000`.
