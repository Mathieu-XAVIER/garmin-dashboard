"""
garmin_client.py — Wrapper autour de python-garminconnect.
"""

import logging
import time
from datetime import date, timedelta
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
)

logger = logging.getLogger(__name__)


class GarminClient:
    CONNECT_COOLDOWN = 300

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self._client = None
        self._last_failed_attempt = 0.0

    def connect(self):
        try:
            self._client = Garmin(self.email, self.password)
            self._client.login()
            logger.info("Connecté à Garmin Connect ✓")
            return True
        except GarminConnectAuthenticationError as e:
            logger.error(f"Erreur d'authentification Garmin : {e}")
            raise
        except GarminConnectTooManyRequestsError as e:
            logger.warning(f"Rate limit Garmin — nouvelle tentative dans {self.CONNECT_COOLDOWN}s : {e}")
            self._client = None
            self._last_failed_attempt = time.time()
            return False
        except Exception as e:
            logger.warning(f"Connexion Garmin échouée (sera retentée) : {e}")
            self._client = None
            self._last_failed_attempt = time.time()
            return False

    @property
    def client(self):
        if self._client is None:
            elapsed = time.time() - self._last_failed_attempt
            if elapsed < self.CONNECT_COOLDOWN:
                logger.debug(f"Cooldown actif, prochaine tentative dans {self.CONNECT_COOLDOWN - elapsed:.0f}s")
                return None
            self.connect()
        return self._client

    def get_activities(self, start=0, limit=50):
        try:
            return self.client.get_activities(start, limit)
        except Exception as e:
            logger.error(f"Erreur get_activities : {e}")
            return []

    def get_activity_details(self, activity_id):
        try:
            return self.client.get_activity_details(activity_id)
        except Exception as e:
            logger.error(f"Erreur get_activity_details({activity_id}) : {e}")
            return {}

    def get_activities_by_date(self, start_date, end_date):
        try:
            return self.client.get_activities_by_date(
                start_date.isoformat(), end_date.isoformat()
            )
        except Exception as e:
            logger.error(f"Erreur get_activities_by_date : {e}")
            return []

    def get_stats(self, target_date):
        try:
            return self.client.get_stats(target_date.isoformat())
        except Exception as e:
            logger.error(f"Erreur get_stats({target_date}) : {e}")
            return {}

    def get_body_battery(self, start_date, end_date):
        try:
            return self.client.get_body_battery(
                start_date.isoformat(), end_date.isoformat()
            )
        except Exception as e:
            logger.error(f"Erreur get_body_battery : {e}")
            return []

    def get_stress(self, target_date):
        try:
            return self.client.get_stress_data(target_date.isoformat())
        except Exception as e:
            logger.error(f"Erreur get_stress({target_date}) : {e}")
            return {}

    def get_heart_rate(self, target_date):
        try:
            return self.client.get_heart_rates(target_date.isoformat())
        except Exception as e:
            logger.error(f"Erreur get_heart_rate({target_date}) : {e}")
            return {}

    def get_sleep(self, target_date):
        try:
            return self.client.get_sleep_data(target_date.isoformat())
        except Exception as e:
            logger.error(f"Erreur get_sleep({target_date}) : {e}")
            return {}

    def get_hrv(self, target_date):
        try:
            return self.client.get_hrv_data(target_date.isoformat())
        except Exception as e:
            logger.error(f"Erreur get_hrv({target_date}) : {e}")
            return {}

    def get_date_range(self, days_back):
        today = date.today()
        return today - timedelta(days=days_back), today
