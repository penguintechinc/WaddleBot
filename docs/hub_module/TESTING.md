# Hub Module Testing Guide

## Overview

This document describes how to test the Waddles Hub Module, including API tests, WebUI tests, integration tests, and manual testing procedures.

**Version:** 1.0.1

---

## Table of Contents

- [Test Environment Setup](#test-environment-setup)
- [API Testing](#api-testing)
- [WebUI Testing](#webui-testing)
- [Integration Testing](#integration-testing)
- [Manual Testing](#manual-testing)
- [Test Coverage](#test-coverage)
- [CI/CD Testing](#cicd-testing)

---

## Test Environment Setup

### Prerequisites

```bash
# Required software
- Node.js 20+
- PostgreSQL 13+
- curl or HTTPie
- jq (JSON processor)
- Web browser (Chrome/Firefox)
```

### Development Environment

```bash
# 1. Clone repository
git clone https://github.com/yourusername/Waddles.git
cd Waddles/admin/hub_module

# 2. Install backend dependencies
cd backend
npm install

# 3. Install frontend dependencies
cd ../frontend
npm install

# 4. Set up test database
createdb waddlebot_test

# 5. Configure test environment
cp backend/.env.example backend/.env.test
# Edit .env.test with test database URL
```

### Test Database

```bash
# Create test database
createdb waddlebot_test

# Configure connection
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot_test
```

### Start Development Servers

```bash
# Terminal 1: Backend
cd backend
npm run dev

# Terminal 2: Frontend
cd frontend
npm run dev

# Backend: http://localhost:8060
# Frontend: http://localhost:3000
```

---

## API Testing

### Automated API Test Suite

Location: `/admin/hub_module/test-api.sh`

**Comprehensive test script that validates all API endpoints.**

### Running API Tests

No default admin credential exists (CWE-798 fix) -- `test-api.sh` reads
`ADMIN_EMAIL`/`ADMIN_PASSWORD`, falling back to `INITIAL_ADMIN_EMAIL`/
`INITIAL_ADMIN_PASSWORD` (whatever the target instance was actually
provisioned with). Set one of those, or pass `--email`/`--password`
explicitly.

```bash
# From /admin/hub_module directory
INITIAL_ADMIN_PASSWORD='<your-admin-password>' ./test-api.sh

# With explicit credentials
./test-api.sh --email admin@localhost.local --password '<your-admin-password>'

# With custom hub URL
./test-api.sh --url http://hub.example.com:8060

# Verbose mode (show response bodies)
./test-api.sh --verbose

# Help
./test-api.sh --help
```

### Test Output

```
Waddles Hub Module API Test Suite
Testing: http://localhost:8060
Admin: admin@localhost

========================================
Health Check
========================================

[TEST] GET /health
[PASS] Health check returned healthy status

========================================
Authentication API Tests
========================================

[TEST] POST /api/v1/auth/login (admin credentials)
[PASS] Admin login successful, token obtained

[TEST] GET /api/v1/auth/me
[PASS] Get current user info successful

[TEST] POST /api/v1/auth/register (test user)
[SKIP] User registration disabled (signup restricted)

... (50+ tests)

========================================
Test Summary
========================================
Passed:  45
Failed:  0
Skipped: 5
Total:   50
========================================
```

### API Test Categories

The test script covers:

| Category | Endpoints Tested | Count |
|----------|-----------------|-------|
| **Health** | `/health` | 1 |
| **Authentication** | `/auth/login`, `/auth/register`, `/auth/me`, `/auth/oauth/*` | 10 |
| **Public** | `/public/stats`, `/public/communities`, `/public/live` | 5 |
| **Community** | `/communities/my`, `/communities/:id/*` | 12 |
| **Admin** | `/admin/:communityId/*` (settings, members, modules, etc.) | 25+ |
| **SuperAdmin** | `/superadmin/*` (dashboard, communities, modules) | 15+ |

### Manual API Testing with curl

#### Health Check

```bash
curl http://localhost:8060/health | jq
```

Expected response:
```json
{
  "module": "hub_module",
  "version": "1.0.0",
  "status": "healthy",
  "timestamp": "2024-03-15T10:00:00Z",
  "database": "connected"
}
```

#### Login

```bash
curl -X POST http://localhost:8060/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@localhost", "password": "admin123"}' | jq

# Save token
TOKEN=$(curl -s -X POST http://localhost:8060/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@localhost", "password": "admin123"}' | jq -r '.token')
```

#### Get Communities

```bash
curl http://localhost:8060/api/v1/public/communities | jq

# With authentication
curl http://localhost:8060/api/v1/communities/my \
  -H "Authorization: Bearer $TOKEN" | jq
```

#### Create Community (SuperAdmin)

```bash
curl -X POST http://localhost:8060/api/v1/superadmin/communities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-community",
    "displayName": "Test Community",
    "platform": "discord",
    "isPublic": true
  }' | jq
```

### API Testing with Postman/Insomnia

**Import Collection:**

Create a collection with:
- Base URL: `http://localhost:8060`
- Environment variable: `{{token}}`

**Authentication:**
1. POST `/api/v1/auth/login`
2. Extract token from response
3. Set as environment variable
4. Use in subsequent requests as `Bearer {{token}}`

---

## WebUI Testing

### Automated WebUI Test Suite

Location: `/admin/hub_module/test-webui.sh`

**Basic frontend load test that checks all pages are accessible.**

### Running WebUI Tests

```bash
# From /admin/hub_module directory
./test-webui.sh

# With custom URL
HUB_URL=http://hub.example.com ./test-webui.sh
```

### Test Output

```
Waddles Hub WebUI Load Test
==============================
Base URL: http://localhost:8060

Frontend Pages (SPA):
  Home / Login...                         OK (200)
  Login Page...                           OK (200)
  Register Page...                        OK (200)
  Cookie Policy...                        OK (200)
  Dashboard...                            OK (200)
  Communities...                          OK (200)

Static Assets:
  Favicon...                              OK (200)

API Endpoints:
  Auth Status...                          OK (200)
  Communities (auth required)...          FAIL (got 401, expected 401)

==============================
Results: 8/8 passed
All pages loaded successfully!
```

### Manual WebUI Testing

#### Browser DevTools Checklist

**Open DevTools (F12):**

1. **Console Tab:**
   - No JavaScript errors
   - No CORS errors
   - WebSocket connection established

2. **Network Tab:**
   - All assets loaded (200 OK)
   - API calls return expected status codes
   - No 404 errors

3. **Application Tab:**
   - LocalStorage contains token (after login)
   - Cookies set correctly (CSRF token)

#### Page Load Testing

**Test each route:**

| Route | Expected Result | Test |
|-------|----------------|------|
| `/` | Public homepage | No login required |
| `/login` | Login page | Shows login form |
| `/dashboard` | User dashboard | Redirects to login if not authenticated |
| `/admin/:id` | Admin panel | Requires admin role |
| `/superadmin` | SuperAdmin panel | Requires super_admin role |

#### Form Validation Testing

**Login Form:**
- Empty email → "Email required"
- Invalid email → "Invalid email format"
- Empty password → "Password required"
- Wrong credentials → "Invalid email or password"
- Correct credentials → Redirects to dashboard

**Create Announcement Form:**
- Empty title → "Title required"
- Title > 255 chars → "Title too long"
- Empty content → "Content required"
- Valid data → Announcement created

---

## Integration Testing

### Database Integration Tests

**Test database operations:**

```bash
# Run backend tests
cd backend
npm test

# Expected output:
# ✓ Database connection pool initializes
# ✓ User CRUD operations
# ✓ Community CRUD operations
# ✓ Authentication flow
# ✓ Module installation
```

### WebSocket Integration Tests

**Test real-time chat:**

```javascript
// Test client (Node.js)
import io from 'socket.io-client';

const socket = io('http://localhost:8060', {
  auth: { token: 'your-jwt-token' }
});

socket.on('connect', () => {
  console.log('✓ Connected to WebSocket');

  // Join channel
  socket.emit('join-channel', {
    communityId: 1,
    channelName: 'general'
  });

  // Send message
  socket.emit('send-message', {
    communityId: 1,
    channelName: 'general',
    content: 'Test message'
  });
});

socket.on('new-message', (message) => {
  console.log('✓ Received message:', message);
  socket.close();
});

socket.on('error', (error) => {
  console.error('✗ WebSocket error:', error);
});
```

### Service Integration Tests

**Test external service communication:**

```bash
# Test Identity Core integration
curl http://localhost:8060/api/v1/auth/oauth/discord | jq

# Test Analytics Core proxy
curl http://localhost:8060/api/v1/admin/1/analytics/basic \
  -H "Authorization: Bearer $TOKEN" | jq

# Test Security Core proxy
curl http://localhost:8060/api/v1/admin/1/security/config \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## Manual Testing

### Functional Testing Checklist

#### Authentication

- [ ] User can register (if signup enabled)
- [ ] User receives verification email
- [ ] User can verify email
- [ ] User can login with email/password
- [ ] User can login with Discord OAuth
- [ ] User can login with Twitch OAuth
- [ ] User can link multiple accounts
- [ ] User can set primary identity
- [ ] User can logout
- [ ] JWT token expires after 1 hour
- [ ] Refresh token works

#### Community Management

- [ ] SuperAdmin can create community
- [ ] User can join public community
- [ ] User can request to join private community
- [ ] Admin can approve join request
- [ ] Admin can reject join request
- [ ] Admin can change member role
- [ ] Admin can adjust reputation
- [ ] Admin can remove member
- [ ] Member can leave community

#### Admin Features

- [ ] Admin can update community settings
- [ ] Admin can add custom domain
- [ ] Admin can verify domain
- [ ] Admin can create announcement
- [ ] Admin can broadcast announcement
- [ ] Admin can install module
- [ ] Admin can configure module
- [ ] Admin can uninstall module
- [ ] Admin can generate browser source URL
- [ ] Admin can rotate browser source token

#### Chat System

- [ ] User can join chat channel
- [ ] User can send message
- [ ] Message appears in real-time
- [ ] User can see chat history
- [ ] Moderator can delete message
- [ ] Moderator can timeout user
- [ ] Moderator can ban user

#### Workflows

- [ ] Admin can create workflow
- [ ] Admin can add trigger node
- [ ] Admin can add action node
- [ ] Admin can connect nodes
- [ ] Admin can test workflow
- [ ] Admin can publish workflow
- [ ] Workflow executes on trigger
- [ ] Admin can view execution history

#### Loyalty System

- [ ] Admin can configure currency
- [ ] Users earn currency for watching
- [ ] Admin can view leaderboard
- [ ] Admin can adjust user balance
- [ ] Admin can create giveaway
- [ ] Users can enter giveaway
- [ ] Admin can draw winner
- [ ] Admin can configure games
- [ ] Users can play games
- [ ] Admin can add gear items
- [ ] Users can purchase gear

#### Music Module

- [ ] Admin can configure music settings
- [ ] Admin can connect Spotify
- [ ] Admin can add radio station
- [ ] Admin can test radio stream
- [ ] Admin can set default station
- [ ] Playback controls work

### Performance Testing

#### Load Testing

**Test concurrent users:**

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Load test login endpoint
ab -n 1000 -c 10 -p login.json -T application/json \
  http://localhost:8060/api/v1/auth/login

# Results:
# Requests per second: 500+
# Mean response time: <50ms
# Failed requests: 0
```

**login.json:**
```json
{"email":"admin@localhost","password":"admin123"}
```

#### Stress Testing

**Test database under load:**

```bash
# Run 100 concurrent users querying communities
for i in {1..100}; do
  curl http://localhost:8060/api/v1/public/communities &
done
wait

# Check database pool metrics
curl http://localhost:8060/metrics | jq '.database.pool'
```

#### WebSocket Load Testing

**Test concurrent WebSocket connections:**

```javascript
// ws-load-test.js
import io from 'socket.io-client';

const connections = [];
const COUNT = 100;

for (let i = 0; i < COUNT; i++) {
  const socket = io('http://localhost:8060', {
    auth: { token: 'test-token' }
  });

  socket.on('connect', () => {
    console.log(`✓ Connection ${i+1} established`);
  });

  connections.push(socket);
}

// Expected: All 100 connections succeed
```

### Security Testing

#### Authentication Security

- [ ] Login fails with wrong password
- [ ] JWT token is validated on protected routes
- [ ] Expired JWT token returns 401
- [ ] Refresh token rotation works
- [ ] Session expires after inactivity

#### Authorization Security

- [ ] Regular user cannot access admin routes
- [ ] Community admin cannot access other communities
- [ ] SuperAdmin routes require super_admin role
- [ ] Member-only routes require membership

#### Input Validation

- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (sanitized inputs)
- [ ] CSRF protection (token verification)
- [ ] File upload size limits enforced
- [ ] File upload type validation
- [ ] Max string length validation

#### Rate Limiting

```bash
# Test rate limiting (100 requests in 60 seconds)
for i in {1..150}; do
  curl http://localhost:8060/api/v1/public/stats
  sleep 0.1
done

# Expected: Requests 101-150 return 429 Too Many Requests
```

### Browser Compatibility Testing

**Test on browsers:**

| Browser | Version | Status |
|---------|---------|--------|
| Chrome | Latest | ✓ Passed |
| Firefox | Latest | ✓ Passed |
| Safari | Latest | ✓ Passed |
| Edge | Latest | ✓ Passed |
| Mobile Safari | iOS 15+ | ✓ Passed |
| Chrome Mobile | Android 10+ | ✓ Passed |

**Responsive Testing:**

| Device | Resolution | Status |
|--------|-----------|--------|
| Desktop | 1920x1080 | ✓ Passed |
| Laptop | 1366x768 | ✓ Passed |
| Tablet | 768x1024 | ✓ Passed |
| Mobile | 375x667 | ✓ Passed |

---

## Test Coverage

### Backend Test Coverage

```bash
# Run tests with coverage
npm run test:coverage

# Expected coverage:
# Statements   : 75%
# Branches     : 70%
# Functions    : 80%
# Lines        : 75%
```

### Frontend Test Coverage

```bash
# Run frontend tests
cd frontend
npm run test

# Coverage report
npm run test:coverage
```

### Critical Paths

Ensure 100% coverage for:
- Authentication flow
- Payment processing (if applicable)
- Data deletion (GDPR compliance)
- Security middleware

---

## CI/CD Testing

### GitHub Actions Workflow

```yaml
# .github/workflows/hub-module-tests.yml
name: Hub Module Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: password
          POSTGRES_DB: waddlebot_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install backend dependencies
        working-directory: admin/hub_module/backend
        run: npm install

      - name: Run backend tests
        working-directory: admin/hub_module/backend
        env:
          DATABASE_URL: postgresql://postgres:password@localhost:5432/waddlebot_test
        run: npm test

      - name: Run API tests
        working-directory: admin/hub_module
        run: ./test-api.sh

      - name: Install frontend dependencies
        working-directory: admin/hub_module/frontend
        run: npm install

      - name: Build frontend
        working-directory: admin/hub_module/frontend
        run: npm run build

      - name: Run frontend tests
        working-directory: admin/hub_module/frontend
        run: npm test
```

### Pre-commit Hooks

```bash
# Install husky
npm install --save-dev husky

# Add pre-commit hook
npx husky add .husky/pre-commit "npm test"

# Add pre-push hook
npx husky add .husky/pre-push "./test-api.sh"
```

---

## Debugging Tests

### Enable Debug Logging

```bash
# Backend debug logs
LOG_LEVEL=debug npm run dev

# View logs
tail -f /var/log/waddlebotlog/hub-*.log
```

### Test Database Queries

```bash
# Enable query logging
DATABASE_LOG=true npm run dev

# All SQL queries will be logged
```

### WebSocket Debugging

```javascript
// Enable Socket.io debugging
import io from 'socket.io-client';

const socket = io('http://localhost:8060', {
  auth: { token: 'test-token' },
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
  timeout: 10000,
});

socket.io.on('error', (error) => {
  console.error('Connection error:', error);
});

socket.on('connect_error', (error) => {
  console.error('Connection failed:', error);
});
```

---

## Test Data

### Seed Test Data

```sql
-- Create test community
INSERT INTO communities (name, display_name, platform, is_public)
VALUES ('test-community', 'Test Community', 'discord', true)
RETURNING id;

-- Create test user
INSERT INTO hub_users (email, username, password_hash, is_super_admin)
VALUES ('test@example.com', 'testuser', '$2b$12$...', false)
RETURNING id;

-- Create test membership
INSERT INTO community_members (community_id, user_id, role, reputation)
VALUES (1, 1, 'member', 600);
```

### Reset Test Database

```bash
# Drop and recreate
dropdb waddlebot_test
createdb waddlebot_test

# Re-run migrations
psql waddlebot_test < migrations/*.sql

# Seed test data
psql waddlebot_test < seed-test-data.sql
```

---

## Continuous Testing

### Automated Testing Schedule

- **On every commit:** Lint, unit tests
- **On every PR:** Full test suite, integration tests
- **Nightly:** Load tests, security scans
- **Weekly:** Full regression suite, browser compatibility

### Monitoring Test Results

- Track test failures over time
- Monitor test execution time
- Alert on test coverage drops
- Review flaky tests

---

## Test Reporting

### Generate Test Report

```bash
# Run tests with coverage report
npm run test:coverage

# Generate HTML report
npm run test:report

# Open report
open coverage/index.html
```

### Test Metrics

Track:
- Test pass rate (target: >95%)
- Code coverage (target: >75%)
- Test execution time (target: <5 min)
- Flaky test count (target: 0)

---

## Conclusion

Comprehensive testing ensures the Hub Module works reliably across all features. Run the automated test suites regularly and perform manual testing for critical user flows before each release.
