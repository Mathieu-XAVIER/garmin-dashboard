"""
routes/activities.py — Endpoints pour les activités sportives.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import date, timedelta
from typing import Optional

from database import get_db, Activity, User
from auth import get_current_user

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("/")
def list_activities(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    activity_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Activity).filter(Activity.user_id == current_user.id).order_by(desc(Activity.start_time))
    if activity_type:
        query = query.filter(Activity.activity_type == activity_type)
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return {"total": total, "offset": offset, "limit": limit, "items": [_serialize(a) for a in items]}


@router.get("/recent")
def recent_activities(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = date.today() - timedelta(days=days)
    items = (
        db.query(Activity)
        .filter(Activity.user_id == current_user.id, Activity.start_time >= since.isoformat())
        .order_by(desc(Activity.start_time))
        .all()
    )
    return [_serialize(a) for a in items]


@router.get("/types")
def activity_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(Activity.activity_type).filter(Activity.user_id == current_user.id).distinct().all()
    return [r[0] for r in rows if r[0]]


@router.get("/{garmin_id}")
def get_activity(
    garmin_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    activity = db.query(Activity).filter(
        Activity.garmin_id == garmin_id,
        Activity.user_id == current_user.id,
    ).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activité introuvable")

    data = _serialize(activity, include_raw=True)
    data["hr_zones_detail"] = _extract_hr_zones(activity.raw)
    data["splits"] = _extract_splits(activity.raw)
    data["metrics_timeline"] = _extract_timeline(activity.raw)
    return data


@router.get("/{garmin_id}/gps")
def get_activity_gps(
    garmin_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    activity = db.query(Activity).filter(
        Activity.garmin_id == garmin_id,
        Activity.user_id == current_user.id,
    ).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activité introuvable")

    if activity.gps_track:
        return {
            "garmin_id": garmin_id,
            "has_gps": True,
            "track": activity.gps_track,
            "start_end": _extract_start_end(activity),
        }

    raw = activity.raw or {}
    if not raw.get("hasPolyline"):
        return {"garmin_id": garmin_id, "has_gps": False, "track": []}

    manager = request.app.state.garmin_manager
    client = manager.get_client(current_user)
    if not client:
        raise HTTPException(400, "Identifiants Garmin non configurés")

    polyline = client.get_activity_gps(int(garmin_id))

    if not polyline:
        return {"garmin_id": garmin_id, "has_gps": False, "track": []}

    track = [
        {
            "lat": pt.get("lat"),
            "lon": pt.get("lon"),
            "altitude": pt.get("altitude"),
            "time": pt.get("time"),
            "speed": pt.get("speed"),
            "hr": pt.get("heartRate"),
        }
        for pt in polyline
        if pt.get("lat") is not None and pt.get("lon") is not None
    ]

    activity.gps_track = track
    db.commit()

    return {
        "garmin_id": garmin_id,
        "has_gps": True,
        "track": track,
        "start_end": _extract_start_end(activity),
    }


def _extract_start_end(activity: Activity) -> dict:
    raw = activity.raw or {}
    return {
        "start_lat": raw.get("startLatitude"),
        "start_lon": raw.get("startLongitude"),
        "end_lat": raw.get("endLatitude"),
        "end_lon": raw.get("endLongitude"),
    }


def _extract_hr_zones(raw: dict | None) -> list[dict]:
    if not raw:
        return []

    zones_raw = raw.get("heartRateZones") or raw.get("timeInHrZone") or []
    if not zones_raw:
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
    if not raw:
        return {}

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
        "has_gps": bool((a.raw or {}).get("hasPolyline")),
    }
    if include_raw:
        data["raw"] = a.raw
    return data
