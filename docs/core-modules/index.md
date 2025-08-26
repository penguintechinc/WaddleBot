# Core Modules Overview

Core modules are the foundation of WaddleBot's architecture. These modules must be running for the system to function properly and provide the essential services that all other components depend on.

## Module Categories

### 🎯 **Required Core Modules**
These modules are essential and must always be running:

| Module | Purpose | Dependencies | Port |
|--------|---------|--------------|------|
| [Router Module](router.md) | Command routing and processing | PostgreSQL, Redis | 8000 |
| [Marketplace](marketplace.md) | Module management and distribution | PostgreSQL, Router | 8001 |
| [Identity Core](identity.md) | Cross-platform user identity | PostgreSQL, Redis, py4web Auth | 8050 |

### ⚙️ **Supporting Core Modules**
These provide additional core functionality:

| Module | Purpose | Dependencies | Port |
|--------|---------|--------------|------|
| [Labels Core](labels.md) | Community and user labeling | PostgreSQL, Redis | 8025 |
| [Portal Module](../admin/portal.md) | Web administration interface | PostgreSQL, Identity Core | 8000 |
| [Browser Sources](browser-sources.md) | OBS integration and overlays | WebSocket, Router | 8027 |

## Architecture Overview

```mermaid
graph TB
    subgraph "External Requests"
        P[Platform Collectors]
        W[Web Portal Users]
        A[Admin Requests]
    end
    
    subgraph "Core Services"
        R[Router Module<br/>:8000]
        M[Marketplace<br/>:8001] 
        I[Identity Core<br/>:8050]
        L[Labels Core<br/>:8025]
        PT[Portal<br/>:8000]
        BS[Browser Sources<br/>:8027]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL)]
        RD[(Redis)]
    end
    
    subgraph "External Integration"
        OBS[OBS Studio]
        WS[WebSocket Clients]
    end
    
    P --> R
    W --> PT
    A --> PT
    
    R --> M
    R --> I
    R --> L
    R --> BS
    
    PT --> I
    PT --> BS
    
    R --> PG
    R --> RD
    I --> PG
    I --> RD
    L --> PG
    L --> RD
    
    BS --> WS
    WS --> OBS
```

## Core Module Responsibilities

### 🚦 **Router Module** - Traffic Control Center
The heart of the WaddleBot system that handles all message routing and command processing.

**Key Features:**
- High-performance multi-threaded command processing
- Rate limiting with sliding window algorithm  
- Session management with Redis
- Database optimization with read replicas
- String matching for content moderation
- Execution engine routing (containers, Lambda, OpenWhisk)

**Performance:**
- Processes up to 100 concurrent events
- Sub-millisecond command lookups with caching
- Horizontal scaling with coordination system

### 🏪 **Marketplace Module** - Module Distribution Hub
Manages the discovery, installation, and lifecycle of community modules.

**Key Features:**
- Module browsing and search functionality
- Version control with upgrade/downgrade support
- Entity-based permission system
- Usage analytics and performance tracking
- Automatic router integration for command registration
- Subscription management for paid modules

**Integration:**
- Syncs commands with Router Module
- Provides API for Portal Module
- Manages module permissions per community

### 🔐 **Identity Core Module** - User Identity Management
Provides cross-platform identity linking and authentication services.

**Key Features:**
- py4web Auth foundation with extended user fields
- Cross-platform identity verification via whispers/DMs
- User API key management for programmatic access
- Multi-threaded processing with Redis caching
- Time-limited verification codes with security measures
- Comprehensive AAA (Authentication, Authorization, Auditing) logging

**Security Features:**
- SHA-256 hashed API keys
- Rate limiting to prevent abuse
- Platform integration for secure code delivery
- Session management with configurable expiration

### 🏷️ **Labels Core Module** - Community Organization
High-performance labeling system for organizing communities, users, and content.

**Key Features:**
- Multi-threaded architecture with ThreadPoolExecutor
- Bulk operations supporting up to 1000 items per batch
- Redis caching with fallback to local cache
- Label management for communities, modules, users, and entity groups
- Search functionality with performance optimization
- Background processing for long-running operations

**Performance:**
- Handles thousands of requests per second
- Concurrent user verification and entity group management
- Real-time metrics and health monitoring

### 🌐 **Portal Module** - Web Administration
Provides web-based administration interface for community managers.

**Key Features:**
- py4web-based web interface with modern design
- Community member management with roles and reputation
- Module installation and configuration management
- Browser source URL management for OBS integration
- Email integration for user notifications
- Dashboard with community statistics and metrics

**Integration:**
- Uses Identity Core for authentication
- Integrates with Browser Sources for OBS URLs
- Connects to Router for community data

### 🎨 **Browser Sources Module** - OBS Integration
Enables real-time browser source overlays for streaming and content creation.

