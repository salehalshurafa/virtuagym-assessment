#!/usr/bin/env bash
#
# Stand up a single PostgreSQL 16 container without docker-compose.
# Use this on the GCP VM when you only need Postgres (no app, no Mailpit).
#
# Reads connection settings from ../.env if present; falls back to defaults
# matching .env.example. Idempotent: if a container named virtuagym-postgres
# is already running, the script just reports its status.

set -euo pipefail

CONTAINER_NAME="virtuagym-postgres"
VOLUME_NAME="virtuagym-postgres-data"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -a; . "$ENV_FILE"; set +a
fi

POSTGRES_DB="${POSTGRES_DB:-virtuagym}"
POSTGRES_USER="${POSTGRES_USER:-virtuagym}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-virtuagym}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

if [ "$POSTGRES_PASSWORD" = "virtuagym" ]; then
    echo "WARNING: POSTGRES_PASSWORD is the default. Set a strong value in .env before exposing this VM." >&2
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is not installed. Run scripts/install-docker.sh first." >&2
    exit 1
fi

if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Container ${CONTAINER_NAME} is already running."
    docker ps --filter "name=${CONTAINER_NAME}"
    exit 0
fi

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Starting existing container ${CONTAINER_NAME}..."
    docker start "${CONTAINER_NAME}"
    exit 0
fi

echo "Creating ${CONTAINER_NAME} (postgres:16) on port ${POSTGRES_PORT}..."
docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    -e "POSTGRES_DB=${POSTGRES_DB}" \
    -e "POSTGRES_USER=${POSTGRES_USER}" \
    -e "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}" \
    -p "${POSTGRES_PORT}:5432" \
    -v "${VOLUME_NAME}:/var/lib/postgresql/data" \
    postgres:16

echo
echo "Postgres is starting. Wait a few seconds, then test the connection from your laptop:"
echo "  psql 'postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@<vm-external-ip>:${POSTGRES_PORT}/${POSTGRES_DB}'"
