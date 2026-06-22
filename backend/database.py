"""
database.py — Modèles SQLAlchemy et initialisation SQLite
"""

from sqlalchemy import (
    create_engine, Column, Integer, Float, String,
    DateTime, JSON, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./garmin.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    garmin_id = Column(String, unique=True, index=True, nullable=False)
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
    created_at = Column(DateTime, default=datetime.utcnow)


class DailyHealth(Base):
    __tablename__ = "daily_health"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, unique=True, index=True, nullable=False)
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


class Sleep(Base):
    __tablename__ = "sleep"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, unique=True, index=True, nullable=False)
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


class HRV(Base):
    __tablename__ = "hrv"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, unique=True, index=True, nullable=False)
    weekly_avg = Column(Float)
    last_night_avg = Column(Float)
    last_night_5_min_high = Column(Float)
    baseline_low = Column(Float)
    baseline_high = Column(Float)
    status = Column(String)
    raw = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
