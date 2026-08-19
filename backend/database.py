"""
database.py — Modèles SQLAlchemy et initialisation SQLite
"""

import os

from sqlalchemy import (
    create_engine, Column, Integer, Float, String, Text,
    DateTime, JSON, ForeignKey, UniqueConstraint, Index, text, inspect as sa_inspect
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./garmin.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    garmin_email = Column(String, nullable=True)
    garmin_password_encrypted = Column(String, nullable=True)
    # Jetons de session Garmin sérialisés puis chiffrés (Fernet). Les
    # conserver évite un login SSO complet — et donc un MFA — à chaque
    # redémarrage, principale cause de blocage temporaire côté Garmin.
    garmin_tokens_encrypted = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    nav_preferences = Column(JSON, nullable=True)


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    garmin_id = Column(String, index=True, nullable=False)
    activity_type = Column(String)
    name = Column(String)
    start_time = Column(DateTime)
    duration_seconds = Column(Float)
    distance_meters = Column(Float)
    calories = Column(Integer)
    avg_heart_rate = Column(Integer)
    max_heart_rate = Column(Integer)
    avg_speed = Column(Float)
    avg_cadence = Column(Integer)
    training_load = Column(Float)
    vo2max = Column(Float)
    aerobic_training_effect = Column(Float)
    anaerobic_training_effect = Column(Float)
    hr_zones = Column(JSON)
    raw = Column(JSON)
    gps_track = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "garmin_id", name="uq_activity_user_garmin"),
    )


class DailyHealth(Base):
    __tablename__ = "daily_health"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    date = Column(String, index=True, nullable=False)
    steps = Column(Integer)
    total_distance_meters = Column(Float)
    calories_total = Column(Integer)
    calories_active = Column(Integer)
    floors_climbed = Column(Integer)
    moderate_intensity_minutes = Column(Integer)
    vigorous_intensity_minutes = Column(Integer)
    avg_stress = Column(Integer)
    max_stress = Column(Integer)
    body_battery_high = Column(Integer)
    body_battery_low = Column(Integer)
    avg_spo2 = Column(Float)
    resting_heart_rate = Column(Integer)
    avg_heart_rate = Column(Integer)
    raw = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_health_user_date"),
    )


class Sleep(Base):
    __tablename__ = "sleep"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    date = Column(String, index=True, nullable=False)
    sleep_start = Column(DateTime)
    sleep_end = Column(DateTime)
    duration_seconds = Column(Integer)
    deep_sleep_seconds = Column(Integer)
    light_sleep_seconds = Column(Integer)
    rem_sleep_seconds = Column(Integer)
    awake_seconds = Column(Integer)
    sleep_score = Column(Integer)
    avg_spo2 = Column(Float)
    avg_hrv = Column(Float)
    avg_respiration = Column(Float)
    raw = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_sleep_user_date"),
    )


class HRV(Base):
    __tablename__ = "hrv"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    date = Column(String, index=True, nullable=False)
    weekly_avg = Column(Float)
    last_night_avg = Column(Float)
    last_night_5_min_high = Column(Float)
    baseline_low = Column(Float)
    baseline_high = Column(Float)
    status = Column(String)
    raw = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_hrv_user_date"),
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Seul le hash est stocké : une fuite de la base ne permet pas de
    # réinitialiser les mots de passe.
    token_hash = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # "auto" (scheduler), "manuel" (bouton) ou "initiale" (saisie des identifiants)
    declencheur = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    # "ok", "partiel" (des erreurs mais des données récupérées) ou "erreur"
    statut = Column(String, nullable=True)
    days_back = Column(Integer, nullable=True)
    activities = Column(Integer, default=0)
    daily_health = Column(Integer, default=0)
    sleep = Column(Integer, default=0)
    hrv = Column(Integer, default=0)
    erreur = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_sync_logs_user_started", "user_id", "started_at"),
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ajouter_colonne(inspector, table: str, colonne: str, type_sql: str):
    """Ajoute une colonne si elle manque (migration sans Alembic)."""
    if table not in inspector.get_table_names():
        return
    if colonne in [c["name"] for c in inspector.get_columns(table)]:
        return
    with engine.connect() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {colonne} {type_sql}"))
        conn.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    inspector = sa_inspect(engine)

    _ajouter_colonne(inspector, "activities", "gps_track", "JSON")
    for table in ("activities", "daily_health", "sleep", "hrv"):
        _ajouter_colonne(inspector, table, "user_id", "INTEGER REFERENCES users(id)")
    _ajouter_colonne(inspector, "users", "nav_preferences", "JSON")
    _ajouter_colonne(inspector, "users", "garmin_tokens_encrypted", "TEXT")
