"""
routes/dashboards.py — CRUD custom dashboards, widgets et exercices.
"""

import re
import unicodedata
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import (
    get_db, User, Activity, DailyHealth, Sleep, HRV,
    CustomDashboard, DashboardWidget, CustomExerciseLog,
)
from auth import get_current_user

router = APIRouter(prefix="/dashboards", tags=["dashboards"])

# --- Whitelist pour la resolution des donnees widget ---

ALLOWED_TABLES = {
    "activities": Activity,
    "daily_health": DailyHealth,
    "sleep": Sleep,
    "hrv": HRV,
}

ALLOWED_FIELDS = {
    "activities": {
        "distance_meters", "duration_seconds", "calories",
        "training_load", "vo2max", "avg_heart_rate", "max_heart_rate",
        "avg_speed", "avg_cadence", "aerobic_training_effect", "anaerobic_training_effect",
    },
    "daily_health": {
        "steps", "total_distance_meters", "calories_total", "calories_active",
        "floors_climbed", "moderate_intensity_minutes", "vigorous_intensity_minutes",
        "avg_stress", "max_stress", "body_battery_high", "body_battery_low",
        "avg_spo2", "resting_heart_rate", "avg_heart_rate",
    },
    "sleep": {
        "duration_seconds", "deep_sleep_seconds", "light_sleep_seconds",
        "rem_sleep_seconds", "awake_seconds", "sleep_score",
        "avg_spo2", "avg_hrv", "avg_respiration",
    },
    "hrv": {
        "weekly_avg", "last_night_avg", "last_night_5_min_high",
        "baseline_low", "baseline_high",
    },
}

TRANSFORMS = {
    "divide_1000": lambda v: round(v / 1000, 2),
    "divide_3600": lambda v: round(v / 3600, 2),
    "divide_60": lambda v: round(v / 60, 1),
    "round_1": lambda v: round(v, 1),
}


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[-\s]+", "-", text)


def _get_dashboard(db: Session, user_id: int, slug: str) -> CustomDashboard:
    d = db.query(CustomDashboard).filter_by(user_id=user_id, slug=slug).first()
    if not d:
        raise HTTPException(404, "Dashboard introuvable")
    return d


def _resolve_date_range(dashboard_config: dict | None) -> tuple[str, str]:
    cfg = dashboard_config or {}
    dr = cfg.get("date_range", {})
    if dr.get("type") == "fixed" and dr.get("start") and dr.get("end"):
        return dr["start"], dr["end"]
    rolling_days = dr.get("rolling_days", 30)
    end = date.today()
    start = end - timedelta(days=rolling_days)
    return start.isoformat(), end.isoformat()


# --- Resolution des donnees widget ---

def _resolve_objective(config: dict, start: str, end: str, dashboard_id: int, user_id: int, db: Session) -> dict:
    if config.get("exercise_type"):
        logs = (
            db.query(CustomExerciseLog)
            .filter(
                CustomExerciseLog.user_id == user_id,
                CustomExerciseLog.dashboard_id == dashboard_id,
                CustomExerciseLog.exercise_type == config["exercise_type"],
                CustomExerciseLog.date >= start,
                CustomExerciseLog.date <= end,
            )
            .all()
        )
        agg = config.get("aggregation", "max")
        reps_values = [l.reps for l in logs]
        if agg == "max":
            value = max(reps_values, default=0)
        elif agg == "sum":
            value = sum(reps_values)
        else:
            value = max(reps_values, default=0)
        return {"current_value": value, "target": config.get("target_value", 0)}

    gq = config.get("garmin_query", {})
    table_name = gq.get("table")
    field_name = gq.get("field")
    if table_name not in ALLOWED_TABLES or field_name not in ALLOWED_FIELDS.get(table_name, set()):
        return {"current_value": 0, "target": config.get("target_value", 0), "error": "Source invalide"}

    model = ALLOWED_TABLES[table_name]
    column = getattr(model, field_name)
    agg = config.get("aggregation", "sum")
    agg_func = {"sum": func.sum, "max": func.max, "avg": func.avg, "min": func.min}.get(agg, func.sum)

    query = db.query(agg_func(column)).filter(model.user_id == user_id)
    date_col = model.start_time if table_name == "activities" else model.date
    query = query.filter(date_col >= start, date_col <= end)

    if table_name == "activities" and gq.get("filter_type"):
        query = query.filter(model.activity_type.in_(gq["filter_type"]))

    raw_value = query.scalar() or 0
    transform_name = gq.get("transform")
    if transform_name and transform_name in TRANSFORMS:
        raw_value = TRANSFORMS[transform_name](raw_value)

    return {"current_value": raw_value, "target": config.get("target_value", 0)}


