# Slack Module Architecture

## System Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Slack Workspaces                              │
└─────────────────────────────────────────────────────────────────────┘
                    │                  │                  │
        ┌───────────┼──────────────────┼──────────────────┼───────────┐
        │           │                  │                  │           │
    Messages    Slash Cmds         Interactions      Shortcuts      Events
        │           │                  │                  │           │
        └───────────┴──────────────────┴──────────────────┴───────────┘
                    │
    ┌───────────────┴───────────────┐
    │                               │
HTTP Mode (webhooks)         Socket Mode (WebSocket)
    │                               │
    ▼                               ▼
POST /slack/events          WebSocket conn
POST /slack/commands        frame: envelope_id
POST /slack/actions         (Async only)
POST /slack/shortcuts
    │                               │
    └───────────────┬───────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │  Request Validation Layer  │
        │ - Signature verification   │
        │ - Rate limiting check      │
        │ - Request parsing          │
        └───────────────────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │  SlackBoltService Layer   │
        │ - Event routing            │
        │ - Credential lookup        │
        │ - Response formatting      │
        └───────────────────────────┘
                    │
            ┌───────┴─────────────┬────────────────┬───────────────┐
            │                     │                │               │
            ▼                     ▼                ▼               ▼
      Message Router        Command Router    Action Router   Shortcut Router
            │                     │                │               │
            │              /waddlebot             │         bookmark_msg
            │              /form                  │         create_ticket
            │              /poll                  │
            │              /ticket                │
            │              ... (24 total)         │
            │                                     │
            └──────────────┬──────────────────────┴───────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │  Event Normalization Layer   │
            │                              │
            │ {                            │
            │   "platform": "slack",       │
            │   "entity_id": "...",        │
            │   "message_type": "...",     │
            │   "content": "..."           │
            │ }                            │
            └──────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │    Router API Interface      │
            │ POST /execute-command        │
            │ POST /execute-response       │
            │ GET /command-status          │
            └──────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │   WaddleBot Router Service   │
            │                              │
            │ - Command execution          │
            │ - Business logic             │
            │ - Response generation        │
            └──────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │   Response Assembly Layer    │
            │                              │
            │ BlockKitBuilder constructs:  │
            │ - Modals                     │
            │ - Buttons                    │
            │ - Select menus               │
            │ - Rich text blocks           │
            └──────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │   Response Execution Layer   │
            │                              │
            │ - Post to channel            │
            │ - Open modals                │
            │ - Update messages            │
            │ - Ephemeral responses        │
            └──────────────────────────────┘
                           │
                           ▼
                    Slack API
```

---

## Core Components

### 1. SlackBoltService

**Location**: `src/services/slack_bolt_service.py`

Main orchestrator for all Slack event handling.

**Responsibilities:**
- Initialize Slack app connection (HTTP or Socket Mode)
- Register event handlers
- Route incoming events to appropriate handlers
- Manage credential lifecycle
- Coordinate responses back to Slack

**Key Methods:**
```python
class SlackBoltService:
    async def initialize(self) -> None
        # Initialize Slack app, register handlers, connect to DB/Redis

    async def handle_slash_command(
        ack, body, respond, client
    ) -> None
        # Route to specific command handler, return response

    async def handle_message_event(
        body, respond, client
    ) -> None
        # Filter for mentions, forward to router

    async def handle_action_event(
        ack, body, respond, client
    ) -> None
        # Route button/select interactions

    async def handle_modal_submission(
        ack, body, respond, client, view
    ) -> None
        # Validate, return errors or forward to router

    async def handle_shortcut(
        ack, body, respond, client
    ) -> None
        # Route global/message shortcuts

    async def get_workspace_token(team_id: str) -> str
        # Lookup from DB, refresh from Redis if needed

    async def post_to_slack(
        team_id: str, channel: str, blocks: list
    ) -> dict
        # Execute response back to Slack
