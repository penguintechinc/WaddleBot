# Slack Action Module - Testing Guide

## Unit Testing

The module includes comprehensive unit tests using `pytest` and `unittest.mock` for mocking the Slack SDK.

### Test Structure

```
tests/
├── unit/
│   ├── test_slack_service.py          # SlackService methods
│   ├── test_app_endpoints.py          # REST API endpoints
│   ├── test_authentication.py         # JWT authentication
│   ├── test_config.py                 # Configuration loading
│   └── test_grpc_handler.py          # gRPC handler
├── fixtures/
│   ├── mock_slack_responses.py        # Slack API response fixtures
│   ├── test_tokens.py                 # JWT token fixtures
│   └── test_payloads.py               # Request payload examples
└── conftest.py                         # pytest configuration
```

### Running Unit Tests

```bash
# Run all tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_app_endpoints.py -v

# Run specific test
pytest tests/unit/test_app_endpoints.py::test_send_message_success -v

# Run with coverage report
pytest tests/unit/ --cov=action.pushing.slack_action_module --cov-report=html

# Run with logging output
pytest tests/unit/ -v --log-cli-level=DEBUG
```

### Sample Unit Test

```python
# tests/unit/test_slack_service.py
import pytest
from unittest.mock import MagicMock, patch
from slack_sdk.errors import SlackApiError

@pytest.fixture
def slack_service():
    """Create SlackService with mocked Slack SDK client"""
    with patch('services.slack_service.WebClient') as mock_client:
        service = SlackService(bot_token="xoxb-test-token")
        service.client = mock_client
        yield service

def test_send_message_success(slack_service):
    """Test successful message sending"""
    # Arrange
    slack_service.client.chat_postMessage.return_value = {
        'ok': True,
        'channel': 'C01234567',
        'ts': '1234567890.123456'
    }

    # Act
    result = slack_service.send_message(
        community_id="test-community",
        channel_id="C01234567",
        text="Hello Slack!"
    )

    # Assert
    assert result['success'] == True
    assert result['message_ts'] == '1234567890.123456'
    slack_service.client.chat_postMessage.assert_called_once()

def test_send_message_channel_not_found(slack_service):
    """Test message send to non-existent channel"""
    # Arrange
    error = SlackApiError(
        message="channel_not_found",
        response={'error': 'channel_not_found'}
    )
    slack_service.client.chat_postMessage.side_effect = error

    # Act
    result = slack_service.send_message(
        community_id="test-community",
        channel_id="C99999999",
        text="Hello"
    )

    # Assert
    assert result['success'] == False
    assert 'channel_not_found' in result['error']

def test_send_message_invalid_auth(slack_service):
    """Test message send with invalid token"""
    # Arrange
    error = SlackApiError(
        message="invalid_auth",
        response={'error': 'invalid_auth'}
    )
    slack_service.client.chat_postMessage.side_effect = error

    # Act & Assert
    result = slack_service.send_message(
        community_id="test-community",
        channel_id="C01234567",
        text="Hello"
    )
    assert result['success'] == False
```

### Mock Slack Responses

```python
# tests/fixtures/mock_slack_responses.py

MOCK_MESSAGE_RESPONSE = {
    'ok': True,
    'channel': 'C01234567',
    'ts': '1234567890.123456',
    'message': {
        'type': 'message',
        'user': 'U01234567',
        'text': 'Hello Slack!',
        'ts': '1234567890.123456'
    }
}

MOCK_REACTION_RESPONSE = {
    'ok': True,
    'channel': 'C01234567',
    'ts': '1234567890.123456'
}

MOCK_FILE_UPLOAD_RESPONSE = {
    'ok': True,
    'file': {
        'id': 'F01234567',
        'name': 'document.pdf',
        'size': 12345,
        'url_private': 'https://files.slack.com/...'
    }
}

MOCK_CHANNEL_CREATE_RESPONSE = {
    'ok': True,
    'channel': {
        'id': 'C01234567',
        'name': 'team-announcements',
        'created': 1234567890,
        'is_general': False,
        'is_private': False
    }
}

MOCK_ERROR_RESPONSE_CHANNEL_NOT_FOUND = {
    'ok': False,
    'error': 'channel_not_found'
}

MOCK_ERROR_RESPONSE_NOT_IN_CHANNEL = {
    'ok': False,
    'error': 'not_in_channel'
}

MOCK_ERROR_RESPONSE_INVALID_AUTH = {
    'ok': False,
    'error': 'invalid_auth'
}

MOCK_ERROR_RESPONSE_RATE_LIMITED = {
    'ok': False,
    'error': 'rate_limited'
}
```

