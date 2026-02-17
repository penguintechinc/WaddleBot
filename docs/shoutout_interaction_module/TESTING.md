# Shoutout Interaction Module — Testing Guide

## Test Strategy

The module uses pytest for unit tests and supports multiple testing levels:

- **Unit Tests** - Individual service methods with mocked dependencies
- **Integration Tests** - Multiple services working together with test database
- **End-to-End Tests** - Full HTTP API endpoints with mock Twitch API
- **Manual Testing** - Interactive testing during development

## Setup for Testing

### Install Test Dependencies

```bash
cd action/interactive/shoutout_interaction_module/
pip install -r requirements-test.txt
```

**requirements-test.txt contents:**
```
pytest>=7.0
pytest-asyncio>=0.20
pytest-cov>=4.0
aioresponses>=0.7
responses>=0.22
```

### Test Database

```bash
# Create test database
createdb waddlebot_test

# Run migrations
psql waddlebot_test < ../../config/postgres/migrations/036_calendar_appointments.sql
psql waddlebot_test < ../../config/postgres/migrations/037_fix_community_schema.sql
```

Or use Docker:

```bash
docker run -d \
  -e POSTGRES_DB=waddlebot_test \
  -e POSTGRES_USER=waddlebot \
  -e POSTGRES_PASSWORD=password \
  -p 5433:5432 \
  postgres:15
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_shoutout_service.py -v
```

### Run Specific Test

```bash
pytest tests/test_shoutout_service.py::test_generate_shoutout_with_live_user -v
```

### Run with Coverage Report

```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

### Run Only Unit Tests

```bash
pytest tests/unit/ -v
```

### Run Only Integration Tests (requires DB)

```bash
pytest tests/integration/ -v
```

## Mock Data & Fixtures

### Mock Twitch Response

```python
# tests/fixtures/twitch_responses.py
MOCK_TWITCH_USER = {
    'data': [{
        'id': '88888888',
        'login': 'pokimane',
        'display_name': 'Pokimane',
        'description': 'Content creator',
        'profile_image_url': 'https://static-cdn.jtvnw.net/...',
        'offline_image_url': 'https://static-cdn.jtvnw.net/...'
    }]
}

MOCK_TWITCH_CHANNEL = {
    'data': [{
        'broadcaster_id': '88888888',
        'broadcaster_login': 'pokimane',
        'game_id': '12345',
        'game_name': 'World of Warcraft',
        'title': 'Mythic+ Dungeons'
    }]
}

MOCK_TWITCH_STREAM = {
    'data': [{
        'id': 'stream_123456',
        'user_id': '88888888',
        'type': 'live',
        'viewer_count': 5000,
        'started_at': '2026-02-15T10:00:00Z'
    }]
}

MOCK_TWITCH_CLIP = {
    'data': [{
        'id': 'clip_abc123',
        'url': 'https://clips.twitch.tv/...',
        'title': 'Best moment',
        'thumbnail_url': 'https://clips.twitch.tv/...',
        'created_at': '2026-02-14T08:00:00Z',
        'duration': 30,
        'view_count': 5000
    }]
}

MOCK_OAUTH_TOKEN = {
    'access_token': 'test_token_12345',
    'token_type': 'bearer',
    'expires_in': 3600
}
```

### Mock Identity Response

```python
# tests/fixtures/identity_responses.py
MOCK_IDENTITY_LINKED = {
    'identities': [
        {
            'platform': 'twitch',
            'platform_user_id': '88888888',
            'platform_username': 'pokimane',
            'is_primary': True
        },
        {
            'platform': 'youtube',
            'platform_user_id': 'UC_abcd1234',
            'platform_username': 'pokimane_youtube',
            'is_primary': False
        }
    ]
}

MOCK_IDENTITY_NOT_LINKED = {
    'identities': [
        {
            'platform': 'twitch',
            'platform_user_id': '88888888',
            'platform_username': 'pokimane',
            'is_primary': True
        }
    ]
}
```

## Example Unit Tests

### Test Shoutout Service

```python
# tests/unit/test_shoutout_service.py
import pytest
from unittest.mock import Mock
from services.shoutout_service import ShoutoutService

