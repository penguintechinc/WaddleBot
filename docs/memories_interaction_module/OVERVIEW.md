# Memories Interaction Module - Overview

## Module Purpose

The Memories Interaction Module is a Quart-based Python service that manages community memories across three core memory types: **Quotes**, **Bookmarks**, and **Reminders**. It provides a comprehensive REST API for communities to capture, organize, and retrieve important moments and information shared within their platforms.

**Module Name**: `memories_interaction_module`  
**Language**: Python 3.12  
**Framework**: Quart + Hypercorn  
**Database**: PostgreSQL (via PyDAL)  
**Version**: 2.0.0  
**Port**: 8031  

## Key Capabilities

### Quotes Management
- **Create & Store Quotes**: Capture memorable quotes with author attribution
- **Full-Text Search**: Search quotes by text content with ranking
- **Category Filtering**: Organize quotes by custom categories
- **Voting System**: Community voting with upvote/downvote functionality
- **Random Selection**: Retrieve random quotes from community
- **Statistics**: Track quote metrics (total, unique authors, categories, average votes)

### Bookmarks Management
- **URL Bookmarking**: Save and share important URLs with metadata
- **Auto-Fetch Metadata**: Automatically extract title and description from URLs
- **Tag Organization**: Categorize bookmarks with flexible tagging
- **Full-Text Search**: Search bookmarks by URL, title, and description
- **Visit Tracking**: Count and track bookmark access patterns
- **Popular Bookmarks**: Query most-visited bookmarks
- **Statistics**: Track bookmark metrics (total, contributors, total visits)

### Reminders Management
- **One-Time Reminders**: Schedule reminders for specific times
- **Recurring Reminders**: Support RRULE format for repeating reminders (FREQ=DAILY, etc.)
- **Channel-Specific**: Route reminders to specific platforms (Twitch, Discord, Slack, Kick)
- **Relative Time Parsing**: Support flexible time formats (5m, 2h, 1d, 3w)
- **ISO Timestamps**: Accept standard ISO 8601 timestamps
- **Pending Query**: API for reminder processors to fetch due reminders
- **Automatic Scheduling**: Auto-schedule next occurrence for recurring reminders
- **Statistics**: Track reminder metrics (pending, sent, recurring, unique users)

## Quick Reference Table

| Feature | Quotes | Bookmarks | Reminders |
|---------|--------|-----------|-----------|
| Create/Store | ✓ | ✓ | ✓ |
| Full-Text Search | ✓ | ✓ | - |
| Filtering | Category, Author | Tags, Creator | User, Community |
| Voting/Ranking | ✓ (votes) | - (visits) | - |
| Auto-Metadata | - | ✓ | - |
| Statistics | ✓ | ✓ | ✓ |
| Deletion | ✓ | ✓ | ✓ (cancel) |

## Architecture Overview

The module follows a clean layered architecture with clear separation of concerns:

```
REST API Layer (app.py)
    ↓
Service Layer (services/)
    ├── quote_service.py
    ├── bookmark_service.py
    └── reminder_service.py
    ↓
Data Access Layer (PyDAL)
    ↓
PostgreSQL Database
```

### Core Components

**app.py** (520 lines)
- Quart application with async endpoints
- Request validation with Pydantic models
- Response formatting (success/error)
- Health and metrics endpoints
- 21 total API endpoints across three feature areas

**Services Layer**
- `quote_service.py`: Quote CRUD, search, voting, statistics
- `bookmark_service.py`: Bookmark CRUD, URL metadata fetching, tag management
- `reminder_service.py`: Reminder scheduling, RRULE handling, pending queries

**Validation Models** (validation_models.py)
- Pydantic models for all request types
- Input validation and sanitization
- Field constraints and error messages

**Configuration** (config.py)
- Environment variable management
- Database connection settings
- Credential loading from platform_integrations table
- Redis listener for credential refresh events

## Database Schema

The module uses three main tables:

**memories_quotes**
- id, community_id, quote_text, author_username, author_user_id
- created_by_username, created_by_user_id, category, votes
- search_vector (for full-text search)
- created_at, updated_at

**memories_bookmarks**
- id, community_id, url, title, description, tags (array)
- created_by_username, created_by_user_id, visits
- search_vector (for full-text search)
- created_at, updated_at

**memories_reminders**
- id, community_id, user_id, username, reminder_text
- remind_at, recurring_rule, channel, platform_channel_id
- is_sent, is_active, sent_at
- created_at

**memories_quote_votes**
- id, quote_id, user_id, username, vote_type (up/down)
- created_at

## Security Features

