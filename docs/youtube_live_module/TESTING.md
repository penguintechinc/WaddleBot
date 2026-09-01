# YouTube Live Module Testing Guide

Comprehensive testing procedures for unit, integration, and end-to-end testing.

## Test Framework Overview

- **Unit Tests**: Test individual services and utilities in isolation
- **Integration Tests**: Test service interactions and database operations
- **End-to-End Tests**: Test complete workflows with real/mock API
- **Smoke Tests**: Quick sanity checks (< 2 minutes)
- **Load Tests**: Performance testing under concurrent load

## Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock httpx

# Install development dependencies
pip install black flake8 mypy

# Create test database
psql -U postgres -c "CREATE DATABASE waddlebot_test;"

# Setup test environment
cp .env.example .env.test
echo "DATABASE_URL=postgresql://localhost/waddlebot_test" >> .env.test
echo "MOCK_API_RESPONSES=true" >> .env.test
```

## Running Tests

### All Tests

```bash
# Run all test categories
make test

# Or directly with pytest
pytest tests/ -v --cov=trigger/receiver/youtube_live_module

# With coverage report
pytest tests/ --cov=trigger/receiver/youtube_live_module \
  --cov-report=html --cov-report=term
```

### Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# E2E tests only
pytest tests/e2e/ -v

# Smoke tests only
pytest tests/smoke/ -v -m smoke
```

### Specific Test File

```bash
# Single file
pytest tests/unit/services/test_youtube_client.py -v

# Specific test function
pytest tests/unit/services/test_youtube_client.py::test_get_channel_info -v
```

### With Coverage Threshold

```bash
# Fail if coverage below 80%
pytest --cov=trigger/receiver/youtube_live_module \
  --cov-fail-under=80
```

## Unit Tests

Test individual services in isolation with mocked dependencies.

### Test Structure

```python
# tests/unit/services/test_youtube_client.py

import pytest
from unittest.mock import AsyncMock, patch
from services.youtube_client import YouTubeClient

class TestYouTubeClient:
    @pytest.fixture
    async def client(self):
        """Fixture: Create YouTubeClient instance"""
        return YouTubeClient(api_key="test-key")

    @pytest.mark.asyncio
    async def test_get_channel_info(self, client):
        """Test: Fetch channel info successfully"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                'items': [{
                    'id': 'UCxxxxxxxxxx',
                    'snippet': {'title': 'Test Channel'}
                }]
            }
            mock_get.return_value = mock_response

            result = await client.get_channel_info('UCxxxxxxxxxx')

            assert result['id'] == 'UCxxxxxxxxxx'
            assert result['snippet']['title'] == 'Test Channel'

    @pytest.mark.asyncio
    async def test_get_channel_info_invalid_key(self, client):
        """Test: Handle invalid API key"""
        client.api_key = "invalid-key"

        with pytest.raises(Exception) as exc_info:
            await client.get_channel_info('UCxxxxxxxxxx')

        assert "unauthorized" in str(exc_info.value).lower()
```

### Running Unit Tests

```bash
# All unit tests
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=trigger/receiver/youtube_live_module.services

# Run specific test class
pytest tests/unit/services/test_youtube_client.py::TestYouTubeClient -v

# Run specific test
pytest tests/unit/services/test_youtube_client.py::TestYouTubeClient::test_get_channel_info -v
```

### Mock API Responses

Use mock responses for testing without YouTube API:

```python
# tests/fixtures/mock_api_responses.py

MOCK_CHANNEL_INFO = {
    'items': [{
        'id': 'UCxxxxxxxxxx',
        'snippet': {
            'title': 'Test Channel',
            'description': 'Test Description',
            'customUrl': 'test-channel',
            'publishedAt': '2020-01-01T00:00:00Z',
            'thumbnails': {
                'default': {'url': 'https://example.com/image.jpg'}
            }
        },
        'statistics': {
            'viewCount': '1000000',
            'subscriberCount': '10000',
            'videoCount': '100'
        }
    }]
}

MOCK_LIVE_BROADCASTS = {
    'items': [{
        'id': 'YxxxxxxxxxB',
        'snippet': {
            'title': 'Live Stream Title',
            'description': 'Stream description',
            'scheduledStartTime': '2026-02-24T10:00:00Z',
            'actualStartTime': '2026-02-24T10:00:00Z'
        },
        'status': {'lifeCycleStatus': 'live'},
        'contentDetails': {'boundStreamId': 'Bgxxxxxxxxxx'}
    }]
}

MOCK_LIVE_CHAT_MESSAGES = {
    'items': [
        {
            'id': 'message-1',
            'snippet': {
                'type': 'textMessageEvent',
                'authorChannelId': {'value': 'UC-author-1'},
                'authorDisplayName': 'User1',
                'displayMessage': 'Great stream!',
                'publishedAt': '2026-02-24T10:00:00Z'
            }
        },
        {
            'id': 'message-2',
            'snippet': {
                'type': 'superChatEvent',
                'authorChannelId': {'value': 'UC-author-2'},
                'authorDisplayName': 'User2',
                'displayMessage': 'Amazing content!',
                'superChatDetails': {
                    'amountMicros': '5000000',
                    'currency': 'USD',
                    'userComment': 'Keep it up!'
                },
                'publishedAt': '2026-02-24T10:01:00Z'
            }
        }
    ],
    'nextPageToken': 'NEXT_PAGE_TOKEN_HERE'
}
```

