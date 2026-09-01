# Engagement Module — Testing Guide

## Test Framework Setup

The Engagement Module uses Python's `pytest` framework for unit and integration testing.

### Installation

```bash
pip install pytest pytest-asyncio pytest-cov requests
```

---

## Mock Data Fixtures

### Poll Fixtures

```python
# tests/fixtures/polls.py
import pytest
from datetime import datetime, timedelta

@pytest.fixture
def poll_data():
    """Mock poll creation data."""
    return {
        "community_id": 1,
        "title": "What is your favorite programming language?",
        "description": "Vote for your preferred language",
        "options": ["Python", "JavaScript", "Go", "Rust"],
        "view_visibility": "community",
        "submit_visibility": "community",
        "allow_multiple_choices": False,
        "max_choices": 1,
        "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
    }

@pytest.fixture
def expired_poll_data():
    """Mock expired poll data."""
    return {
        "community_id": 1,
        "title": "Expired poll",
        "options": ["Option 1", "Option 2"],
        "expires_at": (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
    }

@pytest.fixture
def multi_choice_poll_data():
    """Mock multi-choice poll data."""
    return {
        "community_id": 1,
        "title": "Select all that apply",
        "options": ["Python", "JavaScript", "Go", "Rust"],
        "allow_multiple_choices": True,
        "max_choices": 3
    }

@pytest.fixture
def public_poll_data():
    """Mock public poll data."""
    return {
        "community_id": 1,
        "title": "Public poll",
        "options": ["Yes", "No"],
        "view_visibility": "public",
        "submit_visibility": "public"
    }
```

### Form Fixtures

```python
# tests/fixtures/forms.py
import pytest

@pytest.fixture
def form_data():
    """Mock form creation data."""
    return {
        "community_id": 1,
        "title": "Community Feedback Survey",
        "description": "Help us improve our community",
        "fields": [
            {
                "type": "text",
                "label": "Name",
                "placeholder": "Your full name",
                "required": True
            },
            {
                "type": "email",
                "label": "Email",
                "required": True
            },
            {
                "type": "textarea",
                "label": "Feedback",
                "placeholder": "Tell us what you think",
                "required": True
            },
            {
                "type": "select",
                "label": "Overall satisfaction",
                "options": ["Very satisfied", "Satisfied", "Neutral", "Dissatisfied"],
                "required": False
            }
        ],
        "view_visibility": "community",
        "submit_visibility": "community",
        "allow_anonymous": False,
        "submit_once_per_user": True
    }

@pytest.fixture
def anonymous_form_data():
    """Mock anonymous form data."""
    return {
        "community_id": 1,
        "title": "Anonymous Survey",
        "fields": [
            {
                "type": "textarea",
                "label": "Anonymous feedback",
                "required": True
            }
        ],
        "allow_anonymous": True
    }

@pytest.fixture
def form_submission():
    """Mock form submission data."""
    return {
        "values": {
            "1": "Jane Doe",
            "2": "jane@example.com",
            "3": "Great community! Keep up the good work.",
            "4": "Very satisfied"
        }
    }
```

### Token Fixtures

```python
# tests/fixtures/auth.py
import pytest
import jwt
from datetime import datetime, timedelta
from config import Config

@pytest.fixture
def valid_jwt_token():
    """Generate valid JWT token."""
    payload = {
        "user_id": 1,
        "username": "testuser",
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(
        payload,
        Config.JWT_SECRET,
        algorithm=Config.JWT_ALGORITHM
    )

@pytest.fixture
def expired_jwt_token():
    """Generate expired JWT token."""
    payload = {
        "user_id": 1,
        "username": "testuser",
        "exp": datetime.utcnow() - timedelta(hours=1)
    }
    return jwt.encode(
        payload,
        Config.JWT_SECRET,
        algorithm=Config.JWT_ALGORITHM
    )

@pytest.fixture
def invalid_jwt_token():
    """Return invalid JWT token."""
    return "invalid.token.here"

@pytest.fixture
def auth_header(valid_jwt_token):
    """Return Authorization header."""
    return {"Authorization": f"Bearer {valid_jwt_token}"}
```

---

## Unit Tests

### Health Check Tests

