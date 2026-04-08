# Schedule Service - Comprehensive Workflow Scheduling

## Overview

The `ScheduleService` provides complete scheduling capabilities for WaddleBot workflows with support for:

- **Cron Schedules**: Standard cron expressions (e.g., "0 12 * * *" for daily at noon)
- **Interval Schedules**: Recurring execution at fixed intervals (in seconds)
- **One-Time Schedules**: Single execution at a specific datetime
- **Background Execution**: APScheduler integration for background job management
- **Missed Execution Handling**: Grace period for handling missed schedules
- **Execution Limits**: Support for max execution counts per schedule
- **Persistence**: PostgreSQL storage with async database operations
- **Comprehensive Logging**: AAA (Authentication, Authorization, Audit) logging

## Architecture

### Components

```
ScheduleService
├── APScheduler Integration
│   ├── AsyncIOScheduler for background jobs
│   ├── CronTrigger for cron schedules
│   ├── IntervalTrigger for interval schedules
│   └── Event listeners for job execution tracking
├── croniter Integration
│   ├── Cron expression parsing
│   ├── Next execution calculation
│   └── Timezone support
├── Database Management
│   ├── Async database operations via AsyncDAL
│   ├── workflow_schedules table persistence
│   └── Execution history tracking
├── WorkflowEngine Integration
│   ├── Trigger workflow execution
│   ├── Pass execution context
│   └── Track execution results
└── Logging System
    ├── AAA logging for all operations
    ├── Event tracking (AUDIT, SYSTEM, ERROR)
    └── Execution metrics
```

### Database Schema

The service uses the `workflow_schedules` table (created in migrations):

```sql
CREATE TABLE workflow_schedules (
    id SERIAL PRIMARY KEY,
    schedule_id UUID UNIQUE NOT NULL,
    workflow_id UUID NOT NULL,

    -- Schedule Configuration
    schedule_type VARCHAR(50) NOT NULL,  -- 'cron', 'interval', 'one_time'
    cron_expression VARCHAR(255),         -- For cron type
    interval_seconds INTEGER,             -- For interval type
    scheduled_time TIMESTAMP,             -- For one_time type
    timezone VARCHAR(100) DEFAULT 'UTC',

    -- Status & Execution
    is_active BOOLEAN DEFAULT true,
    next_execution_at TIMESTAMP,
    last_execution_at TIMESTAMP,
    last_execution_id UUID,

    -- Limits
    max_executions INTEGER,               -- NULL = unlimited
    execution_count INTEGER DEFAULT 0,

    -- Context
    context_data JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Usage

### 1. Initialize ScheduleService

```python
from services.schedule_service import ScheduleService
from services.workflow_engine import WorkflowEngine
from flask_core import AsyncDAL

# Initialize dependencies
dal = AsyncDAL(database_uri, read_replicas)
workflow_engine = WorkflowEngine(dal)

# Create ScheduleService
schedule_service = ScheduleService(
    dal=dal,
    workflow_engine=workflow_engine,
    grace_period_minutes=15,  # Grace period for missed executions
    logger_instance=logger    # Optional: custom logger
)
```

### 2. Start and Stop Scheduler

```python
# Start background scheduler (loads all active schedules from DB)
await schedule_service.start_scheduler()

# Stop gracefully (waits for pending jobs)
await schedule_service.stop_scheduler()
```

### 3. Create Cron Schedule

```python
schedule_config = {
    "schedule_type": "cron",
    "cron_expression": "0 12 * * *",  # Daily at noon
    "timezone": "America/New_York",
    "max_executions": None  # No limit
}

result = await schedule_service.add_schedule(
    workflow_id="abc-123-def",
    schedule_config=schedule_config,
    user_id=42,
    community_id=1,
    context_data={
        "custom_param": "value",
        "user_context": {"role": "admin"}
    }
)

print(result["schedule_id"])      # UUID of created schedule
print(result["next_execution_at"]) # Calculated next run time
```

### 4. Create Interval Schedule

```python
schedule_config = {
    "schedule_type": "interval",
    "interval_seconds": 3600,  # Run every hour
    "max_executions": 24       # Run max 24 times
}

result = await schedule_service.add_schedule(
    workflow_id="abc-123-def",
    schedule_config=schedule_config,
    user_id=42,
    community_id=1
)
```

### 5. Create One-Time Schedule

```python
from datetime import datetime, timedelta

schedule_config = {
    "schedule_type": "one_time",
    "scheduled_time": (datetime.utcnow() + timedelta(hours=2)).isoformat()
}

