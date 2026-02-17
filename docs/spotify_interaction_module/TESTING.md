# Spotify Interaction Module — Testing Guide

> Test strategy, OAuth token mocking, playlist and track fixtures, and
> instructions for running the test suite.

---

## Testing Overview

The Spotify Interaction Module uses two complementary testing approaches:

| Approach | Tool | Location | Purpose |
|---|---|---|---|
| Unit/integration tests | pytest + pytest-asyncio | (module dir) | OAuth service logic, token lifecycle |
| API endpoint tests | Bash (test-api.sh) | `test-api.sh` | HTTP endpoint validation |

The `requirements.txt` includes:
- `pytest>=7.4.0`
- `pytest-asyncio>=0.23.0`
- `pytest-cov>=4.1.0`

---

## Running the pytest Suite

### Install Dependencies

```bash
# From the repo root, install the shared library
pip install -e libs/flask_core

# Install module test dependencies
pip install -r action/interactive/spotify_interaction_module/requirements.txt
```

### Run All Tests

```bash
cd action/interactive/spotify_interaction_module
pytest -v
```

### Run with Coverage

```bash
pytest --cov=. --cov-report=term-missing --cov-report=html:htmlcov -v
```

### Run a Specific Test File

```bash
pytest tests/test_oauth_service.py -v
```

### Run with Asyncio Mode

pytest-asyncio must be configured for async test functions. Add to `pytest.ini`
or `pyproject.toml`:

```ini
[pytest]
asyncio_mode = auto
```

Or use the `@pytest.mark.asyncio` decorator on individual async tests.

---

## Running the API Test Script

The `test-api.sh` script tests the running HTTP service. It requires curl and jq.

```bash
# Start the service first
export SPOTIFY_CLIENT_ID=test_client_id
export SPOTIFY_CLIENT_SECRET=test_client_secret
export SPOTIFY_REDIRECT_URI=http://localhost:8026/spotify/auth/callback
export DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
export SECRET_KEY=test-secret

cd action/interactive/spotify_interaction_module
python -m hypercorn app:app --bind 0.0.0.0:8026 &

# Wait for startup
sleep 2

# Run the test suite
./test-api.sh --verbose

# Or against a Docker container
./test-api.sh --url http://localhost:8026

# With API key authentication
./test-api.sh --api-key your-test-api-key
```

---

## Mocking OAuth Tokens

### Test Fixtures for music_oauth_tokens

Use a test PostgreSQL database (or SQLite for unit tests with PyDAL) and insert
token fixtures directly:

```python
import pytest
from datetime import datetime, timedelta

@pytest.fixture
def mock_valid_token(test_db):
    """Insert a valid (non-expired) Spotify token for community 1."""
    expires_at = datetime.utcnow() + timedelta(hours=1)
    test_db.executesql(
        """INSERT INTO music_oauth_tokens
           (community_id, platform, access_token, refresh_token,
            token_type, expires_at, scope, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (community_id, platform) DO UPDATE
           SET access_token = EXCLUDED.access_token,
               expires_at = EXCLUDED.expires_at""",
        [
            1,                              # community_id
            'spotify',                      # platform
            'BQA_mock_access_token_1234',   # access_token
            'AQA_mock_refresh_token_5678',  # refresh_token
            'Bearer',                       # token_type
            expires_at,                     # expires_at
            'user-read-playback-state user-modify-playback-state',  # scope
            datetime.utcnow(),             # created_at
            datetime.utcnow(),             # updated_at
        ]
    )
    return 'BQA_mock_access_token_1234'


@pytest.fixture
def mock_expired_token(test_db):
    """Insert an expired Spotify token for community 2."""
    expires_at = datetime.utcnow() - timedelta(hours=1)  # already expired
    test_db.executesql(
        """INSERT INTO music_oauth_tokens
           (community_id, platform, access_token, refresh_token,
            token_type, expires_at, scope, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (community_id, platform) DO UPDATE
           SET access_token = EXCLUDED.access_token,
               expires_at = EXCLUDED.expires_at""",
        [
            2,
            'spotify',
            'BQA_expired_access_token',
            'AQA_expired_refresh_token',
            'Bearer',
            expires_at,
            'user-read-playback-state',
            datetime.utcnow(),
            datetime.utcnow(),
        ]
    )


@pytest.fixture
def mock_near_expiry_token(test_db):
    """Insert a token expiring in 3 minutes (within the 5-minute refresh buffer)."""
    expires_at = datetime.utcnow() + timedelta(minutes=3)
    test_db.executesql(
        """INSERT INTO music_oauth_tokens
           (community_id, platform, access_token, refresh_token,
            token_type, expires_at, scope, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (community_id, platform) DO UPDATE
           SET access_token = EXCLUDED.access_token,
               expires_at = EXCLUDED.expires_at""",
        [
            3,
            'spotify',
            'BQA_near_expiry_token',
            'AQA_near_expiry_refresh',
            'Bearer',
            expires_at,
            'user-read-playback-state',
            datetime.utcnow(),
            datetime.utcnow(),
        ]
    )
```