```python
# tests/test_health.py
import pytest
from app import app

@pytest.mark.asyncio
async def test_health_check_success():
    """Test successful health check."""
    client = app.test_client()
    response = await client.get("/health")

    assert response.status_code == 200
    data = await response.get_json()
    assert data["status"] == "healthy"
    assert data["module"] == "engagement_module"
    assert "version" in data
    assert "timestamp" in data

@pytest.mark.asyncio
async def test_health_check_database_failure():
    """Test health check when database is down."""
    # Mock database failure
    with patch("app.db.executesql") as mock_db:
        mock_db.side_effect = Exception("Connection refused")

        client = app.test_client()
        response = await client.get("/health")

        assert response.status_code == 503
        data = await response.get_json()
        assert data["status"] == "unhealthy"
```

### Poll Tests

```python
# tests/test_polls.py
import pytest
from app import app

@pytest.mark.asyncio
async def test_create_poll_success(poll_data, auth_header):
    """Test successful poll creation."""
    client = app.test_client()
    response = await client.post(
        "/api/v1/polls",
        json=poll_data,
        headers=auth_header
    )

    assert response.status_code == 201
    data = await response.get_json()
    assert data["success"] is True
    assert data["poll"]["title"] == poll_data["title"]
    assert len(data["poll"]["options"]) == 4

@pytest.mark.asyncio
async def test_create_poll_missing_auth(poll_data):
    """Test poll creation without authentication."""
    client = app.test_client()
    response = await client.post(
        "/api/v1/polls",
        json=poll_data
    )

    assert response.status_code == 401
    data = await response.get_json()
    assert "error" in data

@pytest.mark.asyncio
async def test_create_poll_invalid_options(auth_header):
    """Test poll creation with invalid options."""
    invalid_data = {
        "community_id": 1,
        "title": "Test poll",
        "options": ["Only one option"]  # Need at least 2
    }

    client = app.test_client()
    response = await client.post(
        "/api/v1/polls",
        json=invalid_data,
        headers=auth_header
    )

    assert response.status_code == 400
    data = await response.get_json()
    assert "error" in data

@pytest.mark.asyncio
async def test_get_poll(poll_data, auth_header):
    """Test retrieving poll details."""
    client = app.test_client()

    # Create poll
    create_response = await client.post(
        "/api/v1/polls",
        json=poll_data,
        headers=auth_header
    )
    poll_id = (await create_response.get_json())["poll"]["id"]

    # Get poll
    get_response = await client.get(f"/api/v1/polls/{poll_id}")
    assert get_response.status_code == 200
    data = await get_response.get_json()
    assert data["poll"]["id"] == poll_id
    assert "vote_counts" in data["poll"]

@pytest.mark.asyncio
async def test_list_polls(poll_data, auth_header):
    """Test listing community polls."""
    client = app.test_client()

    # Create multiple polls
    for i in range(3):
        await client.post(
            "/api/v1/polls",
            json={**poll_data, "title": f"Poll {i}"},
            headers=auth_header
        )

    # List polls
    response = await client.get("/api/v1/polls/community/1")
    assert response.status_code == 200
    data = await response.get_json()
    assert data["count"] >= 3

@pytest.mark.asyncio
async def test_vote_on_poll(poll_data, auth_header):
    """Test voting on a poll."""
    client = app.test_client()

    # Create poll
    create_response = await client.post(
        "/api/v1/polls",
        json=poll_data,
        headers=auth_header
    )
    poll_id = (await create_response.get_json())["poll"]["id"]
    options = (await create_response.get_json())["poll"]["options"]

    # Vote on poll
    vote_response = await client.post(
        f"/api/v1/polls/{poll_id}/vote",
        json={"option_ids": [options[0]["id"]]},
        headers=auth_header
    )

    assert vote_response.status_code == 200
    data = await vote_response.get_json()
    assert data["success"] is True

@pytest.mark.asyncio
async def test_duplicate_vote_prevented(poll_data, auth_header):
    """Test that duplicate votes are prevented."""
    client = app.test_client()

    # Create poll
    create_response = await client.post(
        "/api/v1/polls",
        json=poll_data,
        headers=auth_header
    )
    poll_id = (await create_response.get_json())["poll"]["id"]
    options = (await create_response.get_json())["poll"]["options"]

    # Vote once
    await client.post(
        f"/api/v1/polls/{poll_id}/vote",
        json={"option_ids": [options[0]["id"]]},
        headers=auth_header
    )

    # Try to vote again
    response = await client.post(
        f"/api/v1/polls/{poll_id}/vote",
        json={"option_ids": [options[0]["id"]]},
        headers=auth_header
    )

    assert response.status_code == 409

@pytest.mark.asyncio
async def test_vote_on_expired_poll(expired_poll_data, auth_header):
    """Test voting on expired poll is prevented."""
    client = app.test_client()

    # Create expired poll
    create_response = await client.post(
        "/api/v1/polls",
        json=expired_poll_data,
        headers=auth_header
    )
    poll_id = (await create_response.get_json())["poll"]["id"]
    options = (await create_response.get_json())["poll"]["options"]

    # Try to vote on expired poll
    response = await client.post(
        f"/api/v1/polls/{poll_id}/vote",
        json={"option_ids": [options[0]["id"]]},
        headers=auth_header
    )

    assert response.status_code == 400
    data = await response.get_json()
    assert "expired" in data["error"]
```

