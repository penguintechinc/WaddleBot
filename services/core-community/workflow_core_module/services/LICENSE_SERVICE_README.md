# LicenseService - Premium License Validation

## Overview

The `LicenseService` is a comprehensive premium license validation system for the WaddleBot workflow module. It integrates with the **PenguinTech License Server** to enforce license tiers and manage feature access.

**Key Features:**
- Premium license validation with PenguinTech integration
- License tier enforcement (Free vs Premium)
- Workflow creation/execution protection
- Redis-based caching with 5-minute TTL
- Graceful degradation in development mode
- HTTP 402 Payment Required error handling
- Comprehensive AAA (Authentication, Authorization, Audit) logging

## Quick Start

### 1. Installation

The service requires `aiohttp` for async HTTP calls (already in requirements.txt):

```bash
pip install aiohttp==3.9.1 redis==5.0.1
```

### 2. Basic Usage

```python
from services import LicenseService
from flask_core import setup_aaa_logging

# Initialize during app startup
license_service = LicenseService(
    license_server_url="https://license.penguintech.io",
    redis_url="redis://localhost:6379/0",
    release_mode=True,  # Enforce in production
    logger_instance=logger
)

await license_service.connect()

# Check license status
status = await license_service.check_license_status(community_id=123)

# Validate workflow creation
await license_service.validate_workflow_creation(
    community_id=123,
    entity_id="workflow_uuid"
)

# Validate workflow execution
await license_service.validate_workflow_execution(
    workflow_id="workflow_uuid",
    community_id=123
)

# Get license info
info = await license_service.get_license_info(community_id=123)
```

## Architecture

### Class Hierarchy

```
LicenseService
├── License Status Checking
├── Workflow Validation
├── License Information Retrieval
└── Internal Utilities
    ├── Redis Caching
    ├── License Server Integration
    └── Logging (AAA)
```

### Enums

#### LicenseStatus
- `ACTIVE`: License is valid and not expired
- `EXPIRED`: License has passed expiration date
- `INVALID`: License key is invalid or malformed
- `UNLICENSED`: No license found for community

#### LicenseTier
- `FREE`: Free tier (1 workflow per community allowed)
- `PREMIUM`: Premium tier (unlimited workflows)

### Exception Classes

#### LicenseException
Base exception for license errors. Useful for catching all license-related errors.

```python
try:
    await license_service.check_license_status(123)
except LicenseException as e:
    logger.error(f"License error: {e}")
```

#### LicenseValidationException
Raised when license validation fails. Returns HTTP 402 Payment Required.

```python
try:
    await license_service.validate_workflow_creation(123, "wf_1")
except LicenseValidationException as e:
    # e.status_code = 402
    # e.message = "Error message"
    # e.community_id = 123
    return error_response(e.message, 402)
```

## Configuration

### Environment Variables

Set in `.env` or docker environment:

```bash
# License Server URL (PenguinTech)
LICENSE_SERVER_URL=https://license.penguintech.io

# Release Mode (controls enforcement)
RELEASE_MODE=true          # Production: enforce licenses
RELEASE_MODE=false         # Development: skip enforcement

# Redis (for caching)
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
```

### Loading in config.py

```python
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    LICENSE_SERVER_URL = os.getenv(
        'LICENSE_SERVER_URL',
        'https://license.penguintech.io'
    )
    RELEASE_MODE = os.getenv('RELEASE_MODE', 'false').lower() == 'true'
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
```

## API Reference

### check_license_status()

Check the license status for a community.

**Parameters:**
- `community_id` (int): Community ID
- `license_key` (str, optional): License key (PENG-XXXX-XXXX-XXXX-XXXX-ABCD)

**Returns:**
```python
{
    "status": "active",           # LicenseStatus value
    "tier": "premium",            # LicenseTier value
    "expires_at": "2025-12-31",   # ISO datetime or None
    "features": {
        "workflows": True
    },
    "cached": True,               # Whether result was cached
    "dev_mode": False             # True in development mode
}
```

