"""
routes/export.py — Export des données personnelles (CSV, GPX).

Complète la suppression de compte côté RGPD : l'utilisateur doit pouvoir
récupérer ses données, pas seulement les effacer.

Ces routes exigent le jeton Bearer comme les autres : le téléchargement
passe donc par une requête XHR côté client, pas par un lien direct.
"""

import csv
import io
from datetime import date, datetime, timedelta
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import desc
from sqlalchemy.orm import Session

from auth import get_current_user
from database import Activity, DailyHealth, HRV, Sleep, User, get_db

router = APIRouter(prefix="/export", tags=["export"])


def _reponse_csv(entetes: list[str], lignes: list[list], nom_fichier: str) -> Response:
    tampon = io.StringIO()
    redacteur = csv.writer(tampon, delimiter=";")
    redacteur.writerow(entetes)
    redacteur.writerows(lignes)
    return Response(
        # BOM UTF-8 : sans lui, Excel casse les accents des en-têtes.
        content="﻿" + tampon.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'},
    )


@router.get("/activities.csv")
def exporter_activites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lignes = (
        db.query(Activity)
        .filter(Activity.user_id == current_user.id)
        .order_by(desc(Activity.start_time))
        .all()
    )
    return _reponse_csv(
        [
            "date", "nom", "type", "distance_km", "duree_secondes",
            "calories", "fc_moyenne", "fc_max", "charge", "vo2max",
            "effet_aerobie", "effet_anaerobie",
        ],
        [[
            a.start_time.isoformat() if a.start_time else "",
            a.name or "", a.activity_type or "",
            round(a.distance_meters / 1000, 3) if a.distance_meters else "",
            int(a.duration_seconds) if a.duration_seconds else "",
            a.calories or "", a.avg_heart_rate or "", a.max_heart_rate or "",
            round(a.training_load, 1) if a.training_load else "",
            a.vo2max or "", a.aerobic_training_effect or "",
            a.anaerobic_training_effect or "",
        ] for a in lignes],
        f"activites-{date.today().isoformat()}.csv",
    )


@router.get("/health.csv")
def exporter_sante(
    days: int = Query(365, ge=1, le=3650),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Santé, sommeil et HRV réunis sur une ligne par jour."""
    depuis = (date.today() - timedelta(days=days)).isoformat()
    uid = current_user.id

    sante = {
        j.date: j for j in db.query(DailyHealth).filter(
            DailyHealth.user_id == uid, DailyHealth.date >= depuis
        ).all()
    }
    sommeil = {
        s.date: s for s in db.query(Sleep).filter(
            Sleep.user_id == uid, Sleep.date >= depuis
        ).all()
    }
    vfc = {
        h.date: h for h in db.query(HRV).filter(
            HRV.user_id == uid, HRV.date >= depuis
        ).all()
    }

    lignes = []
    for jour in sorted(set(sante) | set(sommeil) | set(vfc), reverse=True):
        j, s, h = sante.get(jour), sommeil.get(jour), vfc.get(jour)
        lignes.append([
            jour,
            j.steps if j else "", j.calories_total if j else "",
            j.resting_heart_rate if j else "", j.avg_stress if j else "",
            j.body_battery_high if j else "", j.body_battery_low if j else "",
            round(s.duration_seconds / 3600, 2) if s and s.duration_seconds else "",
            s.sleep_score if s else "",
            round(s.deep_sleep_seconds / 3600, 2) if s and s.deep_sleep_seconds else "",
            round(s.rem_sleep_seconds / 3600, 2) if s and s.rem_sleep_seconds else "",
            h.last_night_avg if h else "", h.status if h else "",
        ])

    return _reponse_csv(
        [
            "date", "pas", "calories", "fc_repos", "stress_moyen",
            "body_battery_max", "body_battery_min", "sommeil_heures",
            "score_sommeil", "sommeil_profond_h", "sommeil_rem_h",
            "hrv_nuit", "hrv_statut",
        ],
        lignes,
        f"sante-{date.today().isoformat()}.csv",
    )


@router.get("/activities/{garmin_id}.gpx")
def exporter_gpx(
    garmin_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    activite = db.query(Activity).filter(
        Activity.garmin_id == garmin_id,
        Activity.user_id == current_user.id,
    ).first()
    if not activite:
        raise HTTPException(404, "Activité introuvable")
    if not activite.gps_track:
        raise HTTPException(
            404,
            "Aucun tracé GPS en cache pour cette activité. Ouvrez sa carte "
            "une première fois pour le récupérer depuis Garmin.",
        )

    depart = activite.start_time or datetime.utcnow()
    points = []
    for point in activite.gps_track:
        lat, lon = point.get("lat"), point.get("lon")
        if lat is None or lon is None:
            continue
        morceaux = [f'<trkpt lat="{lat}" lon="{lon}">']
        if point.get("altitude") is not None:
            morceaux.append(f'<ele>{point["altitude"]}</ele>')
        if point.get("time") is not None:
            # Garmin fournit un décalage en millisecondes depuis le départ.
            horodatage = depart + timedelta(milliseconds=point["time"])
            morceaux.append(f'<time>{horodatage.strftime("%Y-%m-%dT%H:%M:%SZ")}</time>')
        if point.get("hr") is not None:
            morceaux.append(
                '<extensions><gpxtpx:TrackPointExtension>'
                f'<gpxtpx:hr>{int(point["hr"])}</gpxtpx:hr>'
                '</gpxtpx:TrackPointExtension></extensions>'
            )
        morceaux.append("</trkpt>")
        points.append("".join(morceaux))

    if not points:
        raise HTTPException(404, "Le tracé enregistré ne contient aucun point exploitable")

    nom = escape(activite.name or activite.activity_type or "Activité")
    gpx = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gpx version="1.1" creator="Garmin Dashboard" '
        'xmlns="http://www.topografix.com/GPX/1/1" '
        'xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">\n'
        f"<metadata><name>{nom}</name>"
        f"<time>{depart.strftime('%Y-%m-%dT%H:%M:%SZ')}</time></metadata>\n"
        f"<trk><name>{nom}</name><type>{escape(activite.activity_type or '')}</type>"
        f"<trkseg>{''.join(points)}</trkseg></trk>\n"
        "</gpx>\n"
    )

    return Response(
        content=gpx,
        media_type="application/gpx+xml",
        headers={"Content-Disposition": f'attachment; filename="activite-{garmin_id}.gpx"'},
    )
