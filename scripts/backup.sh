#!/usr/bin/env bash
set -euo pipefail

# Oportuna — backup PostgreSQL del stack Docker.
# Uso: ./scripts/backup.sh [directorio]
# Retención por defecto: 14 días.

BACKUP_DIR="${1:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
DB_USER="${POSTGRES_USER:-oportuna}"
DB_NAME="${POSTGRES_DB:-oportuna}"

mkdir -p "$BACKUP_DIR"
umask 077

stamp="$(date +%Y-%m-%d_%H-%M-%S)"
target="$BACKUP_DIR/oportuna_${stamp}.dump"

echo "Backup -> $target"
docker compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc > "$target"
test -s "$target" || { echo "Backup vacío" >&2; exit 1; }

find "$BACKUP_DIR" -name 'oportuna_*.dump' -type f -mtime +"$RETENTION_DAYS" -delete
echo "OK ($(du -h "$target" | cut -f1))"
