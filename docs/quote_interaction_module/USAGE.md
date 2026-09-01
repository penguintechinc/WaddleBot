# Quote Interaction Module - Usage Guide

## Getting Started

### Prerequisites

- Python 3.13+
- PostgreSQL 14+
- Docker & Docker Compose (recommended)
- curl or Postman for API testing

### Local Development Setup

> **Note:** this module is not currently wired into the repo's `docker-compose.yml` — use manual
> setup (Option 2) for local development until it is added as a service there.

#### Option 2: Manual Setup

```bash
# 1. Clone repository
git clone https://github.com/penguintechinc/waddlebot.git
cd waddlebot

# 2. Set up Python environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r action/interactive/quote_interaction_module/requirements.txt

# 4. Configure environment
export QUOTE_MODULE_PORT=5012
export DATABASE_URL="postgresql://user:pass@localhost:5432/waddlebot"
export LOG_LEVEL=INFO

# 5. Run database migrations
python3 -c "from config.postgres.migrations import run_migrations; run_migrations()"

# 6. Start the module
python3 -m action.interactive.quote_interaction_module.app
```

## Health Check

The module provides two health endpoints for monitoring:

### Readiness Check

```bash
curl -X GET http://localhost:5012/health
```

**Response (Success - 200):**
```json
{
  "status": "healthy",
  "module": "quote_interaction_module",
  "version": "1.0.0",
  "timestamp": "2026-02-16T10:30:45Z"
}
```

### Metrics Endpoint

```bash
curl -X GET http://localhost:5012/metrics
```

Returns Prometheus-compatible metrics including:
- Request counts by endpoint
- Response time histograms
- Database connection pool usage
- Error rates

## Common Workflows

### Workflow 1: Adding a Community Quote

```bash
# Step 1: Create a quote with author information
curl -X POST http://localhost:5012/api/v1/quotes   -H "Content-Type: application/json"   -d '{
    "community_id": 42,
    "text": "The only way to do great work is to love what you do",
    "author": "Steve Jobs",
    "added_by_user_id": 123,
    "platform": "twitch",
    "context": "From a community livestream",
    "tags": ["leadership", "motivation"]
  }'

# Response:
# {
#   "id": 1,
#   "community_id": 42,
#   "quote_text": "The only way to do great work is to love what you do",
#   "author": "Steve Jobs",
#   "added_by_user_id": 123,
#   "created_at": "2026-02-16T10:30:45Z",
#   "updated_at": "2026-02-16T10:30:45Z"
# }
```

### Workflow 2: Retrieving a Random Quote

```bash
# Get a random quote to display in chat or notifications
curl -X GET "http://localhost:5012/api/v1/quotes/random/42"

# Response:
# {
#   "id": 1,
#   "community_id": 42,
#   "quote_text": "The only way to do great work is to love what you do",
#   "quoted_username": "Steve Jobs",
#   "created_at": "2026-02-16T10:30:45Z",
#   "is_approved": true
# }
```

### Workflow 3: Searching Quotes by Keyword

```bash
# Search for quotes containing "work"
curl -X GET "http://localhost:5012/api/v1/quotes/search/42?q=work&limit=10&offset=0"

# Response:
# {
#   "query": "work",
#   "quotes": [
#     {
#       "id": 1,
#       "community_id": 42,
#       "quote_text": "The only way to do great work is to love what you do",
#       "quoted_username": "Steve Jobs",
#       "is_approved": true,
#       "created_at": "2026-02-16T10:30:45Z"
#     }
#   ],
#   "pagination": {
#     "limit": 10,
#     "offset": 0,
#     "total": 1,
#     "has_more": false
#   }
# }
```

### Workflow 4: Finding All Quotes by an Author

```bash
# Get all quotes attributed to "Steve Jobs"
curl -X GET "http://localhost:5012/api/v1/quotes/author/42?author=Jobs&limit=25&offset=0"

# Response:
# {
#   "author": "Jobs",
#   "quotes": [
#     {
#       "id": 1,
#       "community_id": 42,
#       "quote_text": "The only way to do great work is to love what you do",
#       "quoted_username": "Steve Jobs",
#       "created_at": "2026-02-16T10:30:45Z"
#     }
#   ],
#   "pagination": {
#     "limit": 25,
#     "offset": 0,
#     "total": 5,
#     "has_more": false
#   }
# }
```

### Workflow 5: Listing Community Quotes with Pagination

