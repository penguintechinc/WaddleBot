# Discord Module Testing Guide

## Test Categories

The Discord module uses the standard test framework defined in `.claude/testing.md`:

- **Build**: Container image builds and artifact compilation
- **Unit**: Individual function and class behavior
- **Integration**: Discord module with router/database
- **Functional**: User workflows and features (APIs, UI, commands)
- **E2E**: Full user journeys from Discord to router to response
- **Security**: Credentials, permissions, input validation
- **API**: HTTP endpoint functionality
- **Performance**: Load testing and resource usage

### Test Execution Order

```
1. Build Tests      (must pass before others)
2. Unit Tests       (quick validation)
3. Security Tests   (credential handling, validation)
4. API Tests        (endpoint functionality)
5. Integration Tests (router/database interaction)
6. Functional Tests (user-visible workflows)
7. E2E Tests        (full user journeys)
8. Performance Tests (load and stress)
```

## Running Tests

### Run All Tests

```bash
./scripts/test-controller.sh all discord
```

### Run Specific Category

```bash
# Build tests
./scripts/test-controller.sh build discord

# Unit tests
./scripts/test-controller.sh unit discord

# Integration tests
./scripts/test-controller.sh integration discord

# Functional tests
./scripts/test-controller.sh functional discord

# E2E tests
./scripts/test-controller.sh e2e discord

# Security tests
./scripts/test-controller.sh security discord

# API tests
./scripts/test-controller.sh api discord

# Performance tests
./scripts/test-controller.sh performance discord

# Smoke tests (curated subset, <2 min)
./scripts/test-controller.sh smoke discord
```

## Build Tests

Verify the Docker image builds correctly.

### Test Cases

```bash
# Build image without cache
docker build --no-cache -t waddlebot/discord-module:test trigger/receiver/discord_module

# Verify image runs
docker run --rm waddlebot/discord-module:test python --version

# Verify dependencies installed
docker run --rm waddlebot/discord-module:test pip list | grep py-cord

# Check image size (should be < 500MB)
docker image inspect waddlebot/discord-module:test | jq '.Size'
```

### Expected Output

```
Successfully built abc123def456
Successfully tagged waddlebot/discord-module:test
```

## Unit Tests

Test individual functions and classes in isolation.

### Test File Structure

```
tests/
├── unit/
│   ├── test_discord_bot_service.py
│   ├── test_interaction_handler.py
│   ├── test_event_normalization.py
│   ├── test_credential_management.py
│   └── test_response_rendering.py
```

### Running Unit Tests

```bash
pytest tests/unit -v --tb=short

# With coverage
pytest tests/unit --cov=trigger/receiver/discord_module --cov-report=html
```

### Example Test Cases

#### DiscordBotService Tests

```python
def test_normalize_slash_command_event():
    """Slash command events normalized correctly"""
    event = {
        "user_id": "987654321",
        "guild_id": "123456789",
        "command_name": "balance",
        "options": {}
    }

    normalized = bot_service.normalize_event(event, "slashCommand")

    assert normalized["entity_id"] == "guild:channel"
    assert normalized["message_type"] == "slashCommand"
    assert normalized["platform"] == "discord"
    assert normalized["metadata"]["command_name"] == "balance"

def test_normalize_button_interaction():
    """Button interactions normalized correctly"""
    event = {
        "user_id": "987654321",
        "custom_id": "accept_123"
    }

    normalized = bot_service.normalize_event(event, "interaction")

    assert normalized["message_type"] == "interaction"
    assert normalized["metadata"]["interaction_type"] == "button"
```

#### InteractionHandler Tests

```python
def test_build_embed_with_fields():
    """Embed builder creates valid Discord embed"""
    response = {
        "type": "embed",
        "content": {
            "title": "Balance",
            "description": "User balance",
            "color": "0xFFD700",
            "fields": [
                {"name": "Gold", "value": "1000", "inline": True}
            ]
        }
    }

    embed = interaction_handler.build_embed(response)

    assert embed.title == "Balance"
    assert embed.color == 16766720  # 0xFFD700
    assert len(embed.fields) == 1

def test_split_long_message():
    """Long responses split correctly"""
    long_content = "x" * 5000

    messages = interaction_handler.split_message(long_content)

    assert len(messages) == 3
    assert all(len(m) <= 2000 for m in messages)
```