- **Authentication**: Required for deletion, mark-sent operations
- **Authorization**: Users can only delete/modify their own content
- **Input Validation**: Pydantic validation for all inputs
- **URL Sanitization**: Safe URL validation for bookmarks
- **Audit Logging**: Action logging via flask_core
- **SQL Parameterization**: Prevents SQL injection

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Quart | 0.19+ |
| Server | Hypercorn | 0.16+ |
| Validation | Pydantic | 2.0+ |
| Database | PostgreSQL | 12+ |
| HTML Parsing | BeautifulSoup4 | 4.13+ |
| Async HTTP | aiohttp | 3.10+ |
| Date Utilities | python-dateutil | 2.8.2+ |
| Testing | pytest | 7.4+ |

## API Endpoints Overview

### Quotes (7 endpoints)
- `POST /quotes` - Create new quote
- `GET /quotes/<community_id>` - Search quotes with full-text search
- `GET /quotes/<community_id>/random` - Get random quote
- `GET /quotes/<community_id>/<quote_id>` - Get specific quote
- `DELETE /quotes/<community_id>/<quote_id>` - Delete quote (creator only)
- `POST /quotes/<community_id>/<quote_id>/vote` - Vote on quote
- `GET /quotes/<community_id>/stats` - Get community quote statistics

### Bookmarks (8 endpoints)
- `POST /bookmarks` - Create new bookmark
- `GET /bookmarks/<community_id>` - Search bookmarks
- `GET /bookmarks/<community_id>/<bookmark_id>` - Get bookmark
- `DELETE /bookmarks/<community_id>/<bookmark_id>` - Delete bookmark (creator only)
- `GET /bookmarks/<community_id>/popular` - Get most-visited bookmarks
- `GET /bookmarks/<community_id>/tags` - List all tags
- `GET /bookmarks/<community_id>/stats` - Get community bookmark statistics

### Reminders (6 endpoints)
- `POST /reminders` - Create reminder
- `GET /reminders/pending` - Get pending reminders (for processor)
- `POST /reminders/<reminder_id>/sent` - Mark reminder as sent
- `GET /reminders/<community_id>/user/<user_id>` - Get user reminders
- `DELETE /reminders/<community_id>/<reminder_id>` - Cancel reminder
- `GET /reminders/<community_id>/stats` - Get community reminder statistics

## Related Documentation

- **[USAGE.md](USAGE.md)** - Getting started, Docker deployment, health checks
- **[API.md](API.md)** - Complete endpoint reference with examples
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed system design and data flow
- **[CONFIGURATION.md](CONFIGURATION.md)** - Environment variables and setup
- **[TESTING.md](TESTING.md)** - Test strategy and sample data
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common errors and solutions
- **[RELEASE_NOTES.md](RELEASE_NOTES.md)** - Version history

## Quick Start

### 1. Start with Docker

```bash
docker run -d \
  -e DATABASE_URL="postgresql://user:pass@host:5432/waddlebot" \
  -e MODULE_PORT=8031 \
  -p 8031:8031 \
  waddlebot/memories-interaction:latest
```

### 2. Health Check

```bash
curl http://localhost:8031/health
```

### 3. Create a Quote

```bash
curl -X POST http://localhost:8031/api/v1/memories/quotes \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 123,
    "quote_text": "Remember to be awesome!",
    "created_by_username": "alice",
    "created_by_user_id": 1,
    "category": "motivational"
  }'
```

### 4. Search Quotes

```bash
curl http://localhost:8031/api/v1/memories/quotes/123?q=awesome
```

## Real-World Use Cases

### Community Memory Bank
Enable communities to build searchable databases of memorable quotes from members, creating a cultural library of shared values and humor.

### Knowledge Repository
Store and categorize important resource links with automatic metadata extraction, creating a collaborative knowledge base.

### Community Notifications
Schedule reminders for community events, announcements, and recurring activities with platform-specific delivery (Twitch, Discord, etc.).

### Engagement Features
Use quotes and bookmarks to drive engagement through trending content, popular links, and community voting.

## Support & Documentation

- **Source Code**: `/home/penguin/code/waddlebot/action/interactive/memories_interaction_module/`
- **Tests**: `/home/penguin/code/waddlebot/action/interactive/memories_interaction_module/test-api.sh`
- **Configuration**: Environment variables in `config.py`
- **Docker Image**: `waddlebot/memories-interaction:latest`

## Performance & Scalability

- Stateless design allows horizontal scaling
- PostgreSQL connection pooling for efficient database access
- Full-text search indexes for fast quote and bookmark retrieval
- Visit count aggregation for popular bookmarks ranking
- RRULE-based reminder scheduling without cron jobs

---

**Last Updated**: February 16, 2026  
**Module Version**: 2.0.0  
**Maintained By**: WaddleBot Development Team
