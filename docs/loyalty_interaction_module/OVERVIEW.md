# Loyalty Interaction Module — Overview

**Module:** loyalty_interaction_module
**Version:** 1.0.0
**Port:** 8032 (REST API)
**Language:** Python 3.13
**Framework:** Quart (async Flask equivalent)
**Organization:** Penguin Tech Inc

## Purpose

The Loyalty Interaction Module is a comprehensive virtual currency and reward system designed for streaming communities. It enables:

- **Virtual Currency Management** — Earn, spend, transfer, and manage loyalty points
- **Loyalty Rewards System** — Giveaways with reputation-based weighting
- **Minigames** — Engage users with slots, coinflip, and roulette games
- **Player vs Player Duels** — Competitive currency wagering between users
- **Gear/Cosmetics Shop** — Purchase equipment with stat bonuses
- **Leaderboards** — Track top earners and competitors
- **Event-Based Earning** — Automatic points for follows, subs, raids, and cheers

Perfect for Twitch, Discord, Slack, and Kick communities seeking to increase engagement and create economic ecosystems.

## Capabilities

| Feature | Status | Details |
|---------|--------|---------|
| Balance Management | Full | Get, add, remove, transfer, set balances |
| Earning Config | Full | Customize earn rates for all events |
| Giveaways | Full | Create, enter, draw, reputation-weighted |
| Minigames | Full | Slots, Coinflip, Roulette with configurable bets |
| Duels | Full | PvP challenges with currency wagers |
| Gear System | Full | Shop, inventory, equip/unequip items |
| Leaderboards | Full | Sort by balance, earned, wins, etc. |
| Chat Commands | Full | !balance, !gamble, !coinflip, !gear |
| Audit Logging | Full | All transactions logged for compliance |
| Health Checks | Full | Ready, live, and metrics endpoints |

## Quick Reference

### Key Endpoints

| Feature | Endpoint | Method |
|---------|----------|--------|
| Get Balance | `/api/v1/loyalty/currency/{community_id}/balance/{user_id}` | GET |
| Add Currency | `/api/v1/loyalty/currency/{community_id}/add` | POST |
| Transfer | `/api/v1/loyalty/currency/{community_id}/transfer` | POST |
| Leaderboard | `/api/v1/loyalty/currency/{community_id}/leaderboard` | GET |
| Play Slots | `/api/v1/loyalty/games/{community_id}/slots` | POST |
| Play Coinflip | `/api/v1/loyalty/games/{community_id}/coinflip` | POST |
| Create Duel | `/api/v1/loyalty/duels/{community_id}/challenge` | POST |
| Create Giveaway | `/api/v1/loyalty/giveaways/{community_id}` | POST |
| Buy Gear | `/api/v1/loyalty/gear/{community_id}/buy` | POST |

### Configuration Variables

```
MODULE_PORT=8032                           # REST API port
DATABASE_URL=postgresql://...              # PostgreSQL connection
REDIS_URL=redis://localhost:6379           # Redis cache
DEFAULT_EARN_CHAT=1                        # Points per chat message
MIN_BET=10                                 # Minimum game bet
MAX_BET=10000                              # Maximum game bet
DUEL_TIMEOUT_MINUTES=5                     # Duel acceptance timeout
```

### Supported Platforms

- Twitch (default)
- Discord
- Slack
- Kick

## Architecture Highlights

- **Quart Framework** — Fully async Python web framework
- **PyDAL Database** — Abstraction layer supporting PostgreSQL, SQLite, MySQL
- **Redis Caching** — Performance optimization for frequently accessed data
- **JWT Authentication** — Secure admin endpoints
- **Pydantic Validation** — Type-safe request/response handling
- **Audit Logging** — Complete transaction history for compliance

## Documentation Index

| Document | Purpose |
|----------|---------|
| [OVERVIEW.md](OVERVIEW.md) | This file — module purpose and quick reference |
| [USAGE.md](USAGE.md) | Getting started, Docker deployment, real examples |
| [API.md](API.md) | Complete endpoint reference with schemas |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data models, service flow |
| [CONFIGURATION.md](CONFIGURATION.md) | All environment variables, defaults, tuning |
| [TESTING.md](TESTING.md) | Test strategy, fixtures, how to run tests |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues and solutions |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | Version history and changelog |

## Source Code Structure

```
action/interactive/loyalty_interaction_module/
├── app.py                           # Quart app with all endpoints
├── config.py                        # Configuration from env vars
├── validation_models.py             # Pydantic request/response schemas
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Container image definition
├── test-api.sh                      # API testing script
└── services/                        # Service layer
    ├── currency_service.py          # Balance & transfer operations
    ├── earning_config_service.py    # Earning rate configuration
    ├── giveaway_service.py          # Giveaway management
    ├── minigame_service.py          # Slots, coinflip, roulette
    ├── duel_service.py              # PvP duel management
    ├── gear_service.py              # Shop and inventory
    ├── cache_manager.py             # Redis caching layer
    └── simple_games.py              # Game logic implementations
```

## Getting Started

1. **Start Module** → Docker: `docker run -p 8032:8032 waddlebot-loyalty:latest`
2. **Health Check** → `curl http://localhost:8032/health`
3. **Get Balance** → `curl http://localhost:8032/api/v1/loyalty/currency/1/balance/user123?platform=twitch`
4. **Full Guide** → See [USAGE.md](USAGE.md)

## Key Design Decisions

**Async Everything** — All I/O operations are async for high concurrency
**Economic Safety** — Strict validation on all financial operations
**Reputation Integration** — Giveaways can weight by user reputation
**Community Isolation** — All data scoped to community_id
**Audit Trail** — Every transaction logged for compliance
**Platform Agnostic** — Supports Twitch, Discord, Slack, Kick seamlessly

---

**Last Updated:** 2026-02-16
**Maintained by:** Penguin Tech Inc
**License:** Limited AGPL-3.0
