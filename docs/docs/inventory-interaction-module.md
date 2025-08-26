# Inventory Interaction Module Documentation

## Overview

The Inventory Interaction Module is a comprehensive multi-threaded system for tracking any item, whether IRL (In Real Life) or in-game. It provides complete CRUD operations with label support, thread-safe caching, and comprehensive Authentication, Authorization, and Auditing (AAA) logging.

## Features

- **Multi-Threaded Architecture**: ThreadPoolExecutor with configurable workers (default: 20)
- **Item Management**: Track any item with full CRUD operations
- **Label System**: Support up to 5 labels per item for categorization
- **Caching**: High-performance thread-safe caching with TTL
- **AAA Logging**: Comprehensive logging for security and audit trails
- **Health Monitoring**: Real-time metrics and system health checks

## Commands

The inventory module supports the following commands:

### Core Operations

- `!inventory add <item_name> <description> [labels]` - Add new item to inventory
- `!inventory checkout <item_name> <username>` - Check out item to user
- `!inventory checkin <item_name>` - Check item back in
- `!inventory delete <item_name>` - Remove item from inventory

### Query Operations

- `!inventory list [all|available|checkedout]` - List items with filtering
- `!inventory search <query>` - Search items by name, description, or labels
- `!inventory status <item_name>` - Get item status and checkout information
- `!inventory stats` - Get inventory statistics and metrics

### Label Management

- `!inventory labels <item_name> add <label>` - Add label to item
- `!inventory labels <item_name> remove <label>` - Remove label from item

## API Endpoints

### Inventory Management

- `GET /inventory` - List items with filtering
- `POST /inventory` - Add new item
- `GET /inventory/search` - Search items
- `GET /inventory/status` - Get item status
- `GET /inventory/stats` - Get inventory statistics

### Health and Monitoring

- `GET /health` - Health check endpoint
- `GET /metrics` - Performance metrics

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/waddlebot

# Core API Integration
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/router

# Performance Settings
MAX_WORKERS=20
MAX_LABELS_PER_ITEM=5
CACHE_TTL=300
REQUEST_TIMEOUT=30

# AAA Logging Configuration
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false
SYSLOG_HOST=localhost
SYSLOG_PORT=514
SYSLOG_FACILITY=LOCAL0

