#!/usr/bin/env bash
# BJS Menu - Database Backup Script
# Backs up the SQLite database with rotation (keeps last 30 days)

set -euo pipefail

BACKUP_DIR="/opt/bjs-menu/backups"
DB_PATH="/opt/bjs-menu/backend/data/bjsbar.db"
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/bjsbar_${TIMESTAMP}.db"
RETENTION_DAYS=30

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Check database exists
if [ ! -f "${DB_PATH}" ]; then
    echo "ERROR: Database not found at ${DB_PATH}"
    exit 1
fi

# Use SQLite's .backup command for a consistent backup (safe even while DB is in use)
sqlite3 "${DB_PATH}" ".backup '${BACKUP_FILE}'"

# Compress the backup
gzip "${BACKUP_FILE}"

# Remove backups older than retention period
find "${BACKUP_DIR}" -name "bjsbar_*.db.gz" -mtime +${RETENTION_DAYS} -delete

# Log result
BACKUP_SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup created: ${BACKUP_FILE}.gz (${BACKUP_SIZE})"
