"""
Session Garmin : reprise par jetons, double authentification, et
garde-fous de l'endpoint de synchronisation manuelle.
"""

import pytest

import garmin_client
from auth import decrypt_garmin_password
from database import User


class GarthSimule:
    def dumps(self):
        return "JETONS-" + "x" * 600


class GarminSimule:
    """Reproduit le contrat de garminconnect.Garmin utilisé par le wrapper."""

    appels = []

    def __init__(self, email, password, return_on_mfa=False, **kwargs):
        self.email = email
        self.password = password
        self.return_on_mfa = return_on_mfa
        self.client = GarthSimule()

    def login(self, tokenstore=None):
        if tokenstore:
            GarminSimule.appels.append("login-par-jetons")
            return (None, None)
        if self.return_on_mfa:
            GarminSimule.appels.append("mfa-demande")
            return ("needs_mfa", {"etat": "opaque"})
        GarminSimule.appels.append("login-complet")
        return (None, None)

    def resume_login(self, state, code):
        GarminSimule.appels.append(f"resume-{code}")
        if code != "123456":
            raise RuntimeError("code invalide")
        return (None, None)


@pytest.fixture(autouse=True)
def garmin_simule(monkeypatch):
    GarminSimule.appels = []
    monkeypatch.setattr(garmin_client, "Garmin", GarminSimule)
    yield GarminSimule


# ── Persistance des jetons ────────────────────────────────────────────


def test_connexion_memorise_les_jetons():
    memorises = []
    cl = garmin_client.GarminClient("g@g.fr", "pwd", on_tokens=memorises.append)
    assert cl.connect() is True
    assert memorises and memorises[0].startswith("JETONS-")


def test_jetons_existants_evitent_le_login_complet(garmin_simule):
    cl = garmin_client.GarminClient("g@g.fr", "pwd", tokens="JETONS-" + "x" * 600)
    assert cl.connect() is True
    assert garmin_simule.appels == ["login-par-jetons"]


def test_jetons_invalides_retombent_sur_le_login_complet(garmin_simule, monkeypatch):
    class JetonsRefuses(GarminSimule):
        def login(self, tokenstore=None):
            if tokenstore:
                raise RuntimeError("jetons périmés")
            GarminSimule.appels.append("login-complet")
            return (None, None)

    monkeypatch.setattr(garmin_client, "Garmin", JetonsRefuses)
    cl = garmin_client.GarminClient("g@g.fr", "pwd", tokens="périmés" * 100)
    assert cl.connect() is True
    assert garmin_simule.appels == ["login-complet"]


# ── Double authentification ───────────────────────────────────────────


def test_mfa_demande_puis_valide(client, entetes, db):
    reponse = client.put("/auth/garmin-credentials", headers=entetes,
                         json={"garmin_email": "g@g.fr", "garmin_password": "pwd"}).json()
    assert reponse["mfa_required"] is True
    assert reponse["credentials_valid"] is False
    assert client.get("/auth/me", headers=entetes).json()["garmin_mfa_pending"] is True

    assert client.post("/auth/garmin-mfa", headers=entetes, json={"code": "000000"}).status_code == 400
    assert client.post("/auth/garmin-mfa", headers=entetes, json={"code": "123456"}).status_code == 200
    assert client.get("/auth/me", headers=entetes).json()["garmin_mfa_pending"] is False


def test_code_mfa_sans_demande_en_cours(client, entetes):
    reponse = client.post("/auth/garmin-mfa", headers=entetes, json={"code": "123456"})
    assert reponse.status_code == 400


def test_jetons_stockes_chiffres(client, entetes, db):
    client.put("/auth/garmin-credentials", headers=entetes,
               json={"garmin_email": "g@g.fr", "garmin_password": "pwd"})
    client.post("/auth/garmin-mfa", headers=entetes, json={"code": "123456"})

    db.expire_all()
    utilisateur = db.query(User).first()
    assert utilisateur.garmin_tokens_encrypted
    assert "JETONS-" not in utilisateur.garmin_tokens_encrypted
    assert decrypt_garmin_password(utilisateur.garmin_tokens_encrypted).startswith("JETONS-")


def test_mot_de_passe_garmin_jamais_en_clair(client, entetes, db):
    client.put("/auth/garmin-credentials", headers=entetes,
               json={"garmin_email": "g@g.fr", "garmin_password": "secret-garmin"})
    db.expire_all()
    utilisateur = db.query(User).first()
    assert utilisateur.garmin_password_encrypted != "secret-garmin"
    assert decrypt_garmin_password(utilisateur.garmin_password_encrypted) == "secret-garmin"


def test_suppression_des_identifiants_efface_les_jetons(client, entetes, db):
    client.put("/auth/garmin-credentials", headers=entetes,
               json={"garmin_email": "g@g.fr", "garmin_password": "pwd"})
    client.post("/auth/garmin-mfa", headers=entetes, json={"code": "123456"})

    assert client.delete("/auth/garmin-credentials", headers=entetes).status_code == 200
    db.expire_all()
    utilisateur = db.query(User).first()
    assert utilisateur.garmin_email is None
    assert utilisateur.garmin_password_encrypted is None
    assert utilisateur.garmin_tokens_encrypted is None


def test_nouveaux_identifiants_invalident_les_anciens_jetons(client, entetes, db):
    client.put("/auth/garmin-credentials", headers=entetes,
               json={"garmin_email": "g@g.fr", "garmin_password": "pwd"})
    client.post("/auth/garmin-mfa", headers=entetes, json={"code": "123456"})

    client.put("/auth/garmin-credentials", headers=entetes,
               json={"garmin_email": "autre@g.fr", "garmin_password": "pwd2"})
    db.expire_all()
    assert db.query(User).first().garmin_tokens_encrypted is None


# ── Endpoint /sync ────────────────────────────────────────────────────


@pytest.mark.parametrize("jours", [0, -1, 366, 100000])
def test_sync_refuse_les_durees_hors_bornes(client, entetes, jours):
    assert client.post(f"/sync?days={jours}", headers=entetes).status_code == 422


@pytest.mark.parametrize("jours", [1, 7, 365])
def test_sync_accepte_les_durees_valides(client, entetes, jours):
    assert client.post(f"/sync?days={jours}", headers=entetes).status_code == 200


def test_sync_sans_identifiants_garmin(client, entetes):
    corps = client.post("/sync?days=7", headers=entetes).json()
    assert corps["status"] == "error"
    assert "Identifiants Garmin" in corps["message"]


def test_sync_refuse_une_synchro_concurrente(client, entetes, db):
    """Le verrou empêche de doubler la consommation du quota Garmin."""
    from scheduler import syncs_en_cours

    client.put("/auth/garmin-credentials", headers=entetes,
               json={"garmin_email": "g@g.fr", "garmin_password": "pwd"})
    syncs_en_cours.add(db.query(User).first().id)
    try:
        assert client.post("/sync?days=7", headers=entetes).status_code == 409
    finally:
        syncs_en_cours.clear()


def test_statut_de_synchro_sans_historique(client, entetes):
    corps = client.get("/sync/status", headers=entetes).json()
    assert corps["derniere"] is None
    assert corps["historique"] == []
    assert corps["en_cours"] is False
