# GCP Functions Action Module - Testing

## Overview

Testing for the GCP Functions Action Module includes unit tests, integration tests, and end-to-end tests. All tests mock GCP client responses for isolated, reliable testing without actual Cloud Function invocations.

## Test Structure

Tests are located in test-api.sh and test_api.py (if present) and can be run with pytest:

```bash
cd /home/penguin/code/waddlebot/action/pushing/gcp_functions_action_module
python -m pytest test_api.py -v
```

## Unit Tests

### Test Setup

```python
import pytest
from app import app, db, gcp_service
from config import Config
from unittest.mock import Mock, AsyncMock, patch

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client

@pytest.fixture
def mock_gcp():
    with patch('services.gcp_functions_service.aiohttp.ClientSession') as mock_session:
        yield mock_session
```

### Health Check Test

```bash
pytest test_api.py::test_health_check -v
```

**Test:**
```python
def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.json
    assert data['status'] == 'healthy'
    assert data['module'] == 'gcp_functions_action_module'
    assert 'version' in data
    assert 'gcp_project' in data
    assert 'gcp_region' in data
```

### Authentication Tests

```bash
pytest test_api.py::test_token_generation -v
pytest test_api.py::test_invalid_token -v
```

**Test Token Generation:**
```python
def test_token_generation(client):
    response = client.post('/api/v1/auth/token', json={
        'api_key': 'test_key',
        'service': 'test_service'
    })
    assert response.status_code == 200
    data = response.json
    assert 'token' in data
    assert 'expires_in' in data
    assert data['expires_in'] == Config.JWT_EXPIRATION_SECONDS
```

**Test Invalid Token:**
```python
def test_invalid_token(client):
    response = client.post('/api/v1/functions/invoke',
        headers={'Authorization': 'Bearer invalid_token'},
        json={
            'project': 'test',
            'region': 'us-central1',
            'function_name': 'test',
            'payload': {}
        }
    )
    assert response.status_code == 401
    assert 'error' in response.json
```

## Mock GCP Client

Mock GCP API responses to avoid actual invocations:

```python
import aiohttp
from unittest.mock import Mock, AsyncMock, patch

@pytest.fixture
def mock_gcp_api():
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"result": "success"}')
        mock_response.json = AsyncMock(return_value={
            'result': 'success',
            'executionId': 'test-exec-123'
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        yield mock_post
```

## Integration Tests

### Invoke Cloud Function Test

```bash
pytest test_api.py::test_invoke_function -v
```

**Test:**
```python
@pytest.mark.asyncio
async def test_invoke_function(client, mock_gcp_api):
    # Generate token
    token_response = client.post('/api/v1/auth/token', json={
        'api_key': 'test',
        'service': 'test'
    })
    token = token_response.json['token']
    
    # Invoke function
    response = client.post('/api/v1/functions/invoke',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'project': 'test-project',
            'region': 'us-central1',
            'function_name': 'test-function',
            'payload': {'message': 'test'}
        }
    )
    assert response.status_code == 200
    data = response.json
    assert data['success'] == True
    assert 'execution_id' in data
    assert 'execution_time_ms' in data
```

### HTTP Function Invocation Test

```bash
pytest test_api.py::test_invoke_http_function -v
```

**Test:**
```python
@pytest.mark.asyncio
async def test_invoke_http_function(client, mock_gcp_api):
    token_response = client.post('/api/v1/auth/token', json={
        'api_key': 'test',
        'service': 'test'
    })
    token = token_response.json['token']
    
    response = client.post('/api/v1/functions/invoke-http',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'url': 'https://us-central1-test.cloudfunctions.net/fn',
            'payload': {'data': 'test'},
            'method': 'POST'
        }
    )
    assert response.status_code == 200
    data = response.json
    assert data['success'] == True
```

### Batch Invocation Test

```bash
pytest test_api.py::test_batch_invoke -v
```

**Test:**
```python
@pytest.mark.asyncio
async def test_batch_invoke(client, mock_gcp_api):
    token_response = client.post('/api/v1/auth/token', json={
        'api_key': 'test',
        'service': 'test'
    })
    token = token_response.json['token']
    
    response = client.post('/api/v1/functions/batch',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'invocations': [
                {
                    'function_name': 'func1',
                    'payload': {'id': 1}
                },
                {
                    'function_name': 'func2',
                    'payload': {'id': 2}
                }
            ]
        }
    )
    assert response.status_code == 200
    data = response.json
    assert 'responses' in data
    assert data['total_count'] == 2
    assert data['success_count'] >= 0
```

### List Functions Test

```bash
pytest test_api.py::test_list_functions -v
```

