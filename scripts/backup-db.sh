#!/usr/bin/env bash
# BJS Menu - PostgreSQL Database Backup Script
# Backs up the PostgreSQL database with rotation (keeps last 30 days)

set -euo pipefail

BACKUP_DIR="/opt/bjs-menu/backups"
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/bjsbar_${TIMESTAMP}.sql"
RETENTION_DAYS=30

# Load credentials from .env file if available
ENV_FILE="/opt/bjs-menu/.env"
if [ -f "${ENV_FILE}" ]; then
    # Export only POSTGRES_* variables from .env
    set -a
    # shellcheck source=/dev/null
    . "${ENV_FILE}"
    set +a
fi

# Defaults if not set via environment or .env
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-bjsbar}"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Dump the PostgreSQL database from the Docker container
# Uses docker compose to handle varying container names
docker compose -f /opt/bjs-menu/docker-compose.yml exec -T db \
    pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" > "${BACKUP_FILE}"

# Integrity check: verify the backup file is non-empty before compressing
if [ ! -s "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file is empty, aborting"
    rm -f "${BACKUP_FILE}"
    exit 1
fi

# Compress the backup
gzip "${BACKUP_FILE}"

# Remove backups older than retention period
find "${BACKUP_DIR}" -name "bjsbar_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

# Log result
BACKUP_SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup created: ${BACKUP_FILE}.gz (${BACKUP_SIZE})"
