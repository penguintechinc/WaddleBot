# Shared Libraries Reference

Complete documentation for WaddleBot shared libraries providing common functionality across modules.

## Overview

The shared library suite provides standardized components for:
- Database access (AsyncDAL, PyDAL wrapper)
- Authentication and authorization (Flask-Security-Too, JWT)
- API utilities (response formatting, decorators)
- Logging (AAA - Authentication, Authorization, Audit)
- Data models (Python 3.13 dataclasses with slots)
- Module SDK (adapters, security, base components)

## Flask Core Library

Core Flask/Quart utilities shared across all modules.

**Location:** `libs/flask_core/`

### Database Module

AsyncDAL wrapper for non-blocking database operations:

```python
from libs.flask_core import init_database, AsyncDAL

# Initialize
dal = init_database(
    uri='postgresql://user:pass@host/db',
    pool_size=10,
    read_replica_uri='postgresql://user:pass@replica/db'
)

# Async operations
user_id = await dal.insert_async(users, username='john', email='john@example.com')
rows = await dal.select_async(users.id == user_id)
await dal.update_async(users.id == user_id, email='newemail@example.com')
await dal.delete_async(users.id == user_id)

# Transaction support
async with dal.transaction():
    await dal.insert_async(users, username='jane')
    await dal.insert_async(user_roles, user_id=1, role='admin')
```

**Features:**
- Connection pooling
- Read replica support
- Transaction management
- Bulk operations
- No blocking operations

### Authentication Module

Flask-Security-Too integration with JWT and OAuth:

```python
from libs.flask_core import setup_auth, create_jwt_token

# Setup authentication
oauth = setup_auth(app, dal, config={
    'TWITCH_CLIENT_ID': 'your_client_id',
    'TWITCH_CLIENT_SECRET': 'your_secret'
})

# Generate JWT token
token = create_jwt_token(
    user_id='123',
    username='john',
    email='john@example.com',
    roles=['user', 'moderator'],
    scopes=['read', 'write'],
    secret_key=app.config['SECRET_KEY'],
    expires_in=3600  # 1 hour
)
```

**Supported Providers:**
- Twitch
- Discord
- Slack
- Generic OIDC

### API Utilities

Response formatting and decorators:

```python
from libs.flask_core import (
    success_response, error_response,
    async_endpoint, auth_required,
    rate_limit, validate_json
)

# Standardized responses
return success_response({'data': 'value'}, status_code=201)
return error_response('Error message', status_code=400)

# Decorators
@app.route('/protected', methods=['GET'])
@auth_required
@async_endpoint
async def protected_route():
    user = request.current_user
    return success_response({'user': user})

# Rate limiting
@app.route('/api/data', methods=['POST'])
@rate_limit(calls=100, period=3600)
async def rate_limited():
    return success_response({'ok': True})

# Input validation
@validate_json({'required': ['username', 'email']})
async def create_user():
    data = await request.get_json()
    # data is already validated
```

### Logging Module

Comprehensive AAA logging:

```python
from libs.flask_core import setup_aaa_logging

# Setup logging
logger = setup_aaa_logging(
    module_name='my_module',
    version='1.0.0',
    log_level='INFO'
)

# Log events
logger.auth(action='login', user='john', result='SUCCESS')
logger.authz(action='view_community', user='john', community='my_community', result='ALLOWED')
logger.audit(action='update_settings', user='john', community='my_community', result='SUCCESS')
logger.error('Something went wrong', user='john', action='process_data')
logger.performance(action='process_batch', execution_time=150)
logger.system(action='startup', message='Service started', result='SUCCESS')
```

**Log Format:**
```
[timestamp] LEVEL module:version EVENT_TYPE community=X user=Y action=Z result=STATUS
[2025-12-09T12:00:00Z] INFO my_module:1.0.0 AUDIT community=123 user=john action=login result=SUCCESS
```

**Categories:**
- AUTH - Authentication events
- AUTHZ - Authorization decisions
- AUDIT - User actions
- ERROR - Errors and failures
- SYSTEM - Service lifecycle
- PERFORMANCE - Timing metrics

### Data Models

Python 3.13 optimized dataclasses:

