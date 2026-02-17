# Loyalty Interaction Module — Complete API Reference

Full endpoint documentation with request/response schemas, error codes, and examples.

## Base URL

```
http://localhost:8032/api/v1/loyalty
```

All endpoints require:
- `Content-Type: application/json`
- Authentication headers (for admin endpoints)

## Table of Contents

1. [Health Endpoints](#health-endpoints)
2. [Currency Management](#currency-management)
3. [Earning Configuration](#earning-configuration)
4. [Minigames](#minigames)
5. [Duels](#duels)
6. [Giveaways](#giveaways)
7. [Gear System](#gear-system)
8. [Chat Commands](#chat-commands)

---

## Health Endpoints

### GET / or /index

Get module status and available features.

**Request:**
```bash
GET /
```

**Response:**
```json
{
  "success": true,
  "data": {
    "module": "loyalty_interaction_module",
    "version": "1.0.0",
    "status": "operational",
    "features": [
      "currency_management",
      "earning_config",
      "giveaways",
      "minigames",
      "duels",
      "gear_system"
    ],
    "endpoints": {
      "currency": "/api/v1/currency",
      "config": "/api/v1/config",
      "giveaways": "/api/v1/giveaways",
      "games": "/api/v1/games",
      "duels": "/api/v1/duels",
      "gear": "/api/v1/gear"
    }
  }
}
```

### GET /health

Health check endpoint for load balancers.

**Request:**
```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-16T10:30:00Z",
  "checks": {
    "database": "ok",
    "redis": "ok"
  }
}
```

---

## Currency Management

### GET /currency/{community_id}/balance/{user_id}

Get user's current balance and lifetime statistics.

**Path Parameters:**
- `community_id` (int, required): Community ID
- `user_id` (string, required): Platform user ID

**Query Parameters:**
- `platform` (string, default: "twitch"): twitch, discord, slack, or kick

**Request:**
```bash
GET /currency/1/balance/streamer123?platform=twitch
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "balance": 2500,
    "lifetime_earned": 10000,
    "lifetime_spent": 7500
  }
}
```

**Response (404):**
```json
{
  "success": false,
  "error": "User not found",
  "data": {
    "balance": 0,
    "lifetime_earned": 0,
    "lifetime_spent": 0
  }
}
```

---

### POST /currency/{community_id}/add

Add currency to user's balance. **[Auth Required]**

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "user_id": "streamer123",
  "amount": 500,
  "reason": "Subscription bonus",
  "platform": "twitch"
}
```

**Validation:**
- `user_id`: 1-255 characters, required
- `amount`: 1-1,000,000, must be positive
- `reason`: 1-500 characters
- `platform`: twitch|discord|slack|kick

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "new_balance": 3000,
    "message": "Added 500 points"
  }
}
```

**Errors:**
- `400 Bad Request` — amount ≤ 0 or user_id missing
- `401 Unauthorized` — missing auth token
- `500 Server Error` — database error

---

### POST /currency/{community_id}/remove

Remove currency from user's balance. **[Auth Required]**

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "user_id": "streamer123",
  "amount": 100,
  "reason": "Refund for disputed transaction",
  "platform": "twitch"
}
```

**Validation:** Same as add endpoint

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "new_balance": 2900,
    "message": "Removed 100 points"
  }
}
```

---

### POST /currency/{community_id}/transfer

Transfer currency between users.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "community_id": 1,
  "from_user_id": "sender",
  "to_user_id": "receiver",
  "amount": 250,
  "platform": "twitch"
}
```

**Validation:**
- `amount`: 1-1,000,000, must be positive
- Cannot transfer to self
- Both users must exist

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "new_balance": 2650,
    "message": "Transferred 250 points to receiver"
  }
}
```

**Errors:**
- `400 Bad Request` — from_user == to_user
- `402 Payment Required` — insufficient balance
- `404 Not Found` — user doesn't exist

---

### GET /currency/{community_id}/leaderboard

Get top users by balance or earned points.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Query Parameters:**
- `platform` (string, default: "twitch"): Filter by platform
- `limit` (int, default: 10): Max results (1-100)

**Request:**
```bash
GET /currency/1/leaderboard?platform=twitch&limit=20
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "leaderboard": [
      {
        "rank": 1,
        "user_id": "tycoon",
        "balance": 50000,
        "lifetime_earned": 80000
      },
      {
        "rank": 2,
        "user_id": "grinder",
        "balance": 45000,
        "lifetime_earned": 75000
      },
      {
        "rank": 3,
        "user_id": "luckster",
        "balance": 40000,
        "lifetime_earned": 60000
      }
    ]
  }
}
```

---

### PUT /currency/{community_id}/balance/{user_id}

Set exact balance (admin only). **[Auth Required]**

**Path Parameters:**
- `community_id` (int, required): Community ID
- `user_id` (string, required): Platform user ID

**Request Body:**
```json
{
  "community_id": 1,
  "user_id": "streamer123",
  "balance": 5000,
  "platform": "twitch"
}
```

**Validation:**
- `balance`: 0-10,000,000

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "new_balance": 5000,
    "message": "Balance set to 5000"
  }
}
```

---

### DELETE /currency/{community_id}/wipe

Wipe all balances for a community. **[Auth Required]**

**Path Parameters:**
- `community_id` (int, required): Community ID

**Query Parameters:**
- `platform` (string, default: "twitch"): Only wipe this platform

**Request:**
```bash
DELETE /currency/1/wipe?platform=twitch
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "All balances wiped"
  }
}
```

---

## Earning Configuration

### GET /config/{community_id}

Get current earning rates for community.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request:**
```bash
GET /config/1
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "earn_chat": 1,
    "earn_chat_cooldown": 60,
    "earn_watch_time": 2,
    "earn_watch_interval": 300,
    "earn_follow": 50,
    "earn_sub_t1": 500,
    "earn_sub_t2": 1000,
    "earn_sub_t3": 2500,
    "earn_sub_gift": 750,
    "earn_raid_per_viewer": 1,
    "earn_cheer_per_bit": 0.5
  }
}
```

---

### PUT /config/{community_id}

Update earning rates. **[Auth Required]**

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "community_id": 1,
  "earn_chat": 2,
  "earn_follow": 100,
  "earn_sub_t2": 2000,
  "earn_raid_per_viewer": 2
}
```

