# Quote Interaction Module - Testing Guide

## Test Strategy

The Quote Interaction Module uses a multi-level testing approach:

1. Smoke Tests - Quick validation of core functionality
2. Unit Tests - Individual function/method testing
3. Integration Tests - Component interaction testing
4. API Tests - Endpoint testing with real requests
5. Performance Tests - Load and response time validation

## Test Execution

### Running All Tests

```bash
cd /home/penguin/code/waddlebot
make test-quote-module
```

### Running Specific Test Categories

```bash
# Smoke tests only
make smoke-test-quote

# Unit tests
make test-unit-quote

# Integration tests
make test-integration-quote

# API tests
make test-api-quote

# Performance tests
make test-perf-quote
```

## Smoke Tests

Quick validation that the module starts and responds to basic requests.

**Run Time:** < 2 minutes

**Test Script:** `action/interactive/quote_interaction_module/test-api.sh`

```bash
chmod +x action/interactive/quote_interaction_module/test-api.sh
./action/interactive/quote_interaction_module/test-api.sh
```

**Tests Performed:**
1. Health endpoint is reachable
2. Status endpoint returns module info
3. Quote creation succeeds
4. Quote retrieval works
5. Search functionality works
6. Statistics calculation works

### Smoke Test Checklist

- [ ] Module starts without errors
- [ ] GET /health returns 200
- [ ] GET /api/v1/status returns module info
- [ ] POST /api/v1/quotes creates a quote
- [ ] GET /api/v1/quotes/<id> retrieves the quote
- [ ] GET /api/v1/quotes/search/<community_id>?q=test returns results
- [ ] GET /api/v1/quotes/stats/<community_id> returns stats

## Mock Data

### Mock Data Fixtures

Create test quotes for consistent testing:

```python
# tests/fixtures/quotes.py

MOCK_QUOTES = [
    {
        "community_id": 1,
        "text": "The only way to do great work is to love what you do",
        "author": "Steve Jobs",
        "added_by_user_id": 100,
        "quoted_user_id": 200,
        "platform": "twitch",
        "context": "Keynote speech",
        "tags": ["leadership", "motivation"],
        "is_approved": True
    },
    {
        "community_id": 1,
        "text": "Innovation distinguishes a leader from a follower",
        "author": "Steve Jobs",
        "added_by_user_id": 100,
        "quoted_user_id": 200,
        "platform": "twitch",
        "context": "Another keynote",
        "tags": ["innovation", "leadership"],
        "is_approved": True
    },
    {
        "community_id": 1,
        "text": "Be yourself; everyone else is already taken",
        "author": "Oscar Wilde",
        "added_by_user_id": 101,
        "quoted_user_id": 201,
        "platform": "discord",
        "context": "Community discussion",
        "tags": ["wisdom", "authenticity"],
        "is_approved": True
    },
    {
        "community_id": 1,
        "text": "Pending quote awaiting approval",
        "author": "Test Author",
        "added_by_user_id": 102,
        "quoted_user_id": 202,
        "platform": "discord",
        "context": "Test context",
        "tags": ["test"],
        "is_approved": False
    }
]

MOCK_COMMUNITY_ID = 1
MOCK_USER_ID = 100
```

### Seeding Mock Data

```bash
# Seed development database with mock quotes
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/penguin/code/waddlebot')
from action.interactive.quote_interaction_module.services.quote_service import QuoteService
from config import Config
from flask_core import init_database

# Initialize database
dal = init_database(Config.DATABASE_URL, Config.DB_POOL_SIZE)
service = QuoteService(dal)

# Mock data
quotes = [
    {
        "community_id": 1,
        "text": "The only way to do great work is to love what you do",
        "author": "Steve Jobs",
        "added_by_user_id": 100,
        "tags": ["leadership", "motivation"]
    },
    {
        "community_id": 1,
        "text": "Innovation distinguishes a leader from a follower",
        "author": "Steve Jobs",
        "added_by_user_id": 100,
        "tags": ["innovation"]
    },
    {
        "community_id": 1,
        "text": "Be yourself; everyone else is already taken",
        "author": "Oscar Wilde",
        "added_by_user_id": 101,
        "tags": ["wisdom"]
    }
]

# Insert quotes
async def seed():
    for quote in quotes:
        await service.add_quote(**quote)
    print(f"Seeded {len(quotes)} mock quotes")

import asyncio
asyncio.run(seed())
EOF
```

## Unit Tests

Test individual service methods in isolation.

**Location:** `tests/unit/test_quote_service.py`

### Example Unit Tests

Sample unit test structure testing the QuoteService class directly:

```python
import pytest
import asyncio
from datetime import datetime

# Test for successful quote creation
# Test checks that add_quote returns expected quote object with id

@pytest.mark.asyncio
async def test_add_quote_success():
    # Setup mock database
    # Call add_quote with test data
    # Assert result contains id, community_id, quote_text
    # Verify database was called

# Test for quote creation without required field
# Test verifies ValueError is raised when text field is None

@pytest.mark.asyncio
async def test_add_quote_missing_required_field():
    # Attempt to create quote without text
    # Assert ValueError is raised

# Test for retrieving existing quote
# Test calls get_quote and verifies result

@pytest.mark.asyncio
async def test_get_quote_found():
    # Mock database returns quote row
    # Call get_quote(1)
    # Assert result is not None and contains quote data

# Test for retrieving non-existent quote
# Test verifies None is returned for missing quote

@pytest.mark.asyncio
async def test_get_quote_not_found():
    # Mock database returns empty result
    # Call get_quote(999)
    # Assert result is None

# Test for full-text search
# Test calls search_quotes with keyword and verifies ranking

@pytest.mark.asyncio
async def test_search_quotes():
    # Mock count result and search results
    # Call search_quotes with query="work"
    # Assert results are ranked by relevance
    # Assert total count is returned
```

