/**
 * Community Creation Smoke Tests
 *
 * Critical path: login → communities page → create community form → submit → dashboard
 *
 * These tests use network interception to capture the exact API response and error,
 * making it easy to diagnose failures without needing browser DevTools.
 *
 * Environment variables:
 *   BASE_URL        - Default: http://localhost:3000
 *   HUB_TEST_EMAIL  - Test user email (default: admin@localhost.local)
 *   HUB_TEST_PASS   - Test user password (default: admin123)
 */

const { test, expect } = require('@playwright/test');

const TEST_EMAIL = process.env.HUB_TEST_EMAIL || 'admin@localhost.local';
const TEST_PASS = process.env.HUB_TEST_PASS || 'admin123';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Log in via the hub email/password form.
 * Returns true if login succeeded, throws on failure.
 */
async function loginWithPassword(page, email, password) {
  await page.goto('/login', { waitUntil: 'networkidle' });

  // Fill email and password inputs
  await page.fill('input[type="email"], input[name="email"]', email);
  await page.fill('input[type="password"], input[name="password"]', password);

  // Capture the login API response
  const [loginResponse] = await Promise.all([
    page.waitForResponse(r => r.url().includes('/api/v1/auth/login') && r.request().method() === 'POST'),
    page.click('button[type="submit"]'),
  ]);

  const loginData = await loginResponse.json().catch(() => ({}));
  if (!loginData.success) {
    throw new Error(`Login failed: ${JSON.stringify(loginData)}`);
  }

  // Wait for navigation away from login page
  await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 10000 });
  return true;
}

// ---------------------------------------------------------------------------
// Test Suite: Community Creation
// ---------------------------------------------------------------------------

