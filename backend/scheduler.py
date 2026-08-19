"""
scheduler.py — Synchronisation automatique des données Garmin (multi-utilisateurs).
"""

import asyncio
import logging
from datetime import date, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from database import (
    SessionLocal, Activity, DailyHealth, Sleep, HRV, User, SyncLog,
    BodyComposition, TrainingReadiness, RacePrediction,
)
from garmin_client import GarminClient

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

# Utilisateurs dont une synchro est en cours — évite qu'une synchro manuelle
# et la synchro initiale (ou deux clics) tapent le quota Garmin en parallèle.
syncs_en_cours: set[int] = set()

# Profondeur d'historique pour la disponibilité à l'entraînement, qui coûte
# un appel Garmin par jour — inutile de la remonter sur 90 jours.
JOURS_READINESS = 7


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
        "avg_spo2": raw.get("averageSpo2") or raw.get("averageSpO2Value"),
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
        "avg_hrv": daily.get("avgOvernightHrv"),
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


def _parse_body_composition(raw, user_id: int):
    """Une pesée du tableau dateWeightList renvoyé par Garmin."""
    horodatage = raw.get("date") or raw.get("timestampGMT")
    if isinstance(horodatage, (int, float)):
        jour = datetime.fromtimestamp(horodatage / 1000).date().isoformat()
    elif isinstance(horodatage, str):
        jour = horodatage[:10]
    else:
        return None

    poids = raw.get("weight")
    return {
        "user_id": user_id,
        "date": jour,
        # Garmin exprime les masses en grammes.
        "weight_kg": round(poids / 1000, 2) if poids else None,
        "bmi": raw.get("bmi"),
        "body_fat_percent": raw.get("bodyFat"),
        "body_water_percent": raw.get("bodyWater"),
        "bone_mass_kg": round(raw["boneMass"] / 1000, 2) if raw.get("boneMass") else None,
        "muscle_mass_kg": round(raw["muscleMass"] / 1000, 2) if raw.get("muscleMass") else None,
        "visceral_fat": raw.get("visceralFat"),
        "metabolic_age": raw.get("metabolicAge"),
        "raw": raw,
    }


def _parse_training_readiness(raw, target_date, user_id: int):
    """Garmin renvoie une liste ; seule la première entrée nous intéresse."""
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    if not isinstance(raw, dict) or raw.get("score") is None:
        return None
    return {
        "user_id": user_id,
        "date": target_date,
        "score": raw.get("score"),
        "level": raw.get("level"),
        "sleep_score": raw.get("sleepScore"),
        "recovery_time_hours": raw.get("recoveryTime"),
        "hrv_factor_percent": raw.get("hrvFactorPercent"),
        "acute_load": raw.get("acuteLoad"),
        "raw": raw,
    }


_DISTANCES_PREDITES = {
    "time_5k_seconds": 5000,
    "time_10k_seconds": 10000,
    "time_half_seconds": 21097,
    "time_marathon_seconds": 42195,
}


def _parse_race_prediction(raw, user_id: int):
    """Retient la prédiction la plus récente du tableau renvoyé."""
    if isinstance(raw, list):
        raw = raw[-1] if raw else None
    if not isinstance(raw, dict):
        return None

    jour = (raw.get("calendarDate") or raw.get("date") or "")[:10]
    if not jour:
        return None

    donnees = {"user_id": user_id, "date": jour, "raw": raw}
    for colonne, metres in _DISTANCES_PREDITES.items():
        donnees[colonne] = raw.get(f"time{metres}")
    if not any(donnees[c] for c in _DISTANCES_PREDITES):
        return None
    return donnees


def _upsert(db, Model, filter_by, data):
    existing = db.query(Model).filter_by(**filter_by).first()
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
    else:
        db.add(Model(**data))


