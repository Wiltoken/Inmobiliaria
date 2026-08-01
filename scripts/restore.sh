#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Inmobiliaria Platform — Database Restore Script
# ─────────────────────────────────────────────────────────────────────────────
# Usage: docker compose -f docker-compose.prod.yml exec postgres /backups/restore.sh <backup_file>
# Or from host: make restore FILE=inmobiliaria_20240115_030000.sql.gz
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# Configuration
BACKUP_DIR="/backups"
RETENTION_DAYS=7

# PostgreSQL connection parameters
export PGPASSWORD="${POSTGRES_PASSWORD:-changeme}"
PGHOST="${PGHOST:-postgres}"
PGPORT="${PGPORT:-5432}"
PGDATABASE="${PGDATABASE:-inmobiliaria_db}"
PGUSER="${PGUSER:-inmuebles}"

# Get backup file from argument
BACKUP_FILE="${1:-}"

if [ -z "${BACKUP_FILE}" ]; then
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh "${BACKUP_DIR}"/inmobiliaria_*.sql.gz 2>/dev/null || echo "No backups found in ${BACKUP_DIR}"
    exit 1
fi

# Resolve full path
if [[ "${BACKUP_FILE}" != /* ]]; then
    BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"
else
    BACKUP_PATH="${BACKUP_FILE}"
fi

if [ ! -f "${BACKUP_PATH}" ]; then
    echo "ERROR: Backup file not found: ${BACKUP_PATH}"
    exit 1
fi

BACKUP_SIZE=$(du -h "${BACKUP_PATH}" | cut -f1)
echo "[$(date)] Starting database restore from: ${BACKUP_PATH} (${BACKUP_SIZE})"
echo "[$(date)] WARNING: This will overwrite all current data in ${PGDATABASE}"
echo "[$(date)] To proceed, type 'yes' within 10 seconds..."
echo ""

# Confirmation prompt
read -t 10 -r -p "Type 'yes' to confirm: " response || true
if [ "${response}" != "yes" ]; then
    echo "Restore cancelled."
    exit 1
fi

# Create pre-restore backup
PRE_RESTORE_FILE="${BACKUP_DIR}/pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"
echo "[$(date)] Creating pre-restore backup: ${PRE_RESTORE_FILE}"
TEMP_PRE_FILE="/tmp/pre_restore_$(date +%Y%m%d_%H%M%S).sql"
if pg_dump -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -F p -f "${TEMP_PRE_FILE}" --no-password 2>/dev/null; then
    gzip -9 -f "${TEMP_PRE_FILE}"
    mv "${TEMP_PRE_FILE}.gz" "${PRE_RESTORE_FILE}"
    chmod 640 "${PRE_RESTORE_FILE}"
    echo "[$(date)] Pre-restore backup created: ${PRE_RESTORE_FILE}"
else
    echo "[$(date)] WARNING: Could not create pre-restore backup (continuing anyway)"
fi

# Drop existing connections to the database
echo "[$(date)] Dropping existing connections..."
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${PGDATABASE}' AND pid <> pg_backend_pid();" \
    --no-password 2>/dev/null || true

# Drop and recreate the database
echo "[$(date)] Dropping and recreating database..."
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres -c \
    "DROP DATABASE IF EXISTS ${PGDATABASE};" \
    --no-password
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres -c \
    "CREATE DATABASE ${PGDATABASE};" \
    --no-password

# Restore from backup
echo "[$(date)] Restoring from backup..."

# Check if it's a gzip compressed file
if file "${BACKUP_PATH}" | grep -q "gzip"; then
    gunzip -c "${BACKUP_PATH}" | psql \
        -h "${PGHOST}" \
        -p "${PGPORT}" \
        -U "${PGUSER}" \
        -d "${PGDATABASE}" \
        --no-password \
        --echo-errors
else
    psql \
        -h "${PGHOST}" \
        -p "${PGPORT}" \
        -U "${PGUSER}" \
        -d "${PGDATABASE}" \
        -f "${BACKUP_PATH}" \
        --no-password \
        --echo-errors
fi

echo "[$(date)] Restore completed successfully!"

# Run basic verification
TABLE_COUNT=$(psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -t -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';" --no-password 2>/dev/null | tr -d ' ')
echo "[$(date)] Verification: ${TABLE_COUNT} tables in database"

echo "[$(date)] Done!"
