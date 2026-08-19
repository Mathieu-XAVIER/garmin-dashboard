"""
Calculs métier : bornes de dates, agrégats hebdomadaires, série
d'activités, charge d'entraînement.

Ces fonctions ont toutes déjà produit des résultats faux : elles sont
verrouillées ici cas par cas.
"""

from datetime import date, datetime, timedelta

import pytest

from database import Activity, DailyHealth, Sleep, User
from date_utils import day_after, day_start


# ── Bornes de dates ───────────────────────────────────────────────────


def test_day_start_est_minuit():
    assert day_start(date(2026, 8, 19)) == datetime(2026, 8, 19, 0, 0, 0)


def test_day_after_est_le_lendemain_a_minuit():
    assert day_after(date(2026, 8, 19)) == datetime(2026, 8, 20, 0, 0, 0)


def test_la_borne_haute_couvre_toute_la_journee():
    """Une séance à 23h59 doit rester sous la borne haute du jour même."""
    tard = datetime(2026, 8, 19, 23, 59, 59)
    assert tard < day_after(date(2026, 8, 19))


# ── Helpers ───────────────────────────────────────────────────────────


def _id_utilisateur(db):
    return db.query(User).first().id


def _activite(db, user_id, jour, heure=19, charge=100, distance=10000, garmin_id=None):
    db.add(Activity(
        user_id=user_id,
        garmin_id=garmin_id or f"a-{jour.isoformat()}-{heure}",
        activity_type="running", name="Séance",
        start_time=datetime.combine(jour, datetime.min.time()).replace(hour=heure),
        distance_meters=distance, duration_seconds=3000, training_load=charge,
    ))
    db.commit()


# ── Agrégats hebdomadaires ────────────────────────────────────────────


def test_la_seance_du_jour_compte_dans_la_semaine(client, entetes, db):
    """Régression : la borne haute valait minuit, la séance du jour tombait."""
    uid = _id_utilisateur(db)
    aujourdhui = date.today()
    _activite(db, uid, aujourdhui, heure=19)
    _activite(db, uid, aujourdhui - timedelta(days=1), heure=19)

    semaine = client.get("/stats/weekly?weeks=1", headers=entetes).json()[0]
    assert semaine["activity_count"] == 2
    assert semaine["total_distance_km"] == 20.0


def test_une_seance_a_23h59_est_comptee(client, entetes, db):
    uid = _id_utilisateur(db)
    _activite(db, uid, date.today(), heure=23)
    semaine = client.get("/stats/weekly?weeks=1", headers=entetes).json()[0]
    assert semaine["activity_count"] == 1


def test_une_seance_hors_fenetre_est_exclue(client, entetes, db):
    uid = _id_utilisateur(db)
    _activite(db, uid, date.today() - timedelta(days=30))
    semaine = client.get("/stats/weekly?weeks=1", headers=entetes).json()[0]
    assert semaine["activity_count"] == 0


def test_moyennes_hebdo_sur_donnees_de_sante(client, entetes, db):
    uid = _id_utilisateur(db)
    for i in range(3):
        jour = (date.today() - timedelta(days=i)).isoformat()
        db.add(DailyHealth(user_id=uid, date=jour, steps=(i + 1) * 1000))
        db.add(Sleep(user_id=uid, date=jour, duration_seconds=28800))
    db.commit()

    semaine = client.get("/stats/weekly?weeks=1", headers=entetes).json()[0]
    assert semaine["avg_steps_per_day"] == 2000       # (1000+2000+3000)/3
    assert semaine["avg_sleep_duration_seconds"] == 28800


# ── Série d'activités ─────────────────────────────────────────────────


def test_serie_compte_les_jours_consecutifs(client, entetes, db):
    uid = _id_utilisateur(db)
    for i in range(3):
        _activite(db, uid, date.today() - timedelta(days=i))
    serie = client.get("/profile/", headers=entetes).json()["activity_streak"]
    assert serie["current_streak"] == 3


