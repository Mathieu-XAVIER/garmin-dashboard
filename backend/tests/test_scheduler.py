"""Parsing des payloads Garmin et journalisation des synchronisations."""

from datetime import date, datetime

import pytest

import scheduler
from database import (
    Activity, BodyComposition, DailyHealth, HRV, RacePrediction,
    Sleep, SyncLog, TrainingReadiness, User,
)


# ── Parsing ───────────────────────────────────────────────────────────


def test_parse_activite_extrait_les_champs():
    brut = {
        "activityId": 123, "activityName": "Sortie longue",
        "activityType": {"typeKey": "running"},
        "startTimeLocal": "2026-08-19 07:30:00",
        "duration": 3600.0, "distance": 12000.0, "calories": 700,
        "averageHR": 145, "maxHR": 178, "activityTrainingLoad": 210.5,
        "vO2MaxValue": 52.0,
    }
    resultat = scheduler._parse_activity(brut, user_id=1)
    assert resultat["garmin_id"] == "123"
    assert resultat["activity_type"] == "running"
    assert resultat["start_time"] == datetime(2026, 8, 19, 7, 30)
    assert resultat["training_load"] == 210.5
    assert resultat["user_id"] == 1


def test_parse_activite_tolere_un_payload_vide():
    resultat = scheduler._parse_activity({}, user_id=1)
    assert resultat["garmin_id"] == ""
    assert resultat["start_time"] is None


@pytest.mark.parametrize("valeur,attendu", [
    ("2026-08-19 07:30:00", datetime(2026, 8, 19, 7, 30)),
    ("2026-08-19T07:30:00", datetime(2026, 8, 19, 7, 30)),
    ("2026-08-19T07:30:00.000", datetime(2026, 8, 19, 7, 30)),
    (None, None),
    ("format inconnu", None),
])
def test_parse_start_time(valeur, attendu):
    assert scheduler._parse_start_time(valeur) == attendu


def test_parse_sante_quotidienne_renseigne_le_spo2():
    """Régression : la colonne avg_spo2 n'était jamais alimentée."""
    brut = {"totalSteps": 9500, "restingHeartRate": 48, "averageSpo2": 96.5}
    resultat = scheduler._parse_daily_health(brut, "2026-08-19", user_id=1)
    assert resultat["steps"] == 9500
    assert resultat["avg_spo2"] == 96.5


def test_parse_sommeil_lit_la_vfc_et_non_le_stress():
    """Régression : avg_hrv recevait avgSleepStress."""
    brut = {"dailySleepDTO": {
        "sleepTimeSeconds": 27000, "deepSleepSeconds": 5400,
        "avgOvernightHrv": 62.0, "avgSleepStress": 18.0,
        "sleepScores": {"overall": {"value": 82}},
    }}
    resultat = scheduler._parse_sleep(brut, "2026-08-19", user_id=1)
    assert resultat["avg_hrv"] == 62.0
    assert resultat["sleep_score"] == 82


def test_parse_sommeil_sans_dto_retourne_none():
    assert scheduler._parse_sleep({}, "2026-08-19", user_id=1) is None


def test_parse_hrv():
    brut = {"hrvSummary": {"weeklyAvg": 58, "lastNight": 61, "status": "BALANCED"}}
    resultat = scheduler._parse_hrv(brut, "2026-08-19", user_id=1)
    assert resultat["last_night_avg"] == 61
    assert resultat["status"] == "BALANCED"


def test_parse_hrv_sans_resume_retourne_none():
    assert scheduler._parse_hrv({}, "2026-08-19", user_id=1) is None


# ── Client Garmin simulé ──────────────────────────────────────────────


class ClientSimule:
    """Reproduit la surface de GarminClient utilisée par la synchro."""

    def __init__(self, casse=False):
        self.casse = casse

    def get_activities_by_date(self, debut, fin):
        if self.casse:
            raise RuntimeError("Garmin indisponible")
        return [{
            "activityId": 1, "activityName": "Test",
            "activityType": {"typeKey": "running"},
            "startTimeLocal": f"{date.today().isoformat()} 07:00:00",
            "duration": 1800, "distance": 5000,
        }]

    def get_stats(self, jour):
        if self.casse:
            raise RuntimeError("stats indisponibles")
        return {"totalSteps": 8000}

    def get_sleep(self, jour):
        if self.casse:
            raise RuntimeError("sommeil indisponible")
        return {"dailySleepDTO": {"sleepTimeSeconds": 27000}}

    def get_hrv(self, jour):
        if self.casse:
            raise RuntimeError("hrv indisponible")
        return {"hrvSummary": {"lastNight": 60}}

    def get_body_composition(self, debut, fin):
        if self.casse:
            raise RuntimeError("pesées indisponibles")
        return {"dateWeightList": [
            {"date": f"{date.today().isoformat()}T06:00:00.0", "weight": 72500,
             "bmi": 22.4, "bodyFat": 14.2, "muscleMass": 33000},
        ]}

    def get_training_readiness(self, jour):
        if self.casse:
            raise RuntimeError("disponibilité indisponible")
        return [{"score": 72, "level": "READY", "sleepScore": 80, "recoveryTime": 6}]

    def get_race_predictions(self):
        if self.casse:
            raise RuntimeError("prédictions indisponibles")
        return {"calendarDate": date.today().isoformat(),
                "time5K": 1200, "time10K": 2500,
                "timeHalfMarathon": 5400, "timeMarathon": 11400}


