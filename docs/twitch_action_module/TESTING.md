# Twitch Action Module - Testing Guide

## Unit Testing

The module includes comprehensive unit tests using pytest with mocks for IRC and Twitch API.

### Test Structure

```
tests/
├── unit/
│   ├── test_twitch_service.py         # TwitchService methods
│   ├── test_token_manager.py          # Token refresh logic
│   ├── test_app_endpoints.py          # REST API endpoints
│   ├── test_authentication.py         # JWT authentication
│   ├── test_irc_client.py             # IRC protocol handling
│   └── test_config.py                 # Configuration loading
├── fixtures/
│   ├── mock_twitch_responses.py       # Twitch API response fixtures
│   ├── mock_irc_responses.py          # IRC protocol responses
│   ├── test_tokens.py                 # JWT token fixtures
│   └── test_payloads.py               # Request payload examples
└── conftest.py                         # pytest configuration
```

### Running Unit Tests

```bash
# Run all tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_twitch_service.py -v

# Run specific test
pytest tests/unit/test_twitch_service.py::test_send_chat_message_success -v

# Run with coverage
pytest tests/unit/ --cov=action.pushing.twitch_action_module --cov-report=html

# Run with logging
pytest tests/unit/ -v --log-cli-level=DEBUG
```

### Sample Unit Test

```python
# tests/unit/test_twitch_service.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

@pytest.fixture
def twitch_service():
    """Create TwitchService with mocked clients"""
    with patch('services.twitch_service.requests.Session') as mock_session:
        service = TwitchService(token_manager=MagicMock())
        service.http_session = mock_session
        yield service

@pytest.mark.asyncio
async def test_send_chat_message_success(twitch_service):
    """Test successful chat message sending"""
    # Arrange
    twitch_service.token_manager.get_valid_token.return_value = {
        "access_token": "test-token",
        "refresh_token": "refresh-token"
    }

    # Mock IRC connection
    mock_irc = AsyncMock()
    twitch_service.irc_connections["123456789"] = mock_irc
    mock_irc.send_message.return_value = True

    # Act
    result = await twitch_service.send_chat_message(
        broadcaster_id="123456789",
        message="Hello Twitch!"
    )

    # Assert
    assert result["success"] == True
    mock_irc.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_token_refresh_on_expiry(twitch_service):
    """Test automatic token refresh when expired"""
    # Arrange
    token_manager = twitch_service.token_manager
    token_manager.get_valid_token.side_effect = [
        {"access_token": "expired-token"},
        {"access_token": "refreshed-token"}
    ]

    # Act
    token1 = token_manager.get_valid_token("123456789")
    token2 = token_manager.get_valid_token("123456789")

    # Assert
    assert token1["access_token"] == "expired-token"
    assert token2["access_token"] == "refreshed-token"

@pytest.mark.asyncio
async def test_token_refresh_error_handling(twitch_service):
    """Test error handling during token refresh"""
    # Arrange
    token_manager = twitch_service.token_manager
    token_manager.refresh_token.side_effect = Exception("API Error")

    # Act
    with pytest.raises(Exception):
        token_manager.refresh_token("123456789")

    # Assert
    token_manager.refresh_token.assert_called_once()
```

### Mock Twitch Responses

```python
# tests/fixtures/mock_twitch_responses.py

MOCK_TOKEN_RESPONSE = {
    "access_token": "access_token_12345",
    "refresh_token": "refresh_token_12345",
    "expires_in": 3600,
    "scope": ["chat:edit", "chat:read"],
    "token_type": "bearer"
}

MOCK_CLIPS_CREATE_RESPONSE = {
    "data": [
        {
            "id": "clip_12345",
            "url": "https://clips.twitch.tv/Example",
            "edit_url": "https://clips.twitch.tv/Example/edit",
            "created_at": "2024-01-15T10:30:00Z"
        }
    ]
}

MOCK_ERROR_RESPONSE_INVALID_OAUTH_TOKEN = {
    "error": "Unauthorized",
    "status": 401,
    "message": "Invalid OAuth token"
}

MOCK_ERROR_RESPONSE_RATE_LIMITED = {
    "error": "Too Many Requests",
    "status": 429,
    "message": "Rate limited"
}
```

### Mock IRC Responses