**Notes:** Only provide fields to update; omitted fields unchanged.

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "Configuration updated"
  }
}
```

---

### POST /earning/{community_id}/chat

Process chat message earning.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "user_id": "streamer123",
  "platform": "twitch"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "earned": true,
    "amount": 1,
    "new_balance": 2501,
    "message": "Earned 1 point!"
  }
}
```

---

### POST /earning/{community_id}/event

Process event-based earnings (follow, sub, raid, etc.).

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "community_id": 1,
  "user_id": "subscriber456",
  "event_type": "sub_t2",
  "event_data": {
    "tier": 2,
    "gifted": false,
    "months": 1
  },
  "platform": "twitch"
}
```

**Event Types:**
- `follow` — User followed channel
- `sub_t1` — Tier 1 subscription
- `sub_t2` — Tier 2 subscription
- `sub_t3` — Tier 3 subscription
- `sub_gift` — Gifted subscription
- `raid` — Channel raid (check event_data.viewer_count)
- `cheer` — Bits cheered (check event_data.bits)
- `host` — Channel host

**Response (200):**
```json
{
  "success": true,
  "data": {
    "earned": true,
    "amount": 1000,
    "new_balance": 1500,
    "message": "Earned 1000 points for Tier 2 subscription!"
  }
}
```

---

## Minigames

### POST /games/{community_id}/slots

Play slot machine.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "community_id": 1,
  "user_id": "gambler",
  "bet": 50,
  "platform": "twitch"
}
```

**Validation:**
- `bet`: MIN_BET to MAX_BET (config: 10-10000)

**Response (200 - Win):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "symbols": ["cherry", "cherry", "cherry"],
    "won": true,
    "winnings": 150,
    "new_balance": 350,
    "message": "JACKPOT! Three cherries! Won 150 points!"
  }
}
```

**Response (200 - Loss):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "symbols": ["bar", "lemon", "bell"],
    "won": false,
    "winnings": 0,
    "new_balance": 200,
    "message": "No match. Better luck next time!"
  }
}
```

