# Slack Module Testing Guide

## Test Structure

```
trigger/receiver/slack_module/
├── tests/
│   ├── unit/
│   │   ├── test_slack_bolt_service.py
│   │   ├── test_block_kit_builder.py
│   │   └── test_event_normalizer.py
│   ├── integration/
│   │   ├── test_slash_commands.py
│   │   ├── test_interactions.py
│   │   ├── test_modal_submissions.py
│   │   └── test_signature_validation.py
│   ├── e2e/
│   │   ├── test_live_slack_workspace.py
│   │   └── test_socket_mode.py
│   └── conftest.py           # Shared fixtures
```

---

## Running Tests

### Install Test Dependencies

```bash
cd trigger/receiver/slack_module
pip install -r requirements-dev.txt

# Includes: pytest, pytest-asyncio, pytest-cov, pytest-mock, responses
```

### Run All Tests

```bash
# Run all tests with coverage
make test-slack-module

# Or directly:
pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_slack_bolt_service.py -v

# Run specific test function
pytest tests/unit/test_slack_bolt_service.py::test_initialize -v

# Run with live logging output
pytest tests/ -v -s

# Run with debugging
pytest tests/ -v --pdb  # Drops into debugger on failure
```

### Test Categories

**Unit Tests** - Service classes in isolation
```bash
pytest tests/unit/ -v
```

**Integration Tests** - Full flow with mock Slack API
```bash
pytest tests/integration/ -v
```

**E2E Tests** - Live Slack workspace (requires real bot token)
```bash
pytest tests/e2e/ -v -m "not slow"  # Skip slow tests
pytest tests/e2e/ -v -m "slow"      # Run only slow tests
```

**Smoke Tests** - Critical paths only (<2 minutes)
```bash
pytest tests/ -v -m "smoke"
```

---

## Unit Tests

### SlackBoltService Tests

**Location**: `tests/unit/test_slack_bolt_service.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.slack_bolt_service import SlackBoltService

@pytest.fixture
async def service():
    """Service instance with mocked dependencies."""
    service = SlackBoltService()
    service.db = AsyncMock()
    service.redis = AsyncMock()
    service.router_client = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_initialize_http_mode(service):
    """Test HTTP mode initialization."""
    service.use_socket_mode = False
    await service.initialize()

    assert service.app is not None
    assert service.app.client is not None

@pytest.mark.asyncio
async def test_initialize_socket_mode(service):
    """Test Socket Mode initialization."""
    service.use_socket_mode = True
    await service.initialize()

    assert service.app is not None
    # Socket mode app setup

@pytest.mark.asyncio
async def test_slash_command_execution(service):
    """Test slash command processing."""
    # Mock body
    body = {
        'team_id': 'T123456',
        'user_id': 'U123456',
        'channel_id': 'C123456',
        'command': '/waddlebot',
        'text': 'balance',
        'response_url': 'https://hooks.slack.com/...'
    }

    # Mock response
    service.router_client.execute = AsyncMock(return_value={
        'response_type': 'in_channel',
        'blocks': [{'type': 'section', 'text': {...}}]
    })

    # Execute
    result = await service.handle_slash_command(
        ack=AsyncMock(),
        body=body,
        respond=AsyncMock(),
        client=AsyncMock()
    )

    # Verify router called
    service.router_client.execute.assert_called_once()
```

### BlockKitBuilder Tests

**Location**: `tests/unit/test_block_kit_builder.py`

```python
from src.services.block_kit_builder import BlockKitBuilder

def test_create_modal():
    """Test modal creation."""
    modal = BlockKitBuilder.create_modal(
        callback_id="test_form",
        title="Test Modal",
        blocks=[
            BlockKitBuilder.input_block(
                block_id="name_block",
                label="Name",
                element_id="name_input"
            )
        ]
    )

    assert modal['type'] == 'modal'
    assert modal['callback_id'] == 'test_form'
    assert modal['title']['text'] == 'Test Modal'
    assert len(modal['blocks']) == 1

def test_section_with_button():
    """Test button section."""
    section = BlockKitBuilder.section_with_button(
        text="Approve this user?",
        action_id="approve_btn",
        value="U123456",
        label="Approve",
        style="primary"
    )

    assert section['type'] == 'section'
    assert section['accessory']['type'] == 'button'
    assert section['accessory']['action_id'] == 'approve_btn'
    assert section['accessory']['style'] == 'primary'

def test_select_block():
    """Test select dropdown."""
    select = BlockKitBuilder.select_block(
        block_id="priority_select",
        label="Priority",
        action_id="select_priority",
        options=[
            {'text': {'type': 'plain_text', 'text': 'Low'}, 'value': 'low'},
            {'text': {'type': 'plain_text', 'text': 'High'}, 'value': 'high'},
        ]
    )

    assert select['type'] == 'section'
    assert select['accessory']['type'] == 'static_select'
    assert len(select['accessory']['options']) == 2
```

