"""
routes/activities.py — Endpoints pour les activités sportives.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import date, timedelta
from typing import Optional

from database import get_db, Activity

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("/")
def list_activities(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    activity_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Activity).order_by(desc(Activity.start_time))
    if activity_type:
        query = query.filter(Activity.activity_type == activity_type)
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return {"total": total, "offset": offset, "limit": limit, "items": [_s(a) for a in items]}


@router.get("/recent")
def recent_activities(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    since = date.today() - timedelta(days=days)
    items = (
        db.query(Activity)
        .filter(Activity.start_time >= since.isoformat())
        .order_by(desc(Activity.start_time))
        .all()
    )
    return [_s(a) for a in items]


@router.get("/types")
def activity_types(db: Session = Depends(get_db)):
    rows = db.query(Activity.activity_type).distinct().all()
    return [r[0] for r in rows if r[0]]


@router.get("/{garmin_id}")
def get_activity(garmin_id: str, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.garmin_id == garmin_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activité introuvable")
    return _s(activity, include_raw=True)


def _s(a: Activity, include_raw=False):
    data = {
        "id": a.id, "garmin_id": a.garmin_id, "activity_type": a.activity_type,
        "name": a.name, "start_time": a.start_time, "duration_seconds": a.duration_seconds,
        "distance_meters": a.distance_meters, "calories": a.calories,
        "avg_heart_rate": a.avg_heart_rate, "max_heart_rate": a.max_heart_rate,
        "avg_speed": a.avg_speed, "avg_cadence": a.avg_cadence,
        "training_load": a.training_load, "vo2max": a.vo2max,
        "aerobic_training_effect": a.aerobic_training_effect,
        "anaerobic_training_effect": a.anaerobic_training_effect,
        "hr_zones": a.hr_zones,
    }
    if include_raw:
        data["raw"] = a.raw
    return data
