# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projet

Dashboard web personnel pour visualiser les données Garmin Connect. Le backend synchronise périodiquement les données via `python-garminconnect` et les stocke dans SQLite. Le frontend les affiche avec des graphiques ApexCharts.

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

- **`main.py`** — Point d'entrée FastAPI. Le `lifespan` initialise la DB, connecte Garmin, lance la synchro initiale puis le scheduler.
- **`garmin_client.py`** — Wrapper `python-garminconnect` avec reconnexion automatique et cooldown de 5 min après échec.
- **`database.py`** — Modèles SQLAlchemy (Activity, DailyHealth, Sleep, HRV, PrepExerciseLog) et session SQLite. La DB est `backend/garmin.db`.
- **`scheduler.py`** — `sync_all()` récupère activités + santé jour par jour et fait un upsert dans SQLite. APScheduler le relance toutes les N minutes. Les parsers (`_parse_activity`, `_parse_daily_health`, etc.) transforment les payloads Garmin en colonnes DB.
- **`routes/`** — Chaque fichier est un `APIRouter` monté dans `main.py` :
  - `activities.py` (`/activities`) — liste paginée, filtre par type, détail avec zones FC/splits extraits du JSON raw
  - `health.py` (`/health`) — santé quotidienne, sommeil, HRV
  - `stats.py` (`/stats`) — résumé global, stats hebdomadaires, charge d'entraînement
  - `profile.py` (`/profile`) — score de forme composite (HRV + TSB + sommeil), historique VO2max, CTL/ATL, records perso, streak
  - `handball.py` (`/handball`) — suivi prépa physique handball avec objectifs (course km, pompes, squats, abdos) et logs d'exercices CRUD

### Frontend

- **Stores Pinia** : `garmin.ts` (store principal, toutes les données dashboard), `profile.ts`, `handball.ts`. L'API base URL est hardcodée `http://localhost:8000`.
- **Router** : lazy-loaded views — Dashboard `/`, Activities `/activities`, Activity detail `/activities/:id`, Health `/health`, Sleep `/sleep`, Profile `/profile`, Handball `/handball`.
- **Composants** : `components/charts/` (AreaChart, BarChart, DonutChart, LineChart wrappant ApexCharts), `components/cards/` (MetricCard, ActivityRow), SkeletonLoader, EmptyState.
- **Alias** : `@` → `frontend/src/` (configuré dans vite.config.ts).

### Flux de données

Garmin API → `garmin_client.py` → `scheduler.py` (parse + upsert) → SQLite → routes FastAPI (JSON) → stores Pinia (axios) → composants Vue.

## Variables d'environnement (backend/.env)

- `GARMIN_EMAIL` / `GARMIN_PASSWORD` — identifiants Garmin Connect
- `SYNC_INTERVAL_MINUTES` — intervalle de synchro auto (défaut 60)
- `INITIAL_SYNC_DAYS` — profondeur d'historique au premier démarrage (défaut 90)
- `HOST` / `PORT` — serveur uvicorn (défaut 0.0.0.0:8000)

## Conventions

- Langue du code et des messages : français (logs, commentaires, noms d'endpoints descriptifs).
- Chaque payload Garmin brut est stocké dans une colonne `raw` JSON pour pouvoir extraire de nouvelles métriques sans re-synchro.
- Les routes retournent des dicts sérialisés manuellement (pas de schemas Pydantic en réponse, sauf pour les inputs POST).
- Pas de tests automatisés pour l'instant.
- CORS autorise `localhost:5173` et `localhost:3000`.