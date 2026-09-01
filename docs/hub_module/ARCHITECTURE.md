# Hub Module Architecture

## Overview

The Waddles Hub Module is a full-stack web application that serves as the central administration portal and community management interface. It consists of a Node.js/Express backend API and a React-based frontend SPA.

**Version:** 1.0.1
**Tech Stack:** Node.js 20+, Express, React 18, PostgreSQL, Socket.io

---

## Table of Contents

- [System Architecture](#system-architecture)
- [Backend Architecture](#backend-architecture)
- [Frontend Architecture](#frontend-architecture)
- [Database Architecture](#database-architecture)
- [Authentication & Authorization](#authentication--authorization)
- [Real-time Communication](#real-time-communication)
- [Module System](#module-system)
- [API Gateway Pattern](#api-gateway-pattern)
- [Security Architecture](#security-architecture)
- [Deployment Architecture](#deployment-architecture)

---

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  React SPA (Frontend)                                 │   │
│  │  - React Router                                       │   │
│  │  - Axios HTTP Client                                  │   │
│  │  - Socket.io Client                                   │   │
│  │  - TailwindCSS                                        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP/WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway Layer                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Hub Module Backend (Node.js/Express)                │   │
│  │  - REST API Endpoints                                │   │
│  │  - WebSocket Server (Socket.io)                      │   │
│  │  - Authentication Middleware                         │   │
│  │  - Request Validation                                │   │
│  │  - Service Proxy                                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
           │                │                │
           │ PostgreSQL     │ HTTP           │ WebSocket
           ▼                ▼                ▼
┌──────────────────┐  ┌─────────────────────────────────────┐
│   Database       │  │    Waddles Microservices          │
│  - Users         │  │  - Identity Core (OAuth)            │
│  - Communities   │  │  - Analytics Core                   │
│  - Modules       │  │  - Security Core                    │
│  - Announcements │  │  - Loyalty Interaction              │
│  - Chat History  │  │  - Reputation Module                │
│  - Bot Scores    │  │  - Browser Source                   │
└──────────────────┘  └─────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **Frontend SPA** | User interface, routing, state management |
| **Backend API** | Business logic, authentication, authorization |
| **Database** | Data persistence, relational integrity |
| **WebSocket Server** | Real-time chat, notifications |
| **Service Proxy** | Internal microservice communication |
| **Identity Core** | OAuth integration, identity linking |
| **Analytics Core** | Community analytics, bot detection |
| **Security Core** | Content filtering, moderation |

---

## Backend Architecture

### Directory Structure

```
backend/
├── src/
│   ├── config/
│   │   ├── index.js              # Main configuration
│   │   └── database.js           # PostgreSQL connection pool
│   ├── controllers/
│   │   ├── adminController.js    # Community admin endpoints
│   │   ├── authController.js     # Authentication logic
│   │   ├── communityController.js# Community management
│   │   ├── publicController.js   # Public API endpoints
│   │   ├── superadminController.js # Platform admin
│   │   ├── marketplaceController.js # Module marketplace
│   │   ├── musicController.js    # Music module
│   │   └── ...                   # Other controllers
│   ├── middleware/
│   │   ├── auth.js               # JWT authentication
│   │   ├── validation.js         # Request validation
│   │   ├── errorHandler.js       # Global error handling
│   │   ├── csrf.js               # CSRF protection
│   │   └── cookieConsent.js      # GDPR compliance
│   ├── routes/
│   │   ├── index.js              # Route aggregator
│   │   ├── auth.js               # /auth routes
│   │   ├── public.js             # /public routes
│   │   ├── user.js               # /user routes
│   │   ├── community.js          # /community routes
│   │   ├── admin.js              # /admin routes
│   │   ├── superadmin.js         # /superadmin routes
│   │   ├── marketplace.js        # /marketplace routes
│   │   └── music.js              # /music routes
│   ├── services/
│   │   ├── storageService.js     # S3/file storage
│   │   ├── broadcastService.js   # Cross-platform messaging
│   │   ├── platformPermissionService.js # Platform permissions
│   │   └── cookieConsentService.js # Cookie consent
│   ├── websocket/
│   │   ├── index.js              # Socket.io setup
│   │   └── chatHandler.js        # Chat event handlers
│   ├── utils/
│   │   ├── logger.js             # Structured logging
│   │   ├── db.js                 # Database utilities
│   │   ├── errors.js             # Custom error classes
│   │   ├── email.js              # Email sending
│   │   ├── reputation.js         # FICO scoring
│   │   └── certificates.js       # SSL cert management
│   └── index.js                  # Application entry point
├── package.json
└── .env.example
```

### Request Flow

```
1. HTTP Request
   ↓
2. Express Middleware Chain
   ├─ CORS
   ├─ Helmet (Security Headers)
   ├─ Rate Limiting
   ├─ Body Parsing
   ├─ Cookie Parsing
   ├─ XSS Sanitization
   └─ CSRF Verification
   ↓
3. Router (URL Matching)
   ↓
4. Authentication Middleware
   ├─ Verify JWT Token
   ├─ Decode User Claims
   └─ Attach User to Request
   ↓
5. Authorization Middleware
   ├─ Check User Role
   ├─ Verify Community Membership
   └─ Validate Permissions
   ↓
6. Validation Middleware
   ├─ Validate Request Body
   ├─ Validate Query Params
   └─ Validate Path Params
   ↓
7. Controller
   ├─ Business Logic
   ├─ Database Queries
   ├─ Service Calls
   └─ Response Formatting
   ↓
8. Response
   ├─ JSON Serialization
   ├─ HTTP Status Code
   └─ Headers
```

### Core Modules

#### 1. Authentication System

**File:** `/src/controllers/authController.js`

```javascript
// Unified authentication system
- Local email/password authentication
- OAuth integration (Discord, Twitch, YouTube, KICK, Slack)
- JWT token generation and validation
- Session management
- Email verification
- Temporary password system
```

**Features:**
- Bcrypt password hashing (12 rounds)
- JWT tokens with 1-hour expiration
- Refresh token support
- OAuth platform linking
- Primary identity management

#### 2. Community Management

**File:** `/src/controllers/communityController.js`

```javascript
// Community lifecycle management
- Community creation (SuperAdmin)
- Join requests and approval
- Member management
- Server linking (Discord, Slack)
- Activity tracking
- Leaderboards
```

#### 3. Module System

**File:** `/src/controllers/marketplaceController.js`

```javascript
// Module marketplace and installation
- Module registry
- Module installation/uninstallation
- Module configuration
- Module reviews and ratings
```

#### 4. Admin Dashboard

**File:** `/src/controllers/adminController.js`

```javascript
// Community admin features (475+ lines)
- Community settings
- Member role management
- Reputation adjustment (FICO-style)
- Join request approval
- Server link management
- Mirror group configuration
- Browser source tokens
- Custom domains
- Bot detection review
- AI insights access
```

### Database Layer

**File:** `/src/config/database.js`

```javascript
import pg from 'pg';
const { Pool } = pg;

// Connection pool with automatic retry
const pool = new Pool({
  connectionString: config.database.url,
  max: config.database.poolSize,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
  statement_timeout: 30000,
});

// Helper functions
export async function query(text, params) {
  const start = Date.now();
  const res = await pool.query(text, params);
  const duration = Date.now() - start;
  logger.db('Query executed', { duration, rows: res.rowCount });
  return res;
}

export async function getClient() {
  const client = await pool.connect();
  return client;
}

export async function checkConnection() {
  try {
    await query('SELECT 1');
    return true;
  } catch (err) {
    logger.error('Database connection check failed', { error: err.message });
    return false;
  }
}
```

---

## Frontend Architecture

### Directory Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── ChatChannelList.jsx
│   │   │   ├── ChatInput.jsx
│   │   │   └── ChatMessage.jsx
│   │   ├── streams/
│   │   │   ├── LiveStreamGrid.jsx
│   │   │   ├── LiveStreamCard.jsx
│   │   │   └── TwitchEmbed.jsx
│   │   ├── workflow/
│   │   │   ├── WorkflowNodePalette.jsx
│   │   │   ├── WorkflowPropertiesPanel.jsx
│   │   │   ├── WorkflowSidebar.jsx
│   │   │   └── nodes/
│   │   │       ├── TriggerNode.jsx
│   │   │       ├── ActionNode.jsx
│   │   │       ├── ConditionNode.jsx
│   │   │       └── ...
│   │   ├── settings/
│   │   │   └── LinkedAccountCard.jsx
│   │   ├── leaderboard/
│   │   │   └── LeaderboardCard.jsx
│   │   ├── BotScoreCard.jsx
│   │   ├── BotScoreBadge.jsx
│   │   ├── AnnouncementModal.jsx
│   │   ├── CookieBanner.jsx
│   │   └── CommunityTypeBadge.jsx
│   ├── contexts/
│   │   ├── AuthContext.jsx           # Authentication state
│   │   ├── SocketContext.jsx         # WebSocket connection
│   │   └── CookieConsentContext.jsx  # GDPR consent
│   ├── layouts/
│   │   ├── PublicLayout.jsx          # Public pages layout
│   │   ├── DashboardLayout.jsx       # User dashboard layout
│   │   └── AdminLayout.jsx           # Admin panel layout
│   ├── pages/
│   │   ├── public/
│   │   │   ├── HomePage.jsx
│   │   │   ├── CommunitiesPage.jsx
│   │   │   ├── CommunityPublicPage.jsx
│   │   │   ├── LiveStreamsPage.jsx
│   │   │   └── UserPublicProfile.jsx
│   │   ├── auth/
│   │   │   ├── LoginPage.jsx
│   │   │   └── OAuthCallback.jsx
│   │   ├── dashboard/
│   │   │   ├── DashboardHome.jsx
│   │   │   ├── CommunityDashboard.jsx
│   │   │   ├── CommunitySettings.jsx
│   │   │   ├── CommunityChat.jsx
│   │   │   ├── CommunityLeaderboard.jsx
│   │   │   ├── CommunityMembers.jsx
│   │   │   ├── AccountSettings.jsx
│   │   │   └── UserProfileEdit.jsx
│   │   ├── admin/
│   │   │   ├── AdminHome.jsx
│   │   │   ├── AdminMembers.jsx
│   │   │   ├── AdminWorkflows.jsx
│   │   │   ├── AdminModules.jsx
│   │   │   ├── AdminMarketplace.jsx
│   │   │   ├── AdminStreamOverlays.jsx
│   │   │   ├── AdminDomains.jsx
│   │   │   ├── AdminServers.jsx
│   │   │   ├── AdminConnectedPlatforms.jsx
│   │   │   ├── AdminMirrorGroups.jsx
│   │   │   ├── AdminLeaderboardConfig.jsx
│   │   │   ├── AdminCommunityProfile.jsx
│   │   │   ├── ReputationSettings.jsx
│   │   │   ├── AdminAIInsights.jsx
│   │   │   ├── AdminAIResearcherConfig.jsx
│   │   │   ├── AdminBotDetection.jsx
│   │   │   ├── AdminAnnouncements.jsx
│   │   │   ├── AdminShoutouts.jsx
│   │   │   ├── AdminTranslation.jsx
│   │   │   ├── AdminAnalytics.jsx
│   │   │   ├── AdminSecurity.jsx
│   │   │   ├── LoyaltySettings.jsx
│   │   │   ├── LoyaltyLeaderboard.jsx
│   │   │   ├── LoyaltyGiveaways.jsx
│   │   │   ├── LoyaltyGames.jsx
│   │   │   ├── LoyaltyGear.jsx
│   │   │   ├── AdminMusicDashboard.jsx
│   │   │   ├── AdminMusicSettings.jsx
│   │   │   ├── AdminMusicProviders.jsx
│   │   │   └── AdminRadioStations.jsx
│   │   ├── superadmin/
│   │   │   ├── SuperAdminDashboard.jsx
│   │   │   ├── SuperAdminCommunities.jsx
│   │   │   ├── SuperAdminCreateCommunity.jsx
│   │   │   ├── SuperAdminModuleRegistry.jsx
│   │   │   └── SuperAdminPlatformConfig.jsx
│   │   └── platform/
│   │       ├── PlatformDashboard.jsx
│   │       ├── PlatformUsers.jsx
│   │       └── PlatformCommunities.jsx
│   ├── services/
│   │   └── api.js                    # Axios client and API helpers
│   ├── hooks/
│   │   └── useCookieConsent.js
│   ├── App.jsx                       # Root component and routing
│   ├── main.jsx                      # React entry point
│   └── index.css                     # TailwindCSS
├── public/
│   └── waddle.svg
├── package.json
├── vite.config.js
└── tailwind.config.js
```

### React Router Configuration

**File:** `/src/App.jsx`

```javascript
function App() {
  return (
    <Routes>
      {/* Public routes (no auth) */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/communities" element={<CommunitiesPage />} />
        <Route path="/login" element={<LoginPage />} />
      </Route>

      {/* Dashboard routes (requires auth) */}
      <Route element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<DashboardHome />} />
        <Route path="/dashboard/community/:id" element={<CommunityDashboard />} />
      </Route>

      {/* Admin routes (requires community admin) */}
      <Route element={<ProtectedRoute requireAdmin><AdminLayout /></ProtectedRoute>}>
        <Route path="/admin/:communityId" element={<AdminHome />} />
        <Route path="/admin/:communityId/members" element={<AdminMembers />} />
        {/* ... 30+ admin routes ... */}
      </Route>

      {/* SuperAdmin routes (requires super_admin role) */}
      <Route element={<ProtectedRoute requireSuperAdmin><DashboardLayout /></ProtectedRoute>}>
        <Route path="/superadmin" element={<SuperAdminDashboard />} />
        <Route path="/superadmin/communities" element={<SuperAdminCommunities />} />
      </Route>
    </Routes>
  );
}
```

### State Management

#### AuthContext

**File:** `/src/contexts/AuthContext.jsx`

```javascript
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Fetch current user on mount
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      api.get('/api/v1/auth/me')
        .then(res => setUser(res.data.user))
        .catch(() => localStorage.removeItem('token'))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const res = await api.post('/api/v1/auth/login', { email, password });
    localStorage.setItem('token', res.data.token);
    setUser(res.data.user);
  };

  const logout = () => {
    api.post('/api/v1/auth/logout');
    localStorage.removeItem('token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isSuperAdmin: user?.isSuperAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}
```

#### SocketContext

**File:** `/src/contexts/SocketContext.jsx`

```javascript
export function SocketProvider({ children }) {
  const [socket, setSocket] = useState(null);
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      const token = localStorage.getItem('token');
      const newSocket = io('http://localhost:8060', {
        auth: { token }
      });

      setSocket(newSocket);

      return () => newSocket.close();
    }
  }, [user]);

  return (
    <SocketContext.Provider value={socket}>
      {children}
    </SocketContext.Provider>
  );
}
```

### API Service Layer

**File:** `/src/services/api.js`

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 30000,
});

// Request interceptor (add auth token)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor (handle 401, refresh token)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;
      const response = await api.post('/api/v1/auth/refresh');
      localStorage.setItem('token', response.data.token);
      error.config.headers.Authorization = `Bearer ${response.data.token}`;
      return api(error.config);
    }
    return Promise.reject(error);
  }
);

export default api;
```

---

## Database Architecture

### Entity Relationship Diagram

```
┌─────────────────┐      ┌──────────────────────┐
│   hub_users     │──┬──<│ hub_user_identities  │
│  - id (PK)      │  │   │  - id (PK)           │
│  - email        │  │   │  - hub_user_id (FK)  │
│  - username     │  │   │  - platform          │
│  - password_hash│  │   │  - platform_user_id  │
│  - is_super_admin│ │   │  - is_primary        │
└─────────────────┘  │   └──────────────────────┘
        │            │
        │            │   ┌──────────────────────┐
        └────────────┴──<│ community_members    │
                         │  - id (PK)           │
                         │  - community_id (FK) │
                         │  - user_id           │
                         │  - role              │
                         │  - reputation        │
                         └──────────────────────┘
                                  │
                                  │
┌──────────────────┐             │
│   communities    │<────────────┘
│  - id (PK)       │
│  - name (UNIQUE) │      ┌──────────────────────────┐
│  - display_name  │──┬──<│ hub_module_installations │
│  - platform      │  │   │  - id (PK)               │
│  - is_public     │  │   │  - community_id (FK)     │
│  - config (JSONB)│  │   │  - module_id (FK)        │
└──────────────────┘  │   │  - config (JSONB)        │
        │             │   │  - is_enabled            │
        │             │   └──────────────────────────┘
        │             │
        │             │   ┌──────────────────────────┐
        │             ├──<│ announcements            │
        │             │   │  - id (PK)               │
        │             │   │  - community_id (FK)     │
        │             │   │  - title                 │
        │             │   │  - content               │
        │             │   │  - status                │
        │             │   │  - is_pinned             │
        │             │   └──────────────────────────┘
        │             │
        │             │   ┌──────────────────────────┐
        │             └──<│ analytics_bot_scores     │
        │                 │  - id (PK)               │
        │                 │  - community_id (FK)     │
        │                 │  - score (0-100)         │
        │                 │  - grade (A-F)           │
        │                 │  - suspected_bot_count   │
        │                 └──────────────────────────┘
        │
        │                 ┌──────────────────────────┐
        └────────────────<│ hub_chat_messages        │
                          │  - id (PK)               │
                          │  - community_id          │
                          │  - sender_hub_user_id    │
                          │  - sender_username       │
                          │  - message_content       │
                          │  - created_at            │
                          └──────────────────────────┘

┌──────────────────┐
│   hub_modules    │
│  - id (PK)       │
│  - name (UNIQUE) │
│  - version       │
│  - is_published  │
│  - is_core       │
│  - config_schema │
└──────────────────┘
```

### Key Tables

#### hub_users
Primary user accounts (unified authentication).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| email | VARCHAR(255) | Email address |
| username | VARCHAR(255) | Username |
| password_hash | VARCHAR(255) | Bcrypt hash |
| is_super_admin | BOOLEAN | Platform admin flag |
| email_verified | BOOLEAN | Email verification status |
| created_at | TIMESTAMP | Account creation |

#### communities
Community/server definitions.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| name | VARCHAR(255) | Unique slug |
| display_name | VARCHAR(255) | Display name |
| platform | VARCHAR(50) | Primary platform (discord/twitch/etc) |
| is_public | BOOLEAN | Public visibility |
| config | JSONB | Community configuration |
| owner_id | VARCHAR(255) | Owner user ID |
| member_count | INTEGER | Cached member count |

#### community_members
User membership in communities.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| community_id | INTEGER | FK to communities |
| user_id | VARCHAR(255) | User identifier |
| platform | VARCHAR(50) | Platform |
| role | VARCHAR(50) | admin/moderator/member |
| reputation | INTEGER | FICO-style score (300-850) |
| joined_at | TIMESTAMP | Join timestamp |

---

## Authentication & Authorization

### Authentication Flow

```
┌────────┐          ┌────────┐           ┌──────────┐
│ Client │          │  Hub   │           │ Identity │
│        │          │ Backend│           │   Core   │
└───┬────┘          └───┬────┘           └────┬─────┘
    │                   │                     │
    │  POST /auth/login │                     │
    │──────────────────>│                     │
    │                   │                     │
    │   Verify password │                     │
    │<──────────────────│                     │
    │                   │                     │
    │    JWT token      │                     │
    │<──────────────────│                     │
    │                   │                     │
    │  GET /communities │                     │
    │  + JWT in header  │                     │
    │──────────────────>│                     │
    │                   │                     │
    │   Verify JWT      │                     │
    │<──────────────────│                     │
    │                   │                     │
    │   Response        │                     │
    │<──────────────────│                     │
```

### OAuth Flow

```
┌────────┐    ┌────────┐    ┌──────────┐    ┌──────────┐
│ Client │    │  Hub   │    │ Identity │    │ Platform │
│        │    │Backend │    │   Core   │    │  (OAuth) │
└───┬────┘    └───┬────┘    └────┬─────┘    └────┬─────┘
    │             │              │               │
    │ GET /auth/oauth/discord    │               │
    │────────────>│              │               │
    │             │              │               │
    │  Redirect to Discord       │               │
    │<────────────│              │               │
    │             │              │               │
    │  User approves             │               │
    │────────────────────────────────────────────>│
    │             │              │               │
    │  Callback with code        │               │
    │<────────────────────────────────────────────│
    │             │              │               │
    │ POST /auth/oauth/discord/callback          │
    │────────────>│              │               │
    │             │              │               │
    │             │ Exchange code│               │
    │             │─────────────>│               │
    │             │              │               │
    │             │ Get user info│               │
    │             │<─────────────│               │
    │             │              │               │
    │   JWT token │              │               │
    │<────────────│              │               │
```

### Authorization Levels

| Level | Description | Access |
|-------|-------------|--------|
| **Public** | No authentication | Public endpoints only |
| **User** | Authenticated user | Own profile, public communities |
| **Member** | Community member | Community dashboard, chat |
| **Moderator** | Community moderator | Member management (limited) |
| **Admin** | Community admin | Full community control |
| **Platform Admin** | Platform administrator | Cross-community oversight |
| **Super Admin** | Platform owner | All communities, system config |

---

## Real-time Communication

### WebSocket Architecture

**File:** `/src/websocket/index.js`

```javascript
export function setupWebSocket(httpServer) {
  const io = new Server(httpServer, {
    cors: {
      origin: config.cors.origin,
      credentials: true,
    },
    transports: ['websocket', 'polling'],
    pingTimeout: 60000,
    pingInterval: 25000,
  });

  // Authentication middleware
  io.use(async (socket, next) => {
    const token = socket.handshake.auth.token;
    if (!token) return next(new Error('Authentication required'));

    const decoded = jwt.verify(token, config.jwt.secret);
    socket.userId = decoded.userId;
    socket.username = decoded.username;
    next();
  });

  // Connection handling
  io.on('connection', (socket) => {
    // Chat events
    socket.on('join-channel', ({ communityId, channelName }) => {
      socket.join(`community:${communityId}:${channelName}`);
    });

    socket.on('send-message', async ({ communityId, channelName, content }) => {
      const message = {
        username: socket.username,
        content,
        timestamp: new Date().toISOString(),
      };

      // Broadcast to channel
      io.to(`community:${communityId}:${channelName}`).emit('new-message', message);

      // Save to database
      await saveMessage(communityId, channelName, socket.userId, content);
    });
  });

  return io;
}
```

### Chat Event Flow

```
Client A                    Server                    Client B
   │                          │                          │
   │  join-channel            │                          │
   │─────────────────────────>│                          │
   │                          │                          │
   │  Joined: community:1:general                        │
   │<─────────────────────────│                          │
   │                          │                          │
   │  send-message            │                          │
   │─────────────────────────>│                          │
   │                          │                          │
   │                  Save to database                   │
   │                          │                          │
   │                  Broadcast to room                  │
   │                          │───────────────────────────>│
   │  new-message             │  new-message              │
   │<─────────────────────────│                          │
```

---

## Module System

### Module Installation Flow

```
1. Admin browses marketplace
   GET /api/v1/admin/:communityId/marketplace/modules
   └─> Returns available modules

2. Admin installs module
   POST /api/v1/admin/:communityId/marketplace/modules/:id/install
   └─> Creates installation record in database

3. Module configuration
   PUT /api/v1/admin/:communityId/modules/:moduleId/config
   └─> Updates module config (JSONB)

4. Module activation
   └─> Module becomes available in community
```

### Module Registry Schema

```sql
CREATE TABLE hub_modules (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) UNIQUE NOT NULL,
  display_name VARCHAR(255),
  description TEXT,
  version VARCHAR(50),
  author VARCHAR(255),
  category VARCHAR(100),
  is_published BOOLEAN DEFAULT false,
  is_core BOOLEAN DEFAULT false,
  config_schema JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## API Gateway Pattern

The Hub Module acts as an API gateway, proxying requests to internal microservices:

### Analytics Proxy Example

```javascript
router.get('/:communityId/analytics/*', requireCommunityAdmin, async (req, res) => {
  const analyticsPath = req.params[0];
  const response = await httpClient.get(
    `http://analytics-core:8040/api/v1/analytics/${req.params.communityId}/${analyticsPath}`,
    {
      params: req.query,
      headers: {
        'X-API-Key': req.headers['x-api-key'],
        'X-Community-ID': req.params.communityId,
      },
    }
  );
  res.json(response.data);
});
```

### Security Proxy Example

```javascript
router.put('/:communityId/security/*', requireCommunityAdmin, async (req, res) => {
  const securityPath = req.params[0];
  const response = await httpClient.put(
    `http://security-core:8041/api/v1/security/${req.params.communityId}/${securityPath}`,
    req.body,
    {
      headers: {
        'X-API-Key': req.headers['x-api-key'],
        'X-Community-ID': req.params.communityId,
      },
    }
  );
  res.json(response.data);
});
```

---

## Security Architecture

### Layered Security

```
┌────────────────────────────────────────────┐
│  1. Network Layer (HTTPS, WSS)             │
├────────────────────────────────────────────┤
│  2. Rate Limiting (100 req/min)            │
├────────────────────────────────────────────┤
│  3. CORS Policy                            │
├────────────────────────────────────────────┤
│  4. Helmet Security Headers                │
├────────────────────────────────────────────┤
│  5. XSS Sanitization                       │
├────────────────────────────────────────────┤
│  6. CSRF Protection                        │
├────────────────────────────────────────────┤
│  7. JWT Authentication                     │
├────────────────────────────────────────────┤
│  8. Role-Based Authorization               │
├────────────────────────────────────────────┤
│  9. Input Validation                       │
├────────────────────────────────────────────┤
│  10. SQL Injection Prevention (Parameterized)│
└────────────────────────────────────────────┘
```

---

## Deployment Architecture

### Docker Multi-Stage Build

```dockerfile
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY admin/hub_module/frontend/ ./
RUN npm install && npm run build

# Stage 2: Production runtime
FROM node:20-alpine
WORKDIR /app
COPY admin/hub_module/backend/ ./
RUN npm install --only=production
COPY --from=frontend-build /app/frontend/dist ./public
CMD ["node", "src/index.js"]
```

### Production Deployment

```
┌──────────────────────────────────────────────┐
│              Load Balancer / CDN             │
│         (Kubernetes Ingress/HTTPRoute)       │
└──────────────┬───────────────────────────────┘
               │
         HTTPS │
               ▼
┌──────────────────────────────────────────────┐
│          Hub Module Instances                │
│     (Docker containers, scaled 3x)           │
│  ┌──────┐  ┌──────┐  ┌──────┐               │
│  │ Hub1 │  │ Hub2 │  │ Hub3 │               │
│  └──┬───┘  └──┬───┘  └──┬───┘               │
└─────┼─────────┼────────┼────────────────────┘
      │         │        │
      └────┬────┴────┬───┘
           │         │
           ▼         ▼
    ┌──────────┐  ┌─────────────┐
    │PostgreSQL│  │   Redis     │
    │  (RDS)   │  │  (Session)  │
    └──────────┘  └─────────────┘
```

---

## Performance Considerations

1. **Database Connection Pooling:** Max 10-20 connections per instance
2. **Caching:** Redis for session storage, community metadata
3. **Static Assets:** Served via CDN in production
4. **WebSocket Scaling:** Sticky sessions or Redis adapter
5. **Query Optimization:** Indexes on frequently queried columns
6. **Rate Limiting:** Prevent API abuse
7. **Lazy Loading:** Frontend code splitting
8. **Image Optimization:** Compressed avatars/banners

---

## Monitoring & Observability

### Health Endpoints

- `GET /health` - Basic health check
- `GET /metrics` - Application metrics (uptime, memory, DB pool)

### Logging

Structured JSON logging with levels:
- `debug` - Development only
- `info` - General information
- `warn` - Warning conditions
- `error` - Error conditions

### Metrics

- Request count by endpoint
- Response time percentiles (p50, p95, p99)
- Database query duration
- WebSocket connection count
- Error rate by type

---

## Conclusion

The Hub Module is a well-architected full-stack application with clear separation of concerns, comprehensive security, and scalable design patterns. Its role as an API gateway enables seamless integration with the broader Waddles ecosystem.