---

## Mocking the Spotify API (aiohttp)

All calls to `https://accounts.spotify.com/api/token` use `aiohttp.ClientSession`.
Use `pytest-aiohttp` or `aioresponses` to mock these:

```bash
pip install aioresponses
```

### Token Exchange Mock

```python
import pytest
from aioresponses import aioresponses
from services.oauth_service import SpotifyOAuthService

@pytest.fixture
def mock_dal(mocker):
    dal = mocker.MagicMock()
    return dal

@pytest.fixture
def oauth_service(mock_dal):
    return SpotifyOAuthService(
        dal=mock_dal,
        client_id='test_client_id',
        client_secret='test_client_secret',
        redirect_uri='http://localhost:8026/spotify/auth/callback'
    )

@pytest.mark.asyncio
async def test_exchange_code_for_token_success(oauth_service, mock_dal):
    """exchange_code_for_token stores token and returns token data."""
    token_response = {
        'access_token': 'BQA_new_access_token',
        'refresh_token': 'AQA_new_refresh_token',
        'expires_in': 3600,
        'token_type': 'Bearer',
        'scope': 'user-read-playback-state user-modify-playback-state'
    }

    with aioresponses() as m:
        m.post(
            'https://accounts.spotify.com/api/token',
            payload=token_response,
            status=200
        )
        result = await oauth_service.exchange_code_for_token(
            code='auth_code_xyz',
            community_id=1
        )

    assert result['access_token'] == 'BQA_new_access_token'
    assert result['refresh_token'] == 'AQA_new_refresh_token'
    # Verify _store_token was called (executesql called on dal)
    mock_dal.executesql.assert_called_once()


@pytest.mark.asyncio
async def test_exchange_code_for_token_spotify_error(oauth_service):
    """exchange_code_for_token raises on Spotify 400 response."""
    with aioresponses() as m:
        m.post(
            'https://accounts.spotify.com/api/token',
            payload={'error': 'invalid_grant'},
            status=400
        )
        with pytest.raises(Exception) as exc_info:
            await oauth_service.exchange_code_for_token(
                code='bad_code',
                community_id=1
            )
    assert 'Token exchange failed: 400' in str(exc_info.value)
```

### Token Refresh Mock

```python
@pytest.mark.asyncio
async def test_refresh_token_success(oauth_service, mock_dal):
    """refresh_token uses stored refresh_token and updates DB."""
    # Mock DB returning an existing refresh token
    mock_dal.executesql.side_effect = [
        [('AQA_stored_refresh_token',)],  # SELECT refresh_token
        None                               # INSERT/UPDATE (store_token)
    ]

    refresh_response = {
        'access_token': 'BQA_refreshed_access_token',
        'expires_in': 3600,
        'token_type': 'Bearer',
        'scope': 'user-read-playback-state'
        # Note: no refresh_token in response (Spotify may omit it)
    }

    with aioresponses() as m:
        m.post(
            'https://accounts.spotify.com/api/token',
            payload=refresh_response,
            status=200
        )
        result = await oauth_service.refresh_token(community_id=1)

    assert result['access_token'] == 'BQA_refreshed_access_token'
    # Original refresh token preserved when not in response
    assert result['refresh_token'] == 'AQA_stored_refresh_token'


@pytest.mark.asyncio
async def test_refresh_token_no_stored_token(oauth_service, mock_dal):
    """refresh_token raises when no refresh token in DB."""
    mock_dal.executesql.return_value = []  # No rows

    with pytest.raises(Exception) as exc_info:
        await oauth_service.refresh_token(community_id=99)
    assert 'No refresh token found' in str(exc_info.value)
```

