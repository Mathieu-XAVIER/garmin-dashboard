"""
scheduler.py — Synchronisation automatique des données Garmin (multi-utilisateurs).
"""

import logging
from datetime import date, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from database import SessionLocal, Activity, DailyHealth, Sleep, HRV, User
from garmin_client import GarminClient

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def _parse_start_time(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000)
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


def _parse_activity(raw, user_id: int):
    return {
        "user_id": user_id,
        "garmin_id": str(raw.get("activityId", "")),
        "activity_type": raw.get("activityType", {}).get("typeKey", ""),
        "name": raw.get("activityName", ""),
        "start_time": _parse_start_time(raw.get("startTimeLocal")),
        "duration_seconds": raw.get("duration"),
        "distance_meters": raw.get("distance"),
        "calories": raw.get("calories"),
        "avg_heart_rate": raw.get("averageHR"),
        "max_heart_rate": raw.get("maxHR"),
        "avg_speed": raw.get("averageSpeed"),
        "avg_cadence": raw.get("averageRunningCadenceInStepsPerMinute"),
        "training_load": raw.get("activityTrainingLoad"),
        "vo2max": raw.get("vO2MaxValue"),
        "aerobic_training_effect": raw.get("aerobicTrainingEffect"),
        "anaerobic_training_effect": raw.get("anaerobicTrainingEffect"),
        "hr_zones": None,
        "raw": raw,
    }


def _parse_daily_health(raw, target_date, user_id: int):
    return {
        "user_id": user_id,
        "date": target_date,
        "steps": raw.get("totalSteps"),
        "total_distance_meters": raw.get("totalDistanceMeters"),
        "calories_total": raw.get("totalKilocalories"),
        "calories_active": raw.get("activeKilocalories"),
        "floors_climbed": raw.get("floorsAscended"),
        "moderate_intensity_minutes": raw.get("moderateIntensityMinutes"),
        "vigorous_intensity_minutes": raw.get("vigorousIntensityMinutes"),
        "avg_stress": raw.get("averageStressLevel"),
        "max_stress": raw.get("maxStressLevel"),
        "body_battery_high": raw.get("bodyBatteryHighestValue"),
        "body_battery_low": raw.get("bodyBatteryLowestValue"),
        "resting_heart_rate": raw.get("restingHeartRate"),
        "avg_heart_rate": raw.get("averageHeartRate"),
        "raw": raw,
    }


def _ts_to_datetime(ts):
    if ts is None:
        return None
    return datetime.fromtimestamp(ts / 1000)


def _parse_sleep(raw, target_date, user_id: int):
    daily = raw.get("dailySleepDTO")
    if not daily:
        return None
    return {
        "user_id": user_id,
        "date": target_date,
        "sleep_start": _ts_to_datetime(daily.get("sleepStartTimestampLocal")),
        "sleep_end": _ts_to_datetime(daily.get("sleepEndTimestampLocal")),
        "duration_seconds": daily.get("sleepTimeSeconds"),
        "deep_sleep_seconds": daily.get("deepSleepSeconds"),
        "light_sleep_seconds": daily.get("lightSleepSeconds"),
        "rem_sleep_seconds": daily.get("remSleepSeconds"),
        "awake_seconds": daily.get("awakeSleepSeconds"),
        "sleep_score": daily.get("sleepScores", {}).get("overall", {}).get("value"),
        "avg_spo2": daily.get("averageSpO2Value"),
        "avg_hrv": daily.get("avgSleepStress"),
        "avg_respiration": daily.get("averageRespirationValue"),
        "raw": raw,
    }


def _parse_hrv(raw, target_date, user_id: int):
    summary = raw.get("hrvSummary")
    if not summary:
        return None
    return {
        "user_id": user_id,
        "date": target_date,
        "weekly_avg": summary.get("weeklyAvg"),
        "last_night_avg": summary.get("lastNight"),
        "last_night_5_min_high": summary.get("lastNight5MinHigh"),
        "baseline_low": summary.get("baselineLowUpper"),
        "baseline_high": summary.get("baselineBalancedUpper"),
        "status": summary.get("status"),
        "raw": raw,
    }


def _upsert(db, Model, filter_by, data):
    existing = db.query(Model).filter_by(**filter_by).first()
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
    else:
        db.add(Model(**data))


async def sync_user(client: GarminClient, user_id: int, db: Session, days_back: int = 7):
    summary = {"activities": 0, "daily_health": 0, "sleep": 0, "hrv": 0, "errors": []}
    today = date.today()
    start = today - timedelta(days=days_back)

    try:
        activities = client.get_activities_by_date(start, today)
        for raw in activities:
            data = _parse_activity(raw, user_id)
            if data["garmin_id"]:
                _upsert(db, Activity, {"garmin_id": data["garmin_id"], "user_id": user_id}, data)
                summary["activities"] += 1
        db.commit()
        logger.info(f"[user={user_id}] Activités : {summary['activities']} synchronisées")
    except Exception as e:
        summary["errors"].append(f"activities: {e}")
        db.rollback()

    current = start
    while current <= today:
        date_str = current.isoformat()

        try:
            raw = client.get_stats(current)
            if raw:
                _upsert(db, DailyHealth, {"date": date_str, "user_id": user_id},
                        _parse_daily_health(raw, date_str, user_id))
                summary["daily_health"] += 1
        except Exception as e:
            summary["errors"].append(f"daily_health {date_str}: {e}")

        try:
            raw = client.get_sleep(current)
            if raw:
                data = _parse_sleep(raw, date_str, user_id)
                if data:
                    _upsert(db, Sleep, {"date": date_str, "user_id": user_id}, data)
                    summary["sleep"] += 1
        except Exception as e:
            summary["errors"].append(f"sleep {date_str}: {e}")

        try:
            raw = client.get_hrv(current)
            if raw:
                data = _parse_hrv(raw, date_str, user_id)
                if data:
                    _upsert(db, HRV, {"date": date_str, "user_id": user_id}, data)
                    summary["hrv"] += 1
        except Exception as e:
            summary["errors"].append(f"hrv {date_str}: {e}")

        db.commit()
        current += timedelta(days=1)

    logger.info(f"[user={user_id}] Synchro terminée : {summary}")
    return summary


async def sync_all_users(manager, days_back: int = 2):
    db = SessionLocal()
    try:
        users = db.query(User).filter(
            User.garmin_email.isnot(None),
            User.garmin_password_encrypted.isnot(None),
        ).all()
        for user in users:
            try:
                client = manager.get_client(user)
                if client and client.client:
                    await sync_user(client, user.id, db, days_back)
            except Exception as e:
                logger.error(f"Erreur synchro utilisateur {user.id}: {e}")
    finally:
        db.close()


def setup_scheduler(manager, interval_minutes: int = 60):
    scheduler.add_job(
        sync_all_users,
        "interval",
        minutes=interval_minutes,
        args=[manager, 2],
        id="sync_garmin",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler démarré — synchro toutes les {interval_minutes} min")
