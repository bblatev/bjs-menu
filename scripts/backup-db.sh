#!/usr/bin/env bash
# BJS Menu - Database Backup Script
# Supports both SQLite (direct file copy) and PostgreSQL (docker pg_dump)
# Keeps backups with rotation (last 30 days)

set -euo pipefail

BACKUP_DIR="/opt/bjs-menu/backups"
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
RETENTION_DAYS=30

# Load environment from backend .env file
BACKEND_ENV="/opt/bjs-menu/backend/.env"
if [ -f "${BACKEND_ENV}" ]; then
    set -a
    # shellcheck source=/dev/null
    . "${BACKEND_ENV}"
    set +a
fi

# Also load root .env for Docker postgres vars
ROOT_ENV="/opt/bjs-menu/.env"
if [ -f "${ROOT_ENV}" ]; then
    set -a
    # shellcheck source=/dev/null
    . "${ROOT_ENV}"
    set +a
fi

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"

# Detect database type from DATABASE_URL
DATABASE_URL="${DATABASE_URL:-sqlite:///./data/bjsbar.db}"

if [[ "${DATABASE_URL}" == sqlite* ]]; then
    # =========================================================================
    # SQLite Backup
    # =========================================================================
    # Extract the file path from the URL (sqlite:///./data/bjsbar.db -> ./data/bjsbar.db)
    DB_PATH="${DATABASE_URL#sqlite:///}"

    # Resolve relative paths from the backend directory
    if [[ "${DB_PATH}" == ./* ]]; then
        DB_PATH="/opt/bjs-menu/backend/${DB_PATH}"
    fi

    if [ ! -f "${DB_PATH}" ]; then
        echo "ERROR: SQLite database file not found at ${DB_PATH}"
        exit 1
    fi

    BACKUP_FILE="${BACKUP_DIR}/bjsbar_${TIMESTAMP}.db"

    # Use sqlite3 .backup for a safe online backup (handles WAL mode correctly)
    if command -v sqlite3 &>/dev/null; then
        sqlite3 "${DB_PATH}" ".backup '${BACKUP_FILE}'"
    else
        # Fallback: copy the file (safe if no writes are happening)
        cp "${DB_PATH}" "${BACKUP_FILE}"
        # Also copy WAL and SHM files if they exist
        [ -f "${DB_PATH}-wal" ] && cp "${DB_PATH}-wal" "${BACKUP_FILE}-wal"
        [ -f "${DB_PATH}-shm" ] && cp "${DB_PATH}-shm" "${BACKUP_FILE}-shm"
    fi

    # Integrity check
    if [ ! -s "${BACKUP_FILE}" ]; then
        echo "ERROR: Backup file is empty, aborting"
        rm -f "${BACKUP_FILE}" "${BACKUP_FILE}-wal" "${BACKUP_FILE}-shm"
        exit 1
    fi

    # Compress
    gzip "${BACKUP_FILE}"
    chmod 600 "${BACKUP_FILE}.gz"
    # Clean up WAL/SHM copies if they exist
    rm -f "${BACKUP_FILE}-wal" "${BACKUP_FILE}-shm"

    FINAL_FILE="${BACKUP_FILE}.gz"
    GLOB_PATTERN="bjsbar_*.db.gz"

elif [[ "${DATABASE_URL}" == postgresql* ]]; then
    # =========================================================================
    # PostgreSQL Backup (via Docker)
    # =========================================================================
    POSTGRES_USER="${POSTGRES_USER:-postgres}"
    POSTGRES_DB="${POSTGRES_DB:-bjs_menu}"
    BACKUP_FILE="${BACKUP_DIR}/bjsbar_${TIMESTAMP}.sql"

    docker compose -f /opt/bjs-menu/docker-compose.yml exec -T db \
        pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" > "${BACKUP_FILE}"

    if [ ! -s "${BACKUP_FILE}" ]; then
        echo "ERROR: Backup file is empty, aborting"
        rm -f "${BACKUP_FILE}"
        exit 1
    fi

    gzip "${BACKUP_FILE}"
    chmod 600 "${BACKUP_FILE}.gz"
    FINAL_FILE="${BACKUP_FILE}.gz"
    GLOB_PATTERN="bjsbar_*.sql.gz"

else
    echo "ERROR: Unsupported DATABASE_URL scheme: ${DATABASE_URL}"
    exit 1
fi

# Remove backups older than retention period
find "${BACKUP_DIR}" -name "${GLOB_PATTERN}" -mtime +${RETENTION_DAYS} -delete

# Log result
BACKUP_SIZE=$(du -h "${FINAL_FILE}" | cut -f1)
echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup created: ${FINAL_FILE} (${BACKUP_SIZE})"
