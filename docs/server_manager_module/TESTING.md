# Server Manager Interaction Module - Testing Guide

## Test Strategy

The Server Manager Interaction Module requires testing across five distinct areas:

1. **Encryption/Decryption** — credentials must round-trip correctly
2. **RCON Protocol** — command dispatch, player operations, connection pooling
3. **Voice Server Protocols** — Mumble Ice RPC and TeamSpeak ServerQuery
4. **Enforcement Engine** — reputation threshold evaluation and action dispatch
5. **Audit Logging** — every action is persisted correctly and immutably

All service methods are async and must be tested in an async context with `pytest-asyncio`.

---

## Test Categories

### Unit Tests

Tests for individual service methods in isolation, using mocked external connections.

#### encryption_service.py

```python
import pytest
from services.encryption_service import EncryptionService

def test_decrypt_roundtrip():
    key_hex = "a" * 64  # 32-byte test key
    service = EncryptionService(key_hex)

    plaintext = "super_secret_rcon_password"
    # Simulate what the hub backend produces
    ciphertext = service.encrypt_for_test(plaintext)  # test-only helper
    result = service.decrypt(ciphertext)
    assert result == plaintext

def test_wrong_key_raises():
    service_a = EncryptionService("a" * 64)
    service_b = EncryptionService("b" * 64)

    ciphertext = service_a.encrypt_for_test("password")
    with pytest.raises(Exception):
        service_b.decrypt(ciphertext)

def test_invalid_key_length_raises():
    with pytest.raises(ValueError):
        EncryptionService("tooshort")
```

#### enforcement_service.py

```python
@pytest.mark.asyncio
async def test_enforcement_kicks_below_threshold(mock_dal, mock_rcon_service):
    service = EnforcementService(mock_dal, mock_rcon_service)

    # Policy: kick < 400, ban < 320
    mock_dal.policy_returns({
        "reputation_kick_threshold": 400,
        "reputation_ban_threshold": 320
    })

    # Players: one below kick threshold, one above
    mock_rcon_service.player_list_returns([
        {"identifier": "STEAM_A", "reputation_score": 385},
        {"identifier": "STEAM_B", "reputation_score": 720},
    ])

    result = await service.enforce_server(community_id=1, server_id=7, actor_user_id=1)

    assert result["players_evaluated"] == 2
    assert result["players_kicked"] == 1
    assert result["players_banned"] == 0
    assert result["actions"][0]["player"] == "STEAM_A"
    assert result["actions"][0]["action"] == "kick"

@pytest.mark.asyncio
async def test_enforcement_bans_below_ban_threshold(mock_dal, mock_rcon_service):
    service = EnforcementService(mock_dal, mock_rcon_service)
    mock_dal.policy_returns({"reputation_kick_threshold": 400, "reputation_ban_threshold": 320})
    mock_rcon_service.player_list_returns([
        {"identifier": "STEAM_C", "reputation_score": 300}
    ])

    result = await service.enforce_server(community_id=1, server_id=7, actor_user_id=1)
    assert result["players_banned"] == 1

@pytest.mark.asyncio
async def test_enforcement_no_policy_skips():
    # No policy set → enforcement should no-op gracefully
    service = EnforcementService(mock_dal_no_policy, mock_rcon_service)
    result = await service.enforce_server(community_id=1, server_id=7, actor_user_id=1)
    assert result["players_evaluated"] == 0
```

#### provider_service.py

```python
def test_routes_rcon_to_rcon_service():
    provider = ProviderService(rcon_svc, mumble_svc, ts_svc)
    svc = provider.get_service("rcon")
    assert svc is rcon_svc

def test_routes_mumble_to_mumble_service():
    provider = ProviderService(rcon_svc, mumble_svc, ts_svc)
    svc = provider.get_service("mumble")
    assert svc is mumble_svc

def test_routes_teamspeak_to_ts_service():
    provider = ProviderService(rcon_svc, mumble_svc, ts_svc)
    svc = provider.get_service("teamspeak")
    assert svc is ts_svc

def test_unknown_type_raises():
    provider = ProviderService(rcon_svc, mumble_svc, ts_svc)
    with pytest.raises(ValueError, match="Unknown server_type"):
        provider.get_service("irc")
```

---

### Integration Tests

Tests that verify interactions between services and the database.

#### Command Execution + Audit Log