## Integration Tests

Test service interactions and database operations.

### Test Structure

```python
# tests/integration/test_chat_poller.py

import pytest
from unittest.mock import AsyncMock, patch
from services.chat_poller import ChatPoller
from services.youtube_client import YouTubeClient

class TestChatPoller:
    @pytest.fixture
    async def poller(self, db):
        """Fixture: Create ChatPoller with test database"""
        client = YouTubeClient(api_key="test-key")
        return ChatPoller(client=client, db=db)

    @pytest.fixture
    async def db(self):
        """Fixture: Create in-memory test database"""
        # Setup test database
        from config import get_db
        db = get_db(database_url="sqlite:///:memory:")
        yield db
        # Cleanup

    @pytest.mark.asyncio
    async def test_register_channel(self, poller, db):
        """Test: Register channel for polling"""
        result = await poller.register_channel(
            channel_id="UCxxxxxxxxxx",
            channel_name="Test Channel"
        )

        assert result['status'] == 'success'
        assert result['channel_id'] == 'UCxxxxxxxxxx'

        # Verify database
        channels = db.select(lambda c: c.channel_id == "UCxxxxxxxxxx")
        assert len(channels) == 1

    @pytest.mark.asyncio
    async def test_poll_chat_with_messages(self, poller):
        """Test: Poll chat and process messages"""
        with patch.object(poller.client, 'get_live_chat_messages') as mock_poll:
            mock_poll.return_value = {
                'items': [
                    {
                        'id': 'msg-1',
                        'snippet': {
                            'type': 'textMessageEvent',
                            'displayMessage': 'Test message',
                            'authorDisplayName': 'User1'
                        }
                    }
                ]
            }

            messages = await poller._poll_channel("UCxxxxxxxxxx")

            assert len(messages) == 1
            assert messages[0]['text'] == 'Test message'
            assert messages[0]['author'] == 'User1'

    @pytest.mark.asyncio
    async def test_error_counting(self, poller, db):
        """Test: Track and handle polling errors"""
        with patch.object(poller.client, 'get_live_broadcasts') as mock_broadcasts:
            # Simulate 10 consecutive errors
            mock_broadcasts.side_effect = Exception("API Error")

            for i in range(10):
                try:
                    await poller._poll_channel("UCxxxxxxxxxx")
                except:
                    pass

            # Check error count
            channels = db.select(lambda c: c.channel_id == "UCxxxxxxxxxx")
            assert channels[0].error_count >= 10

            # Channel should be disabled after 10 errors
            # (depends on implementation)
```

### Running Integration Tests

```bash
# All integration tests
pytest tests/integration/ -v

# With database
pytest tests/integration/ -v --db postgresql://localhost/waddlebot_test

# With coverage
pytest tests/integration/ --cov=trigger/receiver/youtube_live_module.services
```

## End-to-End Tests

Test complete workflows with real or mocked YouTube API.

### E2E Test Structure