def _sync_user_blocking(client: GarminClient, user_id: int, db: Session, days_back: int = 7):
    """Corps de la synchro — 100 % bloquant (HTTP Garmin + SQL)."""
    summary = {
        "activities": 0, "daily_health": 0, "sleep": 0, "hrv": 0,
        "body_composition": 0, "readiness": 0, "race_predictions": 0,
        "errors": [],
    }
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
        logger.error(f"[user={user_id}] Erreur synchro activités : {e}", exc_info=True)
        db.rollback()

    # Pesées : un seul appel de plage plutôt qu'un par jour.
    try:
        brut = client.get_body_composition(start, today)
        pesees = (brut or {}).get("dateWeightList") or []
        for pesee in pesees:
            data = _parse_body_composition(pesee, user_id)
            if data:
                _upsert(db, BodyComposition, {"date": data["date"], "user_id": user_id}, data)
                summary["body_composition"] += 1
        db.commit()
    except Exception as e:
        summary["errors"].append(f"body_composition: {e}")
        logger.error(f"[user={user_id}] Erreur composition corporelle : {e}", exc_info=True)
        db.rollback()

    # Prédictions de course : idem, un seul appel.
    try:
        brut = client.get_race_predictions(start, today)
        data = _parse_race_prediction(brut, user_id)
        if data:
            _upsert(db, RacePrediction, {"date": data["date"], "user_id": user_id}, data)
            summary["race_predictions"] += 1
        db.commit()
    except Exception as e:
        summary["errors"].append(f"race_predictions: {e}")
        logger.error(f"[user={user_id}] Erreur prédictions de course : {e}", exc_info=True)
        db.rollback()

    # La disponibilité à l'entraînement n'a d'intérêt que récente, et coûte
    # un appel par jour : on la limite à la dernière semaine de la plage.
    debut_readiness = max(start, today - timedelta(days=JOURS_READINESS))

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
            logger.error(f"[user={user_id}] Erreur santé quotidienne {date_str} : {e}", exc_info=True)

        try:
            raw = client.get_sleep(current)
            if raw:
                data = _parse_sleep(raw, date_str, user_id)
                if data:
                    _upsert(db, Sleep, {"date": date_str, "user_id": user_id}, data)
                    summary["sleep"] += 1
        except Exception as e:
            summary["errors"].append(f"sleep {date_str}: {e}")
            logger.error(f"[user={user_id}] Erreur sommeil {date_str} : {e}", exc_info=True)

        try:
            raw = client.get_hrv(current)
            if raw:
                data = _parse_hrv(raw, date_str, user_id)
                if data:
                    _upsert(db, HRV, {"date": date_str, "user_id": user_id}, data)
                    summary["hrv"] += 1
        except Exception as e:
            summary["errors"].append(f"hrv {date_str}: {e}")
            logger.error(f"[user={user_id}] Erreur HRV {date_str} : {e}", exc_info=True)

        if current >= debut_readiness:
            try:
                raw = client.get_training_readiness(current)
                data = _parse_training_readiness(raw, date_str, user_id)
                if data:
                    _upsert(db, TrainingReadiness, {"date": date_str, "user_id": user_id}, data)
                    summary["readiness"] += 1
            except Exception as e:
                summary["errors"].append(f"readiness {date_str}: {e}")
                logger.error(f"[user={user_id}] Erreur disponibilité {date_str} : {e}", exc_info=True)

        db.commit()
        current += timedelta(days=1)

    logger.info(f"[user={user_id}] Synchro terminée : {summary}")
    return summary


def journaliser_echec(db: Session, user_id: int, declencheur: str, message: str):
    """Trace un échec survenu avant même de pouvoir synchroniser."""
    maintenant = datetime.utcnow()
    db.add(SyncLog(
        user_id=user_id, declencheur=declencheur, started_at=maintenant,
        finished_at=maintenant, statut="erreur", erreur=message,
    ))
    db.commit()


def _sync_avec_journal(client: GarminClient, user_id: int, db: Session,
                       days_back: int, declencheur: str):
    log = SyncLog(
        user_id=user_id, declencheur=declencheur,
        started_at=datetime.utcnow(), days_back=days_back,
    )
    db.add(log)
    db.commit()

    try:
        summary = _sync_user_blocking(client, user_id, db, days_back)
    except Exception as e:
        db.rollback()
        log.finished_at = datetime.utcnow()
        log.statut = "erreur"
        log.erreur = str(e)[:2000]
        db.commit()
        raise

    recupere = sum(
        summary[k] for k in (
            "activities", "daily_health", "sleep", "hrv",
            "body_composition", "readiness", "race_predictions",
        )
    )
    log.finished_at = datetime.utcnow()
    log.activities = summary["activities"]
    log.daily_health = summary["daily_health"]
    log.sleep = summary["sleep"]
    log.hrv = summary["hrv"]
    if not summary["errors"]:
        log.statut = "ok"
    else:
        log.statut = "partiel" if recupere else "erreur"
        log.erreur = "\n".join(str(e) for e in summary["errors"][:5])[:2000]
    db.commit()
    return summary


async def sync_user(client: GarminClient, user_id: int, db: Session,
                    days_back: int = 7, declencheur: str = "manuel"):
    """Déporte la synchro dans un thread pour ne pas bloquer l'event loop."""
    return await asyncio.to_thread(
        _sync_avec_journal, client, user_id, db, days_back, declencheur
    )


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
                if not client:
                    continue
                if not await asyncio.to_thread(lambda: client.client):
                    journaliser_echec(
                        db, user.id, "auto",
                        "Connexion à Garmin Connect impossible : identifiants "
                        "invalides, code MFA requis, ou quota d'appels atteint.",
                    )
                    continue
                await sync_user(client, user.id, db, days_back, "auto")
            except Exception as e:
                logger.error(f"Erreur synchro utilisateur {user.id}: {e}", exc_info=True)
                journaliser_echec(db, user.id, "auto", str(e)[:2000])
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
