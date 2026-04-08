# Security Core Module - Reference

Community security policies, content filtering, spam detection, and warning management.

## Overview

The Security Core module manages community safety through configurable security policies, content filtering, spam detection, and user warning systems. It provides APIs for both management and real-time content checking.

## Key Features

- **Per-Community Security Policies** - Configurable security settings per community
- **Content Filtering** - Block messages containing specified words/patterns
- **Spam Detection** - Automatic spam detection with configurable thresholds
- **Warning System** - Issue and track user warnings with auto-ban policies
- **Moderation Logging** - Complete audit trail of moderation actions
- **Cross-Platform Synchronization** - Sync moderation actions across multiple platforms

## Configuration

### Environment Variables

```bash
# Security Service
MODULE_PORT=8050
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/waddlebot
DB_POOL_SIZE=10

# Service Authentication
SERVICE_API_KEY=your-secret-key
```

## REST API Endpoints

### Configuration Management

#### Get Community Security Config
```
GET /api/v1/security/<community_id>/config
```

Returns security configuration for a specific community.

**Response** (200 OK):
```json
{
  "community_id": 123,
  "max_warnings": 3,
  "warning_expiry_days": 30,
  "auto_ban_on_warnings": true,
  "spam_detection_enabled": true,
  "spam_threshold": 0.7,
  "content_filter_enabled": true,
  "blocked_words": ["spam", "abuse"],
  "created_at": "2025-02-05T10:30:15Z",
  "updated_at": "2025-02-05T10:30:15Z"
}
```

#### Update Community Security Config
```
PUT /api/v1/security/<community_id>/config
```

Update security configuration for a community.

**Request**:
```json
{
  "max_warnings": 5,
  "warning_expiry_days": 30,
  "auto_ban_on_warnings": true,
  "spam_detection_enabled": true,
  "spam_threshold": 0.7,
  "content_filter_enabled": true
}
```

**Response** (200 OK):
```json
{
  "community_id": 123,
  "max_warnings": 5,
  ...
}
```

### Warning Management

#### List Community Warnings
```
GET /api/v1/security/<community_id>/warnings
```

List all warnings for a community.

**Query Parameters**:
- `status` (optional): "active", "expired", "all" (default: "active")
- `page` (optional): Page number (default: 1)
- `limit` (optional): Results per page (default: 25)

**Response** (200 OK):
```json
{
  "success": true,
  "warnings": [
    {
      "id": 456,
      "community_id": 123,
      "platform": "twitch",
      "platform_user_id": "user456",
      "warning_reason": "Spam detected",
      "warning_type": "automatic",
      "issued_at": "2025-02-05T10:30:15Z",
      "issued_by": 789,
      "status": "active",
      "expires_at": "2025-03-07T10:30:15Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 25,
    "total": 42
  }
}
```

#### Issue Manual Warning
```
POST /api/v1/security/<community_id>/warnings
```

Issue a manual warning to a user.

**Request**:
```json
{
  "platform": "twitch",
  "platform_user_id": "user456",
  "warning_reason": "Inappropriate language",
  "issued_by": 789
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "warning": {
    "id": 456,
    "community_id": 123,
    "platform": "twitch",
    "platform_user_id": "user456",
    "warning_reason": "Inappropriate language",
    "warning_type": "manual",
    "issued_at": "2025-02-05T10:30:15Z",
    "issued_by": 789,
    "status": "active",
    "expires_at": "2025-03-07T10:30:15Z"
  }
}
```

#### Revoke Warning
```
DELETE /api/v1/security/<community_id>/warnings/<warning_id>
```

Revoke/remove a warning.

**Request**:
```json
{
  "revoked_by": 789,
  "revoke_reason": "False positive - user was defending themselves"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Warning revoked",
  "warning_id": 456
}
```

### Content Filtering

#### View Filter Match Log
```
GET /api/v1/security/<community_id>/filter-matches
```

View messages that matched content filters.

**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `limit` (optional): Results per page (default: 50)

**Response** (200 OK):
```json
{
  "success": true,
  "matches": [
    {
      "id": 789,
      "community_id": 123,
      "platform": "discord",
      "platform_user_id": "user789",
      "matched_pattern": "bad_word",
      "message": "[REDACTED]",
      "action_taken": "delete",
      "matched_at": "2025-02-05T10:30:15Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 156
  }
}
```

#### Add Blocked Words
```
POST /api/v1/security/<community_id>/blocked-words
```

Add words to the community's blocked word list.

**Request**:
```json
{
  "words": ["spam1", "spam2", "abusive"]
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Added 3 words to blocked list",
  "total_blocked_words": 42
}
```

#### Remove Blocked Words
```
DELETE /api/v1/security/<community_id>/blocked-words
```

Remove words from the community's blocked word list.

**Request**:
```json
{
  "words": ["spam1"]
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Removed 1 word from blocked list",
  "total_blocked_words": 41
}
```

### Moderation Logging

