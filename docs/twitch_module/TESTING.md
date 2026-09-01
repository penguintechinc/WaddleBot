# Twitch Module Testing Guide

## Test Framework

The Twitch Module uses pytest for unit and integration testing, with fixtures for mocking Twitch API and database interactions.

**Test Structure**:
```
trigger/receiver/twitch_module/
├── tests/
│   ├── unit/
│   │   ├── test_message_parsing.py
│   │   ├── test_message_splitting.py
│   │   ├── test_hmac_verification.py
│   │   ├── test_cache_manager.py
│   │   └── test_deduplication.py
│   ├── integration/
│   │   ├── test_irc_bot_connection.py
│   │   ├── test_eventsub_webhooks.py
│   │   ├── test_channel_manager_sync.py
│   │   ├── test_viewer_tracker.py
│   │   └── test_api_integration.py
│   ├── e2e/
│   │   ├── test_full_message_flow.py
│   │   ├── test_full_webhook_flow.py
│   │   ├── test_broadcaster_commands.py
│   │   └── test_multi_channel_scenarios.py
│   ├── conftest.py        # Pytest fixtures
│   └── mocks/
│       ├── twitch_api.py   # Mock Twitch API responses
│       └── database.py     # Mock database
```

**Run Tests**:
```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# E2E tests only
pytest tests/e2e/

# Specific test
pytest tests/unit/test_message_splitting.py -v

# With coverage
pytest --cov=src --cov-report=html
```

---

## Unit Tests

### Message Parsing

**File**: `tests/unit/test_message_parsing.py`

Tests IRC message parsing logic.

```python
def test_parse_command_simple():
    """Parse simple command"""
    msg = create_irc_message("!ping", user="testuser")
    result = parse_message(msg)
    assert result.command == "ping"
    assert result.args == []
    assert result.user == "testuser"

def test_parse_command_with_args():
    """Parse command with arguments"""
    msg = create_irc_message("!search pokemon bulbasaur", user="testuser")
    result = parse_message(msg)
    assert result.command == "search"
    assert result.args == ["pokemon", "bulbasaur"]

def test_parse_broadcaster_command():
    """Parse broadcaster-only command"""
    msg = create_irc_message("!!admin ban user123", badges={"broadcaster": "1"})
    result = parse_message(msg)
    assert result.is_broadcaster_command == True
    assert result.command == "admin"
    assert result.is_broadcaster == True

def test_parse_non_broadcaster_denied():
    """Non-broadcaster trying broadcaster command"""
    msg = create_irc_message("!!admin ban user123", badges={})
    result = parse_message(msg)
    assert result.is_broadcaster == False
    assert result.is_broadcaster_command == True
    # Should trigger error response

def test_parse_empty_message():
    """Ignore empty messages"""
    msg = create_irc_message("")
    result = parse_message(msg)
    assert result is None

def test_parse_badges():
    """Extract user badges"""
    msg = create_irc_message("!hi", badges={
        "broadcaster": "1",
        "moderator": "1",
        "subscriber": "3"
    })
    result = parse_message(msg)
    assert result.badges == {
        "broadcaster": "1",
        "moderator": "1",
        "subscriber": "3"
    }
```

**Run**:
```bash
pytest tests/unit/test_message_parsing.py -v
```

---

### Message Splitting

**File**: `tests/unit/test_message_splitting.py`

Tests message splitting logic for messages exceeding 500 chars.

```python
def test_split_short_message():
    """Short message not split"""
    msg = "Hello, world!"
    result = split_message(msg, max_length=500)
    assert result == ["Hello, world!"]

def test_split_long_message():
    """Long message split into multiple parts"""
    msg = "x" * 1500  # 1500 chars
    result = split_message(msg, max_length=500)
    assert len(result) == 3
    assert all(len(part) <= 500 for part in result)

def test_split_preserves_content():
    """Splitting preserves all content"""
    msg = "Test message " * 100  # ~1300 chars
    result = split_message(msg, max_length=500)
    combined = "".join(result)
    assert combined == msg

def test_split_adds_part_numbers():
    """Split messages include part numbers"""
    msg = "x" * 1500
    result = split_message(msg, max_length=500, add_part_numbers=True)
    # Each part should have [N/M] notation
    assert "[1/3]" in result[0]
    assert "[2/3]" in result[1]
    assert "[3/3]" in result[2]

def test_split_respects_word_boundaries():
    """Splitting respects word boundaries when possible"""
    msg = "This is a long message with many words " * 50
    result = split_message(msg, max_length=500, word_boundary=True)
    # No word should be split mid-word (ideally)
    for part in result:
        assert part.strip() == part  # No leading/trailing spaces
```