```bash
# Get first 20 quotes, approved only
curl -X GET "http://localhost:5012/api/v1/quotes/list/42?limit=20&offset=0&approved=true"

# Response:
# {
#   "quotes": [
#     {
#       "id": 1,
#       "community_id": 42,
#       "quote_text": "The only way to do great work is to love what you do",
#       "quoted_username": "Steve Jobs",
#       "is_approved": true,
#       "created_at": "2026-02-16T10:30:45Z"
#     }
#   ],
#   "pagination": {
#     "limit": 20,
#     "offset": 0,
#     "total": 42,
#     "has_more": true
#   }
# }
```

### Workflow 6: Updating a Quote

```bash
# Correct a typo or update approval status
curl -X PUT http://localhost:5012/api/v1/quotes/1   -H "Content-Type: application/json"   -d '{
    "text": "The only way to do great work is to love what you do (corrected)",
    "is_approved": true
  }'

# Response:
# {
#   "id": 1,
#   "message": "Quote updated successfully"
# }
```

### Workflow 7: Deleting a Quote

```bash
# Soft-delete a quote (preserves audit trail)
curl -X DELETE http://localhost:5012/api/v1/quotes/1

# Response:
# {
#   "id": 1,
#   "message": "Quote deleted successfully"
# }
```

### Workflow 8: Getting Community Quote Statistics

```bash
# Get engagement statistics for a community
curl -X GET "http://localhost:5012/api/v1/quotes/stats/42"

# Response:
# {
#   "total_quotes": 150,
#   "approved_quotes": 145,
#   "pending_quotes": 5,
#   "unique_authors": 87,
#   "latest_quote_date": "2026-02-16T10:30:45Z"
# }
```

## Docker Integration

### Build Docker Image

```bash
cd action/interactive/quote_interaction_module
docker build -t waddlebot/quote-interaction:latest .
```

### Run Docker Container

```bash
docker run -d \
  --name quote-module \
  -p 5012:5012 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/waddlebot" \
  -e QUOTE_MODULE_PORT=5012 \
  -e AUTO_APPROVE_QUOTES=true \
  waddlebot/quote-interaction:latest
```

### Docker Compose Service Definition

```yaml
quote_interaction_module:
  image: waddlebot/quote-interaction:latest
  container_name: quote_module
  ports:
    - "5012:5012"
  environment:
    - DATABASE_URL=postgresql://user:pass@postgres:5432/waddlebot
    - QUOTE_MODULE_PORT=5012
    - AUTO_APPROVE_QUOTES=true
    - LOG_LEVEL=INFO
  depends_on:
    - postgres
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5012/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

## Testing the Module

### Using the test-api.sh Script

```bash
# Navigate to module directory
cd action/interactive/quote_interaction_module

# Make script executable
chmod +x test-api.sh

# Run comprehensive API tests
./test-api.sh

# This script tests:
# - Health endpoints
# - Quote creation
# - Quote retrieval
# - Search functionality
# - Author filtering
# - Pagination
# - Update and delete operations
# - Statistics
```

### Manual API Testing with curl

```bash
# Test status endpoint
curl http://localhost:5012/api/v1/status

# Test health endpoint
curl http://localhost:5012/health

# Create test quote
curl -X POST http://localhost:5012/api/v1/quotes \
  -H "Content-Type: application/json" \
  -d '{"community_id": 1, "text": "Test quote", "author": "Test Author"}'
```

## Troubleshooting Connection Issues

### Module Not Responding

```bash
# Check if module is running
curl -v http://localhost:5012/health

# View logs (module not wired into docker-compose.yml — check its own process/journal)
tail -f /var/log/waddlebotlog/quote_interaction_module.log

# Check port availability
lsof -i :5012
```

### Database Connection Issues

```bash
# Verify database is accessible
psql postgresql://user:pass@localhost:5432/waddlebot -c "SELECT 1"

# Check DATABASE_URL environment variable
echo $DATABASE_URL

# Verify migrations have run
psql postgresql://user:pass@localhost:5432/waddlebot -c "\dt quotes"
```

## Performance Tips

1. **Use pagination:** Always use limit/offset to avoid loading large result sets
2. **Search efficiently:** Use full-text search (q parameter) instead of fetching all and filtering client-side
3. **Cache random quotes:** Consider caching random quote requests for 1-5 minutes
4. **Connection pooling:** Ensure DB_POOL_SIZE is appropriately sized for your load
5. **Index coverage:** Full-text search uses tsvector index for O(log n) performance

## API Response Format

All API responses follow this standard format:

**Success Response (2xx):**
```json
{
  "status": "success",
  "data": { },
  "meta": {
    "timestamp": "2026-02-16T10:30:45Z",
    "request_id": "abc123"
  }
}
```

**Error Response (4xx/5xx):**
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Search query must be at least 2 characters"
  },
  "meta": {
    "timestamp": "2026-02-16T10:30:45Z",
    "request_id": "abc123"
  }
}
```
