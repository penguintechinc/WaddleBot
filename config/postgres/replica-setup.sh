#!/bin/bash
# PostgreSQL Read Replica Setup Script for Waddles
# Sets up streaming replication from primary to standby server
# Usage: ./replica-setup.sh [primary_host] [replication_user] [replication_password]

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

PRIMARY_HOST="${1:-localhost}"
PRIMARY_PORT="${2:-5432}"
REPLICATION_USER="${3:-replication}"
REPLICATION_PASSWORD="${4:-changeme}"
REPLICA_DATA_DIR="${REPLICA_DATA_DIR:-/var/lib/postgresql/replica_data}"
REPLICA_SLOT_NAME="${REPLICA_SLOT_NAME:-waddlebot_replica_1}"

# Logging
LOG_FILE="/var/log/postgresql/replica-setup.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE"
    exit 1
}

# =============================================================================
# Pre-flight Checks
# =============================================================================

log "Starting PostgreSQL read replica setup..."
log "Primary Host: $PRIMARY_HOST:$PRIMARY_PORT"
log "Replication User: $REPLICATION_USER"
log "Replica Data Directory: $REPLICA_DATA_DIR"

# Check if PostgreSQL is installed
if ! command -v pg_basebackup &> /dev/null; then
    error "PostgreSQL client tools not found. Install postgresql-client package."
fi

# Check if running as root or postgres user
if [[ $EUID -ne 0 ]] && [[ $(whoami) != "postgres" ]]; then
    error "This script must be run as root or postgres user"
fi

# Verify connectivity to primary
log "Verifying connectivity to primary database..."
if ! pg_isready -h "$PRIMARY_HOST" -p "$PRIMARY_PORT" &> /dev/null; then
    error "Cannot connect to primary database at $PRIMARY_HOST:$PRIMARY_PORT"
fi

# =============================================================================
# Step 1: Create Replication User on Primary (if needed)
# =============================================================================

log "Step 1: Setting up replication user on primary..."

# This step requires connection to primary with superuser privileges
# Typically done by DBA or automated setup
read -p "Create replication user on primary? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    PGPASSWORD="$REPLICATION_PASSWORD" psql -h "$PRIMARY_HOST" -p "$PRIMARY_PORT" -U postgres -tc \
        "CREATE USER IF NOT EXISTS $REPLICATION_USER WITH REPLICATION ENCRYPTED PASSWORD '$REPLICATION_PASSWORD';" \
        || log "User may already exist, continuing..."
    log "Replication user created/verified"
fi

# =============================================================================
# Step 2: Create Replication Slot on Primary
# =============================================================================

log "Step 2: Creating replication slot on primary..."

PGPASSWORD="$REPLICATION_PASSWORD" psql -h "$PRIMARY_HOST" -p "$PRIMARY_PORT" -U "$REPLICATION_USER" -tc \
    "SELECT slot_name FROM pg_replication_slots WHERE slot_name = '$REPLICA_SLOT_NAME';" | grep -q "$REPLICA_SLOT_NAME" && \
    log "Slot already exists" || \
    (PGPASSWORD="$REPLICATION_PASSWORD" psql -h "$PRIMARY_HOST" -p "$PRIMARY_PORT" -U "$REPLICATION_USER" -tc \
    "SELECT * FROM pg_create_physical_replication_slot('$REPLICA_SLOT_NAME');" && \
    log "Replication slot created")

# =============================================================================
# Step 3: Create Data Directory for Replica
# =============================================================================

log "Step 3: Preparing replica data directory..."

if [ -d "$REPLICA_DATA_DIR" ]; then
    if [ -n "$(ls -A "$REPLICA_DATA_DIR")" ]; then
        read -p "Replica directory exists and is not empty. Remove and reinit? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log "Removing existing replica data directory..."
            rm -rf "$REPLICA_DATA_DIR"
        else
            log "Keeping existing directory. Ensure recovery.conf is properly configured."
        fi
    fi
fi

if [ ! -d "$REPLICA_DATA_DIR" ]; then
    mkdir -p "$REPLICA_DATA_DIR"
    chown postgres:postgres "$REPLICA_DATA_DIR"
    chmod 700 "$REPLICA_DATA_DIR"
    log "Created replica data directory: $REPLICA_DATA_DIR"
fi

# =============================================================================
# Step 4: Take Basebackup from Primary
# =============================================================================

log "Step 4: Taking basebackup from primary (this may take a while)..."
log "Backup size depends on primary database size"

