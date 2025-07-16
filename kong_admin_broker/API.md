# Kong Admin Broker API Documentation

The Kong Admin Broker is a specialized service for managing Kong super admin users in the WaddleBot ecosystem. It provides secure API endpoints for creating, managing, and auditing super admin accounts with full Kong consumer integration.

## Base URL
All API endpoints are accessible through Kong API Gateway:
```
https://your-domain.com/api/broker/
```

## Authentication
All API endpoints require authentication via Broker API key in the header:
```http
X-Broker-Key: your_broker_api_key_here
```

The broker API key is configured via the `BROKER_API_KEY` environment variable and provides full administrative access to Kong user management.

## Endpoints

### 1. Health Check

**Endpoint:** `GET /api/broker/v1/health`

Check the health status of the Kong Admin Broker service. **No authentication required.**

**Response:**
```json
{
  "status": "healthy",
  "kong_admin": "connected",
  "service": "kong_admin_broker",
  "version": "1.0.0",
  "timestamp": 1234567890
}
```

### 2. Create Super Admin User

**Endpoint:** `POST /api/broker/v1/super-admins`

Create a new Kong super admin user with full permissions.

**Request Body:**
```json
{
  "username": "john_admin",
  "email": "john@company.com",
  "full_name": "John Administrator",
  "created_by": "system_admin",
  "permissions": [
    "kong:admin:read",
    "kong:admin:write",
    "waddlebot:admin:read",
    "waddlebot:admin:write",
    "waddlebot:users:manage",
    "waddlebot:services:manage"
  ],
  "notes": "Primary system administrator"
}
```

**Response:**
```json
{
  "success": true,
  "user_id": 123,
  "username": "john_admin",
  "email": "john@company.com",
  "kong_consumer_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "api_key": "wbot_abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567",
  "permissions": [
    "kong:admin:read",
    "kong:admin:write",
    "waddlebot:admin:read",
    "waddlebot:admin:write",
    "waddlebot:users:manage",
    "waddlebot:services:manage"
  ],
  "groups": ["admins", "services", "api-users", "super-admins"],
  "message": "Super admin user 'john_admin' created successfully"
}
```

### 3. Get Super Admin User

**Endpoint:** `GET /api/broker/v1/super-admins/{username}`

Get detailed information about a specific super admin user.

**Response:**
```json
{
  "id": 123,
  "username": "john_admin",
  "email": "john@company.com",
  "full_name": "John Administrator",
  "kong_consumer_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "api_key": "***REDACTED***",
  "permissions": [
    "kong:admin:read",
    "kong:admin:write",
    "waddlebot:admin:read",
    "waddlebot:admin:write",
    "waddlebot:users:manage",
    "waddlebot:services:manage"
  ],
  "groups": ["admins", "services", "api-users", "super-admins"],
  "is_active": true,
  "is_super_admin": true,
  "last_login": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-01T09:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "created_by": "system_admin",
  "notes": "Primary system administrator",
  "kong_consumer": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "username": "john_admin",
    "custom_id": "wbot_admin_john_admin",
    "tags": ["super-admin", "waddlebot", "created-by-system_admin"]
  },
  "kong_acl_groups": ["super-admins", "admins", "services", "api-users"]
}
```

### 4. List Super Admin Users

**Endpoint:** `GET /api/broker/v1/super-admins`

List all super admin users with optional filtering.

**Query Parameters:**
- `include_inactive` (boolean, default: false) - Include deactivated users

**Response:**
```json
{
  "super_admins": [
    {
      "id": 123,
      "username": "john_admin",
      "email": "john@company.com",
      "full_name": "John Administrator",
      "is_active": true,
      "last_login": "2024-01-15T10:30:00Z",
      "created_at": "2024-01-01T09:00:00Z",
      "created_by": "system_admin",
      "permissions_count": 6,
      "groups_count": 4
    }
  ],
  "total_count": 1,
  "include_inactive": false
}
```

### 5. Update Super Admin User

**Endpoint:** `PUT /api/broker/v1/super-admins/{username}`

Update super admin user information and permissions.

**Request Body:**
```json
{
  "email": "john.new@company.com",
  "full_name": "John Senior Administrator",
  "permissions": [
    "kong:admin:read",
    "kong:admin:write",
    "waddlebot:admin:read",
    "waddlebot:admin:write",
    "waddlebot:users:manage",
    "waddlebot:services:manage",
    "waddlebot:billing:manage"
  ],
  "notes": "Promoted to senior administrator with billing access",
  "updated_by": "hr_admin"
}
```

**Response:**
```json
{
  "success": true,
  "username": "john_admin",
  "changes": {
    "email": {
      "old": "john@company.com",
      "new": "john.new@company.com"
    },
    "full_name": {
      "old": "John Administrator",
      "new": "John Senior Administrator"
    },
    "permissions": {
      "old": ["kong:admin:read", "kong:admin:write", "waddlebot:admin:read", "waddlebot:admin:write", "waddlebot:users:manage", "waddlebot:services:manage"],
      "new": ["kong:admin:read", "kong:admin:write", "waddlebot:admin:read", "waddlebot:admin:write", "waddlebot:users:manage", "waddlebot:services:manage", "waddlebot:billing:manage"]
    },
    "notes": {
      "old": "Primary system administrator",
      "new": "Promoted to senior administrator with billing access"
    }
  },
  "message": "Super admin user 'john_admin' updated successfully"
}
```

