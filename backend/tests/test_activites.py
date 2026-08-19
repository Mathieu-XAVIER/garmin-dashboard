"""
Détail d'activité : extraction des zones FC, des splits et du tracé GPS
depuis le payload brut Garmin, dont le format varie selon le sport.
"""

from datetime import date, datetime, timedelta

import pytest

from database import Activity, DailyHealth, HRV, Sleep, User
from routes.activities import _extract_hr_zones, _extract_splits, _extract_timeline


# ── Zones de fréquence cardiaque ──────────────────────────────────────


def test_zones_fc_depuis_des_dictionnaires():
    brut = {"heartRateZones": [
        {"secsInZone": 300}, {"secsInZone": 900}, {"secsInZone": 600},
    ]}
    zones = _extract_hr_zones(brut)
    assert [z["seconds"] for z in zones] == [300, 900, 600]
    assert zones[0]["name"] == "Zone 1"
    assert all(z["color"].startswith("#") for z in zones)


def test_zones_fc_depuis_des_nombres():
    zones = _extract_hr_zones({"timeInHrZone": [120, 240]})
    assert [z["seconds"] for z in zones] == [120, 240]


def test_zones_fc_plafonnees_a_cinq():
    zones = _extract_hr_zones({"heartRateZones": [{"secsInZone": 60}] * 8})
    assert len(zones) == 5


@pytest.mark.parametrize("brut", [None, {}, {"heartRateZones": []}])
def test_zones_fc_absentes(brut):
    assert _extract_hr_zones(brut) == []


# ── Splits ────────────────────────────────────────────────────────────


def test_splits_depuis_lap_dtos():
    brut = {"lapDTOs": [
        {"distance": 1000, "duration": 300, "averageHR": 150},
        {"distance": 1000, "duration": 290, "averageHR": 155},
    ]}
    splits = _extract_splits(brut)
    assert [s["index"] for s in splits] == [1, 2]
    assert splits[1]["avg_heart_rate"] == 155


def test_splits_avec_noms_de_champs_alternatifs():
    brut = {"splitSummaries": [
        {"totalDistanceInMeters": 5000, "totalElapsedTime": 1500,
         "averageHeartRate": 148, "totalAscent": 30},
    ]}
    split = _extract_splits(brut)[0]
    assert split["distance_meters"] == 5000
    assert split["duration_seconds"] == 1500
    assert split["elevation_gain"] == 30


def test_splits_ignorent_les_entrees_non_conformes():
    assert _extract_splits({"laps": ["texte", 42, None]}) == []


@pytest.mark.parametrize("brut", [None, {}])
def test_splits_absents(brut):
    assert _extract_splits(brut) == []


# ── Métriques agrégées ────────────────────────────────────────────────


def test_timeline_extrait_les_metriques():
    brut = {"averageSpeed": 3.2, "elevationGain": 120, "normPower": 240}
    metriques = _extract_timeline(brut)
    assert metriques["avg_speed"] == 3.2
    assert metriques["elevation_gain"] == 120
    assert metriques["normalized_power"] == 240


def test_timeline_vide():
    assert _extract_timeline(None) == {}


# ── Endpoints ─────────────────────────────────────────────────────────


@pytest.fixture
def activite(client, entetes, db):
    uid = db.query(User).first().id
    db.add(Activity(
        user_id=uid, garmin_id="42", activity_type="running", name="Sortie",
        start_time=datetime.combine(date.today(), datetime.min.time()).replace(hour=8),
        distance_meters=10000, duration_seconds=3000,
        raw={"hasPolyline": False, "heartRateZones": [{"secsInZone": 600}]},
    ))
    db.commit()
    return uid


def test_detail_expose_zones_et_splits(client, entetes, activite):
    corps = client.get("/activities/42", headers=entetes).json()
    assert corps["garmin_id"] == "42"
    assert corps["hr_zones_detail"][0]["seconds"] == 600
    assert corps["splits"] == []
    assert "metrics_timeline" in corps


def test_activite_inexistante(client, entetes):
    assert client.get("/activities/inexistante", headers=entetes).status_code == 404