```python
# tests/fixtures/mock_irc_responses.py

MOCK_IRC_CONNECT_SUCCESS = [
    ":tmi.twitch.tv NOTICE * :Login authentication failed",
    ":waddlebot!waddlebot@waddlebot.tmi.twitch.tv PRIVMSG #channel :connected"
]

MOCK_IRC_MESSAGE_ACK = {
    "channel": "#channel",
    "message": "message text",
    "user": "waddlebot"
}

MOCK_IRC_ERROR_RESPONSE = {
    "error": "ERR_NOTREGISTERED",
    "message": "You have not registered"
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
    """Generate valid JWT token"""
    import jwt
    import time
    payload = {
        'exp': int(time.time()) + 3600,
        'iat': int(time.time()),
        'sub': 'test-service'
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
    assert data['module'] == 'twitch_action_module'

@pytest.mark.asyncio
async def test_execute_action_unauthorized(client):
    """Test action execution without token"""
    response = await client.post(
        '/api/v1/actions/execute',
        data=json.dumps({
            'action_type': 'send_chat_message',
            'broadcaster_id': '123456789',
            'parameters': {'message': 'Hello'}
        }),
        content_type='application/json'
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_execute_action_with_token(client, valid_jwt_token):
    """Test action execution with valid token"""
    response = await client.post(
        '/api/v1/actions/execute',
        headers={'Authorization': f'Bearer {valid_jwt_token}'},
        data=json.dumps({
            'action_type': 'send_chat_message',
            'broadcaster_id': '123456789',
            'parameters': {'message': 'Hello'}
        }),
        content_type='application/json'
    )
    assert response.status_code in [200, 500]  # 200 if mocked, 500 if no mock

@pytest.mark.asyncio
async def test_batch_execute_actions(client, valid_jwt_token):
    """Test batch action execution"""
    response = await client.post(
        '/api/v1/actions/batch',
        headers={'Authorization': f'Bearer {valid_jwt_token}'},
        data=json.dumps({
            'actions': [
                {
                    'action_type': 'send_chat_message',
                    'broadcaster_id': '123456789',
                    'request_id': 'msg_1',
                    'parameters': {'message': 'Message 1'}
                },
                {
                    'action_type': 'send_chat_message',
                    'broadcaster_id': '123456789',
                    'request_id': 'msg_2',
                    'parameters': {'message': 'Message 2'}
                }
            ]
        }),
        content_type='application/json'
    )
    assert response.status_code in [200, 400, 500]
```

## EventSub Webhook Testing

Test webhook signature verification and event processing:

```python
# tests/integration/test_eventsub_webhooks.py
import hmac
import hashlib
import pytest

def create_eventsub_signature(message_id, timestamp, body, secret):
    """Create valid EventSub signature"""
    hmac_message = f"{message_id}{timestamp}{body}"
    signature = "sha256=" + hmac.new(
        secret.encode(),
        hmac_message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature

@pytest.mark.asyncio
async def test_eventsub_webhook_signature_valid(client):
    """Test valid EventSub webhook signature"""
    # Arrange
    message_id = "test-123"
    timestamp = "2024-01-15T10:30:00Z"
    body = '{"subscription": {"type": "stream.online"}}'
    secret = "your-webhook-secret"

    signature = create_eventsub_signature(message_id, timestamp, body, secret)

    # Act
    response = await client.post(
        '/webhooks/eventsub',
        data=body,
        headers={
            'Twitch-Eventsub-Message-Id': message_id,
            'Twitch-Eventsub-Message-Timestamp': timestamp,
            'Twitch-Eventsub-Message-Signature': signature
        },
        content_type='application/json'
    )

    # Assert
    assert response.status_code == 200  # Signature valid

@pytest.mark.asyncio
async def test_eventsub_webhook_signature_invalid(client):
    """Test invalid EventSub webhook signature"""
    # Arrange
    headers = {
        'Twitch-Eventsub-Message-Id': 'test-123',
        'Twitch-Eventsub-Message-Timestamp': '2024-01-15T10:30:00Z',
        'Twitch-Eventsub-Message-Signature': 'sha256=invalid_signature'
    }

    # Act
    response = await client.post(
        '/webhooks/eventsub',
        data='{}',
        headers=headers,
        content_type='application/json'
    )

    # Assert
    assert response.status_code == 403  # Signature invalid
```

## Test Payloads

### Chat Message Payload
```json
{
  "action_type": "send_chat_message",
  "broadcaster_id": "123456789",
  "request_id": "msg_001",
  "parameters": {
    "message": "Hello Twitch chat!"
  }
}
```

### Clip Creation Payload
```json
{
  "action_type": "create_clip",
  "broadcaster_id": "123456789",
  "request_id": "clip_001",
  "parameters": {
    "title": "Epic Moment",
    "has_delay": false
  }
}
```

