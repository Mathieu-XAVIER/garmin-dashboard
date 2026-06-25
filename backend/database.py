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


class CustomDashboard(Base):
    __tablename__ = "custom_dashboards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, index=True)
    icon = Column(String, nullable=True)
    position = Column(Integer, nullable=False, default=0)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "slug", name="uq_dashboard_user_slug"),
    )


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"

    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(Integer, ForeignKey("custom_dashboards.id", ondelete="CASCADE"), nullable=False, index=True)
    widget_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    position = Column(Integer, nullable=False, default=0)
    width = Column(String, nullable=False, default="full")
    config = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CustomExerciseLog(Base):
    __tablename__ = "custom_exercise_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    dashboard_id = Column(Integer, ForeignKey("custom_dashboards.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(String, nullable=False, index=True)
    exercise_type = Column(String, nullable=False)
    reps = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "dashboard_id", "date", "exercise_type", name="uq_exercise_user_dashboard_date_type"),
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_handball_to_custom_dashboards():
    db = SessionLocal()
    try:
        # Créer le dashboard pour tous les utilisateurs avec credentials Garmin
        # (le dashboard handball était visible par tous avant la migration)
        users = db.query(User).filter(User.garmin_email.isnot(None)).all()
        for user in users:
            user_id = user.id
            existing = db.query(CustomDashboard).filter_by(user_id=user_id, slug="prepa-handball").first()
            if existing:
                continue

            dashboard = CustomDashboard(
                user_id=user_id,
                name="Prépa Handball",
                slug="prepa-handball",
                icon="🤾",
                position=0,
                config={
                    "date_range": {"type": "fixed", "start": "2026-06-30", "end": "2026-08-10"},
                    "description": "Nord Drôme Handball — Prépa physique",
                    "color": "#FF6B35",
                },
            )
            db.add(dashboard)
            db.flush()

            widgets = [
                DashboardWidget(
                    dashboard_id=dashboard.id, widget_type="objective", title="Défi Course",
                    position=0, width="quarter", config={
                        "data_source": "garmin_running_km", "target_value": 50, "unit": "km",
                        "icon": "🏃", "color": "var(--teal)", "aggregation": "sum",
                        "garmin_query": {
                            "table": "activities", "field": "distance_meters",
                            "filter_type": ["running", "trail_running", "treadmill_running", "track_running"],
                            "transform": "divide_1000",
                        },
                    },
                ),
                DashboardWidget(
                    dashboard_id=dashboard.id, widget_type="objective", title="Pompes",
                    position=1, width="quarter", config={
                        "exercise_type": "pompes", "target_value": 30, "unit": "reps",
                        "icon": "💪", "color": "var(--orange)", "aggregation": "max",
                    },
                ),
                DashboardWidget(
                    dashboard_id=dashboard.id, widget_type="objective", title="Squats",
                    position=2, width="quarter", config={
                        "exercise_type": "squats", "target_value": 50, "unit": "reps",
                        "icon": "🦵", "color": "var(--purple)", "aggregation": "max",
                    },
                ),
                DashboardWidget(
                    dashboard_id=dashboard.id, widget_type="objective", title="Abdos",
                    position=3, width="quarter", config={
                        "exercise_type": "abdos", "target_value": 80, "unit": "reps",
                        "icon": "🔥", "color": "#F59E0B", "aggregation": "max",
                    },
                ),
                DashboardWidget(
                    dashboard_id=dashboard.id, widget_type="exercise_tracker", title="Enregistrer un essai",
                    position=4, width="full", config={
                        "exercises": [
                            {"type": "pompes", "label": "Pompes", "icon": "💪", "color": "var(--orange)", "target": 30, "aggregation": "max"},
                            {"type": "squats", "label": "Squats", "icon": "🦵", "color": "var(--purple)", "target": 50, "aggregation": "max"},
                            {"type": "abdos", "label": "Abdos", "icon": "🔥", "color": "#F59E0B", "target": 80, "aggregation": "max"},
                        ],
                        "running_types": ["running", "trail_running", "treadmill_running", "track_running"],
                        "running_target_km": 50,
                        "show_input_form": True,
                        "show_weekly_breakdown": True,
                    },
                ),
            ]
            db.add_all(widgets)

            old_logs = db.query(PrepExerciseLog).filter_by(user_id=user_id).all()
            for log in old_logs:
                db.add(CustomExerciseLog(
                    user_id=user_id,
                    dashboard_id=dashboard.id,
                    date=log.date,
                    exercise_type=log.exercise_type,
                    reps=log.reps,
                ))

        db.commit()
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

    # Migration : colonne nav_preferences sur users
    user_cols = [c["name"] for c in inspector.get_columns("users")]
    if "nav_preferences" not in user_cols:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN nav_preferences JSON"))
            conn.commit()

    # Migration : handball vers custom dashboards
    if "prep_exercise_log" in inspector.get_table_names():
        _migrate_handball_to_custom_dashboards()
