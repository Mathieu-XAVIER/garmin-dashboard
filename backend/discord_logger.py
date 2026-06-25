"""
discord_logger.py — Handler logging qui envoie les erreurs vers un webhook Discord.
"""

import json
import os
import logging
import traceback
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError


def _get_webhook_url() -> str | None:
    return os.getenv("DISCORD_WEBHOOK_URL")


def send_discord_message(title: str, description: str, color: int = 0xFF6B35, fields: list[dict] | None = None):
    url = _get_webhook_url()
    if not url:
        return

    embed = {
        "title": title,
        "description": description[:4000],
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": "Garmin Dashboard"},
    }
    if fields:
        embed["fields"] = fields[:25]

    payload = json.dumps({"embeds": [embed]}).encode()
    req = Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        urlopen(req, timeout=10)
    except (URLError, OSError) as e:
        logging.getLogger(__name__).warning("Échec envoi webhook Discord : %s", e)


def send_discord_error(title: str, description: str, fields: list[dict] | None = None):
    send_discord_message(f"🔴 {title}", description, color=0xFF6B35, fields=fields)


class DiscordHandler(logging.Handler):
    def __init__(self, level=logging.ERROR):
        super().__init__(level)

    def emit(self, record: logging.LogRecord):
        if not _get_webhook_url():
            return

        title = f"{record.levelname} — {record.name}"
        description = record.getMessage()

        fields = []
        if record.exc_info and record.exc_info[1]:
            tb = "".join(traceback.format_exception(*record.exc_info))
            fields.append({
                "name": "Traceback",
                "value": f"```\n{tb[-1000:]}\n```",
                "inline": False,
            })

        fields.append({
            "name": "Fichier",
            "value": f"`{record.pathname}:{record.lineno}`",
            "inline": True,
        })

        send_discord_error(title, description, fields)


def setup_discord_logging():
    if not _get_webhook_url():
        logging.getLogger(__name__).warning(
            "DISCORD_WEBHOOK_URL non défini — les logs ne seront pas envoyés sur Discord"
        )
        return
    handler = DiscordHandler(level=logging.ERROR)
    logging.getLogger().addHandler(handler)
    send_discord_message(
        "✅ Garmin Dashboard démarré",
        "Le webhook Discord est opérationnel.",
        color=0x57F287,
    )
    logging.getLogger(__name__).info("Discord logging activé")
