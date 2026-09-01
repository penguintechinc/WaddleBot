# Loyalty Interaction Module — Usage Guide

Complete guide for deploying, configuring, and using the Loyalty Interaction Module.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Docker Deployment](#docker-deployment)
3. [Health Checks](#health-checks)
4. [Real-World Workflows](#real-world-workflows)
5. [Chat Commands](#chat-commands)
6. [Common Operations](#common-operations)
7. [Error Handling](#error-handling)

## Prerequisites

- Docker (recommended) or Python 3.13+
- PostgreSQL 12+ or SQLite
- Redis 6+ (optional, for caching)
- Community ID (integer from admin system)
- User IDs (platform-specific: Twitch username, Discord user ID, etc.)

## Docker Deployment

### Quick Start

```bash
# Pull the image
docker pull waddlebot/loyalty:latest

# Run with default settings
docker run -d \
  --name loyalty-module \
  -p 8032:8032 \
  -e DATABASE_URL="postgresql://user:password@postgres:5432/waddlebot" \
  -e REDIS_URL="redis://redis:6379" \
  -e MODULE_PORT=8032 \
  -e DEFAULT_EARN_CHAT=1 \
  -e MIN_BET=10 \
  -e MAX_BET=10000 \
  waddlebot/loyalty:latest
```

### Environment Variables

```bash
# Core
MODULE_PORT=8032
DATABASE_URL=postgresql://waddlebot:secret@localhost:5432/waddlebot

# Optional caching
REDIS_URL=redis://localhost:6379

# Service integration
ROUTER_API_URL=http://router:8000
REPUTATION_API_URL=http://reputation:8021
SERVICE_API_KEY=your-api-key-here

# Earning defaults
DEFAULT_EARN_CHAT=1                    # Points per message
DEFAULT_EARN_CHAT_COOLDOWN=60          # Seconds between earnings
DEFAULT_EARN_WATCH_TIME=2              # Points per interval
DEFAULT_EARN_FOLLOW=50                 # Points for follow
DEFAULT_EARN_SUB_T1=500                # Tier 1 subscription
DEFAULT_EARN_SUB_T2=1000               # Tier 2 subscription
DEFAULT_EARN_SUB_T3=2500               # Tier 3 subscription

# Gambling
MIN_BET=10
MAX_BET=10000

# Giveaway
GIVEAWAY_REPUTATION_FLOOR=450

# Duels
DUEL_TIMEOUT_MINUTES=5
```

### Docker Compose

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: waddlebot
      POSTGRES_PASSWORD: waddlebot_secret
      POSTGRES_DB: waddlebot
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  loyalty:
    image: waddlebot/loyalty:latest
    ports:
      - "8032:8032"
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://waddlebot:waddlebot_secret@postgres:5432/waddlebot
      REDIS_URL: redis://redis:6379
      MODULE_PORT: 8032
    command: python -m app

volumes:
  postgres_data:
```

## Health Checks

### Module Status

```bash
curl http://localhost:8032/

# Response:
# {
#   "module": "loyalty_interaction_module",
#   "version": "1.0.0",
#   "status": "operational",
#   "features": ["currency_management", "earning_config", "giveaways", ...],
#   "endpoints": {...}
# }
```

### Health Endpoint

```bash
curl http://localhost:8032/health

# Response:
# {
#   "status": "healthy",
#   "timestamp": "2026-02-16T10:30:00Z"
# }
```

### Readiness Check

```bash
curl http://localhost:8032/ready

# Response: 200 OK when database is connected
```

## Real-World Workflows

### Workflow 1: User Earning Points from Chat

**Scenario:** User sends chat message, system automatically awards loyalty points.

```bash
# 1. Chat message event arrives
curl -X POST http://localhost:8032/api/v1/loyalty/earning/1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "streamer123",
    "platform": "twitch"
  }'

# Response:
# {
#   "earned": true,
#   "amount": 1,
#   "new_balance": 42,
#   "message": "Earned 1 point!"
# }

# 2. User checks balance
curl http://localhost:8032/api/v1/loyalty/currency/1/balance/streamer123?platform=twitch

# Response:
# {
#   "success": true,
#   "data": {
#     "balance": 42,
#     "lifetime_earned": 150,
#     "lifetime_spent": 108
#   }
# }
```

### Workflow 2: User Subscribes, Earns Bonus Points

**Scenario:** User subscribes to channel, automatically awarded subscription bonus.

```bash
# 1. Subscribe event
curl -X POST http://localhost:8032/api/v1/loyalty/earning/1/event \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "subscriber456",
    "event_type": "sub_t2",
    "event_data": {
      "tier": 2,
      "gifted": false
    },
    "platform": "twitch"
  }'

# Response:
# {
#   "earned": true,
#   "amount": 1000,
#   "new_balance": 1500,
#   "message": "Earned 1000 points for Tier 2 subscription!"
# }
```

### Workflow 3: User Plays Minigame

**Scenario:** User plays slots with 50 point bet.

```bash
# 1. Play slots
curl -X POST http://localhost:8032/api/v1/loyalty/games/1/slots \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "user_id": "gambler789",
    "bet": 50,
    "platform": "twitch"
  }'

# Response (Win):
# {
#   "success": true,
#   "symbols": ["cherry", "cherry", "cherry"],
#   "won": true,
#   "winnings": 150,
#   "new_balance": 350,
#   "message": "JACKPOT! Three cherries! Won 150 points!"
# }

# Response (Loss):
# {
#   "success": true,
#   "symbols": ["bar", "lemon", "bell"],
#   "won": false,
#   "winnings": 0,
#   "new_balance": 200,
#   "message": "No match. Better luck next time!"
# }
```

### Workflow 4: Creating a Giveaway

**Scenario:** Streamer creates giveaway with 100 point entry, reputation weighting.

```bash
# 1. Create giveaway
curl -X POST http://localhost:8032/api/v1/loyalty/giveaways/1 \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "title": "Valentine's Day Gift Pack",
    "prize": "50 USD Steam Gift Card",
    "entry_cost": 100,
    "duration_minutes": 120,
    "max_entries": 500,
    "reputation_weighted": true
  }'

# Response:
# {
#   "success": true,
#   "data": {
#     "giveaway_id": 42,
#     "title": "Valentine's Day Gift Pack",
#     "prize": "50 USD Steam Gift Card",
#     "status": "active",
#     "ends_at": "2026-02-16T12:30:00Z"
#   }
# }

# 2. User enters giveaway
curl -X POST http://localhost:8032/api/v1/loyalty/giveaways/1/42/enter \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "giveaway_id": 42,
    "user_id": "participant999",
    "platform": "twitch"
  }'

# Response:
# {
#   "success": true,
#   "message": "Entered giveaway! Good luck!",
#   "entry_number": 47
# }

# 3. Draw winner (after expiration or manually)
curl -X POST http://localhost:8032/api/v1/loyalty/giveaways/1/42/draw \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d '{}'

# Response:
# {
#   "success": true,
#   "winner_user_id": "lucky_viewer",
#   "message": "Winner drawn! Congratulations lucky_viewer!"
# }
```

### Workflow 5: Player vs Player Duel

**Scenario:** Two users challenge each other in duel with 100 point wager.

```bash
# 1. Player A challenges Player B
curl -X POST http://localhost:8032/api/v1/loyalty/duels/1/challenge \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "challenger_id": "player_a",
    "opponent_id": "player_b",
    "wager": 100,
    "platform": "twitch"
  }'

