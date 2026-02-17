# YouTube Action Module - Testing Guide

## Unit Testing

Comprehensive unit tests using pytest with mocks for Google API client.

### Test Structure

```
tests/
├── unit/
│   ├── test_youtube_service.py        # YouTubeService methods
│   ├── test_oauth_manager.py          # OAuth flow
│   ├── test_app_endpoints.py          # REST API endpoints
│   ├── test_authentication.py         # JWT authentication
│   └── test_config.py                 # Configuration
├── fixtures/
│   ├── mock_youtube_responses.py      # Google API responses
│   ├── test_tokens.py                 # JWT fixtures
│   └── test_payloads.py               # Request payloads
└── conftest.py                         # pytest configuration
```

### Running Tests

```bash
# All tests
pytest tests/unit/ -v

# Specific test file
pytest tests/unit/test_youtube_service.py -v

# Specific test
pytest tests/unit/test_youtube_service.py::test_send_chat_message_success -v

# With coverage
pytest tests/unit/ --cov=action.pushing.youtube_action_module --cov-report=html

# With logging
pytest tests/unit/ -v --log-cli-level=DEBUG
```

### Sample Unit Test

```python
# tests/unit/test_youtube_service.py
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def youtube_service():
    """Create YouTubeService with mocked clients"""
    with patch('services.youtube_service.build') as mock_build:
        service = YouTubeService(oauth_manager=MagicMock())
        service.youtube_client = mock_build
        yield service

def test_send_live_chat_message_success(youtube_service):
    """Test successful live chat message"""
    # Arrange
    youtube_service.youtube_client.liveChatMessages().insert().execute.return_value = {
        'id': 'msg_123',
        'kind': 'youtube#liveChatMessage'
    }

    # Act
    result = youtube_service.send_live_chat_message(
        live_chat_id="AimFLc...",
        message="Hello YouTube Live!",
        channel_id="UCxxxxx"
    )

    # Assert
    assert result['success'] == True
    assert result['data']['message_id'] == 'msg_123'

def test_send_chat_quota_exceeded(youtube_service):
    """Test when API quota exceeded"""
    # Arrange
    from googleapiclient.errors import HttpError
    error = HttpError(
        resp=MagicMock(status=403),
        content=b'{"error": {"message": "Quota exceeded"}}'
    )
    youtube_service.youtube_client.liveChatMessages().insert().execute.side_effect = error

    # Act
    result = youtube_service.send_live_chat_message(
        live_chat_id="AimFLc...",
        message="Hello",
        channel_id="UCxxxxx"
    )

    # Assert
    assert result['success'] == False
    assert 'quotaExceeded' in result['error']
```

### Mock Google API Responses

```python
# tests/fixtures/mock_youtube_responses.py

MOCK_LIVE_CHAT_MESSAGE_RESPONSE = {
    'kind': 'youtube#liveChatMessage',
    'id': 'msg_123456',
    'snippet': {
        'type': 'messageCreateEvent',
        'messageText': 'Hello YouTube Live!',
        'publishedAt': '2024-01-15T10:30:00Z',
        'authorChannelUrl': 'http://www.youtube.com/channel/UCyyyyyy',
        'authorChannelId': 'UCyyyyyy',
        'authorDisplayName': 'WaddleBot'
    }
}

MOCK_VIDEO_UPDATE_RESPONSE = {
    'kind': 'youtube#video',
    'id': 'dQw4w9WgXcQ',
    'snippet': {
        'title': 'New Title',
        'description': 'New description',
        'tags': [],
        'categoryId': '24'
    }
}

MOCK_PLAYLIST_CREATE_RESPONSE = {
    'kind': 'youtube#playlist',
    'id': 'PLxxxxx',
    'snippet': {
        'publishedAt': '2024-01-15T10:30:00Z',
        'title': 'My Playlist',
        'description': 'Playlist description',
        'tags': [],
        'defaultLanguage': 'en',
        'localized': {
            'title': 'My Playlist',
            'description': 'Playlist description'
        }
    }
}

MOCK_ERROR_QUOTA_EXCEEDED = {
    'error': {
        'code': 403,
        'message': 'The request cannot be completed because you have exceeded your YouTube API quota',
        'errors': [
            {
                'domain': 'youtube.quota',
                'reason': 'quotaExceeded',
                'message': 'The request cannot be completed because you have exceeded your YouTube API quota'
            }
        ]
    }
}
```

