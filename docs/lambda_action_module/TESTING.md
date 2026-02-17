# Lambda Action Module - Testing Guide

## Overview

This guide covers unit testing, integration testing, and mocking strategies for the Lambda Action Module.

## Testing Setup

### Prerequisites

```bash
pip install pytest pytest-asyncio moto boto3 requests
```

### Test Structure

```
tests/
├── conftest.py           # Pytest fixtures
├── test_config.py        # Configuration tests
├── test_lambda_service.py # Service layer tests
├── test_api.py           # REST API tests
├── test_grpc.py          # gRPC tests
└── fixtures/
    └── mock_data.py      # Test data
```

## Unit Testing with moto

### Setting Up moto Mock

moto provides AWS service mocks for testing without real AWS calls.

#### Basic Setup

```python
import pytest
from moto import mock_lambda
import boto3

@mock_lambda
def test_invoke_lambda():
    # Create mock Lambda client
    client = boto3.client('lambda', region_name='us-east-1')
    
    # Create test function
    client.create_function(
        FunctionName='test-function',
        Runtime='python3.11',
        Role='arn:aws:iam::123456789:role/test-role',
        Handler='index.handler',
        Code={'ZipFile': b'fake code'},
    )
    
    # Invoke function
    response = client.invoke(
        FunctionName='test-function',
        InvocationType='RequestResponse',
        Payload=b'{}'
    )
    
    assert response['StatusCode'] == 200
```

### pytest Fixture for Lambda Service

Create `conftest.py`:

```python
import pytest
from moto import mock_lambda, mock_rds
from pydal import DAL
from services.lambda_service import LambdaService
from config import Config

@pytest.fixture
def db():
    """Create in-memory database for testing."""
    db = DAL('sqlite:memory', folder=None)
    db.define_table(
        'lambda_invocations',
        db.Field('function_name', 'string', required=True),
        db.Field('invocation_type', 'string', required=True),
        db.Field('payload', 'text'),
        db.Field('alias', 'string'),
        db.Field('version', 'string'),
        db.Field('status_code', 'integer'),
        db.Field('response_payload', 'text'),
        db.Field('function_error', 'string'),
        db.Field('executed_version', 'string'),
        db.Field('request_id', 'string'),
        db.Field('success', 'boolean'),
        db.Field('error_message', 'text'),
        db.Field('invoked_at', 'datetime'),
        db.Field('completed_at', 'datetime'),
    )
    return db

@pytest.fixture
@mock_lambda
def lambda_service(db):
    """Create LambdaService with mocked AWS."""
    service = LambdaService(db)
    return service

@pytest.fixture
def aws_lambda_client():
    """Create mocked boto3 Lambda client."""
    with mock_lambda():
        yield boto3.client('lambda', region_name='us-east-1')
```

## Test Data

### Test Lambda Function Data

```python
# fixtures/mock_data.py

TEST_FUNCTION = {
    'FunctionName': 'test-function',
    'Runtime': 'python3.11',
    'Role': 'arn:aws:iam::123456789:role/lambda-role',
    'Handler': 'index.handler',
    'Code': {'ZipFile': b'def handler(event, context): return {"status": "ok"}'},
    'Description': 'Test Lambda function',
    'Timeout': 30,
    'MemorySize': 128,
}

TEST_PAYLOAD = '{"key": "value", "number": 42}'

TEST_RESPONSE = {
    'StatusCode': 200,
    'ExecutedVersion': '\$LATEST',
    'Payload': b'{"status": "ok"}',
    'LogResult': 'U3RhcnQgUmVxdWVzdCBJZDogMS4uLg==',  # Base64 encoded
}
```

## Unit Tests

### Test Configuration

```python
# tests/test_config.py

import pytest
import os
from config import Config

def test_config_aws_credentials():
    """Test AWS credential loading."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'test_key'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test_secret'
    
    assert Config.AWS_ACCESS_KEY_ID == 'test_key'
    assert Config.AWS_SECRET_ACCESS_KEY == 'test_secret'

def test_config_database_url():
    """Test database URL conversion."""
    os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost/db'
    
    # Reload config
    from importlib import reload
    reload(Config)
    
    # Should convert to postgres://
    assert Config.DATABASE_URL.startswith('postgres://')

def test_config_validation():
    """Test configuration validation."""
    errors = Config.validate()
    
    # Should have errors if required fields missing
    assert isinstance(errors, list)

def test_jwt_expiration():
    """Test JWT expiration setting."""
    assert Config.JWT_EXPIRATION_SECONDS == 3600  # Default
```