result = await schedule_service.add_schedule(
    workflow_id="abc-123-def",
    schedule_config=schedule_config,
    user_id=42,
    community_id=1
)
```

### 6. Update Schedule

```python
updated = await schedule_service.update_schedule(
    schedule_id="schedule-uuid",
    schedule_config={
        "schedule_type": "cron",
        "cron_expression": "0 9 * * *",  # Changed to 9 AM
        "timezone": "UTC"
    },
    user_id=42
)
```

### 7. Remove Schedule

```python
removed = await schedule_service.remove_schedule(
    schedule_id="schedule-uuid",
    user_id=42
)
```

### 8. Check Due Schedules

```python
# Manually check for due schedules (typically runs every minute in background)
triggered = await schedule_service.check_due_schedules()

for item in triggered:
    print(f"Triggered: {item['schedule_id']} -> {item['execution_id']}")
```

### 9. Calculate Next Execution

```python
from services.schedule_service import ScheduleService

next_run = ScheduleService.calculate_next_execution(
    schedule_type="cron",
    cron_expression="0 12 * * *",
    timezone="UTC"
)
print(f"Next execution: {next_run}")
```

## Schedule Types

### Cron Schedules

Standard Unix cron expressions with 5 fields:

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
│ │ │ │ │
* * * * *
```

**Examples:**
- `0 0 * * *` - Daily at midnight
- `0 12 * * *` - Daily at noon
- `0 9-17 * * 1-5` - Every hour 9 AM to 5 PM on weekdays
- `*/15 * * * *` - Every 15 minutes
- `0 0 1 * *` - First day of month at midnight
- `0 0 * * 0` - Every Sunday at midnight

### Interval Schedules

Interval in seconds:

```python
schedule_config = {
    "schedule_type": "interval",
    "interval_seconds": 3600,  # Every hour
    "max_executions": 24       # Stop after 24 executions
}
```

**Common Intervals:**
- `60` - Every minute
- `3600` - Every hour
- `86400` - Every day
- `604800` - Every week

### One-Time Schedules

Single execution at specific time:

```python
schedule_config = {
    "schedule_type": "one_time",
    "scheduled_time": "2024-12-25T15:30:00",  # ISO 8601 format
}
```

Must be in the future. Once executed, automatically marked as inactive.

## Execution Flow

### Workflow Triggering

1. **Schedule Due Check**: Every minute, `check_due_schedules()` checks for workflows ready to execute
2. **Grace Period Check**: Only workflows within grace period (default 15 min) are executed
3. **Limit Check**: Verifies schedule hasn't exceeded max_executions
4. **Trigger Data Preparation**: Combines schedule context with execution metadata
5. **Workflow Execution**: Calls `WorkflowEngine.execute_workflow()` with trigger data
6. **State Update**: Updates execution count and next execution time
7. **Audit Logging**: Records execution in audit trail

### Trigger Data Structure

```python
trigger_data = {
    "schedule_id": "schedule-uuid",
    "execution_id": "execution-uuid",
    "triggered_at": "2024-12-20T12:00:00",
    # ... custom context_data from schedule ...
    "custom_param": "value",
    "user_context": {"role": "admin"}
}
```

## Features

### Grace Period Handling

Handles missed executions gracefully:

```python
# Schedule missed execution window check
# If schedule should have run 30 minutes ago but grace period is 15 minutes,
# it will NOT be executed (prevents backlog)

schedule_service = ScheduleService(
    dal=dal,
    workflow_engine=workflow_engine,
    grace_period_minutes=15  # Configurable
)
```

### Execution Limits

Control maximum executions per schedule:

```python
# Limited execution schedule
schedule_config = {
    "schedule_type": "cron",
    "cron_expression": "0 * * * *",
    "max_executions": 100  # Stop after 100 runs
}

# Unlimited execution schedule
schedule_config = {
    "schedule_type": "cron",
    "cron_expression": "0 * * * *",
    "max_executions": None  # Run forever
}
```

When max_executions is reached, schedule is automatically deactivated.

### Context Data

Pass custom context to workflows:

```python
context_data = {
    "workflow_param1": "value1",
    "notification_settings": {
        "email": True,
        "slack": False
    },
    "retry_config": {
        "max_retries": 3,
        "backoff": "exponential"
    }
}

await schedule_service.add_schedule(
    workflow_id="abc-123-def",
    schedule_config=schedule_config,
    user_id=42,
    community_id=1,
    context_data=context_data
)
```

