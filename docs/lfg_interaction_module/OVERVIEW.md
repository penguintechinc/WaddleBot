# LFG Interaction Module - Overview

## Module Purpose

The LFG (Looking-For-Group) Interaction Module is a dedicated microservice that manages the complete lifecycle of looking-for-group posts within gaming communities. It enables users to create and join group-finding posts, automatically manages post expiration and status transitions, and provides real-time filtering and search capabilities.

This module is essential for gaming-focused communities on the Waddlebot platform, streamlining the process of finding teammates, raid partners, or co-op players across Discord, Twitch, and other supported platforms.

## Core Capabilities

### Post Creation & Management
- Users create LFG posts with detailed context (game, activity type, required role, player skill level)
- Posts include player count needs and optional custom messages
- Creators can cancel their posts at any time
- Posts automatically transition to "filled" status when sufficient players join
- Posts automatically expire after a configurable TTL (default: 120 minutes)

### Participant Management
- Users join posts with platform-specific identity information
- System prevents duplicate joins (unique constraint on post_id + user_id)
- Leaving a post automatically decrements player count and may revert "filled" status to "open"
- Platform-aware join tracking (Discord user ID, Twitch username, etc.)

### Intelligent Post Lifecycle
- Auto-detection of filled groups (monitors join count vs. needed count)
- Configurable expiry windows with background job processing
- Status tracking: open → filled/expired/cancelled
- Post filtering by community, game, activity, or search term

## Key Features

- **Per-User Limits**: Maximum 3 active (open/filled) posts per user at any time
- **Game Filtering**: Fast filtering by game title in list operations
- **Auto-Expiry**: Background cron endpoint to clean up stale posts
- **Platform Awareness**: Tracks platform-specific user IDs and display names
- **Status Management**: Clear state transitions (open, filled, expired, cancelled)
- **Unique Join Constraints**: Prevents duplicate participation via database uniqueness

## Architecture at a Glance

```
LFG Interaction Module (Port 8096)
├── Quart Web Framework
├── PostgreSQL Backend (lfg_posts, lfg_joins tables)
├── Redis Cache (optional session/rate-limiting)
├── Async/Await Request Handling
└── REST API (v1 endpoints)
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.12 |
| **Web Framework** | Quart (async, ASGI) |
| **Database** | PostgreSQL (PyDAL abstraction) |
| **Cache** | Redis (optional, for rate-limiting) |
| **Container** | Docker |
| **Port** | 8096 |
| **API Version** | v1 |

## Database Schema

### lfg_posts Table
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| community_id | UUID | Reference to community |
| user_id | UUID | Creator user ID |
| platform | VARCHAR | discord, twitch, youtube, slack, kick |
| game | VARCHAR | Game title (searchable) |
| activity | VARCHAR | raid, pvp, pve, coop, casual, ranked |
| role | VARCHAR | DPS, tank, healer, support, any |
| rank_or_level | VARCHAR | Skill level or in-game rank |
| player_count_needed | INT | Players needed to fill group |
| message | TEXT | Optional custom message |
| platform_message_id | VARCHAR | External platform message reference (optional) |
| status | ENUM | open, filled, expired, cancelled |
| expires_at | TIMESTAMP | Auto-expiry datetime |
| created_at | TIMESTAMP | Creation datetime |

### lfg_joins Table
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| post_id | UUID | FK to lfg_posts |
| user_id | UUID | Participant user ID |
| platform | VARCHAR | discord, twitch, etc. |
| display_name | VARCHAR | User's display name |
| joined_at | TIMESTAMP | Join datetime |
| | UNIQUE(post_id, user_id) | Prevents duplicate joins |

## Integration Points

- **Core API**: License validation, user context, community verification
- **Router API**: Command routing and context-aware message handling
- **Redis**: Session caching and rate-limiting (optional)
- **PostgreSQL**: Persistent storage of posts and joins

## Environment Configuration

All configuration via environment variables:
- `MODULE_PORT=8096` — Service port
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection (optional)
- `CORE_API_URL` — Core API endpoint
- `ROUTER_API_URL` — Router API endpoint
- `LOG_LEVEL=INFO` — Logging level
- `SECRET_KEY` — Session/JWT signing key
- `LFG_DEFAULT_EXPIRY_MINUTES=120` — Post TTL
- `LFG_MAX_ACTIVE_POSTS_PER_USER=3` — Per-user post limit

## Quick Start

1. **Build & Run**: Docker container exposes port 8096
2. **Create Post**: `POST /api/v1/lfg/posts` with game, activity, player count
3. **List Posts**: `GET /api/v1/lfg/posts/{community_id}?game=Valorant`
4. **Join Post**: `POST /api/v1/lfg/posts/{post_id}/join`
5. **Expire Old**: `POST /api/v1/lfg/expire` (background job, hourly)

## Related Documentation

- **[API.md](API.md)** — Complete endpoint reference with examples
- **[USAGE.md](USAGE.md)** — Practical workflows and use cases
- **[CONFIGURATION.md](CONFIGURATION.md)** — Environment setup and tuning
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Internal design and data flow
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — Common issues and solutions
- **[TESTING.md](TESTING.md)** — Test strategy and mock data

## Support & Contributing

For issues, feature requests, or contributions, refer to the main Waddlebot documentation and contribution guidelines. This module is part of the Waddlebot interactive action system.