### 6. Deactivate Super Admin User

**Endpoint:** `POST /api/broker/v1/super-admins/{username}/deactivate`

Deactivate (soft delete) a super admin user and remove Kong ACL permissions.

**Request Body:**
```json
{
  "deactivated_by": "hr_admin",
  "reason": "Employee termination - access revoked per security policy"
}
```

**Response:**
```json
{
  "success": true,
  "username": "john_admin",
  "message": "Super admin user 'john_admin' deactivated successfully"
}
```

### 7. Regenerate API Key

**Endpoint:** `POST /api/broker/v1/super-admins/{username}/regenerate-key`

Regenerate the API key for a super admin user (security rotation).

**Request Body:**
```json
{
  "regenerated_by": "security_admin"
}
```

**Response:**
```json
{
  "success": true,
  "username": "john_admin",
  "new_api_key": "wbot_xyz789abc012def345ghi678jkl901mno234pqr567stu890vwx123",
  "message": "API key regenerated for user 'john_admin'"
}
```

### 8. Get Audit Log

**Endpoint:** `GET /api/broker/v1/audit-log`

Retrieve audit log entries for super admin activities.

**Query Parameters:**
- `username` (string, optional) - Filter by username
- `action` (string, optional) - Filter by action type
- `limit` (integer, default: 100, max: 1000) - Number of entries to return
- `offset` (integer, default: 0) - Pagination offset

**Response:**
```json
{
  "audit_logs": [
    {
      "id": 456,
      "action": "create_super_admin",
      "resource_type": "user",
      "resource_id": "123",
      "details": {
        "username": "john_admin",
        "email": "john@company.com",
        "full_name": "John Administrator",
        "kong_consumer_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "permissions": ["kong:admin:read", "kong:admin:write"],
        "groups": ["admins", "services", "api-users", "super-admins"]
      },
      "performed_by": "system_admin",
      "ip_address": "192.168.1.100",
      "status": "success",
      "error_message": null,
      "created_at": "2024-01-01T09:00:00Z"
    }
  ],
  "count": 1,
  "limit": 100,
  "offset": 0,
  "filters": {
    "username": null,
    "action": null
  }
}
```

### 9. Backup Super Admins

**Endpoint:** `POST /api/broker/v1/backup`

Create a complete backup of all super admin users and their Kong configurations.

**Request Body:**
```json
{
  "backup_type": "scheduled",
  "created_by": "backup_service"
}
```

**Response:**
```json
{
  "success": true,
  "total_users": 5,
  "successful_backups": 5,
  "failed_backups": 0,
  "backup_results": [
    {
      "username": "john_admin",
      "backup_id": 789,
      "status": "success"
    }
  ],
  "failed_backups": [],
  "message": "Backup completed. 5 successful, 0 failed."
}
```

### 10. Get Kong Information

**Endpoint:** `GET /api/broker/v1/kong/info`

Get Kong server information and broker status.

**Response:**
```json
{
  "kong_info": {
    "version": "3.4.0",
    "node_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "hostname": "kong-container",
    "plugins": {
      "available_on_server": ["key-auth", "rate-limiting", "cors"]
    }
  },
  "admin_url": "http://kong:8001",
  "broker_version": "1.0.0"
}
```

### 11. List Kong Consumers

**Endpoint:** `GET /api/broker/v1/kong/consumers`

List all Kong consumers with pagination.

**Query Parameters:**
- `size` (integer, default: 100, max: 1000) - Number of consumers per page
- `offset` (string, optional) - Pagination offset token

**Response:**
```json
{
  "data": [
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "username": "john_admin",
      "custom_id": "wbot_admin_john_admin",
      "tags": ["super-admin", "waddlebot"],
      "created_at": 1704063600
    }
  ],
  "total": 1,
  "next": null
}
```

### 12. Backup Kong Consumer

**Endpoint:** `POST /api/broker/v1/kong/consumers/{username}/backup`

Create a backup of a specific Kong consumer's configuration.

**Response:**
```json
{
  "success": true,
  "username": "john_admin",
  "backup_data": {
    "consumer": {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "username": "john_admin",
      "custom_id": "wbot_admin_john_admin",
      "tags": ["super-admin", "waddlebot"]
    },
    "api_keys": [
      {
        "id": "key-123",
        "key": "wbot_abc123def456...",
        "tags": ["super-admin", "admin-api"]
      }
    ],
    "acl_groups": [
      {
        "id": "acl-456",
        "group": "super-admins"
      }
    ],
    "backup_timestamp": "2024-01-15T10:30:00Z"
  },
  "message": "Backup created for consumer 'john_admin'"
}
```

### 13. Get Statistics

**Endpoint:** `GET /api/broker/v1/statistics`

Get comprehensive statistics about super admin users and Kong status.