@pytest.fixture
def mock_dal():
    """Mock database access layer"""
    return Mock()

@pytest.fixture
def shoutout_service(mock_dal):
    return ShoutoutService(mock_dal)

def test_generate_shoutout_with_live_user(shoutout_service):
    """Test shoutout generation when user is live"""
    twitch_data = {
        'user': {
            'display_name': 'Pokimane',
            'login': 'pokimane',
            'description': 'Streamer'
        },
        'channel': {
            'game_name': 'World of Warcraft',
            'title': 'Mythic+ Dungeons'
        },
        'stream': {
            'viewer_count': 5000,
            'type': 'live'
        }
    }

    result = await shoutout_service.generate_shoutout(
        twitch_data,
        community_id=123,
        platform='twitch'
    )

    assert result['shoutout_text']
    assert 'Pokimane' in result['shoutout_text']
    assert 'World of Warcraft' in result['shoutout_text']
    assert '5000' in result['shoutout_text']

def test_generate_shoutout_with_offline_user(shoutout_service):
    """Test shoutout generation when user is offline"""
    twitch_data = {
        'user': {
            'display_name': 'Pokimane',
            'login': 'pokimane',
            'description': 'Streamer'
        },
        'channel': {
            'game_name': 'World of Warcraft',
            'title': ''
        },
        'stream': {
            'viewer_count': 0,
            'type': 'offline'
        }
    }

    result = await shoutout_service.generate_shoutout(
        twitch_data,
        community_id=123,
        platform='twitch'
    )

    assert result['shoutout_text']
    assert 'offline' not in result['shoutout_text'].lower()

def test_variable_substitution(shoutout_service):
    """Test template variable substitution"""
    template = "Check out {display_name} at twitch.tv/{login}! Playing {game_name}."
    twitch_data = {
        'user': {'display_name': 'Ninja', 'login': 'ninja'},
        'channel': {'game_name': 'Fortnite'},
        'stream': {}
    }

    result = shoutout_service._substitute_variables(template, twitch_data)

    assert result == "Check out Ninja at twitch.tv/ninja! Playing Fortnite."
```

### Test Twitch Service

```python
# tests/unit/test_twitch_service.py
import pytest
from aioresponses import aioresponses
from services.twitch_service import TwitchService
from tests.fixtures.twitch_responses import MOCK_OAUTH_TOKEN, MOCK_TWITCH_USER

@pytest.fixture
def twitch_service():
    return TwitchService(
        client_id='test_client_id',
        client_secret='test_client_secret'
    )

@pytest.mark.asyncio
async def test_get_access_token(twitch_service):
    """Test OAuth token retrieval"""
    with aioresponses() as mocked:
        mocked.post(
            'https://id.twitch.tv/oauth2/token',
            payload=MOCK_OAUTH_TOKEN
        )

        token = await twitch_service._get_access_token()

        assert token == MOCK_OAUTH_TOKEN['access_token']

@pytest.mark.asyncio
async def test_get_full_shoutout_data_found(twitch_service):
    """Test fetching user data when user exists"""
    with aioresponses() as mocked:
        # Mock token request
        mocked.post(
            'https://id.twitch.tv/oauth2/token',
            payload=MOCK_OAUTH_TOKEN
        )

        # Mock user lookup
        mocked.get(
            'https://api.twitch.tv/helix/users?login=pokimane',
            payload=MOCK_TWITCH_USER
        )

        # Mock channel lookup
        mocked.get(
            'https://api.twitch.tv/helix/channels?broadcaster_id=88888888',
            payload=MOCK_TWITCH_CHANNEL
        )

        # Mock stream lookup
        mocked.get(
            'https://api.twitch.tv/helix/streams?user_id=88888888',
            payload=MOCK_TWITCH_STREAM
        )

        result = await twitch_service.get_full_shoutout_data('pokimane')

        assert result is not None
        assert result['user']['login'] == 'pokimane'

