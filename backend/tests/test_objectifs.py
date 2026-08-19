"""Objectifs hebdomadaires, calendrier annuel et exports."""

from datetime import date, datetime, timedelta

import pytest

from database import Activity, DailyHealth, Goal, User
from routes.goals import semaine_courante


@pytest.fixture
def uid(client, entetes, db):
    return db.query(User).first().id


def _activite(db, uid, jour, distance=10000, duree=3000, garmin_id=None, charge=50):
    db.add(Activity(
        user_id=uid, garmin_id=garmin_id or f"a-{jour.isoformat()}",
        activity_type="running", name="Séance",
        start_time=datetime.combine(jour, datetime.min.time()).replace(hour=12),
        distance_meters=distance, duration_seconds=duree, training_load=charge,
    ))
    db.commit()


# ── Semaine calendaire ────────────────────────────────────────────────


def test_semaine_commence_le_lundi():
    lundi, dimanche = semaine_courante(date(2026, 8, 19))  # un mercredi
    assert lundi == date(2026, 8, 17)
    assert dimanche == date(2026, 8, 23)
    assert lundi.weekday() == 0


def test_semaine_un_dimanche():
    lundi, dimanche = semaine_courante(date(2026, 8, 23))
    assert lundi == date(2026, 8, 17)
    assert dimanche == date(2026, 8, 23)


def test_semaine_un_lundi():
    lundi, _ = semaine_courante(date(2026, 8, 17))
    assert lundi == date(2026, 8, 17)


# ── Définition des objectifs ──────────────────────────────────────────


def test_aucun_objectif_au_depart(client, entetes):
    corps = client.get("/goals/", headers=entetes).json()
    assert corps["objectifs"] == []
    assert len(corps["metriques_disponibles"]) == 4


def test_definir_puis_relire(client, entetes):
    client.put("/goals/", headers=entetes, json={"objectifs": [
        {"metrique": "distance_km", "cible": 40},
        {"metrique": "activites", "cible": 4},
    ]})
    objectifs = client.get("/goals/", headers=entetes).json()["objectifs"]
    assert {o["metrique"]: o["cible"] for o in objectifs} == {"distance_km": 40, "activites": 4}


def test_metrique_inconnue_refusee(client, entetes):
    r = client.put("/goals/", headers=entetes, json={
        "objectifs": [{"metrique": "nimporte_quoi", "cible": 10}]})
    assert r.status_code == 400


def test_metrique_invalide_n_enregistre_rien(client, entetes, db):
    """La validation passe avant toute écriture."""
    client.put("/goals/", headers=entetes, json={"objectifs": [
        {"metrique": "distance_km", "cible": 40},
        {"metrique": "inexistante", "cible": 10},
    ]})
    assert db.query(Goal).count() == 0


def test_modifier_une_cible(client, entetes):
    client.put("/goals/", headers=entetes, json={"objectifs": [{"metrique": "distance_km", "cible": 40}]})
    client.put("/goals/", headers=entetes, json={"objectifs": [{"metrique": "distance_km", "cible": 60}]})
    objectifs = client.get("/goals/", headers=entetes).json()["objectifs"]
    assert len(objectifs) == 1
    assert objectifs[0]["cible"] == 60


def test_cible_nulle_supprime_l_objectif(client, entetes):
    client.put("/goals/", headers=entetes, json={"objectifs": [{"metrique": "distance_km", "cible": 40}]})
    client.put("/goals/", headers=entetes, json={"objectifs": [{"metrique": "distance_km", "cible": 0}]})
    assert client.get("/goals/", headers=entetes).json()["objectifs"] == []


# ── Progression ───────────────────────────────────────────────────────


def test_progression_sans_objectif(client, entetes):
    corps = client.get("/goals/progress", headers=entetes).json()
    assert corps["objectifs"] == []
    assert corps["semaine_debut"] <= date.today().isoformat() <= corps["semaine_fin"]


def test_progression_distance(client, entetes, uid, db):
    lundi, _ = semaine_courante()
    _activite(db, uid, lundi, distance=12000, garmin_id="a1")
    _activite(db, uid, lundi + timedelta(days=1), distance=8000, garmin_id="a2")
    client.put("/goals/", headers=entetes, json={"objectifs": [{"metrique": "distance_km", "cible": 40}]})

    objectif = client.get("/goals/progress", headers=entetes).json()["objectifs"][0]
    assert objectif["actuel"] == 20.0
    assert objectif["pourcentage"] == 50
    assert objectif["atteint"] is False