```python
# tests/e2e/test_message_flow.py

import pytest
import httpx
from unittest.mock import patch

class TestMessageFlow:
    @pytest.fixture
    async def app(self):
        """Fixture: Start application server"""
        from app import create_app
        app = create_app()
        # Start server
        yield app
        # Stop server

    @pytest.mark.asyncio
    async def test_register_and_poll_channel(self):
        """E2E: Register channel and verify polling starts"""
        async with httpx.AsyncClient() as client:
            # Register channel
            response = await client.post(
                "http://localhost:8006/api/v1/channels/register",
                json={
                    "channel_id": "UCxxxxxxxxxx",
                    "channel_name": "Test Channel"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'success'

            # Wait for polling to start
            await asyncio.sleep(2)

            # Verify channel is registered
            response = await client.get("http://localhost:8006/api/v1/channels")
            channels = response.json()['channels']
            assert len(channels) == 1
            assert channels[0]['channel_id'] == 'UCxxxxxxxxxx'

    @pytest.mark.asyncio
    async def test_webhook_stream_event(self):
        """E2E: Receive and process webhook event"""
        async with httpx.AsyncClient() as client:
            # Send webhook notification
            payload = """<?xml version="1.0" encoding="UTF-8"?>
            <feed xmlns="http://www.w3.org/2005/Atom">
              <entry>
                <id>yt:video:dQw4w9WgXcQ</id>
                <yt:videoId>dQw4w9WgXcQ</yt:videoId>
                <title>Video Title</title>
                <link href="http://www.youtube.com/watch?v=dQw4w9WgXcQ"/>
                <published>2026-02-24T10:00:00Z</published>
                <updated>2026-02-24T10:35:15Z</updated>
              </entry>
            </feed>"""

            response = await client.post(
                "http://localhost:8006/api/v1/webhook",
                content=payload,
                headers={"Content-Type": "application/atom+xml"}
            )

            assert response.status_code == 200
```

### Running E2E Tests

```bash
# Start module first
python main.py &

# Run E2E tests
pytest tests/e2e/ -v

# With timeout (tests may be slow)
pytest tests/e2e/ -v --timeout=60

# Kill module after tests
pkill -f "python main.py"
```

## Smoke Tests

Quick verification tests (< 2 minutes total).

### Smoke Test Checklist

```python
# tests/smoke/test_smoke.py

import pytest

class TestSmoke:
    @pytest.mark.smoke
    def test_module_starts(self):
        """Smoke: Module starts without errors"""
        # Verify no startup errors
        import subprocess
        result = subprocess.run(
            ["python", "main.py", "--version"],
            capture_output=True,
            timeout=5
        )
        assert result.returncode == 0

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Smoke: /health endpoint responds"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8006/health")
            assert response.status_code == 200
            assert response.json()['status'] == 'healthy'

    @pytest.mark.smoke
    def test_api_key_configured(self):
        """Smoke: YOUTUBE_API_KEY is set"""
        import os
        assert os.getenv('YOUTUBE_API_KEY'), "YOUTUBE_API_KEY not configured"

    @pytest.mark.smoke
    def test_database_accessible(self):
        """Smoke: Database connection works"""
        import os
        from config import get_db
        db = get_db(os.getenv('DATABASE_URL'))
        assert db is not None

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_api_endpoints_respond(self):
        """Smoke: Core endpoints respond with 200"""
        import httpx
        endpoints = [
            "/health",
            "/api/v1/channels",
            "/api/v1/status",
            "/metrics"
        ]

        async with httpx.AsyncClient() as client:
            for endpoint in endpoints:
                response = await client.get(f"http://localhost:8006{endpoint}")
                assert response.status_code in [200, 404]  # 404 is OK if not needed
```

### Running Smoke Tests

```bash
# All smoke tests (fast)
pytest tests/smoke/ -v -m smoke

# Should complete in < 2 minutes
time pytest tests/smoke/ -m smoke
```

## Load Testing

Test performance under concurrent load.

### Load Test Example

```python
# tests/load/test_concurrent_channels.py

import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor

class TestLoadConcurrentChannels:
    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_concurrent_polling(self):
        """Load: Poll 100 channels concurrently"""
        from services.chat_poller import ChatPoller

        poller = ChatPoller()

        # Register 100 channels
        for i in range(100):
            await poller.register_channel(
                channel_id=f"UC{i:0>27}",
                channel_name=f"Channel {i}"
            )

        # Measure polling performance
        import time
        start = time.time()

        # Simulate one polling cycle
        await poller._poll_all_channels()

        elapsed = time.time() - start

        # Should complete in reasonable time
        assert elapsed < 30, f"Polling took {elapsed}s, expected < 30s"

    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_message_throughput(self):
        """Load: Process 1000 messages"""
        from services.chat_poller import ChatPoller

        poller = ChatPoller()

        # Create 1000 mock messages
        messages = [
            {
                'id': f'msg-{i}',
                'snippet': {
                    'type': 'textMessageEvent',
                    'displayMessage': f'Message {i}',
                    'authorDisplayName': f'User{i % 100}'
                }
            }
            for i in range(1000)
        ]

        # Measure processing time
        import time
        start = time.time()

        for msg in messages:
            await poller._process_message(msg)

        elapsed = time.time() - start
        throughput = len(messages) / elapsed

        # Should process > 1000 msgs/second
        assert throughput > 1000, f"Throughput: {throughput} msgs/sec"
```

