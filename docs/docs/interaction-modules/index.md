# Interaction Modules Overview

Interaction modules provide the functional features that communities use daily. Unlike core modules, interaction modules are optional and can be enabled or disabled per community based on their needs.

## Module Categories

### 🤖 **Communication & AI**
| Module | Purpose | Key Features |
|--------|---------|--------------|
| [AI Interaction](ai.md) | Chat responses with AI providers | Ollama, OpenAI, MCP support |
| [Alias System](alias.md) | Linux-style command aliases | Variable substitution, nested commands |

### 🎵 **Media & Entertainment**
| Module | Purpose | Key Features |
|--------|---------|--------------|
| [YouTube Music](youtube-music.md) | Music search and playback | YouTube API, OBS integration |
| [Spotify Integration](spotify.md) | Music control and display | OAuth, device control, playlists |
| [Shoutouts](shoutouts.md) | User recognition and clips | Auto-shoutouts, Twitch clips |

### 🗂️ **Community Management**
| Module | Purpose | Key Features |
|--------|---------|--------------|
| [Inventory Management](../inventory-interaction-module.md) | Item tracking system | Multi-threaded, label support |
| [Calendar Events](calendar.md) | Event management | Approval workflows, recurring events |
| [Memories System](memories.md) | Quote and reminder management | Search, categorization, reminders |

## Architecture Pattern

All interaction modules follow a consistent architecture pattern:

```mermaid
graph LR
    R[Router Module] --> IM[Interaction Module]
    IM --> DB[(Module Database)]
    IM --> API[External APIs]
    IM --> BS[Browser Sources]
    IM --> R
    
    subgraph "Module Structure"
        C[Controllers]
        S[Services]
        M[Models]
    end
    
    IM --> C
    C --> S
    S --> M
```

### **Standard Components**

=== "Controllers"
    Handle HTTP requests and routing:
    ```python
    # Standard controller pattern
    @action
    def process_command(self):
        # Validate request
        # Process command
        # Return response
    ```

=== "Services"
    Business logic and external integrations:
    ```python
    # Service layer pattern
    class ModuleService:
        def __init__(self):
            self.router_service = RouterService()
            self.external_api = ExternalAPI()
        
        def process_request(self, data):
            # Business logic here
            pass
    ```

=== "Models" 
    Database schema and data models:
    ```python
    # py4web DAL models
    db.define_table('module_data',
        Field('community_id', 'string'),
        Field('user_id', 'string'),
        Field('data', 'json')
    )
    ```

## Communication Patterns

### **Router Integration**
All interaction modules communicate with the Router Module:

```python
# Standard router communication
response = requests.post(f"{ROUTER_API_URL}/responses", {
    "session_id": session_id,
    "success": True,
    "response_action": "chat",
    "response_data": {
        "message": "Command executed successfully"
    }
})
```

### **Response Types**
Modules can return different response types:

=== "Chat Response"
    ```json
    {
        "response_action": "chat",
        "response_data": {
            "message": "Hello from the AI module!"
        }
    }
    ```

=== "Media Response"
    ```json
    {
        "response_action": "media", 
        "response_data": {
            "title": "Now Playing",
            "artist": "Artist Name",
            "album_art_url": "https://...",
            "duration": 180
        }
    }
    ```

=== "Ticker Response"
    ```json
    {
        "response_action": "ticker",
        "response_data": {
            "text": "Welcome new follower!",
            "duration": 10,
            "priority": "high"
        }
    }
    ```

## Module Development

### **Creating New Modules**
Follow this template structure for new interaction modules:

```
new_interaction_module/
├── Dockerfile                 # Container definition
├── app.py                    # Main py4web application
├── config.py                 # Configuration management
├── models.py                 # Database models
├── requirements.txt          # Python dependencies
├── services/                 # Business logic
│   ├── __init__.py
│   ├── module_service.py     # Core functionality
│   └── router_service.py     # Router communication
└── k8s/                      # Kubernetes deployment
    └── deployment.yaml
```

### **Standard Environment Variables**
Every interaction module should support these variables:

