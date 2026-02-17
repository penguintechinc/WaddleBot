# Engagement Module — Architecture

## System Overview

The Engagement Module is a microservice for community engagement through polls and forms. It provides a REST API fronted by Quart (async Python framework), backed by PyDAL ORM for database abstraction, and JWT for authentication.

```
┌─────────────────────────────────────────────────────┐
│          REST API Layer (Quart)                     │
│  ┌──────────────────────────────────────────────┐   │
│  │ Health Check  │  Polls API  │  Forms API     │   │
│  └──────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────────────────────────────────────┐
│     Authentication & Authorization Layer          │
│  ┌──────────────────────────────────────────────┐  │
│  │  JWT Token Validation   │ Visibility Engine │  │
│  └──────────────────────────────────────────────┘  │
└────────────────┬───────────────────────────────────┘
                 │
┌────────────────────────────────────────────────────┐
│       Business Logic Layer                        │
│  ┌─────────────────────────────────────────────┐  │
│  │ Poll Manager    │  Form Manager             │  │
│  │ Vote Tracker    │  Submission Handler       │  │
│  │ Results Engine  │  Validation Logic         │  │
│  └─────────────────────────────────────────────┘  │
└────────────────┬───────────────────────────────────┘
                 │
┌────────────────────────────────────────────────────┐
│        Data Access Layer (PyDAL ORM)              │
│  ┌─────────────────────────────────────────────┐  │
│  │  Table Definitions  │  Query Builders      │  │
│  │  Connection Pool    │  Transaction Manager │  │
│  └─────────────────────────────────────────────┘  │
└────────────────┬───────────────────────────────────┘
                 │
┌────────────────────────────────────────────────────┐
│         PostgreSQL Database                       │
│  ┌─────────────────────────────────────────────┐  │
│  │ Polls Schema    │  Forms Schema             │  │
│  │ Votes Table     │  Submissions Table        │  │
│  └─────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. REST API Layer (Quart)

**Framework**: Quart (async Python web framework)

**Key Features**:
- Asynchronous request handling for high concurrency
- Built-in JSON serialization
- Decorator-based routing
- Request/response context management

**Endpoints**:
```
GET    /health                          # Health check
POST   /api/v1/polls                    # Create poll
GET    /api/v1/polls/:poll_id           # Get poll
GET    /api/v1/polls/community/:id      # List polls
POST   /api/v1/polls/:poll_id/vote      # Vote

POST   /api/v1/forms                    # Create form
GET    /api/v1/forms/:form_id           # Get form
GET    /api/v1/forms/community/:id      # List forms
POST   /api/v1/forms/:form_id/submit    # Submit form
GET    /api/v1/forms/:form_id/submissions # Get submissions
```

### 2. Authentication & Authorization

**JWT Token Validation**:
- Tokens expected in `Authorization: Bearer <token>` header
- Validation via `verify_jwt_token()` function
- Supports configurable JWT secret and algorithm
- Automatic token expiration checking

**Visibility Control**:
- Four-tier visibility model (public, registered, community, admins)
- Separate view vs submit permissions
- `check_visibility()` function enforces access control
- IP hashing for anonymous tracking

### 3. Business Logic Layer

#### Poll Management

**State Machine**:
```
Create → Active (voting allowed) → Expired (closed)
          ├─ If expires_at < now: voting rejected
          └─ If is_active = false: not displayed
```

**Vote Tracking**:
- Per-user vote prevention (one vote per user per poll)
- Support for single-choice and multi-choice polls
- Option ID validation before recording vote
- Automatic vote count aggregation

**Vote Recording**:
```python
# Only if:
# 1. Poll exists and is active
# 2. Poll not expired
# 3. User hasn't voted yet
# 4. Option count doesn't exceed max_choices
# 5. User has submit_visibility access

