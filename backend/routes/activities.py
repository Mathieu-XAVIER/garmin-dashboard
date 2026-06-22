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
    """Liste paginée des activités, les plus récentes en premier."""
    query = db.query(Activity).order_by(desc(Activity.start_time))
    if activity_type:
        query = query.filter(Activity.activity_type == activity_type)
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return {"total": total, "offset": offset, "limit": limit, "items": [_serialize(a) for a in items]}


@router.get("/recent")
def recent_activities(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Activités des N derniers jours."""
    since = date.today() - timedelta(days=days)
    items = (
        db.query(Activity)
        .filter(Activity.start_time >= since.isoformat())
        .order_by(desc(Activity.start_time))
        .all()
    )
    return [_serialize(a) for a in items]


@router.get("/types")
def activity_types(db: Session = Depends(get_db)):
    """Liste des types d'activités disponibles."""
    rows = db.query(Activity.activity_type).distinct().all()
    return [r[0] for r in rows if r[0]]


@router.get("/{garmin_id}")
def get_activity(garmin_id: str, db: Session = Depends(get_db)):
    """Détail complet d'une activité avec zones FC et splits."""
    activity = db.query(Activity).filter(Activity.garmin_id == garmin_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activité introuvable")

    data = _serialize(activity, include_raw=True)

    # Extraire les zones FC depuis le payload raw
    data["hr_zones_detail"] = _extract_hr_zones(activity.raw)

    # Extraire les splits
    data["splits"] = _extract_splits(activity.raw)

    # Extraire les données GPS simplifiées (élévation, vitesse)
    data["metrics_timeline"] = _extract_timeline(activity.raw)

    return data


# ---------------------------------------------------------------------------
# Parsers raw → structures utiles
# ---------------------------------------------------------------------------

def _extract_hr_zones(raw: dict | None) -> list[dict]:
    """Zones FC avec durée en secondes et pourcentage."""
    if not raw:
        return []

    # Les zones sont souvent dans heartRateZones ou timeInHrZone
    zones_raw = raw.get("heartRateZones") or raw.get("timeInHrZone") or []

    if not zones_raw:
        # Essayer dans metricDescriptors / activityDetailMetrics
        return []

    result = []
    zone_names = ["Zone 1", "Zone 2", "Zone 3", "Zone 4", "Zone 5"]
    zone_colors = ["#3B5B8F", "#00D4AA", "#F59E0B", "#FF6B35", "#EF4444"]

    for i, zone in enumerate(zones_raw[:5]):
        seconds = 0
        if isinstance(zone, dict):
            seconds = zone.get("secsInZone") or zone.get("seconds") or 0
        elif isinstance(zone, (int, float)):
            seconds = int(zone)

        result.append({
            "name": zone_names[i] if i < len(zone_names) else f"Zone {i+1}",
            "color": zone_colors[i] if i < len(zone_colors) else "#8B92A5",
            "seconds": int(seconds),
        })

    return result


def _extract_splits(raw: dict | None) -> list[dict]:
    """Splits kilométriques ou par mile."""
    if not raw:
        return []

    splits_raw = (
        raw.get("splitSummaries")
        or raw.get("lapDTOs")
        or raw.get("laps")
        or []
    )

    result = []
    for i, split in enumerate(splits_raw):
        if not isinstance(split, dict):
            continue
        result.append({
            "index": i + 1,
            "distance_meters": split.get("distance") or split.get("totalDistanceInMeters"),
            "duration_seconds": split.get("duration") or split.get("totalElapsedTime"),
            "avg_heart_rate": split.get("averageHR") or split.get("averageHeartRate"),
            "avg_speed": split.get("averageSpeed"),
            "avg_cadence": split.get("averageRunningCadenceInStepsPerMinute") or split.get("averageCadence"),
            "elevation_gain": split.get("elevationGain") or split.get("totalAscent"),
        })

    return result


def _extract_timeline(raw: dict | None) -> dict:
    """Données de timeline simplifiées : vitesse et élévation."""
    if not raw:
        return {}

    # Les données détaillées sont rarement dans le résumé d'activité
    # On extrait ce qui est disponible dans le payload
    return {
        "avg_speed": raw.get("averageSpeed"),
        "max_speed": raw.get("maxSpeed"),
        "elevation_gain": raw.get("elevationGain"),
        "elevation_loss": raw.get("elevationLoss"),
        "min_elevation": raw.get("minElevation"),
        "max_elevation": raw.get("maxElevation"),
        "avg_power": raw.get("avgPower"),
        "normalized_power": raw.get("normPower"),
        "training_stress_score": raw.get("trainingStressScore"),
    }


def _serialize(a: Activity, include_raw: bool = False) -> dict:
    data = {
        "id": a.id,
        "garmin_id": a.garmin_id,
        "activity_type": a.activity_type,
        "name": a.name,
        "start_time": a.start_time,
        "duration_seconds": a.duration_seconds,
        "distance_meters": a.distance_meters,
        "calories": a.calories,
        "avg_heart_rate": a.avg_heart_rate,
        "max_heart_rate": a.max_heart_rate,
        "avg_speed": a.avg_speed,
        "avg_cadence": a.avg_cadence,
        "training_load": a.training_load,
        "vo2max": a.vo2max,
        "aerobic_training_effect": a.aerobic_training_effect,
        "anaerobic_training_effect": a.anaerobic_training_effect,
        "hr_zones": a.hr_zones,
    }
    if include_raw:
        data["raw"] = a.raw
    return data