---

## Track and Playlist Fixtures

Use these fixtures for testing endpoints that consume Spotify track/playlist data:

### Track Fixture

```python
MOCK_TRACK = {
    'id': '4iV5W9uYEdYUVa79Axb7Rh',
    'name': 'Never Gonna Give You Up',
    'uri': 'spotify:track:4iV5W9uYEdYUVa79Axb7Rh',
    'duration_ms': 213573,
    'artists': [{'name': 'Rick Astley', 'id': '0gxyHStUsqpMadRV0Di1Qt'}],
    'album': {
        'name': 'Whenever You Need Somebody',
        'images': [{'url': 'https://i.scdn.co/image/ab67616d0000b273', 'height': 640}]
    },
    'preview_url': 'https://p.scdn.co/mp3-preview/abc123',
    'external_urls': {'spotify': 'https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh'}
}

MOCK_TRACK_2 = {
    'id': '7qiZfU4dY1lWllzX7mPBI3',
    'name': 'Shape of You',
    'uri': 'spotify:track:7qiZfU4dY1lWllzX7mPBI3',
    'duration_ms': 233713,
    'artists': [{'name': 'Ed Sheeran', 'id': '6eUKZXaKkcviH0Ku9w2n3V'}],
    'album': {
        'name': 'Divide',
        'images': [{'url': 'https://i.scdn.co/image/ab67616d0000b273ed', 'height': 640}]
    },
    'preview_url': 'https://p.scdn.co/mp3-preview/def456',
    'external_urls': {'spotify': 'https://open.spotify.com/track/7qiZfU4dY1lWllzX7mPBI3'}
}

MOCK_SEARCH_RESPONSE = {
    'tracks': {
        'items': [MOCK_TRACK, MOCK_TRACK_2],
        'total': 2,
        'limit': 10,
        'offset': 0
    }
}
```

### Playlist Fixture

```python
MOCK_PLAYLIST = {
    'id': '37i9dQZF1DXcBWIGoYBM5M',
    'name': 'Today's Top Hits',
    'description': 'Ariana Grande is on top of the Hottest 50!',
    'public': True,
    'collaborative': False,
    'tracks': {
        'total': 50,
        'items': [
            {
                'track': MOCK_TRACK,
                'added_at': '2026-02-16T00:00:00Z',
                'added_by': {'id': 'spotify_user_123'}
            }
        ]
    },
    'external_urls': {'spotify': 'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M'},
    'owner': {'display_name': 'Spotify', 'id': 'spotify'}
}

MOCK_USER_PLAYLISTS = {
    'items': [MOCK_PLAYLIST],
    'total': 1,
    'limit': 20,
    'offset': 0
}
```

### Now Playing Fixture

```python
MOCK_NOW_PLAYING = {
    'is_playing': True,
    'progress_ms': 45000,
    'item': MOCK_TRACK,
    'currently_playing_type': 'track',
    'timestamp': 1739750400000
}
```

---

## get_valid_token Unit Tests

