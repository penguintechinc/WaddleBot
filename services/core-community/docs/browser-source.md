# Browser Source & OBS Overlay Integration

Integration guide for browser source overlays and OBS source updates in the WaddleBot workflow system.

## Overview

The ActionBrowserSource node type enables workflows to dynamically update OBS (Open Broadcaster Software) browser sources and overlays in real-time. This allows real-time alerts, notifications, animations, and interactive overlays triggered by workflow events.

## Node Type: ActionBrowserSource

Node configuration for updating browser sources:

```python
ActionBrowserSourceConfig:
  node_id: str
  label: str
  position: dict
  source_type: str               # "ticker", "alert", "overlay", "custom"
  action: str                    # "display", "hide", "update", "refresh"
  content_template: str          # Template with {{variable}} replacement
  duration: int                  # Display duration in seconds (optional)
  priority: int                  # Priority level for overlays
  enabled: bool = True
  metadata: dict = {}
```

## Source Types

### ticker
Scrolling text ticker for announcements, chat messages, or notifications.

- Use for: Chat overlays, alert messages, live feed displays
- Duration: Persistent or time-limited
- Template: Text content with formatting

Example:
```python
node = ActionBrowserSourceConfig(
    node_id="chat_ticker",
    label="Chat Ticker Update",
    source_type="ticker",
    action="update",
    content_template="New message from {{username}}: {{message}}",
    duration=5
)
```

### alert
Alert boxes and notification popups for events (follows, subscriptions, raids, donations).

- Use for: Event notifications, achievements, milestones
- Duration: Fade-in/out animation (typically 3-8 seconds)
- Priority: Can be stacked

Example:
```python
node = ActionBrowserSourceConfig(
    node_id="follower_alert",
    label="New Follower Alert",
    source_type="alert",
    action="display",
    content_template="{{username}} just followed!",
    duration=5,
    priority=10
)
```

### overlay
Persistent overlays for status displays, counters, progress bars.

- Use for: Game overlays, status displays, leaderboards
- Duration: Persistent (displayed until hidden)
- Priority: Background level (lower values)

Example:
```python
node = ActionBrowserSourceConfig(
    node_id="stream_stats",
    label="Stream Statistics",
    source_type="overlay",
    action="update",
    content_template=JSON.stringify({
        "viewers": "{{viewer_count}}",
        "subscribers": "{{sub_count}}",
        "uptime": "{{stream_uptime}}"
    }),
    priority=1
)
```

### custom
Custom HTML/CSS overlay for complex designs and animations.

- Use for: Custom designed overlays, complex interactions
- Duration: Configurable
- Priority: Any

Example:
```python
node = ActionBrowserSourceConfig(
    node_id="custom_overlay",
    label="Custom Design",
    source_type="custom",
    action="display",
    content_template='<div class="custom">{{content}}</div>',
    duration=10,
    priority=5
)
```

## Actions

### display
Show the browser source or overlay.

```python
action="display"
# Makes the source visible, respects priority for overlays
```

### hide
Hide the browser source or overlay.

```python
action="hide"
# Removes from display, gracefully fades out
```

### update
Update content of the browser source without visibility change.

```python
action="update"
# Updates content, maintains current visibility state
```

### refresh
Force refresh the browser source (reload from URL).

```python
action="refresh"
# Useful for pulling latest data from webhook
```

## Variable Replacement

All content templates support `{{variable}}` replacement from workflow context:

**Common Variables:**
- `{{username}}` - User who triggered the event
- `{{message}}` - Chat message or event message
- `{{count}}` - Count of items (followers, subs, etc.)
- `{{amount}}` - Donation or points amount
- `{{timestamp}}` - Event timestamp
- Any custom variable set earlier in workflow

Example template:
```
"{{username}} donated {{amount}} points! {{message}}"
→ "JohnDoe donated 500 points! Great stream!"
```

## Integration with OBS

### Setup in OBS

1. **Add Browser Source**
   - Source → Browser
   - Set Custom URL: `http://localhost:3000/overlay/broadcast`
   - Set size/position as desired
   - Enable interaction if needed

2. **Multiple Sources**
   - Alert overlay: Centered, high priority
   - Chat ticker: Bottom, scrolling
   - Stats overlay: Corner, persistent
   - Custom elements: As needed

### Webhook Configuration

Browser sources pull updates via HTTP:

```python
# In workflow
node = ActionBrowserSourceConfig(
    node_id="update_overlay",
    action="update",
    source_type="alert",
    content_template='{"event":"{{event_type}}","user":"{{username}}"}',
    duration=5
)
```

The node executor sends HTTP PATCH request:
```
PATCH /api/v1/browser-source/broadcast/update
Content-Type: application/json

{
  "source_type": "alert",
  "action": "update",
  "content": {"event": "follow", "user": "john_doe"},
  "duration": 5,
  "priority": 10
}
```

## Real-World Examples

### Example 1: New Follower Alert