```

**Concurrency Model:**
- Async/await throughout for non-blocking I/O
- Each handler runs in async context
- Database queries use async driver
- HTTP calls to router use aiohttp

---

### 2. BlockKitBuilder

**Location**: `src/services/block_kit_builder.py`

Utility for composing Slack Block Kit components programmatically.

**Responsibilities:**
- Abstract Block Kit complexity
- Generate modals, buttons, selects
- Format text (markdown, plain text)
- Ensure consistency in UI/UX

**Key Methods:**
```python
class BlockKitBuilder:
    @staticmethod
    def create_modal(
        callback_id: str,
        title: str,
        blocks: list,
        private_metadata: str = "",
        submit_label: str = "Submit"
    ) -> dict
        # Return modal JSON for client.views_open()

    @staticmethod
    def section_with_button(
        text: str,
        action_id: str,
        value: str,
        label: str = "Action",
        style: str = "primary"  # primary|danger
    ) -> dict
        # Button in section block

    @staticmethod
    def input_block(
        block_id: str,
        label: str,
        element_id: str,
        placeholder: str = "",
        required: bool = True,
        multiline: bool = False
    ) -> dict
        # Text input block

    @staticmethod
    def select_block(
        block_id: str,
        label: str,
        action_id: str,
        options: list,
        placeholder: str = ""
    ) -> dict
        # Dropdown selection block

    @staticmethod
    def confirmation_modal(
        callback_id: str,
        title: str,
        text: str,
        confirm_label: str = "Confirm",
        deny_label: str = "Cancel"
    ) -> dict
        # Confirmation modal

    @staticmethod
    def format_markdown(text: str) -> dict
        # Rich text block with markdown

    @staticmethod
    def error_message(field: str, reason: str) -> dict
        # Validation error in modal
```

**Example Usage:**
```python
modal = BlockKitBuilder.create_modal(
    callback_id="form_submission",
    title="Create Ticket",
    blocks=[
        BlockKitBuilder.input_block(
            block_id="title_block",
            label="Ticket Title",
            element_id="title_input"
        ),
        BlockKitBuilder.input_block(
            block_id="desc_block",
            label="Description",
            element_id="desc_input",
            multiline=True
        ),
    ]
)
client.views_open(trigger_id=trigger_id, view=modal)
```

---

## Event Flow

### Slash Command Flow

```
User types: /waddlebot balance
        │
        ▼
Slack receives → verifies signature → POST to webhook
        │
        ▼
Module /slack/commands endpoint
        │
        ├─ Validate X-Slack-Signature
        ├─ Check rate limits
        ├─ Parse form data
        │
        ▼
SlackBoltService.handle_slash_command()
        │
        ├─ Lookup team_id in database
        ├─ Extract command text: "balance"
        ├─ Normalize event:
        │   {
        │     "platform": "slack",
        │     "entity_id": "T123:C456",
        │     "message_type": "slashCommand",
        │     "content": "balance",
        │     "user_id": "U789",
        │     "metadata": { "command": "/waddlebot" }
        │   }
        │
        ▼
POST http://router-api/execute-command
        │
        ▼
Router executes business logic
        │
        ├─ Look up user reputation balance
        ├─ Generate response blocks
        ├─ Return { "status": "success", "blocks": [...] }
        │
        ▼
Module receives response
        │
        ├─ Check response_type (ephemeral vs in_channel)
        ├─ Format as Slack API call
        ├─ POST to Slack API (client.chat_postMessage)
        │
        ▼
User sees response in Slack
```

### Modal Submission Flow

```
User fills form → clicks "Submit"
        │
        ▼
Slack POST /slack/actions with type=view_submission
        │
        ├─ Validate signature
        ├─ Parse view.state.values
        │
        ▼
SlackBoltService.handle_modal_submission()
        │
        ├─ Extract field values from state
        ├─ Validate (required fields, format)
        ├─ If validation fails:
        │   return {
        │     "response_action": "errors",
        │     "errors": { "block_1": "Required field" }
        │   }
        │
        ├─ If validation passes:
        │   ├─ Normalize event
        │   ├─ Forward to router
        │   │
        │   ▼
        │   Router processes submission
        │   │
        │   ├─ Save to database
        │   ├─ Generate response (modal close + message)
        │   │
        │   ▼
        │   Module receives response
        │   ├─ Close modal (return {})
        │   ├─ Post response message to channel
        │
        ▼
User sees modal closed + success message
```

### Button/Select Interaction Flow

```
User clicks button in message
        │
        ▼
Slack POST /slack/actions with type=block_actions
        │
        ├─ Parse actions array (may have multiple)
        ├─ Extract action_id, value, block_id
        │
        ▼
SlackBoltService.handle_action_event()
        │
        ├─ Acknowledge immediately (ack)
        ├─ Determine action type (button vs select)
        ├─ Normalize event:
        │   {
        │     "message_type": "interaction",
        │     "metadata": {
        │       "action_id": "approve_button",
        │       "value": "user_123",
        │       "trigger_id": "..."
        │     }
        │   }
        │
        ▼
POST http://router-api/execute-command
        │
        ▼
Router processes action
        │
        ├─ Approve user (action_id=approve_button)
        ├─ Generate response (updated message blocks)
        ├─ Return response blocks
        │
        ▼
