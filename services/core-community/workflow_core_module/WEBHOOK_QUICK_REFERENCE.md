# Webhook API - Quick Reference

## Overview

**File**: `controllers/webhook_api.py` (1,181 lines)

A Quart blueprint providing secure webhook endpoints for triggering workflows via HTTP.

## Quick Start

### 1. Create a Webhook

```bash
curl -X POST http://localhost:8000/api/v1/workflows/{workflow_id}/webhooks \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Webhook",
    "require_signature": true,
    "ip_allowlist": ["192.168.1.0/24"]
  }'
```

**Response**:
```json
{
  "success": true,
  "data": {
    "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    "webhook_id": "550e8400-...",
    "url": "https://api.example.com/api/v1/workflows/webhooks/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
  }
}
```

**Note**: The secret is NOT returned. You'll need to store it securely.

### 2. Trigger the Webhook

```python
import hmac
import hashlib
import json

token = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
secret = "b1c2d3e4f5g6h7i8j9k0l1m2n3o4p5q6"
payload = {"event": "user.created", "user_id": 12345}

body = json.dumps(payload).encode()
message = token.encode() + body
signature = "sha256=" + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

import requests
response = requests.post(
    "https://api.example.com/api/v1/workflows/webhooks/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    json=payload,
    headers={"X-Webhook-Signature": signature}
)

print(response.json())
# {"success": true, "data": {"execution_id": "..."}}
```

### 3. List Webhooks

```bash
curl http://localhost:8000/api/v1/workflows/{workflow_id}/webhooks \
  -H "X-API-Key: your-api-key"
```

### 4. Delete Webhook

```bash
curl -X DELETE http://localhost:8000/api/v1/workflows/{workflow_id}/webhooks/{webhook_id} \
  -H "X-API-Key: your-api-key"
```

## Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/workflows/webhooks/:token` | No | Trigger workflow |
| GET | `/api/v1/workflows/:id/webhooks` | Yes | List webhooks |
| POST | `/api/v1/workflows/:id/webhooks` | Yes | Create webhook |
| DELETE | `/api/v1/workflows/:id/webhooks/:id` | Yes | Delete webhook |

## Key Features

✓ HMAC-SHA256 signature verification
✓ IP allowlist (CIDR ranges)
✓ Rate limiting (60 req/min default)
✓ Secure token generation
✓ Comprehensive audit logging
✓ Permission-based access control

## Configuration

```python
{
  "name": "Webhook Name",                    # Required
  "description": "Optional description",     # Optional
  "require_signature": true,                 # Optional (default: true)
  "ip_allowlist": ["192.168.1.0/24"],       # Optional (default: [])
  "rate_limit_max": 60,                      # Optional (default: 60)
  "rate_limit_window": 60,                   # Optional (default: 60)
  "enabled": true,                           # Optional (default: true)
  "community_id": 123                        # Optional
}
```

## HMAC Signature

**Algorithm**:
```python
message = token.encode() + body
signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
header = f"sha256={signature}"
```

**Header**: `X-Webhook-Signature: sha256=abc123def456...`

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `WEBHOOK_NOT_FOUND` | 404 | Token doesn't exist |
| `WEBHOOK_DISABLED` | 403 | Webhook is disabled |
| `IP_NOT_ALLOWED` | 403 | IP not in allowlist |
| `SIGNATURE_INVALID` | 403 | Signature verification failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `PERMISSION_DENIED` | 403 | User lacks permissions |

## Security Checklist

- [x] HMAC signature verification
- [x] IP allowlist support
- [x] Rate limiting per webhook
- [x] Secure token generation
- [ ] Enable HTTPS (production)
- [ ] Configure firewall rules
- [ ] Monitor webhook activity
- [ ] Regular security audits

## WebhookConfig Structure

```python
@dataclass
class WebhookConfig:
    webhook_id: str              # UUID
    workflow_id: str             # UUID
    token: str                   # 32-char hex (public)
    secret: str                  # 32-char hex (private)
    name: str
    description: Optional[str]
    url: str                     # Full public URL
    enabled: bool
    require_signature: bool
    ip_allowlist: List[str]
    rate_limit_max: int          # Default 60
    rate_limit_window: int       # Default 60
    created_at: datetime
    updated_at: datetime
    last_triggered_at: datetime
    trigger_count: int
```

## WebhookRateLimiter

- In-memory sliding window
- No external dependencies
- Automatic cleanup
- Returns (allowed: bool, remaining: int)

## Helper Functions

```python
generate_webhook_token() → str         # Generate public token
generate_webhook_secret() → str        # Generate private secret
verify_webhook_signature(...) → bool   # Verify HMAC-SHA256
check_ip_allowlist(...) → bool         # Check IP/CIDR
get_webhook_by_token(...) → Optional   # Lookup by token
update_webhook_trigger_stats(...)      # Update stats
```

## Service Dependencies

- `WorkflowService`: Get workflow, permission checks
- `PermissionService`: Check can_view/can_edit
- `WorkflowEngine`: Execute workflows
- `AsyncDAL`: Database access

## HTTP Headers

