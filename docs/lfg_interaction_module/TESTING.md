# LFG Interaction Module - Testing Guide

## Testing Strategy

The LFG Interaction Module uses a comprehensive testing approach covering unit, integration, and end-to-end tests. All tests must pass before code commits.

### Test Categories

| Category | Framework | Scope | Speed | Location |
|----------|-----------|-------|-------|----------|
| **Unit** | pytest | Individual functions, services | Fast | `tests/unit/` |
| **Integration** | pytest + fixtures | Service + database interactions | Medium | `tests/integration/` |
| **Functional** | pytest + test client | API endpoints, request/response | Medium | `tests/functional/` |
| **E2E** | pytest + docker-compose | Full system workflows | Slow | `tests/e2e/` |
| **Load** | locust | Performance under sustained load | Very Slow | `tests/load/` |
| **Smoke** | pytest (subset) | Quick sanity checks | Very Fast | `tests/smoke/` |

---

## Quick Start: Running Tests

### Run All Tests
```bash
make test
# or
pytest tests/ -v
```

### Run Specific Category
```bash
make test-unit           # Unit tests only
make test-integration    # Integration tests
make test-functional     # API endpoint tests
make test-e2e            # Full workflow tests
make test-smoke          # Quick sanity checks (< 2 min)
make test-load           # Performance/load tests
```

### Run Specific Test File
```bash
pytest tests/unit/test_lfg_service.py -v
pytest tests/functional/test_create_post_api.py::test_create_post_success -v
```

### Run with Coverage
```bash
pytest --cov=src --cov-report=html tests/
# Open htmlcov/index.html in browser
```

---

## Unit Tests

### Purpose
Test individual functions and service methods in isolation with mocked dependencies.

### Running Unit Tests
```bash
make test-unit
# or
pytest tests/unit/ -v
```

### Mock Data
```python
# tests/unit/conftest.py - Shared fixtures

@pytest.fixture
def sample_post_payload():
    return {
        "community_id": "community-uuid",
        "user_id": "user-uuid",
        "platform": "discord",
        "game": "Valorant",
        "activity": "ranked",
        "role": "DPS",
        "rank_or_level": "Radiant",
        "player_count_needed": 3,
        "message": "LFG for ranked matches"
    }

@pytest.fixture
def mock_database(mocker):
    db = mocker.Mock()
    db.insert = mocker.Mock(return_value="post-uuid")
    db.query = mocker.Mock()
    return db
```

### Example Unit Test
```python
# tests/unit/test_lfg_service.py

from lfg_service import LfgService
from datetime import datetime, timedelta

def test_create_post_success(sample_post_payload, mock_database, mocker):
    """Test successful post creation"""
    service = LfgService(db=mock_database)

    result = service.create_post(sample_post_payload)

    assert result['status'] == 'open'
    assert result['current_player_count'] == 1
    assert result['player_count_needed'] == 3
    mock_database.insert.assert_called_once()

def test_create_post_max_posts_exceeded(mocker):
    """Test user cannot exceed 3 active posts"""
    mock_db = mocker.Mock()
    mock_db.query().filter_by().count.return_value = 3

    service = LfgService(db=mock_db)

    with pytest.raises(ValueError, match="max active posts"):
        service.create_post({"user_id": "user-uuid", ...})

def test_join_post_fills_group():
    """Test auto-fill detection when enough players join"""
    mock_db = mocker.Mock()
    post = {
        'id': 'post-uuid',
        'player_count_needed': 2,
        'status': 'open'
    }

    # Simulate 2 joins
    service = LfgService(db=mock_db)
    service.join_post('post-uuid', 'user-1', 'discord', 'User1')
    service.join_post('post-uuid', 'user-2', 'discord', 'User2')

    # Should detect filled and update status
    assert post['status'] == 'filled'

def test_leave_post_reverts_filled_status():
    """Test reverting status from filled to open when player leaves"""
    service = LfgService(db=mock_db)

    # Setup: 3-person group, all slots filled
    service.join_post('post-uuid', 'user-1', 'discord', 'User1')
    service.join_post('post-uuid', 'user-2', 'discord', 'User2')
    service.join_post('post-uuid', 'user-3', 'discord', 'User3')
    assert post['status'] == 'filled'

    # User leaves
    service.leave_post('post-uuid', 'user-2')

    # Should revert to open
    assert post['status'] == 'open'
    assert len(service.get_post_joins('post-uuid')) == 2
```

