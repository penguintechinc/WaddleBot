# Memories Interaction Module - Architecture

## System Design

The Memories Interaction Module follows a clean layered architecture with clear separation of concerns:

```
+-------------------------------------------+
|       REST API Layer (Quart)              |
|  - Request validation (Pydantic)          |
|  - Response formatting                    |
|  - Health/metrics endpoints               |
+----+---------------------------------------+
     |
+----v---------------------------------------+
|       Service Layer                       |
|  - QuoteService                           |
|  - BookmarkService                        |
|  - ReminderService                        |
|  - Business logic                         |
|  - Async operations                       |
+----+---------------------------------------+
     |
+----v---------------------------------------+
|    Data Access Layer (PyDAL)              |
|  - SQL query execution                    |
|  - Connection pooling                     |
|  - Transaction management                 |
+----+---------------------------------------+
     |
+----v---------------------------------------+
|    PostgreSQL Database                    |
|  - Schema definitions                     |
|  - Full-text search indexes               |
|  - Constraints & triggers                 |
+-------------------------------------------+
```

## Request Flow

### Typical Request Lifecycle

1. HTTP Request arrives - Quart receives POST/GET/DELETE request
2. Route matching - Flask/Quart routes to appropriate handler
3. Validation - Pydantic model validates and sanitizes input
4. Service execution - Service method processes request
5. Database queries - PyDAL executes parameterized SQL
6. Response formatting - Success/error response wrapper
7. HTTP Response - JSON returned to client

### Example: Create Quote Request

```
Client POST /api/v1/memories/quotes
    |
    v
app.py::add_quote() handler
    |
    +- @validate_json(QuoteCreateRequest)
    |  | Check required fields
    |  | Validate constraints
    |  | Sanitize input
    |
    v
QuoteService.add_quote()
    |
    +- Validate quote_text not empty
    +- SQL INSERT INTO memories_quotes
    |  (with parameterized query)
    |
    v
Database: RETURNING id
    |
    v
Format response with quote_id
    |
    v
HTTP 200 JSON response
```

## Component Architecture

### app.py - REST API Layer (520 lines)

Responsibilities:
- Define all REST endpoints
- Request routing via Flask/Quart blueprints
- Validate incoming requests with Pydantic
- Format responses (success/error wrappers)
- Log audit events
- Handle authentication/authorization

Key sections:
- Health endpoints: /health, /metrics
- Quote endpoints: 7 endpoints (create, search, random, get, delete, vote, stats)
- Bookmark endpoints: 8 endpoints (create, search, get, delete, popular, tags, stats)
- Reminder endpoints: 6 endpoints (create, pending, mark-sent, user-reminders, cancel, stats)

### Service Layer

#### QuoteService (quote_service.py)

```python
class QuoteService:
    async def add_quote(...)           # Create quote
    async def get_quote(...)           # Get by ID or random
    async def search_quotes(...)       # Full-text search with filters
    async def delete_quote(...)        # Delete with authorization check
    async def vote_quote(...)          # Upvote/downvote with aggregation
    async def get_categories(...)      # List all categories
    async def get_stats(...)           # Aggregate statistics
```

Features:
- Full-text search with ranking (PostgreSQL ts_rank())
- Category and author filtering
- Voting system with conflict resolution
- Vote count aggregation (upvotes - downvotes)
- Statistics with aggregate functions

#### BookmarkService (bookmark_service.py)

```python
class BookmarkService:
    async def add_bookmark(...)        # Create bookmark
    async def get_bookmark(...)        # Get by ID
    async def search_bookmarks(...)    # Full-text search
    async def delete_bookmark(...)     # Delete with auth check
    async def increment_visits(...)    # Track accesses
    async def get_popular_bookmarks()  # Order by visits DESC
    async def get_all_tags(...)        # Extract unique tags
    async def get_stats(...)           # Statistics
    async def _fetch_url_metadata(...) # Async HTTP metadata fetch
```

Features:
- Async HTTP client for URL metadata extraction (aiohttp)
- HTML parsing with BeautifulSoup4
- Tag-based filtering with PostgreSQL array operators
- Visit count tracking and ranking
- Popular bookmarks sorted by engagement

#### ReminderService (reminder_service.py)

```python
class ReminderService:
    async def create_reminder(...)       # Create one-time or recurring
    async def get_pending_reminders(...) # Query due reminders
    async def mark_reminder_sent(...)    # Mark sent, schedule next
    async def get_user_reminders(...)    # User-scoped query
    async def cancel_reminder(...)       # Soft-delete (is_active=False)
    async def parse_relative_time(...)   # Parse "5m", "2h", "1d", "3w"
    async def get_stats(...)             # Pending/sent/recurring metrics
```

Features:
- RFC 5545 RRULE parsing (via python-dateutil)
- Relative time parsing (minutes, hours, days, weeks)
- ISO 8601 timestamp support
- Automatic next occurrence scheduling
- Pending reminder queries for background processors
- UTC timezone handling