**Request Headers**:
- `Content-Type: application/json` (optional)
- `X-Webhook-Signature: sha256=...` (if require_signature=true)
- `X-API-Key: ...` (authentication required for management endpoints)

**Response Headers**:
- `Content-Type: application/json`

## Database Table

```sql
CREATE TABLE workflow_webhooks (
  webhook_id UUID PRIMARY KEY,
  workflow_id UUID NOT NULL,
  token VARCHAR(255) UNIQUE NOT NULL,
  secret VARCHAR(255) NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  url TEXT,
  enabled BOOLEAN DEFAULT true,
  require_signature BOOLEAN DEFAULT true,
  ip_allowlist TEXT[] DEFAULT '{}',
  rate_limit_max INTEGER DEFAULT 60,
  rate_limit_window INTEGER DEFAULT 60,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  last_triggered_at TIMESTAMP,
  last_execution_id UUID,
  trigger_count INTEGER DEFAULT 0
);

CREATE INDEX idx_webhook_token ON workflow_webhooks(token);
CREATE INDEX idx_webhook_workflow ON workflow_webhooks(workflow_id);
```

## Logging Format

```
[timestamp] LEVEL module:version EVENT_TYPE community=X user=Y action=Z result=STATUS
```

**Categories**:
- `AUDIT`: Successful operations
- `AUTHZ`: Permission checks
- `ERROR`: Failures
- `SYSTEM`: Service lifecycle

## Example Response Formats

**Success (200 OK)**:
```json
{
  "success": true,
  "data": {"execution_id": "..."},
  "message": "Workflow execution triggered"
}
```

**Error (4xx/5xx)**:
```json
{
  "success": false,
  "error": "ERROR_CODE",
  "message": "Human readable message"
}
```

## Rate Limiting Behavior

- Sliding window algorithm
- Tracked per webhook (not per IP)
- In-memory storage (reset on restart)
- Default: 60 requests per 60 seconds
- Returns 429 when exceeded

## IP Allowlist Support

**CIDR Ranges**:
```json
{"ip_allowlist": ["192.168.1.0/24", "10.0.0.0/8"]}
```

**Individual IPs**:
```json
{"ip_allowlist": ["192.168.1.1", "10.0.0.1"]}
```

**All IPs (empty list)**:
```json
{"ip_allowlist": []}
```

## Workflow Execution

- **Async**: Returns immediately with execution_id
- **Trigger Type**: "webhook"
- **Context**: Includes webhook_id, webhook_name, client_ip
- **Payload**: Any JSON becomes trigger_data

## Testing Commands

### Create Webhook
```bash
curl -X POST http://localhost:8000/api/v1/workflows/test-id/webhooks \
  -H "X-API-Key: test-key" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test"}'
```

### List Webhooks
```bash
curl http://localhost:8000/api/v1/workflows/test-id/webhooks \
  -H "X-API-Key: test-key"
```

### Trigger Webhook (no signature)
```bash
curl -X POST http://localhost:8000/api/v1/workflows/webhooks/token123 \
  -H "Content-Type: application/json" \
  -d '{"test":true}'
```

### Trigger Webhook (with signature)
```bash
BODY='{"test":true}'
TOKEN="abc123"
SECRET="def456"
SIG="sha256=$(echo -n "${TOKEN}${BODY}" | openssl dgst -sha256 -hmac "${SECRET}" -hex | awk '{print $2}')"

curl -X POST http://localhost:8000/api/v1/workflows/webhooks/$TOKEN \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: $SIG" \
  -d "$BODY"
```

## Permissions

| Endpoint | Permission |
|----------|------------|
| POST /webhooks/:token | None (signature-based) |
| GET /webhooks | can_view |
| POST /webhooks | can_edit |
| DELETE /webhooks/:id | can_edit |

## Common Issues

**404 Webhook Not Found**
- Check token spelling
- Verify token is correct
- Ensure webhook exists

**403 IP Not Allowed**
- Check allowlist configuration
- Verify client IP
- Temporarily disable allowlist for testing

**403 Signature Invalid**
- Verify secret is correct
- Check algorithm (must be SHA256)
- Verify message format: token + body
- Check header format: sha256=<hex>

**429 Rate Limit Exceeded**
- Reduce request frequency
- Increase rate_limit_max
- Increase rate_limit_window
- Note: Limits reset on service restart

## Performance Notes

- Token lookup: O(1) with index
- Rate limit check: O(n) where n < 60
- Signature verification: O(payload_size)
- IP check: O(m) where m = allowlist size
- All operations: Async/non-blocking

## Migration from Direct Calls

1. Create webhook → Get token and secret
2. Update client to use webhook URL
3. Implement signature verification
4. Handle 429 rate limit responses
5. Test in staging before production

## References

- Full API docs: `docs/webhook-api.md`
- Integration guide: `WEBHOOK_INTEGRATION.md`
- Controller code: `controllers/webhook_api.py`

---

**Status**: Complete and Production Ready
**Lines of Code**: 1,181
**Test Coverage**: Recommended for critical paths
**Version**: 1.0.0