@pytest.mark.asyncio
async def test_get_full_shoutout_data_not_found(twitch_service):
    """Test when user doesn't exist"""
    with aioresponses() as mocked:
        mocked.post(
            'https://id.twitch.tv/oauth2/token',
            payload=MOCK_OAUTH_TOKEN
        )

        mocked.get(
            'https://api.twitch.tv/helix/users?login=nonexistent',
            payload={'data': []}
        )

        result = await twitch_service.get_full_shoutout_data('nonexistent')

        assert result is None
```

### Test Video Service

```python
# tests/unit/test_video_service.py
import pytest
from aioresponses import aioresponses
from services.video_service import VideoService
from tests.fixtures.twitch_responses import MOCK_TWITCH_CLIP

@pytest.fixture
def video_service():
    return VideoService(
        twitch_client_id='test_client_id',
        twitch_client_secret='test_client_secret',
        youtube_api_key='test_youtube_key'
    )

@pytest.mark.asyncio
async def test_get_video_for_shoutout_twitch_clips(video_service):
    """Test video retrieval preferring Twitch clips"""
    with aioresponses() as mocked:
        # Mock token request
        mocked.post(
            'https://id.twitch.tv/oauth2/token',
            payload=MOCK_OAUTH_TOKEN
        )

        # Mock clips lookup
        mocked.get(
            'https://api.twitch.tv/helix/clips?broadcaster_id=88888888',
            payload=MOCK_TWITCH_CLIP
        )

        # Mock channel info
        mocked.get(
            'https://api.twitch.tv/helix/channels?broadcaster_id=88888888',
            payload=MOCK_TWITCH_CHANNEL
        )

        result = await video_service.get_video_for_shoutout(
            platform='twitch',
            username='pokimane'
        )

        assert result is not None
        assert result['video']['platform'] == 'twitch'
        assert result['video']['title'] == 'Best moment'
```

## Integration Tests

```python
# tests/integration/test_video_shoutout_flow.py
import pytest
from unittest.mock import AsyncMock, patch
from aioresponses import aioresponses

@pytest.mark.asyncio
async def test_full_video_shoutout_flow():
    """Test complete video shoutout workflow"""
    # Setup
    from services.video_shoutout_service import VideoShoutoutService
    from services.video_service import VideoService
    from services.identity_service import IdentityService

    # Mock database pool
    db_pool = AsyncMock()
    video_service = VideoService(
        twitch_client_id='test_id',
        twitch_client_secret='test_secret',
        youtube_api_key='test_key'
    )
    identity_service = IdentityService('http://localhost:8050')

    vso_service = VideoShoutoutService(
        db_pool=db_pool,
        video_service=video_service,
        identity_service=identity_service
    )

    with aioresponses() as mocked:
        # Mock all API calls
        # ... setup mocks ...

        result = await vso_service.execute_video_shoutout(
            community_id=123,
            target_username='pokimane',
            target_platform='twitch',
            trigger_type='manual',
            user_roles=['mod']
        )

        assert result.success is True
        assert result.video is not None
        assert result.channel is not None
```

## End-to-End API Tests

```python
# tests/e2e/test_api_endpoints.py
import pytest
from quart.testing import QuartClient

@pytest.mark.asyncio
async def test_create_shoutout_endpoint(client: QuartClient):
    """Test POST /api/v1/shoutout endpoint"""
    with aioresponses() as mocked:
        # Mock Twitch API calls
        mocked.post(
            'https://id.twitch.tv/oauth2/token',
            payload=MOCK_OAUTH_TOKEN
        )
        mocked.get(
            'https://api.twitch.tv/helix/users',
            payload=MOCK_TWITCH_USER
        )
        mocked.get(
            'https://api.twitch.tv/helix/channels',
            payload=MOCK_TWITCH_CHANNEL
        )
        mocked.get(
            'https://api.twitch.tv/helix/streams',
            payload=MOCK_TWITCH_STREAM
        )

        response = await client.post(
            '/api/v1/shoutout',
            json={
                'username': 'pokimane',
                'community_id': 123,
                'platform': 'twitch'
            }
        )

        assert response.status_code == 200
        data = await response.get_json()
        assert data['success'] is True
        assert 'shoutout_text' in data['data']

