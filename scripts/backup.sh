#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Inmobiliaria Platform — Database Backup Script
# ─────────────────────────────────────────────────────────────────────────────
# Run inside the postgres container: docker compose exec postgres /scripts/backup.sh
# Or from host: make backup
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# Configuration
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/inmobiliaria_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=7

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# PostgreSQL connection parameters
export PGPASSWORD="${POSTGRES_PASSWORD:-changeme}"
# 127.0.0.1 (not "postgres"): these scripts run INSIDE the postgres container
# via `docker compose exec`, so the service hostname does not resolve here.
PGHOST="${PGHOST:-127.0.0.1}"
PGPORT="${PGPORT:-5432}"
PGDATABASE="${PGDATABASE:-inmobiliaria_db}"
PGUSER="${PGUSER:-inmuebles}"

echo "[$(date)] Starting database backup..."

# Create temporary unencrypted dump
TEMP_FILE="/tmp/inmobiliaria_${TIMESTAMP}.sql"
pg_dump \
    -h "${PGHOST}" \
    -p "${PGPORT}" \
    -U "${PGUSER}" \
    -d "${PGDATABASE}" \
    -F p \
    -f "${TEMP_FILE}" \
    --no-password \
    --verbose

# Compress with maximum compression
gzip -9 -f "${TEMP_FILE}"

# Move compressed file to backup directory
mv "${TEMP_FILE}.gz" "${BACKUP_FILE}"

# Set appropriate permissions
chmod 640 "${BACKUP_FILE}"

# Rotate old backups (keep last RETENTION_DAYS)
echo "[$(date)] Rotating backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" \
    -name "inmobiliaria_*.sql.gz" \
    -type f \
    -mtime "+${RETENTION_DAYS}" \
    -delete

# List current backups
echo "[$(date)] Current backups:"
ls -lh "${BACKUP_DIR}"/inmobiliaria_*.sql.gz 2>/dev/null || echo "No backups found"

# Verify the backup file
if [ -f "${BACKUP_FILE}" ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "[$(date)] Backup completed successfully: ${BACKUP_FILE} (${BACKUP_SIZE})"
    exit 0
else
    echo "[$(date)] ERROR: Backup file not created"
    exit 1
fi