**Run**:
```bash
pytest tests/unit/test_message_splitting.py -v
```

---

### HMAC Verification

**File**: `tests/unit/test_hmac_verification.py`

Tests EventSub webhook HMAC-SHA256 signature verification.

```python
def test_hmac_verification_valid():
    """Valid signature verified"""
    msg_id = "123e4567-e89b-12d3-a456-426614174000"
    timestamp = "2025-02-24T10:30:00Z"
    body = '{"event": {"type": "subscribe"}}'
    secret = "test_secret_123"

    # Calculate correct signature
    hmac = calculate_hmac(msg_id, timestamp, body, secret)

    # Verify
    result = verify_hmac(msg_id, timestamp, body, hmac, secret)
    assert result == True

def test_hmac_verification_invalid():
    """Invalid signature rejected"""
    msg_id = "123e4567-e89b-12d3-a456-426614174000"
    timestamp = "2025-02-24T10:30:00Z"
    body = '{"event": {"type": "subscribe"}}'
    secret = "test_secret_123"
    bad_hmac = "invalid_signature"

    result = verify_hmac(msg_id, timestamp, body, bad_hmac, secret)
    assert result == False

def test_hmac_verification_body_tampering():
    """Signature fails if body modified"""
    msg_id = "123e4567-e89b-12d3-a456-426614174000"
    timestamp = "2025-02-24T10:30:00Z"
    body = '{"event": {"type": "subscribe"}}'
    secret = "test_secret_123"

    hmac = calculate_hmac(msg_id, timestamp, body, secret)

    # Modify body
    modified_body = '{"event": {"type": "raid"}}'

    result = verify_hmac(msg_id, timestamp, modified_body, hmac, secret)
    assert result == False

def test_hmac_timestamp_old():
    """Old timestamp rejected"""
    msg_id = "123e4567-e89b-12d3-a456-426614174000"
    timestamp = "2025-02-20T10:30:00Z"  # 4 days old
    body = '{"event": {"type": "subscribe"}}'
    secret = "test_secret_123"

    hmac = calculate_hmac(msg_id, timestamp, body, secret)

    result = verify_hmac_with_timestamp_check(msg_id, timestamp, body, hmac, secret)
    assert result == False  # Should reject old timestamp
```

**Run**:
```bash
pytest tests/unit/test_hmac_verification.py -v
```

---

### Cache Manager

**File**: `tests/unit/test_cache_manager.py`

Tests cache get/set operations and TTL.

```python
@pytest.mark.asyncio
async def test_cache_set_and_get():
    """Cache stores and retrieves values"""
    cache = MemoryCache()
    await cache.set("channel:12345", {"name": "example"}, ttl=300)
    result = await cache.get("channel:12345")
    assert result == {"name": "example"}

@pytest.mark.asyncio
async def test_cache_expiry():
    """Cache entries expire after TTL"""
    cache = MemoryCache()
    await cache.set("key", "value", ttl=1)
    # Immediately available
    assert await cache.get("key") == "value"
    # After TTL expires
    await asyncio.sleep(1.1)
    assert await cache.get("key") is None

@pytest.mark.asyncio
async def test_cache_delete():
    """Cache entries deleted on request"""
    cache = MemoryCache()
    await cache.set("key", "value")
    await cache.delete("key")
    assert await cache.get("key") is None

@pytest.mark.asyncio
async def test_cache_redis_fallback():
    """Falls back to API on cache miss"""
    cache = RedisCache()
    # Simulate cache miss
    cache.redis_down = True
    result = await cache.get("channel:99999")
    # Should fallback to API call (mocked)
    assert result is not None
```