```bash
# Module Identity
MODULE_NAME=your_module_name
MODULE_VERSION=1.0.0
MODULE_PORT=8XXX

# Database Connection
DATABASE_URL=postgresql://user:pass@host:5432/waddlebot

# Core API Integration
CORE_API_URL=http://router-service:8000
ROUTER_API_URL=http://router-service:8000/router

# Performance Settings
MAX_WORKERS=20
REQUEST_TIMEOUT=30
LOG_LEVEL=INFO
```

## Installation & Management

### **Module Registration**
Modules automatically register with the Marketplace on startup:

1. **Health Check**: Marketplace verifies module is running
2. **Capability Discovery**: Module reports supported commands
3. **Registration**: Module added to available modules list
4. **Entity Assignment**: Communities can install the module

### **Community Installation**
Community managers install modules through:

- **Web Portal**: Point-and-click installation interface
- **Chat Commands**: `!marketplace install module_name`
- **API Integration**: Programmatic installation via REST API

### **Permission System**
Each module installation includes:

- **Entity Permissions**: Which communities can use the module
- **User Permissions**: Role-based access within communities
- **Command Permissions**: Granular control over specific commands
- **Rate Limiting**: Per-user and per-community limits

## Performance Considerations

### **Multi-threading**
High-volume modules should use ThreadPoolExecutor:

```python
from concurrent.futures import ThreadPoolExecutor

class ModuleService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=20)
    
    def process_bulk_operation(self, items):
        futures = []
        for item in items:
            future = self.executor.submit(self.process_item, item)
            futures.append(future)
        
        return [f.result() for f in futures]
```

### **Caching Strategy**
Implement caching for frequently accessed data:

```python
import redis
from functools import wraps

def cached(ttl=300):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args)+str(kwargs))}"
            cached_result = redis_client.get(cache_key)
            
            if cached_result:
                return json.loads(cached_result)
            
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

### **Database Optimization**
Use proper indexing and connection pooling:

```python
# Efficient database queries
db.executesql("""
    CREATE INDEX IF NOT EXISTS idx_community_user 
    ON module_data(community_id, user_id)
""")

# Bulk operations
db.executesql("""
    INSERT INTO module_data (community_id, user_id, data)
    VALUES %s
""", [values_list])
```

## Monitoring & Logging

### **Health Endpoints**
Every module should provide health monitoring:

```python
@action
def health(self):
    return {
        "status": "healthy",
        "module": MODULE_NAME,
        "version": MODULE_VERSION,
        "dependencies": {
            "database": check_database_connection(),
            "router": check_router_connection(),
            "external_api": check_external_api()
        }
    }
```

### **AAA Logging**
Implement comprehensive Authentication, Authorization, and Auditing:

```python
import logging

# Structured logging format
logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(message)s')

def log_user_action(community_id, user_id, action, result):
    logger.info(
        f"AUDIT community={community_id} user={user_id} "
        f"action={action} result={result}"
    )
```

## Best Practices

### **Error Handling**
Always provide meaningful error responses:

```python
try:
    result = process_command(data)
    return {"success": True, "data": result}
except ValidationError as e:
    return {"success": False, "error": f"Invalid input: {e}"}
except ExternalAPIError as e:
    return {"success": False, "error": "External service unavailable"}
except Exception as e:
    logger.exception("Unexpected error")
    return {"success": False, "error": "Internal server error"}
```

### **Configuration Management**
Use environment variables with sensible defaults:

```python
import os

class Config:
    MODULE_NAME = os.getenv('MODULE_NAME', 'default_module')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', '10'))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
```

### **Testing Strategy**
Include comprehensive tests:

```python
import unittest
from unittest.mock import Mock, patch

class TestModuleService(unittest.TestCase):
    def setUp(self):
        self.service = ModuleService()
    
    def test_process_command_success(self):
        # Test successful command processing
        pass
    
    def test_process_command_error_handling(self):
        # Test error conditions
        pass
```

## Next Steps

- **[AI Interaction](ai.md)**: Set up AI-powered chat responses
- **[Music Integration](youtube-music.md)**: Add YouTube Music support
- **[Community Tools](../inventory-interaction-module.md)**: Enable inventory management
- **[Development Guide](../CONTRIBUTION.md)**: Build your own modules