### Form Tests

```python
# tests/test_forms.py
import pytest
from app import app

@pytest.mark.asyncio
async def test_create_form_success(form_data, auth_header):
    """Test successful form creation."""
    client = app.test_client()
    response = await client.post(
        "/api/v1/forms",
        json=form_data,
        headers=auth_header
    )

    assert response.status_code == 201
    data = await response.get_json()
    assert data["success"] is True
    assert data["form"]["title"] == form_data["title"]

@pytest.mark.asyncio
async def test_get_form(form_data, auth_header):
    """Test retrieving form details."""
    client = app.test_client()

    # Create form
    create_response = await client.post(
        "/api/v1/forms",
        json=form_data,
        headers=auth_header
    )
    form_id = (await create_response.get_json())["form"]["id"]

    # Get form
    response = await client.get(f"/api/v1/forms/{form_id}")
    assert response.status_code == 200
    data = await response.get_json()
    assert data["form"]["id"] == form_id
    assert "fields" in data["form"]

@pytest.mark.asyncio
async def test_submit_form(form_data, form_submission, auth_header):
    """Test form submission."""
    client = app.test_client()

    # Create form
    create_response = await client.post(
        "/api/v1/forms",
        json=form_data,
        headers=auth_header
    )
    form_id = (await create_response.get_json())["form"]["id"]

    # Submit form
    response = await client.post(
        f"/api/v1/forms/{form_id}/submit",
        json=form_submission,
        headers=auth_header
    )

    assert response.status_code == 201
    data = await response.get_json()
    assert data["success"] is True
    assert "submission_id" in data

@pytest.mark.asyncio
async def test_duplicate_submission_prevented(form_data, form_submission, auth_header):
    """Test that duplicate submissions are prevented."""
    client = app.test_client()

    # Create form
    create_response = await client.post(
        "/api/v1/forms",
        json=form_data,
        headers=auth_header
    )
    form_id = (await create_response.get_json())["form"]["id"]

    # Submit form once
    await client.post(
        f"/api/v1/forms/{form_id}/submit",
        json=form_submission,
        headers=auth_header
    )

    # Try to submit again
    response = await client.post(
        f"/api/v1/forms/{form_id}/submit",
        json=form_submission,
        headers=auth_header
    )

    assert response.status_code == 409

@pytest.mark.asyncio
async def test_get_form_submissions(form_data, form_submission, auth_header):
    """Test retrieving form submissions."""
    client = app.test_client()

    # Create form
    create_response = await client.post(
        "/api/v1/forms",
        json=form_data,
        headers=auth_header
    )
    form_id = (await create_response.get_json())["form"]["id"]

    # Submit form
    await client.post(
        f"/api/v1/forms/{form_id}/submit",
        json=form_submission,
        headers=auth_header
    )

    # Get submissions
    response = await client.get(
        f"/api/v1/forms/{form_id}/submissions",
        headers=auth_header
    )

    assert response.status_code == 200
    data = await response.get_json()
    assert data["count"] >= 1
    assert "submissions" in data
```

---

## Integration Tests