db.poll_votes.insert(poll_id, option_id, user_id)
```

#### Form Management

**Field Types**:
- Text, Textarea: String values
- Email: Email format validation
- Number: Numeric value validation
- Select, Radio, Checkbox: Option selection with options array
- Date: ISO 8601 date strings

**Field Validation**:
```python
validation_json = {
    "min": 5,          # Minimum length/value
    "max": 100,        # Maximum length/value
    "pattern": "^...$" # Regex pattern
}
```

**Submission Constraints**:
- One submission per user enforcement (if enabled)
- Anonymous submission support (user_id = NULL)
- IP-based tracking for anonymous users
- Field-level value storage (text or JSON)

### 4. Data Access Layer (PyDAL)

**Database Abstraction**:
- PyDAL provides database agnosticism
- Automatic SQL generation from Python code
- Connection pooling with configurable pool size
- Transaction management with commit/rollback

**Table Definitions**:

```
community_polls
├── id (primary key)
├── community_id (integer)
├── created_by (integer)
├── title (string, 255)
├── description (text)
├── view_visibility (string)
├── submit_visibility (string)
├── allow_multiple_choices (boolean)
├── max_choices (integer)
├── expires_at (datetime)
├── is_active (boolean)
├── created_at (datetime)
└── updated_at (datetime)

poll_options
├── id (primary key)
├── poll_id (foreign key)
├── option_text (string, 500)
├── sort_order (integer)
└── created_at (datetime)

poll_votes
├── id (primary key)
├── poll_id (foreign key)
├── option_id (foreign key)
├── user_id (integer)
├── ip_hash (string, 64)
└── voted_at (datetime)

community_forms
├── id (primary key)
├── community_id (integer)
├── created_by (integer)
├── title (string, 255)
├── description (text)
├── view_visibility (string)
├── submit_visibility (string)
├── allow_anonymous (boolean)
├── submit_once_per_user (boolean)
├── is_active (boolean)
├── created_at (datetime)
└── updated_at (datetime)

form_fields
├── id (primary key)
├── form_id (foreign key)
├── field_type (string, 50)
├── label (string, 255)
├── placeholder (string, 255)
├── is_required (boolean)
├── options_json (json)
├── validation_json (json)
├── sort_order (integer)
└── created_at (datetime)

form_submissions
├── id (primary key)
├── form_id (foreign key)
├── user_id (integer)
├── ip_hash (string, 64)
└── submitted_at (datetime)

form_field_values
├── id (primary key)
├── submission_id (foreign key)
├── field_id (foreign key)
├── value_text (text)
├── value_json (json)
└── created_at (datetime)
```

---

## Data Flow

### Poll Creation Flow

```
POST /api/v1/polls
  │
  ├─ 1. Validate JWT token
  │
  ├─ 2. Validate request body
  │     ├─ community_id required
  │     ├─ title required (1-255 chars)
  │     └─ options required (min 2)
  │
  ├─ 3. Insert poll record
  │     └─ db.community_polls.insert()
  │
  ├─ 4. Insert poll options (sorted)
  │     └─ db.poll_options.insert() for each option
  │
  ├─ 5. Commit transaction
  │     └─ db.commit()
  │
  └─ Return poll object with options
```

### Vote Recording Flow

```
POST /api/v1/polls/:poll_id/vote
  │
  ├─ 1. Validate JWT token
  │
  ├─ 2. Fetch poll record
  │
  ├─ 3. Validate poll state
  │     ├─ Poll exists
  │     ├─ Poll is active
  │     ├─ Poll not expired
  │     └─ User has submit access
  │
  ├─ 4. Validate vote options
  │     ├─ Count within bounds
  │     ├─ Multiple choice allowed
  │     └─ Options exist
  │
  ├─ 5. Check for duplicate vote
  │     └─ Prevent re-voting
  │
  ├─ 6. Record vote(s)
  │     └─ db.poll_votes.insert() for each option
  │
  ├─ 7. Commit transaction
  │
  └─ Return success
```

### Form Submission Flow

```
POST /api/v1/forms/:form_id/submit
  │
  ├─ 1. Validate JWT token (unless anonymous allowed)
  │
  ├─ 2. Fetch form record
  │
  ├─ 3. Validate form state
  │     ├─ Form exists
  │     ├─ Form is active
  │     └─ User has submit access
  │
  ├─ 4. Check submission constraint
  │     └─ If submit_once_per_user: check existing submissions
  │
  ├─ 5. Hash IP address
  │     └─ hashlib.sha256() for privacy
  │
  ├─ 6. Create submission record
  │     └─ db.form_submissions.insert()
  │
  ├─ 7. Process field values
  │     ├─ Determine value type (text vs JSON)
  │     └─ Insert form_field_values records
  │
  ├─ 8. Commit transaction
  │
  └─ Return submission_id