**Raises:**
- `LicenseException`: If license check fails

**Example:**
```python
try:
    status = await license_service.check_license_status(123)
    if status["status"] != "active":
        logger.warning(f"License not active: {status}")
except LicenseException as e:
    logger.error(f"License check failed: {e}")
```

### validate_workflow_creation()

Validate if a community can create a new workflow.

**Parameters:**
- `community_id` (int): Community ID
- `entity_id` (str): Workflow ID being created
- `license_key` (str, optional): License key

**Returns:**
- `True` if validation passes

**Raises:**
- `LicenseValidationException`: If validation fails (HTTP 402)

**Example:**
```python
@api_bp.route('/workflows', methods=['POST'])
async def create_workflow():
    data = await request.get_json()

    try:
        await license_service.validate_workflow_creation(
            community_id=data['community_id'],
            entity_id=str(uuid.uuid4())
        )

        # Create workflow...
        return success_response({"workflow_id": "..."})

    except LicenseValidationException as e:
        return error_response(e.message, 402)
```

### validate_workflow_execution()

Validate if a workflow can be executed.

**Parameters:**
- `workflow_id` (str): Workflow ID
- `community_id` (int): Community ID
- `license_key` (str, optional): License key

**Returns:**
- `True` if validation passes

**Raises:**
- `LicenseValidationException`: If validation fails (HTTP 402)

**Example:**
```python
@api_bp.route('/workflows/<workflow_id>/execute', methods=['POST'])
async def execute_workflow(workflow_id: str):
    community_id = request.args.get('community_id', type=int)

    try:
        await license_service.validate_workflow_execution(
            workflow_id=workflow_id,
            community_id=community_id
        )

        # Execute workflow...
        return success_response({"status": "executing"})

    except LicenseValidationException as e:
        return error_response(e.message, 402)
```

### get_license_info()

Get complete license information for a community.

**Parameters:**
- `community_id` (int): Community ID
- `license_key` (str, optional): License key

**Returns:**
```python
{
    "tier": "premium",                # "free" or "premium"
    "status": "active",               # License status
    "expires_at": "2025-12-31",       # ISO datetime or None
    "features": {"workflows": True},  # Feature dict
    "workflow_limit": None,           # None = unlimited, 0 = free
    "cached": True                    # Whether result was cached
}
```

**Example:**
```python
info = await license_service.get_license_info(community_id=123)

if info['tier'] == 'free':
    logger.info(f"Free tier community: max 1 workflow (open source limit)")
elif info['tier'] == 'premium':
    logger.info(f"Premium tier: unlimited workflows")
```

### invalidate_cache()

Manually invalidate cached license for a community.

**Parameters:**
- `community_id` (int): Community ID

**Example:**
```python
# After admin updates license via external system
await license_service.invalidate_cache(community_id=123)

# Next check will fetch fresh data from server
status = await license_service.check_license_status(123)
```

## License Tiers

### Free Tier

- **Cost**: $0
- **Workflow Creation**: Allowed (1 workflow per community)
- **Workflow Execution**: Allowed
- **Limit**: Cannot create more workflows after reaching 1
- **Response**: HTTP 402 with message: "Free tier allows 1 workflow per community. Upgrade to Premium for unlimited workflows."

### Open Source Model

Workflows are available for open source projects on the Free tier, limited to 1 workflow per community. This allows community developers to create and test basic workflow automation without cost.

### Premium Tier

- **Cost**: Premium subscription
- **Workflow Creation**: Allowed (unlimited)
- **Workflow Execution**: Allowed
- **Features**: All workflow features enabled

## Caching Strategy

### Cache Configuration

- **Backend**: Redis (with in-memory fallback)
- **TTL**: 5 minutes (300 seconds)
- **Key Format**: `license:community:{community_id}`

### Cache Behavior

