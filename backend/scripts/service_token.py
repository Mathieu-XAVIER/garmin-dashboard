"""Génère un jeton d'accès de longue durée pour un service tiers (ex: Jarvis).

Le jeton rendu par `/auth/login` expire au bout de 24 h (`ACCESS_TOKEN_EXPIRE_MINUTES`),
ce qui convient à un navigateur mais pas à un service qui interroge l'API sans personne
devant l'écran : il faudrait le régénérer tous les jours à la main.

Volontairement un script et non une route : aucune nouvelle surface d'API, aucun nouveau
chemin d'authentification à sécuriser. Le jeton produit est un JWT ordinaire, vérifié par
le `get_current_user` existant — seule sa date d'expiration change. Il vaut donc mot de
passe : à traiter comme une clé d'API, et à révoquer en changeant `JWT_SECRET_KEY`
(ce qui invalide aussi toutes les sessions en cours).

Usage :
    python scripts/service_token.py mon@email.fr            # 365 jours par défaut
    python scripts/service_token.py mon@email.fr --days 90
"""

import argparse
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from auth import create_access_token  # noqa: E402
from database import SessionLocal, User  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email", help="Email du compte pour lequel émettre le jeton.")
    parser.add_argument(
        "--days", type=int, default=365, help="Durée de validité en jours (défaut : 365)."
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email).first()
        if user is None:
            print(f"Aucun compte avec l'email {args.email!r}.", file=sys.stderr)
            return 1
        # Relevé avant la fermeture de la session : l'instance en sort détachée, et
        # tout attribut qu'il faudrait recharger lèverait alors une DetachedInstanceError.
        user_id = user.id
        token = create_access_token({"sub": str(user_id)}, timedelta(days=args.days))
    finally:
        db.close()

    print(f"# Jeton pour {args.email} (utilisateur {user_id}), valable {args.days} jours.")
    print("# À reporter dans le .env de Jarvis :")
    print(f"GARMIN_DASHBOARD_TOKEN={token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