### Test Coverage Goals

- Unit tests: >= 90% coverage
- Critical paths: 100% coverage
- Error handling: >= 80% coverage

## Integration Tests

Test Discord module with router and database.

### Test File Structure

```
tests/
├── integration/
│   ├── test_router_integration.py
│   ├── test_database_integration.py
│   ├── test_redis_integration.py
│   ├── test_credential_flow.py
│   └── test_event_forwarding.py
```

### Running Integration Tests

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run tests
pytest tests/integration -v

# Stop test environment
docker-compose -f docker-compose.test.yml down
```

### Example Test Cases

#### Router Integration

```python
async def test_forward_event_to_router():
    """Events forwarded correctly to router"""
    event = {
        "entity_id": "guild:channel",
        "message_type": "slashCommand",
        "metadata": {"command_name": "balance"}
    }

    response = await bot_service.forward_to_router(event)

    assert response["type"] in ["embed", "text", "button", "modal"]
    assert "content" in response or "components" in response

async def test_router_timeout_handling():
    """Timeouts from router handled gracefully"""
    # Mock slow router (3+ second delay)

    try:
        response = await bot_service.forward_to_router(event, timeout=1)
        assert False, "Should have timed out"
    except asyncio.TimeoutError:
        assert True
```

#### Database Integration

```python
def test_save_credential():
    """Credentials saved and retrieved from database"""
    credential = {
        "user_id": "987654321",
        "guild_id": "123456789",
        "platform": "twitch",
        "token": "encrypted_token",
        "username": "myusername"
    }

    # Save
    cred_service.save_credential(credential)

    # Retrieve
    retrieved = cred_service.get_credential(
        user_id="987654321",
        guild_id="123456789",
        platform="twitch"
    )

    assert retrieved["username"] == "myusername"
    assert retrieved["platform"] == "twitch"

def test_credential_redis_cache():
    """Credentials cached in Redis"""
    # First call - database
    cred1 = cred_service.get_credential(user_id="987654321", ...)

    # Second call - Redis cache
    cred2 = cred_service.get_credential(user_id="987654321", ...)

    # Should be same object (cached)
    assert cred1 is cred2
```

## Functional Tests

Test user-visible features and workflows.

### Test File Structure

```
tests/
├── functional/
│   ├── test_slash_commands.py
│   ├── test_buttons.py
│   ├── test_modals.py
│   ├── test_select_menus.py
│   └── test_admin_commands.py
```

### Running Functional Tests

```bash
pytest tests/functional -v --tb=short
```

### Mock Discord Bot

For testing without Discord connection:

```python
import asyncio
from discord.ext import commands
from unittest.mock import AsyncMock, MagicMock

# Mock bot instance
bot = MagicMock()
bot.get_guild = MagicMock(return_value=MagicMock(name="Test Guild"))
bot.get_user = MagicMock(return_value=MagicMock(name="Test User"))

# Mock interaction
interaction = AsyncMock()
interaction.user.id = "987654321"
interaction.guild.id = "123456789"
interaction.response.send_message = AsyncMock()
```

### Example Test Cases

#### Slash Command Tests

```python
async def test_balance_slash_command():
    """User can check balance with /balance command"""
    interaction = create_mock_interaction(
        command_name="balance",
        user_id="987654321",
        guild_id="123456789"
    )

    await bot_service.handle_slash_command(interaction)

    # Verify response was sent
    interaction.response.send_message.assert_called_once()

    # Verify response type
    call_args = interaction.response.send_message.call_args
    embed = call_args.kwargs.get("embed")
    assert embed is not None
    assert "Balance" in embed.title

async def test_give_slash_command_with_params():
    """User can give currency with /give @user amount"""
    interaction = create_mock_interaction(
        command_name="give",
        options={
            "user": "target_user",
            "amount": 100
        }
    )

    await bot_service.handle_slash_command(interaction)

    interaction.response.send_message.assert_called_once()
