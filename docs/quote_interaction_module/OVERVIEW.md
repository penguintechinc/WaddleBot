# Quote Interaction Module - Overview

## Purpose

The Quote Interaction Module is a community engagement service that manages memorable quotes and sayings within WaddleBot communities. It provides full-text search, pagination, author filtering, and quote moderation capabilities backed by PostgreSQL full-text search indexes.

**Primary Use Cases:**
- Community members can submit quotes for archiving
- Communities can discover random quotes for entertainment
- Full-text search enables finding quotes by keywords
- Quote authors can be tracked and searched independently
- Moderation workflows support quote approval before publication
- Statistics track quote engagement per community

## Key Capabilities

| Feature | Description |
|---------|-------------|
| **Full-Text Search** | PostgreSQL tsvector-based search using plainto_tsquery for natural language queries |
| **Author Filtering** | ILIKE pattern matching to find quotes by specific community members |
| **Random Quote** | Retrieve random approved quotes for community engagement |
| **Pagination** | Configurable limit/offset for efficient large result sets |
| **Soft-Delete** | Quotes are marked deleted (deleted_at) rather than hard-deleted for audit trails |
| **Quote Moderation** | Auto-approval or manual review workflow configurable |
| **Statistics** | Community quote counts, approval status breakdown, unique authors |
| **Multi-Platform** | Track quote origins (Twitch, Discord, etc.) |
| **Contextual Tags** | Support for categorizing quotes with custom tags |

## Module Information

**Language:** Python 3.13+  
**Framework:** Quart (async Python web framework)  
**Database:** PostgreSQL 14+  
**Default Port:** 5012  
**Health Check:** GET `/health`  
**Version:** 1.0.0  

## Technology Stack

- **Web Framework:** Quart (async-ready)
- **Database Driver:** AsyncDAL (async wrapper around PyDAL)
- **Search:** PostgreSQL full-text search (tsvector/plainto_tsquery)
- **Async Runtime:** asyncio via Hypercorn
- **Logging:** Python logging with AAA format

## Quick Reference

### Module Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/quotes` | Create a new quote |
| GET | `/api/v1/quotes/<id>` | Fetch quote by ID |
| GET | `/api/v1/quotes/random/<community_id>` | Get random approved quote |
| GET | `/api/v1/quotes/list/<community_id>` | List paginated quotes |
| GET | `/api/v1/quotes/search/<community_id>` | Full-text search quotes |
| GET | `/api/v1/quotes/author/<community_id>` | Filter quotes by author |
| PUT | `/api/v1/quotes/<id>` | Update quote details |
| DELETE | `/api/v1/quotes/<id>` | Soft-delete quote |
| GET | `/api/v1/quotes/stats/<community_id>` | Get community quote statistics |
| GET | `/health` | Health/readiness check |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/v1/status` | Module status |

### Database Table

**Table Name:** `quotes`  
**Migration:** 015 (quotes table with PostgreSQL full-text search tsvector)

**Key Columns:**
- `id` (SERIAL PRIMARY KEY)
- `community_id` (INTEGER NOT NULL)
- `quote_text` (TEXT NOT NULL)
- `quoted_user_id` (INTEGER)
- `quoted_username` (VARCHAR(255))
- `added_by_user_id` (INTEGER)
- `platform` (VARCHAR(50))
- `context` (TEXT)
- `tags` (ARRAY[TEXT])
- `is_approved` (BOOLEAN DEFAULT TRUE)
- `search_vector` (TSVECTOR - generated from quote_text)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- `deleted_at` (TIMESTAMP - NULL means active)

## Documentation Index

| Document | Purpose |
|----------|---------|
| **OVERVIEW.md** | Module purpose, capabilities, quick reference (this file) |
| **[USAGE.md](USAGE.md)** | Getting started, Docker setup, health checks, common workflows |
| **[API.md](API.md)** | Complete endpoint documentation with request/response examples |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Components, data flow, service design, dependencies |
| **[CONFIGURATION.md](CONFIGURATION.md)** | Environment variables, database setup, configuration options |
| **[TESTING.md](TESTING.md)** | Test strategy, mock data, test execution procedures |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Common errors, debugging steps, log interpretation |
| **[RELEASE_NOTES.md](RELEASE_NOTES.md)** | Version history and release information |

## Configuration Summary

**Critical Environment Variables:**
- `QUOTE_MODULE_PORT` - Service port (default: 5012)
- `DATABASE_URL` - PostgreSQL connection string
- `QUOTE_MODULE_NAME` - Module identifier (default: quote_interaction_module)
- `AUTO_APPROVE_QUOTES` - Enable auto-approval (default: true)

**Optional:**
- `READ_REPLICA_URL` - Read-only database replica for queries
- `REDIS_URL` - Redis connection for credential refresh notifications
- `DB_POOL_SIZE` - Connection pool size (default: 10)
- `API_TIMEOUT` - Request timeout in seconds (default: 30)
- `MAX_PAGE_SIZE` - Maximum pagination limit (default: 100)
- `DEFAULT_PAGE_SIZE` - Default page size (default: 50)

## Service Dependencies

- **PostgreSQL 14+** - Quote storage and full-text search
- **Flask-Core Library** - AAA logging, database initialization
- **AsyncDAL** - Async database abstraction layer
- **Hypercorn** - ASGI application server

## File Structure

```
action/interactive/quote_interaction_module/
├── __init__.py                 # Module initialization
├── app.py                      # Quart application & endpoints
├── config.py                   # Configuration management
├── services/
│   ├── __init__.py
│   └── quote_service.py       # Quote business logic
└── test-api.sh                # Manual API testing script
```

## Quick Start

```bash
# Set environment variables
export QUOTE_MODULE_PORT=5012
export DATABASE_URL="postgresql://user:pass@localhost:5432/waddlebot"

# Start the module
python -m action.interactive.quote_interaction_module.app

# Test health endpoint
curl http://localhost:5012/health

# Add a quote
curl -X POST http://localhost:5012/api/v1/quotes \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "text": "To quote myself, I say this",
    "author": "Albert Einstein",
    "added_by_user_id": 123
  }'

# Search quotes
curl "http://localhost:5012/api/v1/quotes/search/1?q=Einstein"
```

## Performance Characteristics

- **Full-Text Search:** O(log n) with PostgreSQL tsvector index
- **Random Quote:** O(1) using RANDOM() with index on is_approved
- **Author Search:** O(n) with ILIKE pattern matching (case-insensitive)
- **Pagination:** O(k) where k = limit + offset
- **Connection Pool:** 10 concurrent database connections (configurable)

## Security Considerations

- Input validation on all query parameters
- SQL injection prevention via parameterized queries (AsyncDAL)
- Soft-delete audit trail (deleted_at timestamp)
- Community isolation: quotes are always scoped to community_id
- User context tracked (added_by_user_id, quoted_user_id)

## Integration Points

- **WaddleBot Core:** Community management API for community_id resolution
- **Platform Integrations:** Credentials from platform_integrations table
- **Redis (Optional):** Credential refresh notification channel
- **Metrics:** Prometheus-compatible health endpoint

## Next Steps

1. **Get Started:** See [USAGE.md](USAGE.md) for local development setup
2. **API Reference:** See [API.md](API.md) for complete endpoint documentation
3. **Architecture:** See [ARCHITECTURE.md](ARCHITECTURE.md) for system design details
4. **Configuration:** See [CONFIGURATION.md](CONFIGURATION.md) for environment setup
5. **Testing:** See [TESTING.md](TESTING.md) for test procedures
