# PostgreSQL Read Replica Configuration for Waddles

This directory contains production-ready PostgreSQL replication configuration for scaling Waddles's database layer.

## Overview

The read replica system enables:
- **Read scaling**: Route SELECT queries to read replicas to reduce primary load
- **High availability**: Automatic failover and replica health checking
- **Monitoring**: Track replication lag and replica status in real-time
- **Load distribution**: Intelligent replica selection based on health and priority

## Files

### 1. `replication.conf`
PostgreSQL configuration for streaming replication on the primary server.

**Key Settings:**
- `wal_level = replica`: Enables replication-capable WAL logging
- `hot_standby = on`: Allows read-only queries on standby replicas
- `hot_standby_feedback = on`: Sends feedback to primary about oldest query snapshot
- `max_replication_slots = 10`: Supports up to 10 replicas
- Synchronous replication available (commented by default for better performance)

**Location:** Include in primary PostgreSQL configuration:
```bash
# In postgresql.conf
include '/path/to/replication.conf'

# Or set via docker environment
POSTGRES_INIT_ARGS="-c wal_level=replica -c hot_standby=on"
```

### 2. `replica-setup.sh`
Automated shell script to set up a read replica from the primary server.

**Prerequisites:**
- PostgreSQL client tools (`pg_basebackup`, `pg_isready`, `psql`)
- Network connectivity to primary server
- Root or postgres user privileges
- Sufficient disk space for backup

**Usage:**
```bash
# Basic setup
sudo ./replica-setup.sh <primary_host> [primary_port] [replication_user] [replication_password]

# Examples
sudo ./replica-setup.sh localhost 5432 replication mysecurepassword
sudo ./replica-setup.sh db.example.com 5432 replication mysecurepassword

# Environment variables for customization
REPLICA_DATA_DIR=/custom/path REPLICA_SLOT_NAME=my_replica ./replica-setup.sh localhost
```

**What It Does:**
1. Verifies prerequisites and connectivity
2. Creates replication user on primary (with confirmation)
3. Creates a replication slot (prevents WAL deletion during backup)
4. Takes a basebackup using `pg_basebackup`
5. Configures recovery settings with `recovery_target_timeline = 'latest'`
6. Sets proper file permissions
7. Provides next steps for starting the replica

**Output:** Detailed logs to `/var/log/postgresql/replica-setup.log`

### 3. `read_replica.py` (Flask Core Library)
Python library for intelligent read/write query routing with health checking.

**Location:** `/home/penguin/code/Waddles/libs/flask_core/flask_core/read_replica.py`

**Features:**
- Automatic replica health checking
- Replica status tracking (HEALTHY, DEGRADED, UNHEALTHY)
- Automatic failover to primary when replicas unavailable
- Connection pool management
- Replica metrics and performance tracking

**Classes:**

#### `ReadReplicaManager`
Main manager for replica health and routing.

```python
from flask_core import (
    ReadReplicaManager,
    ReplicaConfig,
    create_read_replica_manager
)

# Simple initialization with URIs
manager = create_read_replica_manager(
    primary_uri="postgres://user:pass@localhost:5432/waddlebot",
    replica_uris=[
        "postgres://user:pass@replica1:5432/waddlebot",
        "postgres://user:pass@replica2:5432/waddlebot"
    ],
    health_check_interval=30
)

# Advanced initialization with priority
manager = ReadReplicaManager(
    primary_uri="postgres://...",
    replica_configs=[
        ReplicaConfig(host="replica1", port=5432, priority=0, max_lag_seconds=30),
        ReplicaConfig(host="replica2", port=5432, priority=1, max_lag_seconds=60),
    ]
)

# Start background health checks
await manager.start_health_checks()

# Get read connection (routes to healthy replica or primary)
read_uri = manager.get_read_uri()

# Get write connection (always primary)
write_uri = manager.get_write_uri()

# Get metrics
metrics = manager.get_metrics()
# Returns: {replica_id: {status, replication_lag_seconds, ...}}

# Cleanup
await manager.cleanup()
```

#### `ReadReplicaRouter`
Routes AsyncDAL operations between primary and replicas.

