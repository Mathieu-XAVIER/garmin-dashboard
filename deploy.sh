#!/usr/bin/env bash
# deploy.sh — Déploiement sur VPS Hetzner (Ubuntu 22.04+)
# Usage : bash deploy.sh

set -euo pipefail

REPO_URL="https://github.com/TON_USERNAME/garmin-dashboard.git"
APP_DIR="/opt/garmin-dashboard"
DOMAIN=""

# ──────────────────────────────────────────────
# 1. Docker
# ──────────────────────────────────────────────
install_docker() {
    if command -v docker &>/dev/null; then
        echo "✓ Docker déjà installé"
        return
    fi
    echo "→ Installation de Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker
    usermod -aG docker "$USER"
    echo "✓ Docker installé"
}

# ──────────────────────────────────────────────
# 2. Clonage / mise à jour du repo
# ──────────────────────────────────────────────
setup_repo() {
    if [ -d "$APP_DIR/.git" ]; then
        echo "→ Mise à jour du repo..."
        git -C "$APP_DIR" pull
    else
        echo "→ Clonage du repo..."
        git clone "$REPO_URL" "$APP_DIR"
    fi
}

# ──────────────────────────────────────────────
# 3. Fichier .env backend
# ──────────────────────────────────────────────
setup_env() {
    local env_file="$APP_DIR/backend/.env"
    if [ -f "$env_file" ]; then
        echo "✓ backend/.env déjà présent"
        return
    fi

    echo "→ Génération des clés secrètes..."
    local jwt_key
    jwt_key=$(openssl rand -hex 32)
    local fernet_key
    fernet_key=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || \
                 docker run --rm python:3.12-slim python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

    cat > "$env_file" <<EOF
JWT_SECRET_KEY=${jwt_key}
GARMIN_CREDENTIAL_KEY=${fernet_key}
DATABASE_URL=sqlite:////app/data/garmin.db
ALLOWED_ORIGINS=https://${DOMAIN}
SYNC_INTERVAL_MINUTES=60
INITIAL_SYNC_DAYS=90
HOST=0.0.0.0
PORT=8000
DISCORD_WEBHOOK_URL=
EOF
    echo "✓ backend/.env créé"
}

# ──────────────────────────────────────────────
# 4. Fichier .env racine (Traefik)
# ──────────────────────────────────────────────
setup_traefik_env() {
    local env_file="$APP_DIR/.env"
    if [ -f "$env_file" ]; then
        echo "✓ .env Traefik déjà présent"
        return
    fi
    read -rp "Email pour Let's Encrypt (certificat SSL) : " acme_email
    local pg_password
    pg_password=$(openssl rand -hex 16)
    cat > "$env_file" <<EOF
DOMAIN=${DOMAIN}
ACME_EMAIL=${acme_email}
POSTGRES_PASSWORD=${pg_password}
EOF
    echo "✓ .env Traefik créé (mot de passe PostgreSQL généré automatiquement)"
}

# ──────────────────────────────────────────────
# 5. Lancement
# ──────────────────────────────────────────────
launch() {
    echo "→ Build et démarrage des conteneurs..."
    cd "$APP_DIR"
    docker compose -f docker-compose.prod.yml pull --quiet || true
    docker compose -f docker-compose.prod.yml up -d --build
    echo ""
    echo "✓ Application déployée sur https://${DOMAIN}"
    echo "  Logs : docker compose -f $APP_DIR/docker-compose.prod.yml logs -f"
}

# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
main() {
    if [ "$EUID" -ne 0 ]; then
        echo "Erreur : ce script doit être exécuté en root (sudo bash deploy.sh)"
        exit 1
    fi

    read -rp "Domaine (ex: garmin.monsite.com) : " DOMAIN

    install_docker
    setup_repo
    setup_env
    setup_traefik_env
    launch
}

main "$@"