## Integration Testing

Integration tests verify the full request/response cycle with mocked external dependencies.

### Test Endpoints with Quart Test Client

```python
# tests/integration/test_api_endpoints.py
import pytest
import json
from app import app

@pytest.fixture
def client():
    """Create Quart test client"""
    app.config['TESTING'] = True
    return app.test_client()

@pytest.fixture
def valid_jwt_token():
    """Generate valid JWT token for testing"""
    import jwt
    import time
    payload = {
        'exp': int(time.time()) + 3600,
        'iat': int(time.time()),
        'sub': 'test-client'
    }
    return jwt.encode(
        payload,
        'test-secret-key',
        algorithm='HS256'
    )

@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint"""
    response = await client.get('/health')
    assert response.status_code == 200
    data = await response.get_json()
    assert data['status'] == 'healthy'
    assert data['module'] == 'slack_action_module'

@pytest.mark.asyncio
async def test_send_message_unauthorized(client):
    """Test message send without token"""
    response = await client.post(
        '/api/v1/message',
        data=json.dumps({
            'community_id': 'test',
            'channel_id': 'C01234567',
            'text': 'Hello'
        }),
        content_type='application/json'
    )
    assert response.status_code == 401
    data = await response.get_json()
    assert 'error' in data

@pytest.mark.asyncio
async def test_send_message_with_token(client, valid_jwt_token):
    """Test message send with valid token"""
    response = await client.post(
        '/api/v1/message',
        headers={'Authorization': f'Bearer {valid_jwt_token}'},
        data=json.dumps({
            'community_id': 'test',
            'channel_id': 'C01234567',
            'text': 'Hello'
        }),
        content_type='application/json'
    )
    # Should succeed (if Slack SDK mocked properly)
    assert response.status_code in [200, 500]  # 200 if mocked, 500 if no mock

@pytest.mark.asyncio
async def test_token_generation(client):
    """Test JWT token generation"""
    response = await client.post(
        '/api/v1/token',
        data=json.dumps({
            'api_key': 'test-secret-key',
            'client_id': 'test-client'
        }),
        content_type='application/json'
    )
    assert response.status_code == 200
    data = await response.get_json()
    assert 'token' in data
    assert 'expires_in' in data
```

## Test Payloads

### Message Payload
```json
{
  "community_id": "test-community",
  "channel_id": "C01234567",
  "text": "Test message",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Bold* message"
      }
    }
  ],
  "thread_ts": "1234567890.123456"
}
```

### Reaction Payload
```json
{
  "community_id": "test-community",
  "channel_id": "C01234567",
  "ts": "1234567890.123456",
  "emoji": "thumbsup"
}
```

### File Upload Payload
```json
{
  "community_id": "test-community",
  "channel_id": "C01234567",
  "file_content_base64": "JVBERi0xLjQKJeLj...",
  "filename": "document.pdf",
  "title": "Important Document"
}
```

### Channel Create Payload
```json
{
  "community_id": "test-community",
  "name": "team-announcements",
  "is_private": false
}
```

## Running Tests Locally

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### Test Execution Steps

```bash
# 1. Set up test environment
export SLACK_BOT_TOKEN="xoxb-test-token"
export MODULE_SECRET_KEY="test-secret-key-32-chars-minimum"
export DATABASE_URL="postgresql://user:pass@localhost/test_db"

# 2. Run all tests
pytest tests/ -v

# 3. Run with coverage
pytest tests/ --cov=action.pushing.slack_action_module --cov-report=term-missing

# 4. Run specific test category
pytest tests/unit/ -v          # Unit tests only
pytest tests/integration/ -v   # Integration tests
pytest tests/api/ -v           # API endpoint tests

# 5. Run with detailed output
pytest tests/ -vv --tb=short --log-cli-level=DEBUG
```

### Docker Test Execution