# Response:
# {
#   "success": true,
#   "duel_id": 99,
#   "message": "Challenge created! Waiting for player_b to accept..."
# }

# 2. Player B accepts (can also decline)
curl -X POST http://localhost:8032/api/v1/loyalty/duels/1/accept \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "duel_id": 99,
    "platform": "twitch"
  }'

# Response:
# {
#   "success": true,
#   "winner_id": "player_a",
#   "loser_id": "player_b",
#   "winnings": 200,
#   "message": "Duel complete! player_a wins 200 points!"
# }

# 3. Check pending duels
curl http://localhost:8032/api/v1/loyalty/duels/1/pending/player_b?platform=twitch

# Response:
# {
#   "success": true,
#   "data": {
#     "pending_duels": [
#       {
#         "duel_id": 99,
#         "challenger_id": "player_a",
#         "opponent_id": "player_b",
#         "wager": 100,
#         "created_at": "2026-02-16T10:00:00Z"
#       }
#     ]
#   }
# }
```

### Workflow 6: Gear Shop Purchase

**Scenario:** User purchases cosmetic equipment with stat bonuses.

```bash
# 1. Browse shop
curl http://localhost:8032/api/v1/loyalty/gear/1/shop?category=weapons

# Response:
# {
#   "success": true,
#   "data": {
#     "items": [
#       {
#         "item_id": 1,
#         "name": "Iron Sword",
#         "description": "Basic melee weapon",
#         "category": "weapons",
#         "price": 500,
#         "stat_bonus": {"damage": 10},
#         "available": true
#       },
#       {
#         "item_id": 2,
#         "name": "Diamond Sword",
#         "description": "Legendary melee weapon",
#         "category": "weapons",
#         "price": 5000,
#         "stat_bonus": {"damage": 50},
#         "available": true
#       }
#     ]
#   }
# }

# 2. Purchase item
curl -X POST http://localhost:8032/api/v1/loyalty/gear/1/buy \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "user_id": "collector",
    "item_id": 1,
    "platform": "twitch"
  }'

# Response:
# {
#   "success": true,
#   "message": "Purchased Iron Sword for 500 points!",
#   "new_balance": 1500
# }

# 3. Equip item
curl -X POST http://localhost:8032/api/v1/loyalty/gear/1/equip \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "user_id": "collector",
    "item_id": 1,
    "platform": "twitch"
  }'

# Response:
# {
#   "success": true,
#   "message": "Item equipped successfully!"
# }