---

### POST /games/{community_id}/coinflip

Play coinflip.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "community_id": 1,
  "user_id": "gambler",
  "bet": 100,
  "choice": "heads",
  "platform": "twitch"
}
```

**Validation:**
- `choice`: heads or tails (case insensitive)
- `bet`: MIN_BET to MAX_BET

**Response (200 - Win):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "result": "heads",
    "won": true,
    "winnings": 100,
    "new_balance": 400,
    "message": "You picked heads and won! +100 points!"
  }
}
```

---

### POST /games/{community_id}/roulette

Play roulette.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "community_id": 1,
  "user_id": "gambler",
  "bet": 50,
  "bet_type": "red",
  "bet_value": null,
  "platform": "twitch"
}
```

**Bet Types:**
- `number` — Bet on specific number (0-36), requires `bet_value`
- `red` / `black` — Color bet
- `odd` / `even` — Parity bet
- `high` / `low` — 1-18 or 19-36

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "number": 17,
    "color": "black",
    "won": false,
    "winnings": 0,
    "new_balance": 250,
    "message": "Spun 17 (black). You bet red. Better luck next time!"
  }
}
```

---

### GET /games/{community_id}/stats/{user_id}

Get user's game statistics.

**Path Parameters:**
- `community_id` (int, required): Community ID
- `user_id` (string, required): Platform user ID

**Query Parameters:**
- `platform` (string, default: "twitch"): Platform filter

**Response (200):**
```json
{
  "success": true,
  "data": {
    "total_games": 42,
    "total_wagered": 2500,
    "total_won": 3200,
    "net_winnings": 700,
    "biggest_win": 500,
    "win_rate": 0.52
  }
}
```

---

## Duels

### POST /duels/{community_id}/challenge

Create duel challenge.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "community_id": 1,
  "challenger_id": "player_a",
  "opponent_id": "player_b",
  "wager": 100,
  "platform": "twitch"
}
```

**Validation:**
- `wager`: 1-10000
- Cannot duel self
- Both users must have sufficient balance

**Response (201):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "duel_id": 99,
    "message": "Challenge created! Waiting for player_b to accept..."
  }
}
```

---

### POST /duels/{community_id}/accept

Accept duel challenge.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "community_id": 1,
  "duel_id": 99,
  "platform": "twitch"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "winner_id": "player_a",
    "loser_id": "player_b",
    "winnings": 200,
    "message": "Duel complete! player_a wins 200 points!"
  }
}
```

---

### POST /duels/{community_id}/decline

Decline duel challenge.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "community_id": 1,
  "duel_id": 99,
  "platform": "twitch"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "Duel declined"
  }
}
```

---

### GET /duels/{community_id}/pending/{user_id}

Get pending duels for user.

**Path Parameters:**
- `community_id` (int, required): Community ID
- `user_id` (string, required): Platform user ID

**Query Parameters:**
- `platform` (string, default: "twitch"): Platform filter

**Response (200):**
```json
{
  "success": true,
  "data": {
    "pending_duels": [
      {
        "duel_id": 99,
        "challenger_id": "player_a",
        "opponent_id": "player_b",
        "wager": 100,
        "created_at": "2026-02-16T10:00:00Z"
      }
    ]
  }
}
```

---

### GET /duels/{community_id}/stats/{user_id}

Get duel statistics for user.

**Path Parameters:**
- `community_id` (int, required): Community ID
- `user_id` (string, required): Platform user ID

**Query Parameters:**
- `platform` (string, default: "twitch"): Platform filter

**Response (200):**
```json
{
  "success": true,
  "data": {
    "total_duels": 50,
    "wins": 30,
    "losses": 20,
    "win_rate": 0.60,
    "total_wagered": 5000,
    "net_winnings": 1200
  }
}
```

---

### GET /duels/{community_id}/leaderboard

Get duel leaderboard.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Query Parameters:**
- `limit` (int, default: 10): Max results (1-100)
- `platform` (string, default: "twitch"): Platform filter