1. **First Request**: Hits PenguinTech License Server (~100-200ms)
2. **Cached Requests**: Served from Redis (<5ms)
3. **Cache Miss**: Automatically refreshes after 5 minutes
4. **Manual Invalidation**: Use `invalidate_cache()` for immediate updates

### In-Memory Fallback

If Redis is unavailable, the service automatically falls back to in-memory caching (no TTL). This is suitable for:
- Single-instance deployments
- Development environments
- Temporary Redis outages

## Development Mode vs Production

### Development Mode (RELEASE_MODE=false)

- **License Check**: Skipped
- **Default Behavior**: Assumes Premium tier
- **Workflow Creation**: Always allowed
- **Workflow Execution**: Always allowed
- **Use Case**: Local development and testing

```python
# In development
status = await license_service.check_license_status(123)
# Returns: {"status": "active", "tier": "premium", "dev_mode": True, ...}
```

### Production Mode (RELEASE_MODE=true)

- **License Check**: Enforced
- **Validates Against**: PenguinTech License Server
- **Workflow Creation**: Requires valid license
- **Workflow Execution**: Requires valid license
- **Use Case**: Production deployments

## Error Handling

### HTTP 402 Payment Required

Returned when license validation fails:

```json
{
    "error": true,
    "message": "Free tier allows 1 workflow per community. Upgrade to Premium for unlimited workflows.",
    "status_code": 402,
    "community_id": 123
}
```

### Example Error Handling

```python
from services import LicenseValidationException

try:
    await license_service.validate_workflow_creation(123, "wf_1")
except LicenseValidationException as e:
    return {
        "error": True,
        "message": e.message,
        "status_code": e.status_code,
        "community_id": e.community_id
    }, 402
```

## Logging

### Log Categories

- **AUDIT**: License checks and validations
- **AUTH**: License key validation
- **ERROR**: License check failures
- **SYSTEM**: Service startup/shutdown, cache operations

### Sample Logs

```
[2025-12-09 10:30:45.123] INFO workflow_core_module:1.0.0 AUDIT community=456 action=license_check result=SUCCESS License validated for community 456

[2025-12-09 10:31:12.456] INFO workflow_core_module:1.0.0 AUDIT community=789 action=workflow_creation_denied result=FAILURE Workflow creation denied: free tier limit reached

[2025-12-09 10:32:00.789] ERROR workflow_core_module:1.0.0 ERROR community=100 result=FAILURE License server connection failed: Connection refused

[2025-12-09 10:33:15.321] INFO workflow_core_module:1.0.0 SYSTEM action=license_cache_connect result=SUCCESS Connected to Redis for license caching
```

### Accessing Logs

```python
# In app startup
logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

# Log license events
logger.audit(
    "License validation completed",
    action="license_check",
    community=str(community_id),
    result="SUCCESS"
)
```

## Integration Examples

### Quart/Flask Controller

```python
from quart import Blueprint, request, jsonify
from flask_core import error_response, success_response
from services import LicenseValidationException

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/workflows', methods=['POST'])
async def create_workflow():
    """Create workflow with license validation"""
    license_service = current_app.config['license_service']

    try:
        data = await request.get_json()

        # Validate license
        await license_service.validate_workflow_creation(
            community_id=data['community_id'],
            entity_id=str(uuid.uuid4())
        )

        # Create workflow...
        return success_response({"workflow_id": "..."})

    except LicenseValidationException as e:
        return error_response(e.message, 402)
```

### Database Integration

```python
async def get_workflow_license_key(community_id: int, dal) -> Optional[str]:
    """Fetch license key from database"""
    query = "SELECT license_key FROM communities WHERE id = $1"
    rows = await dal.execute(query, [community_id])
    return rows[0]['license_key'] if rows else None

# Usage
license_key = await get_workflow_license_key(community_id, dal)
await license_service.validate_workflow_creation(
    community_id=community_id,
    entity_id=workflow_id,
    license_key=license_key
)
```