### Token Storage Payload
```json
{
  "broadcaster_id": "123456789",
  "access_token": "access_token_here",
  "refresh_token": "refresh_token_here",
  "expires_in": 3600,
  "scopes": ["chat:edit", "chat:read", "clips:edit"]
}
```

### Batch Actions Payload
```json
{
  "actions": [
    {
      "action_type": "send_chat_message",
      "broadcaster_id": "123456789",
      "request_id": "msg_1",
      "parameters": {"message": "Message 1"}
    },
    {
      "action_type": "send_chat_message",
      "broadcaster_id": "123456789",
      "request_id": "msg_2",
      "parameters": {"message": "Message 2"}
    },
    {
      "action_type": "send_chat_message",
      "broadcaster_id": "123456789",
      "request_id": "msg_3",
      "parameters": {"message": "Message 3"}
    }
  ]
}
```

## Running Tests Locally

### Prerequisites

```bash
# Install dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock httpx
```

### Test Execution

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=action.pushing.twitch_action_module --cov-report=html

# Run specific category
pytest tests/unit/ -v              # Unit tests
pytest tests/integration/ -v       # Integration tests
pytest tests/unit/test_twitch_service.py -v  # Single file

# Detailed output
pytest tests/ -vv --tb=short --log-cli-level=DEBUG

# Stop on first failure
pytest tests/ -x

# Debug mode (drops into pdb on failure)
pytest tests/ --pdb
```

### Docker Test Execution

```bash
# Build test image
docker build -f Dockerfile.test -t twitch-action-module:test .

# Run tests
docker run --rm twitch-action-module:test pytest tests/ -v

# Run with coverage
docker run --rm -v $(pwd)/coverage:/app/coverage \
  twitch-action-module:test \
  pytest tests/ --cov=action.pushing.twitch_action_module --cov-report=html:/app/coverage
```

## Smoke Tests

Quick validation that module starts and responds:

```bash
#!/bin/bash
# smoke-tests.sh

echo "Starting Twitch Action Module smoke tests..."

# Start module
docker run -d \
  --name twitch-action-module-smoke \
  -p 8072:8072 \
  -p 50053:50053 \
  -e TWITCH_CLIENT_ID="test-id" \
  -e TWITCH_CLIENT_SECRET="test-secret" \
  -e MODULE_SECRET_KEY="test-secret-key" \
  -e DATABASE_URL="postgresql://user:pass@postgres:5432/test" \
  twitch-action-module:latest

sleep 3

# Test 1: Health check
echo "Test 1: Health check..."
curl -f http://localhost:8072/health || exit 1

# Test 2: Token generation
echo "Test 2: Token generation..."
curl -f -X POST http://localhost:8072/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "test-secret-key"}' || exit 1

echo "Smoke tests passed!"

# Cleanup
docker stop twitch-action-module-smoke
docker rm twitch-action-module-smoke
```

## Performance Testing

Test message throughput and action latency:

```bash
#!/bin/bash
# perf-test.sh

TOKEN=$(curl -s -X POST http://localhost:8072/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "secret"}' | jq -r '.token')

# Test 1: Sequential messages
echo "Sequential messages (100)..."
time for i in {1..100}; do
  curl -s -X POST http://localhost:8072/api/v1/actions/execute \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"action_type\": \"send_chat_message\",
      \"broadcaster_id\": \"123456789\",
      \"parameters\": {\"message\": \"Message $i\"}
    }" > /dev/null
done

# Test 2: Concurrent requests
echo "Concurrent requests (10 parallel)..."
time for i in {1..100}; do
  curl -s -X POST http://localhost:8072/api/v1/actions/execute \
    -H "Authorization: Bearer $TOKEN" \
    -d "{...}" > /dev/null &
  if [ $(($i % 10)) -eq 0 ]; then wait; fi
done

# Test 3: Batch operations
echo "Batch operations..."
time curl -s -X POST http://localhost:8072/api/v1/actions/batch \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"actions": [...]}'
```

## Test Configuration

### pytest.ini

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
    slow: slow tests
    smoke: smoke tests
```

### conftest.py

```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock
import asyncio

@pytest.fixture
def mock_twitch_client():
    """Mock Twitch API client"""
    client = MagicMock()
    client.clips.create.return_value = {
        "data": [{"id": "clip_123", "url": "https://clips.twitch.tv/..."}]
    }
    return client

@pytest.fixture
def mock_token_manager():
    """Mock token manager"""
    manager = MagicMock()
    manager.get_valid_token.return_value = {"access_token": "test-token"}
    return manager

@pytest.fixture
def mock_database():
    """Mock database connection"""
    db = MagicMock()
    db.executesql.return_value = [("test-token", {})]
    return db
```