```python
# tests/test_integration.py
import pytest
from app import app

@pytest.mark.asyncio
async def test_full_poll_workflow(poll_data, auth_header):
    """Test complete poll creation and voting workflow."""
    client = app.test_client()

    # 1. Create poll
    create_response = await client.post(
        "/api/v1/polls",
        json=poll_data,
        headers=auth_header
    )
    assert create_response.status_code == 201
    poll_id = (await create_response.get_json())["poll"]["id"]

    # 2. List polls
    list_response = await client.get("/api/v1/polls/community/1")
    assert list_response.status_code == 200

    # 3. Get poll details
    get_response = await client.get(f"/api/v1/polls/{poll_id}")
    assert get_response.status_code == 200
    options = (await get_response.get_json())["poll"]["options"]

    # 4. Vote on poll
    vote_response = await client.post(
        f"/api/v1/polls/{poll_id}/vote",
        json={"option_ids": [options[0]["id"]]},
        headers=auth_header
    )
    assert vote_response.status_code == 200

    # 5. Check vote was recorded
    final_response = await client.get(f"/api/v1/polls/{poll_id}")
    final_data = await final_response.get_json()
    assert final_data["poll"]["vote_counts"][options[0]["id"]] == 1

@pytest.mark.asyncio
async def test_full_form_workflow(form_data, form_submission, auth_header):
    """Test complete form creation and submission workflow."""
    client = app.test_client()

    # 1. Create form
    create_response = await client.post(
        "/api/v1/forms",
        json=form_data,
        headers=auth_header
    )
    assert create_response.status_code == 201
    form_id = (await create_response.get_json())["form"]["id"]

    # 2. List forms
    list_response = await client.get("/api/v1/forms/community/1")
    assert list_response.status_code == 200

    # 3. Get form details
    get_response = await client.get(f"/api/v1/forms/{form_id}")
    assert get_response.status_code == 200

    # 4. Submit form
    submit_response = await client.post(
        f"/api/v1/forms/{form_id}/submit",
        json=form_submission,
        headers=auth_header
    )
    assert submit_response.status_code == 201

    # 5. Retrieve submissions
    submissions_response = await client.get(
        f"/api/v1/forms/{form_id}/submissions",
        headers=auth_header
    )
    assert submissions_response.status_code == 200
    data = await submissions_response.get_json()
    assert data["count"] >= 1
```

---

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test

```bash
pytest tests/test_polls.py::test_create_poll_success -v
```

### Run with Coverage

```bash
pytest tests/ --cov=. --cov-report=html
```

### Run Integration Tests Only

```bash
pytest tests/test_integration.py -v
```

---

## Test Configuration

```python
# tests/conftest.py
import pytest
from app import app, db
from config import Config

@pytest.fixture(scope="session")
def test_config():
    """Configure test environment."""
    Config.ENVIRONMENT = "testing"
    Config.DATABASE_URL = "sqlite:///:memory:"  # Use in-memory database for testing
    return Config

@pytest.fixture(autouse=True)
def reset_database(test_config):
    """Reset database before each test."""
    init_database()
    yield
    db.executesql("DELETE FROM poll_votes")
    db.executesql("DELETE FROM poll_options")
    db.executesql("DELETE FROM community_polls")
    db.executesql("DELETE FROM form_field_values")
    db.executesql("DELETE FROM form_submissions")
    db.executesql("DELETE FROM form_fields")
    db.executesql("DELETE FROM community_forms")
    db.commit()
```

---

## Performance Testing

```python
# tests/test_performance.py
import pytest
import time
from app import app

@pytest.mark.asyncio
async def test_poll_creation_performance(poll_data, auth_header):
    """Test poll creation performance."""
    client = app.test_client()

    start = time.time()
    for i in range(100):
        await client.post(
            "/api/v1/polls",
            json={**poll_data, "title": f"Poll {i}"},
            headers=auth_header
        )
    elapsed = time.time() - start

    # Should create 100 polls in less than 5 seconds
    assert elapsed < 5.0
    print(f"Created 100 polls in {elapsed:.2f} seconds")
```

---

## Next Steps

- See [API.md](API.md) for endpoint documentation
- See [CONFIGURATION.md](CONFIGURATION.md) for test environment setup
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for test debugging

**Company**: Penguin Tech Inc
**License**: Limited AGPL-3.0
**Last Updated**: 2026-02-16
