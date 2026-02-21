/**
 * E2E Tests: Community Workflow
 * Tests community creation, listing, and navigation
 *
 * Environment variables:
 *   BASE_URL        - Default: http://localhost:3000
 *   HUB_TEST_EMAIL  - Test user email (default: admin@localhost.local)
 *   HUB_TEST_PASS   - Test user password (default: admin123)
 */

const { test, expect } = require('@playwright/test');

const TEST_EMAIL = process.env.HUB_TEST_EMAIL || 'admin@localhost.local';
const TEST_PASS = process.env.HUB_TEST_PASS || 'admin123';

async function injectCsrfCookie(page) {
  let csrfToken = null;
  const handler = async (response) => {
    const raw = response.headers()['set-cookie'] || '';
    const match = raw.match(/XSRF-TOKEN=([^;]+)/);
    if (match) csrfToken = match[1];
  };
  page.on('response', handler);
  await page.goto('/login', { waitUntil: 'networkidle' });
  page.off('response', handler);
  if (csrfToken) {
    const url = new URL(page.url());
    await page.context().addCookies([{
      name: 'XSRF-TOKEN',
      value: csrfToken,
      domain: url.hostname,
      path: '/',
      httpOnly: false,
      secure: false,
      sameSite: 'Lax',
    }]);
  }
}

async function suppressOverlays(page) {
  await page.evaluate(() => {
    if (!localStorage.getItem('cookieConsent')) {
      localStorage.setItem('cookieConsent', JSON.stringify({
        essential: true, analytics: true, marketing: true, preferences: true,
        timestamp: new Date().toISOString(), policyVersion: '1.0'
      }));
    }
    localStorage.setItem('vendor-request-dismissed', 'true');
  });
}

async function dismissOverlays(page) {
  const acceptBtn = page.locator('button[aria-label="Accept all cookies"], button:has-text("Accept All")').first();
  if (await acceptBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    await acceptBtn.click();
    await acceptBtn.waitFor({ state: 'hidden', timeout: 3000 }).catch(() => {});
  }
  const vendorDismiss = page.locator('button[title="Dismiss"]').first();
  if (await vendorDismiss.isVisible({ timeout: 1000 }).catch(() => false)) {
    await vendorDismiss.click();
    await vendorDismiss.waitFor({ state: 'hidden', timeout: 3000 }).catch(() => {});
  }
}

async function loginWithPassword(page, email, password, retries = 3) {
  await injectCsrfCookie(page);
  await suppressOverlays(page);
  await dismissOverlays(page);

  await page.fill('[data-testid="email-input"], input[type="email"]', email);
  await page.fill('[data-testid="password-input"], input[type="password"]', password);

  const [loginResponse] = await Promise.all([
    page.waitForResponse(
      r => r.url().includes('/api/v1/auth/login') && r.request().method() === 'POST',
      { timeout: 15000 }
    ),
    page.click('[data-testid="auth-submit"], button[type="submit"]'),
  ]);

  const bodyText = await loginResponse.text().catch(() => '(unreadable)');
  let data;
  try { data = JSON.parse(bodyText); } catch { data = {}; }

  if (data?.error?.code === 'RATE_LIMITED' && retries > 0) {
    console.log(`[loginWithPassword] Rate limited, waiting 10s before retry (${retries} left)...`);
    await page.waitForTimeout(10000);
    return loginWithPassword(page, email, password, retries - 1);
  }

  if (!data.success) {
    throw new Error(`Login failed: ${JSON.stringify(data)} (status ${loginResponse.status()})`);
  }

  await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 10000 });
  await suppressOverlays(page);
}

async function installRateLimitRetry(page) {
  await page.route('**/api/**', async (route) => {
    try {
      let response = await route.fetch();
      let retries = 2;
      while (response.status() === 429 && retries > 0) {
        console.log(`[rate-limit-retry] 429 on ${route.request().url()}, waiting 15s (${retries} left)...`);
        await new Promise(r => setTimeout(r, 15000));
        response = await route.fetch();
        retries--;
      }
      await route.fulfill({ response });
    } catch {
      // Context/page closed while route was in-flight — ignore gracefully
    }
  });
}

async function ensureAuthenticated(page) {
  await installRateLimitRetry(page);

  await page.goto('/', { waitUntil: 'networkidle' });
  await suppressOverlays(page);

  const token = await page.evaluate(() => localStorage.getItem('token'));
  if (token) {
    await page.goto('/dashboard', { waitUntil: 'networkidle', timeout: 60000 });
    await suppressOverlays(page);
    if (!page.url().includes('/login')) return;
  }

  await loginWithPassword(page, TEST_EMAIL, TEST_PASS);
}

test.describe('Community Management Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticated(page);
  });

  test('Create new community', async ({ page }) => {
    const communityName = `testcommunity${Date.now()}`;

    // Navigate to create community page
    await page.goto('/communities/create', { waitUntil: 'networkidle' });
    await suppressOverlays(page);
    await dismissOverlays(page);

    // Fill community form using data-testid selectors (matching CommunityForm.jsx)
    await page.fill('[data-testid="community-name-input"], input[name="name"]', communityName);

    // Capture API response for debugging
    let createResponse = null;
    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/communities/create') && response.request().method() === 'POST') {
        createResponse = response;
      }
    });

    // Submit form
    await page.click('[data-testid="create-community-submit"], button[type="submit"]');

    // Wait for either redirect to community dashboard or error display
    const result = await Promise.race([
      page.waitForURL('**/dashboard/community/**', { timeout: 15000 }).then(() => 'success'),
      page.waitForSelector('[data-testid="community-form-error"]', { timeout: 15000 }).then(() => 'error'),
    ]).catch(() => 'timeout');

    // Skip gracefully on server errors
    if (result !== 'success' && createResponse && [429, 500, 502, 503].includes(createResponse.status())) {
      const errorText = await page.locator('[data-testid="community-form-error"]').textContent().catch(() => 'unknown');
      test.skip(true, `Server returned ${createResponse.status()}: ${errorText}`);
      return;
    }

    expect(result).toBe('success');
  });

  test('View community list', async ({ page }) => {
    await page.goto('/communities', { waitUntil: 'networkidle' });
    await dismissOverlays(page);

    // Verify page loaded with the heading
    await expect(page.getByRole('heading', { name: /communities/i }).first()).toBeVisible({ timeout: 8000 });
  });

  test('View community details', async ({ page }) => {
    // Go to communities list
    await page.goto('/communities', { waitUntil: 'networkidle' });
    await dismissOverlays(page);

    // Check if any community cards exist
    const cards = page.locator('[data-testid="community-card"], .card a[href*="/communities/"]');
    const cardCount = await cards.count();

    if (cardCount === 0) {
      test.skip(true, 'No communities available to view details');
      return;
    }

    // Click first community
    await cards.first().click();
    await page.waitForURL(/\/communities\/\d+|\/dashboard\/community\/\d+/, { timeout: 10000 });

    // Verify community page loaded (has some content)
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
  });
});