### Unit Test Checklist
- [ ] Service methods tested with valid inputs
- [ ] Error cases handled (validation, limits)
- [ ] Database calls mocked
- [ ] Edge cases covered (empty lists, null values)
- [ ] 80%+ code coverage

---

## Integration Tests

### Purpose
Test service layer interactions with real (test) PostgreSQL database and Redis.

### Running Integration Tests
```bash
make test-integration
# Requires: docker-compose up infra-postgres redis
```

### Setup (Docker Compose)
```bash
# Start test services
docker-compose -f docker-compose.test.yml up -d

# Run tests
pytest tests/integration/ -v

# Cleanup
docker-compose -f docker-compose.test.yml down
```

### Example Integration Test
```python
# tests/integration/test_lfg_service_db.py

import pytest
from lfg_service import LfgService
from sqlalchemy import create_engine

@pytest.fixture
def test_db():
    """Create fresh test database"""
    engine = create_engine("postgresql://test:test@localhost:5432/test_lfg")
    # Create tables
    Base.metadata.create_all(engine)
    yield engine
    # Cleanup
    Base.metadata.drop_all(engine)

def test_create_and_list_posts(test_db):
    """Test creating posts and listing them"""
    service = LfgService(db=test_db)

    # Create post
    post_id = service.create_post({
        "community_id": "community-123",
        "user_id": "user-123",
        "platform": "discord",
        "game": "Valorant",
        "activity": "ranked",
        "role": "DPS",
        "rank_or_level": "Radiant",
        "player_count_needed": 3,
        "message": "LFG for ranked"
    })

    assert post_id is not None

    # List posts
    posts = service.list_posts(
        community_id="community-123",
        status="open"
    )

    assert len(posts) == 1
    assert posts[0]['game'] == 'Valorant'
    assert posts[0]['status'] == 'open'

def test_join_then_leave(test_db):
    """Test full join/leave cycle"""
    service = LfgService(db=test_db)

    # Create post
    post_id = service.create_post({...})

    # User joins
    service.join_post(post_id, "user-2", "discord", "User2")
    post = service.get_post(post_id)
    assert post['current_player_count'] == 2

    # User leaves
    service.leave_post(post_id, "user-2")
    post = service.get_post(post_id)
    assert post['current_player_count'] == 1

def test_unique_join_constraint(test_db):
    """Test that user can't join same post twice"""
    service = LfgService(db=test_db)

    post_id = service.create_post({...})

    service.join_post(post_id, "user-2", "discord", "User2")

    # Second join should fail
    with pytest.raises(IntegrityError):
        service.join_post(post_id, "user-2", "discord", "User2")

def test_expire_old_posts(test_db, freezegun):
    """Test background expiry job"""
    service = LfgService(db=test_db)

    # Create post expiring in 10 minutes
    service.create_post({...}, expires_in_minutes=10)

    # Fast-forward time by 15 minutes
    with freezegun.freeze_time() as frozen_time:
        frozen_time.move_to(datetime.now() + timedelta(minutes=15))

        expired_count = service.expire_posts()

    assert expired_count == 1
    post = service.get_post(post_id)
    assert post['status'] == 'expired'
```

### Integration Test Checklist
- [ ] Real database used (test instance)
- [ ] Transactions and isolation tested
- [ ] Constraints verified (unique, foreign keys)
- [ ] Data persistence validated
- [ ] Cleanup between tests (fixture teardown)

---

## Functional/API Tests

### Purpose
Test HTTP API endpoints and request/response handling.

### Running Functional Tests
```bash
make test-functional
# Requires: docker-compose up
```