### Running Load Tests

```bash
# Load tests (may take longer)
pytest tests/load/ -v -m load

# With timeout
pytest tests/load/ -v -m load --timeout=300

# Specific load test
pytest tests/load/test_concurrent_channels.py::TestLoadConcurrentChannels::test_concurrent_polling -v
```

## Test Coverage

### Generate Coverage Report

```bash
# HTML report
pytest --cov=trigger/receiver/youtube_live_module \
  --cov-report=html

# Open report
open htmlcov/index.html

# Terminal report
pytest --cov=trigger/receiver/youtube_live_module \
  --cov-report=term-missing
```

### Coverage Targets

- Overall: 80%+
- Services: 90%+
- Routes: 85%+
- Utils: 75%+

### Coverage by Module

```bash
# Specific module
pytest --cov=trigger/receiver/youtube_live_module.services \
  --cov-report=term

# Exclude migrations/fixtures
pytest --cov=trigger/receiver/youtube_live_module \
  --cov-report=term --cov-report=html \
  --ignore=tests/fixtures/
```

## Testing Best Practices

### 1. Use Fixtures for Setup/Teardown

```python
@pytest.fixture
async def client():
    """Fixture: YouTubeClient with test config"""
    return YouTubeClient(api_key="test-key")

@pytest.fixture
async def db():
    """Fixture: In-memory test database"""
    db = create_test_db()
    yield db
    db.teardown()
```

### 2. Mock External Dependencies

```python
from unittest.mock import patch, AsyncMock

with patch('httpx.AsyncClient.get') as mock_get:
    mock_get.return_value = AsyncMock(
        json=AsyncMock(return_value={'result': 'success'})
    )
    # Test code
```

### 3. Use Parameterization for Multiple Cases

```python
@pytest.mark.parametrize("input,expected", [
    ("chat", "textMessageEvent"),
    ("super_chat", "superChatEvent"),
    ("super_sticker", "superStickerEvent"),
])
def test_message_type_detection(input, expected):
    assert detect_type(input) == expected
```

### 4. Async Testing

```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None
```

### 5. Test Error Conditions

```python
def test_invalid_channel_id():
    with pytest.raises(ValueError) as exc_info:
        get_channel_info("invalid")
    assert "invalid" in str(exc_info.value)
```

## Continuous Integration

### Pre-commit Testing

```bash
# Run before each commit
#!/bin/bash
# .git/hooks/pre-commit

set -e

# Lint
flake8 trigger/receiver/youtube_live_module tests/

# Format check
black --check trigger/receiver/youtube_live_module tests/

# Type check
mypy trigger/receiver/youtube_live_module

# Smoke tests
pytest tests/smoke/ -v -m smoke --tb=short

echo "All checks passed!"
```

### CI/CD Pipeline (GitHub Actions)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Lint
        run: flake8 trigger/receiver/youtube_live_module

      - name: Unit tests
        run: pytest tests/unit/ -v

      - name: Integration tests
        run: pytest tests/integration/ -v

      - name: Coverage
        run: |
          pytest --cov=trigger/receiver/youtube_live_module \
            --cov-fail-under=80
```

## Test Data Management

### Mock Data Files

```
tests/
├── fixtures/
│   ├── mock_api_responses.py   # API mock responses
│   ├── mock_chat_messages.json # Sample chat messages
│   └── test_data.sql           # Test database seed
└── ...
```

### Seeding Test Data

```bash
# Load test database with seed data
psql $DATABASE_URL -f tests/fixtures/test_data.sql

# Clear and reseed
psql $DATABASE_URL -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
psql $DATABASE_URL -f tests/fixtures/test_data.sql
```

## Troubleshooting Tests

### Common Issues

```bash
# Test database locked
psql $DATABASE_URL -c "TERMINATE;" 2>/dev/null
psql -U postgres -c "DROP DATABASE waddlebot_test;"
psql -U postgres -c "CREATE DATABASE waddlebot_test;"

# Async timeout
pytest tests/ --timeout=60

# Import errors
python -m pytest tests/  # Use module invocation

# Mock not working
# Ensure patch path is absolute: 'module.submodule.Class.method'
```

## Documentation

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [httpx Testing](https://www.python-httpx.org/advanced/#testing)

## Support

For testing questions, see main WaddleBot documentation or contact development team.
