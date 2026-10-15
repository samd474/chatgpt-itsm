#!/bin/sh
# Restore a dump into a throwaway database to prove the backup works.
# Usage: scripts/restore-test.sh /srv/backups/itsm/itsm_2026-10-15_0200.dump
set -eu
cd "$(dirname "$0")/.."
. ./.env
DUMP="$1"
COMPOSE_FILE="${COMPOSE_FILE:-compose.yml}"
DB=itsm_restore_test
docker compose -f "$COMPOSE_FILE" exec -T db dropdb -U "$POSTGRES_USER" --if-exists "$DB"
docker compose -f "$COMPOSE_FILE" exec -T db createdb -U "$POSTGRES_USER" "$DB"
start=$(date +%s)
docker compose -f "$COMPOSE_FILE" exec -T db pg_restore -U "$POSTGRES_USER" --no-owner -d "$DB" < "$DUMP"
docker compose -f "$COMPOSE_FILE" exec -T db psql -U "$POSTGRES_USER" -d "$DB" -c "SELECT count(*) AS help_requests FROM helprequests_helprequests;"
echo "Restore took $(( $(date +%s) - start ))s. Drop it with: docker compose exec db dropdb -U $POSTGRES_USER $DB"
