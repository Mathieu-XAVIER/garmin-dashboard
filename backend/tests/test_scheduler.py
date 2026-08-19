"""Parsing des payloads Garmin et journalisation des synchronisations."""

from datetime import date, datetime

import pytest

import scheduler
from database import Activity, DailyHealth, HRV, Sleep, SyncLog, User


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