### validation_models.py - Input Validation

Pydantic models for request validation:

Quote Models:
- QuoteCreateRequest - Creation with required/optional fields
- QuoteSearchParams - Search query parameters
- QuoteVoteRequest - Vote requests
- QuoteDeleteRequest - Deletion requests

Bookmark Models:
- BookmarkCreateRequest - URL validation with sanitization
- BookmarkSearchParams - Search with tag filtering
- BookmarkDeleteRequest
- PopularBookmarksParams

Reminder Models:
- ReminderCreateRequest - Time format validation
- ReminderSearchParams
- ReminderMarkSentRequest
- ReminderDeleteRequest
- UserRemindersParams

Validation features:
- Field length constraints
- URL sanitization (prevent XSS)
- Regex patterns (vote_type, channel)
- RRULE format validation
- Relative time format validation
- Array/list validation for tags

### config.py - Configuration

```python
class Config:
    MODULE_NAME = 'memories_interaction_module'
    MODULE_VERSION = '2.0.0'
    MODULE_PORT = 8031
    DATABASE_URL = '...'  # from env
    CORE_API_URL = '...'
    ROUTER_API_URL = '...'
    LOG_LEVEL = 'INFO'
    SECRET_KEY = '...'
    REDIS_URL = '...'     # optional
```

Features:
- Environment variable management via python-dotenv
- Credential loading from database table
- Redis listener for credential refresh notifications
- Thread-safe credential state management

## Data Model

### Quotes Table

Table definition with search indexing:
- id (PRIMARY KEY)
- community_id (indexed)
- quote_text (indexed via search_vector)
- author_username, author_user_id
- created_by_username, created_by_user_id
- category (indexed)
- votes (aggregate from quote_votes)
- search_vector (GIN indexed for full-text)
- created_at, updated_at

### Quote Votes Table

Vote tracking for aggregation:
- id (PRIMARY KEY)
- quote_id (foreign key)
- user_id (unique constraint with quote_id)
- username, vote_type ('up' or 'down')
- created_at

### Bookmarks Table

URL bookmarks with tags and visit tracking:
- id (PRIMARY KEY)
- community_id (indexed)
- url (indexed)
- title, description
- tags (array, indexed via GIN)
- created_by_username, created_by_user_id
- visits (for ranking)
- search_vector (GIN indexed)
- created_at, updated_at

### Reminders Table

Reminder scheduling with RRULE support:
- id (PRIMARY KEY)
- community_id, user_id (indexed)
- username, reminder_text
- remind_at (indexed for pending queries)
- recurring_rule (RRULE format)
- channel, platform_channel_id
- is_sent, is_active (indexed together)
- sent_at, created_at

## Key Algorithms

### Full-Text Search (Quotes & Bookmarks)

PostgreSQL full-text search with ranking using GIN indexes and
plainto_tsquery for tokenization. Ranked by relevance, ordered by date.

### Vote Aggregation

Count upvotes vs downvotes using FILTER clause, compute net score.
Conflict resolution handles user changing vote (on conflict update).

### Recurring Reminder Scheduling

Parse RFC 5545 RRULE via dateutil.rrule, compute next occurrence
using rule.after(datetime.utcnow()), create new reminder record.

## External Dependencies

### Core Dependencies
- Quart (0.19+): Async ASGI web framework
- Hypercorn (0.16+): ASGI server
- Pydantic (2.0+): Data validation
- PyDAL: Database abstraction layer
- python-dateutil: RFC 5545 RRULE parsing
- aiohttp (3.10+): Async HTTP client
- BeautifulSoup4 (4.13+): HTML parsing for bookmark metadata

### Data Layer
- PostgreSQL 12+: Primary database
- psycopg2: PostgreSQL adapter
- Redis (optional): Credential refresh notifications

### Utilities
- python-dotenv: Environment configuration
- bleach: HTML sanitization
- pytz: Timezone handling

## Performance Characteristics

Query Performance:
- Full-text search: O(log n) with GIN index, <100ms
- Quote by ID: O(1) with PK, <10ms
- Vote aggregation: O(m) on quote, <20ms
- Popular bookmarks: O(n log n) with visits index, <50ms
- Pending reminders: O(n) with composite index, <30ms

Connection Pooling:
- Default pool: 5-10 connections
- Timeout: 30 seconds
- Auto-reconnect on exhaustion

Caching:
- No in-memory caching (stateless)
- Database indexes for fast retrieval
- PostgreSQL query planner optimization

## Security Measures

### Input Validation
- Pydantic models with constraints
- Field length limits
- URL sanitization (prevent XSS)
- Whitelist patterns for channels/vote types

### Authorization
- Creator-only deletion checks
- User ID verification before operations
- Soft-delete for reminders (preserve history)

### SQL Injection Prevention
- Parameterized statements (no string interpolation)
- Type validation before queries

### Audit Logging
- Action logging via flask_core
- User tracking for modifications
- Timestamp recording

---

Last Updated: February 16, 2026
Module Version: 2.0.0