@pytest.fixture
def uid(client, entetes, db):
    return db.query(User).first().id


# ── Synchronisation ───────────────────────────────────────────────────


async def test_synchro_ecrit_les_donnees(uid, db):
    resume = await scheduler.sync_user(ClientSimule(), uid, db, days_back=0)
    assert resume["activities"] == 1
    assert db.query(Activity).filter_by(user_id=uid).count() == 1
    assert db.query(DailyHealth).filter_by(user_id=uid).count() == 1
    assert db.query(Sleep).filter_by(user_id=uid).count() == 1
    assert db.query(HRV).filter_by(user_id=uid).count() == 1


async def test_synchro_est_idempotente(uid, db):
    """Deux passages sur la même période ne doivent pas dupliquer."""
    await scheduler.sync_user(ClientSimule(), uid, db, days_back=0)
    await scheduler.sync_user(ClientSimule(), uid, db, days_back=0)
    assert db.query(Activity).filter_by(user_id=uid).count() == 1
    assert db.query(DailyHealth).filter_by(user_id=uid).count() == 1


async def test_journal_statut_ok(uid, db):
    await scheduler.sync_user(ClientSimule(), uid, db, days_back=0, declencheur="manuel")
    journal = db.query(SyncLog).filter_by(user_id=uid).one()
    assert journal.statut == "ok"
    assert journal.declencheur == "manuel"
    assert journal.finished_at is not None
    assert journal.erreur is None
    assert journal.activities == 1


async def test_journal_statut_erreur_avec_message(uid, db):
    await scheduler.sync_user(ClientSimule(casse=True), uid, db, days_back=0, declencheur="auto")
    journal = db.query(SyncLog).filter_by(user_id=uid).one()
    assert journal.statut == "erreur"
    assert journal.activities == 0
    assert "Garmin indisponible" in journal.erreur


async def test_journal_statut_partiel(uid, db):
    """Des erreurs mais des données récupérées : ni ok, ni erreur."""
    class PartiellementCasse(ClientSimule):
        def get_stats(self, jour):
            raise RuntimeError("stats indisponibles")

    await scheduler.sync_user(PartiellementCasse(), uid, db, days_back=0)
    journal = db.query(SyncLog).filter_by(user_id=uid).one()
    assert journal.statut == "partiel"
    assert journal.activities == 1
    assert "stats indisponibles" in journal.erreur


def test_journaliser_echec_de_connexion(uid, db):
    scheduler.journaliser_echec(db, uid, "auto", "MFA requis")
    journal = db.query(SyncLog).filter_by(user_id=uid).one()
    assert journal.statut == "erreur"
    assert journal.erreur == "MFA requis"
    assert journal.finished_at is not None


async def test_la_synchro_ne_bloque_pas_l_event_loop(uid, db):
    """La synchro doit s'exécuter dans un thread, pas sur la boucle."""
    import threading
    thread_appelant = threading.get_ident()
    threads_vus = []

    class ClientTemoin(ClientSimule):
        def get_activities_by_date(self, debut, fin):
            threads_vus.append(threading.get_ident())
            return []

    await scheduler.sync_user(ClientTemoin(), uid, db, days_back=0)
    assert threads_vus and threads_vus[0] != thread_appelant


# ── Nouvelles métriques Garmin ────────────────────────────────────────


def test_parse_pesee_convertit_les_grammes():
    """Garmin exprime poids et masses en grammes."""
    resultat = scheduler._parse_body_composition(
        {"date": "2026-08-19T06:00:00.0", "weight": 72500,
         "boneMass": 3200, "muscleMass": 33000, "bmi": 22.4}, user_id=1)
    assert resultat["date"] == "2026-08-19"
    assert resultat["weight_kg"] == 72.5
    assert resultat["bone_mass_kg"] == 3.2
    assert resultat["muscle_mass_kg"] == 33.0
    assert resultat["bmi"] == 22.4


