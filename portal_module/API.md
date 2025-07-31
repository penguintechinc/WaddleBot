# WaddleBot Unified Community Portal API

The WaddleBot Unified Community Portal provides a comprehensive web interface for community management, identity linking, and OAuth authentication. This document describes all available endpoints and their usage.

## Base Information

- **Framework**: py4web with native features (Auth, Mailer, Forms, Grid, Flash, Fixtures)
- **Base URL**: `http://portal.waddlebot.com` (configurable via `PORTAL_URL`)
- **Port**: 8000 (configurable via `MODULE_PORT`)
- **Authentication**: py4web Auth with OAuth2 provider support

## Architecture Overview

The portal serves as a unified interface that:
- Integrates with the identity_core_module for OAuth and identity management
- Calls various WaddleBot service APIs (router, marketplace, etc.)
- Provides community owners with management dashboards
- Supports both traditional login and OAuth authentication

## Authentication

### Traditional Authentication
- **Login**: `/auth/login` - py4web Auth login
- **Logout**: `/auth/logout` - py4web Auth logout
- **Register**: `/auth/register` - User registration (if enabled)
- **Profile**: `/auth/profile` - User profile management

### OAuth Authentication
- **OAuth Login Page**: `GET /auth/oauth_login` - Shows OAuth provider buttons
- **OAuth Initiate**: `GET /auth/oauth/<provider>` - Redirects to identity service OAuth endpoint
- **OAuth Callback**: `GET /auth/oauth_callback/<provider>` - Handles OAuth provider callbacks

**Supported OAuth Providers**: Discord, Twitch, Slack

## Web Interface Endpoints

### Dashboard & Navigation
- **Root**: `GET /` - Redirects to dashboard if logged in, otherwise login
- **Dashboard**: `GET /dashboard` - Main community dashboard (requires WaddleBot user)

### Community Management
- **Community Details**: `GET /community/<community_id:int>` - Community management page
- **Community Members Grid**: `GET /community/<community_id:int>/members_grid` - py4web Grid for members

### User Management
- **Profile**: `GET /profile` - User profile editing with py4web Form
- **Admin Users**: `GET /admin/users` - Admin user management with py4web Grid (community owners only)

### Identity Management
- **Identity Dashboard**: `GET /identity` - View and manage linked platform identities
- **Link Identity**: `POST /identity/link` - Initiate cross-platform identity linking
- **Verify Identity**: `POST /identity/verify` - Complete identity verification with code
- **Unlink Identity**: `POST /identity/unlink` - Remove platform identity link

### API Key Management
- **API Keys Dashboard**: `GET /api_keys` - View and manage API keys
- **Create API Key**: `POST /api_keys/create` - Create new API key
- **Revoke API Key**: `POST /api_keys/<key_id:int>/revoke` - Revoke API key

## API Endpoints

### Community Integration APIs
These endpoints are called by other WaddleBot modules and chat commands.

#### User Management
```http
POST /api/create_user
Content-Type: application/json

{
    "waddlebot_user_id": "string",
    "email": "string", 
    "display_name": "string" (optional)
}
```

**Response**:
```json
{
    "success": true,
    "user_id": 123,
    "temp_password": "generated_password",
    "email_sent": true
}
```

#### Community Data
```http
GET /api/communities/<waddlebot_user_id>
```

**Response**:
```json
{
    "success": true,
    "communities": [
        {
            "id": 1,
            "name": "Community Name",
            "description": "Description",
            "member_count": 150,
            "entity_group_count": 3,
            "created_at": "2024-01-01T00:00:00Z",
            "settings": {}
        }
    ]
}
```

#### Community Members
```http
GET /api/community/<community_id:int>/members?waddlebot_user_id=<user_id>
```

**Response**:
```json
{
    "success": true,
    "members": [
        {
            "user_id": "user123",
            "display_name": "User Name",
            "role": "member|moderator|admin|owner",
            "reputation": {
                "current_score": 1250,
                "total_events": 45,
                "last_activity": "2024-01-01T00:00:00Z"
            },
            "joined_at": "2024-01-01T00:00:00Z",
            "invited_by": "inviter123"
        }
    ]
}
```

#### Community Modules
```http
GET /api/community/<community_id:int>/modules?waddlebot_user_id=<user_id>
```

**Response**:
```json
{
    "success": true,
    "modules": {
        "core": [
            {
                "id": 1,
                "command": "help",
                "prefix": "!",
                "description": "Show help information",
                "module_type": "local",
                "location": "internal",
                "version": "1.0.0",
                "is_active": true,
                "usage_count": 250,
                "last_used": "2024-01-01T00:00:00Z"
            }
        ],
        "marketplace": []
    }
}
```

#### System Maintenance
```http
GET /api/cleanup
```

**Response**:
```json
{
    "success": true,
    "cleaned_temp_passwords": 5
}
```

## Identity Service Integration

The portal integrates with the identity_core_module through the IdentityAPIClient:

### Identity Management
- `get_user_identities(user_id)` - Get linked platform identities
- `initiate_identity_link(user_id, source_platform, target_platform, target_username)` - Start linking process
- `verify_identity(platform, platform_id, platform_username, verification_code)` - Complete verification
- `unlink_identity(user_id, platform)` - Remove platform link

