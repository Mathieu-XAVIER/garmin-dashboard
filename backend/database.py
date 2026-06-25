"""
database.py — Modèles SQLAlchemy et initialisation SQLite
"""

from sqlalchemy import (
    create_engine, Column, Integer, Float, String,
    DateTime, JSON, ForeignKey, UniqueConstraint, text, inspect as sa_inspect
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./garmin.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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
    created_at = Column(DateTime, default=datetime.utcnow)


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


class PrepExerciseLog(Base):
    __tablename__ = "prep_exercise_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    date = Column(String, nullable=False, index=True)
    exercise_type = Column(String, nullable=False)  # pompes, squats, abdos
    reps = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "date", "exercise_type", name="uq_prep_user_date_type"),
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    inspector = sa_inspect(engine)

    # Migration : colonne gps_track
    act_cols = [c["name"] for c in inspector.get_columns("activities")]
    if "gps_track" not in act_cols:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE activities ADD COLUMN gps_track JSON"))
            conn.commit()

    # Migration : colonne user_id sur toutes les tables de données
    tables_to_migrate = ["activities", "daily_health", "sleep", "hrv", "prep_exercise_log"]
    for table_name in tables_to_migrate:
        if table_name in inspector.get_table_names():
            cols = [c["name"] for c in inspector.get_columns(table_name)]
            if "user_id" not in cols:
                with engine.connect() as conn:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                    conn.commit()
