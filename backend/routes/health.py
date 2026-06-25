"""
routes/health.py — Endpoints pour les données de santé quotidiennes.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import date, timedelta

from database import get_db, DailyHealth, Sleep, HRV, User
from auth import get_current_user

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/daily")
def daily_health(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = (date.today() - timedelta(days=days)).isoformat()
    items = (
        db.query(DailyHealth)
        .filter(DailyHealth.user_id == current_user.id, DailyHealth.date >= since)
        .order_by(desc(DailyHealth.date))
        .all()
    )
    return [_sd(d) for d in items]


@router.get("/daily/{date_str}")
def daily_health_by_date(
    date_str: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.query(DailyHealth).filter(
        DailyHealth.user_id == current_user.id,
        DailyHealth.date == date_str,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Données introuvables pour cette date")
    return _sd(row)


@router.get("/today")
def today_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today().isoformat()
    row = db.query(DailyHealth).filter(
        DailyHealth.user_id == current_user.id,
        DailyHealth.date == today,
    ).first()
    if not row:
        return {"date": today, "message": "Pas encore de données pour aujourd'hui"}
    return _sd(row)


@router.get("/sleep")
def sleep_history(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = (date.today() - timedelta(days=days)).isoformat()
    items = (
        db.query(Sleep)
        .filter(Sleep.user_id == current_user.id, Sleep.date >= since)
        .order_by(desc(Sleep.date))
        .all()
    )
    return [_ss(s) for s in items]


@router.get("/sleep/{date_str}")
def sleep_by_date(
    date_str: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.query(Sleep).filter(
        Sleep.user_id == current_user.id,
        Sleep.date == date_str,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Données de sommeil introuvables")
    return _ss(row)


@router.get("/hrv")
def hrv_history(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = (date.today() - timedelta(days=days)).isoformat()
    items = (
        db.query(HRV)
        .filter(HRV.user_id == current_user.id, HRV.date >= since)
        .order_by(desc(HRV.date))
        .all()
    )
    return [_sh(h) for h in items]


@router.get("/hrv/latest")
def hrv_latest(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.query(HRV).filter(HRV.user_id == current_user.id).order_by(desc(HRV.date)).first()
    if not row:
        return {"message": "Aucune donnée HRV disponible"}
    return _sh(row)


def _sd(d):
    return {
        "date": d.date, "steps": d.steps, "total_distance_meters": d.total_distance_meters,
        "calories_total": d.calories_total, "calories_active": d.calories_active,
        "floors_climbed": d.floors_climbed, "moderate_intensity_minutes": d.moderate_intensity_minutes,
        "vigorous_intensity_minutes": d.vigorous_intensity_minutes, "avg_stress": d.avg_stress,
        "max_stress": d.max_stress, "body_battery_high": d.body_battery_high,
        "body_battery_low": d.body_battery_low, "resting_heart_rate": d.resting_heart_rate,
        "avg_heart_rate": d.avg_heart_rate,
    }


def _ss(s):
    return {
        "date": s.date, "sleep_start": s.sleep_start, "sleep_end": s.sleep_end,
        "duration_seconds": s.duration_seconds, "deep_sleep_seconds": s.deep_sleep_seconds,
        "light_sleep_seconds": s.light_sleep_seconds, "rem_sleep_seconds": s.rem_sleep_seconds,
        "awake_seconds": s.awake_seconds, "sleep_score": s.sleep_score,
        "avg_spo2": s.avg_spo2, "avg_hrv": s.avg_hrv, "avg_respiration": s.avg_respiration,
    }


def _sh(h):
    return {
        "date": h.date, "weekly_avg": h.weekly_avg, "last_night_avg": h.last_night_avg,
        "last_night_5_min_high": h.last_night_5_min_high, "baseline_low": h.baseline_low,
        "baseline_high": h.baseline_high, "status": h.status,
    }
