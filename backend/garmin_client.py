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

    def __init__(self, email: str, password: str, tokens: str | None = None,
                 on_tokens=None):
        self.email = email
        self.password = password
        self.tokens = tokens
        # Appelé avec les jetons sérialisés dès qu'une session valide est
        # établie, pour que l'appelant les persiste.
        self.on_tokens = on_tokens
        self._client = None
        self._last_failed_attempt = 0.0

    def _memoriser_tokens(self, garmin):
        if not self.on_tokens:
            return
        try:
            tokens = garmin.client.dumps()
        except Exception as e:
            logger.debug(f"Sérialisation des jetons Garmin impossible : {e}")
            return
        if tokens and tokens != self.tokens:
            self.tokens = tokens
            self.on_tokens(tokens)

    def connect(self):
        """Ouvre une session Garmin. Retourne True si connecté.

        Reprend d'abord les jetons mémorisés : c'est ce qui évite un login
        SSO complet (et un MFA) à chaque redémarrage du backend.
        """
        if self.tokens:
            try:
                garmin = Garmin(self.email, self.password)
                garmin.login(tokenstore=self.tokens)
                self._client = garmin
                logger.info("Session Garmin reprise depuis les jetons ✓")
                self._memoriser_tokens(garmin)
                return True
            except Exception as e:
                logger.info(f"Jetons Garmin inutilisables, login complet : {e}")
                self.tokens = None

        try:
            garmin = Garmin(self.email, self.password)
            garmin.login()
            self._client = garmin
            logger.info("Connecté à Garmin Connect ✓")
            self._memoriser_tokens(garmin)
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

    # ── MFA ───────────────────────────────────────────────────────────
    def demarrer_login_mfa(self):
        """Lance un login en s'arrêtant si Garmin réclame un code MFA.

        Retourne ("mfa", state) si un code est attendu, ("ok", None) si la
        session est ouverte sans MFA.
        """
        garmin = Garmin(self.email, self.password, return_on_mfa=True)
        statut, state = garmin.login()
        if statut == "needs_mfa":
            return "mfa", (garmin, state)
        self._client = garmin
        self._memoriser_tokens(garmin)
        return "ok", None

    def terminer_login_mfa(self, garmin, state, code: str):
        """Rejoue le login avec le code MFA saisi par l'utilisateur."""
        garmin.resume_login(state, code)
        self._client = garmin
        self._memoriser_tokens(garmin)
        return True

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

    def get_activity_gps(self, activity_id):
        """Récupère le tracé GPS d'une activité via l'API Garmin."""
        try:
            details = self.client.get_activity_details(activity_id)
            if not details:
                return None
            geo = details.get("geoPolylineDTO") or {}
            polyline = geo.get("polyline")
            if polyline and isinstance(polyline, list):
                return polyline
            return None
        except Exception as e:
            logger.error(f"Erreur get_activity_gps({activity_id}) : {e}")
            return None

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

    # Contrairement aux méthodes ci-dessus, ces trois-là laissent remonter
    # leurs erreurs : la synchro les intercepte et les journalise dans
    # SyncLog. Les avaler ici produirait un statut « ok » alors qu'une
    # source a échoué — c'est ce qui masquait le bug des prédictions.
    def get_body_composition(self, start_date, end_date):
        return self.client.get_body_composition(
            start_date.isoformat(), end_date.isoformat()
        )

    def get_training_readiness(self, target_date):
        return self.client.get_training_readiness(target_date.isoformat())

    def get_race_predictions(self):
        """Garmin refuse une plage partielle et ne renvoie que la dernière
        estimation : on appelle donc sans aucun paramètre."""
        return self.client.get_race_predictions()

    def get_date_range(self, days_back):
        today = date.today()
        return today - timedelta(days=days_back), today