**Key Features:**
- Multi-threaded WebSocket communication
- Three source types: ticker, media, and general displays
- Unique token-based URLs per community
- Real-time updates with automatic reconnection
- OBS-optimized templates with transparent backgrounds
- Queue management for ticker messages

**Source Types:**
- **Ticker**: Scrolling text notifications and alerts
- **Media**: Music display with album art and progress bars  
- **General**: Flexible HTML content for forms and announcements

## Module Communication

### **API Communication**
All core modules communicate via REST APIs through Kong Gateway:

```
Kong Gateway (:8000) 
├── /router/*     → Router Module (:8000)
├── /marketplace/* → Marketplace (:8001) 
├── /identity/*   → Identity Core (:8050)
├── /labels/*     → Labels Core (:8025)
├── /browser/*    → Browser Sources (:8027)
└── /portal/*     → Portal Module (:8000)
```

### **Data Sharing**
Core modules share data through:

- **PostgreSQL**: Persistent data storage with read replicas
- **Redis**: Session management, caching, and real-time data
- **Event System**: Router forwards events to appropriate modules
- **WebSocket**: Real-time updates for browser sources

### **Authentication Flow**
1. **User Authentication**: Portal uses Identity Core for login
2. **API Authentication**: Kong validates API keys from Identity Core
3. **Permission Checks**: Router validates entity permissions via Labels Core
4. **Session Management**: Redis stores user sessions across modules

## Configuration

### **Environment Variables**
Each core module requires specific environment configuration:

=== "Router Module"
    ```bash
    # Database
    DATABASE_URL=postgresql://user:pass@host:5432/waddlebot
    READ_REPLICA_URL=postgresql://user:pass@read-host:5432/waddlebot
    
    # Redis
    REDIS_HOST=redis
    REDIS_PORT=6379
    SESSION_TTL=3600
    
    # Performance
    ROUTER_MAX_WORKERS=20
    ROUTER_MAX_CONCURRENT=100
    ```

=== "Identity Core"
    ```bash
    # Module Configuration
    MODULE_NAME=identity_core_module
    MODULE_PORT=8050
    
    # Database & Redis
    DATABASE_URL=postgresql://user:pass@host:5432/waddlebot
    REDIS_HOST=redis
    
    # Security
    SECRET_KEY=your_secret_key_change_me
    SESSION_TTL=3600
    VERIFICATION_CODE_LENGTH=6
    ```

=== "Labels Core"
    ```bash
    # Performance Settings
    MAX_WORKERS=20
    CACHE_TTL=300
    BULK_OPERATION_SIZE=1000
    
    # Database & Redis
    DATABASE_URL=postgresql://user:pass@host:5432/waddlebot
    REDIS_HOST=redis
    ```

### **Database Schema**
Core modules create and manage their own database tables:

- **Router**: `commands`, `entities`, `command_executions`, `rate_limits`
- **Marketplace**: `modules`, `installations`, `subscriptions`
- **Identity**: `auth_user` (extended), `identity_links`, `api_keys`
- **Labels**: `labels`, `user_labels`, `entity_groups`

## Deployment Considerations

### **Startup Order**
Deploy core modules in this order to handle dependencies:

1. **PostgreSQL and Redis** (infrastructure)
2. **Identity Core** (authentication foundation)
3. **Router Module** (central command processing)
4. **Labels Core** (community organization)
5. **Marketplace** (module management)
6. **Portal and Browser Sources** (user interfaces)

### **Health Checks**
All core modules provide health check endpoints:

- `GET /health` - Basic service health
- `GET /health/detailed` - Detailed health with dependency status
- Database connectivity verification
- Redis connection testing
- External service availability

### **Scaling Considerations**
- **Router**: Scale horizontally with coordination system
- **Identity**: Scale based on authentication load
- **Labels**: Handle high-volume labeling operations
- **Browser Sources**: Scale WebSocket connections as needed

## Monitoring and Maintenance

### **Key Metrics**
Monitor these metrics for core module health:

- **Response Times**: API endpoint latency
- **Throughput**: Requests per second
- **Error Rates**: Failed requests and exceptions
- **Database Performance**: Query times and connection counts
- **Cache Hit Rates**: Redis performance metrics

### **Logging**
All core modules implement comprehensive AAA logging:

- **Authentication Events**: Login, logout, token operations
- **Authorization Events**: Permission checks and access control
- **Audit Events**: User actions and configuration changes
- **System Events**: Startup, shutdown, health status

### **Maintenance Tasks**
Regular maintenance for optimal performance:

- **Database Cleanup**: Archive old logs and sessions
- **Cache Management**: Monitor Redis memory usage
- **Health Monitoring**: Automated alerting for service issues
- **Performance Tuning**: Optimize based on usage patterns