# 4. View equipped gear and bonuses
curl http://localhost:8032/api/v1/loyalty/gear/1/equipped/collector?platform=twitch

# Response:
# {
#   "success": true,
#   "data": {
#     "equipped_items": [
#       {
#         "item_id": 1,
#         "name": "Iron Sword",
#         "category": "weapons",
#         "stat_bonus": {"damage": 10}
#       }
#     ],
#     "total_stats": {"damage": 10}
#   }
# }
```

## Chat Commands

The module supports chat commands via the command endpoint. Users can interact via chat messages:

### Available Commands

```
!balance, !bal              Check current balance and lifetime stats
!gamble <amount>            Play slots game
!coinflip <h|t> <amount>   Flip coin (heads/tails)
!roulette <type> <amount>   Play roulette (red/black/odd/even/etc.)
!duel @opponent <amount>    Challenge another user
!gear                       View inventory
!gear shop                  Browse gear shop
!leaderboard [limit]        View top earners (default 10)
```

### Example Command Flow

```bash
# User sends: !balance
# System routes to command endpoint:
curl -X POST http://localhost:8032/api/v1/loyalty/command \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session123",
    "command": "balance",
    "args": [],
    "user_id": "streamer123",
    "community_id": 1,
    "platform": "twitch"
  }'

# Response:
# {
#   "success": true,
#   "data": {
#     "session_id": "session123",
#     "response_action": "chat",
#     "response_data": {
#       "message": "Balance: 2500 | Earned: 10000 | Spent: 7500"
#     }
#   }
# }
```

## Common Operations

### Update Earning Configuration

```bash
# Customize earning rates for community
curl -X PUT http://localhost:8032/api/v1/loyalty/config/1 \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "earn_chat": 2,
    "earn_follow": 100,
    "earn_sub_t2": 2000,
    "earn_raid_per_viewer": 1,
    "earn_cheer_per_bit": 0.5
  }'

# Response:
# {
#   "success": true,
#   "message": "Configuration updated"
# }
```

### Get Leaderboard

```bash
# Top 10 by balance
curl http://localhost:8032/api/v1/loyalty/currency/1/leaderboard?limit=10&platform=twitch

# Response:
# {
#   "success": true,
#   "data": {
#     "leaderboard": [
#       {"rank": 1, "user_id": "tycoon", "balance": 50000, "lifetime_earned": 80000},
#       {"rank": 2, "user_id": "grinder", "balance": 45000, "lifetime_earned": 75000},
#       {"rank": 3, "user_id": "luckster", "balance": 40000, "lifetime_earned": 60000}
#     ]
#   }
# }
```

### Admin: Set User Balance

```bash
# Directly set balance (admin only)
curl -X PUT http://localhost:8032/api/v1/loyalty/currency/1/balance/user123 \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "user_id": "user123",
    "balance": 10000,
    "platform": "twitch"
  }'

# Response:
# {
#   "success": true,
#   "new_balance": 10000,
#   "message": "Balance set to 10000"
# }
```

### Admin: Wipe All Balances

```bash
# DANGER: Resets all balances to zero for community
curl -X DELETE http://localhost:8032/api/v1/loyalty/currency/1/wipe?platform=twitch \
  -H "Authorization: Bearer admin-token"

# Response:
# {
#   "success": true,
#   "message": "All balances wiped"
# }
```

## Error Handling

### Common HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Balance retrieved |
| 400 | Bad request | Invalid bet amount |
| 401 | Unauthorized | Missing auth token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not found | User/giveaway doesn't exist |
| 500 | Server error | Database connection failed |

### Error Response Format

```json
{
  "success": false,
  "error": "Insufficient balance to place bet",
  "error_code": "INSUFFICIENT_FUNDS",
  "details": {
    "balance": 50,
    "required": 100
  }
}
```

### Common Errors

```
Error: "Insufficient balance"
→ User doesn't have enough points for bet/purchase

Error: "User not found"
→ User hasn't earned any points yet (create zero balance record)

Error: "Bet outside allowed range"
→ Bet must be between MIN_BET and MAX_BET (config defaults: 10-10000)

Error: "Giveaway not active"
→ Giveaway is closed, ended, or cancelled

Error: "Duel timeout expired"
→ Other player didn't respond within DUEL_TIMEOUT_MINUTES
```

## Performance Tuning

### Redis Caching

Enable Redis for faster leaderboard and balance queries:

```bash
# Set Redis URL
export REDIS_URL=redis://redis:6379

# Cache automatically caches:
# - User balances (TTL: 5 minutes)
# - Leaderboards (TTL: 10 minutes)
# - Shop items (TTL: 1 hour)
```

### Database Indexing

Ensure database has these indexes for performance:

```sql
CREATE INDEX idx_loyalty_balances_community ON loyalty_balances(community_id);
CREATE INDEX idx_loyalty_balances_user ON loyalty_balances(community_id, platform_user_id);
CREATE INDEX idx_transactions_community ON loyalty_transactions(community_id);
```

---

**Last Updated:** 2026-02-16
