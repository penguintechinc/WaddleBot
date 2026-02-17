# Analytics Core Module — Testing Guide

**Version:** 1.0.0
**Last Updated:** 2026-02-16

---

## Table of Contents

1. [Test Structure](#test-structure)
2. [Event Fixtures](#event-fixtures)
3. [Time-Series Test Data](#time-series-test-data)
4. [Running Tests](#running-tests)
5. [Unit Tests](#unit-tests)
6. [Integration Tests](#integration-tests)
7. [Performance Tests](#performance-tests)
8. [Test Coverage](#test-coverage)
9. [Debugging Tests](#debugging-tests)

---

## Test Structure

```
core/analytics_core_module/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures
│   ├── test_analytics_service.py
│   ├── test_metrics_service.py
│   ├── test_bot_score_service.py
│   ├── test_api_endpoints.py
│   ├── integration/
│   │   ├── test_event_ingestion.py
│   │   ├── test_aggregation.py
│   │   └── test_bot_detection.py
│   ├── fixtures/
│   │   ├── events.py
│   │   ├── timeseries.py
│   │   └── config.py
│   └── performance/
│       ├── test_query_performance.py
│       └── test_aggregation_performance.py
```

---

## Event Fixtures

### Basic Event Fixture

```python
# tests/fixtures/events.py

SIMPLE_MESSAGE_EVENT = {
    "community_id": 123,
    "event_type": "message",
    "platform": "discord",
    "platform_user_id": "user123",
    "timestamp": "2026-02-16T10:30:00Z",
    "metadata": {
        "channel_id": "chan123",
        "message_length": 150
    }
}

VIEWER_JOIN_EVENT = {
    "community_id": 123,
    "event_type": "viewer_join",
    "platform": "twitch",
    "platform_user_id": "twitch456",
    "timestamp": "2026-02-16T10:35:00Z",
    "metadata": {
        "session_id": "sess789"
    }
}

VIEWER_LEAVE_EVENT = {
    "community_id": 123,
    "event_type": "viewer_leave",
    "platform": "twitch",
    "platform_user_id": "twitch456",
    "timestamp": "2026-02-16T11:00:00Z",
    "metadata": {
        "session_id": "sess789",
        "duration_seconds": 1500
    }
}
```

### Batch Event Fixture (100 events)

```python
def create_batch_events(community_id=123, count=100, start_time=None):
    """Create batch of test events for a community."""
    if start_time is None:
        start_time = datetime.utcnow()

    events = []
    for i in range(count):
        timestamp = start_time + timedelta(minutes=i)
        events.append({
            "community_id": community_id,
            "event_type": "message",
            "platform": "discord",
            "platform_user_id": f"user_{i % 10}",  # 10 unique users
            "timestamp": timestamp.isoformat() + "Z",
            "metadata": {
                "channel_id": f"chan_{i % 5}",  # 5 channels
                "message_length": 50 + (i % 100)
            }
        })
    return events
```

### Platform-Specific Events

```python
# Discord event
DISCORD_MESSAGE = {
    "community_id": 123,
    "event_type": "message",
    "platform": "discord",
    "platform_user_id": "discord:123456789",
    "timestamp": "2026-02-16T10:30:00Z",
    "metadata": {
        "guild_id": "guild123",
        "channel_id": "chan123",
        "message_id": "msg123",
        "author_name": "alice"
    }
}

# Twitch event
TWITCH_VIEWER = {
    "community_id": 123,
    "event_type": "viewer_join",
    "platform": "twitch",
    "platform_user_id": "twitch:alice",
    "timestamp": "2026-02-16T10:30:00Z",
    "metadata": {
        "channel_id": "channelalice",
        "user_login": "alice"
    }
}

# Slack event
SLACK_MESSAGE = {
    "community_id": 123,
    "event_type": "message",
    "platform": "slack",
    "platform_user_id": "slack:U123456",
    "timestamp": "2026-02-16T10:30:00Z",
    "metadata": {
        "workspace_id": "T123456",
        "channel_id": "C123456",
        "user_name": "alice"
    }
}

# YouTube event
YOUTUBE_COMMENT = {
    "community_id": 123,
    "event_type": "message",
    "platform": "youtube",
    "platform_user_id": "youtube:user123",
    "timestamp": "2026-02-16T10:30:00Z",
    "metadata": {
        "video_id": "abc123def456",
        "comment_id": "comment123",
        "channel_id": "channel123"
    }
}
```

### Bot Detection Test Events

```python
def create_rapid_posting_events(community_id=123, user_id="bot_user", count=10):
    """Create events that trigger rapid posting detection."""
    events = []
    base_time = datetime.utcnow()

    for i in range(count):
        events.append({
            "community_id": community_id,
            "event_type": "message",
            "platform": "discord",
            "platform_user_id": user_id,
            "timestamp": (base_time + timedelta(seconds=i)).isoformat() + "Z",
            "metadata": {
                "message_text": f"message {i}",
                "message_length": 50
            }
        })
    return events


def create_duplicate_message_events(community_id=123, user_id="bot_user"):
    """Create events that trigger duplicate message detection."""
    events = []
    base_time = datetime.utcnow()
    message_text = "This is a repeated message"

    for i in range(4):  # 4 identical messages
        events.append({
            "community_id": community_id,
            "event_type": "message",
            "platform": "discord",
            "platform_user_id": user_id,
            "timestamp": (base_time + timedelta(seconds=i*30)).isoformat() + "Z",
            "metadata": {
                "message_text": message_text,
                "message_length": len(message_text)
            }
        })
    return events
```

---

## Time-Series Test Data

### Day-Level Aggregation Fixture

```python
def create_daily_metrics(community_id=123, days=30):
    """Create 30 days of daily metric data."""
    metrics = []
    base_date = datetime.utcnow() - timedelta(days=30)

    for day in range(days):
        timestamp = base_date + timedelta(days=day)
        metrics.append({
            "community_id": community_id,
            "metric_type": "messages",
            "metric_subtype": None,
            "timestamp_bucket": timestamp,
            "bucket_size": "1d",
            "value": 2000 + (day * 50),  # Incrementing values
            "metadata": {
                "peak_hour": "19:00",
                "unique_users": 100 + day
            }
        })
    return metrics
```

### Hourly Metrics Fixture

```python
def create_hourly_metrics(community_id=123, hours=24):
    """Create 24 hours of hourly metric data."""
    metrics = []
    base_time = datetime.utcnow() - timedelta(hours=24)

    for hour in range(hours):
        timestamp = base_time + timedelta(hours=hour)
        metrics.append({
            "community_id": community_id,
            "metric_type": "messages",
            "timestamp_bucket": timestamp,
            "bucket_size": "1h",
            "value": 100 + (hour * 10),
            "metadata": {
                "avg_message_length": 50
            }
        })
    return metrics
```

### Multi-Metric Fixture

```python
def create_multi_metric_data(community_id=123, days=7):
    """Create metrics for multiple types across a week."""
    metrics = []
    base_date = datetime.utcnow() - timedelta(days=7)
    metric_types = ["messages", "viewers", "engagement", "growth"]

    for day in range(days):
        timestamp = base_date + timedelta(days=day)
        for metric_type in metric_types:
            # Different base values per metric type
            base_value = {
                "messages": 2000,
                "viewers": 500,
                "engagement": 75,
                "growth": 2.5
            }[metric_type]

            metrics.append({
                "community_id": community_id,
                "metric_type": metric_type,
                "timestamp_bucket": timestamp,
                "bucket_size": "1d",
                "value": base_value + (day * 10),
                "metadata": {}
            })
    return metrics
```

---

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-mock

# Set up test database
export DATABASE_URL="postgresql://test:test@localhost:5432/waddlebot_test"
createdb waddlebot_test
```

### Run All Tests

```bash
# Run all tests with coverage
pytest core/analytics_core_module/tests/ -v --cov=core/analytics_core_module

# Run specific test file
pytest core/analytics_core_module/tests/test_analytics_service.py -v

# Run specific test
pytest core/analytics_core_module/tests/test_analytics_service.py::test_get_basic_stats -v
```

### Test Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only performance tests
pytest -m performance

# Skip slow tests
pytest -m "not slow"
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=core/analytics_core_module --cov-report=html

# View report
open htmlcov/index.html

# Minimum coverage threshold (80%)
pytest --cov=core/analytics_core_module --cov-fail-under=80
```

---

## Unit Tests

### Analytics Service Tests

```python
# tests/test_analytics_service.py

import pytest
from analytics_service import AnalyticsService

@pytest.mark.asyncio
async def test_get_basic_stats(mock_dal, logger):
    """Test basic stats calculation."""
    service = AnalyticsService(mock_dal, logger)

    # Mock database responses
    mock_dal.executesql.side_effect = [
        [(150,)],           # total_chatters
        [(2450.5 * 3600,)], # total_stream_time
        [("alice", 1250), ("bob", 890), ("charlie", 750)],  # top users
        [(85,)],            # active_7d
        [(120,)]            # active_30d
    ]

    # Call service
    stats = await service.get_basic_stats(123)

    # Assertions
    assert stats['total_chatters'] == 150
    assert stats['total_stream_time_hours'] == 2450.5
    assert stats['active_chatters_7d'] == 85
    assert stats['active_chatters_30d'] == 120
    assert len(stats['messages_per_user']) == 3


@pytest.mark.asyncio
async def test_get_config_default(mock_dal, logger):
    """Test config creation for new community."""
    service = AnalyticsService(mock_dal, logger)

    # Mock: config doesn't exist
    mock_dal.executesql.side_effect = [None, None]

    config = await service.get_config(999)

    # Should return defaults
    assert config['community_id'] == 999
    assert config['is_premium'] == False
    assert config['basic_stats_enabled'] == True
    assert config['polling_interval_seconds'] == 30


@pytest.mark.asyncio
async def test_update_config(mock_dal, logger):
    """Test configuration update."""
    service = AnalyticsService(mock_dal, logger)

    await service.update_config(123, {
        'is_premium': True,
        'polling_interval_seconds': 15
    })

    # Verify UPDATE was called with correct params
    mock_dal.executesql.assert_called()
    mock_dal.commit.assert_called()
```

### Metrics Service Tests

```python
@pytest.mark.asyncio
async def test_get_timeseries_default_range(mock_dal, logger):
    """Test time-series query with defaults."""
    service = MetricsService(mock_dal, logger)

    # Mock database response
    mock_dal.executesql.return_value = [
        (datetime(2026, 2, 16), 2500.0, {}),
        (datetime(2026, 2, 17), 2600.0, {})
    ]

    result = await service.get_timeseries(
        community_id=123,
        metric_type='messages',
        bucket_size='1d'
    )

    # Verify query parameters
    assert result['community_id'] == 123
    assert result['metric_type'] == 'messages'
    assert result['bucket_size'] == '1d'
    assert result['count'] == 2
    assert len(result['data']) == 2


@pytest.mark.asyncio
async def test_get_timeseries_custom_range(mock_dal, logger):
    """Test time-series with custom date range."""
    service = MetricsService(mock_dal, logger)

    mock_dal.executesql.return_value = []

    await service.get_timeseries(
        community_id=123,
        metric_type='engagement',
        bucket_size='1w',
        start_date='2026-01-01',
        end_date='2026-02-15'
    )

    # Verify date parsing
    call_args = mock_dal.executesql.call_args
    assert call_args[0][1][3]  # start_date parameter
    assert call_args[0][1][4]  # end_date parameter
```

### Bot Score Service Tests

```python
@pytest.mark.asyncio
async def test_calculate_bot_score(mock_dal, logger):
    """Test bot score calculation."""
    service = BotScoreService(mock_dal, logger)

    # Mock component score queries
    mock_dal.execute.side_effect = [
        [{"member_count": 250}],           # community size
        [{"bad_actor_count": 5}],          # bad actors
        [{"total_users": 100}],            # total users
        [{"health_score": 85, "engagement_level": 70}],  # reputation
        [{"total_events": 1000, "violations": 50}],      # security
        [{"rapid_posters": 2, "duplicate_users": 1}],    # AI behavioral
        [{"active_users": 100}]            # active users
    ]

    score = await service.calculate_score(123)

    # Verify score components
    assert 0 <= score['overall_score'] <= 100
    assert score['grade'] in ['A', 'B', 'C', 'D', 'F']
    assert score['size_category'] == 'medium'
    assert 'bad_actor_score' in score['component_scores']
```

---

## Integration Tests

### Event Ingestion Integration Test

```python
# tests/integration/test_event_ingestion.py

@pytest.mark.asyncio
@pytest.mark.integration
async def test_event_ingestion_flow(app, test_client, mock_dal):
    """Test full event ingestion workflow."""
    # 1. Send events via API
    response = await test_client.post(
        '/api/v1/internal/events',
        json={
            "community_id": 123,
            "events": create_batch_events(count=10)
        },
        headers={'X-Service-API-Key': 'test-key'}
    )

    assert response.status_code == 200
    data = await response.get_json()
    assert data['data']['processed'] == 10

    # 2. Verify events were stored
    assert mock_dal.executesql.called

    # 3. Query stats to verify data
    stats = await app.analytics_service.get_basic_stats(123)
    assert stats['total_chatters'] > 0
```

### Aggregation Integration Test

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_aggregation_flow(app, mock_dal):
    """Test aggregation pipeline."""
    # 1. Insert test events
    events = create_batch_events(community_id=123, count=100)

    # 2. Trigger aggregation
    result = await app.analytics_service.run_aggregation(community_id=123)
    assert result['status'] == 'queued'

    # 3. Verify metrics were created
    metrics = await app.metrics_service.get_timeseries(
        community_id=123,
        metric_type='messages'
    )
    assert metrics['count'] > 0
```

### Bot Detection Integration Test

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_bot_detection_flow(app, mock_dal):
    """Test bot detection end-to-end."""
    # 1. Insert rapid posting events
    events = create_rapid_posting_events(count=10)

    # 2. Request bot score
    score = await app.bot_score_service.calculate_score(123)

    # 3. Verify suspicious activity detected
    assert score['overall_score'] < 100
    assert score['component_scores']['ai_behavioral_score'] < 100

    # 4. Query suspected bots
    bots = await app.bot_score_service.get_suspected_bots(123)
    assert len(bots) > 0
```

---

## Performance Tests

### Query Performance Test

```python
# tests/performance/test_query_performance.py

import time
import pytest

@pytest.mark.performance
@pytest.mark.slow
async def test_query_performance_large_dataset(mock_dal, logger):
    """Test query performance with large dataset."""
    service = MetricsService(mock_dal, logger)

    # Mock large dataset (1 year of daily metrics)
    large_dataset = create_daily_metrics(days=365)

    start_time = time.time()
    result = await service.get_timeseries(
        community_id=123,
        metric_type='messages',
        bucket_size='1d'
    )
    elapsed = time.time() - start_time

    # Query should complete in < 500ms
    assert elapsed < 0.5
    assert result['count'] == 365


@pytest.mark.performance
async def test_aggregation_performance(mock_dal, logger):
    """Test aggregation performance."""
    service = AnalyticsService(mock_dal, logger)

    # Create 10,000 test events
    events = create_batch_events(count=10000)

    start_time = time.time()
    result = await service.process_events(events)
    elapsed = time.time() - start_time

    # Should process 10k events in < 5 seconds
    assert elapsed < 5.0
    assert result['processed'] == 10000
```

---

## Test Coverage

### Current Coverage

```bash
$ pytest --cov=core/analytics_core_module --cov-report=term-missing

Name                                          Stmts  Miss Cover
──────────────────────────────────────────────────────────────
analytics_core_module/__init__.py                 2    0  100%
analytics_core_module/app.py                    120    5   96%
analytics_core_module/config.py                  45    3   93%
analytics_core_module/services/analytics_service.py   75    2   97%
analytics_core_module/services/metrics_service.py    40    1   98%
analytics_core_module/services/bot_score_service.py 190   15   92%
──────────────────────────────────────────────────────────────
TOTAL                                           472   26   94%
```

### Coverage Goals

- Overall: 80%+ (current 94%)
- Critical paths: 95%+
- Bot detection logic: 90%+
- API endpoints: 85%+

---

## Debugging Tests

### Enable Debug Logging

```bash
# Run with debug output
pytest --log-cli-level=DEBUG core/analytics_core_module/tests/test_analytics_service.py

# Run with print statements
pytest -s core/analytics_core_module/tests/test_analytics_service.py
```

### Use pytest breakpoint

```python
@pytest.mark.asyncio
async def test_something(mock_dal):
    # Break here for debugging
    breakpoint()

    result = await some_function()
    assert result
```

### Inspect Mock Calls

```python
def test_mock_inspection(mock_dal):
    # Inspect how mock was called
    print(mock_dal.executesql.call_count)
    print(mock_dal.executesql.call_args_list)

    # Assert specific calls
    mock_dal.executesql.assert_called_once_with(
        "SELECT * FROM ...",
        [123]
    )
```

---

**Last Updated:** 2026-02-16
**Maintained By:** Penguin Tech Inc