### Example Functional Test
```python
# tests/functional/test_lfg_api.py

import pytest
from quart.testing import QuartClient

@pytest.fixture
async def client(app):
    """Quart test client"""
    async with app.test_client() as c:
        yield c

@pytest.mark.asyncio
async def test_create_post_endpoint(client, auth_header):
    """Test POST /api/v1/lfg/posts"""
    response = await client.post(
        '/api/v1/lfg/posts',
        json={
            "community_id": "community-uuid",
            "user_id": "user-uuid",
            "platform": "discord",
            "game": "Valorant",
            "activity": "ranked",
            "role": "DPS",
            "rank_or_level": "Radiant",
            "player_count_needed": 3,
            "message": "Looking for ranked team"
        },
        headers=auth_header
    )

    assert response.status_code == 201
    data = await response.get_json()
    assert data['status'] == 'success'
    assert data['data']['status'] == 'open'
    assert 'id' in data['data']

@pytest.mark.asyncio
async def test_list_posts_endpoint(client, auth_header):
    """Test GET /api/v1/lfg/posts/{community_id}"""
    response = await client.get(
        '/api/v1/lfg/posts/community-uuid',
        headers=auth_header
    )

    assert response.status_code == 200
    data = await response.get_json()
    assert 'posts' in data['data']
    assert 'total' in data['data']

@pytest.mark.asyncio
async def test_join_post_endpoint(client, auth_header):
    """Test POST /api/v1/lfg/posts/{post_id}/join"""
    # First create a post
    create_response = await client.post('/api/v1/lfg/posts', json={...})
    post_id = (await create_response.get_json())['data']['id']

    # Join it
    response = await client.post(
        f'/api/v1/lfg/posts/{post_id}/join',
        json={
            "user_id": "user-2",
            "platform": "discord",
            "display_name": "User2#1234"
        },
        headers=auth_header
    )

    assert response.status_code == 200
    data = await response.get_json()
    assert data['data']['current_player_count'] == 2

@pytest.mark.asyncio
async def test_error_max_posts_exceeded(client, auth_header):
    """Test 409 error when user exceeds max posts"""
    # Create 3 posts
    for i in range(3):
        await client.post('/api/v1/lfg/posts', json={...}, headers=auth_header)

    # 4th should fail
    response = await client.post(
        '/api/v1/lfg/posts',
        json={...},
        headers=auth_header
    )

    assert response.status_code == 409
    data = await response.get_json()
    assert data['error'] == 'MAX_POSTS_EXCEEDED'

@pytest.mark.asyncio
async def test_error_unauthorized_cancel(client, auth_header, other_user_header):
    """Test 401 when non-creator tries to cancel post"""
    # User 1 creates post
    response = await client.post('/api/v1/lfg/posts', json={...}, headers=auth_header)
    post_id = (await response.get_json())['data']['id']

    # User 2 tries to cancel
    response = await client.delete(
        f'/api/v1/lfg/posts/{post_id}',
        json={"user_id": "other-user"},
        headers=other_user_header
    )

    assert response.status_code == 401
    data = await response.get_json()
    assert data['error'] == 'INSUFFICIENT_PERMISSIONS'
```

### Functional Test Checklist
- [ ] All HTTP methods tested (GET, POST, DELETE)
- [ ] Status codes validated (200, 201, 400, 401, 404, 409, 500)
- [ ] Request validation tested (missing fields, invalid types)
- [ ] Authorization tested (with/without token, insufficient permissions)
- [ ] Response format validated (JSON structure)
- [ ] Pagination tested (limit, offset)
- [ ] Filters tested (game, activity, status)

---

## End-to-End Tests

### Purpose
Test complete user workflows in realistic scenarios.

### Running E2E Tests
```bash
make test-e2e
# Full docker-compose stack up
```

