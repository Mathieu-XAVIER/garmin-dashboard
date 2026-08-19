"""
main.py — Point d'entrée de l'API Garmin Dashboard.
"""

import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from sqlalchemy import desc

from database import init_db, get_db, User, SyncLog
from garmin_manager import GarminManager
from scheduler import sync_user, sync_all_users, setup_scheduler, syncs_en_cours
from auth import get_current_user
from discord_logger import setup_discord_logging
from routes.activities import router as activities_router
from routes.health import router as health_router
from routes.stats import router as stats_router
from routes.profile import router as profile_router
from routes.auth import router as auth_router
from routes.preferences import router as preferences_router
from routes.goals import router as goals_router
from routes.export import router as export_router
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
setup_discord_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Démarrage de l'application…")
    init_db()
    app.state.garmin_manager = GarminManager()
    logger.info("Base de données initialisée ✓")

    if os.getenv("RUN_SCHEDULER", "true").lower() in ("1", "true", "yes"):
        interval = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))
        setup_scheduler(app.state.garmin_manager, interval_minutes=interval)
    else:
        logger.info("Scheduler désactivé sur ce process (RUN_SCHEDULER=false)")
    yield
    logger.info("Arrêt de l'application")


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Garmin Dashboard API",
    description="API pour visualiser les données Garmin Connect",
    version="0.2.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:3000")
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(activities_router)
app.include_router(health_router)
app.include_router(stats_router)
app.include_router(profile_router)
app.include_router(preferences_router)
app.include_router(goals_router)
app.include_router(export_router)


@app.get("/")
def root():
    return {"status": "ok", "message": "Garmin Dashboard API"}


@app.post("/sync")
@limiter.limit("6/hour")
async def manual_sync(
    request: Request,
    days: int = Query(7, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    manager = app.state.garmin_manager
    client = manager.get_client(current_user)
    if not client:
        return {"status": "error", "message": "Identifiants Garmin non configurés"}

    if current_user.id in syncs_en_cours:
        raise HTTPException(409, "Une synchronisation est déjà en cours")

    syncs_en_cours.add(current_user.id)
    try:
        summary = await sync_user(client, current_user.id, db,
                                  days_back=days, declencheur="manuel")
    finally:
        syncs_en_cours.discard(current_user.id)
    return {"status": "ok", "summary": summary}


def _serialiser_log(log: SyncLog) -> dict:
    return {
        "id": log.id,
        "declencheur": log.declencheur,
        "started_at": log.started_at,
        "finished_at": log.finished_at,
        "statut": log.statut,
        "days_back": log.days_back,
        "activities": log.activities,
        "daily_health": log.daily_health,
        "sleep": log.sleep,
        "hrv": log.hrv,
        "erreur": log.erreur,
    }


@app.get("/sync/status")
def sync_status(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Dernières synchros de l'utilisateur, la plus récente en tête."""
    logs = (
        db.query(SyncLog)
        .filter(SyncLog.user_id == current_user.id)
        .order_by(desc(SyncLog.started_at))
        .limit(limit)
        .all()
    )
    return {
        "en_cours": current_user.id in syncs_en_cours,
        "a_des_identifiants": bool(
            current_user.garmin_email and current_user.garmin_password_encrypted
        ),
        "derniere": _serialiser_log(logs[0]) if logs else None,
        "historique": [_serialiser_log(l) for l in logs],
    }


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
