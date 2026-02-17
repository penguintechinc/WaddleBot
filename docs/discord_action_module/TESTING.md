# Discord Action Module - Testing

## Overview

Testing for the Discord Action Module includes unit tests, integration tests, and end-to-end tests. All tests mock Discord API responses to ensure reliable, isolated testing.

## Test Structure

Tests are located in test_api.py and can be run with pytest:

```bash
cd /home/penguin/code/waddlebot/action/pushing/discord_action_module
python -m pytest test_api.py -v
```

## Unit Tests

### Test Setup

```python
import pytest
from app import app, db, discord_service
from config import Config

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client
```

### Health Check Test

```bash
pytest test_api.py::test_health_check -v
```

**Test:**
```python
def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.json
    assert data['status'] == 'healthy'
    assert data['module'] == 'discord_action_module'
    assert 'version' in data
    assert 'config' in data
```

### Authentication Tests

```bash
pytest test_api.py::test_token_generation -v
pytest test_api.py::test_invalid_token -v
pytest test_api.py::test_expired_token -v
```

**Test Token Generation:**
```python
def test_token_generation(client):
    response = client.post('/api/v1/token', json={
        'client_id': 'test_app',
        'client_secret': 'test_secret'
    })
    assert response.status_code == 200
    data = response.json
    assert 'token' in data
    assert 'expires_in' in data
    assert data['expires_in'] == Config.JWT_EXPIRATION_SECONDS
```

**Test Invalid Token:**
```python
def test_invalid_token(client):
    response = client.post('/api/v1/message', 
        headers={'Authorization': 'Bearer invalid_token'},
        json={
            'channel_id': '123',
            'content': 'test'
        }
    )
    assert response.status_code == 401
    assert 'error' in response.json
```

## Mock Discord API

Mock Discord API responses to avoid rate limits and external dependencies:

```python
import aiohttp
from unittest.mock import Mock, AsyncMock, patch

@pytest.fixture
def mock_discord_api():
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'id': '123456789987654321',
            'content': 'test message',
            'author': {'id': '987654321'},
            'channel_id': '123456789'
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        yield mock_post
```

## Integration Tests

### Send Message Test

```bash
pytest test_api.py::test_send_message -v
```

**Test:**
```python
@pytest.mark.asyncio
async def test_send_message(client, mock_discord_api):
    # Generate token
    token_response = client.post('/api/v1/token', json={
        'client_id': 'test',
        'client_secret': 'test'
    })
    token = token_response.json['token']
    
    # Send message
    response = client.post('/api/v1/message',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'channel_id': '123456789',
            'content': 'Test message'
        }
    )
    assert response.status_code == 200
    data = response.json
    assert data['success'] == True
    assert 'message_id' in data
```

### Send Embed Test

```bash
pytest test_api.py::test_send_embed -v
```

**Test:**
```python
@pytest.mark.asyncio
async def test_send_embed(client, mock_discord_api):
    token_response = client.post('/api/v1/token', json={
        'client_id': 'test',
        'client_secret': 'test'
    })
    token = token_response.json['token']
    
    response = client.post('/api/v1/embed',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'channel_id': '123456789',
            'embed': {
                'title': 'Test Embed',
                'description': 'Test description',
                'color': 3447003,
                'fields': [{
                    'name': 'Field 1',
                    'value': 'Value 1'
                }]
            }
        }
    )
    assert response.status_code == 200
    assert response.json['success'] == True
```

### Role Management Test

```bash
pytest test_api.py::test_add_role -v
```

**Test:**
```python
@pytest.mark.asyncio
async def test_add_role(client, mock_discord_api):
    token_response = client.post('/api/v1/token', json={
        'client_id': 'test',
        'client_secret': 'test'
    })
    token = token_response.json['token']
    
    response = client.post('/api/v1/role',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'guild_id': '987654321',
            'user_id': '123456789',
            'role_id': '555555555',
            'action': 'add'
        }
    )
    assert response.status_code == 200
    assert response.json['success'] == True
```

### Moderation Tests

```bash
pytest test_api.py::test_kick_user -v
pytest test_api.py::test_ban_user -v
pytest test_api.py::test_timeout_user -v
```