def _resolve_metric(config: dict, start: str, end: str, user_id: int, db: Session) -> dict:
    gq = config.get("garmin_query", {})
    table_name = gq.get("table")
    field_name = gq.get("field")
    if table_name not in ALLOWED_TABLES or field_name not in ALLOWED_FIELDS.get(table_name, set()):
        return {"value": 0, "error": "Source invalide"}

    model = ALLOWED_TABLES[table_name]
    column = getattr(model, field_name)
    date_mode = gq.get("date_mode", "latest")

    if date_mode == "latest":
        date_col = model.start_time if table_name == "activities" else model.date
        row = db.query(column).filter(model.user_id == user_id, column.isnot(None)).order_by(date_col.desc()).first()
        value = row[0] if row else 0
    elif date_mode == "avg_period":
        date_col = model.start_time if table_name == "activities" else model.date
        value = db.query(func.avg(column)).filter(model.user_id == user_id, date_col >= start, date_col <= end).scalar() or 0
    else:
        today = date.today().isoformat()
        date_col = model.start_time if table_name == "activities" else model.date
        row = db.query(column).filter(model.user_id == user_id, date_col == today).first()
        value = row[0] if row else 0

    transform_name = gq.get("transform")
    if transform_name and transform_name in TRANSFORMS:
        value = TRANSFORMS[transform_name](value)

    return {"value": value}


def _resolve_chart(config: dict, start: str, end: str, user_id: int, db: Session) -> dict:
    gq = config.get("garmin_query", {})
    table_name = gq.get("table")
    field_name = gq.get("field")
    if table_name not in ALLOWED_TABLES or field_name not in ALLOWED_FIELDS.get(table_name, set()):
        return {"labels": [], "values": [], "error": "Source invalide"}

    model = ALLOWED_TABLES[table_name]
    column = getattr(model, field_name)
    date_col = model.start_time if table_name == "activities" else model.date

    query = (
        db.query(date_col, column)
        .filter(model.user_id == user_id, date_col >= start, date_col <= end, column.isnot(None))
        .order_by(date_col)
    )

    if table_name == "activities" and gq.get("filter_type"):
        query = query.filter(model.activity_type.in_(gq["filter_type"]))

    rows = query.all()
    labels = [str(r[0])[:10] for r in rows]
    values = [r[1] for r in rows]

    transform_name = gq.get("transform")
    if transform_name and transform_name in TRANSFORMS:
        fn = TRANSFORMS[transform_name]
        values = [fn(v) if v else 0 for v in values]

    return {"labels": labels, "values": values}


