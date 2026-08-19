"""
conftest.py — Fixtures partagées.

L'environnement est fixé AVANT tout import applicatif : database.py lit
DATABASE_URL au moment de l'import pour construire son engine.
"""

import os
import tempfile

_dossier = tempfile.mkdtemp(prefix="garmin-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_dossier}/test.db"
os.environ["JWT_SECRET_KEY"] = "cle-de-test-non-secrete"
os.environ["RUN_SCHEDULER"] = "false"
os.environ["ALLOW_REGISTRATION"] = "true"
os.environ.pop("SMTP_HOST", None)
# backend/.env est chargé par main.py : sans ça, les tests enverraient
# leurs logs vers le vrai webhook Discord du projet.
os.environ["DISCORD_WEBHOOK_URL"] = ""

from cryptography.fernet import Fernet  # noqa: E402

os.environ["GARMIN_CREDENTIAL_KEY"] = Fernet.generate_key().decode()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from routes import auth as routes_auth  # noqa: E402
from scheduler import syncs_en_cours  # noqa: E402

# Les quotas d'appels fausseraient les tests qui enchaînent les requêtes.
main.limiter.enabled = False
routes_auth.limiter.enabled = False


@pytest.fixture(scope="session")
def client():
    with TestClient(main.app) as c:
        yield c


@pytest.fixture(autouse=True)
def base_vierge(client):
    """Repart d'une base vide et d'un état mémoire propre à chaque test."""
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    syncs_en_cours.clear()
    routes_auth._mfa_en_attente.clear()
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def creer_utilisateur(client, email="a@exemple.fr", mot_de_passe="motdepasse"):
    """Inscrit un utilisateur et retourne ses en-têtes d'authentification."""
    reponse = client.post("/auth/register", json={"email": email, "password": mot_de_passe})
    assert reponse.status_code == 200, reponse.text
    return {"Authorization": f"Bearer {reponse.json()['access_token']}"}


@pytest.fixture
def entetes(client):
    return creer_utilisateur(client)