### API Keys
- `create_api_key(session_token, name, expires_in_days)` - Create API key
- `list_api_keys(session_token)` - List user's API keys
- `revoke_api_key(session_token, key_id)` - Revoke API key
- `regenerate_api_key(session_token, key_id)` - Regenerate API key

### OAuth
- `initiate_oauth_login(provider)` - Get OAuth URL
- `register_user(username, email, password, ...)` - User registration
- `login_user(username, password)` - User login
- `get_user_profile(session_token)` - Get user profile

## Environment Configuration

### Required Environment Variables
```bash
# Database
DATABASE_URL="postgresql://user:pass@host:5432/waddlebot"

# Portal Configuration
PORTAL_URL="https://portal.waddlebot.com"
APP_NAME="WaddleBot Community Portal"

# Identity Service Integration
IDENTITY_API_URL="http://identity-core:8050"
PORTAL_API_KEY="your_api_key_here"
API_TIMEOUT="30"

# Browser Source Integration
BROWSER_SOURCE_BASE_URL="http://browser-source:8027"
```

### Optional Environment Variables
```bash
# SMTP Configuration
SMTP_HOST="smtp.company.com"
SMTP_PORT="587"
SMTP_USERNAME="portal@company.com"
SMTP_PASSWORD="smtp_password"
SMTP_TLS="true"
FROM_EMAIL="noreply@waddlebot.com"

# Logging
LOG_LEVEL="INFO"
LOG_DIR="/var/log/waddlebotlog"
ENABLE_SYSLOG="false"

# Performance
MAX_WORKERS="10"
REQUEST_TIMEOUT="30"
SESSION_TTL="28800"
```

## Database Schema

### Portal-Specific Tables
```sql
-- Community access management
portal_community_access (
    id, user_id, community_id, access_granted_at,
    access_granted_by, is_active
)

-- Temporary password management
portal_temp_passwords (
    id, waddlebot_user_id, temp_password, email,
    expires_at, used, created_at
)
```

### Extended py4web Auth User
```sql
-- Custom fields added to auth_user
auth_user (
    -- Standard py4web fields
    id, username, email, password, first_name, last_name,
    
    -- WaddleBot custom fields
    waddlebot_user_id,      -- Unique WaddleBot user ID
    display_name,           -- Display name for portal
    is_community_owner,     -- Community owner flag
    temp_password_expires,  -- Temp password expiration
    created_by_command,     -- Created via chat command
    last_portal_login       -- Last portal access
)
```

## Security Features

### Authentication & Authorization
- py4web Auth with session management
- OAuth2 integration with platform providers
- Custom fixtures for community owner and WaddleBot user requirements
- API key authentication for service calls

### Security Headers & Settings
- CORS enabled for API endpoints
- Secure session handling with Redis (optional)
- Password complexity settings (relaxed for temp passwords)
- Non-root container execution

### Access Control
- Community owner access control via custom fixtures
- WaddleBot user verification requirements
- Role-based access to admin functions
- Session timeout management

## Integration with Other Modules

### Router Module
- Calls router APIs for command and entity management
- Integrates with RBAC service for permissions
- Real-time community statistics

### Marketplace Module  
- Module installation/management interface
- Community module configurations
- Usage analytics and monitoring

### Browser Source Module
- Provides browser source URLs for communities
- Token management for OBS integration
- Real-time display coordination

### Labels Core Module
- User label management
- Entity group coordination
- Permission-based access via labels

## Development & Testing

### Running Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="sqlite://portal.db"
export PORTAL_URL="http://localhost:8000"

# Run with py4web
python -m py4web run --host 0.0.0.0 --port 8000 portal_module
```

### Docker Development
```bash
# Build container
docker build -t waddlebot/portal:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL="sqlite://portal.db" \
  -e PORTAL_URL="http://localhost:8000" \
  waddlebot/portal:latest
```

### Testing
```bash
# Run tests
pytest tests/

# Test coverage
pytest --cov=portal_module tests/
```

## Monitoring & Health Checks

### Health Endpoints
- `GET /api/cleanup` - System health and cleanup
- Container health check via curl to cleanup endpoint

### Logging
- Structured logging with configurable levels
- Syslog support for centralized logging
- AAA (Authentication, Authorization, Auditing) event logging

### Metrics
- py4web built-in performance monitoring
- Custom performance tracking for API calls
- Session and user activity metrics

## Error Handling

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (missing/invalid parameters)
- `401` - Unauthorized (not logged in)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `500` - Internal Server Error

### Error Responses
```json
{
    "success": false,
    "error": "error_type",
    "message": "Human-readable error message"
}
```

## Rate Limiting & Performance

### Built-in Limits
- Session timeout: 8 hours (configurable)
- Request timeout: 30 seconds (configurable)
- File upload limit: 10MB (configurable via ingress)

### Performance Optimizations
- py4web Grid pagination for large datasets
- Lazy loading of community data
- Efficient database queries with proper indexing
- Redis session storage (optional)

This API documentation provides comprehensive coverage of the WaddleBot Unified Community Portal's capabilities, integrations, and usage patterns.