def _resolve_exercise_tracker(config: dict, start: str, end: str, dashboard_id: int, user_id: int, db: Session) -> dict:
    exercises_config = config.get("exercises", [])
    logs = (
        db.query(CustomExerciseLog)
        .filter(
            CustomExerciseLog.user_id == user_id,
            CustomExerciseLog.dashboard_id == dashboard_id,
            CustomExerciseLog.date >= start,
            CustomExerciseLog.date <= end,
        )
        .order_by(CustomExerciseLog.date)
        .all()
    )

    exercise_summaries = []
    for ex_cfg in exercises_config:
        ex_logs = [l for l in logs if l.exercise_type == ex_cfg["type"]]
        reps_values = [l.reps for l in ex_logs]
        agg = ex_cfg.get("aggregation", "max")
        if agg == "max":
            best = max(reps_values, default=0)
        else:
            best = sum(reps_values)
        exercise_summaries.append({
            "type": ex_cfg["type"],
            "label": ex_cfg.get("label", ex_cfg["type"]),
            "icon": ex_cfg.get("icon", ""),
            "color": ex_cfg.get("color", "var(--teal)"),
            "target": ex_cfg.get("target", 0),
            "best": best,
        })

    entries = [
        {"id": l.id, "date": l.date, "exercise_type": l.exercise_type, "reps": l.reps}
        for l in logs
    ]

    # Charger les running entries si configuré
    running_types = config.get("running_types")
    all_running = []
    if running_types:
        rows = (
            db.query(Activity)
            .filter(
                Activity.user_id == user_id,
                Activity.activity_type.in_(running_types),
                Activity.start_time >= start,
                Activity.start_time <= end + "T23:59:59",
                Activity.distance_meters.isnot(None),
            )
            .order_by(Activity.start_time)
            .all()
        )
        all_running = [
            {
                "garmin_id": a.garmin_id,
                "name": a.name,
                "date": str(a.start_time)[:10],
                "distance_km": round((a.distance_meters or 0) / 1000, 2),
                "duration_seconds": a.duration_seconds,
                "avg_heart_rate": a.avg_heart_rate,
            }
            for a in rows
        ]

    total_km = sum(r["distance_km"] for r in all_running)
    total_runs = len(all_running)

    # Calcul de la semaine courante
    from datetime import date as dt_date
    today = dt_date.today()
    s_date = dt_date.fromisoformat(start)
    e_date = dt_date.fromisoformat(end)
    total_weeks_count = max(1, ((e_date - s_date).days + 1 + 6) // 7)
    if today < s_date:
        current_week = 0
    elif today > e_date:
        current_week = total_weeks_count
    else:
        current_week = min(total_weeks_count, max(1, (today - s_date).days // 7 + 1))

    # Calcul du breakdown hebdomadaire
    weeks = []
    if config.get("show_weekly_breakdown") and start and end:
        s = s_date
        week_num = 0
        while s <= e_date:
            week_num += 1
            w_end = min(s + timedelta(days=6), e_date)
            w_start_s, w_end_s = s.isoformat(), w_end.isoformat()
            w_logs = [l for l in logs if w_start_s <= l.date <= w_end_s]
            w_running = [r for r in all_running if w_start_s <= r["date"] <= w_end_s]
            w_km = sum(r["distance_km"] for r in w_running)

            week_data = {
                "week": week_num, "start": w_start_s, "end": w_end_s,
                "km": round(w_km, 2), "runs": len(w_running),
                "running_entries": w_running,
                "exercise_entries": [
                    {"id": l.id, "date": l.date, "exercise_type": l.exercise_type, "reps": l.reps}
                    for l in w_logs
                ],
            }
            for ex_cfg in exercises_config:
                ex_reps = [l.reps for l in w_logs if l.exercise_type == ex_cfg["type"]]
                agg = ex_cfg.get("aggregation", "max")
                week_data[ex_cfg["type"]] = max(ex_reps, default=0) if agg == "max" else sum(ex_reps)
            weeks.append(week_data)
            s = w_end + timedelta(days=1)

    return {
        "exercises": exercise_summaries,
        "entries": entries,
        "weeks": weeks,
        "total_km": round(total_km, 2),
        "total_runs": total_runs,
        "current_week": current_week,
        "total_weeks": total_weeks_count,
    }


def _resolve_activity_list(config: dict, start: str, end: str, user_id: int, db: Session) -> dict:
    query = db.query(Activity).filter(Activity.user_id == user_id)

    date_mode = config.get("date_mode", "dashboard_range")
    if date_mode == "dashboard_range":
        query = query.filter(Activity.start_time >= start, Activity.start_time <= end + "T23:59:59")

    filter_types = config.get("filter_types")
    if filter_types:
        query = query.filter(Activity.activity_type.in_(filter_types))

    query = query.order_by(Activity.start_time.desc())
    limit = config.get("limit", 10)
    rows = query.limit(limit).all()

    return {
        "activities": [
            {
                "garmin_id": a.garmin_id,
                "name": a.name,
                "activity_type": a.activity_type,
                "date": str(a.start_time)[:10] if a.start_time else None,
                "distance_km": round((a.distance_meters or 0) / 1000, 2),
                "duration_seconds": a.duration_seconds,
                "avg_heart_rate": a.avg_heart_rate,
                "calories": a.calories,
            }
            for a in rows
        ]
    }


def _resolve_widget_data(widget: DashboardWidget, dashboard: CustomDashboard, user_id: int, db: Session) -> dict:
    config = widget.config or {}
    start, end = _resolve_date_range(dashboard.config)
    wtype = widget.widget_type

    if wtype == "objective":
        return _resolve_objective(config, start, end, dashboard.id, user_id, db)
    elif wtype == "metric":
        return _resolve_metric(config, start, end, user_id, db)
    elif wtype == "chart":
        return _resolve_chart(config, start, end, user_id, db)
    elif wtype == "exercise_tracker":
        return _resolve_exercise_tracker(config, start, end, dashboard.id, user_id, db)
    elif wtype == "activity_list":
        return _resolve_activity_list(config, start, end, user_id, db)
    else:
        return {"error": f"Type de widget inconnu : {wtype}"}


# --- Schemas Pydantic ---

class DashboardCreateInput(BaseModel):
    name: str
    icon: str | None = None
    config: dict | None = None

class DashboardUpdateInput(BaseModel):
    name: str | None = None
    icon: str | None = None
    config: dict | None = None

class WidgetCreateInput(BaseModel):
    widget_type: str
    title: str
    width: str = "full"
    config: dict

class WidgetUpdateInput(BaseModel):
    title: str | None = None
    width: str | None = None
    config: dict | None = None
    position: int | None = None

class ReorderInput(BaseModel):
    order: list[int]

class ExerciseInput(BaseModel):
    date: str
    exercise_type: str
    reps: int


# --- Routes Dashboard CRUD ---

@router.get("/")
def list_dashboards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dashboards = (
        db.query(CustomDashboard)
        .filter_by(user_id=current_user.id)
        .order_by(CustomDashboard.position)
        .all()
    )
    return [
        {"id": d.id, "name": d.name, "slug": d.slug, "icon": d.icon, "position": d.position, "config": d.config}
        for d in dashboards
    ]


@router.post("/")
def create_dashboard(
    body: DashboardCreateInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    slug = _slugify(body.name)
    if not slug:
        raise HTTPException(400, "Nom invalide")

    existing = db.query(CustomDashboard).filter_by(user_id=current_user.id, slug=slug).first()
    if existing:
        raise HTTPException(400, f"Un dashboard avec le slug '{slug}' existe déjà")

    max_pos = db.query(func.max(CustomDashboard.position)).filter_by(user_id=current_user.id).scalar() or -1

    dashboard = CustomDashboard(
        user_id=current_user.id,
        name=body.name,
        slug=slug,
        icon=body.icon,
        position=max_pos + 1,
        config=body.config,
    )
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)

    return {"id": dashboard.id, "name": dashboard.name, "slug": dashboard.slug, "icon": dashboard.icon, "position": dashboard.position, "config": dashboard.config}


@router.put("/reorder")
def reorder_dashboards(
    body: ReorderInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dashboards = db.query(CustomDashboard).filter_by(user_id=current_user.id).all()
    id_map = {d.id: d for d in dashboards}
    for idx, did in enumerate(body.order):
        if did in id_map:
            id_map[did].position = idx
    db.commit()
    return {"status": "ok"}


@router.get("/{slug}")
def get_dashboard(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = _get_dashboard(db, current_user.id, slug)
    widgets = db.query(DashboardWidget).filter_by(dashboard_id=d.id).order_by(DashboardWidget.position).all()

    return {
        "id": d.id, "name": d.name, "slug": d.slug, "icon": d.icon,
        "position": d.position, "config": d.config,
        "widgets": [
            {"id": w.id, "widget_type": w.widget_type, "title": w.title, "position": w.position, "width": w.width, "config": w.config}
            for w in widgets
        ],
    }


@router.get("/{slug}/data")
def get_dashboard_data(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = _get_dashboard(db, current_user.id, slug)
    widgets = db.query(DashboardWidget).filter_by(dashboard_id=d.id).order_by(DashboardWidget.position).all()

    widgets_with_data = []
    for w in widgets:
        data = _resolve_widget_data(w, d, current_user.id, db)
        widgets_with_data.append({
            "id": w.id, "widget_type": w.widget_type, "title": w.title,
            "position": w.position, "width": w.width, "config": w.config,
            "data": data,
        })

    return {
        "dashboard": {"id": d.id, "name": d.name, "slug": d.slug, "icon": d.icon, "config": d.config},
        "widgets": widgets_with_data,
    }


@router.put("/{slug}")
def update_dashboard(
    slug: str,
    body: DashboardUpdateInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = _get_dashboard(db, current_user.id, slug)
    if body.name is not None:
        d.name = body.name
        new_slug = _slugify(body.name)
        if new_slug != d.slug:
            conflict = db.query(CustomDashboard).filter_by(user_id=current_user.id, slug=new_slug).first()
            if conflict:
                raise HTTPException(400, f"Un dashboard avec le slug '{new_slug}' existe déjà")
            d.slug = new_slug
    if body.icon is not None:
        d.icon = body.icon
    if body.config is not None:
        d.config = body.config
    db.commit()
    return {"id": d.id, "name": d.name, "slug": d.slug, "icon": d.icon, "position": d.position, "config": d.config}


@router.delete("/{slug}")
def delete_dashboard(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = _get_dashboard(db, current_user.id, slug)
    db.query(CustomExerciseLog).filter_by(dashboard_id=d.id).delete()
    db.query(DashboardWidget).filter_by(dashboard_id=d.id).delete()
    db.delete(d)
    db.commit()
    return {"status": "ok"}


# --- Routes Widget CRUD ---

@router.post("/{slug}/widgets")
def add_widget(
    slug: str,
    body: WidgetCreateInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = _get_dashboard(db, current_user.id, slug)
    valid_types = {"objective", "metric", "chart", "exercise_tracker", "activity_list"}
    if body.widget_type not in valid_types:
        raise HTTPException(400, f"Type invalide. Types possibles : {', '.join(valid_types)}")

    max_pos = db.query(func.max(DashboardWidget.position)).filter_by(dashboard_id=d.id).scalar() or -1

    widget = DashboardWidget(
        dashboard_id=d.id,
        widget_type=body.widget_type,
        title=body.title,
        position=max_pos + 1,
        width=body.width,
        config=body.config,
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)

    return {"id": widget.id, "widget_type": widget.widget_type, "title": widget.title, "position": widget.position, "width": widget.width, "config": widget.config}


@router.put("/{slug}/widgets/reorder")
def reorder_widgets(
    slug: str,
    body: ReorderInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = _get_dashboard(db, current_user.id, slug)
    widgets = db.query(DashboardWidget).filter_by(dashboard_id=d.id).all()
    id_map = {w.id: w for w in widgets}
    for idx, wid in enumerate(body.order):
        if wid in id_map:
            id_map[wid].position = idx
    db.commit()
    return {"status": "ok"}


@router.put("/{slug}/widgets/{widget_id}")
def update_widget(
    slug: str,
    widget_id: int,
    body: WidgetUpdateInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = _get_dashboard(db, current_user.id, slug)
    w = db.query(DashboardWidget).filter_by(id=widget_id, dashboard_id=d.id).first()
    if not w:
        raise HTTPException(404, "Widget introuvable")
    if body.title is not None:
        w.title = body.title
    if body.width is not None:
        w.width = body.width
    if body.config is not None:
        w.config = body.config
    if body.position is not None:
        w.position = body.position
    db.commit()
    return {"id": w.id, "widget_type": w.widget_type, "title": w.title, "position": w.position, "width": w.width, "config": w.config}


@router.delete("/{slug}/widgets/{widget_id}")
def delete_widget(
    slug: str,
    widget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = _get_dashboard(db, current_user.id, slug)
    w = db.query(DashboardWidget).filter_by(id=widget_id, dashboard_id=d.id).first()
    if not w:
        raise HTTPException(404, "Widget introuvable")
    db.delete(w)
    db.commit()
    return {"status": "ok"}


# --- Routes Exercices ---

@router.post("/{slug}/exercises")
def add_exercise(
    slug: str,
    body: ExerciseInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = _get_dashboard(db, current_user.id, slug)
    if body.reps < 0:
        raise HTTPException(400, "Le nombre de reps doit être positif")

    existing = (
        db.query(CustomExerciseLog)
        .filter_by(user_id=current_user.id, dashboard_id=d.id, date=body.date, exercise_type=body.exercise_type)
        .first()
    )
    if existing:
        existing.reps = body.reps
    else:
        db.add(CustomExerciseLog(
            user_id=current_user.id,
            dashboard_id=d.id,
            date=body.date,
            exercise_type=body.exercise_type,
            reps=body.reps,
        ))
    db.commit()
    return {"status": "ok"}


@router.delete("/{slug}/exercises/{exercise_id}")
def delete_exercise(
    slug: str,
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = _get_dashboard(db, current_user.id, slug)
    row = db.query(CustomExerciseLog).filter_by(id=exercise_id, user_id=current_user.id, dashboard_id=d.id).first()
    if not row:
        raise HTTPException(404, "Entrée introuvable")
    db.delete(row)
    db.commit()
    return {"status": "ok"}