### APScheduler Integration

Automatic background job scheduling:

```python
# Cron schedules automatically registered with APScheduler
# Interval schedules automatically registered with APScheduler
# One-time schedules handled by check_due_schedules loop

# The service manages:
# - Job registration/deregistration
# - Event listening for execution tracking
# - Error handling and retry logic
# - Graceful shutdown with pending job completion
```

## Logging

Comprehensive AAA logging for audit and debugging:

### Log Levels

- **AUDIT**: All schedule operations (create, update, remove, execute)
- **SYSTEM**: Scheduler lifecycle events (start, stop, load schedules)
- **ERROR**: Execution failures and exceptions

### Log Structure

```
[timestamp] LEVEL module:version EVENT_TYPE community=X user=Y action=Z result=STATUS

Example:
2024-12-20 12:00:00 INFO schedule_service:1.0.0 AUDIT community=1 user=42 action=schedule_create result=SUCCESS schedule_id=abc-123 workflow_id=def-456 schedule_type=cron
```

### Log Events

- `schedule_service_init` - Service initialization
- `scheduler_start` - Scheduler started
- `scheduler_stop` - Scheduler stopped
- `schedule_create` - Schedule created
- `schedule_update` - Schedule configuration updated
- `schedule_remove` - Schedule deactivated
- `schedule_triggered` - Workflow triggered by schedule
- `schedule_executed` - Schedule successfully executed
- `schedule_missed` - Execution missed grace period
- `schedule_limit_reached` - Max executions reached
- `scheduler_job_executed` - APScheduler job completed
- `scheduler_job_error` - APScheduler job failed

## Error Handling

### Exception Types

```python
from services.schedule_service import (
    ScheduleServiceException,      # Base exception
    ScheduleNotFoundException,      # Schedule not found (404)
    InvalidScheduleException,       # Invalid configuration (400)
)
```

### Common Errors

**Invalid Cron Expression:**
```python
try:
    schedule_config = {
        "schedule_type": "cron",
        "cron_expression": "invalid cron"  # Invalid
    }
    await schedule_service.add_schedule(...)
except InvalidScheduleException as e:
    print(f"Cron error: {e.message}")  # "Invalid cron expression: ..."
```

**Missing Required Field:**
```python
try:
    schedule_config = {
        "schedule_type": "cron"
        # Missing cron_expression
    }
    await schedule_service.add_schedule(...)
except InvalidScheduleException as e:
    print(f"Config error: {e.message}")  # "cron_expression required..."
```

**Schedule Not Found:**
```python
try:
    await schedule_service.remove_schedule("non-existent-id", user_id=42)
except ScheduleNotFoundException as e:
    print(f"Not found: {e.message}")  # "Schedule not found: ..."
```

## Performance Considerations

### Database Queries

- Indexes on: `workflow_id`, `is_active`, `next_execution_at`, `schedule_type`
- Optimized queries for due schedule checking
- Bulk operations for loading schedules

### Memory Management

- Active schedules cached in memory for quick lookup
- Scheduler job registration for efficient background execution
- ThreadPoolExecutor for parallel workflow execution

### Scalability

- APScheduler handles many concurrent jobs
- Background loop checks due schedules every minute
- Grace period prevents execution backlog
- Execution limits prevent runaway schedules

## Configuration

### Environment Variables

```bash
# Scheduler Configuration
SCHEDULER_TIMEZONE=UTC                          # Default timezone
SCHEDULER_JOB_DEFAULTS_MAX_INSTANCES=3          # Max concurrent instances per job
SCHEDULER_JOB_DEFAULTS_COALESCE=true            # Coalesce missed job runs

# Workflow Execution
MAX_CONCURRENT_WORKFLOWS=10                     # Max parallel workflows
WORKFLOW_TIMEOUT_SECONDS=3600                   # Default workflow timeout
WORKFLOW_MAX_RETRIES=3                          # Default retry count

# Schedule Service
SCHEDULE_GRACE_PERIOD_MINUTES=15                # Grace period for missed executions
LOG_LEVEL=INFO                                  # Logging level
```

### Initialization in App

```python
# In app.py or startup code
from services.schedule_service import ScheduleService

async def startup():
    # Initialize service
    schedule_service = ScheduleService(
        dal=dal,
        workflow_engine=workflow_engine,
        grace_period_minutes=int(os.getenv("SCHEDULE_GRACE_PERIOD_MINUTES", "15"))
    )

    # Start scheduler
    await schedule_service.start_scheduler()

    # Store in app context for use in routes
    app.schedule_service = schedule_service

async def shutdown():
    # Graceful shutdown
    await app.schedule_service.stop_scheduler()
```