**Run**:
```bash
pytest tests/unit/test_cache_manager.py -v
```

---

### Deduplication

**File**: `tests/unit/test_deduplication.py`

Tests EventSub message ID deduplication.

```python
def test_dedup_first_message():
    """First occurrence of message_id not deduplicated"""
    dedup = DeduplicationManager(window_size=100)
    msg_id = "123e4567-e89b-12d3-a456-426614174000"
    result = dedup.check_and_add(msg_id)
    assert result == False  # Not a duplicate

def test_dedup_duplicate():
    """Duplicate message_id recognized"""
    dedup = DeduplicationManager(window_size=100)
    msg_id = "123e4567-e89b-12d3-a456-426614174000"
    dedup.check_and_add(msg_id)
    # Second occurrence
    result = dedup.check_and_add(msg_id)
    assert result == True  # Is a duplicate

def test_dedup_window():
    """Dedup window respects size limit"""
    dedup = DeduplicationManager(window_size=5)
    # Add 5 messages
    for i in range(5):
        dedup.check_and_add(f"msg-{i}")
    # Add 6th message
    dedup.check_and_add("msg-5")
    # First message should be evicted
    result = dedup.check_and_add("msg-0")
    assert result == False  # No longer in window

def test_dedup_order_preserved():
    """FIFO order maintained"""
    dedup = DeduplicationManager(window_size=3)
    dedup.check_and_add("msg-1")
    dedup.check_and_add("msg-2")
    dedup.check_and_add("msg-3")
    dedup.check_and_add("msg-4")  # Evicts msg-1
    # Check order
    assert dedup.window == ["msg-2", "msg-3", "msg-4"]
```

**Run**:
```bash
pytest tests/unit/test_deduplication.py -v
```

---

## Integration Tests

### IRC Bot Connection

**File**: `tests/integration/test_irc_bot_connection.py`

Tests IRC bot connection and message handling.

```python
@pytest.mark.asyncio
async def test_bot_connects_to_irc():
    """Bot establishes IRC connection"""
    bot = TwitchBotService(mock_config)
    await bot.start()
    assert bot.connected == True
    await bot.stop()

@pytest.mark.asyncio
async def test_bot_joins_channel():
    """Bot joins channel successfully"""
    bot = TwitchBotService(mock_config)
    await bot.start()
    await bot.join_channel("example_channel")
    assert "example_channel" in bot.active_channels
    await bot.stop()

@pytest.mark.asyncio
async def test_bot_receives_message():
    """Bot receives and processes chat message"""
    bot = TwitchBotService(mock_config)
    received_messages = []

    async def capture_message(msg):
        received_messages.append(msg)

    bot.register_message_handler(capture_message)
    await bot.start()

    # Simulate incoming message (via mock IRC connection)
    await bot._on_message_received({
        "channel": "#example_channel",
        "author": "testuser",
        "content": "!ping"
    })

    assert len(received_messages) == 1
    assert received_messages[0].command == "ping"
    await bot.stop()

@pytest.mark.asyncio
async def test_bot_sends_message():
    """Bot sends message to channel"""
    bot = TwitchBotService(mock_config)
    await bot.start()

    response = await bot.send_message("example_channel", "Hello, chat!")
    assert response.status == "sent"
    await bot.stop()

@pytest.mark.asyncio
async def test_bot_reconnection():
    """Bot reconnects on connection loss"""
    bot = TwitchBotService(mock_config)
    await bot.start()

    # Simulate connection drop
    await bot._on_connection_lost()

    # Bot should reconnect
    await asyncio.sleep(2)
    assert bot.connected == True
    await bot.stop()
```

**Run**:
```bash
pytest tests/integration/test_irc_bot_connection.py -v
```

---

### EventSub Webhooks

**File**: `tests/integration/test_eventsub_webhooks.py`

Tests EventSub webhook reception and processing.

