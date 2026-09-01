# Workflow Core Module - Usage Guide

## Overview

This guide provides comprehensive examples and tutorials for creating, testing, and deploying workflows using the Workflow Core Module.

**Target Audience:** Developers, workflow creators, system administrators

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Creating Your First Workflow](#creating-your-first-workflow)
3. [Workflow Builder WebUI](#workflow-builder-webui)
4. [Node Type Reference](#node-type-reference)
5. [Advanced Patterns](#advanced-patterns)
6. [Variables & Expressions](#variables--expressions)
7. [Testing Workflows](#testing-workflows)
8. [Scheduling Workflows](#scheduling-workflows)
9. [Webhooks](#webhooks)
10. [Best Practices](#best-practices)

---

## Getting Started

### Prerequisites

- Access to Waddles admin panel
- Valid JWT authentication token
- Understanding of basic workflow concepts
- (Optional) License for advanced features

### Quick Start Checklist

1. ✓ Ensure workflow module is running (`/health` returns 200)
2. ✓ Obtain JWT authentication token
3. ✓ (Optional) Request license key for your community
4. ✓ Access workflow builder UI or use API
5. ✓ Create your first workflow
6. ✓ Test execution
7. ✓ Publish and activate

---

## Creating Your First Workflow

### Example 1: Simple Command-Response Workflow

This workflow responds to a chat command with a message.

#### Step 1: Define Workflow Structure

```json
{
  "name": "Hello World Workflow",
  "description": "Responds to !hello command",
  "entity_id": 123,
  "community_id": 456,
  "nodes": {
    "trigger1": {
      "node_id": "trigger1",
      "node_type": "trigger_command",
      "label": "Command: !hello",
      "position": {"x": 100, "y": 100},
      "config": {
        "command_name": "hello",
        "aliases": ["hi", "greet"]
      }
    },
    "action1": {
      "node_id": "action1",
      "node_type": "action_chat_message",
      "label": "Send Response",
      "position": {"x": 300, "y": 100},
      "config": {
        "message": "Hello, {{username}}! Welcome to the stream!",
        "target": "chat"
      }
    },
    "end1": {
      "node_id": "end1",
      "node_type": "flow_end",
      "label": "End",
      "position": {"x": 500, "y": 100}
    }
  },
  "connections": [
    {
      "connection_id": "conn1",
      "from_node_id": "trigger1",
      "from_port_name": "output",
      "to_node_id": "action1",
      "to_port_name": "input"
    },
    {
      "connection_id": "conn2",
      "from_node_id": "action1",
      "from_port_name": "output",
      "to_node_id": "end1",
      "to_port_name": "input"
    }
  ],
  "global_variables": {}
}
```

#### Step 2: Create Workflow via API

```bash
curl -X POST http://localhost:8070/api/v1/workflows \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d @workflow.json
```

#### Step 3: Publish Workflow

```bash
curl -X POST http://localhost:8070/api/v1/workflows/WORKFLOW_ID/publish \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"community_id": 456}'
```

#### Step 4: Test Execution

Trigger the workflow:
```bash
# Via chat (if integrated)
!hello

# Or via API
curl -X POST http://localhost:8070/api/v1/workflows/WORKFLOW_ID/execute \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 456,
    "variables": {
      "username": "TestUser"
    }
  }'
```

Expected output: Chat message "Hello, TestUser! Welcome to the stream!"

---

### Example 2: Conditional Workflow

This workflow uses conditional logic to respond differently based on user input.

#### Workflow Nodes

1. **Trigger:** Command `!checktime`
2. **Data:** Get current hour
3. **Condition:** If hour < 12
4. **Action (True):** Send "Good morning!"
5. **Action (False):** Send "Good afternoon/evening!"
6. **End**

#### Workflow Definition

```json
{
  "name": "Time-Based Greeting",
  "description": "Greets user based on time of day",
  "entity_id": 123,
  "community_id": 456,
  "nodes": {
    "trigger1": {
      "node_id": "trigger1",
      "node_type": "trigger_command",
      "label": "!checktime",
      "position": {"x": 100, "y": 200},
      "config": {
        "command_name": "checktime"
      }
    },
    "data1": {
      "node_id": "data1",
      "node_type": "data_transform",
      "label": "Get Current Hour",
      "position": {"x": 300, "y": 200},
      "config": {
        "transform_code": "from datetime import datetime\noutput = datetime.now().hour"
      }
    },
    "condition1": {
      "node_id": "condition1",
      "node_type": "condition_if",
      "label": "Is Morning?",
      "position": {"x": 500, "y": 200},
      "config": {
        "condition": {
          "operator": "less_than",
          "left": "{{hour}}",
          "right": 12
        }
      }
    },
    "action_morning": {
      "node_id": "action_morning",
      "node_type": "action_chat_message",
      "label": "Morning Greeting",
      "position": {"x": 700, "y": 100},
      "config": {
        "message": "Good morning, {{username}}! 🌅"
      }
    },
    "action_evening": {
      "node_id": "action_evening",
      "node_type": "action_chat_message",
      "label": "Evening Greeting",
      "position": {"x": 700, "y": 300},
      "config": {
        "message": "Good afternoon/evening, {{username}}! 🌙"
      }
    },
    "end1": {
      "node_id": "end1",
      "node_type": "flow_end",
      "label": "End",
      "position": {"x": 900, "y": 200}
    }
  },
  "connections": [
    {"connection_id": "c1", "from_node_id": "trigger1", "from_port_name": "output", "to_node_id": "data1", "to_port_name": "input"},
    {"connection_id": "c2", "from_node_id": "data1", "from_port_name": "output", "to_node_id": "condition1", "to_port_name": "input"},
    {"connection_id": "c3", "from_node_id": "condition1", "from_port_name": "true", "to_node_id": "action_morning", "to_port_name": "input"},
    {"connection_id": "c4", "from_node_id": "condition1", "from_port_name": "false", "to_node_id": "action_evening", "to_port_name": "input"},
    {"connection_id": "c5", "from_node_id": "action_morning", "from_port_name": "output", "to_node_id": "end1", "to_port_name": "input"},
    {"connection_id": "c6", "from_node_id": "action_evening", "from_port_name": "output", "to_node_id": "end1", "to_port_name": "input"}
  ]
}
```

---

### Example 3: Loop Workflow

This workflow demonstrates looping over a collection.

#### Use Case

Send a message for each item in a list (e.g., announce winners).

#### Workflow Definition

```json
{
  "name": "Announce Winners",
  "description": "Loop through winners and announce each one",
  "nodes": {
    "trigger1": {
      "node_type": "trigger_command",
      "config": {"command_name": "winners"}
    },
    "data1": {
      "node_type": "data_variable_set",
      "config": {
        "variable_name": "winners",
        "value": ["Alice", "Bob", "Charlie"]
      }
    },
    "loop1": {
      "node_type": "loop_foreach",
      "config": {
        "collection_variable": "winners",
        "item_variable": "winner",
        "index_variable": "index"
      }
    },
    "action1": {
      "node_type": "action_chat_message",
      "config": {
        "message": "🎉 Congratulations {{winner}}! You're winner #{{index + 1}}!"
      }
    },
    "delay1": {
      "node_type": "action_delay",
      "config": {
        "delay_seconds": 2
      }
    }
  },
  "connections": [
    {"from_node_id": "trigger1", "to_node_id": "data1"},
    {"from_node_id": "data1", "to_node_id": "loop1"},
    {"from_node_id": "loop1", "from_port_name": "loop_body", "to_node_id": "action1"},
    {"from_node_id": "action1", "to_node_id": "delay1"},
    {"from_node_id": "delay1", "to_node_id": "loop1", "to_port_name": "loop_continue"}
  ]
}
```

**Expected Execution:**
1. Set winners = ["Alice", "Bob", "Charlie"]
2. Loop iteration 1: "🎉 Congratulations Alice! You're winner #1!"
3. Wait 2 seconds
4. Loop iteration 2: "🎉 Congratulations Bob! You're winner #2!"
5. Wait 2 seconds
6. Loop iteration 3: "🎉 Congratulations Charlie! You're winner #3!"
7. Loop complete, workflow ends

---

## Workflow Builder WebUI

### Accessing the Builder

Navigate to: `https://your-waddlebot-instance/admin/workflows`

### Interface Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Workflow Builder                                           │
├─────────────────────────────────────────────────────────────┤
│  [Node Palette]        [Canvas]            [Properties]     │
│  ┌──────────────┐     ┌────────────────┐  ┌──────────────┐ │
│  │ Triggers     │     │                │  │ Node Config  │ │
│  │ - Command    │     │   [Node1]      │  │              │ │
│  │ - Event      │     │      ↓         │  │ Name: ___    │ │
│  │ - Webhook    │     │   [Node2]      │  │ Type: ___    │ │
│  │              │     │      ↓         │  │              │ │
│  │ Conditions   │     │   [Node3]      │  │ Config:      │ │
│  │ - If/Else    │     │                │  │ { ... }      │ │
│  │ - Switch     │     │                │  │              │ │
│  │              │     │                │  │              │ │
│  │ Actions      │     │                │  │ [Save]       │ │
│  │ - Module     │     │                │  │ [Test]       │ │
│  │ - Webhook    │     │                │  │ [Publish]    │ │
│  │ - Message    │     │                │  │              │ │
│  └──────────────┘     └────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Creating a Workflow in the UI

#### Step 1: Create New Workflow

1. Click "New Workflow"
2. Enter name and description
3. Select entity and community

#### Step 2: Add Nodes

1. Drag node from palette to canvas
2. Double-click node to configure
3. Fill in node properties
4. Click "Save" on node config

#### Step 3: Connect Nodes

1. Click on output port of first node
2. Drag to input port of second node
3. Connection line appears
4. Repeat for all connections

#### Step 4: Configure Global Variables

1. Click "Global Variables" tab
2. Add variable name and default value
3. Variables are available to all nodes

#### Step 5: Validate

1. Click "Validate" button
2. Review any errors or warnings
3. Fix issues as needed

#### Step 6: Test

1. Click "Test" button
2. Provide test input data
3. Review execution trace
4. Check outputs and logs

#### Step 7: Publish

1. Click "Publish" button
2. Workflow status changes to "active"
3. Workflow is now live and executable

---

## Node Type Reference

### Trigger Nodes

#### trigger_command

Triggered when a user types a chat command.

**Configuration:**
```json
{
  "command_name": "mycommand",
  "aliases": ["alias1", "alias2"],
  "description": "Command description",
  "cooldown_seconds": 5,
  "permission_level": "everyone"
}
```

**Output Data:**
- `username`: User who triggered
- `args`: Command arguments (array)
- `message`: Full message text

#### trigger_event

Triggered by system events.

**Configuration:**
```json
{
  "event_type": "user_joined",
  "filters": {
    "platform": "twitch"
  }
}
```

**Output Data:**
- Event-specific data based on `event_type`

#### trigger_webhook

Triggered by HTTP POST to webhook URL.

**Configuration:**
```json
{
  "webhook_token": "generated-token",
  "require_signature": true
}
```

**Output Data:**
- `payload`: Webhook POST body
- `headers`: HTTP headers

#### trigger_schedule

Triggered by cron schedule.

**Configuration:**
```json
{
  "cron_expression": "0 9 * * *",
  "timezone": "America/New_York",
  "enabled": true
}
```

**Output Data:**
- `scheduled_time`: ISO timestamp of scheduled execution

---

### Condition Nodes

#### condition_if

If/else branching.

**Configuration:**
```json
{
  "condition": {
    "operator": "equals",
    "left": "{{status}}",
    "right": "active"
  }
}
```

**Operators:**
- `equals`, `not_equals`
- `greater_than`, `less_than`, `greater_equal`, `less_equal`
- `contains`, `not_contains`
- `matches_regex`, `in_list`, `not_in_list`

**Output Ports:**
- `true`: Condition is true
- `false`: Condition is false

#### condition_switch

Multi-way branching (like switch/case).

**Configuration:**
```json
{
  "switch_variable": "{{tier}}",
  "cases": [
    {"value": "gold", "output_port": "case_gold"},
    {"value": "silver", "output_port": "case_silver"},
    {"value": "bronze", "output_port": "case_bronze"}
  ],
  "default_port": "case_default"
}
```

**Output Ports:**
- `case_gold`, `case_silver`, `case_bronze`: Specific cases
- `case_default`: No match

---

### Action Nodes

#### action_module

Execute a module action via Router.

**Configuration:**
```json
{
  "module_name": "music_module",
  "action": "play_song",
  "params": {
    "song_name": "{{requested_song}}",
    "volume": 80
  }
}
```

**Output Data:**
- Module-specific response

#### action_webhook

Send HTTP request to external API.

**Configuration:**
```json
{
  "url": "https://api.example.com/notify",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer {{api_token}}"
  },
  "body": {
    "message": "{{notification_text}}"
  },
  "timeout_seconds": 30
}
```

**Output Data:**
- `status_code`: HTTP status code
- `response_body`: Response body
- `response_headers`: Response headers

#### action_chat_message

Send message to chat.

**Configuration:**
```json
{
  "message": "Hello {{username}}!",
  "target": "chat",
  "delay_ms": 0
}
```

#### action_delay

Wait for specified duration.

**Configuration:**
```json
{
  "delay_seconds": 5
}
```

---

### Data Nodes

#### data_transform

Transform data using Python code (sandboxed).

**Configuration:**
```json
{
  "transform_code": "output = input['value'] * 2",
  "input_variable": "my_input",
  "output_variable": "my_output"
}
```

**Available Globals:**
- `input`: Input data
- `variables`: Context variables (read-only)
- Standard Python builtins (safe subset)

**Example Transforms:**

```python
# Parse JSON string
import json
output = json.loads(input)

# Calculate sum
output = sum([int(x) for x in input.split(',')])

# String manipulation
output = input.strip().upper()

# Date formatting
from datetime import datetime
output = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
```

#### data_variable_set

Set variable value.

**Configuration:**
```json
{
  "variable_name": "counter",
  "value": "{{counter + 1}}"
}
```

#### data_variable_get

Get variable value.

**Configuration:**
```json
{
  "variable_name": "user_score",
  "default_value": 0
}
```

---

### Loop Nodes

#### loop_foreach

Iterate over collection.

**Configuration:**
```json
{
  "collection_variable": "items",
  "item_variable": "item",
  "index_variable": "i"
}
```

**Ports:**
- Input: `input`
- Output: `loop_body` (execute for each item), `output` (after loop completes)

#### loop_while

Loop while condition is true.

**Configuration:**
```json
{
  "condition": {
    "operator": "less_than",
    "left": "{{counter}}",
    "right": 10
  },
  "max_iterations": 100
}
```

#### loop_break

Break out of current loop.

**Configuration:**
```json
{
  "condition": {
    "operator": "equals",
    "left": "{{found}}",
    "right": true
  }
}
```

---

### Flow Nodes

#### flow_merge

Wait for all inputs before continuing.

**Configuration:**
```json
{
  "merge_strategy": "wait_all"
}
```

#### flow_parallel

Execute multiple paths in parallel.

**Configuration:**
```json
{
  "max_parallel": 5
}
```

#### flow_end

Terminate workflow execution.

**Configuration:**
```json
{
  "output_data": {
    "result": "success"
  }
}
```

---

## Advanced Patterns

### Pattern 1: API Integration with Error Handling

```json
{
  "nodes": {
    "trigger": {"node_type": "trigger_command", "config": {"command_name": "weather"}},
    "webhook": {
      "node_type": "action_webhook",
      "config": {
        "url": "https://api.weather.com/forecast",
        "method": "GET",
        "params": {"city": "{{city}}"}
      }
    },
    "condition": {
      "node_type": "condition_if",
      "config": {
        "condition": {
          "operator": "equals",
          "left": "{{webhook_status}}",
          "right": 200
        }
      }
    },
    "success": {
      "node_type": "action_chat_message",
      "config": {"message": "Weather: {{weather_data.temp}}°F"}
    },
    "error": {
      "node_type": "action_chat_message",
      "config": {"message": "Failed to fetch weather data"}
    }
  },
  "connections": [
    {"from_node_id": "trigger", "to_node_id": "webhook"},
    {"from_node_id": "webhook", "to_node_id": "condition"},
    {"from_node_id": "condition", "from_port_name": "true", "to_node_id": "success"},
    {"from_node_id": "condition", "from_port_name": "false", "to_node_id": "error"}
  ]
}
```

### Pattern 2: Parallel Execution

Execute multiple actions concurrently:

```json
{
  "nodes": {
    "trigger": {"node_type": "trigger_command"},
    "parallel": {"node_type": "flow_parallel"},
    "action1": {"node_type": "action_module", "config": {"module_name": "lights", "action": "flash"}},
    "action2": {"node_type": "action_module", "config": {"module_name": "sound", "action": "play_sfx"}},
    "action3": {"node_type": "action_chat_message", "config": {"message": "Effect triggered!"}},
    "merge": {"node_type": "flow_merge"}
  },
  "connections": [
    {"from_node_id": "trigger", "to_node_id": "parallel"},
    {"from_node_id": "parallel", "from_port_name": "out1", "to_node_id": "action1"},
    {"from_node_id": "parallel", "from_port_name": "out2", "to_node_id": "action2"},
    {"from_node_id": "parallel", "from_port_name": "out3", "to_node_id": "action3"},
    {"from_node_id": "action1", "to_node_id": "merge"},
    {"from_node_id": "action2", "to_node_id": "merge"},
    {"from_node_id": "action3", "to_node_id": "merge"}
  ]
}
```

### Pattern 3: Dynamic Loop with Break

```json
{
  "nodes": {
    "trigger": {"node_type": "trigger_command"},
    "set_counter": {"node_type": "data_variable_set", "config": {"variable_name": "counter", "value": 0}},
    "loop": {
      "node_type": "loop_while",
      "config": {
        "condition": {"operator": "less_than", "left": "{{counter}}", "right": 100}
      }
    },
    "transform": {
      "node_type": "data_transform",
      "config": {"transform_code": "import random\noutput = random.randint(1, 10)"}
    },
    "check": {
      "node_type": "condition_if",
      "config": {"condition": {"operator": "equals", "left": "{{output}}", "right": 7}}
    },
    "break": {"node_type": "loop_break"},
    "increment": {
      "node_type": "data_variable_set",
      "config": {"variable_name": "counter", "value": "{{counter + 1}}"}
    },
    "result": {
      "node_type": "action_chat_message",
      "config": {"message": "Found lucky number 7 after {{counter}} attempts!"}
    }
  }
}
```

---

## Variables & Expressions

### Variable Scopes

1. **Global Variables**: Defined in workflow definition, available to all nodes
2. **Trigger Variables**: Provided by trigger (username, args, etc.)
3. **Node Output Variables**: Set by node execution
4. **Loop Variables**: `item`, `index` in foreach loops

### Expression Syntax

Use `{{expression}}` to interpolate variables:

```
Hello, {{username}}!
Your score is {{score * 2}}
Time: {{timestamp.strftime('%H:%M:%S')}}
```

### Expression Examples

#### String Operations
```python
{{username.upper()}}
{{message.strip()}}
{{'Welcome ' + username}}
{{message[:10]}}  # First 10 characters
```

#### Math Operations
```python
{{score + 100}}
{{price * 1.1}}  # Add 10% tax
{{points // 10}}  # Integer division
{{abs(value)}}
{{max(a, b, c)}}
```

#### Conditional Expressions
```python
{{score if score > 0 else 0}}
{{'VIP' if tier == 'gold' else 'Regular'}}
```

#### List Operations
```python
{{len(items)}}
{{items[0]}}
{{', '.join(names)}}
{{[x * 2 for x in numbers]}}
```

#### Date/Time
```python
{{datetime.now()}}
{{timestamp.year}}
{{(datetime.now() - created_at).days}}
```

---

## Testing Workflows

### Test Workflow Endpoint

Use the test endpoint for dry-run execution:

```bash
curl -X POST http://localhost:8070/api/v1/workflows/WORKFLOW_ID/test \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 456,
    "variables": {
      "username": "TestUser",
      "message": "test message"
    }
  }'
```

### Test Response

```json
{
  "success": true,
  "data": {
    "execution_id": "test-exec-uuid",
    "test_mode": true,
    "status": "completed",
    "execution_time_seconds": 1.5,
    "trace": [
      {
        "node_id": "trigger1",
        "status": "completed",
        "duration_seconds": 0.1,
        "input": {},
        "output": {"username": "TestUser"},
        "logs": ["Trigger activated"],
        "error": null
      },
      {
        "node_id": "action1",
        "status": "completed",
        "duration_seconds": 0.5,
        "input": {"username": "TestUser"},
        "output": {"message_sent": true},
        "logs": ["Message sent"],
        "error": null
      }
    ],
    "final_variables": {"username": "TestUser"},
    "summary": {
      "nodes_executed": 2,
      "nodes_failed": 0,
      "total_duration": 1.5,
      "passed": true
    }
  }
}
```

### Debugging Tips

1. **Review Trace**: Check each node's input/output
2. **Check Logs**: Look for error messages in node logs
3. **Verify Variables**: Ensure variables have expected values
4. **Test Expressions**: Use data_transform nodes to print variables

---

## Scheduling Workflows

### Create a Schedule

```bash
curl -X POST http://localhost:8070/api/v1/workflows/WORKFLOW_ID/schedules \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Report",
    "cron_expression": "0 9 * * *",
    "timezone": "America/New_York",
    "enabled": true
  }'
```

### Cron Expression Examples

| Expression | Description |
|------------|-------------|
| `0 * * * *` | Every hour at minute 0 |
| `0 9 * * *` | Every day at 9 AM |
| `0 0 * * 0` | Every Sunday at midnight |
| `*/15 * * * *` | Every 15 minutes |
| `0 9 * * 1-5` | Every weekday at 9 AM |
| `0 0 1 * *` | First day of every month |

---

## Webhooks

### Create Webhook

```bash
curl -X POST http://localhost:8070/api/v1/workflows/WORKFLOW_ID/webhooks \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GitHub Webhook",
    "require_signature": true,
    "ip_allowlist": ["192.30.252.0/22"],
    "rate_limit_max": 100,
    "rate_limit_window": 60
  }'
```

### Trigger Webhook

```bash
curl -X POST https://your-instance.com/api/v1/workflows/webhooks/TOKEN \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: sha256=SIGNATURE" \
  -d '{
    "event": "push",
    "repository": "my-repo",
    "commits": 3
  }'
```

### Generate Signature (Python)

```python
import hmac
import hashlib

def generate_signature(token, secret, body):
    message = token.encode() + body.encode()
    signature = 'sha256=' + hmac.new(
        secret.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    return signature
```

---

## Best Practices

### Workflow Design

1. **Keep It Simple**: Start with simple workflows, add complexity as needed
2. **Use Descriptive Names**: Name nodes and variables clearly
3. **Add Comments**: Use node descriptions to document purpose
4. **Test Thoroughly**: Use test endpoint before publishing
5. **Handle Errors**: Add error handling for external calls

### Performance

1. **Avoid Deep Nesting**: Limit loop depth to 3-4 levels
2. **Set Timeouts**: Configure appropriate timeouts for webhooks
3. **Use Parallel Execution**: Run independent actions concurrently
4. **Optimize Loops**: Limit iterations, use loop_break when possible

### Security

1. **Validate Input**: Check user input in trigger nodes
2. **Use Permissions**: Set appropriate permission levels on commands
3. **Secure Webhooks**: Enable signature verification
4. **Limit API Keys**: Don't hardcode sensitive data, use variables

### Maintenance

1. **Version Control**: Keep track of workflow versions
2. **Monitor Executions**: Review execution logs regularly
3. **Update Schedules**: Adjust schedules based on usage patterns
4. **Archive Unused**: Archive workflows that are no longer needed