def test_gps_absent_si_pas_de_trace(client, entetes, activite):
    corps = client.get("/activities/42/gps", headers=entetes).json()
    assert corps["has_gps"] is False
    assert corps["track"] == []


def test_gps_servi_depuis_le_cache(client, entetes, activite, db):
    """Un tracé déjà en base ne doit pas rappeler l'API Garmin."""
    ligne = db.query(Activity).filter_by(garmin_id="42").one()
    ligne.gps_track = [{"lat": 45.4, "lon": 4.9}]
    db.commit()

    corps = client.get("/activities/42/gps", headers=entetes).json()
    assert corps["has_gps"] is True
    assert corps["track"] == [{"lat": 45.4, "lon": 4.9}]


def test_liste_paginee(client, entetes, db):
    uid = db.query(User).first().id
    for i in range(5):
        db.add(Activity(user_id=uid, garmin_id=f"g{i}", activity_type="running",
                        start_time=datetime.utcnow() - timedelta(days=i)))
    db.commit()

    corps = client.get("/activities/?limit=2&offset=0", headers=entetes).json()
    assert corps["total"] == 5
    assert len(corps["items"]) == 2
    page2 = client.get("/activities/?limit=2&offset=2", headers=entetes).json()
    assert page2["items"][0]["garmin_id"] != corps["items"][0]["garmin_id"]


def test_filtre_par_type(client, entetes, db):
    uid = db.query(User).first().id
    db.add(Activity(user_id=uid, garmin_id="r", activity_type="running", start_time=datetime.utcnow()))
    db.add(Activity(user_id=uid, garmin_id="v", activity_type="cycling", start_time=datetime.utcnow()))
    db.commit()

    corps = client.get("/activities/?activity_type=cycling", headers=entetes).json()
    assert corps["total"] == 1
    assert corps["items"][0]["activity_type"] == "cycling"
    assert sorted(client.get("/activities/types", headers=entetes).json()) == ["cycling", "running"]


# ── Santé et préférences ──────────────────────────────────────────────


def test_sante_du_jour_sans_donnees(client, entetes):
    corps = client.get("/health/today", headers=entetes).json()
    assert "message" in corps


def test_sante_du_jour_avec_donnees(client, entetes, db):
    uid = db.query(User).first().id
    db.add(DailyHealth(user_id=uid, date=date.today().isoformat(), steps=12000, avg_spo2=96.0))
    db.commit()
    corps = client.get("/health/today", headers=entetes).json()
    assert corps["steps"] == 12000


def test_hrv_latest_sans_donnees(client, entetes):
    assert "message" in client.get("/health/hrv/latest", headers=entetes).json()


def test_hrv_latest_prend_la_plus_recente(client, entetes, db):
    uid = db.query(User).first().id
    db.add(HRV(user_id=uid, date="2026-08-01", last_night_avg=50))
    db.add(HRV(user_id=uid, date="2026-08-15", last_night_avg=62))
    db.commit()
    assert client.get("/health/hrv/latest", headers=entetes).json()["last_night_avg"] == 62


def test_preferences_de_navigation(client, entetes):
    assert client.get("/preferences/nav", headers=entetes).json()["hidden_tabs"] == []
    client.put("/preferences/nav", headers=entetes, json={"hidden_tabs": ["sleep", "health"]})
    assert client.get("/preferences/nav", headers=entetes).json()["hidden_tabs"] == ["sleep", "health"]
    assert client.get("/auth/me", headers=entetes).json()["nav_preferences"] == {"hidden_tabs": ["sleep", "health"]}


def test_resume_global(client, entetes, db):
    uid = db.query(User).first().id
    db.add(Activity(user_id=uid, garmin_id="a", activity_type="running",
                    start_time=datetime.utcnow(), distance_meters=12500,
                    calories=800, vo2max=54.0))
    db.add(Sleep(user_id=uid, date=date.today().isoformat(), sleep_score=88))
    db.commit()

    corps = client.get("/stats/summary", headers=entetes).json()
    assert corps["total_activities"] == 1
    assert corps["total_distance_km"] == 12.5
    assert corps["latest_sleep_score"] == 88
    assert corps["latest_vo2max"] == 54.0