@pytest.mark.asyncio
async def test_create_shoutout_user_not_found(client: QuartClient):
    """Test shoutout creation when user doesn't exist"""
    with aioresponses() as mocked:
        mocked.post(
            'https://id.twitch.tv/oauth2/token',
            payload=MOCK_OAUTH_TOKEN
        )
        mocked.get(
            'https://api.twitch.tv/helix/users',
            payload={'data': []}
        )

        response = await client.post(
            '/api/v1/shoutout',
            json={
                'username': 'nonexistent_user',
                'community_id': 123,
                'platform': 'twitch'
            }
        )

        assert response.status_code == 404
        data = await response.get_json()
        assert data['success'] is False
        assert 'not found' in data['error'].lower()
```

## Manual Testing

### Test Text Shoutout Locally

```bash
# Start module
python app.py

# In another terminal, test the endpoint
curl -X POST http://localhost:8011/api/v1/shoutout \
  -H "Content-Type: application/json" \
  -d '{
    "username": "ninja",
    "community_id": 123,
    "platform": "twitch"
  }'
```

### Test with Mock Data

```python
# tests/manual/test_manual.py
"""Manual testing with real-ish data"""
import asyncio
from services.shoutout_service import ShoutoutService

async def test_manual():
    dal = None  # Would normally connect to real database
    service = ShoutoutService(dal)

    # Simulate Twitch API response
    twitch_data = {
        'user': {
            'id': '88888888',
            'login': 'pokimane',
            'display_name': 'Pokimane',
            'description': 'IRL streamer',
            'profile_image_url': 'https://static-cdn.jtvnw.net/...'
        },
        'channel': {
            'id': '88888888',
            'broadcaster_login': 'pokimane',
            'game_id': '12345',
            'game_name': 'World of Warcraft',
            'title': 'Mythic+ Dungeons'
        },
        'stream': {
            'id': 'stream_123456',
            'type': 'live',
            'viewer_count': 5000,
            'started_at': '2026-02-15T10:00:00Z'
        }
    }

    result = await service.generate_shoutout(
        twitch_data,
        community_id=123,
        platform='twitch'
    )

    print(f"Generated shoutout: {result['shoutout_text']}")
    # Expected: "Go check out Pokimane at twitch.tv/pokimane! They're currently streaming World of Warcraft with 5000 viewers!"

asyncio.run(test_manual())
```

## Smoke Tests

```bash
# tests/smoke/test_smoke.py
def test_module_starts():
    """Module should start without errors"""
    from app import app
    assert app is not None

def test_health_endpoint():
    """Health endpoint should be accessible"""
    client = app.test_client()
    response = client.get('/health')
    assert response.status_code == 200

def test_status_endpoint():
    """Status endpoint should return module info"""
    client = app.test_client()
    response = client.get('/api/v1/status')
    assert response.status_code == 200
    data = response.get_json()
    assert data['data']['module'] == 'shoutout_interaction_module'
    assert data['data']['version'] == '2.0.0'
```

## Coverage Requirements

Aim for these coverage targets:

- **Overall:** 80%+
- **Core services:** 90%+
- **API endpoints:** 85%+
- **Utils:** 70%+

Run coverage report:

```bash
pytest --cov=. --cov-report=term-missing
```

## Performance Testing

```python
# tests/performance/test_performance.py
import pytest
import time
from aioresponses import aioresponses

@pytest.mark.asyncio
async def test_shoutout_generation_performance():
    """Shoutout generation should complete in <100ms"""
    service = ShoutoutService(Mock())
    twitch_data = {...}  # Mock data

    start = time.perf_counter()
    result = await service.generate_shoutout(
        twitch_data,
        community_id=123,
        platform='twitch'
    )
    elapsed = time.perf_counter() - start

    assert elapsed < 0.1, f"Generation took {elapsed}s, expected <0.1s"
    assert result['shoutout_text']
```
