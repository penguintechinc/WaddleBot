# AI Researcher Module — Troubleshooting Guide

## Common Issues & Solutions

### 1. Module Fails to Start

**Symptom:** Container exits immediately or `hypercorn` doesn't bind to port

**Diagnosis:**
```bash
# Check logs
docker logs ai-researcher

# Verify port availability
lsof -i :8070

# Test configuration
python -c "from config import Config; Config.validate()"
```

**Solutions:**

**Port Already in Use:**
```bash
# Find process using port
lsof -i :8070

# Kill process or use different port
kill <PID>
# OR
export MODULE_PORT=8071
```

**Configuration Error:**
```bash
# Check .env file exists and is readable
cat .env | grep DATABASE_URL

# Validate all required variables are set
python -c "from config import Config; print(Config.DATABASE_URL)"
```

**Database Connection Failed:**
```bash
# Test PostgreSQL connection
psql postgresql://waddlebot:password@localhost:5432/waddlebot -c "SELECT 1"

# Check connection string format
# Should be: postgresql://user:pass@host:port/database
```

---

### 2. Rate Limiting Errors (HTTP 429)

**Symptom:** Requests return `429 Too Many Requests`

**Diagnosis:**
```bash
# Check Redis connection
redis-cli ping

# Check current rate limit settings
curl http://localhost:8070/api/v1/status | jq .rate_limits

# Monitor rate limiter
docker logs ai-researcher | grep "rate_limit"
```

**Solutions:**

**Redis Connection Lost:**
```bash
# Verify Redis is running
redis-cli ping
# Expected: PONG

# Check Redis URL
echo $REDIS_URL
# Should be: redis://host:port/db

# Fallback to database
# Module automatically uses database if Redis unavailable
# Check logs for: "Rate limiter initialized with database fallback"
```

**Rate Limits Too Strict:**
```bash
# Increase limits for testing
export RATE_LIMIT_RESEARCH=100
export RATE_LIMIT_MEMORY=300
export GLOBAL_RATE_LIMIT_RESEARCH=1000

# Restart module
docker restart ai-researcher
```

**Verify Rate Limit Configuration:**
```bash
curl http://localhost:8070/api/v1/status | jq '.config.rate_limits'
```

---

### 3. "Provider Error" or AI Generation Fails

**Symptom:** Research queries return provider error or empty responses

**Diagnosis:**
```bash
# Check AI provider logs
docker logs ollama  # If using Ollama
# OR
echo "WADDLEAI_API_KEY: $WADDLEAI_API_KEY"  # If using WaddleAI

# Test provider directly
curl http://ollama:11434/api/tags  # Ollama
# OR
curl -H "Authorization: Bearer $WADDLEAI_API_KEY" \
  http://waddleai-proxy:8000/api/v1/models  # WaddleAI

# Check module config
curl http://localhost:8070/api/v1/status | jq '.config.ai_provider'
```

**Solutions:**

**Ollama Not Responding:**
```bash
# Verify Ollama is running
curl http://ollama:11434/api/tags

# Check if model exists
ollama list

# Pull missing model
ollama pull tinyllama

# Check Ollama logs
docker logs ollama

# Verify connectivity from module container
docker exec ai-researcher curl http://ollama:11434/api/tags
```

**WaddleAI Authentication Failed:**
```bash
# Check API key format (must start with wa-)
echo $WADDLEAI_API_KEY | grep "^wa-"

# Verify API key is valid
curl -H "Authorization: Bearer $WADDLEAI_API_KEY" \
  http://waddleai-proxy:8000/api/v1/auth/verify

# Check API key in logs (never share publicly)
docker logs ai-researcher | grep "WADDLEAI"
```

**Model Not Loaded:**
```bash
# List available models
ollama list
# OR for WaddleAI
curl http://waddleai-proxy:8000/api/v1/models

# Load model (Ollama)
ollama pull llama2

# Update config with available model
export OLLAMA_MODEL=llama2
docker restart ai-researcher
```

**Network Issues:**
```bash
# Test connectivity from module
docker exec ai-researcher curl -v http://ollama:11434/api/tags

# Check Docker network
docker network inspect waddlebot-network

# Verify service endpoints
docker ps | grep -E "ollama|waddleai|postgres"
```

---

### 4. Qdrant/mem0 Errors

**Symptom:** Memory operations fail, "Connection to Qdrant failed"

**Diagnosis:**
```bash
# Test Qdrant connectivity
curl http://qdrant:6333/health

# Check collection
curl http://qdrant:6333/collections/ai_researcher_memory

# Monitor Qdrant logs
docker logs qdrant

# Check module configuration
curl http://localhost:8070/api/v1/status | jq '.checks.qdrant'
```

**Solutions:**

**Qdrant Not Running:**
```bash
# Start Qdrant
docker run -d \
  --name qdrant \
  --network waddlebot-network \
  -p 6333:6333 \
  qdrant/qdrant:latest

# Verify health
curl http://localhost:6333/health
```

**Collection Missing:**
```bash
# Create collection
curl -X PUT http://qdrant:6333/collections/ai_researcher_memory \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
  }'

# Verify
curl http://qdrant:6333/collections/ai_researcher_memory
```