```python
@pytest.mark.asyncio
async def test_eventsub_webhook_subscribe():
    """Process channel.subscribe webhook"""
    client = AsyncClient(app)

    msg_id = "123e4567-e89b-12d3-a456-426614174000"
    timestamp = "2025-02-24T10:30:00Z"
    body = json.dumps({
        "subscription": {
            "type": "channel.subscribe",
            "id": "sub-123"
        },
        "event": {
            "broadcaster_user_id": "12345",
            "broadcaster_user_name": "ChannelOwner",
            "user_id": "67890",
            "user_login": "new_subscriber",
            "tier": "1000",
            "is_gift": False
        }
    })

    hmac = calculate_hmac(msg_id, timestamp, body, EVENTSUB_SECRET)

    response = await client.post("/eventsub/webhook",
        headers={
            "Twitch-Eventsub-Message-Id": msg_id,
            "Twitch-Eventsub-Timestamp": timestamp,
            "Twitch-Eventsub-Signature": f"sha256={hmac}"
        },
        content=body
    )

    assert response.status_code == 200
    assert response.json()["status"] == "received"

@pytest.mark.asyncio
async def test_eventsub_webhook_invalid_signature():
    """Reject webhook with invalid signature"""
    client = AsyncClient(app)

    bad_hmac = "invalid_signature_123"
    response = await client.post("/eventsub/webhook",
        headers={
            "Twitch-Eventsub-Message-Id": "msg-123",
            "Twitch-Eventsub-Timestamp": "2025-02-24T10:30:00Z",
            "Twitch-Eventsub-Signature": f"sha256={bad_hmac}"
        },
        json={"event": {}}
    )

    assert response.status_code == 403
```

**Run**:
```bash
pytest tests/integration/test_eventsub_webhooks.py -v
```

---

### Channel Manager Sync

**File**: `tests/integration/test_channel_manager_sync.py`

Tests database channel sync and join/leave operations.

```python
@pytest.mark.asyncio
async def test_channel_manager_loads_from_db():
    """Load channels from database"""
    manager = ChannelManager(mock_db)
    await manager.refresh_channels()

    channels = await manager.get_channels()
    assert len(channels) > 0
    assert all(ch.is_active for ch in channels)

@pytest.mark.asyncio
async def test_channel_manager_detects_new_channels():
    """Detect new channels to join"""
    manager = ChannelManager(mock_db)

    # Load initial channels
    await manager.refresh_channels()

    # Add new channel to database
    mock_db.add_channel("new_channel")

    # Refresh and detect
    new_channels = await manager.get_new_channels()
    assert "new_channel" in new_channels

@pytest.mark.asyncio
async def test_channel_manager_detects_removed_channels():
    """Detect channels to leave"""
    manager = ChannelManager(mock_db)

    # Load initial channels
    await manager.refresh_channels()

    # Mark channel as inactive
    mock_db.update_channel("old_channel", is_active=False)

    # Refresh and detect
    removed_channels = await manager.get_removed_channels()
    assert "old_channel" in removed_channels
```

**Run**:
```bash
pytest tests/integration/test_channel_manager_sync.py -v
```

---

## E2E Tests

### Full Message Flow

**File**: `tests/e2e/test_full_message_flow.py`

Tests complete message flow from IRC to Router and back.

```python
@pytest.mark.asyncio
async def test_message_flow_command_response():
    """Full flow: IRC → Router → Response"""
    # Setup
    bot = TwitchBotService(mock_config)
    router = MockRouter()
    await bot.start()

    # User sends command
    await bot._on_message_received({
        "channel": "#example_channel",
        "author": "testuser",
        "content": "!ping"
    })

    # Router receives message
    call = router.last_call
    assert call.method == "POST"
    assert call.path == "/api/v1/messages"
    assert call.body.command == "ping"

    # Router responds
    router.set_response(MessageResponse(
        status="success",
        response="pong! Latency: 45ms"
    ))

    # Bot sends response
    await asyncio.sleep(1)  # Wait for processing

    sent_messages = bot.sent_messages
    assert len(sent_messages) == 1
    assert "pong! Latency: 45ms" in sent_messages[0]

    await bot.stop()

@pytest.mark.asyncio
async def test_message_flow_with_splitting():
    """Message split across multiple sends"""
    bot = TwitchBotService(mock_config)
    await bot.start()

    # Simulate long response
    long_message = "x" * 1500
    await bot._on_message_received({
        "channel": "#example_channel",
        "author": "testuser",
        "content": "!longcommand"
    })

    # Wait for response
    await asyncio.sleep(2)

    # Check message was split
    sent_messages = bot.sent_messages
    assert len(sent_messages) >= 2  # Split into multiple messages

    await bot.stop()
```