**Response (200):**
```json
{
  "success": true,
  "data": {
    "leaderboard": [
      {
        "rank": 1,
        "user_id": "duel_master",
        "wins": 100,
        "total_duels": 120,
        "win_rate": 0.83
      },
      {
        "rank": 2,
        "user_id": "fighter",
        "wins": 80,
        "total_duels": 110,
        "win_rate": 0.73
      }
    ]
  }
}
```

---

## Giveaways

### POST /giveaways/{community_id}

Create giveaway. **[Auth Required]**

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "community_id": 1,
  "title": "Valentine's Day Gift Pack",
  "prize": "50 USD Steam Gift Card",
  "entry_cost": 100,
  "duration_minutes": 120,
  "max_entries": 500,
  "reputation_weighted": true
}
```

**Validation:**
- `title`: 3-200 characters
- `prize`: 1-500 characters
- `entry_cost`: 0-100000
- `duration_minutes`: 1-10080 (max 7 days)
- `max_entries`: 1-100000 (optional)
- `reputation_weighted`: boolean

**Response (201):**
```json
{
  "success": true,
  "data": {
    "giveaway_id": 42,
    "title": "Valentine's Day Gift Pack",
    "prize": "50 USD Steam Gift Card",
    "status": "active",
    "ends_at": "2026-02-16T12:30:00Z"
  }
}
```

---

### GET /giveaways/{community_id}

List giveaways for community.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Query Parameters:**
- `status` (string): Filter by status (active, ended, cancelled)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "giveaways": [
      {
        "giveaway_id": 42,
        "title": "Valentine's Day Gift Pack",
        "prize": "50 USD Steam Gift Card",
        "status": "active",
        "entry_cost": 100,
        "entry_count": 47,
        "max_entries": 500,
        "ends_at": "2026-02-16T12:30:00Z"
      }
    ]
  }
}
```

---

### GET /giveaways/{community_id}/{giveaway_id}

Get giveaway details.

**Path Parameters:**
- `community_id` (int, required): Community ID
- `giveaway_id` (int, required): Giveaway ID

**Response (200):**
```json
{
  "success": true,
  "data": {
    "giveaway_id": 42,
    "title": "Valentine's Day Gift Pack",
    "prize": "50 USD Steam Gift Card",
    "description": "Lucky winner gets a gift!",
    "status": "active",
    "entry_cost": 100,
    "entry_count": 47,
    "max_entries": 500,
    "reputation_weighted": true,
    "winner_user_id": null,
    "created_at": "2026-02-16T10:30:00Z",
    "ends_at": "2026-02-16T12:30:00Z"
  }
}
```

---

### POST /giveaways/{community_id}/{giveaway_id}/enter

Enter giveaway.

**Path Parameters:**
- `community_id` (int, required): Community ID
- `giveaway_id` (int, required): Giveaway ID

**Request Body:**
```json
{
  "community_id": 1,
  "giveaway_id": 42,
  "user_id": "participant999",
  "platform": "twitch"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "Entered giveaway! Good luck!",
    "entry_number": 47
  }
}
```

**Errors:**
- `402 Payment Required` — Insufficient balance for entry cost
- `409 Conflict` — Already entered, max entries reached, giveaway closed

---

### POST /giveaways/{community_id}/{giveaway_id}/draw

Draw winner. **[Auth Required]**

**Path Parameters:**
- `community_id` (int, required): Community ID
- `giveaway_id` (int, required): Giveaway ID

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "winner_user_id": "lucky_viewer",
    "message": "Winner drawn! Congratulations lucky_viewer!"
  }
}
```

---

### PUT /giveaways/{community_id}/{giveaway_id}/end

End giveaway. **[Auth Required]**

**Path Parameters:**
- `community_id` (int, required): Community ID
- `giveaway_id` (int, required): Giveaway ID

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "Giveaway ended"
  }
}
```

---

## Gear System

### GET /gear/{community_id}/shop