```python
@pytest.mark.asyncio
async def test_get_valid_token_valid_unexpired(oauth_service, mock_dal):
    """get_valid_token returns token directly when not near expiry."""
    from datetime import datetime, timedelta
    expires_at = datetime.utcnow() + timedelta(hours=1)  # 1 hour away
    mock_dal.executesql.return_value = [('BQA_valid_token', expires_at)]

    result = await oauth_service.get_valid_token(community_id=1)
    assert result == 'BQA_valid_token'


@pytest.mark.asyncio
async def test_get_valid_token_near_expiry_triggers_refresh(oauth_service, mock_dal):
    """get_valid_token triggers refresh when token is within 5 minutes of expiry."""
    from datetime import datetime, timedelta
    expires_at = datetime.utcnow() + timedelta(minutes=3)  # within 5-min buffer

    # First call: get token and expiry
    # Second call: get refresh token (in refresh_token method)
    # Third call: store updated token
    mock_dal.executesql.side_effect = [
        [('BQA_near_expiry', expires_at)],
        [('AQA_refresh_token',)],
        None  # store_token upsert
    ]

    with aioresponses() as m:
        m.post(
            'https://accounts.spotify.com/api/token',
            payload={'access_token': 'BQA_fresh', 'expires_in': 3600,
                     'token_type': 'Bearer', 'scope': 'user-read-playback-state'},
            status=200
        )
        result = await oauth_service.get_valid_token(community_id=3)

    assert result == 'BQA_fresh'


@pytest.mark.asyncio
async def test_get_valid_token_no_token(oauth_service, mock_dal):
    """get_valid_token returns None when no token record exists."""
    mock_dal.executesql.return_value = []  # No rows

    result = await oauth_service.get_valid_token(community_id=99)
    assert result is None
```

---

## is_authenticated Unit Tests

```python
@pytest.mark.asyncio
async def test_is_authenticated_true(oauth_service, mock_dal):
    """is_authenticated returns True when get_valid_token returns a token."""
    from datetime import datetime, timedelta
    expires_at = datetime.utcnow() + timedelta(hours=1)
    mock_dal.executesql.return_value = [('BQA_valid', expires_at)]

    result = await oauth_service.is_authenticated(community_id=1)
    assert result is True


@pytest.mark.asyncio
async def test_is_authenticated_false(oauth_service, mock_dal):
    """is_authenticated returns False when no token is found."""
    mock_dal.executesql.return_value = []

    result = await oauth_service.is_authenticated(community_id=99)
    assert result is False
```

---

## revoke_token Unit Tests

```python
@pytest.mark.asyncio
async def test_revoke_token_success(oauth_service, mock_dal):
    """revoke_token executes DELETE and returns True."""
    mock_dal.executesql.return_value = None

    result = await oauth_service.revoke_token(community_id=1)
    assert result is True
    mock_dal.executesql.assert_called_once()
    # Verify the SQL includes DELETE and community_id
    call_args = mock_dal.executesql.call_args
    assert 'DELETE FROM music_oauth_tokens' in call_args[0][0]
    assert 1 in call_args[0][1]


@pytest.mark.asyncio
async def test_revoke_token_db_error(oauth_service, mock_dal):
    """revoke_token returns False on database exception."""
    mock_dal.executesql.side_effect = Exception('DB connection lost')

    result = await oauth_service.revoke_token(community_id=1)
    assert result is False
```

---

## API Endpoint Tests (test-api.sh)

The bash script `test-api.sh` covers these scenarios:

| Test | Validation |
|---|---|
| GET /health | status=healthy, module field, version field |
| GET /healthz | status=healthy, checks map present |
| GET /metrics | Response non-empty, contains metric lines |
| GET /api/v1/status | data.status=operational, data.module present |
| GET /api/v1/nonexistent | HTTP 404 |
| DELETE /api/v1/status | HTTP 405 method not allowed |

Environment variables for the script:

```bash
SPOTIFY_URL=http://localhost:8026   # Base URL
SPOTIFY_API_KEY=                    # API key (optional)
VERBOSE=false                       # Enable verbose request/response logging
```

---

## CI Integration

Add to your CI pipeline after building the Docker image:

```bash
# Start the container
docker run -d --name spotify-test \
  -p 8026:8026 \
  -e DATABASE_URL=postgresql://test:test@host.docker.internal:5432/waddlebot_test \
  -e SPOTIFY_CLIENT_ID=test_id \
  -e SPOTIFY_CLIENT_SECRET=test_secret \
  -e SPOTIFY_REDIRECT_URI=http://localhost:8026/spotify/auth/callback \
  -e SECRET_KEY=ci-test-secret \
  waddlebot/spotify-interaction:latest

# Wait for startup
sleep 3

# Run API tests
./action/interactive/spotify_interaction_module/test-api.sh --url http://localhost:8026

# Cleanup
docker stop spotify-test && docker rm spotify-test
```