Module receives response
        │
        ├─ Update message with new blocks (client.chat_update)
        │   OR
        ├─ Post ephemeral response (client.chat_postEphemeral)
        │
        ▼
Message updated in Slack
```

---

## Request Validation

### Signature Verification

Slack signs every webhook with HMAC-SHA256:

```python
# Request signature format
X-Slack-Signature: v0=hmac_sha256_hash

# Validation formula
timestamp = request.headers['X-Slack-Request-Timestamp']
signature = request.headers['X-Slack-Signature']

# Prevent replay attacks (timestamp must be recent)
if abs(current_time - timestamp) > 300:
    return 401 Unauthorized

# Verify signature
base_string = f"v0:{timestamp}:{request.body}"
computed_hash = hmac.new(
    SIGNING_SECRET.encode(),
    base_string.encode(),
    hashlib.sha256
).hexdigest()
expected_signature = f"v0={computed_hash}"

if not hmac.compare_digest(signature, expected_signature):
    return 401 Unauthorized
```

### Rate Limiting

Per-team rate limits:

```python
RATE_LIMITS = {
    'slash_commands': 300/60,      # 5 per second per team
    'events': 300/60,              # 5 per second per team
    'actions': 300/60,             # 5 per second per team
}

# Implementation
redis.incr(f"ratelimit:slash_commands:{team_id}")
remaining = redis.ttl(f"ratelimit:slash_commands:{team_id}")
if remaining > RATE_LIMITS['slash_commands']:
    return 429 Too Many Requests
```

---

## Credential Management

### Token Storage

Slack bot tokens stored encrypted in database:

```sql
CREATE TABLE slack_workspaces (
    id SERIAL PRIMARY KEY,
    team_id VARCHAR(20) UNIQUE,
    team_name VARCHAR(255),
    bot_token TEXT,  -- AES-256 encrypted
    signing_secret TEXT,  -- AES-256 encrypted
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### Token Refresh (Redis Cache)

Tokens cached in Redis to avoid DB hits:

```python
async def get_workspace_token(team_id: str) -> str:
    # Check Redis cache first
    cached = await redis.get(f"workspace_token:{team_id}")
    if cached:
        return cached

    # Fallback to database
    workspace = await db.slack_workspaces.find(team_id=team_id)
    token = decrypt(workspace.bot_token)

    # Cache for 5 minutes
    await redis.setex(
        f"workspace_token:{team_id}",
        300,
        token
    )
    return token
```

---

## Response Handling

### Response Types

**In-Channel Response:**
```json
{
    "response_type": "in_channel",
    "blocks": [...]
}
```
Visible to entire channel.

**Ephemeral Response:**
```json
{
    "response_type": "ephemeral",
    "blocks": [...]
}
```
Only visible to user who triggered command.

**Modal Response:**
```json
{
    "type": "modal",
    "callback_id": "form_submit",
    "title": "...",
    "blocks": [...]
}
```
Opens as dialog overlay.

**Async Response (via response_url):**
```
POST https://hooks.slack.com/commands/T../B../X..
{
    "response_type": "in_channel",
    "blocks": [...]
}
```
Sent after initial 3-second response.

---

## Error Handling & Resilience

### Transient Error Retry

```python
async def call_router_with_retry(
    method: str,
    endpoint: str,
    data: dict,
    max_retries: int = 3
):
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    f"{ROUTER_API_URL}{endpoint}",
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            # Exponential backoff with jitter
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(wait_time)
```

### Modal Validation Errors

```python
if not title:
    ack()  # Acknowledge first
    return {
        "response_action": "errors",
        "errors": {
            "title_block": "Ticket title required"
        }
    }
```

---

## Performance Optimizations

### Async/Await Pattern

All I/O is non-blocking:

```python
# Concurrent requests to Router API
responses = await asyncio.gather(
    call_router("/check-user", user_data),
    call_router("/check-balance", user_data),
    call_router("/check-permissions", user_data)
)
```

### Connection Pooling

HTTP client pooled to avoid exhausting sockets:

```python
# Reuse session across requests
self.session = aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(
        limit=100,
        limit_per_host=30
    )
)
```

### Response Caching

Cache common queries:

```python
@cache.cached(timeout=300, key_prefix="user_perms:")
async def check_user_permissions(user_id: str) -> dict:
    return await db.user_roles.find(user_id=user_id)
```

---

## Testing Architecture

See [TESTING.md](TESTING.md) for test structure.

**Unit Tests**: Service classes in isolation
**Integration Tests**: Full flow with mock Slack API
**E2E Tests**: Live Slack workspace with test bot
