"""
routes/auth.py — Inscription, connexion, gestion des identifiants Garmin.
"""

import hashlib
import os
import asyncio
import logging
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from database import (
    get_db, User, Activity, DailyHealth,
    Sleep, HRV, PasswordResetToken, SyncLog,
)
from auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    encrypt_garmin_password,
    get_current_user,
)
from garmin_client import GarminClient
from garminconnect import (
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
)
from mailer import envoyer_email, smtp_configure
from scheduler import sync_user, syncs_en_cours

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterInput(BaseModel):
    email: str
    password: str


class GarminCredentialsInput(BaseModel):
    garmin_email: str
    garmin_password: str


class GarminMfaInput(BaseModel):
    code: str


class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordInput(BaseModel):
    email: str


class ResetPasswordInput(BaseModel):
    token: str
    new_password: str


LONGUEUR_MIN_MOT_DE_PASSE = 8
DUREE_VALIDITE_RESET = timedelta(hours=1)


def _valider_mot_de_passe(mot_de_passe: str):
    if len(mot_de_passe) < LONGUEUR_MIN_MOT_DE_PASSE:
        raise HTTPException(
            400,
            f"Le mot de passe doit contenir au moins {LONGUEUR_MIN_MOT_DE_PASSE} caractères",
        )


def _hacher_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/register")
@limiter.limit("5/minute")
def register(request: Request, body: RegisterInput, db: Session = Depends(get_db)):
    if os.getenv("ALLOW_REGISTRATION", "true").lower() not in ("1", "true", "yes"):
        raise HTTPException(403, "Les inscriptions sont fermées sur cette instance")

    _valider_mot_de_passe(body.password)

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
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "has_garmin_credentials": bool(current_user.garmin_email and current_user.garmin_password_encrypted),
        "garmin_mfa_pending": current_user.id in _mfa_en_attente,
        "garmin_email": current_user.garmin_email,
        "created_at": current_user.created_at,
        "nav_preferences": current_user.nav_preferences,
    }




# ── Mot de passe ──────────────────────────────────────────────────────


@router.put("/password")
def change_password(
    body: ChangePasswordInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(400, "Mot de passe actuel incorrect")
    _valider_mot_de_passe(body.new_password)
    current_user.hashed_password = get_password_hash(body.new_password)
    db.commit()
    return {"status": "ok"}


@router.post("/forgot-password")
@limiter.limit("5/hour")
def forgot_password(request: Request, body: ForgotPasswordInput, db: Session = Depends(get_db)):
    """Envoie un lien de réinitialisation.

    La réponse est volontairement identique que le compte existe ou non :
    l'endpoint ne doit pas permettre d'énumérer les adresses inscrites.
    """
    reponse = {
        "status": "ok",
        "message": "Si un compte existe pour cette adresse, un lien vient d'être envoyé.",
    }

    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        return reponse

    # Les demandes précédentes encore valides sont neutralisées.
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({PasswordResetToken.used_at: datetime.utcnow()})

    token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=_hacher_token(token),
        expires_at=datetime.utcnow() + DUREE_VALIDITE_RESET,
    ))
    db.commit()

    base = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    lien = f"{base}/reset-password?token={token}"
    envoyer_email(
        user.email,
        "Réinitialisation de votre mot de passe",
        "Vous avez demandé à réinitialiser votre mot de passe.\n\n"
        f"Ouvrez ce lien pour choisir un nouveau mot de passe :\n{lien}\n\n"
        "Ce lien expire dans 1 heure et ne peut servir qu'une fois.\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.",
    )
    return reponse


@router.post("/reset-password")
@limiter.limit("10/hour")
def reset_password(request: Request, body: ResetPasswordInput, db: Session = Depends(get_db)):
    _valider_mot_de_passe(body.new_password)

    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == _hacher_token(body.token),
        PasswordResetToken.used_at.is_(None),
    ).first()
    if not reset or reset.expires_at < datetime.utcnow():
        raise HTTPException(400, "Lien invalide ou expiré")

    user = db.query(User).filter(User.id == reset.user_id).first()
    if not user:
        raise HTTPException(400, "Lien invalide ou expiré")

    user.hashed_password = get_password_hash(body.new_password)
    reset.used_at = datetime.utcnow()
    db.commit()
    return {"status": "ok", "message": "Mot de passe mis à jour"}


# ── Garmin Connect ────────────────────────────────────────────────────


# Logins Garmin suspendus en attente d'un code MFA. L'objet de session ne
# peut pas être sérialisé : il reste en mémoire, avec une péremption courte.
_mfa_en_attente: dict[int, dict] = {}
DUREE_VALIDITE_MFA = timedelta(minutes=10)


def _purger_mfa_expires():
    limite = datetime.utcnow() - DUREE_VALIDITE_MFA
    for uid in [u for u, v in _mfa_en_attente.items() if v["depuis"] < limite]:
        _mfa_en_attente.pop(uid, None)