## Integration Testing

```python
# tests/integration/test_oauth_flow.py
import pytest
from app import app

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    return app.test_client()

@pytest.mark.asyncio
async def test_health_check(client):
    """Test health endpoint"""
    response = await client.get('/health')
    assert response.status_code == 200
    data = await response.get_json()
    assert data['status'] == 'healthy'

@pytest.mark.asyncio
async def test_oauth_authorize(client):
    """Test OAuth authorization URL"""
    response = await client.get('/oauth/authorize?state=channel-123')
    assert response.status_code == 200
    data = await response.get_json()
    assert data['success'] == True
    assert 'authorization_url' in data
    assert 'accounts.google.com' in data['authorization_url']

@pytest.mark.asyncio
async def test_send_chat_unauthorized(client):
    """Test chat send without auth"""
    response = await client.post(
        '/api/v1/chat/send',
        json={
            'channel_id': 'UCxxxxx',
            'live_chat_id': 'AimFLc...',
            'message': 'Hello'
        }
    )
    assert response.status_code == 401
```

## Test Payloads

### Live Chat Message
```json
{
  "channel_id": "UCxxxxx",
  "live_chat_id": "AimFLc...",
  "message": "Hello YouTube Live!"
}
```

### Playlist Creation
```json
{
  "channel_id": "UCxxxxx",
  "title": "My Playlist",
  "description": "Playlist description",
  "privacy": "private"
}
```

### Video Update
```json
{
  "channel_id": "UCxxxxx",
  "video_id": "dQw4w9WgXcQ",
  "title": "New Title"
}
```

### Comment Post
```json
{
  "channel_id": "UCxxxxx",
  "video_id": "dQw4w9WgXcQ",
  "text": "Great video!"
}
```

## Running Tests

### Prerequisites

```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### Execution

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=action.pushing.youtube_action_module

# Docker
docker build -f Dockerfile.test -t youtube-action-module:test .
docker run --rm youtube-action-module:test pytest tests/ -v
```

## Smoke Tests

```bash
#!/bin/bash
# smoke-tests.sh

echo "Starting YouTube Action Module smoke tests..."

# Start module
docker run -d \
  --name youtube-action-module-smoke \
  -p 8073:8073 \
  -p 50054:50054 \
  -e YOUTUBE_CLIENT_ID="test-id" \
  -e YOUTUBE_CLIENT_SECRET="test-secret" \
  -e MODULE_SECRET_KEY="test-secret-key" \
  -e DATABASE_URL="postgresql://..." \
  youtube-action-module:latest

sleep 3

# Test 1: Health check
echo "Test 1: Health check..."
curl -f http://localhost:8073/health || exit 1

# Test 2: OAuth authorize
echo "Test 2: OAuth authorize..."
curl -f -G http://localhost:8073/oauth/authorize -d "state=test" || exit 1

echo "Smoke tests passed!"

docker stop youtube-action-module-smoke
docker rm youtube-action-module-smoke
```

## Test Configuration

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
asyncio_mode = auto
markers =
    unit: unit tests
    integration: integration tests
    slow: slow tests
```

### conftest.py

```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_youtube_client():
    """Mock YouTube API client"""
    client = MagicMock()
    return client

@pytest.fixture
def mock_oauth_manager():
    """Mock OAuth manager"""
    manager = MagicMock()
    manager.get_credentials.return_value = MagicMock(
        access_token="test-token"
    )
    return manager
```