List shop items.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Query Parameters:**
- `category` (string): Filter by category (optional)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "item_id": 1,
        "name": "Iron Sword",
        "description": "Basic melee weapon",
        "category": "weapons",
        "price": 500,
        "stat_bonus": {"damage": 10},
        "available": true
      },
      {
        "item_id": 2,
        "name": "Diamond Sword",
        "description": "Legendary melee weapon",
        "category": "weapons",
        "price": 5000,
        "stat_bonus": {"damage": 50},
        "available": true
      }
    ]
  }
}
```

---

### GET /gear/{community_id}/inventory/{user_id}

Get user's inventory.

**Path Parameters:**
- `community_id` (int, required): Community ID
- `user_id` (string, required): Platform user ID

**Query Parameters:**
- `platform` (string, default: "twitch"): Platform filter

**Response (200):**
```json
{
  "success": true,
  "data": {
    "inventory": [
      {
        "item_id": 1,
        "name": "Iron Sword",
        "category": "weapons",
        "equipped": true,
        "stat_bonus": {"damage": 10}
      }
    ]
  }
}
```

---

### POST /gear/{community_id}/buy

Purchase item.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "community_id": 1,
  "user_id": "collector",
  "item_id": 1,
  "platform": "twitch"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "Purchased Iron Sword for 500 points!",
    "new_balance": 1500
  }
}
```

---

### POST /gear/{community_id}/equip

Equip item.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "community_id": 1,
  "user_id": "collector",
  "item_id": 1,
  "platform": "twitch"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "Item equipped successfully!"
  }
}
```

---

### POST /gear/{community_id}/unequip

Unequip item.

**Path Parameters:**
- `community_id` (int, required): Community ID

**Request Body:**
```json
{
  "community_id": 1,
  "user_id": "collector",
  "item_id": 1,
  "platform": "twitch"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "Item unequipped successfully!"
  }
}
```

---

### GET /gear/{community_id}/equipped/{user_id}

Get equipped gear and stat totals.

**Path Parameters:**
- `community_id` (int, required): Community ID
- `user_id` (string, required): Platform user ID

**Query Parameters:**
- `platform` (string, default: "twitch"): Platform filter

**Response (200):**
```json
{
  "success": true,
  "data": {
    "equipped_items": [
      {
        "item_id": 1,
        "name": "Iron Sword",
        "category": "weapons",
        "stat_bonus": {"damage": 10}
      }
    ],
    "total_stats": {"damage": 10}
  }
}
```

---

### GET /gear/categories

Get all gear categories.

**Request:**
```bash
GET /gear/categories
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "categories": ["weapons", "armor", "accessories", "cosmetics"]
  }
}
```

---

## Chat Commands

### POST /command

Handle chat command.

**Request Body:**
```json
{
  "session_id": "session123",
  "command": "balance",
  "args": [],
  "user_id": "streamer123",
  "community_id": 1,
  "platform": "twitch"
}
```

**Available Commands:**
- `balance`, `bal` — Check balance
- `gamble <amount>` — Play slots
- `coinflip <h|t> <amount>` — Flip coin
- `roulette <type> <amount>` — Play roulette
- `duel @opponent <amount>` — Challenge user
- `gear` — Show inventory
- `gear shop` — Browse shop
- `leaderboard [limit]` — Top earners

**Response (200):**
```json
{
  "success": true,
  "data": {
    "session_id": "session123",
    "response_action": "chat",
    "response_data": {
      "message": "Balance: 2500 | Earned: 10000 | Spent: 7500"
    }
  }
}
```

---

## Global Error Responses

All endpoints may return:

**400 Bad Request**
```json
{
  "success": false,
  "error": "Invalid input",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "field": "bet",
    "message": "Bet must be between 10 and 10000"
  }
}
```

**401 Unauthorized**
```json
{
  "success": false,
  "error": "Authentication required",
  "error_code": "UNAUTHORIZED"
}
```

**403 Forbidden**
```json
{
  "success": false,
  "error": "Insufficient permissions",
  "error_code": "FORBIDDEN"
}
```

**404 Not Found**
```json
{
  "success": false,
  "error": "Resource not found",
  "error_code": "NOT_FOUND"
}
```

**409 Conflict**
```json
{
  "success": false,
  "error": "Operation not allowed",
  "error_code": "CONFLICT",
  "details": {
    "reason": "Giveaway is no longer active"
  }
}
```

**500 Internal Server Error**
```json
{
  "success": false,
  "error": "Internal server error",
  "error_code": "SERVER_ERROR"
}
```

---

**Last Updated:** 2026-02-16