**Embedding Model Issues:**
```bash
# Check embedder configuration
echo $MEM0_EMBEDDER_PROVIDER
echo $MEM0_EMBEDDER_MODEL

# Verify embedder is available
ollama list | grep $MEM0_EMBEDDER_MODEL

# Pull if missing
ollama pull nomic-embed-text

# Restart module
docker restart ai-researcher
```

**Vector Dimension Mismatch:**
```bash
# Check collection vector size
curl http://qdrant:6333/collections/ai_researcher_memory | jq '.result.config.params.vectors.size'

# Check embedder output dimension
# nomic-embed-text: 384 dimensions
# all-minilm: 384 dimensions
# all-mpnet-base-v2: 768 dimensions

# If mismatch, recreate collection with correct dimensions
curl -X DELETE http://qdrant:6333/collections/ai_researcher_memory
# Then restart module to recreate with correct dimensions
```

---

### 5. Database Connection Issues

**Symptom:** "Failed to connect to database" or query timeouts

**Diagnosis:**
```bash
# Test PostgreSQL directly
psql $DATABASE_URL -c "SELECT version()"

# Check connection pool status
docker logs ai-researcher | grep "pool"

# Monitor active connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Check for long-running queries
psql $DATABASE_URL -c "SELECT pid, query, query_start FROM pg_stat_activity WHERE state != 'idle';"
```

**Solutions:**

**Connection String Invalid:**
```bash
# Format check
# postgresql://user:password@host:port/database

# Test each component
# 1. Host reachable
ping localhost

# 2. Port accessible
nc -zv localhost 5432

# 3. Credentials valid
psql -U waddlebot -h localhost -d waddlebot -c "SELECT 1"

# 4. Full string works
psql postgresql://waddlebot:password@localhost:5432/waddlebot -c "SELECT 1"
```

**Connection Pool Exhausted:**
```bash
# Increase pool size
export DB_POOL_SIZE=40
export DB_MAX_OVERFLOW=80

# Restart module
docker restart ai-researcher

# Monitor pool usage
docker logs ai-researcher | grep "pool"
```

**Database Down:**
```bash
# Check PostgreSQL status
docker ps | grep postgres

# Restart PostgreSQL
docker restart postgres

# Verify connectivity
psql postgresql://waddlebot:password@localhost:5432/waddlebot -c "SELECT 1"
```

**Missing Tables:**
```bash
# Run migrations
python scripts/migrate.py --db $DATABASE_URL

# Check if tables exist
psql $DATABASE_URL -c "\dt ai_*"

# If missing, create tables manually
psql $DATABASE_URL < schema/ai_researcher_tables.sql
```

---

### 6. High Latency or Timeouts

**Symptom:** Requests take >5 seconds or timeout

**Diagnosis:**
```bash
# Measure endpoint latency
time curl -X POST http://localhost:8070/api/v1/researcher/research \
  -H "Content-Type: application/json" \
  -d '{"community_id": 123, "user_id": 456, "query": "test"}'

# Check processing_time_ms in response
# High value = slow LLM response

# Monitor system resources
docker stats ai-researcher

# Check database query performance
docker logs ai-researcher | grep "query.*ms"
```

**Solutions:**

**Slow LLM Response:**
```bash
# Use faster model
export OLLAMA_MODEL=tinyllama  # Faster
# vs
export OLLAMA_MODEL=llama2  # Slower but better quality

# Reduce max tokens
export OLLAMA_MAX_TOKENS=1000  # Default: 2000

# Increase timeout
export LLM_REQUEST_TIMEOUT=120  # Default: 60

# Check LLM CPU/memory
docker stats ollama
```

**Database Query Slow:**
```bash
# Add indexes
psql $DATABASE_URL -c "CREATE INDEX idx_context_community ON ai_context_messages(community_id);"

# Check query plans
psql $DATABASE_URL -c "EXPLAIN ANALYZE SELECT * FROM ai_context_messages WHERE community_id = 123 LIMIT 100;"

# Increase pool size
export DB_POOL_SIZE=40
```

**High Concurrency:**
```bash
# Increase workers
# In docker-compose.yml or Dockerfile:
# CMD ["hypercorn", "app:app", "--workers", "8"]

# Or via environment
export HYPERCORN_WORKERS=8

# Increase LLM concurrency
export MAX_CONCURRENT_LLM_CALLS=20  # Default: 10
export LLM_QUEUE_SIZE=200  # Default: 100
```

---

### 7. Memory/Cache Issues

**Symptom:** Out of memory, cache not working, stale data

**Diagnosis:**
```bash
# Check Redis memory
redis-cli info memory

# Check module memory usage
docker stats ai-researcher

# Verify cache is being used
docker logs ai-researcher | grep "cache"

# Check Redis key count
redis-cli dbsize

# Monitor cache hit rate
docker logs ai-researcher | grep "was_cached"
```

**Solutions:**