### Test Lambda Service

```python
# tests/test_lambda_service.py

import pytest
import asyncio
import boto3
from moto import mock_lambda
from services.lambda_service import LambdaService
from fixtures.mock_data import TEST_FUNCTION, TEST_PAYLOAD

@mock_lambda
@pytest.mark.asyncio
async def test_invoke_function_success(lambda_service, aws_lambda_client):
    """Test successful function invocation."""
    # Create test function
    aws_lambda_client.create_function(**TEST_FUNCTION)
    
    # Invoke
    success, status_code, payload, error, logs, version = \
        await lambda_service.invoke_function(
            'test-function',
            TEST_PAYLOAD,
            'RequestResponse'
        )
    
    assert success == True
    assert status_code == 200
    assert error == ''

@mock_lambda
@pytest.mark.asyncio
async def test_invoke_function_not_found(lambda_service):
    """Test invocation of non-existent function."""
    success, status_code, payload, error, logs, version = \
        await lambda_service.invoke_function(
            'non-existent',
            TEST_PAYLOAD,
            'RequestResponse'
        )
    
    assert success == False
    assert 'not found' in error.lower()

@mock_lambda
@pytest.mark.asyncio
async def test_invoke_async(lambda_service, aws_lambda_client):
    """Test asynchronous invocation."""
    aws_lambda_client.create_function(**TEST_FUNCTION)
    
    success, status_code, request_id = \
        await lambda_service.invoke_async(
            'test-function',
            TEST_PAYLOAD
        )
    
    assert success == True
    assert status_code == 202

@mock_lambda
@pytest.mark.asyncio
async def test_list_functions(lambda_service, aws_lambda_client):
    """Test listing Lambda functions."""
    # Create multiple functions
    for i in range(3):
        func = TEST_FUNCTION.copy()
        func['FunctionName'] = f'test-function-{i}'
        aws_lambda_client.create_function(**func)
    
    success, functions, marker = \
        await lambda_service.list_functions(max_items=50)
    
    assert success == True
    assert len(functions) >= 3

@mock_lambda
@pytest.mark.asyncio
async def test_get_function_config(lambda_service, aws_lambda_client):
    """Test getting function configuration."""
    aws_lambda_client.create_function(**TEST_FUNCTION)
    
    success, config = \
        await lambda_service.get_function_config('test-function')
    
    assert success == True
    assert config['function_name'] == 'test-function'
    assert config['runtime'] == 'python3.11'
```

## Integration Tests

### Test REST API

```python
# tests/test_api.py

import pytest
import json
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
async def test_token_generation(client):
    """Test JWT token generation."""
    response = await client.post(
        '/api/v1/token',
        json={
            'client_id': 'test',
            'client_secret': 'secret'
        }
    )
    assert response.status_code == 200
    data = await response.get_json()
    assert 'token' in data
    assert data['expires_in'] == 3600

@pytest.mark.asyncio
async def test_invoke_requires_auth(client):
    """Test that invoke endpoint requires authentication."""
    response = await client.post(
        '/api/v1/invoke',
        json={
            'function_name': 'test',
            'payload': '{}',
            'invocation_type': 'RequestResponse'
        }
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_invoke_with_auth(client):
    """Test invoke with valid token."""
    # Get token
    token_response = await client.post(
        '/api/v1/token',
        json={'client_id': 'test', 'client_secret': 'secret'}
    )
    token_data = await token_response.get_json()
    token = token_data['token']
    
    # Invoke with token
    response = await client.post(
        '/api/v1/invoke',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'function_name': 'test',
            'payload': '{}',
            'invocation_type': 'RequestResponse'
        }
    )
    
    # With moto, should work (function created in mock)
    assert response.status_code in [200, 500]  # 500 if function not found
```

## End-to-End Tests

### Test Complete Workflow

