"""
garmin_manager.py — Pool de GarminClient, un par utilisateur.
"""

import logging
from auth import decrypt_garmin_password
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
            self._clients[user.id] = GarminClient(user.garmin_email, password)

        return self._clients[user.id]

    def invalidate(self, user_id: int):
        self._clients.pop(user_id, None)
