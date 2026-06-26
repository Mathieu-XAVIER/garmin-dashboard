"""
routes/auth.py — Inscription, connexion, gestion des identifiants Garmin.
"""

import os
import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from database import (
    get_db, User, CustomDashboard, Activity, DailyHealth,
    Sleep, HRV, PrepExerciseLog, CustomExerciseLog, DashboardWidget,
)
from auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    encrypt_garmin_password,
    get_current_user,
)
from garmin_client import GarminClient
from scheduler import sync_user

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterInput(BaseModel):
    email: str
    password: str


class GarminCredentialsInput(BaseModel):
    garmin_email: str
    garmin_password: str


@router.post("/register")
@limiter.limit("5/minute")
def register(request: Request, body: RegisterInput, db: Session = Depends(get_db)):
    if len(body.password) < 6:
        raise HTTPException(400, "Le mot de passe doit contenir au moins 6 caractères")

    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(400, "Un compte existe déjà avec cet email")

    user = User(
        email=body.email,
        hashed_password=get_password_hash(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dashboards = (
        db.query(CustomDashboard)
        .filter_by(user_id=current_user.id)
        .order_by(CustomDashboard.position)
        .all()
    )
    return {
        "id": current_user.id,
        "email": current_user.email,
        "has_garmin_credentials": bool(current_user.garmin_email and current_user.garmin_password_encrypted),
        "garmin_email": current_user.garmin_email,
        "created_at": current_user.created_at,
        "nav_preferences": current_user.nav_preferences,
        "custom_dashboards": [
            {"id": d.id, "name": d.name, "slug": d.slug, "icon": d.icon, "position": d.position}
            for d in dashboards
        ],
    }


@router.put("/garmin-credentials")
async def update_garmin_credentials(
    body: GarminCredentialsInput,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    credentials_valid = False
    client = GarminClient(body.garmin_email, body.garmin_password)
    try:
        credentials_valid = client.connect()
    except Exception:
        credentials_valid = False

    current_user.garmin_email = body.garmin_email
    current_user.garmin_password_encrypted = encrypt_garmin_password(body.garmin_password)
    db.commit()

    manager = request.app.state.garmin_manager
    manager.invalidate(current_user.id)

    if credentials_valid:
        initial_days = int(os.getenv("INITIAL_SYNC_DAYS", "90"))
        logger.info(f"Synchro initiale de {initial_days} jours pour user {current_user.id}")
        asyncio.create_task(_initial_sync(manager, current_user, initial_days))

    return {
        "status": "ok",
        "garmin_email": body.garmin_email,
        "credentials_valid": credentials_valid,
    }


async def _initial_sync(manager, user, days):
    from database import SessionLocal
    db = SessionLocal()
    try:
        client = manager.get_client(user)
        if client and client.client:
            await sync_user(client, user.id, db, days_back=days)
    except Exception as e:
        logger.error(f"Erreur synchro initiale user {user.id}: {e}")
    finally:
        db.close()


@router.delete("/garmin-credentials")
def delete_garmin_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.garmin_email = None
    current_user.garmin_password_encrypted = None
    db.commit()
    return {"status": "ok"}


@router.delete("/account")
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Supprime le compte et toutes les données associées (RGPD)."""
    user_id = current_user.id

    # Supprimer les widgets des dashboards de l'utilisateur
    dashboards = db.query(CustomDashboard).filter_by(user_id=user_id).all()
    for dashboard in dashboards:
        db.query(DashboardWidget).filter_by(dashboard_id=dashboard.id).delete()
        db.query(CustomExerciseLog).filter_by(dashboard_id=dashboard.id).delete()
    db.query(CustomDashboard).filter_by(user_id=user_id).delete()

    # Supprimer toutes les données de l'utilisateur
    for model in (Activity, DailyHealth, Sleep, HRV, PrepExerciseLog, CustomExerciseLog):
        db.query(model).filter_by(user_id=user_id).delete()

    db.delete(current_user)
    db.commit()
    return {"status": "ok", "message": "Compte et données supprimés"}