# pg_basebackup pulls data from primary and streams WAL
# Using replication slot ensures no WAL files are discarded during backup
PGPASSWORD="$REPLICATION_PASSWORD" pg_basebackup \
    -h "$PRIMARY_HOST" \
    -p "$PRIMARY_PORT" \
    -U "$REPLICATION_USER" \
    -D "$REPLICA_DATA_DIR" \
    -v \
    -P \
    -Xs \
    -R \
    -S "$REPLICA_SLOT_NAME" \
    -C \
    || error "Failed to take basebackup"

log "Basebackup completed successfully"

# =============================================================================
# Step 5: Configure Recovery Settings
# =============================================================================

log "Step 5: Configuring recovery settings..."

# The -R flag in pg_basebackup creates standby.signal and postgresql.auto.conf
# Verify and update if needed

# Ensure standby.signal exists (marks this as standby server)
if [ ! -f "$REPLICA_DATA_DIR/standby.signal" ]; then
    touch "$REPLICA_DATA_DIR/standby.signal"
    log "Created standby.signal"
fi

# Update postgresql.auto.conf with primary connection info
cat >> "$REPLICA_DATA_DIR/postgresql.auto.conf" << EOF

# Waddles Read Replica Configuration
primary_conninfo = 'host=$PRIMARY_HOST port=$PRIMARY_PORT user=$REPLICATION_USER password=$REPLICATION_PASSWORD application_name=$REPLICA_SLOT_NAME'
primary_slot_name = '$REPLICA_SLOT_NAME'
hot_standby = on
hot_standby_feedback = on
recovery_target_timeline = 'latest'

EOF

log "Updated postgresql.auto.conf with replication settings"

# =============================================================================
# Step 6: Set Proper Permissions
# =============================================================================

log "Step 6: Setting permissions..."

chown -R postgres:postgres "$REPLICA_DATA_DIR"
chmod -R 700 "$REPLICA_DATA_DIR"
chmod 600 "$REPLICA_DATA_DIR"/postgresql.auto.conf
log "Permissions set correctly"

# =============================================================================
# Step 7: Verify Configuration
# =============================================================================

log "Step 7: Verifying configuration..."

# Check for required files
if [ ! -f "$REPLICA_DATA_DIR/standby.signal" ]; then
    error "standby.signal not found"
fi

if ! grep -q "primary_conninfo" "$REPLICA_DATA_DIR/postgresql.auto.conf"; then
    error "primary_conninfo not configured"
fi

log "Configuration verified"

# =============================================================================
# Final Instructions
# =============================================================================

cat << EOF

================================================================================
PostgreSQL Read Replica Setup Complete
================================================================================

Next Steps:

1. Start the PostgreSQL replica server:
   sudo systemctl start postgresql
   or
   docker run -d --name postgres-replica \\
     -e PGDATA=$REPLICA_DATA_DIR \\
     -v $REPLICA_DATA_DIR:$REPLICA_DATA_DIR \\
     postgres:latest

2. Monitor replication on the replica:
   psql -U postgres
   > SELECT * FROM pg_stat_replication;

3. Monitor replication on the primary:
   psql -U postgres
   > SELECT * FROM pg_stat_replication;
   > SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;

4. Verify the replica is accepting connections:
   psql -h localhost -U postgres
   > SELECT version();

5. To promote replica to primary (in case of primary failure):
   psql -U postgres
   > SELECT pg_promote();

6. Monitor replica lag in your application:
   psql -U postgres
   > SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;

Key Configuration Files:
- Primary: /etc/postgresql/postgresql.conf (includes replication.conf)
- Replica: $REPLICA_DATA_DIR/postgresql.auto.conf

Troubleshooting:
- Check logs: tail -f /var/log/postgresql/postgresql.log
- Verify slot status: SELECT * FROM pg_replication_slots;
- Check WAL sender: SELECT * FROM pg_stat_replication;
- Verify backup was successful: ls -lah $REPLICA_DATA_DIR

For monitoring and alerting, enable these views:
- pg_stat_replication: Shows active replication connections
- pg_replication_slots: Shows replication slot status
- pg_stat_wal_receiver: Shows WAL receiver status on replica

================================================================================

EOF

log "PostgreSQL read replica setup completed successfully"
log "Replica data directory: $REPLICA_DATA_DIR"
log "Monitor progress with: tail -f /var/log/postgresql/postgresql.log"