def test_progression_objectif_atteint(client, entetes, uid, db):
    lundi, _ = semaine_courante()
    _activite(db, uid, lundi, distance=45000)
    client.put("/goals/", headers=entetes, json={"objectifs": [{"metrique": "distance_km", "cible": 40}]})

    objectif = client.get("/goals/progress", headers=entetes).json()["objectifs"][0]
    assert objectif["atteint"] is True
    assert objectif["pourcentage"] > 100


def test_progression_ignore_la_semaine_precedente(client, entetes, uid, db):
    lundi, _ = semaine_courante()
    _activite(db, uid, lundi - timedelta(days=1), distance=30000)  # dimanche d'avant
    client.put("/goals/", headers=entetes, json={"objectifs": [{"metrique": "distance_km", "cible": 40}]})

    assert client.get("/goals/progress", headers=entetes).json()["objectifs"][0]["actuel"] == 0


def test_progression_pas_est_une_moyenne(client, entetes, uid, db):
    lundi, _ = semaine_courante()
    for i in range(3):
        db.add(DailyHealth(user_id=uid, date=(lundi + timedelta(days=i)).isoformat(), steps=(i + 1) * 3000))
    db.commit()
    client.put("/goals/", headers=entetes, json={"objectifs": [{"metrique": "pas", "cible": 10000}]})

    objectif = client.get("/goals/progress", headers=entetes).json()["objectifs"][0]
    assert objectif["actuel"] == 6000  # (3000+6000+9000)/3


def test_objectifs_cloisonnes_par_utilisateur(client, db):
    from conftest import creer_utilisateur
    a = creer_utilisateur(client, "a@exemple.fr")
    b = creer_utilisateur(client, "b@exemple.fr")
    client.put("/goals/", headers=a, json={"objectifs": [{"metrique": "distance_km", "cible": 40}]})
    assert client.get("/goals/", headers=b).json()["objectifs"] == []


# ── Calendrier ────────────────────────────────────────────────────────


def test_calendrier_vide(client, entetes):
    corps = client.get("/stats/calendar", headers=entetes).json()
    assert corps["jours"] == []
    assert corps["annee"] == date.today().year


def test_calendrier_agrege_par_jour(client, entetes, uid, db):
    jour = date(date.today().year, 3, 15)
    _activite(db, uid, jour, distance=10000, duree=3000, garmin_id="matin")
    db.add(Activity(user_id=uid, garmin_id="soir", activity_type="cycling",
                    start_time=datetime.combine(jour, datetime.min.time()).replace(hour=18),
                    distance_meters=20000, duration_seconds=3600, training_load=80))
    db.commit()

    corps = client.get(f"/stats/calendar?year={jour.year}", headers=entetes).json()
    assert len(corps["jours"]) == 1
    case = corps["jours"][0]
    assert case["activites"] == 2
    assert case["distance_km"] == 30.0
    assert case["duree_secondes"] == 6600
    assert sorted(case["types"]) == ["cycling", "running"]


def test_calendrier_filtre_par_annee(client, entetes, uid, db):
    annee = date.today().year
    _activite(db, uid, date(annee, 6, 1), garmin_id="cette-annee")
    _activite(db, uid, date(annee - 1, 6, 1), garmin_id="annee-passee")

    assert len(client.get(f"/stats/calendar?year={annee}", headers=entetes).json()["jours"]) == 1
    assert len(client.get(f"/stats/calendar?year={annee - 1}", headers=entetes).json()["jours"]) == 1


def test_calendrier_ne_renvoie_que_les_jours_actifs(client, entetes, uid, db):
    """Une année creuse ne doit pas transiter 365 cases vides."""
    _activite(db, uid, date(date.today().year, 5, 5))
    corps = client.get("/stats/calendar", headers=entetes).json()
    assert corps["jours_actifs"] == 1
    assert len(corps["jours"]) == 1


# ── Exports ───────────────────────────────────────────────────────────


def test_export_activites_csv(client, entetes, uid, db):
    _activite(db, uid, date.today(), distance=12345)
    reponse = client.get("/export/activities.csv", headers=entetes)

    assert reponse.status_code == 200
    assert "text/csv" in reponse.headers["content-type"]
    assert "attachment" in reponse.headers["content-disposition"]
    assert ".csv" in reponse.headers["content-disposition"]

    lignes = reponse.text.lstrip("﻿").strip().split("\r\n")
    assert lignes[0].split(";")[:3] == ["date", "nom", "type"]
    assert "12.345" in lignes[1]