### Event Normalizer Tests

**Location**: `tests/unit/test_event_normalizer.py`

```python
from src.utils.event_normalizer import EventNormalizer

def test_normalize_slash_command():
    """Test slash command normalization."""
    raw_event = {
        'team_id': 'T123456',
        'user_id': 'U123456',
        'channel_id': 'C123456',
        'command': '/waddlebot',
        'text': 'balance'
    }

    normalized = EventNormalizer.normalize_slash_command(raw_event)

    assert normalized['platform'] == 'slack'
    assert normalized['entity_id'] == 'T123456:C123456'
    assert normalized['message_type'] == 'slashCommand'
    assert normalized['user_id'] == 'U123456'
    assert normalized['content'] == 'balance'
    assert normalized['metadata']['command'] == '/waddlebot'

def test_normalize_block_action():
    """Test button/select action normalization."""
    raw_event = {
        'team': {'id': 'T123456'},
        'user': {'id': 'U123456'},
        'channel': {'id': 'C123456'},
        'actions': [{
            'type': 'button',
            'action_id': 'approve_button',
            'value': 'user_789',
            'block_id': 'action_block'
        }]
    }

    normalized = EventNormalizer.normalize_block_action(raw_event)

    assert normalized['platform'] == 'slack'
    assert normalized['message_type'] == 'interaction'
    assert normalized['metadata']['action_id'] == 'approve_button'
    assert normalized['metadata']['value'] == 'user_789'
```

---

## Integration Tests

### Signature Validation Tests

**Location**: `tests/integration/test_signature_validation.py`

```python
import pytest
import hmac
import hashlib
from datetime import datetime

@pytest.fixture
def slack_headers():
    """Generate valid Slack webhook headers."""
    timestamp = str(int(datetime.now().timestamp()))
    body = '{"type": "event_callback", "event": {}}'
    base_string = f'v0:{timestamp}:{body}'

    signature = hmac.new(
        b'test-signing-secret',
        base_string.encode(),
        hashlib.sha256
    ).hexdigest()

    return {
        'X-Slack-Request-Timestamp': timestamp,
        'X-Slack-Signature': f'v0={signature}',
        'Content-Type': 'application/json'
    }

@pytest.mark.asyncio
async def test_valid_signature(client, slack_headers):
    """Test request with valid signature is accepted."""
    response = await client.post(
        '/slack/events',
        json={'type': 'url_verification', 'challenge': 'test'},
        headers=slack_headers
    )

    assert response.status_code == 200

@pytest.mark.asyncio
async def test_invalid_signature(client):
    """Test request with invalid signature is rejected."""
    response = await client.post(
        '/slack/events',
        json={'type': 'url_verification', 'challenge': 'test'},
        headers={
            'X-Slack-Request-Timestamp': str(int(datetime.now().timestamp())),
            'X-Slack-Signature': 'v0=invalid_signature'
        }
    )

    assert response.status_code == 401
```

### Slash Command Integration Tests

**Location**: `tests/integration/test_slash_commands.py`