```

---

## Integration Patterns

### With Reputation Module

The Engagement Module can emit events to the Reputation Module:
- Poll creation: +5 reputation points (optional)
- Poll voting: +1 reputation point
- Form submission: +2 reputation points

### With Analytics Module

Metrics exported to Analytics:
- Daily poll counts
- Daily form submissions
- Vote distribution per poll
- Field participation rates

### With Permission System

Leverages existing permission checks:
- Visibility levels enforced by check_visibility()
- Community membership verified via gRPC (future)
- Admin status checked before data retrieval

---

## Scalability Considerations

### Stateless Design

The module is completely stateless:
- All state in PostgreSQL
- No in-memory caches
- No session data
- Can run multiple instances behind load balancer

### Connection Pooling

```python
db = DAL(
    config.DATABASE_URL,
    pool_size=config.DB_POOL_SIZE,  # Default: 10
    migrate_enabled=True,
    fake_migrate_all=False
)
```

Increase `DB_POOL_SIZE` if seeing connection exhaustion errors.

### Async/Await

Quart uses async for concurrency:
```python
@app.route("/api/v1/polls", methods=["POST"])
async def create_poll():  # Async handler
    data = await request.get_json()  # Non-blocking JSON parse
    # ... process ...
```

### Indexing Strategy

Recommended database indexes for performance:

```sql
-- Polls queries
CREATE INDEX idx_polls_community ON community_polls(community_id);
CREATE INDEX idx_polls_active ON community_polls(is_active, created_at);

-- Votes queries
CREATE INDEX idx_votes_poll ON poll_votes(poll_id);
CREATE INDEX idx_votes_user_poll ON poll_votes(user_id, poll_id);

-- Forms queries
CREATE INDEX idx_forms_community ON community_forms(community_id);
CREATE INDEX idx_forms_active ON community_forms(is_active, created_at);

-- Submissions queries
CREATE INDEX idx_submissions_form ON form_submissions(form_id);
CREATE INDEX idx_submissions_user_form ON form_submissions(user_id, form_id);
```

---

## Security Considerations

### JWT Validation

All protected endpoints validate JWT:
```python
def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid signature or malformed
```

### SQL Injection Prevention

PyDAL parameterizes all queries:
```python
# Safe: Uses parameterized query
rows = db(db.poll_votes.poll_id == poll_id).select()
```

### IP Hash Privacy

IP addresses are hashed for anonymous tracking:
```python
def hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()  # One-way hash
```

### Visibility Enforcement

All list/get operations respect visibility:
```python
def check_visibility(visibility: str, user_id: Optional[int],
                    community_id: int, is_admin: bool) -> bool:
    if visibility == "public":
        return True
    if visibility == "registered":
        return user_id is not None
    if visibility == "community":
        return user_id is not None  # Would check community membership
    if visibility == "admins":
        return is_admin
    return False
```

---

## Error Handling

### Database Errors

Automatic transaction rollback on exception:
```python
try:
    db.poll_votes.insert(...)
    db.commit()
except Exception as e:
    logger.error(f"Vote failed: {e}")
    db.rollback()
    return jsonify({"error": str(e)}), 500
```

### Logging

All operations logged with context:
```
[2026-02-16 10:30:45,123] INFO engagement_module:vote:378 Vote recorded for poll 42
[2026-02-16 10:30:46,456] ERROR engagement_module:create_poll:328 Create poll failed: Invalid options
```

---

## Future Enhancements

1. **Real-time Updates**: WebSocket support for live vote counts
2. **Caching**: Redis caching for high-traffic polls
3. **Pagination**: Limit/offset for large form submission lists
4. **Polling Analytics**: Engagement metrics and trends
5. **Export**: CSV export of poll results and form submissions
6. **Scheduling**: Auto-publish/close polls at specific times

---

## Next Steps

- See [CONFIGURATION.md](CONFIGURATION.md) for deployment setup
- See [TESTING.md](TESTING.md) for test fixtures
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues

**Company**: Penguin Tech Inc
**License**: Limited AGPL-3.0
**Last Updated**: 2026-02-16