**Redis Memory Full:**
```bash
# Check Redis config
redis-cli config get maxmemory

# Increase maxmemory
redis-cli config set maxmemory 2gb

# Clear old keys
redis-cli FLUSHDB

# Enable eviction
redis-cli config set maxmemory-policy allkeys-lru
```

**Cache Not Working:**
```bash
# Verify Redis connection
redis-cli ping
# Expected: PONG

# Check if semantic caching is enabled
echo $ENABLE_SEMANTIC_CACHE

# Clear cache to test
redis-cli FLUSHDB

# Restart module
docker restart ai-researcher

# Make request and check response
curl http://localhost:8070/api/v1/researcher/research \
  ... | jq '.was_cached'
# First time: false, second time: true (if cache working)
```

**Stale Cache Data:**
```bash
# Reduce TTL for fresh data
export CACHE_TTL_RESEARCH=600  # 10 minutes instead of 60

# Or clear entire cache
redis-cli FLUSHDB

# Restart module
docker restart ai-researcher
```

---

### 8. Bot Detection False Positives/Negatives

**Symptom:** Legitimate users flagged as bots or bots not detected

**Diagnosis:**
```bash
# Check detection results
curl http://localhost:8070/api/v1/admin/123/bot-detection?limit=20

# Check threshold
echo $BOT_DETECTION_THRESHOLD

# Review flagged users
curl http://localhost:8070/api/v1/admin/123/bot-detection?flagged_only=true
```

**Solutions:**

**Adjust Threshold:**
```bash
# Lower threshold (more sensitive, more false positives)
export BOT_DETECTION_THRESHOLD=0.5

# Higher threshold (less sensitive, misses real bots)
export BOT_DETECTION_THRESHOLD=0.8

# Restart module
docker restart ai-researcher
```

**Update Detection Models:**
```bash
# Retrain behavior patterns
curl -X POST http://localhost:8070/api/v1/admin/123/bot-detection/retrain \
  -H "X-Service-Key: $SERVICE_API_KEY"

# Review and acknowledge flagged accounts
curl -X POST http://localhost:8070/api/v1/researcher/123/anomalies/1/acknowledge \
  -H "Content-Type: application/json" \
  -d '{"admin_id": 789, "notes": "False positive - real user"}'
```

---

### 9. Sentiment Analysis Inaccuracy

**Symptom:** Sentiment scores don't match community feel

**Diagnosis:**
```bash
# Get current sentiment
curl http://localhost:8070/api/v1/researcher/123/sentiment?timeframe=7d

# Check message volume
curl http://localhost:8070/api/v1/researcher/123/context?limit=1000

# Review analyzer configuration
docker logs ai-researcher | grep sentiment
```

**Solutions:**

**Use Better Model:**
```bash
# Use advanced sentiment model with WaddleAI
export AI_PROVIDER=waddleai
export WADDLEAI_PREFERRED_MODEL=gpt-4

# Restart
docker restart ai-researcher
```

**Increase Context Window:**
```bash
# Use more messages for analysis
export RESEARCH_MAX_CONTEXT_MESSAGES=500  # Default: 100

docker restart ai-researcher
```

---

### 10. Performance Under Load

**Symptom:** Module slows down with many concurrent users

**Diagnosis:**
```bash
# Load test
ab -n 100 -c 10 http://localhost:8070/api/v1/status

# Monitor during load
docker stats ai-researcher

# Check queue length
docker logs ai-researcher | grep queue
```

**Solutions:**

**Horizontal Scaling:**
```bash
# Run multiple instances behind load balancer
docker run -d -p 8071:8070 waddlebot/ai-researcher:latest
docker run -d -p 8072:8070 waddlebot/ai-researcher:latest

# Configure load balancer to distribute requests
```

**Increase Concurrency:**
```bash
export MAX_CONCURRENT_LLM_CALLS=30
export DB_POOL_SIZE=60
export BATCH_WORKER_THREADS=15
export THREAD_POOL_WORKERS=40

docker restart ai-researcher
```

**Enable Caching Aggressively:**
```bash
export ENABLE_SEMANTIC_CACHE=true
export SEMANTIC_CACHE_THRESHOLD=0.85  # More lenient
export CACHE_TTL_RESEARCH=3600

docker restart ai-researcher
```

---

## Getting Help

### Collect Diagnostic Information

```bash
# Gather logs
docker logs ai-researcher > logs.txt

# Collect configuration (sanitized)
env | grep -E "AI_|DATABASE|REDIS|QDRANT" > config.txt

# System info
docker stats ai-researcher > stats.txt
docker inspect ai-researcher > container.json

# Database info
psql $DATABASE_URL -c "\dt ai_*" > schema.txt
psql $DATABASE_URL -c "SELECT COUNT(*) FROM ai_context_messages;" > message_count.txt
```

### Support Channels

- **Issues:** Post diagnostic info in #waddlebot-dev
- **Email:** support@penguintech.io
- **Documentation:** See [OVERVIEW.md](OVERVIEW.md) for full docs

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
export ENABLE_AAA_LOGGING=true

docker restart ai-researcher

# Tail logs
docker logs -f ai-researcher | grep -E "DEBUG|ERROR|WARN"
```