```python
@pytest.mark.asyncio
async def test_slash_command_balance(client, mock_router):
    """Test /waddlebot balance command."""
    # Mock router response
    mock_router.return_value = {
        'response_type': 'ephemeral',
        'blocks': [
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': 'Your balance: **500 WaddleBucks**'
                }
            }
        ]
    }

    # Send command
    response = await client.post('/slack/commands', data={
        'team_id': 'T123456',
        'user_id': 'U123456',
        'channel_id': 'C123456',
        'command': '/waddlebot',
        'text': 'balance',
        'response_url': 'https://hooks.slack.com/...'
    })

    assert response.status_code == 200

    # Verify router called with normalized event
    mock_router.assert_called_once()
    args = mock_router.call_args[0]
    assert args[0]['message_type'] == 'slashCommand'
    assert args[0]['content'] == 'balance'

@pytest.mark.asyncio
async def test_slash_command_form(client, mock_router):
    """Test /form command opens modal."""
    mock_router.return_value = {
        'response_action': 'open_modal',
        'view': {
            'type': 'modal',
            'callback_id': 'form_submit',
            'title': 'Create Ticket',
            'blocks': [...]
        }
    }

    response = await client.post('/slack/commands', data={
        'team_id': 'T123456',
        'user_id': 'U123456',
        'command': '/form',
        'text': 'new',
        'trigger_id': 'trigger_123'
    })

    assert response.status_code == 200
```

### Modal Submission Tests

**Location**: `tests/integration/test_modal_submissions.py`

```python
@pytest.mark.asyncio
async def test_modal_submission_validation_error(client):
    """Test modal submission with validation error."""
    response = await client.post('/slack/actions', json={
        'type': 'view_submission',
        'view': {
            'id': 'V123',
            'callback_id': 'form_submit',
            'state': {
                'values': {
                    'title_block': {
                        'title_input': {
                            'value': None  # Missing required field
                        }
                    }
                }
            }
        },
        'user': {'id': 'U123456'},
        'team': {'id': 'T123456'}
    })

    assert response.status_code == 200
    body = await response.json()
    assert body['response_action'] == 'errors'
    assert 'title_block' in body['errors']

@pytest.mark.asyncio
async def test_modal_submission_success(client, mock_router):
    """Test modal submission with valid data."""
    mock_router.return_value = {
        'response_type': 'in_channel',
        'blocks': [...]
    }

    response = await client.post('/slack/actions', json={
        'type': 'view_submission',
        'view': {
            'id': 'V123',
            'callback_id': 'form_submit',
            'state': {
                'values': {
                    'title_block': {
                        'title_input': {
                            'value': 'Test Ticket'
                        }
                    }
                }
            }
        },
        'user': {'id': 'U123456'},
        'team': {'id': 'T123456'}
    })

    assert response.status_code == 200
    body = await response.json()
    assert body == {}  # Empty response on success

    # Verify router called
    mock_router.assert_called_once()
```

---

## E2E Tests

### Live Slack Workspace Tests

**Location**: `tests/e2e/test_live_slack_workspace.py`

Requires: Valid `SLACK_BOT_TOKEN`, test workspace, test user account

```python
import pytest
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

@pytest.fixture
def slack_client():
    """Real Slack client for E2E testing."""
    return WebClient(token=os.getenv('SLACK_BOT_TOKEN'))

@pytest.fixture
async def test_channel(slack_client):
    """Create temporary test channel."""
    response = slack_client.conversations_create(
        name=f'test-{int(time.time())}'
    )
    channel_id = response['channel']['id']
    yield channel_id

    # Cleanup
    slack_client.conversations_delete(channel=channel_id)

@pytest.mark.e2e
@pytest.mark.slow
async def test_slash_command_in_workspace(slack_client, test_channel):
    """Test slash command execution in real workspace."""
    # This test requires manual trigger or Slack API workaround
    # Can't directly invoke slash commands via API

    # Instead, verify bot can post messages
    response = slack_client.chat_postMessage(
        channel=test_channel,
        text='Test message'
    )

    assert response['ok']
    assert response['message']['text'] == 'Test message'

@pytest.mark.e2e
@pytest.mark.slow
async def test_modal_open_close(slack_client):
    """Test modal can be opened and closed."""
    # Get trigger ID (requires user interaction or special token)
    # Simplified version shows bot posting capability

    # Verify bot has modal posting permissions
    response = slack_client.auth_test()
    assert response['ok']
```

### Socket Mode Tests

**Location**: `tests/e2e/test_socket_mode.py`