```

#### Button Interaction Tests

```python
async def test_button_click_interaction():
    """User can click button and see response"""
    interaction = create_mock_interaction(
        interaction_type="button",
        custom_id="accept_trade_123"
    )

    await bot_service.handle_interaction(interaction)

    # Verify interaction was processed
    interaction.response.send_message.assert_called_once()

    # Verify message was updated or sent
    assert interaction.response.send_message.called
```

#### Modal Tests

```python
async def test_modal_form_submission():
    """User can fill and submit modal form"""
    interaction = create_mock_interaction(
        interaction_type="modal",
        custom_id="feedback_form_123",
        form_data={
            "feedback_text": "Great bot!",
            "rating_select": "5_stars"
        }
    )

    await bot_service.handle_interaction(interaction)

    interaction.response.send_message.assert_called_once()

    # Verify form data was processed
    call_args = interaction.response.send_message.call_args
    message = call_args.kwargs.get("content")
    assert "submitted" in message.lower() or "received" in message.lower()
```

## E2E Tests

Test complete user journeys from Discord to response.

### Test File Structure

```
tests/
├── e2e/
│   ├── test_complete_workflows.py
│   ├── test_multi_step_interactions.py
│   └── test_error_recovery.py
```

### Running E2E Tests

```bash
# Start full environment
docker-compose up -d

# Wait for services ready
./scripts/wait-for-services.sh

# Run E2E tests
pytest tests/e2e -v --tb=short

# Clean up
docker-compose down
```

### Example Test Cases

#### Balance Command Workflow

```python
async def test_complete_balance_workflow():
    """User gets balance: command -> router -> response"""
    # Setup
    user_id = "987654321"
    guild_id = "123456789"

    # User types /balance
    interaction = create_real_interaction(
        user_id=user_id,
        guild_id=guild_id,
        command_name="balance"
    )

    # Bot processes command
    await bot_service.handle_slash_command(interaction)

    # Verify event forwarded to router
    assert router_api_called_with(
        entity_id=f"{guild_id}:{user_id}",
        message_type="slashCommand"
    )

    # Verify response rendered
    interaction.response.send_message.assert_called()

    # Verify embed contains balance
    embed = interaction.response.send_message.call_args.kwargs["embed"]
    assert any("1000" in str(f.value) for f in embed.fields)
```

#### Multi-Step Poll Creation

```python
async def test_poll_creation_workflow():
    """User creates poll: command -> modal -> submit -> response"""

    # Step 1: User types /poll create
    cmd_interaction = create_real_interaction(command_name="poll", subcommand="create")
    await bot_service.handle_slash_command(cmd_interaction)

    # Verify modal was sent
    modal = cmd_interaction.response.send_modal.call_args.args[0]
    assert modal.title == "Create Poll"

    # Step 2: User fills and submits modal
    modal_interaction = create_real_interaction(
        interaction_type="modal",
        custom_id=modal.custom_id,
        form_data={
            "poll_question": "What's your favorite game?",
            "option_1": "Valorant",
            "option_2": "CS:GO"
        }
    )

    await bot_service.handle_interaction(modal_interaction)

    # Verify poll created
    poll = get_poll_from_database()
    assert poll.question == "What's your favorite game?"
    assert len(poll.options) == 2

    # Step 3: Verify response with voting buttons
    response = modal_interaction.response.send_message.call_args
    assert len(response.kwargs["components"]) > 0  # Has buttons
```

## Security Tests

Test credential handling and permission validation.

### Test File Structure

```
tests/
├── security/
│   ├── test_credential_encryption.py
│   ├── test_admin_permission_checks.py
│   ├── test_input_validation.py
│   └── test_injection_prevention.py
```

### Running Security Tests

```bash
# Security tests
pytest tests/security -v

# With security scanning
./scripts/test-controller.sh security discord
```

### Example Test Cases

#### Credential Encryption

```python
def test_credential_encryption():
    """Credentials encrypted in database"""
    plaintext_token = "secret_token_12345"

    # Save credential
    cred_service.save_credential({
        "user_id": "987654321",
        "token": plaintext_token
    })

    # Query raw database
    raw_data = db.execute("SELECT token FROM discord_credentials WHERE user_id = ?",
                          ("987654321",))

    # Verify token is encrypted (not plaintext)
    assert raw_data[0]["token"] != plaintext_token
    assert len(raw_data[0]["token"]) > len(plaintext_token)

    # Verify token can be decrypted and used
    retrieved_cred = cred_service.get_credential("987654321")
    assert retrieved_cred["token"] == plaintext_token