def test_export_sante_reunit_les_trois_sources(client, entetes, uid, db):
    from database import HRV, Sleep
    jour = date.today().isoformat()
    db.add(DailyHealth(user_id=uid, date=jour, steps=9000, resting_heart_rate=48))
    db.add(Sleep(user_id=uid, date=jour, duration_seconds=27000, sleep_score=85))
    db.add(HRV(user_id=uid, date=jour, last_night_avg=62, status="BALANCED"))
    db.commit()

    lignes = client.get("/export/health.csv", headers=entetes).text.lstrip("﻿").strip().split("\r\n")
    assert len(lignes) == 2
    valeurs = lignes[1].split(";")
    assert valeurs[0] == jour
    assert "9000" in valeurs and "85" in valeurs and "BALANCED" in valeurs


def test_export_csv_vide_garde_les_entetes(client, entetes):
    lignes = client.get("/export/activities.csv", headers=entetes).text.lstrip("﻿").strip().split("\r\n")
    assert len(lignes) == 1
    assert lignes[0].startswith("date;nom;type")


def test_export_csv_exige_un_jeton(client):
    assert client.get("/export/activities.csv").status_code == 401
    assert client.get("/export/health.csv").status_code == 401


def test_export_csv_cloisonne(client, db):
    from conftest import creer_utilisateur
    a = creer_utilisateur(client, "a@exemple.fr")
    b = creer_utilisateur(client, "b@exemple.fr")
    id_b = db.query(User).filter(User.email == "b@exemple.fr").first().id
    _activite(db, id_b, date.today())

    lignes = client.get("/export/activities.csv", headers=a).text.lstrip("﻿").strip().split("\r\n")
    assert len(lignes) == 1  # A ne voit que les en-têtes


# ── GPX ───────────────────────────────────────────────────────────────


def test_gpx_sans_trace_renvoie_404(client, entetes, uid, db):
    _activite(db, uid, date.today(), garmin_id="42")
    reponse = client.get("/export/activities/42.gpx", headers=entetes)
    assert reponse.status_code == 404
    assert "tracé GPS" in reponse.json()["detail"]


def test_gpx_activite_inexistante(client, entetes):
    assert client.get("/export/activities/999.gpx", headers=entetes).status_code == 404


def test_gpx_bien_forme(client, entetes, uid, db):
    _activite(db, uid, date.today(), garmin_id="42")
    ligne = db.query(Activity).filter_by(garmin_id="42").one()
    ligne.gps_track = [
        {"lat": 45.43, "lon": 4.94, "altitude": 210.5, "time": 0, "hr": 132},
        {"lat": 45.44, "lon": 4.95, "altitude": 215.0, "time": 60000, "hr": 145},
    ]
    db.commit()

    reponse = client.get("/export/activities/42.gpx", headers=entetes)
    assert reponse.status_code == 200
    assert "application/gpx+xml" in reponse.headers["content-type"]

    gpx = reponse.text
    assert gpx.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert gpx.count("<trkpt") == 2
    assert 'lat="45.43" lon="4.94"' in gpx
    assert "<ele>210.5</ele>" in gpx
    assert "<gpxtpx:hr>132</gpxtpx:hr>" in gpx

    # Le fichier doit être un XML valide.
    import xml.etree.ElementTree as ET
    ET.fromstring(gpx)


def test_gpx_ignore_les_points_sans_coordonnees(client, entetes, uid, db):
    _activite(db, uid, date.today(), garmin_id="42")
    ligne = db.query(Activity).filter_by(garmin_id="42").one()
    ligne.gps_track = [{"lat": 45.43, "lon": 4.94}, {"lat": None, "lon": None}]
    db.commit()

    assert client.get("/export/activities/42.gpx", headers=entetes).text.count("<trkpt") == 1


def test_gpx_echappe_le_nom(client, entetes, uid, db):
    """Un nom d'activité contenant des chevrons casserait le XML."""
    db.add(Activity(user_id=uid, garmin_id="42", activity_type="running",
                    name="Sortie <test> & cie", start_time=datetime.utcnow(),
                    gps_track=[{"lat": 45.4, "lon": 4.9}]))
    db.commit()

    gpx = client.get("/export/activities/42.gpx", headers=entetes).text
    assert "&lt;test&gt; &amp; cie" in gpx
    import xml.etree.ElementTree as ET
    ET.fromstring(gpx)


def test_gpx_cloisonne(client, db):
    from conftest import creer_utilisateur
    a = creer_utilisateur(client, "a@exemple.fr")
    creer_utilisateur(client, "b@exemple.fr")
    id_b = db.query(User).filter(User.email == "b@exemple.fr").first().id
    db.add(Activity(user_id=id_b, garmin_id="42", activity_type="running",
                    start_time=datetime.utcnow(), gps_track=[{"lat": 45.4, "lon": 4.9}]))
    db.commit()

    assert client.get("/export/activities/42.gpx", headers=a).status_code == 404
