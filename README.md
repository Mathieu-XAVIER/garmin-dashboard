# 🏃 Garmin Dashboard

Interface web personnalisée pour visualiser ses données Garmin Connect — alternative claire et lisible à l'application officielle.

## Stack

- **Backend** : Python 3.11+ · FastAPI · SQLite · APScheduler
- **Frontend** : Vue 3 · Vite · Pinia · ApexCharts
- **Source de données** : [`python-garminconnect`](https://github.com/cyberjunky/python-garminconnect)

## Fonctionnalités

- 📊 Activités (course, vélo, natation…) avec métriques détaillées
- ❤️ Fréquence cardiaque, HRV, zones d'entraînement
- 🔋 Body Battery et niveau de stress journalier
- 😴 Analyse du sommeil (phases, score)
- 👣 Steps, calories, intensité
- 🔄 Synchronisation automatique toutes les heures

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
cp .env.example .env       # Renseigner les identifiants Garmin Connect
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Configuration

Copier `backend/.env.example` en `backend/.env` et renseigner :

```env
GARMIN_EMAIL=ton.email@example.com
GARMIN_PASSWORD=ton_mot_de_passe
```

## Architecture

```
garmin-dashboard/
├── backend/
│   ├── main.py              # FastAPI app + CORS + startup
│   ├── garmin_client.py     # Wrapper python-garminconnect
│   ├── scheduler.py         # Synchro automatique (APScheduler)
│   ├── database.py          # SQLite, modèles, helpers
│   ├── routes/
│   │   ├── activities.py    # Endpoints activités
│   │   ├── health.py        # Endpoints santé (sommeil, HRV, body battery…)
│   │   └── stats.py         # Statistiques agrégées
│   ├── requirements.txt
│   └── .env.example
└── frontend/                # Vue 3 (à scaffolder)
```

## Données disponibles

| Catégorie | Métriques |
|---|---|
| Activités | Distance, durée, allure, FC moy/max, cadence, VO2max estimé, zones |
| Santé quotidienne | Steps, calories, intensité, stress, body battery |
| Sommeil | Durée, phases (léger/profond/REM), score, SpO2 nocturne |
| Cardio | FC au repos, HRV, variabilité |