## Testing

### Unit Test Example

```python
import pytest
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_cron_schedule_creation(schedule_service, dal):
    """Test creating a cron schedule"""
    config = {
        "schedule_type": "cron",
        "cron_expression": "0 12 * * *",
        "timezone": "UTC"
    }

    result = await schedule_service.add_schedule(
        workflow_id="test-workflow",
        schedule_config=config,
        user_id=1,
        community_id=1
    )

    assert result["schedule_id"] is not None
    assert result["schedule_type"] == "cron"
    assert result["is_active"] is True
    assert result["execution_count"] == 0

@pytest.mark.asyncio
async def test_interval_schedule_execution(schedule_service, workflow_engine):
    """Test interval schedule triggering"""
    config = {
        "schedule_type": "interval",
        "interval_seconds": 1,
        "max_executions": 1
    }

    schedule = await schedule_service.add_schedule(
        workflow_id="test-workflow",
        schedule_config=config,
        user_id=1,
        community_id=1
    )

    # Manually trigger due schedules check
    triggered = await schedule_service.check_due_schedules()

    assert len(triggered) > 0
    assert triggered[0]["schedule_id"] == schedule["schedule_id"]
```

## API Integration

### REST Endpoints (Example)

```python
@app.route("/api/v1/schedules", methods=["POST"])
@auth_required
async def create_schedule(request):
    """Create new schedule"""
    data = await request.json
    result = await app.schedule_service.add_schedule(
        workflow_id=data["workflow_id"],
        schedule_config=data["schedule_config"],
        user_id=request.user_id,
        community_id=request.community_id,
        context_data=data.get("context_data")
    )
    return json_response(result, status=201)

@app.route("/api/v1/schedules/<schedule_id>", methods=["PUT"])
@auth_required
async def update_schedule(request, schedule_id):
    """Update schedule"""
    data = await request.json
    result = await app.schedule_service.update_schedule(
        schedule_id=schedule_id,
        schedule_config=data["schedule_config"],
        user_id=request.user_id
    )
    return json_response(result)

@app.route("/api/v1/schedules/<schedule_id>", methods=["DELETE"])
@auth_required
async def delete_schedule(request, schedule_id):
    """Remove schedule"""
    await app.schedule_service.remove_schedule(
        schedule_id=schedule_id,
        user_id=request.user_id
    )
    return json_response({"status": "removed"})
```

## Troubleshooting

### Schedule Not Executing

1. **Check if scheduler is running:**
   ```python
   print(schedule_service._is_running)  # Should be True
   ```

2. **Verify schedule is active:**
   ```sql
   SELECT is_active, next_execution_at FROM workflow_schedules
   WHERE schedule_id = 'xxx';
   ```

3. **Check workflow execution limits:**
   ```sql
   SELECT execution_count, max_executions FROM workflow_schedules
   WHERE schedule_id = 'xxx';
   ```

4. **Verify workflow exists and is valid:**
   ```sql
   SELECT * FROM workflows WHERE workflow_id = 'xxx';
   ```

### Scheduler Startup Issues

1. **Check APScheduler initialization:** Look for startup errors in logs
2. **Verify database connectivity:** Ensure AsyncDAL can connect
3. **Check for permission issues:** Ensure schedule service can access tables
4. **Review environment variables:** Verify configuration is correct

### High Memory Usage

1. **Check active schedule count:** `len(schedule_service._active_schedules)`
2. **Monitor APScheduler job count:** Check with `scheduler.get_jobs()`
3. **Implement max_executions:** Prevent runaway schedules
4. **Use grace period:** Prevent backlog of missed executions

## Future Enhancements

- [ ] Timezone-aware next execution calculation
- [ ] Schedule pause/resume functionality
- [ ] Execution history retention policy
- [ ] Workflow chaining and dependencies
- [ ] Schedule templates and inheritance
- [ ] Real-time schedule status dashboard
- [ ] Distributed scheduling with Redis
- [ ] Schedule conflict detection
- [ ] Automatic retry with exponential backoff
- [ ] Execution performance metrics and analytics

## See Also

- [Workflow Engine Documentation](./WORKFLOW_SERVICE_INTEGRATION.md)
- [API Reference](../../docs/api-reference.md)
- [Database Schema](../../docs/database-schema.md)
- [Environment Variables](../../docs/environment-variables.md)
