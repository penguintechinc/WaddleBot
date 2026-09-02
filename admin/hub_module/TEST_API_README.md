# WaddleBot Hub Module API Test Suite

Comprehensive API test script for the WaddleBot Hub Module.

## Features

- **Complete API Coverage**: Tests all Hub Module endpoints including auth, community, admin, and superadmin APIs
- **Color-Coded Output**: Green (pass), Red (fail), Yellow (skip) for easy reading
- **CI/CD Friendly**: Non-interactive, returns proper exit codes
- **Flexible Configuration**: Environment variables and command-line options
- **Smart Test Flow**: Authenticates once, reuses token, creates test data as needed
- **Clean Summary**: Detailed pass/fail/skip statistics

## Prerequisites

- `bash` (4.0+)
- `curl`
- `jq` (JSON processor)
- Running Hub Module instance

## Installation

The script is self-contained. Just make it executable:

```bash
chmod +x test-api.sh
```

## Usage

### Basic Usage

Run against default local instance (http://localhost:8060):

```bash
./test-api.sh
```

### Custom URL

```bash
./test-api.sh --url http://hub.example.com:8060
```

### Custom Credentials

```bash
./test-api.sh --email admin@example.com --password mypassword
```

### Using Environment Variables

```bash
export HUB_URL=http://hub.example.com:8060
export ADMIN_EMAIL=admin@example.com
export ADMIN_PASSWORD=mypassword
./test-api.sh
```

### Verbose Mode

Show full response bodies (useful for debugging):

```bash
./test-api.sh --verbose
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-h, --help` | Show help message | - |
| `-u, --url URL` | Hub module URL | `http://localhost:8060` |
| `-e, --email EMAIL` | Admin email | `$INITIAL_ADMIN_EMAIL`, or `admin@localhost.local` |
| `-p, --password PASS` | Admin password | `$INITIAL_ADMIN_PASSWORD`, if set (no hardcoded default -- CWE-798 fix) |
| `-v, --verbose` | Show response bodies | `false` |

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed

## Test Categories

### 1. Health Check
- `GET /health` - Verify service is running

### 2. Authentication API
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - Admin login
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/auth/verify-email` - Email verification
- `POST /api/v1/auth/resend-verification` - Resend verification email

### 3. Public API
- `GET /api/v1/public/stats` - Platform statistics
- `GET /api/v1/public/communities` - List public communities
- `GET /api/v1/public/communities/:id` - Get specific community
- `GET /api/v1/public/live` - Live streams
- `GET /api/v1/public/signup-settings` - Signup settings

### 4. Community API (Authenticated)
- `GET /api/v1/community/my` - User's communities
- `POST /api/v1/community/:id/join` - Join community
- `GET /api/v1/community/:id/dashboard` - Community dashboard
- `GET /api/v1/community/:id/servers` - Community servers
- `GET /api/v1/community/:id/modules` - Installed modules
- `GET /api/v1/community/:id/leaderboard` - Leaderboard
- `GET /api/v1/community/:id/activity` - Activity feed
- `GET /api/v1/community/:id/events` - Events
- `GET /api/v1/community/:id/memories` - Memories
- `GET /api/v1/community/:id/chat/history` - Chat history
- `GET /api/v1/community/:id/chat/channels` - Chat channels

### 5. Admin API (Community Admin)
- `GET /api/v1/admin/:communityId/members` - List members
- `PUT /api/v1/admin/:communityId/members/:userId/role` - Update member role
- `DELETE /api/v1/admin/:communityId/members/:userId` - Remove member
- `GET /api/v1/admin/:communityId/settings` - Community settings
- `PUT /api/v1/admin/:communityId/settings` - Update settings
- `GET /api/v1/admin/:communityId/servers` - Linked servers
- `GET /api/v1/admin/:communityId/server-link-requests` - Server link requests
- `POST /api/v1/admin/:communityId/server-link-requests/:id/approve` - Approve request
- `POST /api/v1/admin/:communityId/server-link-requests/:id/reject` - Reject request
- `DELETE /api/v1/admin/:communityId/servers/:id` - Remove server
- `GET /api/v1/admin/:communityId/mirror-groups` - List mirror groups
- `POST /api/v1/admin/:communityId/mirror-groups` - Create mirror group
- `GET /api/v1/admin/:communityId/mirror-groups/:id` - Get mirror group
- `PUT /api/v1/admin/:communityId/mirror-groups/:id` - Update mirror group
- `DELETE /api/v1/admin/:communityId/mirror-groups/:id` - Delete mirror group
- `GET /api/v1/admin/:communityId/modules` - Admin modules
- `GET /api/v1/admin/:communityId/browser-sources` - Browser sources
- `POST /api/v1/admin/:communityId/temp-password` - Generate temp password

### 6. SuperAdmin API
- `GET /api/v1/superadmin/dashboard` - Dashboard stats
- `GET /api/v1/superadmin/communities` - List all communities
- `POST /api/v1/superadmin/communities` - Create community
- `GET /api/v1/superadmin/communities/:id` - Get community
- `PUT /api/v1/superadmin/communities/:id` - Update community
- `DELETE /api/v1/superadmin/communities/:id` - Delete community
- `GET /api/v1/superadmin/settings` - Hub settings
- `PUT /api/v1/superadmin/settings` - Update hub settings
- `GET /api/v1/superadmin/marketplace/modules` - All modules
- `GET /api/v1/superadmin/platform-config` - Platform configs

## CI/CD Integration

### GitLab CI

```yaml
test:api:
  stage: test
  script:
    - ./admin/hub_module/test-api.sh --url $HUB_URL
  only:
    - merge_requests
```

### GitHub Actions

```yaml
- name: Run API Tests
  run: |
    cd admin/hub_module
    ./test-api.sh --url http://localhost:8060
```

### Jenkins

```groovy
stage('API Tests') {
    steps {
        sh './admin/hub_module/test-api.sh --url ${HUB_URL}'
    }
}
```

## Test Output Example

```
WaddleBot Hub Module API Test Suite
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

...

========================================
Test Summary
========================================
Passed:  47
Failed:  0
Skipped: 8
Total:   55
========================================
```

## Troubleshooting

### Connection Refused

Ensure the Hub Module is running:

```bash
docker ps | grep hub_module
# or
curl http://localhost:8060/health
```

### Authentication Failed

Verify admin credentials:

```bash
# Check database
docker exec -it postgres psql -U waddlebot -d waddlebot \
  -c "SELECT email, is_super_admin FROM hub_users WHERE email='admin@localhost';"
```

### jq Command Not Found

Install jq:

```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq

# Alpine
apk add jq
```

## Development

### Adding New Tests

Add tests in the appropriate section:

```bash
print_test "GET /api/v1/new/endpoint"
if response=$(api_call GET /api/v1/new/endpoint "" 200 true); then
    print_pass "New endpoint test successful"
else
    print_fail "New endpoint test failed"
fi
```

### Test Structure

Each test follows this pattern:
1. Print test description
2. Make API call with expected status code
3. Validate response (optional)
4. Print pass/fail/skip

## Notes

- Tests requiring admin/superadmin permissions will be skipped if user lacks privileges
- Some tests create temporary data (communities, mirror groups) which are cleaned up
- The script maintains state across tests (auth token, discovered IDs)
- Failed tests don't stop execution - all tests run to completion

## License

Part of WaddleBot project. See main project LICENSE for details.