```python
workflow = WorkflowDefinition(
    metadata=WorkflowMetadata(
        name="Follower Alert System",
        trigger_type="event"
    ),
    nodes={
        "follower_trigger": TriggerEventConfig(
            node_id="follower_trigger",
            event_type="follow",
            platforms=["twitch"]
        ),
        "fetch_avatar": ActionModuleConfig(
            node_id="fetch_avatar",
            module_name="user_module",
            input_mapping={"user_id": "user_id"},
            output_mapping={"avatar_url": "user_avatar"}
        ),
        "show_alert": ActionBrowserSourceConfig(
            node_id="show_alert",
            source_type="alert",
            action="display",
            content_template='{"username":"{{username}}","avatar":"{{user_avatar}}"}',
            duration=5,
            priority=10
        )
    },
    connections=[
        WorkflowConnection(
            from_node_id="follower_trigger",
            from_port_name="triggered",
            to_node_id="fetch_avatar",
            to_port_name="input"
        ),
        WorkflowConnection(
            from_node_id="fetch_avatar",
            from_port_name="output",
            to_node_id="show_alert",
            to_port_name="input"
        )
    ]
)
```

### Example 2: Chat Ticker

```python
node = ActionBrowserSourceConfig(
    node_id="chat_ticker",
    label="Chat Messages",
    source_type="ticker",
    action="update",
    content_template="{{username}}: {{message}}",
    duration=null  # Persistent ticker
)
```

### Example 3: Stream Stats Overlay

```python
node = ActionBrowserSourceConfig(
    node_id="stats_overlay",
    label="Stream Statistics",
    source_type="overlay",
    action="update",
    content_template='{"viewers":{{viewer_count}},"duration":"{{stream_duration}}","game":"{{current_game}}"}',
    priority=1
)
```

## Node Executor Implementation

The NodeExecutor handles browser source nodes:

```python
async def execute_browser_source_node(
    node: ActionBrowserSourceConfig,
    context: ExecutionContext
) -> NodeExecutionState:
    """Execute browser source action"""
    
    # 1. Replace variables in content template
    content = replace_variables(node.content_template, context.variables)
    
    # 2. Send HTTP PATCH to browser source service
    response = await http_client.patch(
        f"{BROWSER_SOURCE_URL}/broadcast/update",
        json={
            "source_type": node.source_type,
            "action": node.action,
            "content": content,
            "duration": node.duration,
            "priority": node.priority
        },
        timeout=5
    )
    
    # 3. Record result
    if response.status_code == 200:
        state.mark_completed()
        state.set_output("browser_source_response", response.json())
    else:
        state.mark_failed(
            f"Browser source update failed: {response.status_code}",
            error_type="api_error"
        )
    
    return state
```

## Error Handling

**Common Errors:**

- `BROWSER_SOURCE_NOT_FOUND` (404) - Source doesn't exist
- `INVALID_TEMPLATE` (400) - Invalid variable replacement
- `PRIORITY_CONFLICT` (409) - Overlay priority conflict
- `TIMEOUT` (504) - Browser source service timeout
- `API_ERROR` (500) - Backend service error

**Handling in Workflow:**

Use ConditionIf nodes to handle failures:

```python
node = ConditionIfConfig(
    node_id="check_browser_result",
    condition=[
        ConditionRule(
            variable="browser_source_error",
            operator=OperatorType.EQUALS,
            value=None
        )
    ],
    output_true_port="success",
    output_false_port="error"
)
```

## Performance Considerations

- **Network Latency**: Browser source updates are async
- **Queue Processing**: Updates processed in order per source
- **Priority Handling**: Higher priority overlays render on top
- **Duration Management**: Automatic cleanup of timed overlays
- **Refresh Rate**: Don't update same source more than 10x/sec

## Security

### Input Validation

All content templates are validated:
- Max length: 10,000 characters
- No script injection (sanitized)
- Only allowed HTML tags in custom overlays

### Template Validation

Variables replaced in context of workflow scope:
- Only accessible variables replaced
- Safe fallback on missing variable
- No access to sensitive data

### Example Validation

```python
# ✓ Safe - only workflow variables
content = "{{username}}: {{message}}"

# ✗ Unsafe - would be rejected
content = "<script>alert('xss')</script>"

# ✓ Safe - HTML sanitized
content = '<div class="alert">{{username}}</div>'
```

## Best Practices

1. **Use appropriate source types** for different use cases
2. **Set reasonable durations** - avoid overlapping alerts
3. **Test in OBS** before deploying to production
4. **Use templates** for consistent formatting
5. **Monitor update frequency** - avoid network saturation
6. **Handle errors gracefully** - fallback displays
7. **Document variables** in workflow comments
8. **Version overlays** with workflow version
9. **Clean up old overlays** - set duration appropriately
10. **Cache frequently updated content** when possible

## Configuration

**Environment Variables:**

```bash
# Browser Source Service
BROWSER_SOURCE_URL=http://localhost:3000/api/v1
BROWSER_SOURCE_TIMEOUT=5
BROWSER_SOURCE_MAX_LENGTH=10000
BROWSER_SOURCE_RATE_LIMIT=10  # updates per second per source
```

**Database Table:**

```sql
CREATE TABLE browser_source_updates (
  id SERIAL PRIMARY KEY,
  workflow_id UUID,
  execution_id UUID,
  source_type VARCHAR(50),
  action VARCHAR(20),
  content JSONB,
  duration INT,
  priority INT,
  created_at TIMESTAMP
);
```

## Related Documentation

- **workflow-engine.md** - Complete workflow engine reference
- **NODE_EXECUTOR.md** - Node execution logic and patterns
- **MODELS.md** - Node configuration data models