### Example E2E Workflow Test
```python
# tests/e2e/test_lfg_workflows.py

@pytest.mark.asyncio
async def test_complete_raid_formation_workflow(client, auth_headers):
    """
    Simulate a complete raid formation:
    1. Leader creates raid LFG post
    2. Players join
    3. Post fills automatically
    4. One player leaves
    5. Post reopens for new player
    6. Fills again
    """
    leader_headers = auth_headers['leader']
    player1_headers = auth_headers['player1']
    player2_headers = auth_headers['player2']
    player3_headers = auth_headers['player3']
    player4_headers = auth_headers['player4']

    # Step 1: Leader creates raid (needs 4 players)
    create_response = await client.post(
        '/api/v1/lfg/posts',
        json={
            "community_id": "raid-community",
            "user_id": "leader-id",
            "platform": "discord",
            "game": "World of Warcraft",
            "activity": "raid",
            "role": "tank",
            "rank_or_level": "Mythic+",
            "player_count_needed": 4,
            "message": "Mythic+ raid, Friday 8pm EST"
        },
        headers=leader_headers
    )
    assert create_response.status_code == 201
    post_id = (await create_response.get_json())['data']['id']

    # Verify post is open
    list_response = await client.get(
        '/api/v1/lfg/posts/raid-community',
        headers=leader_headers
    )
    posts = (await list_response.get_json())['data']['posts']
    assert len(posts) == 1
    assert posts[0]['status'] == 'open'
    assert posts[0]['current_player_count'] == 1

    # Step 2: Player 1 joins
    response = await client.post(
        f'/api/v1/lfg/posts/{post_id}/join',
        json={
            "user_id": "player1-id",
            "platform": "discord",
            "display_name": "Player1#1234"
        },
        headers=player1_headers
    )
    assert response.status_code == 200
    assert (await response.get_json())['data']['status'] == 'open'

    # Step 3: Players 2 and 3 join
    for headers in [player2_headers, player3_headers]:
        response = await client.post(
            f'/api/v1/lfg/posts/{post_id}/join',
            json={
                "user_id": "player-id",
                "platform": "discord",
                "display_name": "PlayerName"
            },
            headers=headers
        )
        assert response.status_code == 200

    # Step 4: Final player joins → group fills
    response = await client.post(
        f'/api/v1/lfg/posts/{post_id}/join',
        json={
            "user_id": "player4-id",
            "platform": "discord",
            "display_name": "Player4#1234"
        },
        headers=player4_headers
    )
    assert response.status_code == 200
    data = await response.get_json()
    assert data['data']['status'] == 'filled'  # Auto-filled!
    assert data['data']['current_player_count'] == 4

    # Verify post no longer in open list
    list_response = await client.get(
        '/api/v1/lfg/posts/raid-community?status=open',
        headers=leader_headers
    )
    posts = (await list_response.get_json())['data']['posts']
    assert len(posts) == 0

    # Step 5: Player 2 leaves (schedule conflict)
    response = await client.delete(
        f'/api/v1/lfg/posts/{post_id}/join',
        json={"user_id": "player2-id"},
        headers=player2_headers
    )
    assert response.status_code == 200
    data = await response.get_json()
    assert data['data']['status'] == 'open'  # Reverted!
    assert data['data']['current_player_count'] == 3

    # Step 6: New player joins to fill slot
    new_player_headers = auth_headers['new_player']
    response = await client.post(
        f'/api/v1/lfg/posts/{post_id}/join',
        json={
            "user_id": "newplayer-id",
            "platform": "discord",
            "display_name": "NewPlayer#5678"
        },
        headers=new_player_headers
    )
    assert response.status_code == 200
    assert (await response.get_json())['data']['status'] == 'filled'
```

### E2E Test Checklist
- [ ] Complete user workflows tested
- [ ] Multiple concurrent users simulated
- [ ] Error recovery tested
- [ ] Post lifecycle validated (create → fill → expire)
- [ ] Race conditions tested (concurrent joins)
- [ ] Data consistency verified

---

## Smoke Tests (Quick Validation)

### Purpose
Minimal set of tests to verify service is working (< 2 minutes).

### Running Smoke Tests
```bash
make test-smoke
# Runs only critical tests
```

