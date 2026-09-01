# Loyalty Interaction Module — Testing & Validation Guide

Complete testing strategy, fixtures, and procedures for validating loyalty system functionality.

## Table of Contents

1. [Test Strategy](#test-strategy)
2. [Unit Tests](#unit-tests)
3. [Integration Tests](#integration-tests)
4. [Fixtures & Mock Data](#fixtures--mock-data)
5. [API Testing](#api-testing)
6. [Load Testing](#load-testing)
7. [Running Tests](#running-tests)

## Test Strategy

### Testing Pyramid

```
         /\
        /  \
       / E2E \         - Full workflows (10%)
      /______\
      /      \
     /  API   \       - Endpoint tests (30%)
    /________\
    /          \
   / Unit Tests \    - Service logic (60%)
  /____________\
```

### Test Coverage Goals

- **Critical Path:** 95%+ coverage (currency transactions, games)
- **Services:** 90%+ coverage (business logic)
- **API Endpoints:** 85%+ coverage (request/response)
- **Edge Cases:** 80%+ coverage (error conditions)

### Test Types

| Type | Focus | Tools | Count |
|------|-------|-------|-------|
| Unit | Services in isolation | pytest, unittest | 50+ |
| Integration | Service interaction | pytest-asyncio | 30+ |
| API | HTTP endpoints | httpx, pytest | 25+ |
| Load | Performance | locust, k6 | 5+ |
| E2E | Full workflows | selenium/playwright | 10+ |

## Unit Tests

### Currency Service Tests

**Test: Balance Retrieval**
```python
@pytest.mark.asyncio
async def test_get_balance_user_exists():
    """Should return balance for existing user"""
    dal = MagicMock()
    dal.execute = AsyncMock(return_value=[{
        'balance': 1000,
        'lifetime_earned': 2000,
        'lifetime_spent': 1000
    }])

    service = CurrencyService(dal)
    balance = await service.get_balance(1, 'twitch', 'user123')

    assert balance.balance == 1000
    assert balance.lifetime_earned == 2000
    dal.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_balance_user_not_found():
    """Should return zero balance for new user"""
    dal = MagicMock()
    dal.execute = AsyncMock(return_value=[])

    service = CurrencyService(dal)
    balance = await service.get_balance(1, 'twitch', 'user123')

    assert balance.balance == 0
    assert balance.lifetime_earned == 0
```

**Test: Add Currency**
```python
@pytest.mark.asyncio
async def test_add_currency_success():
    """Should add currency and return new balance"""
    dal = MagicMock()
    dal.execute = AsyncMock(side_effect=[
        # get current balance
        [{'balance': 500}],
        # update balance
        [None],
        # insert transaction
        [None],
        # get new balance
        [{'balance': 1000}]
    ])

    service = CurrencyService(dal)
    result = await service.add_currency(
        community_id=1,
        platform='twitch',
        platform_user_id='user123',
        amount=500,
        reason='test'
    )

    assert result.success == True
    assert result.new_balance == 1000

@pytest.mark.asyncio
async def test_add_currency_zero_amount():
    """Should reject zero amount"""
    dal = MagicMock()
    service = CurrencyService(dal)

    with pytest.raises(ValueError):
        await service.add_currency(1, 'twitch', 'user123', 0, 'test')
```

**Test: Transfer Currency**
```python
@pytest.mark.asyncio
async def test_transfer_success():
    """Should transfer currency between users"""
    dal = MagicMock()
    service = CurrencyService(dal)

    result = await service.transfer(
        community_id=1,
        platform='twitch',
        from_user_id='sender',
        to_user_id='receiver',
        amount=100
    )

    assert result.success == True
    # Verify both users' balances were updated
    assert dal.execute.call_count >= 2

@pytest.mark.asyncio
async def test_transfer_insufficient_balance():
    """Should reject transfer with insufficient balance"""
    dal = MagicMock()
    dal.execute = AsyncMock(return_value=[{'balance': 50}])
    service = CurrencyService(dal)

    with pytest.raises(InsufficientFundsError):
        await service.transfer(1, 'twitch', 'sender', 'receiver', 100)

@pytest.mark.asyncio
async def test_transfer_to_self_rejected():
    """Should reject transfer to self"""
    dal = MagicMock()
    service = CurrencyService(dal)

    with pytest.raises(ValueError, match='cannot transfer'):
        await service.transfer(1, 'twitch', 'user', 'user', 100)
```

### Minigame Service Tests

**Test: Slots Game**
```python
@pytest.mark.asyncio
async def test_play_slots_win():
    """Should handle slots win"""
    dal = MagicMock()
    dal.execute = AsyncMock(side_effect=[
        [{'balance': 500}],  # check balance
        [None],  # deduct bet
        [None],  # add winnings
        [{'balance': 650}]   # get new balance
    ])

    service = MinigameService(dal)
    result = await service.play_slots(
        community_id=1,
        platform='twitch',
        platform_user_id='gambler',
        bet=50
    )

    assert result.success == True
    assert result.won in [True, False]  # Should be determined
    assert result.new_balance >= 0

@pytest.mark.asyncio
async def test_play_slots_insufficient_balance():
    """Should reject bet with insufficient balance"""
    dal = MagicMock()
    dal.execute = AsyncMock(return_value=[{'balance': 5}])

    service = MinigameService(dal)
    with pytest.raises(InsufficientFundsError):
        await service.play_slots(1, 'twitch', 'gambler', 100)
```

**Test: Coinflip Game**
```python
@pytest.mark.asyncio
async def test_play_coinflip_valid_choice():
    """Should accept heads or tails"""
    dal = MagicMock()
    service = MinigameService(dal)

    # Test heads
    result = await service.play_coinflip(1, 'twitch', 'gambler', 50, 'heads')
    assert result.result in ['heads', 'tails']

    # Test tails
    result = await service.play_coinflip(1, 'twitch', 'gambler', 50, 'tails')
    assert result.result in ['heads', 'tails']

@pytest.mark.asyncio
async def test_play_coinflip_invalid_choice():
    """Should reject invalid choice"""
    dal = MagicMock()
    service = MinigameService(dal)

    with pytest.raises(ValueError, match='heads or tails'):
        await service.play_coinflip(1, 'twitch', 'gambler', 50, 'invalid')
```

### Duel Service Tests

**Test: Create Challenge**
```python
@pytest.mark.asyncio
async def test_create_duel_success():
    """Should create duel challenge"""
    dal = MagicMock()
    service = DuelService(dal)

    result = await service.create_challenge(
        community_id=1,
        platform='twitch',
        challenger_id='player_a',
        opponent_id='player_b',
        wager=100
    )

    assert result.success == True
    assert result.duel_id > 0

@pytest.mark.asyncio
async def test_create_duel_self_challenge():
    """Should reject self-challenge"""
    dal = MagicMock()
    service = DuelService(dal)

    with pytest.raises(ValueError, match='cannot duel yourself'):
        await service.create_challenge(
            1, 'twitch', 'player_a', 'player_a', 100
        )
```

## Integration Tests

### Currency & Transaction Flow

**Test: Chat Earning Process**
```python
@pytest.mark.asyncio
async def test_chat_earning_integration():
    """Should process chat earning with config"""
    dal = AsyncMock()
    currency_service = CurrencyService(dal)
    earning_service = EarningConfigService(dal, currency_service)

    # 1. Get earning config
    config = await earning_service.get_config(1)
    assert config.earn_chat == 1

    # 2. Process chat earning
    result = await earning_service.process_chat_earning(
        community_id=1,
        platform='twitch',
        platform_user_id='chatter'
    )

    # 3. Verify earning
    assert result.earned == True
    assert result.amount == 1
    assert result.new_balance >= 1
```

### Event Earning Process

**Test: Subscription Earning**
```python
@pytest.mark.asyncio
async def test_subscription_earning():
    """Should award points for subscription"""
    dal = AsyncMock()
    service = EarningConfigService(dal, CurrencyService(dal))

    result = await service.process_event_earning(
        community_id=1,
        platform='twitch',
        platform_user_id='sub_user',
        event_type='sub_t2',
        event_data={'tier': 2}
    )

    assert result.earned == True
    assert result.amount == 1000  # Default T2 earning
```

### Giveaway Entry & Drawing

**Test: Giveaway Workflow**
```python
@pytest.mark.asyncio
async def test_giveaway_entry_and_draw():
    """Should handle giveaway entry and winner drawing"""
    dal = AsyncMock()
    service = GiveawayService(dal, CurrencyService(dal))

    # 1. Create giveaway
    giveaway = await service.create_giveaway(
        community_id=1,
        title='Test Giveaway',
        prize='Prize',
        entry_cost=100,
        duration_minutes=60,
        max_entries=100,
        reputation_weighted=False
    )
    assert giveaway.giveaway_id > 0

    # 2. Enter giveaway
    result = await service.enter_giveaway(
        community_id=1,
        giveaway_id=giveaway.giveaway_id,
        platform='twitch',
        platform_user_id='player1'
    )
    assert result.success == True
    assert result.entry_number == 1

    # 3. Draw winner
    draw_result = await service.draw_winner(
        community_id=1,
        giveaway_id=giveaway.giveaway_id
    )
    assert draw_result.success == True
    assert draw_result.winner_user_id is not None
```

## Fixtures & Mock Data

### Pytest Fixtures

**Database Fixture**
```python
@pytest.fixture
async def test_dal():
    """Mock database access layer"""
    dal = AsyncMock()
    dal.execute = AsyncMock(return_value=[])
    return dal

@pytest.fixture
async def currency_service(test_dal):
    """Currency service with mock DAL"""
    return CurrencyService(test_dal)

@pytest.fixture
async def earning_service(test_dal, currency_service):
    """Earning service with mocks"""
    return EarningConfigService(test_dal, currency_service)
```

**Test Data Fixture**
```python
@pytest.fixture
def sample_users():
    """Sample user data"""
    return {
        'user1': {'user_id': 'user1', 'platform': 'twitch', 'balance': 1000},
        'user2': {'user_id': 'user2', 'platform': 'twitch', 'balance': 500},
        'user3': {'user_id': 'user3', 'platform': 'discord', 'balance': 2000},
    }

@pytest.fixture
def sample_earning_config():
    """Sample earning configuration"""
    return {
        'earn_chat': 1,
        'earn_chat_cooldown': 60,
        'earn_watch_time': 2,
        'earn_follow': 50,
        'earn_sub_t1': 500,
        'earn_sub_t2': 1000,
        'earn_sub_t3': 2500,
    }
```

### Mock Data Generation

**Seeding Test Community**
```python
async def seed_test_community():
    """Create test data for community"""
    dal = init_database(DATABASE_URL)
    currency_service = CurrencyService(dal)

    # Create users
    users = ['player1', 'player2', 'player3', 'gambler1', 'duelist1']
    for user in users:
        await currency_service.add_currency(
            community_id=1,
            platform='twitch',
            platform_user_id=user,
            amount=1000,
            reason='test_setup'
        )

    # Create giveaway
    giveaway_service = GiveawayService(dal, currency_service)
    await giveaway_service.create_giveaway(
        community_id=1,
        title='Test Giveaway',
        prize='Test Prize',
        entry_cost=50,
        duration_minutes=60,
        max_entries=100
    )

    return dal, currency_service, giveaway_service
```

## API Testing

### Test Suite with pytest & httpx

**Endpoint Tests**
```python
@pytest.mark.asyncio
async def test_get_balance_endpoint(client):
    """Test GET /currency/{community_id}/balance/{user_id}"""
    response = await client.get(
        '/api/v1/loyalty/currency/1/balance/user123',
        params={'platform': 'twitch'}
    )

    assert response.status_code == 200
    data = response.json()
    assert 'balance' in data['data']
    assert 'lifetime_earned' in data['data']

@pytest.mark.asyncio
async def test_add_currency_endpoint(client, auth_token):
    """Test POST /currency/{community_id}/add"""
    response = await client.post(
        '/api/v1/loyalty/currency/1/add',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={
            'user_id': 'user123',
            'amount': 500,
            'reason': 'test',
            'platform': 'twitch'
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data['data']['success'] == True

@pytest.mark.asyncio
async def test_invalid_bet_amount(client):
    """Test bet amount validation"""
    # Bet too low
    response = await client.post(
        '/api/v1/loyalty/games/1/slots',
        json={
            'community_id': 1,
            'user_id': 'gambler',
            'bet': 1,  # Below MIN_BET
            'platform': 'twitch'
        }
    )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_transfer_to_self_rejected(client):
    """Test self-transfer validation"""
    response = await client.post(
        '/api/v1/loyalty/currency/1/transfer',
        json={
            'community_id': 1,
            'from_user_id': 'user',
            'to_user_id': 'user',  # Same user
            'amount': 100,
            'platform': 'twitch'
        }
    )
    assert response.status_code == 400
```

### Bash Test Script

**test-api.sh**
```bash
#!/bin/bash

set -e

API="http://localhost:8032/api/v1/loyalty"
COMMUNITY=1
USER="test_user_$$"

echo "Testing Loyalty Module API..."

# Test 1: Get Balance (non-existent user)
echo "Test 1: Get balance for new user..."
curl -s "$API/currency/$COMMUNITY/balance/$USER?platform=twitch" | jq '.'

# Test 2: Add Currency
echo -e "\nTest 2: Add 500 currency..."
curl -s -X POST "$API/currency/$COMMUNITY/add" \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER'",
    "amount": 500,
    "reason": "test",
    "platform": "twitch"
  }' | jq '.'

# Test 3: Check Balance
echo -e "\nTest 3: Check balance..."
curl -s "$API/currency/$COMMUNITY/balance/$USER?platform=twitch" | jq '.'

# Test 4: Play Slots
echo -e "\nTest 4: Play slots with 50 bet..."
curl -s -X POST "$API/games/$COMMUNITY/slots" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": '$COMMUNITY',
    "user_id": "'$USER'",
    "bet": 50,
    "platform": "twitch"
  }' | jq '.'

# Test 5: Get Leaderboard
echo -e "\nTest 5: Get leaderboard..."
curl -s "$API/currency/$COMMUNITY/leaderboard?limit=5&platform=twitch" | jq '.'

echo -e "\nAll tests completed!"
```

## Load Testing

### Locust Test

**locustfile.py**
```python
from locust import HttpUser, task, between
import random

class LoyaltyUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.user_id = f"user_{random.randint(1000, 9999)}"
        self.community_id = 1

    @task(3)
    def get_balance(self):
        """Check balance frequently"""
        self.client.get(
            f"/api/v1/loyalty/currency/{self.community_id}/balance/{self.user_id}",
            params={'platform': 'twitch'}
        )

    @task(2)
    def play_game(self):
        """Play games moderately"""
        self.client.post(
            f"/api/v1/loyalty/games/{self.community_id}/slots",
            json={
                'community_id': self.community_id,
                'user_id': self.user_id,
                'bet': random.randint(10, 100),
                'platform': 'twitch'
            }
        )

    @task(1)
    def get_leaderboard(self):
        """Check leaderboard occasionally"""
        self.client.get(
            f"/api/v1/loyalty/currency/{self.community_id}/leaderboard"
        )
```

**Run load test:**
```bash
# Run with 100 users, spawn rate 10 per second
locust -f locustfile.py -u 100 -r 10 -t 5m http://localhost:8032
```

## Running Tests

### Unit Tests Only

```bash
# Run all unit tests
pytest tests/unit -v

# Run specific test file
pytest tests/unit/test_currency_service.py -v

# Run specific test
pytest tests/unit/test_currency_service.py::test_add_currency_success -v

# Run with coverage
pytest tests/unit --cov=services --cov-report=html
```

### Integration Tests

```bash
# Run integration tests (requires database)
pytest tests/integration -v --tb=short

# Run with live database
DATABASE_URL=postgresql://... pytest tests/integration
```

### API Tests

```bash
# Run API tests (requires service running)
pytest tests/api -v

# With custom base URL
API_BASE_URL=http://custom:8032 pytest tests/api
```

### Full Test Suite

```bash
# Run all tests with coverage report
pytest tests/ --cov=. --cov-report=term-missing --cov-report=html

# Run with specific marker
pytest -m "not slow" tests/

# Run in parallel
pytest -n auto tests/
```

### Continuous Integration

**GitHub Actions Example:**
```yaml
name: Test

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
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt pytest pytest-asyncio pytest-cov
      - run: pytest tests/ --cov --cov-report=xml
      - uses: codecov/codecov-action@v2
```

---

**Last Updated:** 2026-02-16
