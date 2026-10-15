#!/bin/sh
# Logical PostgreSQL backup in custom format (restore with scripts/restore-test.sh).
set -eu
cd "$(dirname "$0")/.."
. ./.env
DEST="${BACKUP_DIR:-/srv/backups/itsm}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.yml}"
mkdir -p "$DEST"
FILE="$DEST/itsm_$(date +%F_%H%M).dump"
docker compose -f "$COMPOSE_FILE" exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$FILE"
echo "Wrote $FILE"