### Run Unit Tests

```bash
pytest tests/unit/test_quote_service.py -v
```

## Integration Tests

Test component interactions with real database.

**Location:** `tests/integration/test_quote_api.py`

### Example Integration Tests

Sample integration test structure testing API endpoints:

```python
# Test creating and retrieving a quote
# Test flow: POST quote, then GET the created quote
# Verify status codes and data integrity

@pytest.mark.asyncio
async def test_create_and_retrieve_quote():
    # POST to create quote
    # Assert response status is 201
    # Extract quote ID from response
    # GET the created quote
    # Assert response status is 200
    # Assert quote text matches

# Test searching quotes
# Test creates multiple quotes then searches for keywords

@pytest.mark.asyncio
async def test_search_quotes_integration():
    # Create 3 quotes with "work" keyword
    # GET search endpoint with q=work
    # Assert all created quotes in results
    # Assert search ranking works

# Test pagination
# Test verifies limit and offset work correctly

@pytest.mark.asyncio
async def test_pagination():
    # GET with limit=2, offset=0
    # Assert response has 2 items max
    # Assert pagination metadata includes has_more flag
    # GET with offset=2 for next page
    # Assert different results than first page
```

### Run Integration Tests

```bash
pytest tests/integration/test_quote_api.py -v
```

## API Tests

Test endpoints with curl or HTTP client.

### Test with curl

```bash
# Create quote
QUOTE_ID=$(curl -s -X POST http://localhost:5012/api/v1/quotes \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "text": "Test quote",
    "author": "Test Author",
    "added_by_user_id": 100
  }' | jq -r '.id')

echo "Created quote: $QUOTE_ID"

# Retrieve quote
curl -X GET "http://localhost:5012/api/v1/quotes/$QUOTE_ID"

# Search quotes
curl -X GET "http://localhost:5012/api/v1/quotes/search/1?q=test"

# Get stats
curl -X GET "http://localhost:5012/api/v1/quotes/stats/1"

# Update quote
curl -X PUT "http://localhost:5012/api/v1/quotes/$QUOTE_ID" \
  -H "Content-Type: application/json" \
  -d '{"text": "Updated quote"}'

# Delete quote
curl -X DELETE "http://localhost:5012/api/v1/quotes/$QUOTE_ID"
```

### Test with test-api.sh Script

```bash
chmod +x action/interactive/quote_interaction_module/test-api.sh
./action/interactive/quote_interaction_module/test-api.sh

# Output:
# Testing Quote Interaction Module API...
# Health check passed
# Status endpoint passed
# Quote creation passed
# Quote retrieval passed
# Search functionality passed
# Statistics passed
# All tests passed!
```

## Performance Tests

Test response times and throughput under load.

### Load Testing with Apache Bench

```bash
# Create test quote first
QUOTE_ID=$(curl -s -X POST http://localhost:5012/api/v1/quotes \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "text": "Test quote",
    "author": "Test Author"
  }' | jq -r '.id')

# Test 1000 requests with 10 concurrent connections
ab -n 1000 -c 10 http://localhost:5012/api/v1/quotes/$QUOTE_ID

# Results show:
# - Requests per second
# - Time per request
# - Failed requests
```

### Load Testing with wrk

```bash
# Install wrk
brew install wrk  # macOS
sudo apt-get install wrk  # Ubuntu

# Test GET endpoint
wrk -t12 -c400 -d30s \
  http://localhost:5012/api/v1/quotes/random/1

# Test POST endpoint with script
cat > post.lua << 'EOF'
request = function()
  wrk.method = "POST"
  wrk.headers["Content-Type"] = "application/json"
  wrk.body = '{"community_id":1,"text":"Load test","author":"Test"}'
  return wrk.format(nil)
end
EOF

wrk -t12 -c400 -d30s \
  -s post.lua \
  http://localhost:5012/api/v1/quotes
```

## Pre-Commit Testing Checklist

Before committing changes, run:

```bash
# 1. Lint code
flake8 action/interactive/quote_interaction_module/ --max-line-length=100

# 2. Run unit tests
pytest tests/unit/test_quote_service.py -v

# 3. Run integration tests
pytest tests/integration/test_quote_api.py -v

# 4. Run smoke tests
./action/interactive/quote_interaction_module/test-api.sh

# 5. Check code coverage
pytest --cov=action.interactive.quote_interaction_module tests/
```

## Continuous Integration

The module uses GitHub Actions for automated testing. See `.github/workflows/quote-module-tests.yml`

**Triggers:**
- Push to main, develop, and feature branches
- Pull requests
- Manual trigger

**Tests Run:**
- Linting (flake8, pylint)
- Unit tests
- Integration tests
- Smoke tests
- Performance benchmarks

## Test Coverage Goals

- **Overall:** >= 80%
- **Services:** >= 90%
- **Endpoints:** >= 85%
- **Critical paths:** 100%

## Debugging Failed Tests

### View Detailed Logs

```bash
# Run test with verbose output
pytest tests/unit/test_quote_service.py -vv -s

# Show print statements
pytest tests/ -v -s

# Show captured logs
pytest tests/ -v --log-cli-level=DEBUG
```

### Database Debugging

```bash
# Connect to test database
psql postgresql://user:pass@localhost:5432/waddlebot_test

# Check test data
SELECT COUNT(*) FROM quotes;
SELECT * FROM quotes LIMIT 5;

# Clear test data
DELETE FROM quotes WHERE community_id = 999;
```

### Module Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python -m action.interactive.quote_interaction_module.app

# View logs
docker-compose logs -f quote_interaction_module
```
