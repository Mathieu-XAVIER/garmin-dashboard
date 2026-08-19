"""
Isolation multi-utilisateurs — le test le plus important du projet.

Chaque route de données est protégée par get_current_user et filtrée par
user_id. Une seule de ces clauses oubliée exposerait les données de santé
d'un utilisateur à un autre.
"""

from datetime import date, datetime, timedelta

import pytest

from conftest import creer_utilisateur
from database import Activity, DailyHealth, HRV, Sleep, SyncLog

ROUTES_PROTEGEES = [
    "/activities/",
    "/activities/recent",
    "/activities/types",
    "/health/daily",
    "/health/today",
    "/health/sleep",
    "/health/hrv",
    "/health/hrv/latest",
    "/stats/summary",
    "/stats/weekly",
    "/stats/training-load",
    "/profile/",
    "/preferences/nav",
    "/sync/status",
]


@pytest.mark.parametrize("route", ROUTES_PROTEGEES)
def test_route_refuse_sans_jeton(client, route):
    assert client.get(route).status_code == 401


@pytest.mark.parametrize("route", ROUTES_PROTEGEES)
def test_route_refuse_jeton_invalide(client, route):
    entetes = {"Authorization": "Bearer jeton.completement.faux"}
    assert client.get(route, headers=entetes).status_code == 401


def _remplir(db, user_id: int, suffixe: str):
    aujourdhui = date.today()
    db.add(Activity(
        user_id=user_id, garmin_id=f"act-{suffixe}", activity_type="running",
        name=f"Sortie {suffixe}", start_time=datetime.combine(aujourdhui, datetime.min.time()).replace(hour=8),
        distance_meters=10000, duration_seconds=3000, training_load=80, vo2max=50,
    ))
    db.add(DailyHealth(user_id=user_id, date=aujourdhui.isoformat(), steps=9000, resting_heart_rate=50))
    db.add(Sleep(user_id=user_id, date=aujourdhui.isoformat(), duration_seconds=27000, sleep_score=80))
    db.add(HRV(user_id=user_id, date=aujourdhui.isoformat(), last_night_avg=60, status="BALANCED"))
    db.add(SyncLog(user_id=user_id, declencheur="manuel", started_at=datetime.utcnow(), statut="ok"))
    db.commit()


def test_un_utilisateur_ne_voit_que_ses_donnees(client, db):
    entetes_a = creer_utilisateur(client, "a@exemple.fr")
    entetes_b = creer_utilisateur(client, "b@exemple.fr")

    from database import User
    id_a = db.query(User).filter(User.email == "a@exemple.fr").first().id
    id_b = db.query(User).filter(User.email == "b@exemple.fr").first().id

    _remplir(db, id_a, "A")
    _remplir(db, id_b, "B")

    # Chacun voit exactement une activité : la sienne.
    for entetes, attendu in ((entetes_a, "Sortie A"), (entetes_b, "Sortie B")):
        corps = client.get("/activities/", headers=entetes).json()
        assert corps["total"] == 1
        assert corps["items"][0]["name"] == attendu

    # Les agrégats ne mélangent pas les deux comptes.
    resume_a = client.get("/stats/summary", headers=entetes_a).json()
    assert resume_a["total_activities"] == 1
    assert resume_a["total_distance_km"] == 10.0

    # Le journal de synchro est cloisonné lui aussi.
    for entetes in (entetes_a, entetes_b):
        assert len(client.get("/sync/status", headers=entetes).json()["historique"]) == 1


def test_detail_activite_d_autrui_est_introuvable(client, db):
    entetes_a = creer_utilisateur(client, "a@exemple.fr")
    creer_utilisateur(client, "b@exemple.fr")

    from database import User
    id_b = db.query(User).filter(User.email == "b@exemple.fr").first().id
    _remplir(db, id_b, "B")

    # A connaît l'identifiant Garmin de B mais ne doit pas pouvoir le lire.
    assert client.get("/activities/act-B", headers=entetes_a).status_code == 404
    assert client.get("/activities/act-B/gps", headers=entetes_a).status_code == 404


def test_donnees_de_sante_datees_ne_fuient_pas(client, db):
    entetes_a = creer_utilisateur(client, "a@exemple.fr")
    creer_utilisateur(client, "b@exemple.fr")

    from database import User
    id_b = db.query(User).filter(User.email == "b@exemple.fr").first().id
    _remplir(db, id_b, "B")

    jour = date.today().isoformat()
    assert client.get(f"/health/daily/{jour}", headers=entetes_a).status_code == 404
    assert client.get(f"/health/sleep/{jour}", headers=entetes_a).status_code == 404
    assert client.get("/health/daily", headers=entetes_a).json() == []
    assert client.get("/health/hrv", headers=entetes_a).json() == []


def test_suppression_de_compte_n_efface_que_ses_donnees(client, db):
    entetes_a = creer_utilisateur(client, "a@exemple.fr")
    entetes_b = creer_utilisateur(client, "b@exemple.fr")

    from database import User
    id_a = db.query(User).filter(User.email == "a@exemple.fr").first().id
    id_b = db.query(User).filter(User.email == "b@exemple.fr").first().id
    _remplir(db, id_a, "A")
    _remplir(db, id_b, "B")

    assert client.delete("/auth/account", headers=entetes_a).status_code == 200

    db.expire_all()
    assert db.query(Activity).filter_by(user_id=id_a).count() == 0
    assert db.query(Activity).filter_by(user_id=id_b).count() == 1
    assert db.query(SyncLog).filter_by(user_id=id_b).count() == 1
    # B reste pleinement fonctionnel.
    assert client.get("/stats/summary", headers=entetes_b).json()["total_activities"] == 1