def test_credential_not_logged():
    """Credentials never logged in plaintext"""
    plaintext_token = "secret_12345"

    # Simulate processing with credential
    cred = {"token": plaintext_token}
    logger.debug(f"Processing credential: {cred}")

    # Check logs don't contain plaintext
    logs = get_logs()
    assert plaintext_token not in logs
```

#### Admin Permission Checks

```python
def test_admin_context_command_requires_admin():
    """Only admins can use /context switch"""
    # User without admin permission
    non_admin_user = create_mock_user(permissions=0)

    interaction = create_mock_interaction(
        command_name="context",
        subcommand="switch",
        user=non_admin_user,
        guild_id="123456789"
    )

    # Should reject
    response = bot_service.handle_slash_command(interaction)

    # Verify error message
    message = interaction.response.send_message.call_args.kwargs["content"]
    assert "admin" in message.lower() or "permission" in message.lower()

def test_admin_link_command_validates_guild():
    """Admin can only link guilds bot is in"""
    admin_user = create_mock_user(permissions=ADMIN)

    # Guild bot is not in
    invalid_guild_id = "999999999"

    interaction = create_mock_interaction(
        command_name="link",
        options={"guild_id": invalid_guild_id},
        user=admin_user
    )

    # Should reject
    response = bot_service.handle_slash_command(interaction)

    # Verify error
    message = interaction.response.send_message.call_args.kwargs["content"]
    assert "not in" in message.lower() or "cannot" in message.lower()
```

#### Input Validation

```python
def test_give_command_validates_amount():
    """Give command validates amount is positive number"""
    test_cases = [
        (-100, False),   # Negative
        (0, False),      # Zero
        (abc, False),    # Not a number
        (100, True),     # Valid
        (999999, True),  # Valid large amount
    ]

    for amount, should_succeed in test_cases:
        interaction = create_mock_interaction(
            command_name="give",
            options={"amount": amount}
        )

        response = bot_service.handle_slash_command(interaction)

        if should_succeed:
            assert interaction.response.send_message.called
            message = interaction.response.send_message.call_args.kwargs["content"]
            assert "success" in message.lower() or "gave" in message.lower()
        else:
            message = interaction.response.send_message.call_args.kwargs["content"]
            assert "invalid" in message.lower() or "must be" in message.lower()
```

## API Tests

Test HTTP endpoints.

### Test File Structure

```
tests/
├── api/
│   ├── test_status_endpoint.py
│   ├── test_guilds_endpoint.py
│   ├── test_health_endpoint.py
│   └── test_metrics_endpoint.py
```

### Running API Tests

```bash
# Start service
docker-compose up -d discord-module

# Run API tests
pytest tests/api -v

# Stop service
docker-compose down
```

### Example Test Cases

#### Status Endpoint

```python
async def test_get_status():
    """GET /api/v1/status returns bot status"""
    client = httpx.AsyncClient(base_url="http://localhost:8003")

    response = await client.get("/api/v1/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "latency_ms" in data
    assert "guilds_count" in data

async def test_get_status_bot_disconnected():
    """GET /api/v1/status returns 503 if bot disconnected"""
    # Simulate bot disconnection
    disconnect_bot()

    client = httpx.AsyncClient(base_url="http://localhost:8003")
    response = await client.get("/api/v1/status")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] != "ok"
```

#### Guilds Endpoint

```python
async def test_get_guilds():
    """GET /api/v1/bot/guilds returns connected guilds"""
    client = httpx.AsyncClient(base_url="http://localhost:8003")

    response = await client.get("/api/v1/bot/guilds")

    assert response.status_code == 200
    data = response.json()
    assert "guilds" in data
    assert len(data["guilds"]) > 0

    guild = data["guilds"][0]
    assert "id" in guild
    assert "name" in guild
    assert "member_count" in guild