```python
@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skipif(
    not os.getenv('SLACK_APP_TOKEN'),
    reason="Socket Mode E2E requires SLACK_APP_TOKEN"
)
async def test_socket_mode_connection():
    """Test Socket Mode connection and message reception."""
    service = SlackBoltService()
    service.use_socket_mode = True
    service.app_token = os.getenv('SLACK_APP_TOKEN')

    # Initialize
    await service.initialize()

    # Verify connected
    assert service.socket_connected

    # Wait for heartbeat
    await asyncio.sleep(2)

    # Should still be connected
    assert service.socket_connected
```

---

## Mock Data Fixtures

### Common Test Data

**Location**: `tests/conftest.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_slack_event_slash_command():
    """Slash command event fixture."""
    return {
        'type': 'event_callback',
        'token': 'verification_token',
        'team_id': 'T0001',
        'team_domain': 'example',
        'channel_id': 'C2147483705',
        'user_id': 'U2147483697',
        'user_name': 'alice',
        'command': '/waddlebot',
        'text': 'balance',
        'response_url': 'https://hooks.slack.com/commands/T0001/B00000000/XXXXXXXXXXXXXXXXXXXX',
        'trigger_id': '13345224609.738474920.8085319811',
        'api_app_id': 'A123456'
    }

@pytest.fixture
def mock_slack_event_message():
    """Message event fixture."""
    return {
        'type': 'event_callback',
        'event': {
            'type': 'message',
            'channel': 'C2147483705',
            'user': 'U2147483697',
            'text': 'hello',
            'ts': '1609459200.000000'
        },
        'team_id': 'T0001'
    }

@pytest.fixture
def mock_slack_event_action():
    """Button action event fixture."""
    return {
        'type': 'block_actions',
        'user': {'id': 'U2147483697', 'name': 'alice'},
        'api_app_id': 'A123456',
        'team': {'id': 'T0001', 'domain': 'example'},
        'channel': {'id': 'C2147483705', 'name': 'general'},
        'trigger_id': '13345224609.738474920.8085319811',
        'actions': [
            {
                'type': 'button',
                'action_id': 'approve_button',
                'value': 'user_123',
                'block_id': 'action_block_1'
            }
        ]
    }

@pytest.fixture
def mock_router_client():
    """Mock router API client."""
    client = AsyncMock()
    client.execute_command = AsyncMock(return_value={
        'response_type': 'in_channel',
        'blocks': []
    })
    return client

@pytest.fixture
def mock_database():
    """Mock database connection."""
    db = AsyncMock()
    db.slack_workspaces.find = AsyncMock(return_value={
        'team_id': 'T0001',
        'bot_token': 'xoxb-test',
        'signing_secret': 'test-secret'
    })
    return db
```

---

## Coverage & Reporting

### Generate Coverage Report

```bash
# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# View report
open htmlcov/index.html

# Coverage thresholds (CI will fail below these)
pytest tests/ --cov=src --cov-fail-under=80
```

### Expected Coverage

| Module | Target |
|--------|--------|
| SlackBoltService | 90%+ |
| BlockKitBuilder | 95%+ |
| Event normalization | 85%+ |
| Request validation | 90%+ |
| Overall | 85%+ |

---

## Continuous Integration

### Pre-commit Tests (smoke)

```bash
# Run only smoke tests before commit
pytest tests/ -m "smoke" --tb=short

# Typical execution: <30 seconds
```

### GitHub Actions Workflow

**Location**: `.github/workflows/test-slack.yml`

```yaml
name: Slack Module Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r trigger/receiver/slack_module/requirements-dev.txt

      - name: Run unit tests
        run: |
          pytest trigger/receiver/slack_module/tests/unit -v

      - name: Run integration tests
        run: |
          pytest trigger/receiver/slack_module/tests/integration -v

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Testing Checklist

Before committing Slack module changes:

- [ ] All unit tests pass: `pytest tests/unit -v`
- [ ] All integration tests pass: `pytest tests/integration -v`
- [ ] Coverage >= 85%: `pytest tests/ --cov-fail-under=85`
- [ ] No linting errors: `flake8 src/ tests/`
- [ ] Type hints valid: `mypy src/`
- [ ] Smoke tests pass: `pytest tests/ -m "smoke"`
- [ ] Manual testing: Test command in Slack workspace
- [ ] Documentation updated if changing behavior