**Test Kick:**
```python
@pytest.mark.asyncio
async def test_kick_user(client, mock_discord_api):
    token_response = client.post('/api/v1/token', json={
        'client_id': 'test',
        'client_secret': 'test'
    })
    token = token_response.json['token']
    
    response = client.post('/api/v1/moderation/kick',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'guild_id': '987654321',
            'user_id': '123456789',
            'reason': 'Test kick'
        }
    )
    assert response.status_code == 200
    assert response.json['success'] == True
```

## End-to-End Tests

### Real Discord API Testing

For E2E testing with real Discord, use test Discord server:

```bash
# Set real credentials for testing
export DISCORD_BOT_TOKEN="your_test_bot_token"
export DATABASE_URL="postgresql://test:test@localhost/test_discord"

# Run E2E tests
pytest test_api.py -v -m "e2e"
```

**Test Payloads:**

```json
{
  "message": {
    "channel_id": "YOUR_TEST_CHANNEL_ID",
    "content": "E2E Test Message",
    "embed": {
      "title": "E2E Test",
      "description": "Testing with real Discord API",
      "color": 3447003
    }
  },
  "role": {
    "guild_id": "YOUR_TEST_GUILD_ID",
    "user_id": "YOUR_TEST_USER_ID",
    "role_id": "YOUR_TEST_ROLE_ID",
    "action": "add"
  },
  "moderation": {
    "guild_id": "YOUR_TEST_GUILD_ID",
    "user_id": "YOUR_TEST_USER_ID",
    "reason": "E2E Testing"
  }
}
```

## Error Handling Tests

### Test Missing Token

```python
def test_missing_auth_token(client):
    response = client.post('/api/v1/message', json={
        'channel_id': '123',
        'content': 'test'
    })
    assert response.status_code == 401
    assert 'error' in response.json
```

### Test Invalid Parameters

```python
def test_missing_channel_id(client, token):
    response = client.post('/api/v1/message',
        headers={'Authorization': f'Bearer {token}'},
        json={'content': 'test'}
    )
    assert response.status_code == 400
    assert 'error' in response.json
```

### Test Rate Limiting

```python
@pytest.mark.asyncio
async def test_rate_limit_enforcement(client, token, mock_discord_api):
    # Make rapid requests
    tasks = []
    for i in range(10):
        response = client.post('/api/v1/message',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'channel_id': '123',
                'content': f'Message {i}'
            }
        )
        tasks.append(response)
    
    # Some should be rate limited or queued
    assert len(tasks) == 10
```

## Database Testing

### Test Activity Logging

```python
@pytest.mark.asyncio
async def test_action_logging(client, token, mock_discord_api):
    # Send message
    response = client.post('/api/v1/message',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'channel_id': '123456789',
            'content': 'Test'
        }
    )
    
    # Check database for logged action
    action = db(db.discord_actions.action_type == 'MESSAGE').select().first()
    assert action is not None
    assert action.channel_id == '123456789'
    assert action.success == True
```

## Running Tests

### All Tests
```bash
pytest test_api.py -v
```

### Specific Test
```bash
pytest test_api.py::test_send_message -v
```

### With Coverage
```bash
pytest test_api.py --cov=. --cov-report=html
```

### Mark Tests by Category
```bash
pytest test_api.py -m "unit" -v
pytest test_api.py -m "integration" -v
pytest test_api.py -m "e2e" -v
```

## Test Data

Mock test data for various scenarios:

```python
TEST_DATA = {
    'valid_channel': '123456789987654321',
    'valid_guild': '987654321123456789',
    'valid_user': '111111111222222222',
    'valid_role': '333333333444444444',
    'valid_message': '555555555666666666',
    'invalid_channel': 'invalid',
    'invalid_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.invalid',
}
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_discord
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt pytest pytest-cov
      - run: pytest test_api.py --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Troubleshooting Tests

**Tests fail with database error:**
```bash
# Ensure PostgreSQL is running
docker-compose -f docker-compose.yml up -d postgres

# Run tests
pytest test_api.py -v
```

**AsyncIO test errors:**
```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Mark async tests
@pytest.mark.asyncio
async def test_async_function():
    ...
```

**Mock errors:**
```bash
# Verify mock patch path matches import
from unittest.mock import patch

# Use correct path: module.where.function
@patch('app.aiohttp.ClientSession.post')
def test_with_mock(mock_post):
    ...
```

See test_api.py for complete test examples.