**Test:**
```python
@pytest.mark.asyncio
async def test_list_functions(client, token):
    response = client.get('/api/v1/functions/list?project=test&region=us-central1',
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 200
    data = response.json
    assert 'project' in data
    assert 'region' in data
    assert 'functions' in data
    assert 'count' in data
```

### Get Function Details Test

```bash
pytest test_api.py::test_get_function_details -v
```

**Test:**
```python
@pytest.mark.asyncio
async def test_get_function_details(client, token):
    response = client.get('/api/v1/functions/test-fn/details?project=test&region=us-central1',
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 200
    data = response.json
    assert data['success'] == True
    assert 'function' in data
```

## Error Handling Tests

### Test Missing Required Parameters

```python
def test_missing_function_name(client, token):
    response = client.post('/api/v1/functions/invoke',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'project': 'test',
            'region': 'us-central1',
            'payload': {}
        }
    )
    assert response.status_code == 400
    assert 'error' in response.json
```

### Test Batch Size Limit

```python
def test_batch_size_exceeded(client, token):
    # Create batch with > MAX_BATCH_SIZE functions
    invocations = [
        {'function_name': f'func{i}', 'payload': {}}
        for i in range(101)
    ]
    
    response = client.post('/api/v1/functions/batch',
        headers={'Authorization': f'Bearer {token}'},
        json={'invocations': invocations}
    )
    assert response.status_code == 400
    assert 'exceeds maximum' in response.json['error']
```

## Database Testing

### Test Execution Logging

```python
@pytest.mark.asyncio
async def test_execution_logging(client, token, mock_gcp_api):
    # Invoke function
    response = client.post('/api/v1/functions/invoke',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'project': 'test',
            'region': 'us-central1',
            'function_name': 'test-fn',
            'payload': {'test': 'data'}
        }
    )
    
    assert response.status_code == 200
    
    # Check database for logged execution
    exec_id = response.json['execution_id']
    execution = db(db.gcp_function_invocations.execution_id == exec_id).select().first()
    
    assert execution is not None
    assert execution.function_name == 'test-fn'
    assert execution.success == True
    assert execution.status_code == 200
```

### Test Statistics

```python
def test_get_stats(client, token):
    response = client.get('/api/v1/stats',
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 200
    data = response.json
    assert 'stats' in data
    assert 'total_invocations' in data['stats']
    assert 'successful_invocations' in data['stats']
    assert 'failed_invocations' in data['stats']
    assert 'average_execution_time_ms' in data['stats']
```

## Test Data

Test payload examples:

```python
TEST_DATA = {
    'valid_project': 'test-project',
    'valid_region': 'us-central1',
    'valid_function': 'test-function',
    'valid_payload': {'message': 'test', 'id': 123},
    'valid_url': 'https://us-central1-test.cloudfunctions.net/fn',
    'invalid_project': 'invalid',
    'invalid_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.invalid',
    'large_payload': {f'key{i}': f'value{i}' for i in range(1000)},
}
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_gcp
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt pytest pytest-cov pytest-asyncio
      - run: pytest test_api.py --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Running Tests

### All Tests
```bash
pytest test_api.py -v
```

### Specific Test
```bash
pytest test_api.py::test_invoke_function -v
```

### With Coverage
```bash
pytest test_api.py --cov=. --cov-report=html
```

### Mark Tests by Category
```bash
pytest test_api.py -m "unit" -v
pytest test_api.py -m "integration" -v
```

## Bash Test Script

Run tests with bash:

```bash
cd /home/penguin/code/waddlebot/action/pushing/gcp_functions_action_module

# Test health check
./test-api.sh health

# Test function invocation
./test-api.sh invoke

# Test batch operations
./test-api.sh batch

# All tests
./test-api.sh all
```

## Troubleshooting Tests

**Tests fail with database error:**
```bash
# Ensure PostgreSQL is running
docker-compose -f docker-compose.yml up -d postgres

# Run tests
pytest test_api.py -v
```

**AsyncIO test errors:**
```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Mark async tests
@pytest.mark.asyncio
async def test_async_function():
    ...
```

**Mock GCP errors:**
```bash
# Verify mock patch path matches import
from unittest.mock import patch

# Correct path format
@patch('services.gcp_functions_service.aiohttp.ClientSession')
def test_with_mock(mock_session):
    ...
```

**Credential errors in testing:**
```bash
# Set testing mode
export TESTING_MODE="true"

# Set minimal credentials for testing
export GCP_PROJECT_ID="test-project"
export GCP_SERVICE_ACCOUNT_KEY='{"type":"mock"}'
```

See test_api.py for complete test examples.