def test_serie_survit_a_une_journee_du_jour_sans_seance(client, entetes, db):
    """Régression : la série retombait à zéro chaque matin."""
    uid = _id_utilisateur(db)
    for i in (1, 2, 3):
        _activite(db, uid, date.today() - timedelta(days=i))
    serie = client.get("/profile/", headers=entetes).json()["activity_streak"]
    assert serie["current_streak"] == 3


def test_serie_s_interrompt_sur_un_trou(client, entetes, db):
    uid = _id_utilisateur(db)
    _activite(db, uid, date.today())
    _activite(db, uid, date.today() - timedelta(days=2))  # J-1 manquant
    serie = client.get("/profile/", headers=entetes).json()["activity_streak"]
    assert serie["current_streak"] == 1


def test_serie_nulle_sans_activite(client, entetes):
    serie = client.get("/profile/", headers=entetes).json()["activity_streak"]
    assert serie["current_streak"] == 0
    assert serie["best_streak_90d"] == 0


def test_plusieurs_seances_le_meme_jour_comptent_pour_un(client, entetes, db):
    uid = _id_utilisateur(db)
    _activite(db, uid, date.today(), heure=8, garmin_id="matin")
    _activite(db, uid, date.today(), heure=18, garmin_id="soir")
    serie = client.get("/profile/", headers=entetes).json()["activity_streak"]
    assert serie["current_streak"] == 1


def test_meilleure_serie_sur_90_jours(client, entetes, db):
    uid = _id_utilisateur(db)
    for i in (10, 11, 12, 13):
        _activite(db, uid, date.today() - timedelta(days=i))
    for i in (2, 3):
        _activite(db, uid, date.today() - timedelta(days=i))
    serie = client.get("/profile/", headers=entetes).json()["activity_streak"]
    assert serie["best_streak_90d"] == 4


# ── Charge d'entraînement ─────────────────────────────────────────────


def test_ctl_et_atl_moyennent_sur_leur_fenetre(client, entetes, db):
    """CTL = charge / 42 jours, ATL = charge / 7 jours."""
    uid = _id_utilisateur(db)
    _activite(db, uid, date.today(), charge=420)

    forme = client.get("/profile/", headers=entetes).json()["fitness_score"]
    assert forme["ctl"] == 10.0   # 420 / 42
    assert forme["atl"] == 60.0   # 420 / 7
    assert forme["tsb"] == -50.0  # fatigue aiguë


def test_charge_du_jour_prise_en_compte(client, entetes, db):
    """Régression : la borne haute excluait la séance du jour du CTL."""
    uid = _id_utilisateur(db)
    _activite(db, uid, date.today(), heure=20, charge=210)
    forme = client.get("/profile/", headers=entetes).json()["fitness_score"]
    assert forme["ctl"] == 5.0


def test_load_balance_retourne_16_points(client, entetes):
    equilibre = client.get("/profile/", headers=entetes).json()["load_balance"]
    assert len(equilibre) == 16
    assert equilibre[0]["date"] < equilibre[-1]["date"]


def test_training_load_agrege_par_jour(client, entetes, db):
    uid = _id_utilisateur(db)
    _activite(db, uid, date.today(), heure=8, charge=50, garmin_id="matin")
    _activite(db, uid, date.today(), heure=18, charge=70, garmin_id="soir")

    charges = client.get("/stats/training-load", headers=entetes).json()
    assert len(charges) == 1
    assert charges[0]["training_load"] == 120


def test_records_personnels(client, entetes, db):
    uid = _id_utilisateur(db)
    _activite(db, uid, date.today() - timedelta(days=5), distance=21000, garmin_id="semi")
    _activite(db, uid, date.today() - timedelta(days=2), distance=10000, garmin_id="dix")

    records = client.get("/profile/", headers=entetes).json()["personal_bests"]
    assert records["running_max_distance"]["value_km"] == 21.0
