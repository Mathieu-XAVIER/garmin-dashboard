"""
routes/goals.py — Objectifs hebdomadaires et suivi de progression.

La semaine est calendaire (lundi → dimanche) : c'est ce qu'attend un
utilisateur qui parle de « cette semaine », contrairement aux fenêtres
glissantes de /stats/weekly.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import Activity, DailyHealth, Goal, User, get_db
from date_utils import day_after, day_start

router = APIRouter(prefix="/goals", tags=["goals"])

# Métrique → libellé et unité affichés côté client.
METRIQUES = {
    "distance_km":   {"libelle": "Distance", "unite": "km", "cumul": True},
    "activites":     {"libelle": "Séances", "unite": "", "cumul": True},
    "duree_minutes": {"libelle": "Durée", "unite": "min", "cumul": True},
    "pas":           {"libelle": "Pas par jour", "unite": "pas", "cumul": False},
}


class GoalInput(BaseModel):
    metrique: str
    cible: float


class GoalsInput(BaseModel):
    objectifs: list[GoalInput]


def semaine_courante(aujourdhui: date | None = None) -> tuple[date, date]:
    """Lundi et dimanche de la semaine contenant `aujourdhui`."""
    aujourdhui = aujourdhui or date.today()
    lundi = aujourdhui - timedelta(days=aujourdhui.weekday())
    return lundi, lundi + timedelta(days=6)


def _serialiser(objectif: Goal) -> dict:
    meta = METRIQUES.get(objectif.metrique, {})
    return {
        "metrique": objectif.metrique,
        "cible": objectif.cible,
        "libelle": meta.get("libelle", objectif.metrique),
        "unite": meta.get("unite", ""),
    }


@router.get("/")
def lister_objectifs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    objectifs = db.query(Goal).filter(Goal.user_id == current_user.id).all()
    return {
        "objectifs": [_serialiser(o) for o in objectifs],
        "metriques_disponibles": [
            {"metrique": cle, **meta} for cle, meta in METRIQUES.items()
        ],
    }


@router.put("/")
def definir_objectifs(
    body: GoalsInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remplace la liste d'objectifs. Une cible nulle ou négative supprime."""
    for entree in body.objectifs:
        if entree.metrique not in METRIQUES:
            raise HTTPException(400, f"Métrique inconnue : {entree.metrique}")

    for entree in body.objectifs:
        existant = db.query(Goal).filter(
            Goal.user_id == current_user.id,
            Goal.metrique == entree.metrique,
        ).first()

        if entree.cible <= 0:
            if existant:
                db.delete(existant)
            continue

        if existant:
            existant.cible = entree.cible
        else:
            db.add(Goal(user_id=current_user.id, metrique=entree.metrique, cible=entree.cible))

    db.commit()
    objectifs = db.query(Goal).filter(Goal.user_id == current_user.id).all()
    return {"objectifs": [_serialiser(o) for o in objectifs]}


def _valeurs_de_la_semaine(db: Session, user_id: int, lundi: date, dimanche: date) -> dict:
    activites = db.query(Activity).filter(
        Activity.user_id == user_id,
        Activity.start_time >= day_start(lundi),
        Activity.start_time < day_after(dimanche),
    ).all()

    jours_sante = db.query(DailyHealth).filter(
        DailyHealth.user_id == user_id,
        DailyHealth.date >= lundi.isoformat(),
        DailyHealth.date <= dimanche.isoformat(),
        DailyHealth.steps.isnot(None),
    ).all()

    return {
        "distance_km": round(sum((a.distance_meters or 0) for a in activites) / 1000, 2),
        "activites": len(activites),
        "duree_minutes": round(sum((a.duration_seconds or 0) for a in activites) / 60),
        "pas": round(sum((j.steps or 0) for j in jours_sante) / len(jours_sante)) if jours_sante else 0,
    }


@router.get("/progress")
def progression(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lundi, dimanche = semaine_courante()
    valeurs = _valeurs_de_la_semaine(db, current_user.id, lundi, dimanche)
    objectifs = db.query(Goal).filter(Goal.user_id == current_user.id).all()

    resultat = []
    for objectif in objectifs:
        actuel = valeurs.get(objectif.metrique, 0)
        pourcentage = round(actuel / objectif.cible * 100) if objectif.cible else 0
        resultat.append({
            **_serialiser(objectif),
            "actuel": actuel,
            "pourcentage": min(pourcentage, 999),
            "atteint": actuel >= objectif.cible,
        })

    return {
        "semaine_debut": lundi.isoformat(),
        "semaine_fin": dimanche.isoformat(),
        "jours_ecoules": min((date.today() - lundi).days + 1, 7),
        "objectifs": resultat,
    }
