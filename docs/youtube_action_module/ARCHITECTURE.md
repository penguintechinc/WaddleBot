# YouTube Action Module - Architecture

## System Design

The YouTube Action Module implements OAuth 2.0 authorization code flow with multi-channel credential management:

### Core Components

```
┌──────────────────────────────────────────────────┐
│        YouTube Action Module (Container)         │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ gRPC Server (Port 50054)                   │  │
│  │ ─ Receives ExecuteAction gRPC messages    │  │
│  │ ─ Routes to YouTubeService                │  │
│  └────────────────────────────────────────────┘  │
│                       │                          │
│                       ▼                          │
│  ┌────────────────────────────────────────────┐  │
│  │ REST API Server (Port 8073)                │  │
│  │ ─ OAuth authorization flow endpoints      │  │
│  │ ─ Action execution endpoints              │  │
│  │ ─ Token/credential management            │  │
│  └────────────────────────────────────────────┘  │
│                       │                          │
│                       ▼                          │
│  ┌────────────────────────────────────────────┐  │
│  │ YouTubeService                             │  │
│  │ ─ Google API client management             │  │
│  │ ─ Action handlers (chat, video, etc.)     │  │
│  │ ─ Error handling & retries                │  │
│  └────────────────────────────────────────────┘  │
│                       │                          │
│                       ▼                          │
│  ┌────────────────────────────────────────────┐  │
│  │ OAuthManager                               │  │
│  │ ─ Authorization code flow                 │  │
│  │ ─ Token storage & refresh                 │  │
│  │ ─ Multi-channel credential management    │  │
│  └────────────────────────────────────────────┘  │
│          │                            │          │
│          ▼                            ▼          │
│    ┌──────────────┐            ┌──────────────┐  │
│    │ PyDAL        │            │ Google Auth  │  │
│    │ Database     │            │ Library      │  │
│    │              │            │              │  │
│    │ Credentials  │            │ OAuth Flow   │  │
│    │ storage      │            │              │  │
│    └──────────────┘            └──────────────┘  │
└──────────────────────────────────────────────────┘
         │                              │
         │ (Database)                   │ (HTTPS)
         ▼                              ▼
    ┌──────────────┐            ┌──────────────────┐
    │ PostgreSQL   │            │ Google Accounts  │
    │ Database     │            │ & APIs           │
    │              │            │                  │
    │ Credentials  │            │ accounts.google. │
    │ History      │            │ com/o/oauth2     │
    └──────────────┘            │ www.googleapis.  │
                                │ com/youtube      │
                                └──────────────────┘
```

## OAuth 2.0 Authorization Code Flow

```
1. User Initiates Authorization
   ├─ Browser: GET /oauth/authorize?state=channel-id
   └─ Module: Returns Google auth URL with:
      ├─ client_id
      ├─ redirect_uri
      ├─ response_type=code
      └─ scopes=[youtube, youtube.force-ssl]
         │
         ▼
2. User Grants Permission
   ├─ Browser redirects to: accounts.google.com/o/oauth2/auth?...
   ├─ User signs in and grants permissions
   └─ Google redirects to callback URL with authorization code
         │
         ▼
3. Exchange Code for Token
   ├─ Module receives: GET /oauth/callback?code=abc123&state=...
   ├─ Module → Google: POST /oauth2/token
   │  ├─ grant_type=authorization_code
   │  ├─ code=abc123
   │  ├─ client_id=...
   │  ├─ client_secret=...
   │  └─ redirect_uri=...
   │
   └─ Google returns:
      ├─ access_token (expires in 3600s)
      ├─ refresh_token (never expires)
      └─ expires_in
         │
         ▼
4. Store Credentials
   ├─ Module stores in database:
   │  ├─ channel_id
   │  ├─ access_token
   │  ├─ refresh_token
   │  ├─ expires_at (calculated)
   │  └─ scopes
   │
   └─ Return success to user
         │
         ▼
5. Future API Calls
   ├─ Check if token expired
   ├─ If yes: Refresh token automatically
   │  ├─ POST /oauth2/token with refresh_token
   │  └─ Get new access_token
   │
   └─ Use access_token for YouTube Data API calls
```

## YouTube Data API v3 Integration

### API Client Setup

```python
# Credentials loaded from database
credentials = google.auth.credentials.Credentials(
    token=access_token,
    refresh_token=refresh_token,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=client_id,
    client_secret=client_secret
)

# Build YouTube Data API client
youtube = build('youtube', 'v3', credentials=credentials)
```

### Example API Call: Send Live Chat Message

```python
# Request structure
request = youtube.liveChatMessages().insert(
    part='snippet',
    body={
        'snippet': {
            'liveChatId': live_chat_id,
            'type': 'messageCreateEvent',
            'messageSnippet': {
                'displayMessage': message_text
            }
        }
    }
)

# Execute request with error handling
try:
    response = request.execute()
    # Returns: {'kind': 'youtube#liveChatMessage', 'id': 'msg_123', ...}
except HttpError as error:
    # Handle error: quotaExceeded, invalidCredentials, etc.
```

## Live Chat Polling Architecture

For monitoring live chat (future enhancement):

```
1. Polling Loop
   ├─ Get live_chat_id from broadcast
   ├─ Poll messages at interval (5-10 seconds)
   └─ Process new messages
         │
         ▼
2. Message Processing
   ├─ Filter by user/content
   ├─ Apply moderation rules
   ├─ Execute commands if configured
   └─ Store in database
         │
         ▼
3. Rate Limiting
   ├─ Track quota usage
   ├─ Implement exponential backoff
   └─ Queue operations during heavy load
```

## Database Schema