def _lancer_synchro_initiale(manager, user_id: int):
    initial_days = int(os.getenv("INITIAL_SYNC_DAYS", "90"))
    logger.info(f"Synchro initiale de {initial_days} jours pour user {user_id}")
    asyncio.create_task(_initial_sync(manager, user_id, initial_days))


@router.put("/garmin-credentials")
async def update_garmin_credentials(
    body: GarminCredentialsInput,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Les identifiants sont enregistrés avant la tentative de connexion :
    # le client a besoin d'eux, et un MFA en attente ne doit pas les perdre.
    current_user.garmin_email = body.garmin_email
    current_user.garmin_password_encrypted = encrypt_garmin_password(body.garmin_password)
    current_user.garmin_tokens_encrypted = None  # jetons de l'ancien compte
    db.commit()

    manager = request.app.state.garmin_manager
    manager.invalidate(current_user.id)
    _mfa_en_attente.pop(current_user.id, None)
    _purger_mfa_expires()

    client = manager.get_client(current_user)
    reponse = {
        "status": "ok",
        "garmin_email": body.garmin_email,
        "credentials_valid": False,
        "mfa_required": False,
        "message": None,
    }

    try:
        statut, en_attente = await asyncio.to_thread(client.demarrer_login_mfa)
    except GarminConnectAuthenticationError as e:
        logger.info(f"Identifiants Garmin refusés pour user {current_user.id} : {e}")
        reponse["message"] = (
            "Garmin a refusé ces identifiants. Vérifiez l'adresse e-mail et le "
            "mot de passe de votre compte Garmin Connect."
        )
        return reponse
    except GarminConnectTooManyRequestsError:
        reponse["message"] = (
            "Garmin a temporairement bloqué les tentatives de connexion "
            "(trop d'essais). Réessayez dans quelques minutes."
        )
        return reponse
    except Exception as e:
        logger.warning(f"Connexion Garmin impossible pour user {current_user.id} : {e}")
        reponse["message"] = f"Connexion à Garmin Connect impossible : {e}"
        return reponse

    if statut == "mfa":
        garmin, state = en_attente
        _mfa_en_attente[current_user.id] = {
            "client": client, "garmin": garmin, "state": state,
            "depuis": datetime.utcnow(),
        }
        reponse["mfa_required"] = True
        reponse["message"] = (
            "Garmin demande un code de vérification. Saisissez celui reçu par "
            "e-mail ou sur votre application d'authentification."
        )
        return reponse

    reponse["credentials_valid"] = True
    _lancer_synchro_initiale(manager, current_user.id)
    return reponse


@router.post("/garmin-mfa")
async def submit_garmin_mfa(
    body: GarminMfaInput,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Termine un login Garmin suspendu en fournissant le code MFA."""
    _purger_mfa_expires()
    en_attente = _mfa_en_attente.get(current_user.id)
    if not en_attente:
        raise HTTPException(
            400,
            "Aucune demande de code en cours, ou délai dépassé. "
            "Ressaisissez vos identifiants Garmin.",
        )

    try:
        await asyncio.to_thread(
            en_attente["client"].terminer_login_mfa,
            en_attente["garmin"], en_attente["state"], body.code.strip(),
        )
    except Exception as e:
        logger.info(f"Code MFA refusé pour user {current_user.id} : {e}")
        raise HTTPException(400, "Code de vérification refusé par Garmin.")

    _mfa_en_attente.pop(current_user.id, None)
    _lancer_synchro_initiale(request.app.state.garmin_manager, current_user.id)
    return {"status": "ok", "credentials_valid": True}


async def _initial_sync(manager, user_id: int, days: int):
    from database import SessionLocal

    if user_id in syncs_en_cours:
        logger.info(f"Synchro déjà en cours pour user {user_id}, initiale ignorée")
        return

    syncs_en_cours.add(user_id)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        client = manager.get_client(user)
        if client and await asyncio.to_thread(lambda: client.client):
            await sync_user(client, user_id, db, days_back=days, declencheur="initiale")
    except Exception as e:
        logger.error(f"Erreur synchro initiale user {user_id}: {e}", exc_info=True)
    finally:
        db.close()
        syncs_en_cours.discard(user_id)


@router.delete("/garmin-credentials")
def delete_garmin_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.garmin_email = None
    current_user.garmin_password_encrypted = None
    current_user.garmin_tokens_encrypted = None
    db.commit()
    _mfa_en_attente.pop(current_user.id, None)
    return {"status": "ok"}


@router.delete("/account")
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Supprime le compte et toutes les données associées (RGPD)."""
    user_id = current_user.id

    # Supprimer toutes les données de l'utilisateur
    for model in (Activity, DailyHealth, Sleep, HRV, SyncLog, PasswordResetToken):
        db.query(model).filter_by(user_id=user_id).delete()

    db.delete(current_user)
    db.commit()
    return {"status": "ok", "message": "Compte et données supprimés"}