# Module Info
MODULE_NAME=inventory_interaction_module
MODULE_VERSION=1.0.0
MODULE_PORT=8024
```

## Database Schema

### Inventory Items Table

```sql
CREATE TABLE inventory_items (
    id SERIAL PRIMARY KEY,
    community_id VARCHAR(255) NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    description TEXT,
    labels TEXT[], -- JSON array of labels
    is_checked_out BOOLEAN DEFAULT FALSE,
    checked_out_to VARCHAR(255),
    checked_out_at TIMESTAMP WITH TIME ZONE,
    checked_in_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(community_id, item_name)
);
```

### Inventory Activity Table

```sql
CREATE TABLE inventory_activity (
    id SERIAL PRIMARY KEY,
    community_id VARCHAR(255) NOT NULL,
    item_id INTEGER REFERENCES inventory_items(id),
    action VARCHAR(50) NOT NULL, -- add, checkout, checkin, delete, labels
    performed_by VARCHAR(255) NOT NULL,
    details JSONB, -- Additional context
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Database Indexes

```sql
-- Performance indexes
CREATE INDEX idx_inventory_community ON inventory_items(community_id);
CREATE INDEX idx_inventory_name ON inventory_items(community_id, item_name);
CREATE INDEX idx_inventory_checkout ON inventory_items(is_checked_out, community_id);
CREATE INDEX idx_activity_community ON inventory_activity(community_id);
CREATE INDEX idx_activity_item ON inventory_activity(item_id);
```

## Logging System

The module implements comprehensive AAA logging with the following structure:

### Log Categories

- **AUTH**: Authentication events (login, logout, token refresh)
- **AUTHZ**: Authorization events (permission checks, access grants/denials)
- **AUDIT**: User actions and system changes (CRUD operations)
- **ERROR**: Error conditions and exceptions
- **SYSTEM**: System events (startup, shutdown, health checks)

### Log Structure

```
[timestamp] LEVEL module:version EVENT_TYPE community=X user=Y action=Z result=STATUS [additional_fields]
```

### Log Outputs

- **Console**: All logs to stdout/stderr for container orchestration
- **File Logging**: Structured logs to `/var/log/waddlebotlog/` with rotation
- **Syslog**: Optional syslog support for centralized logging

## Performance Features

### Multi-Threading

- ThreadPoolExecutor with configurable worker count
- Thread-safe operations for all inventory functions
- Concurrent processing for high-volume communities

### Caching

- In-memory caching with TTL for frequently accessed data
- Thread-safe cache operations with locking
- Cache invalidation on data changes

### Connection Pooling

- Database connection pooling for optimal performance
- Separate read/write connections for complex operations

## Security Features

### Input Validation

- Comprehensive validation for all user inputs
- SQL injection prevention through parameterized queries
- XSS protection for web interfaces

### Authorization

- Community-based access control
- User permission validation for all operations
- Decorator-based authorization checking

### Audit Trail

- Complete audit log of all user actions
- Immutable activity tracking
- Performance metrics for security monitoring

## Deployment

### Docker

```bash
docker build -t waddlebot-inventory-interaction .
docker run -p 8024:8024 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/waddlebot \
  -e CORE_API_URL=http://router-service:8000 \
  -v /var/log/waddlebotlog:/var/log/waddlebotlog \
  waddlebot-inventory-interaction
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inventory-interaction
spec:
  replicas: 3
  selector:
    matchLabels:
      app: inventory-interaction
  template:
    metadata:
      labels:
        app: inventory-interaction
    spec:
      containers:
      - name: inventory-interaction
        image: waddlebot-inventory-interaction:latest
        ports:
        - containerPort: 8024
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: waddlebot-secrets
              key: database-url
        - name: MAX_WORKERS
          value: "20"
        - name: CACHE_TTL
          value: "300"
        volumeMounts:
        - name: log-volume
          mountPath: /var/log/waddlebotlog
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8024
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8024
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: log-volume
        hostPath:
          path: /var/log/waddlebotlog
```

## Monitoring

### Health Checks

The module provides comprehensive health checks:

- Database connectivity
- Cache system status
- Thread pool health
- Performance metrics

### Metrics

Available metrics include:

- Total items per community
- Checked out items count
- Available items count
- Recent activity statistics
- Performance timing data
- Error rates and types

## Testing

### Unit Tests

```bash
# Run unit tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html
```

### Integration Tests

```bash
# Run integration tests
python -m pytest tests/test_api.py -v

# Test specific functionality
python -m pytest tests/test_inventory_service.py::TestInventoryService::test_add_item_success -v
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check DATABASE_URL environment variable
   - Verify PostgreSQL server is running
   - Ensure database exists and user has permissions

2. **Permission Errors**
   - Check log directory permissions (`/var/log/waddlebotlog`)
   - Ensure non-root user can write to log directory
   - Verify community and user context in requests

3. **Performance Issues**
   - Monitor thread pool utilization
   - Check cache hit rates
   - Review database query performance
   - Increase MAX_WORKERS if needed

### Log Analysis

```bash
# View inventory-specific logs
tail -f /var/log/waddlebotlog/inventory_interaction_module.log

# View audit logs
tail -f /var/log/waddlebotlog/inventory_interaction_module_audit.log

# Search for specific errors
grep "ERROR" /var/log/waddlebotlog/inventory_interaction_module_error.log
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing to the inventory interaction module.

## License

This module is part of the WaddleBot project and is licensed under the same terms as the main project.