```python
from dataclasses import dataclass, field
from libs.flask_core import MessageType, Platform, CommandRequest, CommandResult

@dataclass(slots=True)
class User:
    id: int
    username: str
    email: str
    roles: list = field(default_factory=list)

# Built-in models
request = CommandRequest(
    entity_id='twitch:channel:12345',
    user_id='user123',
    message='!help',
    message_type=MessageType.CHAT_MESSAGE,
    platform=Platform.TWITCH,
    username='john_doe'
)

result = CommandResult(
    execution_id='exec_123',
    command_id=1,
    success=True,
    processing_time_ms=45
)
```

**Features:**
- `slots=True` for memory efficiency
- Full type hints
- Frozen/immutable variants
- JSON serialization support

## Module SDK

SDK for building WaddleBot modules and integrations.

**Location:** `libs/module_sdk/`

### BaseModule

Base class for all modules:

```python
from libs.module_sdk import BaseModule, ExecuteRequest, ExecuteResponse

class MyModule(BaseModule):
    MODULE_NAME = "my_weather_module"
    MODULE_VERSION = "1.0.0"
    
    async def execute_async(self, request: ExecuteRequest) -> ExecuteResponse:
        # Process request
        try:
            result = await self.fetch_weather(request.args[0])
            return ExecuteResponse(
                success=True,
                message=f"Weather: {result}"
            )
        except Exception as e:
            return ExecuteResponse(
                success=False,
                error=str(e)
            )

# Use in app
module = MyModule()
response = await module.execute_async(request)
```

### Adapters

**WebhookAdapter** - Call external webhooks:

```python
from libs.module_sdk.adapters import WebhookAdapter

adapter = WebhookAdapter(
    webhook_url="https://your-module.com/webhook",
    secret_key="your-secret-key",
    module_name="my_weather_module",
    timeout=5.0,
    module_version="1.0.0",
    required_scopes=["community.read"]
)

response = await adapter.execute_async(request)
```

**Features:**
- HMAC-SHA256 signatures
- Automatic health tracking
- Configurable timeouts
- Custom metadata

### Security - Scoped Tokens

OAuth-like token system for module permissions:

```python
from libs.module_sdk.security import create_scoped_token_service

# Create service
service = create_scoped_token_service(
    secret_key="your-secret-key-minimum-32-chars"
)

# Generate token
token = service.generate_token(
    community_id="community_123",
    module_name="music_module",
    scopes=["read", "write"],
    expires_in=3600
)

# Validate token
payload = service.validate_token(token)
if payload and 'write' in payload['scopes']:
    # User has write scope
    pass

# Grant scope to module
await service.grant_scope_async(
    community_id="community_123",
    module_name="music_module",
    scope="playlist:manage",
    granted_by_user_id="user_456"
)
```

**Token Types:**
- ACCESS - Short-lived (default 1 hour)
- SERVICE - Long-lived (up to 8760 hours)
- REFRESH - Refresh tokens

**Scope Format:**
```
resource:action
community:read
music:write
playlist:manage
```

## Common Integration Patterns

### Example 1: Database Access

```python
from libs.flask_core import init_database

async def create_user_workflow(username: str, email: str):
    dal = init_database(DATABASE_URI)
    
    # Create tables
    users = dal.define_table('users',
        dal.Field('username', 'string'),
        dal.Field('email', 'string')
    )
    
    # Insert async
    user_id = await dal.insert_async(users, username=username, email=email)
    return user_id
```

### Example 2: API Endpoint with Auth

```python
from libs.flask_core import auth_required, success_response, error_response

@app.route('/api/users/:id', methods=['GET'])
@auth_required
async def get_user(user_id):
    current_user = request.current_user
    
    if current_user.id != user_id and 'admin' not in current_user.roles:
        return error_response('Forbidden', 403)
    
    # Fetch user
    user = await dal.select_async(users.id == user_id)
    return success_response(user)
```

### Example 3: Module with Adapter

```python
from libs.module_sdk import BaseModule
from libs.module_sdk.adapters import WebhookAdapter

class WeatherModule(BaseModule):
    def __init__(self):
        self.adapter = WebhookAdapter(
            webhook_url="https://weather-api.example.com/webhook",
            secret_key="secret",
            module_name="weather"
        )
    
    async def execute_async(self, request: ExecuteRequest) -> ExecuteResponse:
        return await self.adapter.execute_async(request)
```

### Example 4: Scoped Tokens in Workflow

