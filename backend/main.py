"""
main.py — Point d'entrée de l'API Garmin Dashboard.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import init_db
from garmin_client import GarminClient
from scheduler import sync_all, setup_scheduler
from routes.activities import router as activities_router
from routes.health import router as health_router
from routes.stats import router as stats_router
from routes.profile import router as profile_router

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

garmin_client = GarminClient(
    email=os.getenv("GARMIN_EMAIL", ""),
    password=os.getenv("GARMIN_PASSWORD", ""),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Démarrage de l'application…")
    init_db()
    logger.info("Base de données initialisée ✓")
    garmin_client.connect()
    initial_days = int(os.getenv("INITIAL_SYNC_DAYS", "90"))
    logger.info(f"Synchro initiale sur {initial_days} jours…")
    await sync_all(garmin_client, days_back=initial_days)
    interval = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))
    setup_scheduler(garmin_client, interval_minutes=interval)
    yield
    logger.info("Arrêt de l'application")


app = FastAPI(
    title="Garmin Dashboard API",
    description="API pour visualiser les données Garmin Connect",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(activities_router)
app.include_router(health_router)
app.include_router(stats_router)
app.include_router(profile_router)


@app.get("/")
def root():
    return {"status": "ok", "message": "Garmin Dashboard API"}


@app.post("/sync")
async def manual_sync(days: int = 7):
    summary = await sync_all(garmin_client, days_back=days)
    return {"status": "ok", "summary": summary}


@app.get("/health-check")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
