"""
routes/profile.py — Vue profil : forme, tendances, récupération.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import date, timedelta

from database import (
    get_db, Activity, DailyHealth, Sleep, HRV, User, RacePrediction,
)
from date_utils import day_start, day_after
from auth import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    uid = current_user.id

    return {
        "fitness_score":    _fitness_score(db, today, uid),
        "vo2max_history":   _vo2max_history(db, uid),
        "load_balance":     _load_balance(db, today, uid),
        "recovery_trend":   _recovery_trend(db, today, uid),
        "rhr_trend":        _rhr_trend(db, today, uid),
        "sleep_trend":      _sleep_trend(db, today, uid),
        "personal_bests":   _personal_bests(db, uid),
        "activity_streak":  _activity_streak(db, today, uid),
        "race_predictions": _race_predictions(db, uid),
    }


def _race_predictions(db: Session, uid: int) -> dict | None:
    ligne = (
        db.query(RacePrediction)
        .filter(RacePrediction.user_id == uid)
        .order_by(desc(RacePrediction.date))
        .first()
    )
    if not ligne:
        return None
    return {
        "date": ligne.date,
        "5k": ligne.time_5k_seconds,
        "10k": ligne.time_10k_seconds,
        "semi": ligne.time_half_seconds,
        "marathon": ligne.time_marathon_seconds,
    }


def _fitness_score(db: Session, today: date, uid: int) -> dict:
    ctl = _avg_load(db, today, 42, uid)
    atl = _avg_load(db, today, 7, uid)
    tsb = ctl - atl

    hrv_rows = db.query(HRV).filter(
        HRV.user_id == uid,
        HRV.date >= (today - timedelta(days=7)).isoformat(),
    ).all()
    hrv_avg_7 = _mean([h.last_night_avg for h in hrv_rows if h.last_night_avg])

    hrv_all = db.query(HRV).filter(
        HRV.user_id == uid,
        HRV.date >= (today - timedelta(days=42)).isoformat(),
    ).all()
    hrv_baseline = _mean([h.last_night_avg for h in hrv_all if h.last_night_avg])

    hrv_score = 20
    if hrv_baseline and hrv_avg_7:
        ratio = hrv_avg_7 / hrv_baseline
        hrv_score = min(40, max(0, 20 + (ratio - 1) * 60))

    tsb_score = 15
    if ctl:
        tsb_norm = tsb / max(ctl, 1)
        tsb_score = min(30, max(0, 15 + tsb_norm * 30))

    sleep_rows = db.query(Sleep).filter(
        Sleep.user_id == uid,
        Sleep.date >= (today - timedelta(days=7)).isoformat(),
    ).all()
    sleep_avg = _mean([s.sleep_score for s in sleep_rows if s.sleep_score])
    sleep_score = ((sleep_avg or 70) / 100) * 30

    total = round(hrv_score + tsb_score + sleep_score)

    return {
        "score": min(100, max(0, total)),
        "ctl": round(ctl, 1) if ctl else None,
        "atl": round(atl, 1) if atl else None,
        "tsb": round(tsb, 1) if ctl else None,
        "hrv_avg_7d": round(hrv_avg_7, 1) if hrv_avg_7 else None,
        "hrv_baseline_42d": round(hrv_baseline, 1) if hrv_baseline else None,
        "sleep_score_avg_7d": round(sleep_avg, 1) if sleep_avg else None,
    }


def _vo2max_history(db: Session, uid: int) -> list[dict]:
    rows = (
        db.query(Activity.start_time, Activity.vo2max, Activity.activity_type)
        .filter(Activity.user_id == uid, Activity.vo2max.isnot(None))
        .order_by(Activity.start_time)
        .all()
    )
    return [
        {
            "date": str(r.start_time)[:10],
            "vo2max": round(r.vo2max, 1),
            "activity_type": r.activity_type,
        }
        for r in rows
    ]


def _load_balance(db: Session, today: date, uid: int) -> list[dict]:
    debut = today - timedelta(weeks=15, days=42)
    rows = (
        db.query(Activity.start_time, Activity.training_load)
        .filter(
            Activity.user_id == uid,
            Activity.start_time >= day_start(debut),
            Activity.training_load.isnot(None),
        )
        .all()
    )
    charges = [(r.start_time.date(), r.training_load) for r in rows if r.start_time]

    def moyenne(fin: date, jours: int) -> float:
        depuis = fin - timedelta(days=jours)
        return sum(c for j, c in charges if depuis <= j <= fin) / jours

    result = []
    for i in range(15, -1, -1):
        week_end = today - timedelta(weeks=i)
        ctl = moyenne(week_end, 42)
        atl = moyenne(week_end, 7)
        result.append({
            "date": week_end.isoformat(),
            "ctl": round(ctl, 1),
            "atl": round(atl, 1),
            "tsb": round(ctl - atl, 1),
        })
    return result


def _recovery_trend(db: Session, today: date, uid: int) -> list[dict]:
    health = (
        db.query(DailyHealth)
        .filter(DailyHealth.user_id == uid, DailyHealth.date >= (today - timedelta(days=30)).isoformat())
        .order_by(DailyHealth.date)
        .all()
    )
    hrv_map = {
        h.date: h.last_night_avg
        for h in db.query(HRV)
        .filter(HRV.user_id == uid, HRV.date >= (today - timedelta(days=30)).isoformat())
        .all()
        if h.last_night_avg
    }
    return [
        {
            "date": h.date,
            "body_battery": h.body_battery_high,
            "hrv": hrv_map.get(h.date),
            "resting_hr": h.resting_heart_rate,
        }
        for h in health
    ]


def _rhr_trend(db: Session, today: date, uid: int) -> list[dict]:
    rows = (
        db.query(DailyHealth.date, DailyHealth.resting_heart_rate)
        .filter(
            DailyHealth.user_id == uid,
            DailyHealth.date >= (today - timedelta(days=90)).isoformat(),
            DailyHealth.resting_heart_rate.isnot(None),
        )
        .order_by(DailyHealth.date)
        .all()
    )
    result = []
    values = [r.resting_heart_rate for r in rows]
    for i, r in enumerate(rows):
        window = values[max(0, i - 6): i + 1]
        result.append({
            "date": r.date,
            "rhr": r.resting_heart_rate,
            "rhr_ma7": round(sum(window) / len(window), 1),
        })
    return result


def _sleep_trend(db: Session, today: date, uid: int) -> list[dict]:
    rows = (
        db.query(Sleep)
        .filter(Sleep.user_id == uid, Sleep.date >= (today - timedelta(days=30)).isoformat())
        .order_by(Sleep.date)
        .all()
    )
    return [
        {
            "date": s.date,
            "score": s.sleep_score,
            "duration_h": round(s.duration_seconds / 3600, 2) if s.duration_seconds else None,
            "deep_h": round(s.deep_sleep_seconds / 3600, 2) if s.deep_sleep_seconds else None,
            "rem_h": round(s.rem_sleep_seconds / 3600, 2) if s.rem_sleep_seconds else None,
        }
        for s in rows
    ]


def _personal_bests(db: Session, uid: int) -> dict:
    bests: dict = {}

    for type_key in ["running", "cycling", "swimming"]:
        row = (
            db.query(Activity)
            .filter(
                Activity.user_id == uid,
                Activity.activity_type == type_key,
                Activity.distance_meters.isnot(None),
            )
            .order_by(desc(Activity.distance_meters))
            .first()
        )
        if row:
            bests[f"{type_key}_max_distance"] = {
                "value_km": round(row.distance_meters / 1000, 2),
                "date": str(row.start_time)[:10],
                "activity_name": row.name,
            }

    row = db.query(Activity).filter(
        Activity.user_id == uid,
        Activity.vo2max.isnot(None),
    ).order_by(desc(Activity.vo2max)).first()
    if row:
        bests["vo2max_best"] = {
            "value": round(row.vo2max, 1),
            "date": str(row.start_time)[:10],
        }

    return bests


def _activity_streak(db: Session, today: date, uid: int) -> dict:
    rows = (
        db.query(Activity.start_time)
        .filter(
            Activity.user_id == uid,
            Activity.start_time >= day_start(today - timedelta(days=365)),
            Activity.start_time.isnot(None),
        )
        .all()
    )
    jours = {r.start_time.date() for r in rows if r.start_time}

    # La série ne doit pas retomber à zéro chaque matin : tant que la séance
    # du jour n'a pas eu lieu, on fait courir le compteur depuis la veille.
    depart = today if today in jours else today - timedelta(days=1)
    streak = 0
    d = depart
    while d in jours:
        streak += 1
        d -= timedelta(days=1)

    best = 0
    current = 0
    for i in range(90):
        if (today - timedelta(days=i)) in jours:
            current += 1
            best = max(best, current)
        else:
            current = 0

    return {"current_streak": streak, "best_streak_90d": best}


def _avg_load(db: Session, end_date: date, days: int, uid: int) -> float:
    start = end_date - timedelta(days=days)
    rows = (
        db.query(Activity.training_load)
        .filter(
            Activity.user_id == uid,
            Activity.start_time >= day_start(start),
            Activity.start_time < day_after(end_date),
            Activity.training_load.isnot(None),
        )
        .all()
    )
    if not rows:
        return 0.0
    return sum(r.training_load for r in rows) / days


def _mean(values: list) -> float | None:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None