```python
from flask_core import ReadReplicaRouter, init_database

dal_primary = init_database(primary_uri)
dal_replicas = [
    init_database(replica_uri)
    for replica_uri in replica_uris
]

router = ReadReplicaRouter(
    replica_manager=manager,
    dal_primary=dal_primary,
    dal_replicas=dal_replicas
)

# SELECT queries route to replicas automatically
rows = await router.select_async(query)

# INSERT/UPDATE/DELETE always use primary
await router.insert_async(table, field="value")
await router.update_async(query, field="value")
await router.delete_async(query)
```

## Integration with Flask Modules

### Example: Using Read Replicas in a Flask Module

```python
from flask import Flask
from flask_core import (
    init_database,
    ReadReplicaManager,
    ReadReplicaRouter,
    ReplicaConfig,
    setup_aaa_logging
)
import asyncio

app = Flask(__name__)
setup_aaa_logging()

# Initialize replicas
replica_configs = [
    ReplicaConfig(
        host="replica1.internal",
        port=5432,
        priority=0,  # Preferred replica
        max_lag_seconds=30
    ),
    ReplicaConfig(
        host="replica2.internal",
        port=5432,
        priority=1,  # Fallback replica
        max_lag_seconds=30
    )
]

replica_manager = ReadReplicaManager(
    primary_uri=os.getenv("DATABASE_URL"),
    replica_configs=replica_configs,
    health_check_interval=30
)

# Initialize databases
dal_primary = init_database(os.getenv("DATABASE_URL"))
dal_replicas = [
    init_database(f"postgres://...@{c.host}:{c.port}/waddlebot")
    for c in replica_configs
]

# Create router
db_router = ReadReplicaRouter(
    replica_manager=replica_manager,
    dal_primary=dal_primary,
    dal_replicas=dal_replicas
)

@app.before_request
async def startup():
    await replica_manager.start_health_checks()

@app.teardown_appcontext
async def shutdown(exception=None):
    await replica_manager.cleanup()

@app.route("/users")
async def list_users():
    # Automatically routes to replica
    users = await db_router.select_async(
        db.users.id > 0
    )
    return {"users": [dict(u) for u in users]}

@app.route("/users", methods=["POST"])
async def create_user():
    # Automatically routes to primary
    user_id = await db_router.insert_async(
        db.users,
        name=request.json["name"],
        email=request.json["email"]
    )
    return {"id": user_id}

@app.route("/health/replicas")
async def replica_health():
    # Health check endpoint
    return replica_manager.get_metrics()
```

## Monitoring and Maintenance

### Check Replica Status

```sql
-- On replica server
SELECT pg_is_in_recovery() AS is_standby;
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;

-- Check WAL receiver status
SELECT * FROM pg_stat_wal_receiver;

-- Check if open transactions block recovery
SELECT pid, usename, application_name, state
FROM pg_stat_activity
WHERE backend_type = 'walsender';
```

### Monitor from Primary

```sql
-- View active replicas
SELECT
    slot_name,
    active,
    restart_lsn,
    confirmed_flush_lsn
FROM pg_replication_slots;

-- View replication connections
SELECT
    client_addr,
    usename,
    application_name,
    backend_start,
    state
FROM pg_stat_replication;

-- Calculate replication lag
SELECT
    now() - pg_last_xact_replay_timestamp() as replication_lag,
    pg_last_wal_receive_lsn() as receive_lsn,
    pg_last_wal_replay_lsn() as replay_lsn;
```

### Health Check Endpoints

```python
# In your Flask module
@app.route("/health/replica")
def replica_health():
    return {
        "replication_lag_seconds": 2.5,
        "is_standby": True,
        "connected_to_primary": True,
        "last_check": datetime.now().isoformat()
    }
```

## Promotion to Primary (Failover)

If primary fails and you need to promote a replica to primary:

```sql
-- On replica server
SELECT pg_promote();

-- Wait for recovery to complete
SELECT pg_is_in_recovery();  -- Should return FALSE
```

Then update connection strings in your application to point to the new primary.

## Performance Tuning