```python
@pytest.mark.asyncio
async def test_command_execution_writes_log(db_session):
    service = RconService(db_session, encryption_service)

    # Execute command (against a mock RCON server)
    result = await service.execute_command(
        community_id=1,
        server_id=7,
        command="say Hello",
        executed_by_user_id=1001
    )

    assert result["success"] is True
    assert result["log_id"] is not None

    # Verify log entry
    log = await db_session.fetchrow(
        "SELECT * FROM rcon_command_log WHERE id = $1", result["log_id"]
    )
    assert log["command"] == "say Hello"
    assert log["executed_by_user_id"] == 1001
    assert log["success"] is True

@pytest.mark.asyncio
async def test_failed_command_still_logs(db_session):
    # Even when RCON returns an error, it should be logged
    result = await rcon_service.execute_command(
        community_id=1, server_id=7,
        command="invalid.command.xyz",
        executed_by_user_id=1001
    )

    log = await db_session.fetchrow(
        "SELECT success FROM rcon_command_log WHERE id = $1", result["log_id"]
    )
    assert log["success"] is False
```

#### Kick/Ban + Access Log

```python
@pytest.mark.asyncio
async def test_kick_writes_access_log(db_session):
    result = await rcon_service.kick_player(
        community_id=1,
        server_id=7,
        player_identifier="STEAM_12345",
        reason="Test kick",
        actor_user_id=1001
    )
    assert result["success"] is True

    log = await db_session.fetchrow(
        "SELECT * FROM server_access_log WHERE id = $1", result["log_id"]
    )
    assert log["action"] == "kick"
    assert log["target_player_identifier"] == "STEAM_12345"
    assert log["auto_enforced"] is False

@pytest.mark.asyncio
async def test_ban_with_sync_writes_ban_sync_records(db_session):
    result = await enforcement_service.ban_player(
        community_id=1,
        server_id=7,
        player_identifier="STEAM_12345",
        reason="Cheating",
        actor_user_id=1001,
        sync_to_all_servers=True
    )

    # Verify sync records were created for other servers
    sync_records = await db_session.fetch(
        "SELECT * FROM server_ban_sync WHERE community_id = 1 AND player_identifier = $1",
        "STEAM_12345"
    )
    assert len(sync_records) > 0
    assert all(r["synced"] is True for r in sync_records)
```

#### Policy CRUD

```python
@pytest.mark.asyncio
async def test_create_and_retrieve_policy(db_session):
    # Create
    policy = await policy_service.set_policy(
        community_id=1,
        server_id=7,
        policy_type="reputation_threshold",
        reputation_kick_threshold=420,
        reputation_ban_threshold=340
    )
    assert policy["reputation_kick_threshold"] == 420

    # Retrieve
    fetched = await policy_service.get_policy(community_id=1, server_id=7)
    assert fetched["reputation_kick_threshold"] == 420
    assert fetched["reputation_ban_threshold"] == 340

@pytest.mark.asyncio
async def test_update_policy(db_session):
    await policy_service.set_policy(1, 7, "reputation_threshold", 420, 340)
    updated = await policy_service.set_policy(1, 7, "reputation_threshold", 500, 400)
    assert updated["reputation_kick_threshold"] == 500

@pytest.mark.asyncio
async def test_server_without_policy_returns_none(db_session):
    result = await policy_service.get_policy(community_id=99, server_id=99)
    assert result is None
```

---

### Smoke Tests

Quick validation that the module is running correctly.

```bash
# Is the module healthy?
curl -f http://localhost:8098/health && echo "PASS: health"

# Is the API responding?
curl -f http://localhost:8098/api/v1/status && echo "PASS: status"

# Is the database connected (check health response)?
curl -s http://localhost:8098/health | python3 -m json.tool | grep '"database": "connected"'

# Backward-compat route still works?
curl -f http://localhost:8098/api/v1/server-status/status && echo "PASS: backward compat"
```

---

### End-to-End Tests

Simulate real-world admin workflows.

#### E2E: Add Server, Test, Execute Command, Review Log

```python
@pytest.mark.asyncio
async def test_full_admin_workflow(test_client, community_id=42):
    # 1. Test connection before saving
    resp = await test_client.post(
        f"/api/v1/server-manager/{community_id}/connect-test",
        json={
            "server_type": "rcon",
            "game_type": "minecraft",
            "host": TEST_MC_HOST,
            "port": TEST_MC_RCON_PORT,
            "password": TEST_MC_RCON_PASS
        }
    )
    assert resp.status_code == 200
    assert resp.json["success"] is True

    # 2. Execute a command
    resp = await test_client.post(
        f"/api/v1/server-manager/{community_id}/command",
        json={
            "server_id": TEST_SERVER_ID,
            "command": "list",
            "executed_by_user_id": 1001
        }
    )
    assert resp.status_code == 200
    log_id = resp.json["log_id"]
    assert log_id is not None

    # 3. Access log records the command
    resp = await test_client.get(
        f"/api/v1/server-manager/{community_id}/servers/{TEST_SERVER_ID}/access-log"
    )
    assert resp.status_code == 200
```

#### E2E: Set Policy and Run Enforcement

