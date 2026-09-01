# OpenWhisk Action Module - Testing Guide

## Testing Setup

### Prerequisites

```bash
pip install pytest pytest-asyncio pytest-mock requests
```

### Test Structure

```
tests/
├── conftest.py              # Fixtures
├── test_config.py           # Configuration tests
├── test_openwhisk_service.py # Service tests
├── test_api.py              # API tests
└── fixtures/
    └── mock_data.py         # Test data
```

## Unit Tests

### Test OpenWhisk Service

```python
# tests/test_openwhisk_service.py

import pytest
from unittest.mock import Mock, AsyncMock, patch
from services.openwhisk_service import OpenWhiskService

@pytest.mark.asyncio
async def test_invoke_action_success(mocker):
    """Test successful action invocation."""
    service = OpenWhiskService()
    
    # Mock OpenWhisk API response
    mocker.patch.object(service, '_post', new_callable=AsyncMock, return_value={
        'activation_id': 'abc123',
        'response': {'result': 'success'},
        'duration': 125
    })
    
    result = await service.invoke_action(
        'guest',
        'my-action',
        {'data': 'test'},
        blocking=True
    )
    
    assert result['success'] == True
    assert result['activation_id'] == 'abc123'

@pytest.mark.asyncio
async def test_invoke_action_not_found(mocker):
    """Test action not found error."""
    service = OpenWhiskService()
    
    # Mock 404 response
    mocker.patch.object(service, '_post', new_callable=AsyncMock, 
        side_effect=Exception('Action not found'))
    
    result = await service.invoke_action(
        'guest',
        'missing',
        {},
        blocking=True
    )
    
    assert result['success'] == False
    assert 'not found' in result['error'].lower()

@pytest.mark.asyncio
async def test_invoke_sequence(mocker):
    """Test sequence invocation."""
    service = OpenWhiskService()
    
    mocker.patch.object(service, '_post', new_callable=AsyncMock, return_value={
        'activation_id': 'seq123',
        'response': {'result': 'final output'}
    })
    
    result = await service.invoke_sequence(
        'guest',
        'action1->action2->action3',
        {'input': 'data'}
    )
    
    assert result['success'] == True

@pytest.mark.asyncio
async def test_fire_trigger(mocker):
    """Test trigger firing."""
    service = OpenWhiskService()
    
    mocker.patch.object(service, '_put', new_callable=AsyncMock, return_value={
        'activation_id': 'trig123'
    })
    
    result = await service.fire_trigger(
        'guest',
        'my-trigger',
        {'event': 'data'}
    )
    
    assert result['success'] == True
```

## Integration Tests

### Test REST API

```python
# tests/test_api.py

import pytest
from app import app

@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.mark.asyncio
async def test_health_check(client):
    """Test health endpoint."""
    response = await client.get('/health')
    assert response.status_code == 200
    data = await response.get_json()
    assert data['status'] == 'healthy'

@pytest.mark.asyncio
async def test_auth_token_generation(client):
    """Test token generation."""
    response = await client.post(
        '/api/v1/auth/token',
        json={'api_key': 'test-key'}
    )
    assert response.status_code == 200
    data = await response.get_json()
    assert 'token' in data

@pytest.mark.asyncio
async def test_action_invocation_requires_auth(client):
    """Test authentication required."""
    response = await client.post(
        '/api/v1/actions/invoke',
        json={'action_name': 'test'}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_action_invocation_with_auth(client, mocker):
    """Test action invocation with token."""
    # Get token
    token_response = await client.post(
        '/api/v1/auth/token',
        json={'api_key': 'test'}
    )
    token = (await token_response.get_json())['token']
    
    # Mock service
    mocker.patch('services.openwhisk_service.OpenWhiskService.invoke_action',
        new_callable=AsyncMock,
        return_value={
            'success': True,
            'activation_id': 'test123',
            'result': {}
        }
    )
    
    # Invoke with token
    response = await client.post(
        '/api/v1/actions/invoke',
        headers={'Authorization': f'Bearer {token}'},
        json={'action_name': 'test', 'payload': {}}
    )
    
    assert response.status_code == 200
```

## Mocking OpenWhisk

### Mock REST API Responses

```python
@pytest.fixture
def mock_openwhisk_api(mocker):
    """Mock OpenWhisk REST API."""
    mock_post = mocker.patch('aiohttp.ClientSession.post')
    mock_post.return_value.__aenter__.return_value.json = AsyncMock(
        return_value={
            'activation_id': 'test123',
            'response': {'result': 'data'}
        }
    )
    return mock_post
```

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run with Coverage

```bash
pytest tests/ --cov=services --cov=app --cov-report=html
```

### Run Async Tests

```bash
pytest tests/ -v --asyncio-mode=auto
```

### Run Specific Test

```bash
pytest tests/test_openwhisk_service.py::test_invoke_action_success -v
```

## Test Data

### Sample Payloads

```python
# fixtures/mock_data.py

TEST_ACTION_PAYLOAD = {"name": "test", "value": 123}

TEST_ACTION_RESPONSE = {
    "activation_id": "abc123def456",
    "response": {
        "status_code": 0,
        "result": {
            "message": "success"
        }
    },
    "duration": 125
}
```

## Best Practices

1. **Mock external services** (OpenWhisk API)
2. **Test happy path and errors**
3. **Keep tests focused**
4. **Use descriptive names**
5. **Maintain >80% coverage**
6. **Run before committing**

## CI/CD Integration

```yaml
name: Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
    - run: pip install -r requirements.txt pytest pytest-asyncio
    - run: pytest tests/ -v --cov=services --cov=app
```

See [API.md](API.md) and [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more details.