**Response:**
```json
{
  "super_admins": {
    "active_count": 5,
    "inactive_count": 2,
    "total_count": 7
  },
  "kong": {
    "total_consumers": 150,
    "admin_url": "http://kong:8001",
    "health": true
  },
  "recent_activity": {
    "audit_log_entries": 25,
    "last_activity": "2024-01-15T10:30:00Z"
  },
  "broker": {
    "version": "1.0.0",
    "uptime_check": "healthy"
  }
}
```

## Kong Integration

### Consumer Management
The broker automatically manages Kong consumers for super admin users:

- **Consumer Creation**: Automatically creates Kong consumers with appropriate tags
- **API Key Management**: Generates secure API keys and manages rotation
- **ACL Group Assignment**: Assigns users to `super-admins` and other required groups
- **Cleanup**: Properly removes ACL memberships when deactivating users

### Security Features

**API Key Security:**
- 64-character secure random API keys with `wbot_` prefix
- Automatic key rotation capabilities
- Keys are hashed and stored securely

**Audit Logging:**
- Complete audit trail of all administrative actions
- IP address and user agent tracking
- Detailed change tracking with before/after values

**Access Control:**
- Broker-level authentication via secure API key
- Kong-level rate limiting (100/min, 1000/hour)
- CORS protection for web applications

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": {
    "code": 400,
    "message": "Username is required",
    "type": "validation_error"
  }
}
```

Common HTTP status codes:
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (missing/invalid broker key)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (user not found)
- `409` - Conflict (username/email already exists)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error (system failure)
- `503` - Service Unavailable (Kong admin API offline)

## Usage Examples

### Using curl

```bash
# Create super admin user
curl -X POST https://your-domain.com/api/broker/v1/super-admins \
  -H "X-Broker-Key: your_broker_key" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_admin",
    "email": "john@company.com",
    "full_name": "John Administrator",
    "created_by": "system_admin"
  }'

# List all super admin users
curl -X GET https://your-domain.com/api/broker/v1/super-admins \
  -H "X-Broker-Key: your_broker_key"

# Get audit log
curl -X GET "https://your-domain.com/api/broker/v1/audit-log?limit=50" \
  -H "X-Broker-Key: your_broker_key"

# Health check (no auth required)
curl https://your-domain.com/broker/health
```

### Using Python

```python
import requests

# Configure broker client
BROKER_BASE = "https://your-domain.com/api/broker"
BROKER_KEY = "your_broker_key"
headers = {"X-Broker-Key": BROKER_KEY, "Content-Type": "application/json"}

# Create super admin user
response = requests.post(
    f"{BROKER_BASE}/v1/super-admins",
    headers=headers,
    json={
        "username": "john_admin",
        "email": "john@company.com",
        "full_name": "John Administrator",
        "created_by": "system_admin"
    }
)

result = response.json()
print(f"Created user: {result['username']}")
print(f"API Key: {result['api_key']}")
```

### Using JavaScript/Node.js

```javascript
const axios = require('axios');

const brokerClient = axios.create({
  baseURL: 'https://your-domain.com/api/broker',
  headers: {
    'X-Broker-Key': 'your_broker_key',
    'Content-Type': 'application/json'
  }
});

// Create super admin user
async function createSuperAdmin(userData) {
  try {
    const response = await brokerClient.post('/v1/super-admins', userData);
    console.log('Super admin created:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error creating super admin:', error.response?.data || error.message);
  }
}

// Usage
createSuperAdmin({
  username: 'john_admin',
  email: 'john@company.com',
  full_name: 'John Administrator',
  created_by: 'system_admin'
});
```

## Environment Configuration

Configure the Kong Admin Broker using environment variables:

```bash
# Kong Admin API
KONG_ADMIN_URL=http://kong:8001
KONG_ADMIN_USERNAME=admin
KONG_ADMIN_PASSWORD=admin_password

# Broker Security
BROKER_SECRET_KEY=waddlebot_broker_secret_key_change_me_in_production
BROKER_API_KEY=wbot_broker_master_key_placeholder

# Database
DATABASE_URL=postgresql://waddlebot:waddlebot_password@db:5432/waddlebot

# Super Admin Configuration
SUPER_ADMIN_GROUP=super-admins
API_KEY_LENGTH=64
REQUIRE_EMAIL_VERIFICATION=false

# Logging
LOG_LEVEL=INFO

# Email (optional)
SMTP_HOST=smtp.company.com
SMTP_USERNAME=broker@company.com
SMTP_PASSWORD=smtp_password
FROM_EMAIL=noreply@waddlebot.com
```

## Security Considerations

**Production Deployment:**
- Change default `BROKER_API_KEY` to a secure random value
- Use HTTPS for all API communications
- Implement network-level access controls
- Regular API key rotation for super admin users
- Monitor audit logs for suspicious activity

**Kong Integration:**
- Ensure Kong Admin API is not publicly accessible
- Use Kong's built-in security features (rate limiting, IP restrictions)
- Regular backup of Kong configuration
- Monitor Kong consumer creation and modifications

For additional security best practices, see the main WaddleBot security documentation.