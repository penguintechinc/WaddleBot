# Loyalty Interaction Module — Configuration Guide

Complete reference for all environment variables, configuration options, and tuning parameters.

## Table of Contents

1. [Required Configuration](#required-configuration)
2. [Optional Configuration](#optional-configuration)
3. [Earning Multipliers](#earning-multipliers)
4. [Gambling Limits](#gambling-limits)
5. [Giveaway Settings](#giveaway-settings)
6. [Duel Settings](#duel-settings)
7. [Example .env Files](#example-env-files)
8. [Tuning & Optimization](#tuning--optimization)

## Required Configuration

### Database

**DATABASE_URL**
- **Type:** String
- **Default:** `postgresql://waddlebot:waddlebot_secret@localhost:5432/waddlebot`
- **Required:** Yes
- **Description:** PostgreSQL connection string
- **Example:** `postgresql://user:password@host:5432/database`
- **Other Formats:**
  - SQLite: `sqlite:///path/to/db.sqlite`
  - MySQL: `mysql://user:password@host/database`

**Connection String Format:**
```
postgresql://[user[:password]@][host[:port]][/dbname]
```

### Module Port

**MODULE_PORT**
- **Type:** Integer
- **Default:** `8032`
- **Range:** 1024-65535
- **Required:** No (default fine for most)
- **Description:** REST API listening port
- **Example:** `8032`
- **Note:** Must not conflict with other services

## Optional Configuration

### Redis Caching

**REDIS_URL**
- **Type:** String
- **Default:** `redis://localhost:6379`
- **Required:** No (caching disabled if not set)
- **Description:** Redis connection for performance optimization
- **Example:** `redis://redis:6379` or `redis://:password@redis:6379`

**When to Use:**
- High traffic communities (>1000 concurrent users)
- Frequent leaderboard/balance queries
- Production deployments
- Can be disabled for development

### Service Integration

**ROUTER_API_URL**
- **Type:** String
- **Default:** `http://router:8000`
- **Required:** No
- **Description:** URL of central router for chat command forwarding
- **Example:** `http://router:8000`

**REPUTATION_API_URL**
- **Type:** String
- **Default:** `http://reputation:8021`
- **Required:** No (reputation weighting disabled if not set)
- **Description:** URL of reputation service for giveaway weighting
- **Example:** `http://reputation:8021`

**SERVICE_API_KEY**
- **Type:** String
- **Default:** (empty)
- **Required:** Only if ROUTER_API_URL is set
- **Description:** API key for service-to-service authentication
- **Example:** `sk_loyalty_123456789`
- **Security:** Store in secret vault, never commit to git

## Earning Multipliers

Controls how many loyalty points users earn from various activities.

### Chat Earning

**DEFAULT_EARN_CHAT**
- **Type:** Integer
- **Default:** `1`
- **Range:** 0-1000
- **Description:** Points awarded per chat message
- **Example:** `1` = 1 point per message, `5` = 5 points per message
- **Tips:**
  - Higher = easier points accumulation = inflation risk
  - Lower = more effort needed = better currency value
  - Start at 1-2 for balance

**DEFAULT_EARN_CHAT_COOLDOWN**
- **Type:** Integer
- **Unit:** Seconds
- **Default:** `60`
- **Range:** 0-3600
- **Description:** Minimum seconds between chat earnings for same user
- **Example:** `60` = user can earn once per minute
- **Tips:**
  - Prevents spam earnings
  - `0` = no cooldown (may cause spam)
  - `300` = 5 minute cooldown (restrictive)

### Watch Time Earning

**DEFAULT_EARN_WATCH_TIME**
- **Type:** Integer
- **Default:** `2`
- **Range:** 0-1000
- **Description:** Points per watch interval
- **Example:** `2` = 2 points per interval

**DEFAULT_EARN_WATCH_INTERVAL**
- **Type:** Integer
- **Unit:** Seconds
- **Default:** `300` (5 minutes)
- **Range:** 60-3600
- **Description:** Interval for watch time earnings
- **Example:** `300` = award every 5 minutes of watching
- **Tips:**
  - Larger interval = less inflation
  - Smaller interval = more rewards (engagement boost)

### Subscription Bonuses

These apply when users subscribe to Twitch channel (or equivalent on other platforms).

**DEFAULT_EARN_SUB_T1**
- **Type:** Integer
- **Default:** `500`
- **Range:** 0-100000
- **Description:** Points for Tier 1 subscription
- **Example:** `500` = 500 points for $4.99 sub

**DEFAULT_EARN_SUB_T2**
- **Type:** Integer
- **Default:** `1000`
- **Range:** 0-100000
- **Description:** Points for Tier 2 subscription
- **Example:** `1000` = 1000 points for $9.99 sub

**DEFAULT_EARN_SUB_T3**
- **Type:** Integer
- **Default:** `2500`
- **Range:** 0-100000
- **Description:** Points for Tier 3 subscription
- **Example:** `2500` = 2500 points for $24.99 sub

**Recommendation:** Use 100x sub tier for balance
```
T1 ($4.99) → 500 points
T2 ($9.99) → 1000 points
T3 ($24.99) → 2500 points
```

### Special Event Bonuses

**DEFAULT_EARN_FOLLOW**
- **Type:** Integer
- **Default:** `50`
- **Range:** 0-10000
- **Description:** Bonus points for following channel
- **Example:** `50` = 50 point bonus per follow

**DEFAULT_EARN_SUB_GIFT**
- **Type:** Integer
- **Default:** `750`
- **Range:** 0-100000
- **Description:** Points for gifted subscription
- **Example:** `750` = 750 points when someone gifts subs to community

**DEFAULT_EARN_RAID_PER_VIEWER**
- **Type:** Integer
- **Default:** `1`
- **Range:** 0-1000
- **Description:** Points per raider viewer
- **Example:** `1` = 50 raid viewers = 50 points, `2` = 50 raid = 100 points

**DEFAULT_EARN_CHEER_PER_BIT**
- **Type:** Float
- **Default:** `0.5`
- **Range:** 0.0-100.0
- **Description:** Points per bit cheered
- **Example:** `0.5` = 100 bits = 50 points, `1.0` = 100 bits = 100 points
- **Tips:** Often less than sub earning (avoid cheer farming)

## Gambling Limits

### Bet Limits

**MIN_BET**
- **Type:** Integer
- **Default:** `10`
- **Range:** 1-100000
- **Description:** Minimum allowed bet in games
- **Example:** `10` = users must bet at least 10 points
- **Tips:**
  - Prevents micro-bets/spam
  - Too low = excessive transactions
  - Too high = excludes newer players

**MAX_BET**
- **Type:** Integer
- **Default:** `10000`
- **Range:** 10-10000000
- **Description:** Maximum allowed bet in games
- **Example:** `10000` = users can bet up to 10000 points
- **Tips:**
  - Prevents runaway losses
  - Too high = risky for players
  - Too low = frustrates high-balance players
  - Recommend 100x MIN_BET

**Recommended Ranges:**
```
New Communities: MIN=10, MAX=500
Growing Communities: MIN=50, MAX=5000
Mature Communities: MIN=100, MAX=10000
High-Value Communities: MIN=1000, MAX=50000
```

## Giveaway Settings

### Reputation Weighting

**GIVEAWAY_REPUTATION_FLOOR**
- **Type:** Integer
- **Default:** `450`
- **Range:** 0-850
- **Description:** Minimum reputation score to enter reputation-weighted giveaways
- **Example:** `450` = only users with 450+ reputation can enter
- **Tips:**
  - Prevents low-quality users from spamming entries
  - Higher floor = more exclusive giveaways
  - Set to 0 to disable reputation floor

### Reputation Tiers

Defined in `config.py` for giveaway weight multipliers:

```python
REPUTATION_TIERS = {
    'exceptional': {'min': 800, 'max': 850, 'weight': 1.5},  # 1.5x odds
    'very_good':   {'min': 740, 'max': 799, 'weight': 1.25}, # 1.25x odds
    'good':        {'min': 670, 'max': 739, 'weight': 1.1},  # 1.1x odds
    'fair':        {'min': 580, 'max': 669, 'weight': 1.0},  # 1.0x odds (normal)
    'poor':        {'min': 300, 'max': 579, 'weight': 0.75}, # 0.75x odds
}
```

**How It Works:**
1. User with reputation 810 (exceptional) enters giveaway
2. If reputation_weighted=true, their entry counts as 1.5x
3. Winner selection: random weighted by these multipliers
4. High reputation users have better odds

**To Modify:** Edit `/action/interactive/loyalty_interaction_module/config.py` lines 60-66

## Duel Settings

### Challenge Timeout

**DUEL_TIMEOUT_MINUTES**
- **Type:** Integer
- **Default:** `5`
- **Range:** 1-60
- **Description:** Minutes for opponent to accept challenge before expiration
- **Example:** `5` = 5 minute window to respond
- **Tips:**
  - Too short = people miss challenges
  - Too long = challenges pile up
  - 5 minutes is reasonable for fast-paced streams

## Example .env Files

### Development Setup

```bash
# .env.development
DATABASE_URL=postgresql://waddlebot:waddlebot_secret@localhost:5432/waddlebot
MODULE_PORT=8032
REDIS_URL=redis://localhost:6379

# Service integration (optional for local dev)
ROUTER_API_URL=http://localhost:8000
REPUTATION_API_URL=http://localhost:8021

# Earning defaults
DEFAULT_EARN_CHAT=1
DEFAULT_EARN_CHAT_COOLDOWN=60
DEFAULT_EARN_WATCH_TIME=2
DEFAULT_EARN_FOLLOW=50
DEFAULT_EARN_SUB_T1=500
DEFAULT_EARN_SUB_T2=1000
DEFAULT_EARN_SUB_T3=2500

# Gambling
MIN_BET=10
MAX_BET=10000

# Giveaway
GIVEAWAY_REPUTATION_FLOOR=450

# Duels
DUEL_TIMEOUT_MINUTES=5
```

### Small Community (100-500 users)

```bash
# .env.small
DATABASE_URL=postgresql://user:pass@postgres.example.com:5432/loyalty
MODULE_PORT=8032
REDIS_URL=redis://redis.example.com:6379

ROUTER_API_URL=http://router.internal:8000
REPUTATION_API_URL=http://reputation.internal:8021
SERVICE_API_KEY=sk_loyalty_xxxxxxxxxxxxx

# Lower earning to balance supply
DEFAULT_EARN_CHAT=1
DEFAULT_EARN_CHAT_COOLDOWN=120
DEFAULT_EARN_WATCH_TIME=1
DEFAULT_EARN_FOLLOW=25
DEFAULT_EARN_SUB_T1=250
DEFAULT_EARN_SUB_T2=500
DEFAULT_EARN_SUB_T3=1250

# Conservative limits
MIN_BET=5
MAX_BET=1000

GIVEAWAY_REPUTATION_FLOOR=400
DUEL_TIMEOUT_MINUTES=5
```

### Large Community (5000+ users)

```bash
# .env.large
DATABASE_URL=postgresql://user:pass@postgres-primary.example.com/loyalty
MODULE_PORT=8032
REDIS_URL=redis://redis-cluster.example.com:6379

ROUTER_API_URL=http://router.internal:8000
REPUTATION_API_URL=http://reputation.internal:8021
SERVICE_API_KEY=sk_loyalty_xxxxxxxxxxxxx

# Higher earning to keep currency valuable
DEFAULT_EARN_CHAT=2
DEFAULT_EARN_CHAT_COOLDOWN=60
DEFAULT_EARN_WATCH_TIME=3
DEFAULT_EARN_FOLLOW=100
DEFAULT_EARN_SUB_T1=1000
DEFAULT_EARN_SUB_T2=2000
DEFAULT_EARN_SUB_T3=5000

# Generous limits for established players
MIN_BET=50
MAX_BET=50000

GIVEAWAY_REPUTATION_FLOOR=500
DUEL_TIMEOUT_MINUTES=10
```

### High-Value Casino Setup

```bash
# .env.casino
DATABASE_URL=postgresql://user:pass@postgres-ha.example.com/loyalty_casino
MODULE_PORT=8032
REDIS_URL=redis://redis-sentinel.example.com:26379

ROUTER_API_URL=http://router.internal:8000
REPUTATION_API_URL=http://reputation.internal:8021
SERVICE_API_KEY=sk_loyalty_xxxxxxxxxxxxx

# Higher earning for engagement
DEFAULT_EARN_CHAT=3
DEFAULT_EARN_CHAT_COOLDOWN=30
DEFAULT_EARN_WATCH_TIME=5
DEFAULT_EARN_FOLLOW=200
DEFAULT_EARN_SUB_T1=2000
DEFAULT_EARN_SUB_T2=4000
DEFAULT_EARN_SUB_T3=10000

# Very high limits
MIN_BET=500
MAX_BET=100000

GIVEAWAY_REPUTATION_FLOOR=600
DUEL_TIMEOUT_MINUTES=10
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  loyalty:
    image: waddlebot/loyalty:latest
    ports:
      - "8032:8032"
    environment:
      DATABASE_URL: postgresql://waddlebot:waddlebot_secret@postgres:5432/waddlebot
      MODULE_PORT: 8032
      REDIS_URL: redis://redis:6379
      DEFAULT_EARN_CHAT: 1
      MIN_BET: 10
      MAX_BET: 10000
    depends_on:
      - postgres
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8032/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: waddlebot
      POSTGRES_PASSWORD: waddlebot_secret
      POSTGRES_DB: waddlebot
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## Tuning & Optimization

### For Inflation Control

If loyalty points are accumulating too fast:

1. **Reduce earning rates:**
   ```bash
   DEFAULT_EARN_CHAT=1 → 0          # Disable chat earning
   DEFAULT_EARN_SUB_T2=1000 → 500  # Cut subscription bonus
   ```

2. **Increase cooldowns:**
   ```bash
   DEFAULT_EARN_CHAT_COOLDOWN=60 → 300  # 5 min between messages
   ```

3. **Raise minimum bets:**
   ```bash
   MIN_BET=10 → 100  # More points needed to gamble
   ```

4. **Reduce giveaway duration:**
   - Shorter giveaways = less entry farming opportunities

### For Player Engagement

If players aren't earning fast enough:

1. **Increase earning rates:**
   ```bash
   DEFAULT_EARN_CHAT=1 → 3
   DEFAULT_EARN_FOLLOW=50 → 200
   ```

2. **Add bonus multipliers:**
   - Temporary 2x earn weekend events
   - Double points during special streams

3. **Lower bet limits:**
   ```bash
   MIN_BET=100 → 10  # Easier to gamble
   MAX_BET=10000 → 5000  # Less risk
   ```

4. **Frequent giveaways:**
   - Daily/hourly small giveaways
   - Better odds than big weekly ones

### For Database Performance

Check database indexes:

```sql
-- Verify indexes exist
SELECT * FROM pg_indexes WHERE schemaname = 'public' AND tablename LIKE 'loyalty%';

-- Create missing indexes if needed
CREATE INDEX idx_loyalty_balances_community_balance
  ON loyalty_balances(community_id, balance DESC);
```

### For Redis Cache Effectiveness

Monitor cache hit rate:

```bash
# Redis stats
redis-cli INFO stats | grep hits
```

**Cache TTL Tuning:**
- More cache = faster but more stale data (5-10 min OK)
- Less cache = more fresh but slower
- Balance for your use case

---

**Last Updated:** 2026-02-16