def test_parse_pesee_accepte_un_horodatage_numerique():
    resultat = scheduler._parse_body_composition(
        {"date": 1755561600000, "weight": 70000}, user_id=1)
    assert resultat["weight_kg"] == 70.0
    assert len(resultat["date"]) == 10


def test_parse_pesee_sans_date_ignoree():
    assert scheduler._parse_body_composition({"weight": 70000}, user_id=1) is None


def test_parse_disponibilite_depuis_une_liste():
    resultat = scheduler._parse_training_readiness(
        [{"score": 65, "level": "MODERATE", "sleepScore": 74}], "2026-08-19", user_id=1)
    assert resultat["score"] == 65
    assert resultat["level"] == "MODERATE"


@pytest.mark.parametrize("brut", [[], {}, None, [{"level": "READY"}]])
def test_parse_disponibilite_sans_score(brut):
    assert scheduler._parse_training_readiness(brut, "2026-08-19", user_id=1) is None


def test_parse_predictions_de_course():
    """Format réellement renvoyé par Garmin : clés par distance symbolique."""
    resultat = scheduler._parse_race_prediction(
        {"calendarDate": "2026-08-19", "time5K": 1564, "time10K": 3369,
         "timeHalfMarathon": 7774, "timeMarathon": 17755}, user_id=1)
    assert resultat["time_5k_seconds"] == 1564
    assert resultat["time_10k_seconds"] == 3369
    assert resultat["time_half_seconds"] == 7774
    assert resultat["time_marathon_seconds"] == 17755


def test_parse_predictions_accepte_les_cles_en_metres():
    """D'anciennes réponses nomment les champs par la distance en mètres."""
    resultat = scheduler._parse_race_prediction(
        {"calendarDate": "2026-08-19", "time5000": 1200, "time42195": 11400}, user_id=1)
    assert resultat["time_5k_seconds"] == 1200
    assert resultat["time_marathon_seconds"] == 11400


def test_parse_predictions_retient_la_plus_recente():
    resultat = scheduler._parse_race_prediction([
        {"calendarDate": "2026-07-01", "time5K": 1300},
        {"calendarDate": "2026-08-19", "time5K": 1200},
    ], user_id=1)
    assert resultat["date"] == "2026-08-19"
    assert resultat["time_5k_seconds"] == 1200


@pytest.mark.parametrize("brut", [[], {}, None, [{"calendarDate": "2026-08-19"}]])
def test_parse_predictions_sans_temps(brut):
    assert scheduler._parse_race_prediction(brut, user_id=1) is None


async def test_synchro_ecrit_les_nouvelles_metriques(uid, db):
    resume = await scheduler.sync_user(ClientSimule(), uid, db, days_back=0)
    assert resume["body_composition"] == 1
    assert resume["readiness"] == 1
    assert resume["race_predictions"] == 1
    assert db.query(BodyComposition).filter_by(user_id=uid).one().weight_kg == 72.5
    assert db.query(TrainingReadiness).filter_by(user_id=uid).one().score == 72
    assert db.query(RacePrediction).filter_by(user_id=uid).one().time_5k_seconds == 1200


async def test_disponibilite_limitee_aux_derniers_jours(uid, db, monkeypatch):
    """Un appel par jour : inutile de remonter 90 jours d'historique."""
    jours_demandes = []

    class ClientTemoin(ClientSimule):
        def get_training_readiness(self, jour):
            jours_demandes.append(jour)
            return []

    monkeypatch.setattr(scheduler, "JOURS_READINESS", 2)
    await scheduler.sync_user(ClientTemoin(), uid, db, days_back=30)
    assert len(jours_demandes) == 3  # aujourd'hui + 2 jours


async def test_les_appels_de_plage_ne_sont_faits_qu_une_fois(uid, db):
    """Pesées et prédictions coûtent un seul appel, pas un par jour."""
    appels = {"pesees": 0, "predictions": 0}

    class ClientTemoin(ClientSimule):
        def get_body_composition(self, debut, fin):
            appels["pesees"] += 1
            return {}

        def get_race_predictions(self):
            appels["predictions"] += 1
            return {}

    await scheduler.sync_user(ClientTemoin(), uid, db, days_back=30)
    assert appels == {"pesees": 1, "predictions": 1}


async def test_une_source_en_echec_n_est_plus_masquee(uid, db):
    """Les wrappers avalaient l'erreur : le journal disait « ok » alors
    qu'une source avait échoué."""
    class PredictionsCassees(ClientSimule):
        def get_race_predictions(self):
            raise RuntimeError("paramètres refusés par Garmin")

    await scheduler.sync_user(PredictionsCassees(), uid, db, days_back=0)
    journal = db.query(SyncLog).filter_by(user_id=uid).one()
    assert journal.statut == "partiel"
    assert "paramètres refusés" in journal.erreur
