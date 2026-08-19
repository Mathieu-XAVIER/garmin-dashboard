"""
garmin_manager.py — Pool de GarminClient, un par utilisateur.
"""

import logging

from auth import decrypt_garmin_password, encrypt_garmin_password
from database import SessionLocal, User
from garmin_client import GarminClient

logger = logging.getLogger(__name__)


class GarminManager:

    def __init__(self):
        self._clients: dict[int, GarminClient] = {}

    def get_client(self, user) -> GarminClient | None:
        if not user.garmin_email or not user.garmin_password_encrypted:
            return None

        if user.id not in self._clients:
            password = decrypt_garmin_password(user.garmin_password_encrypted)
            tokens = None
            if user.garmin_tokens_encrypted:
                try:
                    tokens = decrypt_garmin_password(user.garmin_tokens_encrypted)
                except Exception as e:
                    logger.warning(f"Jetons Garmin illisibles pour user {user.id} : {e}")
            self._clients[user.id] = GarminClient(
                user.garmin_email,
                password,
                tokens=tokens,
                on_tokens=self._faire_persister(user.id),
            )

        return self._clients[user.id]

    def _faire_persister(self, user_id: int):
        """Callback de sauvegarde des jetons, avec sa propre session.

        Le client peut renouveler ses jetons depuis un thread de synchro,
        hors de toute requête : il ne peut pas réutiliser la session HTTP.
        """
        def enregistrer(tokens: str):
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.garmin_tokens_encrypted = encrypt_garmin_password(tokens)
                    db.commit()
                    logger.debug(f"Jetons Garmin mémorisés pour user {user_id}")
            except Exception as e:
                logger.warning(f"Impossible de mémoriser les jetons user {user_id} : {e}")
                db.rollback()
            finally:
                db.close()
        return enregistrer

    def invalidate(self, user_id: int):
        self._clients.pop(user_id, None)
