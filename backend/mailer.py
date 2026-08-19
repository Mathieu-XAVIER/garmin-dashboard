"""
mailer.py — Envoi d'e-mails transactionnels (réinitialisation de mot de passe).

Si le SMTP n'est pas configuré, le message est écrit dans les logs au niveau
WARNING : une instance auto-hébergée reste utilisable sans serveur mail.
"""

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def smtp_configure() -> bool:
    return bool(os.getenv("SMTP_HOST"))


def envoyer_email(destinataire: str, sujet: str, corps: str) -> bool:
    """Retourne True si le message est réellement parti par SMTP."""
    if not smtp_configure():
        logger.warning(
            "SMTP non configuré — e-mail non envoyé.\n"
            "  À : %s\n  Sujet : %s\n%s", destinataire, sujet, corps
        )
        return False

    message = EmailMessage()
    message["From"] = os.getenv("SMTP_FROM", "no-reply@garmin-dashboard.local")
    message["To"] = destinataire
    message["Subject"] = sujet
    message.set_content(corps)

    hote = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    utilisateur = os.getenv("SMTP_USER")
    mot_de_passe = os.getenv("SMTP_PASSWORD")

    try:
        if port == 465:
            serveur = smtplib.SMTP_SSL(hote, port, timeout=15)
        else:
            serveur = smtplib.SMTP(hote, port, timeout=15)
        with serveur:
            if port != 465:
                serveur.starttls()
            if utilisateur and mot_de_passe:
                serveur.login(utilisateur, mot_de_passe)
            serveur.send_message(message)
        logger.info("E-mail envoyé à %s", destinataire)
        return True
    except Exception as e:
        logger.error("Échec d'envoi de l'e-mail à %s : %s", destinataire, e)
        return False