async def test_get_guilds_pagination():
    """GET /api/v1/bot/guilds supports pagination"""
    client = httpx.AsyncClient(base_url="http://localhost:8003")

    response = await client.get("/api/v1/bot/guilds?limit=5&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert len(data["guilds"]) <= 5
    assert "limit" in data
    assert "offset" in data
```

## Performance Tests

Load and stress testing.

### Test File Structure

```
tests/
├── performance/
│   ├── test_event_throughput.py
│   ├── test_response_latency.py
│   └── test_resource_usage.py
```

### Running Performance Tests

```bash
pytest tests/performance -v --durations=0
```

### Example Test Cases

#### Event Throughput

```python
async def test_event_throughput():
    """Module handles 1000+ events per second"""
    num_events = 1000
    start_time = time.time()

    # Send events rapidly
    tasks = []
    for i in range(num_events):
        event = create_test_event(
            user_id=f"user_{i % 100}",
            command_name="balance"
        )
        tasks.append(bot_service.forward_to_router(event))

    await asyncio.gather(*tasks)

    elapsed = time.time() - start_time
    throughput = num_events / elapsed

    # Should handle > 100 events/sec (at least)
    assert throughput > 100, f"Throughput too low: {throughput} events/sec"
    print(f"Throughput: {throughput:.0f} events/sec")
```

#### Response Latency

```python
async def test_response_latency():
    """Command response latency < 1 second"""
    latencies = []

    for i in range(100):
        interaction = create_mock_interaction(command_name="balance")

        start = time.time()
        await bot_service.handle_slash_command(interaction)
        elapsed = (time.time() - start) * 1000  # ms

        latencies.append(elapsed)

    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
    max_latency = max(latencies)

    print(f"P95 latency: {p95_latency:.0f}ms")
    print(f"P99 latency: {p99_latency:.0f}ms")
    print(f"Max latency: {max_latency:.0f}ms")

    # Should be < 1000ms
    assert p95_latency < 1000, f"P95 latency too high: {p95_latency}ms"
```

## Smoke Tests

Quick validation before commit (all tests should pass in < 2 minutes).

### Smoke Test Coverage

```bash
# Smoke test suite (subset of all tests)
pytest tests/smoke -v --tb=short

# Or use test controller
./scripts/test-controller.sh smoke discord
```

### Smoke Test Cases

1. Build test - Image builds successfully
2. Health check - `/health` endpoint returns 200
3. Status check - `/api/v1/status` returns valid status
4. Basic command - `/balance` command processes and returns response
5. Error handling - Invalid command returns error
6. Database connectivity - Credentials can be stored and retrieved
7. Router integration - Event forwarded to router successfully

## Test Data and Mocks

### Mock Discord Guilds

```python
MOCK_GUILD = {
    "id": "123456789",
    "name": "Test Guild",
    "icon_url": "https://...",
    "owner_id": "987654321",
    "member_count": 100
}

MOCK_USER = {
    "id": "987654321",
    "username": "testuser",
    "discriminator": "0001"
}
```

### Mock Router Responses

```python
MOCK_EMBED_RESPONSE = {
    "type": "embed",
    "content": {
        "title": "Balance",
        "description": "Your balance",
        "color": "0xFFD700",
        "fields": [
            {"name": "Gold", "value": "1000", "inline": True}
        ]
    }
}

MOCK_BUTTON_RESPONSE = {
    "type": "button",
    "components": [
        {
            "type": "button",
            "label": "Accept",
            "custom_id": "accept_123",
            "style": "success"
        }
    ]
}
```

## Coverage Reports

Generate coverage after tests:

```bash
pytest tests/ --cov=trigger/receiver/discord_module --cov-report=html

# View report
open htmlcov/index.html
```

Target coverages:
- Overall: >= 85%
- Critical paths: 100%
- Error handling: >= 80%
- API endpoints: 100%

## Continuous Integration

Tests run automatically on:
- Every commit to any branch (PR checks)
- Merges to main (full test suite)
- Release tags (all categories)

See `.github/workflows/discord-module-tests.yml` for CI configuration.
