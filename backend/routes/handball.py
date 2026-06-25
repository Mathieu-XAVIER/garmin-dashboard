"""
routes/handball.py — Suivi de la prépa physique handball.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import date, timedelta

from database import get_db, Activity, PrepExerciseLog, User
from auth import get_current_user

router = APIRouter(prefix="/handball", tags=["handball"])

PREP_START = date(2026, 6, 30)
PREP_END = date(2026, 8, 10)
PREP_WEEKS = 6

OBJECTIVES = {
    "course_km": 50,
    "pompes": 30,
    "squats": 50,
    "abdos": 80,
}

RUNNING_TYPES = {"running", "trail_running", "treadmill_running", "track_running"}


def _week_bounds(week_num: int) -> tuple[date, date]:
    start = PREP_START + timedelta(weeks=week_num - 1)
    end = start + timedelta(days=6)
    return start, min(end, PREP_END)


def _get_running_entries(db: Session, start: date, end: date, uid: int) -> list[dict]:
    rows = (
        db.query(Activity)
        .filter(
            Activity.user_id == uid,
            Activity.activity_type.in_(RUNNING_TYPES),
            Activity.start_time >= start.isoformat(),
            Activity.start_time <= (end + timedelta(days=1)).isoformat(),
            Activity.distance_meters.isnot(None),
        )
        .order_by(Activity.start_time)
        .all()
    )
    return [
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


def _get_exercises(db: Session, start: date, end: date, uid: int) -> list[dict]:
    rows = (
        db.query(PrepExerciseLog)
        .filter(
            PrepExerciseLog.user_id == uid,
            PrepExerciseLog.date >= start.isoformat(),
            PrepExerciseLog.date <= end.isoformat(),
        )
        .order_by(PrepExerciseLog.date)
        .all()
    )
    return [
        {
            "id": r.id,
            "date": r.date,
            "exercise_type": r.exercise_type,
            "reps": r.reps,
        }
        for r in rows
    ]


@router.get("/prep")
def get_prep(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uid = current_user.id
    today = date.today()
    current_week = min(PREP_WEEKS, max(1, (today - PREP_START).days // 7 + 1))
    if today < PREP_START:
        current_week = 0
    elif today > PREP_END:
        current_week = PREP_WEEKS

    running = _get_running_entries(db, PREP_START, PREP_END, uid)
    exercises = _get_exercises(db, PREP_START, PREP_END, uid)

    total_km = sum(r["distance_km"] for r in running)

    best_pompes = max((e["reps"] for e in exercises if e["exercise_type"] == "pompes"), default=0)
    best_squats = max((e["reps"] for e in exercises if e["exercise_type"] == "squats"), default=0)
    best_abdos = max((e["reps"] for e in exercises if e["exercise_type"] == "abdos"), default=0)

    weeks = []
    for w in range(1, PREP_WEEKS + 1):
        w_start, w_end = _week_bounds(w)
        w_running = [r for r in running if w_start.isoformat() <= r["date"] <= w_end.isoformat()]
        w_exercises = [e for e in exercises if w_start.isoformat() <= e["date"] <= w_end.isoformat()]
        w_km = sum(r["distance_km"] for r in w_running)
        w_pompes = max((e["reps"] for e in w_exercises if e["exercise_type"] == "pompes"), default=0)
        w_squats = max((e["reps"] for e in w_exercises if e["exercise_type"] == "squats"), default=0)
        w_abdos = max((e["reps"] for e in w_exercises if e["exercise_type"] == "abdos"), default=0)

        weeks.append({
            "week": w,
            "start": w_start.isoformat(),
            "end": w_end.isoformat(),
            "km": round(w_km, 2),
            "runs": len(w_running),
            "pompes": w_pompes,
            "squats": w_squats,
            "abdos": w_abdos,
            "running_entries": w_running,
            "exercise_entries": w_exercises,
        })

    return {
        "prep_start": PREP_START.isoformat(),
        "prep_end": PREP_END.isoformat(),
        "current_week": current_week,
        "total_weeks": PREP_WEEKS,
        "objectives": OBJECTIVES,
        "totals": {
            "km": round(total_km, 2),
            "runs": len(running),
            "best_pompes": best_pompes,
            "best_squats": best_squats,
            "best_abdos": best_abdos,
        },
        "weeks": weeks,
    }


class ExerciseInput(BaseModel):
    date: str
    exercise_type: str
    reps: int


@router.post("/exercises")
def add_exercise(
    body: ExerciseInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.exercise_type not in ("pompes", "squats", "abdos"):
        raise HTTPException(400, "Type invalide : pompes, squats ou abdos")
    if body.reps < 0:
        raise HTTPException(400, "Le nombre de reps doit être positif")

    existing = (
        db.query(PrepExerciseLog)
        .filter_by(user_id=current_user.id, date=body.date, exercise_type=body.exercise_type)
        .first()
    )
    if existing:
        existing.reps = body.reps
    else:
        db.add(PrepExerciseLog(
            user_id=current_user.id,
            date=body.date,
            exercise_type=body.exercise_type,
            reps=body.reps,
        ))
    db.commit()
    return {"status": "ok"}


@router.delete("/exercises/{exercise_id}")
def delete_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.query(PrepExerciseLog).filter_by(id=exercise_id, user_id=current_user.id).first()
    if not row:
        raise HTTPException(404, "Entrée introuvable")
    db.delete(row)
    db.commit()
    return {"status": "ok"}
