#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ ! -f "${PROJECT_DIR}/.env.prod" ]; then
    echo "[ERROR] No se encontro .env.prod. Ejecuta primero: bash scripts/setup-env-gcp.sh"
    exit 1
fi

source "${PROJECT_DIR}/.env.prod"
BACKUP_DIR="${PROJECT_DIR}/backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%F_%H%M)
BACKUP_FILE="${BACKUP_DIR}/si2_backup_${TIMESTAMP}.sql"

echo "Creando backup: ${BACKUP_FILE}"

docker compose --env-file "${PROJECT_DIR}/.env.prod" \
    -f "${PROJECT_DIR}/docker-compose.prod.yml" \
    exec -T postgres \
    pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" > "$BACKUP_FILE"

gzip "$BACKUP_FILE"
echo "Backup completado: ${BACKUP_FILE}.gz"

# Keep only last 7 backups
ls -t "${BACKUP_DIR}"/si2_backup_*.sql.gz 2>/dev/null | tail -n +8 | xargs rm -f 2>/dev/null || true