## Testing

### Unit Tests

See `test_license_service_examples.py` for comprehensive test examples:

```python
@pytest.mark.asyncio
async def test_workflow_creation_premium_allowed():
    """Test that premium tier can create workflows"""
    service = LicenseService(
        license_server_url="http://localhost:8080",
        release_mode=False
    )

    result = await service.validate_workflow_creation(123, "wf_1")
    assert result is True

@pytest.mark.asyncio
async def test_workflow_creation_free_denied():
    """Test that free tier cannot create workflows"""
    service = LicenseService(
        license_server_url="http://localhost:8080",
        release_mode=True
    )

    with pytest.raises(LicenseValidationException):
        await service.validate_workflow_creation(123, "wf_1")
```

### Running Tests

```bash
# Run all license service tests
pytest core/workflow_core_module/services/test_license_service_examples.py -v

# Run specific test
pytest core/workflow_core_module/services/test_license_service_examples.py::TestLicenseService::test_workflow_creation_premium_allowed -v
```

## Performance

### Response Times

- **Development Mode**: <1ms (no network call)
- **Cached Response**: <5ms (Redis lookup)
- **First Check**: 100-200ms (network request to license server)
- **Fallback Cache**: <1ms (in-memory lookup)

### Optimization Tips

1. **Use Redis**: Much faster than license server calls
2. **Cache Warmed**: Pre-load frequent licenses on startup
3. **Batch Operations**: Group multiple validations if possible
4. **Invalidate Selectively**: Only invalidate when necessary

## Troubleshooting

### "License check failed"

1. Verify `LICENSE_SERVER_URL` is correct
2. Check network connectivity to license server
3. Verify license key format: `PENG-XXXX-XXXX-XXXX-XXXX-ABCD`
4. Check logs for detailed error messages

### "License server request timed out"

1. Increase timeout value in code (currently 10 seconds)
2. Check network latency to license server
3. Verify license server is running and responsive
4. Consider using Redis cache to reduce server load

### "Connection refused to Redis"

1. Verify Redis is running
2. Check `REDIS_URL` setting
3. Service will automatically fall back to in-memory cache
4. Check logs for connection errors

### License Status Always Invalid

1. Verify license key is correct
2. Check if license has expired
3. Verify license is active in PenguinTech system
4. Try invalidating cache: `await license_service.invalidate_cache(123)`

## Security Considerations

1. **HTTPS Only**: Always use HTTPS for license server communication
2. **No Logging Keys**: Never log license keys in plain text
3. **Cache TTL**: 5-minute default balances performance and security
4. **Dev Mode**: Only enable in development (RELEASE_MODE=false)
5. **Network Security**: Use VPC or network policies to restrict license server access

## Files Included

1. **license_service.py** (643 lines, 21KB)
   - Core LicenseService implementation
   - License status checking and validation
   - Redis caching and fallback
   - PenguinTech License Server integration
   - AAA logging

2. **LICENSE_SERVICE_INTEGRATION.md** (370 lines)
   - Comprehensive integration guide
   - Configuration examples
   - API reference
   - Troubleshooting guide

3. **test_license_service_examples.py** (550+ lines)
   - Unit tests
   - Integration examples
   - Usage patterns
   - Test fixtures

4. **LICENSE_SERVICE_README.md** (This file)
   - Overview and quick start
   - Architecture documentation
   - Complete API reference
   - Performance and security guide

## Next Steps

1. **Integration**: Add to `app.py` startup/shutdown
2. **Controllers**: Add license validation to workflow endpoints
3. **Database**: Fetch license keys from communities table
4. **Tests**: Run test suite with pytest
5. **Deployment**: Set environment variables in production

## Support

For issues or questions:
1. Check logs in `/var/log/waddlebotlog/`
2. Review integration guide in `LICENSE_SERVICE_INTEGRATION.md`
3. Check test examples in `test_license_service_examples.py`
4. Verify configuration in `config.py`
