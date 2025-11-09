#!/bin/bash

# SQLite Database Backup Script
# Backs up the game platform database with compression and retention

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB_FILE="${PROJECT_ROOT}/data/game_platform.db"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="game_platform_${DATE}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if database exists
if [ ! -f "$DB_FILE" ]; then
    log_error "Database file not found: $DB_FILE"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

log_info "Starting database backup..."
log_info "Database: $DB_FILE"
log_info "Backup directory: $BACKUP_DIR"

# Check if sqlite3 is installed
if ! command -v sqlite3 &> /dev/null; then
    log_error "sqlite3 command not found. Please install SQLite."
    exit 1
fi

# Perform backup using SQLite's backup command (handles WAL mode correctly)
log_info "Creating backup: ${BACKUP_NAME}.db"
sqlite3 "$DB_FILE" ".backup '${BACKUP_DIR}/${BACKUP_NAME}.db'"

if [ $? -ne 0 ]; then
    log_error "Backup failed"
    exit 1
fi

# Verify backup
ORIGINAL_SIZE=$(stat -f%z "$DB_FILE" 2>/dev/null || stat -c%s "$DB_FILE" 2>/dev/null)
BACKUP_SIZE=$(stat -f%z "${BACKUP_DIR}/${BACKUP_NAME}.db" 2>/dev/null || stat -c%s "${BACKUP_DIR}/${BACKUP_NAME}.db" 2>/dev/null)

log_info "Original size: $ORIGINAL_SIZE bytes"
log_info "Backup size: $BACKUP_SIZE bytes"

if [ "$BACKUP_SIZE" -lt 1000 ]; then
    log_error "Backup file suspiciously small, something may have gone wrong"
    exit 1
fi

# Compress backup
log_info "Compressing backup..."
gzip "${BACKUP_DIR}/${BACKUP_NAME}.db"

if [ $? -ne 0 ]; then
    log_error "Compression failed"
    exit 1
fi

COMPRESSED_SIZE=$(stat -f%z "${BACKUP_DIR}/${BACKUP_NAME}.db.gz" 2>/dev/null || stat -c%s "${BACKUP_DIR}/${BACKUP_NAME}.db.gz" 2>/dev/null)
COMPRESSION_RATIO=$(echo "scale=2; $COMPRESSED_SIZE * 100 / $BACKUP_SIZE" | bc)

log_info "Compressed size: $COMPRESSED_SIZE bytes (${COMPRESSION_RATIO}% of original)"

# Clean up old backups
log_info "Cleaning up backups older than $RETENTION_DAYS days..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "game_platform_*.db.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)

if [ "$DELETED_COUNT" -gt 0 ]; then
    log_info "Deleted $DELETED_COUNT old backup(s)"
else
    log_info "No old backups to delete"
fi

# List current backups
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "game_platform_*.db.gz" | wc -l)
log_info "Current backup count: $BACKUP_COUNT"

# Calculate total backup size
TOTAL_SIZE=$(find "$BACKUP_DIR" -name "game_platform_*.db.gz" -exec stat -f%z {} + 2>/dev/null || find "$BACKUP_DIR" -name "game_platform_*.db.gz" -exec stat -c%s {} + 2>/dev/null | awk '{s+=$1} END {print s}')
TOTAL_SIZE_MB=$(echo "scale=2; $TOTAL_SIZE / 1024 / 1024" | bc)

log_info "Total backup storage: ${TOTAL_SIZE_MB} MB"

log_info "Backup completed successfully: ${BACKUP_NAME}.db.gz"

# Exit successfully
exit 0
