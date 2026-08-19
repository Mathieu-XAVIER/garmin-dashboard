"""Inscription, connexion, cycle de vie du mot de passe."""

import os
import re
from datetime import datetime, timedelta

import pytest

from conftest import creer_utilisateur
from database import PasswordResetToken, User


# ── Inscription ───────────────────────────────────────────────────────


def test_mot_de_passe_trop_court_refuse(client):
    r = client.post("/auth/register", json={"email": "a@exemple.fr", "password": "court12"})
    assert r.status_code == 400
    assert "8 caractères" in r.json()["detail"]


def test_email_deja_pris_refuse(client):
    creer_utilisateur(client, "a@exemple.fr")
    r = client.post("/auth/register", json={"email": "a@exemple.fr", "password": "motdepasse"})
    assert r.status_code == 400


def test_inscriptions_fermees(client, monkeypatch):
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    r = client.post("/auth/register", json={"email": "z@exemple.fr", "password": "motdepasse"})
    assert r.status_code == 403


def test_fermeture_n_empeche_pas_les_connexions(client, monkeypatch):
    """Fermer les inscriptions ne doit pas verrouiller les comptes existants."""
    creer_utilisateur(client, "a@exemple.fr")
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    r = client.post("/auth/login", data={"username": "a@exemple.fr", "password": "motdepasse"})
    assert r.status_code == 200


# ── Connexion ─────────────────────────────────────────────────────────


def test_mauvais_mot_de_passe(client):
    creer_utilisateur(client, "a@exemple.fr")
    r = client.post("/auth/login", data={"username": "a@exemple.fr", "password": "mauvais123"})
    assert r.status_code == 401


def test_compte_inexistant(client):
    r = client.post("/auth/login", data={"username": "fantome@exemple.fr", "password": "motdepasse"})
    assert r.status_code == 401


def test_me_expose_l_etat_du_compte(client, entetes):
    corps = client.get("/auth/me", headers=entetes).json()
    assert corps["email"] == "a@exemple.fr"
    assert corps["has_garmin_credentials"] is False
    assert corps["garmin_mfa_pending"] is False
    assert "hashed_password" not in corps


def test_le_mot_de_passe_est_hache_en_base(client, db):
    creer_utilisateur(client, "a@exemple.fr")
    utilisateur = db.query(User).first()
    assert utilisateur.hashed_password != "motdepasse"
    assert utilisateur.hashed_password.startswith("$2b$")


# ── Changement de mot de passe ────────────────────────────────────────


def test_changement_exige_le_mot_de_passe_actuel(client, entetes):
    r = client.put("/auth/password", headers=entetes,
                   json={"current_password": "faux", "new_password": "nouveaumdp"})
    assert r.status_code == 400


def test_changement_applique_la_longueur_minimale(client, entetes):
    r = client.put("/auth/password", headers=entetes,
                   json={"current_password": "motdepasse", "new_password": "court12"})
    assert r.status_code == 400


def test_changement_reussi_invalide_l_ancien(client, entetes):
    r = client.put("/auth/password", headers=entetes,
                   json={"current_password": "motdepasse", "new_password": "nouveaumdp"})
    assert r.status_code == 200
    assert client.post("/auth/login", data={"username": "a@exemple.fr", "password": "nouveaumdp"}).status_code == 200
    assert client.post("/auth/login", data={"username": "a@exemple.fr", "password": "motdepasse"}).status_code == 401


# ── Réinitialisation ──────────────────────────────────────────────────


def _demander_reinitialisation(client, caplog, email="a@exemple.fr"):
    """Déclenche l'envoi et récupère le jeton dans les logs (SMTP non configuré)."""
    with caplog.at_level("WARNING"):
        client.post("/auth/forgot-password", json={"email": email})
    trouve = re.search(r"token=([A-Za-z0-9_-]+)", caplog.text)
    return trouve.group(1) if trouve else None


def test_adresse_inconnue_repond_comme_une_connue(client):
    """L'endpoint ne doit pas permettre d'énumérer les comptes inscrits."""
    creer_utilisateur(client, "a@exemple.fr")
    connue = client.post("/auth/forgot-password", json={"email": "a@exemple.fr"})
    inconnue = client.post("/auth/forgot-password", json={"email": "fantome@exemple.fr"})
    assert connue.status_code == inconnue.status_code == 200
    assert connue.json() == inconnue.json()


def test_aucun_jeton_cree_pour_une_adresse_inconnue(client, db):
    client.post("/auth/forgot-password", json={"email": "fantome@exemple.fr"})
    assert db.query(PasswordResetToken).count() == 0


def test_seul_le_hash_du_jeton_est_stocke(client, caplog, db):
    creer_utilisateur(client, "a@exemple.fr")
    jeton = _demander_reinitialisation(client, caplog)
    assert jeton
    enregistre = db.query(PasswordResetToken).first()
    assert enregistre.token_hash != jeton
    assert jeton not in enregistre.token_hash


def test_cycle_de_reinitialisation_complet(client, caplog):
    creer_utilisateur(client, "a@exemple.fr")
    jeton = _demander_reinitialisation(client, caplog)
    r = client.post("/auth/reset-password", json={"token": jeton, "new_password": "nouveaumdp"})
    assert r.status_code == 200
    assert client.post("/auth/login", data={"username": "a@exemple.fr", "password": "nouveaumdp"}).status_code == 200


def test_jeton_utilisable_une_seule_fois(client, caplog):
    creer_utilisateur(client, "a@exemple.fr")
    jeton = _demander_reinitialisation(client, caplog)
    assert client.post("/auth/reset-password", json={"token": jeton, "new_password": "nouveaumdp"}).status_code == 200
    rejeu = client.post("/auth/reset-password", json={"token": jeton, "new_password": "encoreautre"})
    assert rejeu.status_code == 400


def test_jeton_inconnu_refuse(client):
    r = client.post("/auth/reset-password", json={"token": "inexistant", "new_password": "nouveaumdp"})
    assert r.status_code == 400


def test_jeton_expire_refuse(client, caplog, db):
    creer_utilisateur(client, "a@exemple.fr")
    jeton = _demander_reinitialisation(client, caplog)
    enregistre = db.query(PasswordResetToken).first()
    enregistre.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()
    r = client.post("/auth/reset-password", json={"token": jeton, "new_password": "nouveaumdp"})
    assert r.status_code == 400


def test_nouvelle_demande_invalide_la_precedente(client, caplog, db):
    creer_utilisateur(client, "a@exemple.fr")
    premier = _demander_reinitialisation(client, caplog)
    caplog.clear()
    second = _demander_reinitialisation(client, caplog)
    assert premier != second
    assert client.post("/auth/reset-password", json={"token": premier, "new_password": "nouveaumdp"}).status_code == 400
    assert client.post("/auth/reset-password", json={"token": second, "new_password": "nouveaumdp"}).status_code == 200


def test_reinitialisation_applique_la_longueur_minimale(client, caplog):
    creer_utilisateur(client, "a@exemple.fr")
    jeton = _demander_reinitialisation(client, caplog)
    assert client.post("/auth/reset-password", json={"token": jeton, "new_password": "court12"}).status_code == 400