### youtube_oauth_credentials Table

```sql
CREATE TABLE youtube_oauth_credentials (
  id INT PRIMARY KEY AUTO_INCREMENT,
  channel_id VARCHAR(100) NOT NULL UNIQUE,
  channel_name VARCHAR(255),
  access_token VARCHAR(2000) NOT NULL,
  refresh_token VARCHAR(1000) NOT NULL,
  token_uri VARCHAR(255),
  client_id VARCHAR(255),
  client_secret VARCHAR(255),
  expires_at TIMESTAMP NOT NULL,
  scopes JSON,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  last_refreshed_at TIMESTAMP,
  INDEX idx_channel_id (channel_id),
  INDEX idx_expires_at (expires_at)
);
```

### action_history Table

```sql
CREATE TABLE action_history (
  id INT PRIMARY KEY AUTO_INCREMENT,
  channel_id VARCHAR(100) NOT NULL,
  action_type VARCHAR(50) NOT NULL,
  resource_id VARCHAR(100),
  success BOOLEAN NOT NULL DEFAULT FALSE,
  error TEXT,
  request_data JSON,
  response_data JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  duration_ms INT,
  INDEX idx_channel_id (channel_id),
  INDEX idx_action_type (action_type),
  INDEX idx_created_at (created_at)
);
```

## Token Refresh Strategy

### Automatic Refresh

```python
def get_valid_credentials(channel_id):
    """Get credentials, refreshing if necessary"""
    creds = load_from_database(channel_id)

    # Check if refresh needed
    if creds.expired and creds.refresh_token:
        # Refresh token automatically
        creds.refresh(request)
        save_to_database(channel_id, creds)

    return creds
```

### Refresh Timing

```
Token Lifetime: 3600 seconds (1 hour)

Proactive Refresh:
├─ Monitor expires_at timestamp
├─ Refresh when expires_at - now < buffer (300s)
└─ Keep tokens fresh for API calls

On-Demand Refresh:
├─ If token expired when API call attempted
├─ Refresh immediately and retry
└─ Fail if refresh fails
```

## Feature Flags Implementation

```python
FEATURES = {
    'ENABLE_CHAT_ACTIONS': os.getenv("ENABLE_CHAT_ACTIONS", "true").lower() == "true",
    'ENABLE_VIDEO_ACTIONS': os.getenv("ENABLE_VIDEO_ACTIONS", "true").lower() == "true",
    'ENABLE_PLAYLIST_ACTIONS': os.getenv("ENABLE_PLAYLIST_ACTIONS", "true").lower() == "true",
    'ENABLE_BROADCAST_ACTIONS': os.getenv("ENABLE_BROADCAST_ACTIONS", "true").lower() == "true",
    'ENABLE_COMMENT_ACTIONS': os.getenv("ENABLE_COMMENT_ACTIONS", "true").lower() == "true",
}

# Usage in handler
if FEATURES['ENABLE_CHAT_ACTIONS']:
    # Allow chat operations
else:
    return {"success": False, "message": "Chat operations disabled"}
```

## Error Handling

### Common YouTube API Errors

```python
try:
    response = youtube_service.execute()
except HttpError as error:
    error_code = error.resp.status

    if error_code == 403:
        # Forbidden - insufficient permissions or quota
        if 'quotaExceeded' in error.content:
            # Daily quota exceeded - wait until next day
        elif 'forbidden' in error.content:
            # User denied access - request new authorization

    elif error_code == 401:
        # Unauthorized - token invalid/expired
        # Attempt refresh, if fails request new authorization

    elif error_code == 404:
        # Not found - resource doesn't exist
        # Verify IDs and parameters

    else:
        # Other errors - log and retry
        logger.error(f"YouTube API error: {error}")
```

## Deployment Architecture

### Container Networking

```
waddlebot-network (Docker bridge)
├── youtube-action-module:8073 (REST)
├── youtube-action-module:50054 (gRPC)
├── waddlebot-router:50051 (sends gRPC)
├── postgres:5432 (credentials)
└── redis:6379 (credential notifications)
```

### Scaling Considerations

Module is stateless with shared database:

- Each instance manages separate OAuth flows
- Shared database stores credentials
- No session affinity required
- Load balancer can route any request to any instance

**Scaling Example:**

```yaml
youtube-action-module:
  replicas: 3
  ports: [8073, 50054]
  # All instances share:
  # - PostgreSQL database
  # - Redis for notifications
  # - OAuth credentials
```

## Performance Optimization

### Connection Pooling

- **HTTP Connections**: Reused via requests library
- **Database Pool**: 10 connections default
- **API Clients**: One per channel (cached)

### Caching Strategy

- **Credentials**: Cache in memory for 5 minutes
- **Channel Info**: Cache for session
- **API Responses**: No caching (real-time)

### Rate Limiting Handling

```
YouTube Limit: 100 requests per 100 seconds

Module Strategy:
├─ Track request count per 100s window
├─ Queue excess requests
├─ Retry with exponential backoff
│  ├─ 1s, 2s, 4s, 8s, 16s...
│  └─ Max 5 retries
└─ Fail after max retries
```

## Security Considerations

### Credential Storage

- Access tokens: Encrypted in database
- Refresh tokens: Encrypted in database
- Client secret: Environment variable only (not in DB)
- Never logged: Tokens redacted from logs

### OAuth Security

- PKCE support: Not used (server-side flow)
- State parameter: Validates authorization response
- HTTPS only: Required for production
- Token validation: Signature verified by Google

### API Key Security

- MODULE_SECRET_KEY: 32+ character minimum
- Stored as environment variable
- Rotated regularly
- Never committed to version control
