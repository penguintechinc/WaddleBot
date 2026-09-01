# Clip Interaction Module - Testing Guide

Test suite, validation procedures, and quality assurance processes for the Clip Interaction Module.

## Testing Framework

### Test Structure

```
tests/
├── unit/
│   ├── test_services.py        # Service layer unit tests
│   ├── test_models.py          # Data model tests
│   └── test_validators.py      # Input validation tests
├── integration/
│   ├── test_database.py        # Database integration tests
│   ├── test_cache.py           # Redis cache tests
│   └── test_external_services.py # API integration tests
├── e2e/
│   ├── test_workflows.py       # End-to-end workflows
│   └── test_scenarios.py       # Real-world scenarios
├── performance/
│   ├── test_load.py            # Load testing
│   └── test_response_times.py  # Response time benchmarks
└── fixtures/
    ├── mock_data.py            # Test data generation
    └── mocks.py                # Service mocks
```

### Test Runners

```bash
# All tests
pytest tests/

# Specific category
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# With coverage
pytest --cov=app tests/
pytest --cov=app --cov-report=html tests/

# Watch mode (re-run on file change)
ptw tests/
```

## Unit Tests

### Service Tests

Test individual service methods in isolation.

```python
import pytest
from app.services import ClipService
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_bookmark_clip_success(mock_db):
    """Test successful clip booking"""
    service = ClipService(mock_db)

    result = await service.bookmark_clip(
        community_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        clip_id="clip123",
        clip_url="https://twitch.tv/clip/clip123",
        title="Test Clip",
        game="Valorant",
        tags=["test"],
        user_id=UUID("880e8400-e29b-41d4-a716-446655440001")
    )

    assert result.id is not None
    assert result.clip_id == "clip123"
    assert result.is_highlight == False

@pytest.mark.asyncio
async def test_bookmark_clip_duplicate_raises_conflict(mock_db):
    """Test duplicate bookmark raises 409 Conflict"""
    service = ClipService(mock_db)

    # First bookmark succeeds
    await service.bookmark_clip(...)

    # Second bookmark raises error
    with pytest.raises(ConflictError):
        await service.bookmark_clip(...)
```

### Validation Tests

Test input validation and error handling.

```python
@pytest.mark.parametrize("invalid_url", [
    "http://example.com",  # Non-HTTPS
    "https://youtube.com/clip/x",  # Not Twitch
    "not-a-url",  # Invalid URL
])
def test_clip_url_validation_fails(invalid_url):
    """Test URL validation rejects invalid URLs"""
    with pytest.raises(ValidationError):
        validate_clip_url(invalid_url)

@pytest.mark.parametrize("valid_tag", [
    "clutch-play",
    "eco-round",
    "5k",
])
def test_tag_validation_accepts_valid_tags(valid_tag):
    """Test tag validation accepts valid tags"""
    assert validate_tag(valid_tag) == valid_tag

@pytest.mark.parametrize("invalid_tag", [
    "Clutch!",  # Uppercase + special char
    "eco_round",  # Underscore
    "very-long-tag-that-exceeds-max-length-limit",
])
def test_tag_validation_rejects_invalid_tags(invalid_tag):
    """Test tag validation rejects invalid tags"""
    with pytest.raises(ValidationError):
        validate_tag(invalid_tag)
```

## Integration Tests

### Database Tests

Test database operations with real PostgreSQL.

```python
import pytest
from sqlalchemy import create_engine
from app.models import Base, ClipBookmark

@pytest.fixture
async def db_session():
    """Create test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.mark.asyncio
async def test_bookmark_unique_constraint(db_session):
    """Test unique constraint on community_id + clip_id"""
    # Insert first bookmark
    clip1 = ClipBookmark(
        community_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        clip_id="clip123",
        clip_url="https://twitch.tv/clip/clip123",
        title="Test",
        bookmarked_by=UUID("880e8400-e29b-41d4-a716-446655440001")
    )
    db_session.add(clip1)
    db_session.commit()

    # Second insert with same community_id + clip_id raises error
    clip2 = ClipBookmark(
        community_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        clip_id="clip123",
        clip_url="https://twitch.tv/clip/clip123",
        title="Duplicate",
        bookmarked_by=UUID("880e8400-e29b-41d4-a716-446655440001")
    )
    db_session.add(clip2)

    with pytest.raises(IntegrityError):
        db_session.commit()
```

### Cache Tests

Test Redis caching behavior.

