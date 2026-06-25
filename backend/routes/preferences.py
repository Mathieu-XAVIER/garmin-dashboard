"""
routes/preferences.py — Preferences de navigation utilisateur.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, User
from auth import get_current_user

router = APIRouter(prefix="/preferences", tags=["preferences"])


class NavPreferencesInput(BaseModel):
    hidden_tabs: list[str]


@router.get("/nav")
def get_nav_preferences(current_user: User = Depends(get_current_user)):
    prefs = current_user.nav_preferences or {}
    return {"hidden_tabs": prefs.get("hidden_tabs", [])}


@router.put("/nav")
def update_nav_preferences(
    body: NavPreferencesInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.nav_preferences = {"hidden_tabs": body.hidden_tabs}
    db.commit()
    return {"hidden_tabs": body.hidden_tabs}