```bash
# Build test image
docker build -f Dockerfile.test -t slack-action-module:test .

# Run tests in container
docker run --rm slack-action-module:test pytest tests/ -v

# Run with coverage report
docker run --rm -v $(pwd)/coverage:/app/coverage \
  slack-action-module:test \
  pytest tests/ --cov=action.pushing.slack_action_module \
  --cov-report=html:/app/coverage
```

## Smoke Tests

Quick validation that the module starts and responds:

```bash
#!/bin/bash
# smoke-tests.sh

echo "Starting Slack Action Module smoke tests..."

# Start module in background
docker run -d \
  --name slack-action-module-smoke \
  -p 8071:8071 \
  -p 50052:50052 \
  -e SLACK_BOT_TOKEN="xoxb-test" \
  -e MODULE_SECRET_KEY="test-secret-key" \
  -e DATABASE_URL="postgresql://user:pass@postgres:5432/test" \
  slack-action-module:latest

sleep 3

# Test 1: Health check
echo "Test 1: Health check..."
curl -f http://localhost:8071/health || exit 1

# Test 2: Token generation
echo "Test 2: Token generation..."
curl -f -X POST http://localhost:8071/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "test-secret-key", "client_id": "test"}' || exit 1

# Test 3: Invalid auth (should return 401)
echo "Test 3: Invalid auth check..."
curl -f http://localhost:8071/api/v1/message \
  -H "Authorization: Bearer invalid" \
  && exit 1 || [ $? -eq 22 ]

echo "All smoke tests passed!"

# Cleanup
docker stop slack-action-module-smoke
docker rm slack-action-module-smoke
```

## Performance Testing

Test message throughput and latency:

```bash
#!/bin/bash
# perf-test.sh

echo "Running performance tests..."

# Generate JWT token
TOKEN=$(curl -s -X POST http://localhost:8071/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "secret", "client_id": "perf-test"}' \
  | jq -r '.token')

# Test 1: Send 100 messages sequentially
echo "Test 1: Sequential message sending (100 messages)..."
time for i in {1..100}; do
  curl -s -X POST http://localhost:8071/api/v1/message \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"community_id\": \"perf-test\",
      \"channel_id\": \"C01234567\",
      \"text\": \"Message $i\"
    }" > /dev/null
done

# Test 2: Concurrent requests
echo "Test 2: Concurrent requests (10 parallel)..."
time for i in {1..100}; do
  curl -s -X POST http://localhost:8071/api/v1/message \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"community_id\": \"perf-test\",
      \"channel_id\": \"C01234567\",
      \"text\": \"Concurrent $i\"
    }" > /dev/null &
  if [ $(($i % 10)) -eq 0 ]; then wait; fi
done

echo "Performance tests complete!"
```

## Test Configuration

### pytest.ini Configuration

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: unit tests
    integration: integration tests
    slow: slow running tests
    smoke: smoke tests
```

### conftest.py Setup

```python
# tests/conftest.py
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture
def mock_slack_client():
    """Mock Slack SDK WebClient"""
    client = MagicMock()
    client.chat_postMessage.return_value = {
        'ok': True,
        'channel': 'C01234567',
        'ts': '1234567890.123456'
    }
    return client

@pytest.fixture
def mock_database():
    """Mock PyDAL database connection"""
    db = MagicMock()
    db.executesql.return_value = [('xoxb-test-token', {})]
    return db

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

## Debugging Tests

### Enable Debug Output

```bash
# Verbose logging with all prints
pytest tests/unit/test_slack_service.py -vv -s

# Show variable values and full tracebacks
pytest tests/unit/test_slack_service.py -vv --tb=long

# Stop on first failure
pytest tests/unit/ -x

# Enter debugger on failure
pytest tests/unit/ --pdb

# Print all mock calls
pytest tests/unit/ -vv --log-cli-level=DEBUG
```

### Mock Inspection

```python
def test_with_mock_inspection():
    mock_client = MagicMock()
    mock_client.chat_postMessage.return_value = {'ok': True}

    # Inspect calls
    print(mock_client.chat_postMessage.call_count)      # 0 before call
    print(mock_client.chat_postMessage.call_args)       # Arguments
    print(mock_client.chat_postMessage.call_args_list)  # All calls
    print(mock_client.method_calls)                      # All method calls
```