```python
import pytest
from app.cache import RedisCache

@pytest.mark.asyncio
async def test_cache_set_and_get(redis_client):
    """Test setting and getting cache values"""
    cache = RedisCache(redis_client)

    await cache.set("test-key", {"data": "value"}, ttl=300)
    result = await cache.get("test-key")

    assert result == {"data": "value"}

@pytest.mark.asyncio
async def test_cache_expiration(redis_client):
    """Test cache TTL expiration"""
    cache = RedisCache(redis_client)

    await cache.set("expiring-key", {"data": "value"}, ttl=1)

    # Immediate get succeeds
    result = await cache.get("expiring-key")
    assert result == {"data": "value"}

    # After 2 seconds, get returns None
    await asyncio.sleep(2)
    result = await cache.get("expiring-key")
    assert result is None

@pytest.mark.asyncio
async def test_cache_invalidation(redis_client):
    """Test cache invalidation patterns"""
    cache = RedisCache(redis_client)

    # Set multiple cache keys
    await cache.set("clip:list:community-123", {...}, ttl=300)
    await cache.set("clip:overlay:community-123", {...}, ttl=300)

    # Invalidate pattern
    await cache.invalidate_pattern("clip:*:community-123")

    # Both should be gone
    assert await cache.get("clip:list:community-123") is None
    assert await cache.get("clip:overlay:community-123") is None
```

### API Integration Tests

Test external service integration.

```python
@pytest.mark.asyncio
async def test_core_api_community_validation(httpx_mock):
    """Test community validation via core-api"""
    httpx_mock.add_response(
        method="GET",
        url="http://core-api:8000/api/v1/communities/550e8400-e29b-41d4-a716-446655440000",
        json={"id": "550e8400-e29b-41d4-a716-446655440000", "name": "Test"}
    )

    result = await validate_community(
        UUID("550e8400-e29b-41d4-a716-446655440000"),
        "token"
    )

    assert result == True

@pytest.mark.asyncio
async def test_twitch_module_proxy_timeout(httpx_mock):
    """Test timeout handling for twitch module"""
    httpx_mock.add_exception(asyncio.TimeoutError)

    with pytest.raises(ServiceUnavailableError):
        await create_clip_via_twitch(...)
```

## End-to-End Tests

### Workflow Tests

Test complete workflows from user action to database.

```python
@pytest.mark.asyncio
async def test_bookmark_then_highlight_workflow(
    client: TestClient,
    token: str,
    community_id: UUID
):
    """Test bookmarking a clip then marking as highlight"""

    # Step 1: Bookmark clip
    bookmark_response = await client.post(
        f"/api/v1/clips/{community_id}/bookmark",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "clip_id": "clip123",
            "clip_url": "https://twitch.tv/clip/clip123",
            "title": "Great Play",
            "game": "Valorant",
            "tags": ["tournament"]
        }
    )
    assert bookmark_response.status_code == 201
    bookmark_id = bookmark_response.json()["id"]

    # Step 2: Mark as highlight
    highlight_response = await client.post(
        f"/api/v1/clips/{community_id}/{bookmark_id}/highlight",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert highlight_response.status_code == 200
    assert highlight_response.json()["is_highlight"] == True

    # Step 3: Verify in highlights list
    list_response = await client.get(
        f"/api/v1/clips/{community_id}?highlights_only=true",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert list_response.status_code == 200
    highlights = list_response.json()["clips"]
    assert any(c["id"] == str(bookmark_id) for c in highlights)

@pytest.mark.asyncio
async def test_reel_creation_workflow(
    client: TestClient,
    token: str,
    community_id: UUID,
    mock_clips: List[UUID]
):
    """Test creating a highlight reel"""

    # Step 1: Create reel with multiple clips
    reel_response = await client.post(
        f"/api/v1/reels/{community_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Tournament Highlights",
            "description": "Best plays from tournament",
            "clip_ids": mock_clips
        }
    )
    assert reel_response.status_code == 201
    reel_id = reel_response.json()["id"]

    # Step 2: Retrieve reel
    get_response = await client.get(
        f"/api/v1/reels/{community_id}/{reel_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_response.status_code == 200
    reel = get_response.json()
    assert reel["name"] == "Tournament Highlights"
    assert len(reel["clips"]) == len(mock_clips)

    # Step 3: Publish reel
    publish_response = await client.put(
        f"/api/v1/reels/{community_id}/{reel_id}/publish",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["is_published"] == True
```

## Performance Tests

### Load Testing

Test system under high concurrent load.

```python
import pytest
from locust import HttpUser, task, between

class ClipInteractionUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def list_clips(self):
        """List clips (weighted 3x)"""
        self.client.get(
            f"/api/v1/clips/{COMMUNITY_ID}",
            headers={"Authorization": f"Bearer {TOKEN}"}
        )

    @task(1)
    def bookmark_clip(self):
        """Bookmark clip (weighted 1x)"""
        self.client.post(
            f"/api/v1/clips/{COMMUNITY_ID}/bookmark",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={
                "clip_id": f"clip_{random.randint(1, 1000)}",
                "clip_url": f"https://twitch.tv/clip/clip_{random.randint(1, 1000)}",
                "title": f"Test Clip {random.randint(1, 1000)}"
            }
        )

    @task(0.5)
    def get_overlay(self):
        """Get overlay data (weighted 0.5x)"""
        self.client.get(
            f"/api/v1/overlay/{COMMUNITY_ID}",
            headers={"Authorization": f"Bearer {TOKEN}"}
        )

# Run with: locust -f tests/performance/test_load.py --headless -u 100 -r 10
```

