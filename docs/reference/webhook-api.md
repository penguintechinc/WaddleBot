# Webhook API Reference

## Overview

The Webhook API provides a secure, public-facing endpoint to trigger workflow executions from external services. This document covers:

- Public webhook trigger endpoint (no authentication required)
- Webhook management (CRUD operations with authentication)
- Security features (HMAC verification, IP allowlisting, rate limiting)
- Configuration and best practices

## Architecture

### Components

1. **WebhookConfig**: Dataclass holding webhook metadata and configuration
2. **WebhookRateLimiter**: In-memory sliding window rate limiter
3. **Public Endpoint**: `/api/v1/workflows/webhooks/<token>`
4. **Management Endpoints**: `/api/v1/workflows/<id>/webhooks`

### Security Features

- **HMAC-SHA256 Signature Verification**: Validates webhook payload integrity
- **IP Allowlisting**: Restricts webhook triggers to specific IP addresses/CIDR ranges
- **Rate Limiting**: 60 requests/minute per webhook (configurable)
- **Secure Token Generation**: 32-character hex tokens for webhook identification
- **Secret Management**: Separate HMAC secrets for signature verification
- **AAA Logging**: Comprehensive Authentication, Authorization, and Audit logging

## Endpoints

### POST /api/v1/workflows/webhooks/:token

Publicly accessible webhook trigger endpoint.

**Authentication**: None (but signature verification recommended)

**Request**:

```http
POST /api/v1/workflows/webhooks/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6 HTTP/1.1
Content-Type: application/json
X-Webhook-Signature: sha256=abc123def456...

{
  "event": "user.created",
  "user_id": 12345,
  "username": "john_doe",
  "email": "john@example.com",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Headers**:

| Header | Required | Description |
|--------|----------|-------------|
| `Content-Type` | Optional | Should be `application/json` for JSON payloads |
| `X-Webhook-Signature` | Conditional | HMAC-SHA256 signature (required if webhook has `require_signature=true`) |

**Query Parameters**: None

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `token` | string | Public webhook token (32-char hex) |

**Request Body**:

Any valid JSON object. This payload is passed to the workflow execution as trigger data.

**Response (200 OK)**:

```json
{
  "success": true,
  "data": {
    "execution_id": "550e8400-e29b-41d4-a716-446655440000",
    "webhook_id": "550e8400-e29b-41d4-a716-446655440001",
    "workflow_id": "550e8400-e29b-41d4-a716-446655440002",
    "status": "queued",
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "message": "Workflow execution triggered"
}
```

**Response (400 Bad Request)**:

```json
{
  "success": false,
  "error": "BAD_REQUEST",
  "message": "Invalid JSON payload"
}
```

**Response (403 Forbidden)**:

```json
{
  "success": false,
  "error": "IP_NOT_ALLOWED",
  "message": "IP address not allowed"
}
```

**Response (404 Not Found)**:

```json
{
  "success": false,
  "error": "WEBHOOK_NOT_FOUND",
  "message": "Webhook not found"
}
```

**Response (429 Too Many Requests)**:

```json
{
  "success": false,
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded (max 60 requests per 60s)"
}
```

---

### GET /api/v1/workflows/:id/webhooks

List all webhooks for a workflow.

**Authentication**: Required (API Key)

**Authorization**: Requires `can_view` permission on workflow

**Request**:

```http
GET /api/v1/workflows/550e8400-e29b-41d4-a716-446655440000/webhooks?community_id=123 HTTP/1.1
X-API-Key: your-api-key
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `community_id` | integer | Optional | Community ID for permission context |

**Response (200 OK)**:

```json
{
  "success": true,
  "data": [
    {
      "webhook_id": "550e8400-e29b-41d4-a716-446655440001",
      "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
      "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
      "name": "User Signup Webhook",
      "description": "Triggered when new users sign up",
      "url": "https://api.example.com/api/v1/workflows/webhooks/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
      "enabled": true,
      "require_signature": true,
      "ip_allowlist": ["192.168.1.0/24"],
      "rate_limit_max": 60,
      "rate_limit_window": 60,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "last_triggered_at": "2024-01-02T10:30:00Z",
      "trigger_count": 42
    }
  ],
  "message": "Retrieved 1 webhooks"
}
```

---

### POST /api/v1/workflows/:id/webhooks

Create a new webhook for a workflow.

**Authentication**: Required (API Key)

**Authorization**: Requires `can_edit` permission on workflow

**Request**:

```http
POST /api/v1/workflows/550e8400-e29b-41d4-a716-446655440000/webhooks HTTP/1.1
Content-Type: application/json
X-API-Key: your-api-key

{
  "name": "User Signup Webhook",
  "description": "Triggered when new users sign up",
  "require_signature": true,
  "ip_allowlist": ["192.168.1.0/24", "10.0.0.1"],
  "rate_limit_max": 100,
  "rate_limit_window": 60,
  "community_id": 123
}
```

**Request Body**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Display name for the webhook |
| `description` | string | No | null | Long description of webhook purpose |
| `require_signature` | boolean | No | true | Enforce HMAC signature verification |
| `ip_allowlist` | array | No | [] | List of allowed IPs/CIDR ranges (empty = all) |
| `rate_limit_max` | integer | No | 60 | Max requests per rate_limit_window |
| `rate_limit_window` | integer | No | 60 | Time window in seconds |
| `enabled` | boolean | No | true | Whether webhook is active |
| `community_id` | integer | No | - | Community context (for auditing) |

**Response (201 Created)**:

```json
{
  "success": true,
  "data": {
    "webhook_id": "550e8400-e29b-41d4-a716-446655440001",
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    "name": "User Signup Webhook",
    "description": "Triggered when new users sign up",
    "url": "https://api.example.com/api/v1/workflows/webhooks/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    "enabled": true,
    "require_signature": true,
    "ip_allowlist": ["192.168.1.0/24"],
    "rate_limit_max": 100,
    "rate_limit_window": 60,
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z",
    "trigger_count": 0
  },
  "message": "Webhook created successfully"
}
```

**Note**: The response includes the `token` (public) but not the `secret`. Store both securely on your client side.

---

### DELETE /api/v1/workflows/:id/webhooks/:webhookId

Delete a webhook.

**Authentication**: Required (API Key)

**Authorization**: Requires `can_edit` permission on workflow

**Request**:

```http
DELETE /api/v1/workflows/550e8400-e29b-41d4-a716-446655440000/webhooks/550e8400-e29b-41d4-a716-446655440001?community_id=123 HTTP/1.1
X-API-Key: your-api-key
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `community_id` | integer | Optional | Community ID for permission context |

**Response (200 OK)**:

```json
{
  "success": true,
  "data": {
    "webhook_id": "550e8400-e29b-41d4-a716-446655440001"
  },
  "message": "Webhook deleted successfully"
}
```

---

## HMAC Signature Verification

When a webhook has `require_signature=true`, you must include an `X-Webhook-Signature` header with your request.

### Signature Format

```
X-Webhook-Signature: sha256=<hex_digest>
```

### Calculation Algorithm

1. Concatenate the webhook token and request body:
   ```
   message = token.encode() + body
   ```

2. Calculate HMAC-SHA256:
   ```
   signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
   ```

3. Format with prefix:
   ```
   header_value = "sha256=" + signature
   ```

### Example (Python)

```python
import hmac
import hashlib

def sign_webhook_request(token: str, secret: str, body: bytes) -> str:
    """Generate HMAC-SHA256 signature for webhook request"""
    message = token.encode() + body
    signature = hmac.new(
        secret.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

# Usage
token = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
secret = "b1c2d3e4f5g6h7i8j9k0l1m2n3o4p5q6"
payload = b'{"event": "user.created", "user_id": 12345}'

signature = sign_webhook_request(token, secret, payload)
# headers: {"X-Webhook-Signature": signature}
```

### Example (JavaScript)

```javascript
const crypto = require('crypto');

function signWebhookRequest(token, secret, body) {
  const message = token + body;
  const signature = crypto
    .createHmac('sha256', secret)
    .update(message)
    .digest('hex');
  return `sha256=${signature}`;
}

// Usage
const token = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6";
const secret = "b1c2d3e4f5g6h7i8j9k0l1m2n3o4p5q6";
const payload = JSON.stringify({event: 'user.created', user_id: 12345});

const signature = signWebhookRequest(token, secret, payload);
// headers: {"X-Webhook-Signature": signature}
```

---

## IP Allowlisting

Webhooks can be configured to only accept requests from specific IP addresses or CIDR ranges.

### Configuration

```json
{
  "name": "Secure Webhook",
  "ip_allowlist": [
    "192.168.1.0/24",      // CIDR range
    "10.0.0.1",             // Single IP
    "10.20.0.0/16"          // Another range
  ]
}
```

### Behavior

- **Empty allowlist**: All IPs are allowed (default)
- **Non-empty allowlist**: Only specified IPs/ranges are allowed
- **Request rejected**: Returns 403 Forbidden if IP not allowed

### Example Error Response

```json
{
  "success": false,
  "error": "IP_NOT_ALLOWED",
  "message": "IP address not allowed"
}
```

---

## Rate Limiting

Webhooks implement sliding window rate limiting to prevent abuse.

### Configuration

```json
{
  "name": "Rate Limited Webhook",
  "rate_limit_max": 100,     // Max 100 requests...
  "rate_limit_window": 60    // ...per 60 seconds
}
```

### Default Limits

- **Requests per minute**: 60 (configurable per webhook)
- **Window**: 60 seconds

### Example Error Response

```json
{
  "success": false,
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded (max 60 requests per 60s)"
}
```

### Behavior

- Requests are counted in a sliding window
- Old requests outside the window are automatically discarded
- Rate limits are enforced per webhook (not per user)
- In-memory storage (reset on service restart)

---

## Webhook Lifecycle

### Creation Flow

```
1. POST /api/v1/workflows/:id/webhooks
   - Generate webhook token (public)
   - Generate webhook secret (private)
   - Create webhook configuration
   - Store in database
   - Return URL with token
```

### Trigger Flow

```
1. External service calls: POST /api/v1/workflows/webhooks/:token
2. Server validates:
   - Token exists and is enabled
   - Client IP is in allowlist
   - HMAC signature is valid (if required)
   - Rate limit not exceeded
3. Server triggers workflow execution
4. Return execution_id to caller
5. Workflow executes asynchronously
```

### Deletion Flow

```
1. DELETE /api/v1/workflows/:id/webhooks/:webhookId
2. Server validates user permissions
3. Delete webhook from database
4. Future requests to token return 404
```

---

## Best Practices

### For Webhook Creators

1. **Always enable signature verification**: `require_signature: true`
2. **Set appropriate rate limits**: Consider your expected traffic
3. **Use IP allowlisting**: Restrict to known source IPs
4. **Secure the secret**: Store the webhook secret securely (never in version control)
5. **Monitor trigger count**: Check `last_triggered_at` and `trigger_count` regularly
6. **Set descriptive names**: Help future maintainers understand the webhook purpose

### For Webhook Consumers

1. **Verify signatures**: Always validate `X-Webhook-Signature` headers
2. **Handle retries**: Design workflows to be idempotent
3. **Log all requests**: Track webhook triggers for debugging
4. **Monitor rate limits**: Implement exponential backoff on 429 responses
5. **Update payload schema**: Test with real webhook data before deployment
6. **Set appropriate timeouts**: Use 30-60 second timeouts

### Security Checklist

- [ ] HTTPS only (TLS 1.2+)
- [ ] Signature verification enabled
- [ ] IP allowlist configured
- [ ] Rate limits set appropriately
- [ ] Secrets not logged or exposed
- [ ] Audit logging enabled
- [ ] Error responses don't leak sensitive data
- [ ] Webhook URLs not shared publicly

---

## Database Schema

### workflow_webhooks Table

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
  ip_allowlist TEXT[],           -- JSON array
  rate_limit_max INTEGER DEFAULT 60,
  rate_limit_window INTEGER DEFAULT 60,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  last_triggered_at TIMESTAMP,
  last_execution_id UUID,
  trigger_count INTEGER DEFAULT 0,

  FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
);

CREATE INDEX idx_webhook_token ON workflow_webhooks(token);
CREATE INDEX idx_webhook_workflow ON workflow_webhooks(workflow_id);
```

---

## Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `WEBHOOK_NOT_FOUND` | 404 | Webhook token does not exist |
| `WEBHOOK_DISABLED` | 403 | Webhook exists but is disabled |
| `IP_NOT_ALLOWED` | 403 | Client IP not in allowlist |
| `SIGNATURE_REQUIRED` | 403 | Signature header missing (required) |
| `SIGNATURE_INVALID` | 403 | Signature verification failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INVALID_JSON` | 400 | Malformed JSON payload |
| `WORKFLOW_NOT_FOUND` | 404 | Workflow does not exist |
| `PERMISSION_DENIED` | 403 | User lacks required permissions |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Logging

All webhook operations are logged with AAA (Authentication, Authorization, Audit) categories:

### Log Format

```
[timestamp] LEVEL module:version EVENT_TYPE community=X user=Y action=Z result=STATUS
```

### Example Logs

```
2024-01-01T12:00:00 INFO workflow_core_module:1.0.0 AUDIT community=123 user=456 action=trigger_webhook_public webhook_id=abc123 result=SUCCESS

2024-01-01T12:00:01 WARNING workflow_core_module:1.0.0 AUDIT community=123 user=unknown action=trigger_webhook_public webhook_id=abc123 result=SIGNATURE_INVALID

2024-01-01T12:00:02 INFO workflow_core_module:1.0.0 AUDIT community=123 user=456 action=create_webhook workflow_id=def456 webhook_id=abc123 result=SUCCESS
```

### Log Categories

- `AUDIT`: Webhook creation, deletion, triggers (successful)
- `AUTHZ`: Permission checks, authorization failures
- `ERROR`: Internal errors, parsing failures
- `SYSTEM`: Service startup/shutdown

---

## Testing

### Test Webhook Creation

```bash
curl -X POST https://api.example.com/api/v1/workflows/{workflow_id}/webhooks \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Webhook",
    "description": "For testing",
    "require_signature": true,
    "rate_limit_max": 60
  }'
```

### Test Webhook Trigger (with signature)

```bash
# Generate signature
TOKEN="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
SECRET="b1c2d3e4f5g6h7i8j9k0l1m2n3o4p5q6"
PAYLOAD='{"test": true}'

SIGNATURE="sha256=$(echo -n "${TOKEN}${PAYLOAD}" | openssl dgst -sha256 -hmac "${SECRET}" | awk '{print $2}')"

curl -X POST https://api.example.com/api/v1/workflows/webhooks/${TOKEN} \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: ${SIGNATURE}" \
  -d "${PAYLOAD}"
```

---

## Migration Guide

### From Direct Workflow Calls

If you previously called workflows directly, switching to webhooks:

1. Create webhook via API
2. Store token and secret securely
3. Update request URLs to use webhook endpoint
4. Add signature verification
5. Handle 429 rate limit responses

### Webhook Update

To modify an existing webhook, delete and recreate (API does not support PATCH):

```bash
# Delete old webhook
curl -X DELETE https://api.example.com/api/v1/workflows/{id}/webhooks/{webhook_id}

# Create new webhook with updated config
curl -X POST https://api.example.com/api/v1/workflows/{id}/webhooks ...
```

---

## FAQ

**Q: Can I update webhook configuration?**
A: Currently, webhooks are immutable after creation. Delete and recreate to modify.

**Q: What if the server restarts? Do rate limits persist?**
A: No, rate limits are stored in-memory. After restart, limit counters reset.

**Q: Can webhooks be used for other workflow triggers?**
A: No, webhooks are specifically for external HTTP-triggered workflows. Use the workflow engine directly for internal triggers.

**Q: How long are webhooks retained?**
A: Indefinitely, until manually deleted. Monitor unused webhooks.

**Q: Can I test webhooks before deploying to production?**
A: Yes, create a test webhook with debug logging enabled. Monitor logs in real-time.

---

## Support

For issues or questions:
- Check logs: `/var/log/waddlebotlog/`
- Review this documentation
- Contact the Waddles team
