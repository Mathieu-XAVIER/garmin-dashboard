# Garmin Dashboard

Dashboard web multi-utilisateurs pour visualiser ses données Garmin Connect. Alternative claire et responsive à l'application officielle, consultable sur desktop et mobile.

## Stack

- **Backend** : Python 3.11+ / FastAPI / SQLite / APScheduler
- **Frontend** : Vue 3 / Vite / TypeScript / Pinia / ApexCharts
- **Auth** : JWT (python-jose) + bcrypt + chiffrement Fernet des credentials Garmin
- **Source de données** : [`python-garminconnect`](https://github.com/cyberjunky/python-garminconnect)
- **Déploiement** : Docker Compose

## Fonctionnalités

- Multi-utilisateurs avec inscription/connexion (JWT)
- Credentials Garmin chiffrés (Fernet) et gérés par utilisateur
- Synchronisation automatique périodique (configurable)
- Dashboard principal avec KPIs, Body Battery, HRV, activités récentes
- Activités détaillées : distance, durée, allure, FC, zones, splits, carte GPS
- Santé quotidienne : steps, calories, stress, body battery, FC repos
- Sommeil : score, phases (profond/léger/REM), SpO2
- Profil : score de forme composite, CTL/ATL/TSB, VO2max, records personnels
- Prépa handball : suivi d'objectifs course + exercices (pompes, squats, abdos)
- Dashboards personnalisés : widgets configurables (métriques, graphiques, objectifs, exercices)
- Navigation personnalisable (masquer/afficher les onglets)
- Interface responsive : bottom nav mobile, menu hamburger, tableaux scrollables, modals adaptés

## Installation

### Prérequis

- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # Renseigner les variables (voir Configuration)
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker compose up
```

## Configuration

Variables d'environnement dans `backend/.env` :

| Variable | Description | Défaut |
|---|---|---|
| `JWT_SECRET_KEY` | Clé secrète pour signer les tokens JWT | (obligatoire) |
| `GARMIN_CREDENTIAL_KEY` | Clé Fernet pour chiffrer les mots de passe Garmin | (obligatoire) |
| `SYNC_INTERVAL_MINUTES` | Intervalle de synchro automatique | `60` |
| `INITIAL_SYNC_DAYS` | Profondeur d'historique au premier démarrage | `90` |
| `HOST` / `PORT` | Adresse et port du serveur | `0.0.0.0` / `8000` |
| `DISCORD_WEBHOOK_URL` | Webhook Discord pour remonter les erreurs (optionnel) | — |

Générer les clés :

```bash
# JWT
openssl rand -hex 32

# Fernet
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Architecture

```
garmin-dashboard/
├── backend/
│   ├── main.py              # FastAPI + lifespan (init DB, GarminManager, scheduler)
│   ├── auth.py              # JWT, bcrypt, Fernet, get_current_user
│   ├── garmin_client.py     # Wrapper python-garminconnect (reconnexion + cooldown)
│   ├── garmin_manager.py    # Pool de GarminClient par utilisateur
│   ├── scheduler.py         # sync_all_users() via APScheduler
│   ├── database.py          # Modèles SQLAlchemy (User, Activity, DailyHealth, Sleep, HRV…)
│   ├── routes/
│   │   ├── auth.py          # /auth — inscription, connexion, credentials Garmin
│   │   ├── activities.py    # /activities — liste, filtres, détail avec zones/splits
│   │   ├── health.py        # /health — santé quotidienne, sommeil, HRV
│   │   ├── stats.py         # /stats — résumé, stats hebdo, charge d'entraînement
│   │   ├── profile.py       # /profile — forme, VO2max, CTL/ATL, records, streak
│   │   └── handball.py      # /handball — suivi prépa physique handball
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.vue           # Layout : sidebar desktop + bottom nav mobile + menu hamburger
    │   ├── api.ts            # Instance axios (Bearer token, redirect 401)
    │   ├── assets/main.css   # Design tokens, reset, responsive
    │   ├── router/           # Routes lazy-loaded avec guard auth
    │   ├── stores/           # Pinia : auth, garmin, profile, handball, nav, dashboards
    │   ├── views/            # Dashboard, Activities, Health, Sleep, Profile, Handball, Custom
    │   └── components/
    │       ├── charts/       # AreaChart, BarChart, DonutChart, LineChart (ApexCharts)
    │       ├── cards/        # MetricCard, ActivityRow
    │       ├── maps/         # ActivityMap (Leaflet)
    │       ├── widgets/      # WidgetRenderer, MetricWidget, ChartWidget, ObjectiveWidget…
    │       ├── dashboard-editor/  # WidgetAddModal, DashboardCreateModal, DataSourcePicker
    │       └── sidebar/      # NavSettings
    └── index.html            # Viewport mobile, PWA meta tags
```

## Flux de données

Inscription → JWT → Saisie credentials Garmin (chiffrés Fernet) → `GarminManager` → `scheduler.py` (synchro périodique) → SQLite → Routes FastAPI (protégées par `user_id`) → Stores Pinia (axios + Bearer) → Composants Vue

## Données disponibles

| Catégorie | Métriques |
|---|---|
| Activités | Distance, durée, allure, FC moy/max, cadence, VO2max, zones FC, splits, carte GPS |
| Santé quotidienne | Steps, calories, intensité (modérée/vigoureuse), stress, body battery |
| Sommeil | Durée, phases (léger/profond/REM/éveillé), score, SpO2 nocturne |
| Cardio | FC au repos, HRV (moyenne, baseline, statut) |
| Profil | Score de forme composite, CTL/ATL/TSB, records personnels, streak |
