# Loyalty Interaction Module — Architecture & System Design

Deep dive into system design, data models, service architecture, and data flows.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Core Services](#core-services)
3. [Database Schema](#database-schema)
4. [Data Flow Examples](#data-flow-examples)
5. [Economic Model](#economic-model)
6. [Concurrency & Scalability](#concurrency--scalability)

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Chat/API Clients                          │
│  (Twitch, Discord, Slack, Kick, Web Frontend)              │
└────────────────────────┬────────────────────────────────────┘
                         │
                    REST API (8032)
                         │
┌────────────────────────▼────────────────────────────────────┐
│         Quart Application (Async Web Framework)             │
│  ┌─────────────┬──────────────┬─────────────────────────┐  │
│  │  Blueprints │  Validation  │  Authentication/Auth    │  │
│  │  (Routes)   │  (Pydantic)  │                         │  │
│  └──────┬──────┴──────────────┴───────────┬─────────────┘  │
│         │                                  │                │
│  ┌──────▼─────────────────────────────────▼────────────┐   │
│  │  Service Layer (Async Operations)                    │   │
│  │  ┌────────────────────────────────────────────────┐ │   │
│  │  │ CurrencyService   — Balance, transfers        │ │   │
│  │  │ EarningConfigService — Event-based earning    │ │   │
│  │  │ MinigameService   — Games (slots, etc.)       │ │   │
│  │  │ DuelService       — PvP challenges            │ │   │
│  │  │ GiveawayService   — Giveaway management       │ │   │
│  │  │ GearService       — Shop & inventory          │ │   │
│  │  └────────────────────────────────────────────────┘ │   │
│  └───────────────────────┬──────────────────────────────┘   │
└──────────────────────────┼─────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────▼───┐   ┌───▼────┐  ┌──▼──────┐
         │PostgreSQL│  │ Redis  │  │ PyDAL  │
         │Database │  │ Cache  │  │ Abstraction
         └─────────┘  └────────┘  └────────┘
```

### Request Processing Flow

```
1. HTTP Request Arrives
   ├─ Router matches endpoint
   ├─ Pydantic validates JSON
   ├─ Auth middleware checks token
   │
2. Service Layer Execution
   ├─ Currency/Giveaway/Game Service method called
   ├─ Database query via PyDAL
   ├─ Async/await for I/O operations
   │
3. Transaction & Logging
   ├─ Economy operation logged for audit
   ├─ Redis cache updated
   │
4. Response Formation
   ├─ success_response() or error_response()
   ├─ HTTP 200/400/401/500 with JSON
   │
5. Client Response
   └─ Client receives result and updates UI
```

## Core Services

### 1. CurrencyService

**Responsibility:** Core balance and transaction operations

**Key Methods:**
```python
async def get_balance(community_id, platform, platform_user_id) -> BalanceInfo
  # Returns user's balance and lifetime earned/spent stats

async def add_currency(community_id, platform, platform_user_id, amount, reason) -> TransactionResult
  # Adds currency and logs transaction

async def remove_currency(...) -> TransactionResult
  # Removes currency with validation

async def transfer(community_id, platform, from_user_id, to_user_id, amount) -> TransactionResult
  # P2P currency transfer with balance checks

async def get_leaderboard(community_id, platform, limit) -> List[BalanceInfo]
  # Returns top N users by balance

async def set_balance(community_id, platform, user_id, balance) -> TransactionResult
  # Admin: set exact balance (dangerous operation)

async def wipe_all_balances(community_id, platform) -> bool
  # Admin: reset all balances (audit-logged)
```

**Database Operations:**
- Reads from `loyalty_balances` table
- Writes to `loyalty_transactions` table (audit trail)
- Updates balance atomically

### 2. EarningConfigService

**Responsibility:** Configure and process event-based earnings

**Key Methods:**
```python
async def get_config(community_id) -> EarningConfig
  # Returns current earning multipliers for community

async def update_config(community_id, **kwargs) -> bool
  # Updates earning rates (e.g., chat points, follow bonus)

async def process_chat_earning(community_id, platform, user_id) -> EarningResult
  # Award points for chat message with cooldown check

async def process_event_earning(community_id, platform, user_id, event_type, event_data) -> EarningResult
  # Award points for follows, subs, raids, cheers based on config
```

**Earning Multipliers:**
- `earn_chat` — Points per chat message (default: 1)
- `earn_chat_cooldown` — Seconds between chat earnings (default: 60)
- `earn_watch_time` — Points per watch interval (default: 2)
- `earn_watch_interval` — Watch interval in seconds (default: 300)
- `earn_follow` — Bonus for follow (default: 50)
- `earn_sub_t1/t2/t3` — Tier-based subscription bonuses
- `earn_sub_gift` — Gifted subscription bonus
- `earn_raid_per_viewer` — Points per raid viewer (default: 1)
- `earn_cheer_per_bit` — Points per bit cheered (default: 0.5)

### 3. MinigameService

**Responsibility:** Game logic and outcome generation

**Games:**
- **Slots** — 3 symbols, match 2+ for payout (3x = jackpot)
- **Coinflip** — 50/50 bet on heads/tails, 2x payout
- **Roulette** — European wheel (0-36), various bet types, configurable payouts

**Key Methods:**
```python
async def play_slots(community_id, platform, user_id, bet) -> GameResult
async def play_coinflip(community_id, platform, user_id, bet, choice) -> GameResult
async def play_roulette(community_id, platform, user_id, bet, bet_type, bet_value) -> GameResult
  # All validate bet amount, deduct wager, credit winnings

async def get_user_stats(community_id, platform, user_id) -> GameStats
  # Returns total_games, total_wagered, total_won, net_winnings, win_rate
```

**Responsible Gambling:**
- Configurable MIN_BET and MAX_BET
- House edge built into payouts
- Stats tracking for player awareness

### 4. DuelService

**Responsibility:** PvP combat with currency stakes

**Challenge Workflow:**
1. Challenger creates challenge with wager
2. Opponent has DUEL_TIMEOUT_MINUTES to accept
3. Combat outcome randomly determined (50/50 base, modified by equipped gear)
4. Winner gets 2x wager, loser loses wager

**Key Methods:**
```python
async def create_challenge(community_id, platform, challenger_id, opponent_id, wager) -> DuelResult
async def accept_challenge(community_id, platform, duel_id) -> DuelResult
async def decline_challenge(community_id, duel_id) -> bool
async def get_pending_duels(community_id, platform, user_id) -> List[Duel]
async def get_user_stats(community_id, platform, user_id) -> DuelStats
async def get_leaderboard(community_id, platform, limit) -> List[DuelStats]
```

**Gear Impact:**
- Equipped gear provides stat bonuses
- Stats improve win probability (configurable algorithm)
- Cosmetics-only gear available for aesthetics

### 5. GiveawayService

**Responsibility:** Prize draws with optional reputation weighting

**Key Methods:**
```python
async def create_giveaway(community_id, title, prize, entry_cost, duration_minutes, max_entries, reputation_weighted) -> Giveaway
async def list_giveaways(community_id, status=None) -> List[Giveaway]
async def get_giveaway(community_id, giveaway_id) -> Giveaway
async def enter_giveaway(community_id, giveaway_id, platform, user_id) -> EntryResult
  # Validates entry cost, prevents duplicates, manages entries

async def draw_winner(community_id, giveaway_id) -> DrawResult
  # Selects winner: uniform random OR reputation-weighted

async def end_giveaway(community_id, giveaway_id) -> bool
  # Closes giveaway for entries
```

**Reputation Weighting:**
If `reputation_weighted=true`, entry selection is weighted by user reputation:
- Fetch user reputation from REPUTATION_API_URL
- Map reputation score to weight multiplier (see REPUTATION_TIERS in config)
- Use weighted random selection algorithm

### 6. GearService

**Responsibility:** Shop, inventory, equipment management

**Key Methods:**
```python
async def get_shop_items(community_id, category=None) -> List[Item]
async def get_user_inventory(community_id, platform, user_id) -> List[InventoryItem]
async def buy_item(community_id, platform, user_id, item_id) -> TransactionResult
  # Validates price, deducts currency, adds to inventory

async def equip_item(community_id, platform, user_id, item_id) -> bool
async def unequip_item(community_id, platform, user_id, item_id) -> bool
async def get_equipped_stats(community_id, platform, user_id) -> EquippedStats
  # Returns equipped items and aggregated stat bonuses

async def get_categories() -> List[str]
```

**Item Types:**
- Cosmetics — No stat bonus, visual only
- Weapons — Damage stat bonus
- Armor — Defense stat bonus
- Accessories — Various stat bonuses

## Database Schema

### Core Tables

**loyalty_balances**
```sql
CREATE TABLE loyalty_balances (
  id SERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL,
  platform VARCHAR(50) NOT NULL,
  platform_user_id VARCHAR(255) NOT NULL,
  balance INTEGER NOT NULL DEFAULT 0,
  lifetime_earned INTEGER NOT NULL DEFAULT 0,
  lifetime_spent INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(community_id, platform, platform_user_id),
  INDEX(community_id, balance DESC)
);
```

**loyalty_transactions**
```sql
CREATE TABLE loyalty_transactions (
  id SERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL,
  platform VARCHAR(50) NOT NULL,
  user_id VARCHAR(255) NOT NULL,
  transaction_type VARCHAR(50) NOT NULL,
  amount INTEGER NOT NULL,
  reason TEXT,
  previous_balance INTEGER,
  new_balance INTEGER,
  related_user_id VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX(community_id, created_at DESC),
  INDEX(community_id, user_id, created_at DESC)
);
```

**loyalty_earning_config**
```sql
CREATE TABLE loyalty_earning_config (
  id SERIAL PRIMARY KEY,
  community_id INTEGER UNIQUE NOT NULL,
  earn_chat INTEGER DEFAULT 1,
  earn_chat_cooldown INTEGER DEFAULT 60,
  earn_watch_time INTEGER DEFAULT 2,
  earn_watch_interval INTEGER DEFAULT 300,
  earn_follow INTEGER DEFAULT 50,
  earn_sub_t1 INTEGER DEFAULT 500,
  earn_sub_t2 INTEGER DEFAULT 1000,
  earn_sub_t3 INTEGER DEFAULT 2500,
  earn_sub_gift INTEGER DEFAULT 750,
  earn_raid_per_viewer INTEGER DEFAULT 1,
  earn_cheer_per_bit DECIMAL(5,2) DEFAULT 0.5,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX(community_id)
);
```

**loyalty_games**
```sql
CREATE TABLE loyalty_games (
  id SERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL,
  platform VARCHAR(50) NOT NULL,
  user_id VARCHAR(255) NOT NULL,
  game_type VARCHAR(50) NOT NULL,
  bet INTEGER NOT NULL,
  won BOOLEAN NOT NULL,
  winnings INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX(community_id, user_id, created_at DESC),
  INDEX(community_id, created_at DESC)
);
```

**loyalty_duels**
```sql
CREATE TABLE loyalty_duels (
  id SERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL,
  platform VARCHAR(50) NOT NULL,
  challenger_id VARCHAR(255) NOT NULL,
  opponent_id VARCHAR(255) NOT NULL,
  wager INTEGER NOT NULL,
  winner_id VARCHAR(255),
  status VARCHAR(50) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP,
  expires_at TIMESTAMP,
  INDEX(community_id, status, created_at DESC),
  INDEX(community_id, opponent_id, status)
);
```

**loyalty_giveaways**
```sql
CREATE TABLE loyalty_giveaways (
  id SERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL,
  title VARCHAR(200) NOT NULL,
  prize VARCHAR(500) NOT NULL,
  entry_cost INTEGER DEFAULT 0,
  reputation_weighted BOOLEAN DEFAULT FALSE,
  status VARCHAR(50) NOT NULL DEFAULT 'active',
  max_entries INTEGER,
  winner_user_id VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ends_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  INDEX(community_id, status, created_at DESC),
  INDEX(community_id, ends_at)
);
```

**loyalty_giveaway_entries**
```sql
CREATE TABLE loyalty_giveaway_entries (
  id SERIAL PRIMARY KEY,
  giveaway_id INTEGER NOT NULL,
  platform VARCHAR(50) NOT NULL,
  user_id VARCHAR(255) NOT NULL,
  entry_number INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(giveaway_id, platform, user_id),
  INDEX(giveaway_id, created_at),
  FOREIGN KEY (giveaway_id) REFERENCES loyalty_giveaways(id)
);
```

**loyalty_gear_items**
```sql
CREATE TABLE loyalty_gear_items (
  id SERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  category VARCHAR(50),
  price INTEGER NOT NULL,
  rarity VARCHAR(50) DEFAULT 'common',
  stat_bonus JSONB DEFAULT '{}',
  available BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX(community_id, category)
);
```

**loyalty_gear_inventory**
```sql
CREATE TABLE loyalty_gear_inventory (
  id SERIAL PRIMARY KEY,
  community_id INTEGER NOT NULL,
  platform VARCHAR(50) NOT NULL,
  user_id VARCHAR(255) NOT NULL,
  item_id INTEGER NOT NULL,
  equipped BOOLEAN DEFAULT FALSE,
  acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(community_id, platform, user_id, item_id),
  INDEX(community_id, user_id),
  FOREIGN KEY (item_id) REFERENCES loyalty_gear_items(id)
);
```

## Data Flow Examples

### Flow 1: User Plays Slots (Game Economic Transaction)

```
1. User sends: POST /games/1/slots { bet: 50 }
2. Service validates:
   - User exists with balance >= 50
   - Bet within MIN_BET/MAX_BET range
3. Deduct bet (atomic operation)
   - UPDATE loyalty_balances SET balance = balance - 50
   - INSERT INTO loyalty_transactions (type: 'spend', amount: -50)
4. Generate game outcome (RNG slots logic)
   - Symbols: cherry, cherry, cherry (JACKPOT)
5. Payout calculation:
   - Jackpot = 3x bet = 150
6. Credit winnings (atomic operation)
   - UPDATE loyalty_balances SET balance = balance + 150
   - INSERT INTO loyalty_transactions (type: 'win', amount: 150)
7. Log game record:
   - INSERT INTO loyalty_games (game_type: 'slots', bet: 50, won: true, winnings: 150)
8. Return response with new balance
```

### Flow 2: User Subscribes, Earns Bonus

```
1. External event arrives: POST /earning/1/event { event_type: 'sub_t2' }
2. Service loads earning config:
   - SELECT earn_sub_t2 FROM loyalty_earning_config WHERE community_id = 1
   - earn_sub_t2 = 1000
3. Check user balance:
   - If user doesn't exist, create zero balance record
4. Award points:
   - UPDATE loyalty_balances SET balance = balance + 1000, lifetime_earned = lifetime_earned + 1000
   - INSERT INTO loyalty_transactions (type: 'earn', reason: 'sub_t2', amount: 1000)
5. Update Redis cache (if enabled)
6. Return success with new balance
```

### Flow 3: Duel Challenge & Resolution

```
1. Challenger creates: POST /duels/1/challenge { opponent_id: 'p2', wager: 100 }
2. Validate:
   - Challenger.balance >= 100
   - Opponent.balance >= 100
   - challenger_id != opponent_id
3. Create duel record:
   - INSERT INTO loyalty_duels (status: 'pending', expires_at: now + 5 min)
4. Opponent accepts: POST /duels/1/{duel_id}/accept
5. Resolve (randomly determine winner, weighted by gear stats):
   - Fetch both players' equipped gear
   - Calculate stat advantage
   - Random weighted coin flip
   - Winner determined (e.g., 'p1')
6. Transfer currency:
   - Deduct wager from loser: balance - 100
   - Award 2x wager to winner: balance + 200
   - Log transactions for both
7. Update duel record:
   - UPDATE loyalty_duels SET winner_id='p1', status='completed', completed_at=now
8. Return result to both players
```

## Economic Model

### Currency Management

**Key Principles:**
1. **Atomic Transactions** — All updates are atomic (no partial updates)
2. **Full Audit Trail** — Every transaction logged in `loyalty_transactions`
3. **Balance Validation** — Always check sufficient balance before spend
4. **Lifetime Tracking** — Track total earned and spent for statistics

**Transaction Types:**
- `earn` — Points gained (chat, events, rewards)
- `spend` — Points lost (bets, purchases)
- `transfer` — P2P transfer
- `admin_adjust` — Manual admin adjustment (logged with auditor)
- `win` — Game/duel winnings
- `refund` — Refund operations

### House Economics

**Minigames (House Advantage):**
- Slots: ~30% house edge (typical slot machine)
- Coinflip: ~5% house edge (near fair)
- Roulette: ~2.7% house edge (European wheel)

**Duels (Zero-Sum):**
- 100% zero-sum: winner gets 2x, loser loses bet
- No house cut, all currency stays in player ecosystem

**Giveaways:**
- Entry cost directly from players
- Prize distributed to winner
- Community/streamer can pocket entry fees or reinvest

**Gear Shop:**
- Items priced by rarity and stat bonus
- Price set per-item by community admins
- Full revenue to community

### Economic Safety

**Limits:**
- MAX_BET prevents runaway losses (default: 10,000)
- Account balance floor is 0 (can't go negative)
- Giveaway entry costs configurable to prevent exploitation
- Duel timeouts prevent indefinite pending challenges

**Monitoring:**
- Audit logs track all transactions with reason
- Community admins can see spending patterns
- Alert system for suspicious activity (future)

## Concurrency & Scalability

### Async/Await Architecture

**Why Quart (Async Flask)?**
- Non-blocking I/O operations
- Single thread handles many concurrent requests
- Thousands of concurrent users on modest hardware
- No thread pool overhead

**All database and Redis operations are async:**
```python
# Async operations don't block other requests
balance = await currency_service.get_balance(...)  # Non-blocking
result = await minigame_service.play_slots(...)    # Non-blocking
```

### Database Optimization

**Indexes for Performance:**
```sql
-- Fast balance lookups
CREATE INDEX idx_loyalty_balances_community_user
  ON loyalty_balances(community_id, platform_user_id);

-- Fast leaderboard queries
CREATE INDEX idx_loyalty_balances_community_balance
  ON loyalty_balances(community_id, balance DESC);

-- Fast transaction history
CREATE INDEX idx_loyalty_transactions_community_user
  ON loyalty_transactions(community_id, user_id, created_at DESC);
```

**Connection Pooling:**
- asyncpg maintains connection pool for PostgreSQL
- Reuses connections across requests
- Configurable pool size for hardware

### Caching Strategy

**Redis Caching (Optional):**
```
User Balances
├─ Key: loyalty:balance:{community_id}:{user_id}
├─ TTL: 5 minutes
└─ Used for: Fast repeated balance queries

Leaderboards
├─ Key: loyalty:leaderboard:{community_id}
├─ TTL: 10 minutes
└─ Used for: Leaderboard API responses

Shop Items
├─ Key: loyalty:shop:{community_id}
├─ TTL: 1 hour
└─ Used for: Shop browsing
```

**Cache Invalidation:**
- Balance cache invalidated on transaction
- Leaderboard cache invalidated on significant changes
- Shop cache invalidated on admin updates

### Horizontal Scalability

**Stateless Design:**
- Each instance processes requests independently
- No session affinity required
- Database and Redis are shared state
- Load balancer can distribute across instances

**Load Balancing:**
```
┌──────────────┐
│ Load Balancer│
└─────┬────────┘
      │
   ┌──┴──┬────────┬────────┐
   │     │        │        │
 ┌─▼──┐┌─▼──┐ ┌──▼─┐ ┌───▼┐
 │Srv1││Srv2│ │Srv3│ │Srv4│
 └────┘└────┘ └────┘ └────┘
   All → PostgreSQL (primary)
   All → Redis (optional)
```

**Database Scaling:**
- Read replicas for leaderboards (eventually consistent)
- Write operations to primary only
- Connection pooling across instances

---

**Last Updated:** 2026-02-16