```python
@pytest.mark.asyncio
async def test_policy_and_enforcement(test_client):
    community_id = 42
    server_id = TEST_SERVER_ID

    # Set a strict policy
    resp = await test_client.put(
        f"/api/v1/server-manager/{community_id}/servers/{server_id}/policy",
        json={
            "policy_type": "reputation_threshold",
            "reputation_kick_threshold": 800,  # Very strict — kick almost everyone
            "reputation_ban_threshold": 300
        }
    )
    assert resp.status_code == 200

    # Trigger enforcement
    resp = await test_client.post(
        f"/api/v1/server-manager/{community_id}/servers/{server_id}/enforce",
        json={"actor_user_id": 1001}
    )
    assert resp.status_code == 200
    assert "players_evaluated" in resp.json
```

---

## Test Data Setup

### Sample Server Configurations

```python
test_servers = [
    {
        "name": "Rust Main",
        "server_type": "rcon",
        "game_type": "rust",
        "host": "rust-test.internal",
        "port": 28015,
        "rcon_port": 28016,
    },
    {
        "name": "Minecraft SMP",
        "server_type": "rcon",
        "game_type": "minecraft",
        "host": "mc-test.internal",
        "port": 25565,
        "rcon_port": 25575,
    },
    {
        "name": "Community Mumble",
        "server_type": "mumble",
        "game_type": None,
        "host": "mumble-test.internal",
        "port": 64738,
    },
    {
        "name": "TeamSpeak 3",
        "server_type": "teamspeak",
        "game_type": None,
        "host": "ts-test.internal",
        "port": 9987,
    }
]

test_policies = [
    {
        "server_id": 1,  # Rust
        "policy_type": "reputation_threshold",
        "reputation_kick_threshold": 420,
        "reputation_ban_threshold": 340
    },
    {
        "server_id": 2,  # Minecraft
        "policy_type": "reputation_threshold",
        "reputation_kick_threshold": 380,
        "reputation_ban_threshold": 310
    }
]
```

### Pytest Fixtures

```python
import pytest
import pytest_asyncio

@pytest_asyncio.fixture
async def db_session():
    dal = await init_test_database()  # Uses test PostgreSQL or SQLite
    yield dal
    await dal.close()

@pytest_asyncio.fixture
async def test_servers(db_session):
    created = []
    for server_data in test_servers:
        server = await db_session.execute(
            "INSERT INTO server_status_configs (...) VALUES (...) RETURNING *",
            list(server_data.values())
        )
        created.append(server)
    return created

@pytest_asyncio.fixture
async def encryption_service():
    return EncryptionService("a" * 64)  # Deterministic test key

@pytest.fixture
def mock_rcon_client():
    """Returns a mock RCON client that echoes commands."""
    class MockRcon:
        async def execute(self, cmd):
            return f"MOCK RESPONSE: {cmd}"
        async def connect(self): pass
        async def disconnect(self): pass
    return MockRcon()
```

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific test file
pytest tests/test_enforcement_service.py -v

# With coverage
pytest tests/ --cov=action/interactive/server_manager_interaction_module \
    --cov-report=html:coverage/server_manager

# Debug a failing test
pytest tests/test_rcon_service.py::test_command_execution_writes_log -v -s --pdb
```

---

## Validation Procedures

### Pre-Deployment Validation

1. All unit tests pass with 100% success
2. Integration tests pass against a real (or realistic mock) PostgreSQL instance
3. Migration 055 applied successfully — all new tables exist
4. Backward-compat routes return the same responses as the old module
5. Encryption key validation: module starts with a 64-char hex key
6. SSRF protection: `connect-test` with a private IP returns `SSRF_BLOCKED`

### Data Integrity SQL Checks

```sql
-- Every command log has a valid server_id
SELECT COUNT(*) FROM rcon_command_log c
LEFT JOIN server_status_configs s ON c.server_id = s.id
WHERE s.id IS NULL;
-- Expected: 0

-- Every access log entry has a valid server_id
SELECT COUNT(*) FROM server_access_log a
LEFT JOIN server_status_configs s ON a.server_id = s.id
WHERE s.id IS NULL;
-- Expected: 0

-- No duplicate policies per server
SELECT community_id, server_id, COUNT(*)
FROM server_access_policies
GROUP BY 1, 2
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Verify ban sync completed
SELECT COUNT(*) FROM server_ban_sync WHERE synced = FALSE;
-- Expected: 0 (or small number of in-progress syncs)
```

### Backward Compatibility Check

```bash
# These routes must return HTTP 200 (same as old server_status_interaction_module)
curl -f http://localhost:8098/api/v1/server-status/status
# Add any previously known backward-compat routes here
```

---

**Module**: server_manager_interaction_module
**Version**: 1.0.0
**Last Updated**: 2026-02-24
