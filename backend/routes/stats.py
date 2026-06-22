"""
routes/stats.py — Statistiques agrégées pour le dashboard.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import date, timedelta

from database import get_db, Activity, DailyHealth, Sleep, HRV

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary")
def global_summary(db: Session = Depends(get_db)):
    total_activities = db.query(Activity).count()
    total_distance = db.query(func.sum(Activity.distance_meters)).scalar() or 0
    total_calories_sport = db.query(func.sum(Activity.calories)).scalar() or 0
    last_rhr = db.query(DailyHealth.resting_heart_rate).filter(DailyHealth.resting_heart_rate.isnot(None)).order_by(desc(DailyHealth.date)).scalar()
    last_hrv = db.query(HRV.last_night_avg).filter(HRV.last_night_avg.isnot(None)).order_by(desc(HRV.date)).scalar()
    last_sleep_score = db.query(Sleep.sleep_score).filter(Sleep.sleep_score.isnot(None)).order_by(desc(Sleep.date)).scalar()
    last_vo2max = db.query(Activity.vo2max).filter(Activity.vo2max.isnot(None)).order_by(desc(Activity.start_time)).scalar()
    return {
        "total_activities": total_activities,
        "total_distance_km": round(total_distance / 1000, 1) if total_distance else 0,
        "total_calories_sport": total_calories_sport,
        "latest_resting_hr": last_rhr,
        "latest_hrv": last_hrv,
        "latest_sleep_score": last_sleep_score,
        "latest_vo2max": last_vo2max,
    }


@router.get("/weekly")
def weekly_stats(weeks: int = Query(12, ge=1, le=52), db: Session = Depends(get_db)):
    result = []
    today = date.today()
    for i in range(weeks - 1, -1, -1):
        week_end = today - timedelta(weeks=i)
        week_start = week_end - timedelta(days=6)
        acts = db.query(Activity).filter(
            Activity.start_time >= week_start.isoformat(),
            Activity.start_time <= week_end.isoformat(),
        ).all()
        health_rows = db.query(DailyHealth).filter(
            DailyHealth.date >= week_start.isoformat(),
            DailyHealth.date <= week_end.isoformat(),
        ).all()
        sleep_rows = db.query(Sleep).filter(
            Sleep.date >= week_start.isoformat(),
            Sleep.date <= week_end.isoformat(),
        ).all()
        result.append({
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "activity_count": len(acts),
            "total_duration_seconds": sum((a.duration_seconds or 0) for a in acts),
            "total_distance_km": round(sum((a.distance_meters or 0) for a in acts) / 1000, 2),
            "total_calories": sum((a.calories or 0) for a in acts),
            "avg_steps_per_day": sum((h.steps or 0) for h in health_rows) // len(health_rows) if health_rows else 0,
            "avg_body_battery_high": sum((h.body_battery_high or 0) for h in health_rows) // len(health_rows) if health_rows else 0,
            "avg_sleep_duration_seconds": sum((s.duration_seconds or 0) for s in sleep_rows) // len(sleep_rows) if sleep_rows else 0,
        })
    return result


@router.get("/training-load")
def training_load(days: int = Query(42, ge=7, le=180), db: Session = Depends(get_db)):
    since = (date.today() - timedelta(days=days)).isoformat()
    acts = db.query(Activity).filter(Activity.start_time >= since).order_by(Activity.start_time).all()
    by_day = {}
    for a in acts:
        if a.start_time:
            day = str(a.start_time)[:10]
            by_day[day] = by_day.get(day, 0) + (a.training_load or 0)
    return [{"date": d, "training_load": v} for d, v in sorted(by_day.items())]