#### View Moderation Log
```
GET /api/v1/security/<community_id>/moderation-log
```

View all moderation actions taken in a community.

**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `limit` (optional): Results per page (default: 50)

**Response** (200 OK):
```json
{
  "success": true,
  "actions": [
    {
      "id": 111,
      "community_id": 123,
      "action_type": "warning",
      "action_reason": "Spam detected",
      "platform": "twitch",
      "platform_user_id": "user456",
      "moderator_id": 789,
      "taken_at": "2025-02-05T10:30:15Z",
      "synced_to_platforms": ["discord", "slack"]
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 523
  }
}
```

## Internal Service-to-Service Endpoints

### Real-Time Message Check
```
POST /api/v1/internal/check
```

Check message against spam and content filters (real-time).

**Request**:
```json
{
  "community_id": 123,
  "platform": "twitch",
  "platform_user_id": "user456",
  "message": "This is a test message",
  "metadata": {}
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "allowed": true
}
```

Or if blocked:
```json
{
  "success": true,
  "allowed": false,
  "blocked_reason": "content_filtered",
  "matched_pattern": "bad_word",
  "action_taken": "delete"
}
```

### Issue Automated Warning
```
POST /api/v1/internal/warn
```

Issue an automated warning (via spam detection, filter hits, etc.).

**Request**:
```json
{
  "community_id": 123,
  "platform": "twitch",
  "platform_user_id": "user456",
  "warning_type": "spam",
  "warning_reason": "Multiple spam messages detected",
  "trigger_message": "spam spam spam"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "warning": {
    "id": 456,
    "status": "active",
    "expires_at": "2025-03-07T10:30:15Z"
  }
}
```

### Sync Moderation Action
```
POST /api/v1/internal/sync-action
```

Sync a moderation action across multiple platforms.

**Request**:
```json
{
  "community_id": 123,
  "platform": "twitch",
  "platform_user_id": "user456",
  "action_type": "mute",
  "action_reason": "Spam",
  "moderator_id": 789,
  "sync_to_platforms": ["discord", "slack"]
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "synced_platforms": ["discord", "slack"],
  "failed_platforms": []
}
```

## Database Schema

### security_policies
Per-community security configuration.

```sql
id (Integer, Primary Key)
community_id (Integer, Unique)
max_warnings (Integer)
warning_expiry_days (Integer)
auto_ban_on_warnings (Boolean)
spam_detection_enabled (Boolean)
spam_threshold (Float)
content_filter_enabled (Boolean)
created_at (Timestamp)
updated_at (Timestamp)
```

### content_filters
Blocked word lists per community.

```sql
id (Integer, Primary Key)
community_id (Integer)
word (String)
is_regex (Boolean)
created_at (Timestamp)
created_by (Integer)
```

### filter_matches
Content filter match log.

```sql
id (Integer, Primary Key)
community_id (Integer)
platform (String)
platform_user_id (String)
matched_pattern (String)
message_hash (String)
action_taken (String)
matched_at (Timestamp)
```

### warnings
User warning records.

```sql
id (Integer, Primary Key)
community_id (Integer)
platform (String)
platform_user_id (String)
warning_reason (String)
warning_type (String)               # manual, automatic, spam, filter
issued_at (Timestamp)
issued_by (Integer)                 # Hub user ID of moderator
status (String)                     # active, expired, revoked
expires_at (Timestamp)
revoked_at (Timestamp)
revoked_by (Integer)
revoke_reason (String)
created_at (Timestamp)
updated_at (Timestamp)
```

### moderation_log
Complete audit trail of moderation actions.

```sql
id (Integer, Primary Key)
community_id (Integer)
action_type (String)                # warning, mute, ban, delete, etc.
action_reason (String)
platform (String)
platform_user_id (String)
moderator_id (Integer)              # Hub user ID
taken_at (Timestamp)
synced_to_platforms (Array)        # List of platforms synced to
created_at (Timestamp)
```

## Spam Detection Algorithm

The spam detector analyzes:
- Message frequency per user
- Character repetition (e.g., "aaaaaa")
- Word repetition (e.g., "spam spam spam")
- Capitalization patterns
- Special character patterns

**Default Threshold**: 0.7 (70% confidence = spam)

Each factor contributes a weighted score:
- Frequency anomaly: 30%
- Repetition patterns: 40%
- Caps/special chars: 20%
- URL/link content: 10%

## Logging

All security operations logged with:
- Timestamp
- Log level (INFO, WARNING, ERROR)
- Module: security_core
- Community ID
- Action details

Example:
```
2025-02-05 10:30:15 [security_core] INFO: Warning issued: community=123, user=user456, reason=spam
2025-02-05 10:31:20 [security_core] WARNING: High filter match rate: community=123, matches=15/min
```

## Related Documentation

- [Core Identity Service README](../README.md) - Combined service overview
- [Database Schema](../../docs/architecture/database-schema.md)
- [Moderation Policies](../../docs/SECURITY.md)