### Smoke Test Checklist
```bash
# tests/smoke/test_lfg_smoke.py

@pytest.mark.smoke
async def test_service_health():
    """Verify service is up"""
    response = await client.get('/health')
    assert response.status_code == 200

@pytest.mark.smoke
async def test_database_connected():
    """Verify database connectivity"""
    response = await client.get('/health')
    data = await response.get_json()
    assert data['database'] == 'connected'

@pytest.mark.smoke
async def test_create_post_basic():
    """Smoke test: create post"""
    response = await client.post('/api/v1/lfg/posts', json={...})
    assert response.status_code == 201

@pytest.mark.smoke
async def test_list_posts_basic():
    """Smoke test: list posts"""
    response = await client.get('/api/v1/lfg/posts/community-id')
    assert response.status_code == 200

@pytest.mark.smoke
async def test_metrics_available():
    """Verify metrics endpoint"""
    response = await client.get('/metrics')
    assert response.status_code == 200
```

---

## Load Testing

### Purpose
Validate performance under sustained load.

### Running Load Tests
```bash
pip install locust
locust -f tests/load/locustfile.py --host=http://localhost:8096
```

### Example Load Test
```python
# tests/load/locustfile.py

from locust import HttpUser, task, between

class LfgUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def list_posts(self):
        """List posts (70% of traffic)"""
        self.client.get(
            '/api/v1/lfg/posts/community-uuid',
            headers={'Authorization': 'Bearer token'}
        )

    @task(1)
    def create_post(self):
        """Create new post (20% of traffic)"""
        self.client.post(
            '/api/v1/lfg/posts',
            json={
                "community_id": "community-uuid",
                "user_id": "user-uuid",
                "platform": "discord",
                "game": "Valorant",
                "activity": "ranked",
                "role": "DPS",
                "rank_or_level": "Radiant",
                "player_count_needed": 3,
                "message": "LFG"
            },
            headers={'Authorization': 'Bearer token'}
        )

    @task(1)
    def join_post(self):
        """Join post (10% of traffic)"""
        self.client.post(
            '/api/v1/lfg/posts/post-uuid/join',
            json={
                "user_id": "user-uuid",
                "platform": "discord",
                "display_name": "User"
            },
            headers={'Authorization': 'Bearer token'}
        )
```

---

## Test Data/Fixtures

### Mock Community
```python
MOCK_COMMUNITY = {
    "id": "community-uuid",
    "name": "Gaming Guild",
    "platform": "discord",
    "channel_id": "123456789"
}
```

### Mock Users
```python
MOCK_USERS = {
    "leader": {
        "id": "leader-uuid",
        "username": "GuildLeader",
        "platform_id": "discord:123"
    },
    "player1": {
        "id": "player1-uuid",
        "username": "Player1",
        "platform_id": "discord:456"
    },
    # ... more users
}
```

### Mock Posts
```python
MOCK_POST_VALORANT_RANKED = {
    "community_id": "community-uuid",
    "user_id": "user-uuid",
    "platform": "discord",
    "game": "Valorant",
    "activity": "ranked",
    "role": "DPS",
    "rank_or_level": "Radiant",
    "player_count_needed": 3,
    "message": "Looking for ranked team, EU servers"
}

MOCK_POST_WOW_RAID = {
    "community_id": "community-uuid",
    "user_id": "user-uuid",
    "platform": "discord",
    "game": "World of Warcraft",
    "activity": "raid",
    "role": "healer",
    "rank_or_level": "Mythic+",
    "player_count_needed": 10,
    "message": "Mythic+ progression, voice required"
}
```

---

## Test Coverage Requirements

| Component | Target | Tool |
|-----------|--------|------|
| Services | 85%+ | pytest-cov |
| Controllers | 80%+ | pytest-cov |
| Models | 90%+ | pytest-cov |
| Database | 75%+ | pytest-cov |
| **Overall** | **80%+** | **pytest-cov** |

### Generate Coverage Report
```bash
pytest --cov=src --cov-report=html tests/
open htmlcov/index.html
```

---

## Pre-Commit Testing

**Before pushing**, run:

```bash
# Full test suite
make test

# Linting
make lint

# Smoke tests (quick)
make test-smoke

# All checks pass?
git add .
git commit -m "feat: add LFG posts"
```

---

## CI/CD Integration

Tests run automatically on:
- Pull requests (all tests)
- Commits to main (unit + integration + e2e)
- Pre-release (full suite including load tests)

See `.github/workflows/` for details.
