# WaddleBot Identity Core Module

Cross-platform identity linking and verification system built on py4web Auth with comprehensive API key management.

## Features

### Core Identity Management
- **py4web Auth Integration**: Built on py4web's robust authentication system
- **Cross-Platform Linking**: Link Discord, Twitch, and Slack accounts to single WaddleBot identity
- **Verification System**: Secure whisper/DM-based verification with time-limited codes
- **User API Keys**: Self-service API key generation with same permissions as user identity

### Platform Support
- **Twitch**: Whisper-based verification via Twitch API
- **Discord**: Direct message verification via Discord bot
- **Slack**: Direct message verification via Slack API

### Security Features
- **Secure Verification Codes**: 6-character alphanumeric codes (excluding ambiguous characters)
- **Time-Limited Codes**: 10-minute expiration with resend capability
- **Rate Limiting**: Protects against spam and abuse
- **Comprehensive Logging**: Full AAA (Authentication, Authorization, Auditing) logging
- **API Key Security**: SHA-256 hashed storage, configurable expiration

## API Endpoints

### Platform Linking
- `POST /identity/link` - Initiate cross-platform identity linking
- `POST /identity/verify` - Verify identity with whisper/DM code
- `GET /identity/user/<user_id>` - Get user's linked identities
- `GET /identity/platform/<platform>/<platform_id>` - Get user ID for platform user
- `DELETE /identity/unlink` - Unlink a platform identity

### API Key Management
- `POST /identity/api-keys` - Create API key for authenticated user
- `GET /identity/api-keys` - List user's API keys
- `DELETE /identity/api-keys/<key_id>` - Revoke API key
- `POST /identity/api-keys/<key_id>/regenerate` - Regenerate API key

### User Management (py4web Auth)
- `POST /auth/register` - Register new user account
- `POST /auth/login` - Login user session
- `POST /auth/logout` - Logout user session
- `GET /auth/profile` - Get user profile information
- `PUT /auth/profile` - Update user profile

### Administration
- `GET /identity/stats` - Get identity statistics
- `GET /health` - Health check endpoint

## Usage Example

### Linking Platforms
1. User types `!identity link twitch penguinzplays` in Discord
2. Identity module sends verification code to penguinzplays on Twitch via whisper
3. User types `!verify ABC123` in Twitch chat
4. Identity module verifies code and links both accounts to single WaddleBot user

### API Key Management
```bash
# Create API key
curl -X POST http://identity-core:8050/identity/api-keys \
  -H "Authorization: Bearer <user_session>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Bot Key", "expires_in_days": 365}'

# Use API key
curl -X GET http://identity-core:8050/identity/user/123 \
  -H "X-API-Key: wbot_user_..."
```

## Database Schema

### Core Tables
- `auth_user` - py4web user accounts (extended with WaddleBot fields)
- `platform_identities` - Links platform accounts to WaddleBot users
- `identity_verifications` - Pending verification requests
- `user_api_keys` - User-generated API keys for programmatic access

### Extended py4web Fields
- `waddlebot_display_name` - Custom display name
- `primary_platform` - Primary platform for user
- `reputation_score` - User reputation points
- `metadata` - Additional user metadata

## Configuration

### Environment Variables
```bash
# Module Configuration
MODULE_NAME=identity_core_module
MODULE_VERSION=1.0.0
MODULE_PORT=8050

# Database
DATABASE_URL=postgresql://user:pass@host:5432/waddlebot

# Redis (for caching and rate limiting)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_password

# Security
SECRET_KEY=your_secret_key
VALID_API_KEYS=system_key1,system_key2
MAX_API_KEYS_PER_USER=5

# Platform APIs
TWITCH_API_URL=http://twitch-collector:8002
DISCORD_API_URL=http://discord-collector:8003
SLACK_API_URL=http://slack-collector:8004

# Email (py4web Mailer)
SMTP_HOST=smtp.company.com
SMTP_USERNAME=identity@company.com
SMTP_PASSWORD=smtp_password
FROM_EMAIL=noreply@waddlebot.com

# Verification Settings
VERIFICATION_CODE_LENGTH=6
VERIFICATION_TIMEOUT_MINUTES=10
RESEND_COOLDOWN_SECONDS=60
```

## Deployment

### Docker
```bash
docker build -t waddlebot/identity-core-module .
docker run -p 8050:8050 waddlebot/identity-core-module
```

### Kubernetes
```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
```

## Integration with WaddleBot Router

The identity module automatically registers the following commands with the router:
- `!identity link <platform> <username>` - Link platform account
- `!identity unlink <platform>` - Unlink platform account
- `!identity status` - Check identity status
- `!verify <code>` - Verify identity with code
- `!whoami` - Show WaddleBot identity

## Security Considerations

### Authentication
- py4web session-based authentication for web interface
- API key authentication for programmatic access
- System API keys for inter-module communication

### Verification Security
- Time-limited verification codes (10 minutes)
- Rate limiting to prevent spam
- Secure code generation (excludes ambiguous characters)
- Platform-specific whisper/DM delivery

### Data Protection
- API keys stored as SHA-256 hashes
- Comprehensive audit logging
- User data anonymization in logs
- Secure session management

## Logging

Comprehensive AAA logging with structured output:
- **Authentication**: Login attempts, API key usage
- **Authorization**: Permission checks, rate limiting
- **Auditing**: All user actions with full context
- **System Events**: Module status, health checks

Log format:
```
[timestamp] LEVEL module:version EVENT_TYPE user=X platform=Y action=Z result=STATUS [details]
```

## Development

### Running Tests
```bash
python -m pytest tests/ -v
```

### Code Structure
```
identity_core_module/
├── app.py                 # Main py4web application
├── models.py             # Database models
├── config.py             # Configuration
├── logging_config.py     # AAA logging setup
├── services/             # Service layer
│   ├── platform_service.py   # Platform whisper/DM
│   ├── verification_service.py # Code generation
│   ├── router_service.py     # Router integration
│   └── identity_service.py   # Core identity logic
├── tests/                # Unit tests
├── k8s/                  # Kubernetes manifests
└── Dockerfile           # Container definition
```

## Contributing

1. Follow WaddleBot code patterns and conventions
2. Include comprehensive unit tests
3. Use structured logging for all operations
4. Follow security best practices
5. Update documentation for new features