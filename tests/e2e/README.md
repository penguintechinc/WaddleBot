# Waddles End-to-End (E2E) Tests

Playwright-based E2E tests for critical user workflows.

## Test Coverage

- **auth-workflow.spec.js** - Registration, login, logout flows (Waddles)
- **community-workflow.spec.js** - Community creation, viewing, management (Waddles)
- **vendor-workflow.spec.js** - Vendor submission and approval process (Waddles)

## Running Tests

```bash
# Install dependencies
cd tests/e2e
npm install
npx playwright install chromium

# Run all tests
npm test

# Run with headed browser
npm run test:headed

# Debug mode
npm run test:debug

# Interactive UI mode
npm run test:ui

# View test report
npm run report
```

## Environment Variables

```bash
BASE_URL=http://localhost:3000  # Frontend URL
```

### Local Testing

```bash
# Start services
cd /path/to/waddlebot
docker compose up -d

# Run E2E tests
cd tests/e2e
npm test
```

### Beta Testing

```bash
BASE_URL=https://waddlebot.penguintech.io npm test
```

## Test Structure

E2E tests verify complete user workflows from start to finish:

### Authentication Workflow
1. User registers with email/password
2. User verifies email (if required)
3. User logs in
4. User accesses protected pages
5. User logs out

### Community Workflow
1. Admin creates new community
2. Admin configures community settings
3. Admin links platform servers (Twitch/Discord/etc)
4. Admin installs modules
5. Members join community
6. Members interact with community features

### Vendor Workflow
1. Vendor submits module for review
2. Admin reviews submission
3. Admin approves/rejects module
4. Vendor updates module details
5. Module appears in marketplace

## Writing E2E Tests

E2E tests should:
- Test complete user journeys
- Use real UI interactions (clicks, form fills, navigation)
- Wait for page loads and async operations
- Take screenshots/videos on failure
- Clean up test data after completion

Example test:
```javascript
const { test, expect } = require('@playwright/test');

test('My workflow', async ({ page }) => {
  // Navigate
  await page.goto('/my-page');

  // Interact
  await page.fill('input[name="field"]', 'value');
  await page.click('button[type="submit"]');

  // Assert
  await expect(page.locator('.success')).toBeVisible();
});
```

## Best Practices

- Use data-testid attributes for stable selectors
- Avoid hardcoded waits (use waitForSelector instead)
- Keep tests independent (no shared state)
- Clean up test data in afterEach/afterAll
- Use descriptive test names
- Test both happy and error paths

## CI/CD Integration

Tests can be run in GitHub Actions:

```yaml
- name: Run E2E tests
  run: |
    cd tests/e2e
    npm install
    npx playwright install chromium
    BASE_URL=${{ env.BASE_URL }} npm test
```
