# Alias Interaction Module — Testing Guide

## Overview

This guide covers testing strategies for the Alias Interaction Module, including unit tests, integration tests, and manual testing procedures.

**Test Framework:** pytest with async support (pytest-asyncio)

---

## Table of Contents

1. [Test Structure](#test-structure)
2. [Unit Tests](#unit-tests)
3. [Integration Tests](#integration-tests)
4. [Mock Data](#mock-data)
5. [Running Tests](#running-tests)
6. [Test Coverage](#test-coverage)
7. [Continuous Integration](#continuous-integration)

---

## Test Structure

### Test Directory Layout

```
tests/
├── unit/
│   └── test_alias_service.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_database_operations.py
├── fixtures/
│   ├── conftest.py
│   └── mock_data.py
└── smoke/
    └── test_smoke.py
```

### Test File Naming Convention

- Test files: test_*.py
- Test functions: test_<component>_<scenario>
- Fixtures: fixtures/conftest.py

---

## Unit Tests

### Test AliasService

File: tests/unit/test_alias_service.py

```python
import pytest
from services.alias_service import AliasService
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
async def mock_dal():
    dal = MagicMock()
    dal.aliases = MagicMock()
    return dal


@pytest.fixture
async def alias_service(mock_dal):
    return AliasService(mock_dal)


@pytest.mark.asyncio
async def test_create_alias(alias_service):
    alias_service.dal.insert_async = AsyncMock(return_value='alias-123')
    
    result = await alias_service.create_alias(
        community_id='community-1',
        alias_name='test_alias',
        command='echo test',
        created_by='admin'
    )
    
    assert result['id'] == 'alias-123'
    assert result['alias_name'] == 'test_alias'


@pytest.mark.asyncio
async def test_list_aliases(alias_service):
    mock_row = MagicMock()
    mock_row.alias_name = 'test_alias'
    
    alias_service.dal.select_async = AsyncMock(return_value=[mock_row])
    
    result = await alias_service.list_aliases('community-1')
    
    assert len(result) == 1


@pytest.mark.asyncio
async def test_execute_alias_user_substitution(alias_service):
    mock_row = MagicMock()
    mock_row.id = 'alias-1'
    mock_row.command = 'notify {user}'
    mock_row.usage_count = 0
    
    alias_service.dal.select_async = AsyncMock(return_value=[mock_row])
    alias_service.dal.update_async = AsyncMock()
    
    result = await alias_service.execute_alias(
        alias_name='notify',
        user='john_doe',
        args=[]
    )
    
    assert result == 'notify john_doe'


@pytest.mark.asyncio
async def test_execute_alias_arg_substitution(alias_service):
    mock_row = MagicMock()
    mock_row.id = 'alias-1'
    mock_row.command = 'create --title {arg1} --priority {arg2}'
    mock_row.usage_count = 0
    
    alias_service.dal.select_async = AsyncMock(return_value=[mock_row])
    alias_service.dal.update_async = AsyncMock()
    
    result = await alias_service.execute_alias(
        alias_name='issue',
        user='admin',
        args=['Bug', 'High']
    )
    
    assert result == 'create --title Bug --priority High'


@pytest.mark.asyncio
async def test_execute_alias_all_args(alias_service):
    mock_row = MagicMock()
    mock_row.id = 'alias-1'
    mock_row.command = 'search {all_args}'
    mock_row.usage_count = 0
    
    alias_service.dal.select_async = AsyncMock(return_value=[mock_row])
    alias_service.dal.update_async = AsyncMock()
    
    result = await alias_service.execute_alias(
        alias_name='search',
        user='user',
        args=['term1', 'term2', 'term3']
    )
    
    assert result == 'search term1 term2 term3'


@pytest.mark.asyncio
async def test_execute_alias_not_found(alias_service):
    alias_service.dal.select_async = AsyncMock(return_value=[])
    
    result = await alias_service.execute_alias(
        alias_name='nonexistent',
        user='user',
        args=[]
    )
    
    assert result is None


@pytest.mark.asyncio
async def test_delete_alias(alias_service):
    alias_service.dal.update_async = AsyncMock(return_value=True)
    
    result = await alias_service.delete_alias('alias-123')
    
    assert result is True
```

---

## Integration Tests

### Test API Endpoints

File: tests/integration/test_api_endpoints.py

```python
import pytest
from quart import Quart
import json


@pytest.fixture
async def client():
    from app import app
    async with app.test_client() as client:
        yield client


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get('/health')
    assert response.status_code == 200
    data = json.loads(await response.get_data())
    assert data['status'] == 'healthy'


@pytest.mark.asyncio
async def test_status_endpoint(client):
    response = await client.get('/api/v1/status')
    assert response.status_code == 200
    data = json.loads(await response.get_data())
    assert data['data']['status'] == 'operational'


@pytest.mark.asyncio
async def test_create_alias_endpoint(client):
    payload = {
        'community_id': 'test-community',
        'alias_name': 'test_alias',
        'command': 'echo test',
        'created_by': 'admin'
    }
    response = await client.post('/api/v1/aliases', json=payload)
    assert response.status_code == 201
    data = json.loads(await response.get_data())
    assert data['data']['alias_name'] == 'test_alias'


@pytest.mark.asyncio
async def test_list_aliases_endpoint(client):
    response = await client.get('/api/v1/aliases?community_id=test-community')
    assert response.status_code == 200
    data = json.loads(await response.get_data())
    assert 'data' in data


@pytest.mark.asyncio
async def test_execute_alias_endpoint(client):
    payload = {
        'alias_name': 'test_alias',
        'user': 'test_user',
        'args': []
    }
    response = await client.post('/api/v1/aliases/execute', json=payload)
    assert response.status_code == 200
    data = json.loads(await response.get_data())
    assert 'command' in data['data']


@pytest.mark.asyncio
async def test_delete_alias_endpoint(client):
    response = await client.delete('/api/v1/aliases/test-alias-id')
    assert response.status_code == 200
    data = json.loads(await response.get_data())
    assert data['data']['message'] == 'Alias deleted'
```

---

## Mock Data

### Sample Test Data

File: tests/fixtures/mock_data.py

```python
MOCK_COMMUNITY_IDS = [
    'community-engineering',
    'community-ops',
    'community-support'
]

MOCK_ALIASES = [
    {
        'id': 'alias-001',
        'community_id': 'community-engineering',
        'alias_name': 'test_run',
        'command': 'pytest --cov',
        'created_by': 'alice',
        'usage_count': 5
    },
    {
        'id': 'alias-002',
        'community_id': 'community-ops',
        'alias_name': 'check_health',
        'command': 'health_check --user {user}',
        'created_by': 'bob',
        'usage_count': 42
    },
    {
        'id': 'alias-003',
        'community_id': 'community-support',
        'alias_name': 'report_issue',
        'command': 'create_ticket --title {arg1} --priority {arg2}',
        'created_by': 'charlie',
        'usage_count': 18
    }
]

async def seed_mock_aliases(dal):
    for alias in MOCK_ALIASES:
        await dal.insert_async(dal.aliases, **alias)
```

### Fixture Setup

File: tests/fixtures/conftest.py

```python
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(scope='session')
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_dal():
    dal = MagicMock()
    dal.aliases = MagicMock()
    dal.insert_async = AsyncMock()
    dal.select_async = AsyncMock()
    dal.update_async = AsyncMock()
    dal.delete_async = AsyncMock()
    return dal


@pytest.fixture
async def test_app():
    from app import app
    return app


@pytest.fixture
async def test_client(test_app):
    async with test_app.test_client() as client:
        yield client
```

---

## Running Tests

### Install Test Dependencies

```bash
cd action/interactive/alias_interaction_module
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov
```

### Run All Tests

```bash
pytest tests/
pytest -v tests/
pytest --cov=. --cov-report=html tests/
```

### Run Specific Test Files

```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/unit/test_alias_service.py
pytest tests/unit/test_alias_service.py::test_create_alias
```

### Run with Different Log Levels

```bash
pytest -v --log-cli-level=DEBUG tests/
pytest -q tests/
```

### Test with Timeout

```bash
pytest --timeout=10 tests/
```

---

## Test Coverage

### Generate Coverage Report

```bash
pytest --cov=. --cov-report=term-missing tests/
pytest --cov=. --cov-report=html tests/
open htmlcov/index.html
pytest --cov=. --cov-report=xml tests/
```

### Coverage Targets

- Unit Tests: Minimum 80% coverage for AliasService
- Integration Tests: Minimum 70% coverage for API endpoints
- Overall: Minimum 75% code coverage

---

## Manual Testing

### Smoke Test

```bash
python3 app.py &
SERVICE_PID=$!
sleep 2

curl http://localhost:8010/health

curl -X POST http://localhost:8010/api/v1/aliases \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "test-community",
    "alias_name": "manual_test",
    "command": "echo manual test",
    "created_by": "tester"
  }'

curl "http://localhost:8010/api/v1/aliases?community_id=test-community"

curl -X POST http://localhost:8010/api/v1/aliases/execute \
  -H "Content-Type: application/json" \
  -d '{
    "alias_name": "manual_test",
    "user": "tester",
    "args": []
  }'

kill $SERVICE_PID
```

---

## Continuous Integration

### GitHub Actions Example

File: .github/workflows/test-alias-module.yml

```yaml
name: Test Alias Interaction Module

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: waddlebot
          POSTGRES_PASSWORD: password
          POSTGRES_DB: waddlebot
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        cd action/interactive/alias_interaction_module
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://waddlebot:password@localhost:5432/waddlebot
      run: |
        cd action/interactive/alias_interaction_module
        pytest --cov=. --cov-report=xml tests/
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
```

---

## Debugging Failed Tests

### Enable Debug Logging

```bash
pytest -v --log-cli-level=DEBUG -s tests/test_file.py::test_function
```

### Test with Database

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/test_db"
pytest tests/integration/
```

### View Test Database State

```bash
psql $DATABASE_URL -c "SELECT * FROM aliases LIMIT 5;"
```

---

## Best Practices

1. Use Fixtures - Reuse test setup across multiple tests
2. Mock External Dependencies - Don't depend on Redis or Router Service
3. Test Both Success and Failure - Test error cases too
4. Use Descriptive Names - Test names should describe what they test
5. Async Tests - Mark async tests with @pytest.mark.asyncio
6. Isolation - Each test should be independent
7. Coverage - Aim for 80+ percent coverage on business logic

---

## Test Checklist Before Commit

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Code coverage above 75 percent
- [ ] No hardcoded test data in source
- [ ] Mock data is realistic
- [ ] Error cases are tested
- [ ] Async/await patterns are correct