### For High Read Load
```bash
# Increase number of replicas in replica_configs
# Reduce health check interval (e.g., 15 seconds for faster detection)
# Use `priority=0` for fastest replicas as preferred replicas
```

### For Low Replication Lag Requirements
```bash
# Enable synchronous replication in replication.conf (requires restart)
synchronous_commit = remote_apply
synchronous_standby_names = '*'  # All replicas must confirm

# Increase checkpoint frequency
checkpoint_timeout = 5min  # Default 15min
```

### For High Write Throughput
```bash
# Use async replication (default configuration)
synchronous_commit = on  # Just primary durability

# Tune WAL settings
wal_compression = on  # Already enabled in replication.conf
wal_writer_delay = 200ms
wal_writer_flush_after = 1MB
```

## Troubleshooting

### Replica Not Connecting to Primary
```bash
# Check connectivity
pg_isready -h primary_host -p 5432

# Verify replication user credentials
psql -h primary_host -U replication -d postgres

# Check pg_hba.conf on primary allows replication connections
# Should include: host replication replication 0.0.0.0/0 md5
```

### Replication Lag Too High
```sql
-- Check for long-running transactions on replica
SELECT pid, usename, xact_start, query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY xact_start;

-- Kill blocking transaction if necessary
SELECT pg_terminate_backend(pid);

-- Check primary for slow write rate
SELECT * FROM pg_stat_statements
WHERE query ILIKE '%UPDATE%' OR query ILIKE '%INSERT%'
ORDER BY total_time DESC;
```

### Replication Slot Failure
```sql
-- On primary: drop broken slot
SELECT pg_drop_replication_slot('slot_name');

-- On replica: remove recovery.conf and standby.signal
rm /path/to/data/recovery.conf
rm /path/to/data/standby.signal

-- Re-run replica-setup.sh to recreate
```

## Docker Deployment

### Primary Server
```dockerfile
FROM postgres:latest

COPY config/postgres/replication.conf /etc/postgresql/

ENV POSTGRES_INITDB_ARGS="-c include=/etc/postgresql/replication.conf"
```

### Replica Server
```dockerfile
FROM postgres:latest

VOLUME /var/lib/postgresql/data

# Start in recovery mode (standby)
# Data will be populated by replica-setup.sh pg_basebackup
```

### Docker Compose
```yaml
version: '3.8'

services:
  postgres-primary:
    image: postgres:latest
    environment:
      POSTGRES_INITDB_ARGS: "-c wal_level=replica -c hot_standby=on"
    volumes:
      - primary_data:/var/lib/postgresql/data
      - ./config/postgres/replication.conf:/etc/postgresql/replication.conf

  postgres-replica:
    image: postgres:latest
    depends_on:
      - postgres-primary
    environment:
      PGDATA: /var/lib/postgresql/data/replica
    volumes:
      - replica_data:/var/lib/postgresql/data/replica
    # Run replica-setup.sh in init script
    command: ["sh", "-c", "./config/postgres/replica-setup.sh postgres-primary"]

volumes:
  primary_data:
  replica_data:
```

## Security Considerations

1. **Replication User Permissions**: Least privilege
   ```sql
   CREATE USER replication REPLICATION;
   GRANT CONNECT ON DATABASE waddlebot TO replication;
   ```

2. **Network Security**: Use private networks for replication
   - Database traffic should not cross public networks
   - Use VPN or AWS security groups

3. **Passwords**: Store in Kubernetes secrets or secure vault
   ```bash
   # Kubernetes example
   kubectl create secret generic db-replication \
     --from-literal=password=secure_password
   ```

4. **Monitoring Access**: Restrict metrics endpoint
   ```python
   @app.route("/health/replicas")
   @auth_required(roles=['admin', 'monitoring'])
   async def replica_health():
       return replica_manager.get_metrics()
   ```

## References

- [PostgreSQL Documentation: Streaming Replication](https://www.postgresql.org/docs/current/warm-standby.html)
- [PostgreSQL High Availability](https://www.postgresql.org/docs/current/different-replication-setup.html)
- [Waddles Project Documentation](../../docs/)