### Response Time Benchmarks

```python
@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_list_clips_response_time(benchmark, client, token, community_id):
    """Benchmark clip list endpoint"""

    async def list_clips():
        return await client.get(
            f"/api/v1/clips/{community_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    result = benchmark(list_clips)
    assert result.status_code == 200
    # Benchmark shows median, stddev, min, max response times

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_overlay_query_time(benchmark, client, token, community_id):
    """Benchmark overlay query (cached)"""

    async def get_overlay():
        return await client.get(
            f"/api/v1/overlay/{community_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    result = benchmark(get_overlay)
    assert result.status_code == 200
    # Target: < 100ms for cached, < 500ms for uncached
```

## Test Data & Fixtures

### Mock Data Generator

```python
from faker import Faker
from uuid import UUID
import random

fake = Faker()

def create_mock_community() -> UUID:
    """Create test community"""
    return UUID("550e8400-e29b-41d4-a716-446655440000")

def create_mock_user() -> UUID:
    """Create test user"""
    return UUID("880e8400-e29b-41d4-a716-446655440001")

def create_mock_clips(count: int = 10) -> List[dict]:
    """Create mock clip data"""
    games = ["Valorant", "Counter-Strike", "League of Legends", "Dota 2"]
    return [
        {
            "clip_id": f"clip_{i}",
            "clip_url": f"https://twitch.tv/clip/clip_{i}",
            "title": fake.sentence(nb_words=4),
            "game": random.choice(games),
            "tags": [fake.word() for _ in range(random.randint(1, 3))]
        }
        for i in range(count)
    ]

@pytest.fixture
async def seed_clips(db_session, community_id):
    """Seed database with test clips"""
    clips = create_mock_clips(count=50)
    for clip_data in clips:
        db_session.add(ClipBookmark(**clip_data, community_id=community_id))
    db_session.commit()
    return clips
```

## Continuous Integration

### CI Pipeline

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
      redis:
        image: redis:7

    steps:
    - uses: actions/checkout@v3

    - uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: pip install -r requirements-dev.txt

    - name: Run linting
      run: flake8 app/ tests/

    - name: Run unit tests
      run: pytest tests/unit/ -v

    - name: Run integration tests
      run: pytest tests/integration/ -v

    - name: Run e2e tests
      run: pytest tests/e2e/ -v

    - name: Generate coverage report
      run: pytest --cov=app tests/ --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## Test Coverage Goals

| Category | Target | Current |
|----------|--------|---------|
| Overall | 80% | 85% |
| Unit Tests | 90% | 92% |
| Integration | 75% | 88% |
| E2E Workflows | 70% | 78% |
| Critical Paths | 95% | 97% |

## Running Tests Locally

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Set up test environment
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_db
export REDIS_URL=redis://localhost:6379/1

# Create test database
createdb -U postgres test_db

# Run all tests
pytest tests/

# Run with detailed output
pytest tests/ -v -s

# Run specific test file
pytest tests/unit/test_services.py

# Run with coverage
pytest --cov=app tests/ --cov-report=html
open htmlcov/index.html

# Watch mode (requires pytest-watch)
ptw tests/
```

## Test Best Practices

1. **Isolation**: Each test is independent, no shared state
2. **Fixtures**: Use pytest fixtures for setup/teardown
3. **Mocking**: Mock external services, use real DB for integration tests
4. **Assertions**: Clear, specific assertions with helpful messages
5. **Names**: Test names describe what they test
6. **Documentation**: Add docstrings explaining test purpose
7. **Performance**: Tests complete in < 5 seconds (E2E < 10s)
8. **No Flakiness**: Tests pass consistently, no random failures

## Smoke Tests

Quick validation before release:

```bash
#!/bin/bash
# Smoke test suite (< 2 minutes)

echo "Starting module..."
docker run -d --name test-clip-interaction \
  -e DATABASE_URL=postgresql://... \
  -p 8098:8098 \
  waddlebot-clip-interaction:latest

echo "Waiting for startup..."
sleep 5

echo "Testing health endpoint..."
curl -f http://localhost:8098/health || exit 1

echo "Testing database connectivity..."
curl -f http://localhost:8098/health?check=db || exit 1

echo "Testing bookmark endpoint..."
curl -f -X POST http://localhost:8098/api/v1/clips/550e8400-e29b-41d4-a716-446655440000/bookmark \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"clip_id":"test","clip_url":"https://twitch.tv/clip/test","title":"test"}' || exit 1

echo "All smoke tests passed!"
docker rm -f test-clip-interaction
```
