"""
main.py — Point d'entrée de l'API Garmin Dashboard.
"""

import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, get_db, User
from garmin_manager import GarminManager
from scheduler import sync_user, sync_all_users, setup_scheduler
from auth import get_current_user
from routes.activities import router as activities_router
from routes.health import router as health_router
from routes.stats import router as stats_router
from routes.profile import router as profile_router
from routes.handball import router as handball_router
from routes.auth import router as auth_router
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Démarrage de l'application…")
    init_db()
    app.state.garmin_manager = GarminManager()
    logger.info("Base de données initialisée ✓")

    interval = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))
    setup_scheduler(app.state.garmin_manager, interval_minutes=interval)
    yield
    logger.info("Arrêt de l'application")


app = FastAPI(
    title="Garmin Dashboard API",
    description="API pour visualiser les données Garmin Connect",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(activities_router)
app.include_router(health_router)
app.include_router(stats_router)
app.include_router(profile_router)
app.include_router(handball_router)


@app.get("/")
def root():
    return {"status": "ok", "message": "Garmin Dashboard API"}


@app.post("/sync")
async def manual_sync(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    manager = app.state.garmin_manager
    client = manager.get_client(current_user)
    if not client:
        return {"status": "error", "message": "Identifiants Garmin non configurés"}
    summary = await sync_user(client, current_user.id, db, days_back=days)
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