**Run**:
```bash
pytest tests/e2e/test_full_message_flow.py -v
```

---

### Broadcaster Commands

**File**: `tests/e2e/test_broadcaster_commands.py`

Tests broadcaster-only command enforcement.

```python
@pytest.mark.asyncio
async def test_broadcaster_command_allowed():
    """Broadcaster can use !! commands"""
    bot = TwitchBotService(mock_config)
    await bot.start()

    await bot._on_message_received({
        "channel": "#example_channel",
        "author": "channel_owner",
        "content": "!!ban spamuser",
        "badges": {"broadcaster": "1"}
    })

    # Router should receive the command
    assert bot.last_router_call.body.command == "ban"
    await bot.stop()

@pytest.mark.asyncio
async def test_broadcaster_command_denied():
    """Non-broadcaster cannot use !! commands"""
    bot = TwitchBotService(mock_config)
    await bot.start()

    await bot._on_message_received({
        "channel": "#example_channel",
        "author": "random_user",
        "content": "!!ban spamuser",
        "badges": {}
    })

    # Should not send to router
    assert bot.last_router_call is None

    # Should send error response
    error_messages = bot.sent_messages
    assert any("restricted" in msg.lower() for msg in error_messages)

    await bot.stop()
```

**Run**:
```bash
pytest tests/e2e/test_broadcaster_commands.py -v
```

---

## Manual Testing

### Test Checklist

**Before committing changes, verify**:

1. **Service startup**
   ```bash
   docker-compose up trigger-twitch
   curl http://localhost:8002/health
   # Should return 200
   ```

2. **Database connection**
   ```bash
   curl http://localhost:8002/api/v1/status | jq '.database.connected'
   # Should be: true
   ```

3. **Bot connection**
   ```bash
   curl http://localhost:8002/api/v1/bot/channels | jq '.channels | length'
   # Should be: > 0
   ```

4. **Message sending**
   ```bash
   curl -X POST http://localhost:8002/api/v1/bot/send \
     -H "Authorization: Bearer test-key" \
     -d '{"channel_id": "12345", "message": "Test message"}'
   # Should return 200
   ```

5. **EventSub webhook**
   ```bash
   # Use test script in tests/manual/
   python tests/manual/send_eventsub_test.py
   ```

6. **Message splitting**
   ```bash
   # Send 1500-char message
   python tests/manual/test_message_split.py
   # Should see multiple messages in bot output
   ```

---

### Smoke Tests (Pre-Commit)

**Run before every commit**:

```bash
# Unit tests (fast)
pytest tests/unit/ -x

# Quick integration test
pytest tests/integration/test_irc_bot_connection.py -x

# API health check
curl http://localhost:8002/health

# No test failures
echo $?  # Should be 0
```

---

## CI/CD Integration

GitHub Actions workflow (`.github/workflows/twitch-module-test.yml`):

```yaml
name: Twitch Module Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
      redis:
        image: redis:7

    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - run: pip install -r trigger/receiver/twitch_module/requirements.txt

      - run: pytest trigger/receiver/twitch_module/tests/unit/ -v

      - run: pytest trigger/receiver/twitch_module/tests/integration/ -v

      - run: pytest trigger/receiver/twitch_module/tests/e2e/ -v

      - uses: codecov/codecov-action@v3
```

---

## Coverage Goals

Maintain minimum coverage:
- **Unit tests**: 90%+
- **Integration tests**: 80%+
- **E2E tests**: Key user flows

**Check coverage**:
```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```