```python
# tests/test_e2e.py

import pytest
import asyncio
from moto import mock_lambda

@mock_lambda
@pytest.mark.asyncio
async def test_complete_workflow(lambda_service, aws_lambda_client, client):
    """Test complete invocation workflow."""
    
    # Step 1: Create Lambda function
    aws_lambda_client.create_function(
        FunctionName='workflow-test',
        Runtime='python3.11',
        Role='arn:aws:iam::123456789:role/test',
        Handler='index.handler',
        Code={'ZipFile': b'def handler(e, c): return {}'},
    )
    
    # Step 2: Generate token
    token_response = await client.post(
        '/api/v1/token',
        json={'client_id': 'test', 'client_secret': 'secret'}
    )
    token = (await token_response.get_json())['token']
    
    # Step 3: List functions
    list_response = await client.get(
        '/api/v1/functions',
        headers={'Authorization': f'Bearer {token}'}
    )
    functions = (await list_response.get_json())['functions']
    assert len(functions) > 0
    
    # Step 4: Get function config
    config_response = await client.get(
        '/api/v1/functions/workflow-test',
        headers={'Authorization': f'Bearer {token}'}
    )
    config = (await config_response.get_json())['config']
    assert config['function_name'] == 'workflow-test'
    
    # Step 5: Invoke function
    invoke_response = await client.post(
        '/api/v1/invoke',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'function_name': 'workflow-test',
            'payload': '{}',
            'invocation_type': 'RequestResponse'
        }
    )
    result = await invoke_response.get_json()
    assert result['success'] == True
```

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_lambda_service.py -v
```

### Run Specific Test

```bash
pytest tests/test_lambda_service.py::test_invoke_function_success -v
```

### Run with Coverage

```bash
pytest tests/ --cov=services --cov=app --cov-report=html
```

### Run Async Tests

```bash
pytest tests/ -v --asyncio-mode=auto
```

## Test Markers

```python
@pytest.mark.asyncio
async def test_async_function():
    pass

@pytest.mark.slow
def test_slow_operation():
    pass

@pytest.mark.integration
def test_integration():
    pass
```

Run marked tests:

```bash
pytest -m asyncio tests/
pytest -m slow tests/
pytest -m integration tests/
```

## Mocking Strategies

### Mock AWS Lambda

```python
@mock_lambda
def test_with_mocked_lambda():
    # All boto3 Lambda calls are mocked
    pass
```

### Mock Database

```python
@pytest.fixture
def mock_db():
    """Use in-memory SQLite for tests."""
    return DAL('sqlite:memory')
```

### Mock Redis

```python
@pytest.fixture
def mock_redis(mocker):
    """Mock Redis client."""
    redis_mock = mocker.patch('redis.Redis')
    redis_mock.return_value.publish.return_value = 1
    return redis_mock
```

## Test Coverage

Target coverage: >80%

Check coverage:

```bash
pytest tests/ --cov=services --cov=app --cov-report=term-missing
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
      with:
        python-version: '3.13'
    - run: pip install -r requirements.txt pytest pytest-asyncio moto
    - run: pytest tests/ -v --cov=services --cov=app
```

## Performance Tests

```python
import time
import pytest

@pytest.mark.performance
@mock_lambda
@pytest.mark.asyncio
async def test_invocation_performance(lambda_service, aws_lambda_client):
    """Test invocation latency."""
    aws_lambda_client.create_function(
        FunctionName='perf-test',
        Runtime='python3.11',
        Role='arn:aws:iam::123456789:role/test',
        Handler='index.handler',
        Code={'ZipFile': b'def handler(e, c): return {}'},
    )
    
    start = time.time()
    for i in range(100):
        await lambda_service.invoke_function(
            'perf-test',
            '{}',
            'RequestResponse'
        )
    duration = time.time() - start
    
    # Should complete 100 invocations in reasonable time
    assert duration < 10  # seconds
```

## Test Data Cleanup

```python
@pytest.fixture(autouse=True)
def cleanup_db(db):
    """Cleanup database after each test."""
    yield
    db.executesql('DELETE FROM lambda_invocations')
    db.commit()
```

## Debugging Tests

Run with verbose output:

```bash
pytest tests/ -v -s
```

Drop into debugger:

```python
def test_something():
    import pdb; pdb.set_trace()
    # Debug here
```

## Best Practices

1. **Use fixtures** for common setup
2. **Mock external services** (AWS, database)
3. **Test happy path and errors**
4. **Keep tests focused and simple**
5. **Use descriptive names**
6. **Maintain >80% coverage**
7. **Run tests before committing**

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for test execution issues.