test.describe('Community Creation - Core Smoke Tests', () => {
  // Each test logs in fresh to avoid session state issues
  test.beforeEach(async ({ page }) => {
    await loginWithPassword(page, TEST_EMAIL, TEST_PASS);
  });

  test('Create community button visible to authenticated users on /communities', async ({ page }) => {
    await page.goto('/communities', { waitUntil: 'networkidle' });

    const createBtn = page.locator('[data-testid="create-community-btn"]');
    await expect(createBtn).toBeVisible({ timeout: 5000 });
    await expect(createBtn).toHaveText(/Create a Community/i);
  });

  test('Create community button links to /communities/create', async ({ page }) => {
    await page.goto('/communities', { waitUntil: 'networkidle' });

    const createBtn = page.locator('[data-testid="create-community-btn"]');
    await createBtn.click();

    await page.waitForURL('**/communities/create', { timeout: 10000 });
    await expect(page).toHaveURL(/\/communities\/create/);
  });

  test('Community creation form renders correctly', async ({ page }) => {
    await page.goto('/communities/create', { waitUntil: 'networkidle' });

    // Check form elements are present
    await expect(page.locator('[data-testid="community-name-input"]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[data-testid="create-community-submit"]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('select[name="platform"]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('select[name="communityType"]')).toBeVisible({ timeout: 5000 });
  });

  test('Community creation succeeds and redirects to community dashboard', async ({ page }) => {
    const communityName = `smoke-test-${Date.now()}`;

    await page.goto('/communities/create', { waitUntil: 'networkidle' });

    // Fill in the form
    await page.fill('[data-testid="community-name-input"]', communityName);
    await page.fill('input[name="displayName"]', `Smoke Test ${Date.now()}`);

    // Capture the API request/response for debugging
    let createResponse = null;
    let createResponseBody = null;

    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/communities/create') || response.url().includes('/api/v1/community/create')) {
        createResponse = response;
        try {
          createResponseBody = await response.json();
        } catch {
          createResponseBody = { raw: await response.text().catch(() => '(unreadable)') };
        }
      }
    });

    // Submit the form
    await page.click('[data-testid="create-community-submit"]');

    // Wait for navigation to community dashboard (success path) or error display (failure path)
    const result = await Promise.race([
      page.waitForURL('**/dashboard/community/**', { timeout: 15000 }).then(() => 'success'),
      page.waitForSelector('[data-testid="community-form-error"]', { timeout: 15000 }).then(() => 'error'),
    ]).catch(() => 'timeout');

    // Debug output: show API response if test fails
    if (result !== 'success') {
      const errorText = await page.locator('[data-testid="community-form-error"]').textContent().catch(() => null);
      const pageUrl = page.url();

      console.error('Community creation did not succeed:');
      console.error('  Result:', result);
      console.error('  Current URL:', pageUrl);
      console.error('  Error shown in UI:', errorText);
      console.error('  API response status:', createResponse?.status());
      console.error('  API response body:', JSON.stringify(createResponseBody, null, 2));
    }

    // Assert success
    expect(result).toBe('success');
    await expect(page).toHaveURL(/\/dashboard\/community\/\d+/);
  });

  test('Community creation shows error on duplicate name', async ({ page }) => {
    // Use a very short unique name that is likely to be unique
    const firstRun = `duptest-${Date.now()}`;

    // Create the first community
    await page.goto('/communities/create', { waitUntil: 'networkidle' });
    await page.fill('[data-testid="community-name-input"]', firstRun);

    const [firstResponse] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/communities/create') && r.request().method() === 'POST', { timeout: 10000 }),
      page.click('[data-testid="create-community-submit"]'),
    ]);
    const firstBody = await firstResponse.json().catch(() => ({}));

    if (!firstBody.success) {
      // If the first creation failed, skip the duplicate test
      test.skip(true, `First community creation failed (${firstBody?.error?.message}), skipping duplicate test`);
      return;
    }

    // Navigate back and try to create with the same name
    await page.goto('/communities/create', { waitUntil: 'networkidle' });
    await page.fill('[data-testid="community-name-input"]', firstRun);
    await page.click('[data-testid="create-community-submit"]');

    // Should show an error about duplicate name
    await expect(page.locator('[data-testid="community-form-error"]')).toBeVisible({ timeout: 10000 });
    const errorText = await page.locator('[data-testid="community-form-error"]').textContent();
    expect(errorText).toMatch(/already exists|duplicate|conflict/i);
  });

  test('Community creation requires community name', async ({ page }) => {
    await page.goto('/communities/create', { waitUntil: 'networkidle' });

    // Submit without filling in the name
    await page.click('[data-testid="create-community-submit"]');

    // Either browser validation or our error should be shown
    const nameInput = page.locator('[data-testid="community-name-input"]');
    const isRequired = await nameInput.evaluate(el => el.validity.valueMissing).catch(() => false);
    const errorShown = await page.locator('[data-testid="community-form-error"]').isVisible({ timeout: 2000 }).catch(() => false);

    expect(isRequired || errorShown).toBe(true);
  });

  test('Create community API returns proper structure', async ({ page }) => {
    const communityName = `api-test-${Date.now()}`;

    await page.goto('/communities/create', { waitUntil: 'networkidle' });
    await page.fill('[data-testid="community-name-input"]', communityName);

    const [response] = await Promise.all([
      page.waitForResponse(
        r => r.url().includes('/communities/create') && r.request().method() === 'POST',
        { timeout: 15000 }
      ),
      page.click('[data-testid="create-community-submit"]'),
    ]);

    const body = await response.json().catch(() => null);

    // Log details for debugging
    console.log('Create community API response:');
    console.log('  Status:', response.status());
    console.log('  Body:', JSON.stringify(body, null, 2));

    // Verify proper response structure
    expect(response.status()).toBe(201);
    expect(body).not.toBeNull();
    expect(body.success).toBe(true);
    expect(body.community).toBeDefined();
    expect(body.community.id).toBeDefined();
    expect(typeof body.community.id).toBe('number');
  });
});

// ---------------------------------------------------------------------------
// Test Suite: Community Creation - Error Cases (network interception)
// ---------------------------------------------------------------------------

test.describe('Community Creation - Network Diagnostics', () => {
  test.beforeEach(async ({ page }) => {
    await loginWithPassword(page, TEST_EMAIL, TEST_PASS);
  });

  test('Auth token is sent with community creation request', async ({ page }) => {
    await page.goto('/communities/create', { waitUntil: 'networkidle' });
    await page.fill('[data-testid="community-name-input"]', `auth-check-${Date.now()}`);

    let authHeader = null;
    page.on('request', (req) => {
      if (req.url().includes('/communities/create') && req.method() === 'POST') {
        authHeader = req.headers()['authorization'];
      }
    });

    await page.click('[data-testid="create-community-submit"]');
    await page.waitForTimeout(2000);

    expect(authHeader).toBeTruthy();
    expect(authHeader).toMatch(/^Bearer .+/);
  });

  test('Unauthenticated user cannot access /communities/create', async ({ page }) => {
    // Go to create page without logging in (clear storage first)
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());

    await page.goto('/communities/create');
    await page.waitForURL(url => url.toString().includes('/login') || url.toString() === page.url(), { timeout: 5000 });

    // Should be redirected to login
    await expect(page).toHaveURL(/\/login|\/$/);
  });
});
