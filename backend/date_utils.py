"""
date_utils.py — Bornes de dates pour les colonnes DateTime.

Comparer une colonne DateTime à une date au format ISO ('2026-08-19') revient
à la comparer à minuit : tout ce qui s'est passé dans la journée est exclu.
On passe donc toujours par de vrais datetime, avec une borne haute exclusive.
"""

from datetime import date, datetime, time, timedelta


def day_start(d: date) -> datetime:
    """Minuit au début de la journée `d` (borne basse, inclusive)."""
    return datetime.combine(d, time.min)


def day_after(d: date) -> datetime:
    """Minuit au début du lendemain de `d` (borne haute, exclusive)."""
    return datetime.combine(d + timedelta(days=1), time.min)