```python
from libs.module_sdk.security import ScopedTokenService

service = ScopedTokenService(secret_key="secret", dal=dal)

# In workflow action node
token = service.generate_token(
    community_id=context.entity_id,
    module_name="music",
    scopes=["playlist:read"]
)

# Send to external service
response = await webhook_call(
    url="https://music-service/api/playlists",
    headers={"Authorization": f"Bearer {token}"}
)
```

## Installation

**Flask Core:**
```bash
cd /home/penguin/code/waddlebot/libs/flask_core
pip install -e .
```

**Module SDK:**
```bash
cd /home/penguin/code/waddlebot/libs/module_sdk
pip install -e .
```

## Dependencies

### Flask Core
- Flask/Quart (async web framework)
- Flask-Security-Too (authentication)
- PyDAL (database abstraction)
- aiohttp (async HTTP)
- python-dotenv (environment variables)

### Module SDK
- httpx >= 0.27.0 (async HTTP)
- PyJWT (token generation)
- cryptography (encryption)
- Flask Core (depends on)

## Python 3.13 Optimizations

- Dataclasses with `slots=True` for memory efficiency
- Structural pattern matching for conditionals
- Type aliases for better type hints
- TaskGroup for structured concurrency

## Configuration

### Flask Core Config

```python
# In config.py
class Config:
    DATABASE_URI = os.getenv('DATABASE_URI')
    REDIS_URL = os.getenv('REDIS_URL')
    SECRET_KEY = os.getenv('SECRET_KEY')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    JWT_SECRET = os.getenv('JWT_SECRET')
```

### Module SDK Config

```python
# In module
TOKEN_SECRET_KEY = os.getenv('TOKEN_SECRET_KEY')
WEBHOOK_TIMEOUT = int(os.getenv('WEBHOOK_TIMEOUT', '5'))
MAX_SIGNATURE_AGE = int(os.getenv('MAX_SIGNATURE_AGE', '300'))
```

## Security Best Practices

1. **Secrets:** Load from environment variables, never hardcode
2. **Tokens:** Use JWT with short expiration (1 hour default)
3. **Scopes:** Granular permissions (not blanket access)
4. **HTTPS:** Always use TLS in production
5. **Logging:** Never log secrets, tokens, or sensitive data
6. **Validation:** Always validate inputs before processing
7. **Rate Limiting:** Implement per endpoint
8. **CORS:** Configure properly for cross-origin requests

## Performance Considerations

### AsyncDAL

- Connection pooling reduces latency
- Read replicas distribute query load
- Bulk operations more efficient than loops

### Logging

- Async log writing (non-blocking)
- Buffered I/O for batch operations
- Log rotation prevents disk bloat

### Tokens

- In-memory caching for validation (~1-2ms)
- Redis-backed caching for distributed systems
- Automatic expired token cleanup

## Error Handling

### Flask Core Patterns

```python
from libs.flask_core import error_response, LicenseValidationException

try:
    # Check license
    await license_service.validate_feature(community_id)
except LicenseValidationException as e:
    return error_response(e.message, 402)  # Payment Required

try:
    # Process data
    result = await process_async(data)
    return success_response(result)
except ValueError as e:
    return error_response(str(e), 400)
except Exception as e:
    logger.error(f"Unexpected error: {e}", action="process")
    return error_response("Internal server error", 500)
```

### Module SDK Patterns

```python
from libs.module_sdk import ExecuteResponse

async def safe_execute(request):
    try:
        result = await do_work(request)
        return ExecuteResponse(success=True, message=result)
    except TimeoutError:
        return ExecuteResponse(success=False, error="Request timeout")
    except ValidationError as e:
        return ExecuteResponse(success=False, error=f"Validation: {e}")
    except Exception as e:
        logger.error(f"Unexpected: {e}")
        return ExecuteResponse(success=False, error="Internal error")
```

## Testing

### Unit Tests

```bash
# Flask Core
pytest libs/flask_core/tests/ -v

# Module SDK
pytest libs/module_sdk/tests/ -v
```

### Integration Tests

```bash
# Full integration with database
pytest tests/integration/ -v
```

## Related Documentation

- **workflow-engine.md** - Workflow system using these libraries
- **shared-libs.md** - This document
- Individual library READMEs in their directories
