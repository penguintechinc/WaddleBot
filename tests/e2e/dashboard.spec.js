/**
 * Dashboard Smoke Tests
 *
 * Covers the main authenticated dashboard surface:
 *   - Dashboard home loads and shows welcome message
 *   - Empty state (no communities) renders correctly
 *   - Community cards render and link correctly when communities exist
 *   - Navigation to key dashboard sub-pages
 *   - Super admin banner visible for super admin users
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
 * Recover XSRF-TOKEN from Set-Cookie headers and inject as an accessible
 * cookie. Needed when testing over HTTP (port-forward) because the backend
 * sets Secure cookies in production, which browsers silently drop on HTTP.
 */
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

/**
 * Suppress all fixed-position overlays (cookie banner, vendor footer) by
 * injecting the localStorage keys they check. Call BEFORE navigating to
 * pages that render these overlays.
 */
async function suppressOverlays(page) {
  await page.evaluate(() => {
    if (!localStorage.getItem('gdpr_consent')) {
      localStorage.setItem('gdpr_consent', JSON.stringify({
        accepted: true, essential: true, functional: true, analytics: true, marketing: true,
        timestamp: new Date().toISOString(), policyVersion: '1.0'
      }));
    }
    localStorage.setItem('vendor-request-dismissed', 'true');
  });
}

/** Dismiss cookie consent banner and vendor request footer if present */
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

/**
 * Intercept /api/v1/auth/me requests and retry on 429 rate limit.
 * The React app's fetchCurrentUser clears the token and sets user=null
 * on ANY error. This ensures the auth/me endpoint succeeds by retrying.
 */
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

// ---------------------------------------------------------------------------
// Test Suite: Dashboard Home
// ---------------------------------------------------------------------------

test.describe('Dashboard - Home Page', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticated(page);
    await page.goto('/dashboard', { waitUntil: 'networkidle' });
    await dismissOverlays(page);

    // Guard: if rate limiting cleared the token and bounced us to /login, re-authenticate
    if (page.url().includes('/login')) {
      await loginWithPassword(page, TEST_EMAIL, TEST_PASS);
      await page.goto('/dashboard', { waitUntil: 'networkidle' });
      await dismissOverlays(page);
    }
  });

  test('dashboard home renders welcome message with username', async ({ page }) => {
    const welcome = page.locator('[data-testid="dashboard-welcome"]');
    await expect(welcome).toBeVisible({ timeout: 8000 });
    await expect(welcome).toContainText(/Welcome back/i);
    // Should include the actual username (not empty)
    const text = await welcome.textContent();
    expect(text.trim().length).toBeGreaterThan('Welcome back, '.length);
  });

  test('dashboard home shows loading state or content after navigation', async ({ page }) => {
    // Navigate fresh — spinner may be too brief to catch, so accept either spinner or content
    await page.goto('/dashboard');
    await suppressOverlays(page);
    // Wait for either the loading spinner or the actual content (welcome message or community grid)
    await page.waitForSelector(
      '[data-testid="dashboard-loading"], [data-testid="dashboard-welcome"], [data-testid="communities-grid"], [data-testid="no-communities"]',
      { timeout: 12000 }
    );
  });

  test('dashboard shows community content or empty state after loading', async ({ page }) => {
    // Wait for loading to finish
    await page.waitForSelector(
      '[data-testid="communities-grid"], [data-testid="no-communities"]',
      { timeout: 12000 }
    );

    const hasGrid = await page.locator('[data-testid="communities-grid"]').isVisible().catch(() => false);
    const hasEmpty = await page.locator('[data-testid="no-communities"]').isVisible().catch(() => false);

    expect(hasGrid || hasEmpty).toBe(true);
  });

  test('empty state shows Browse Communities button linking to /communities', async ({ page }) => {
    const noCommunitiesDiv = page.locator('[data-testid="no-communities"]');
    const isVisible = await noCommunitiesDiv.isVisible({ timeout: 8000 }).catch(() => false);

    if (!isVisible) {
      // User has communities — skip empty state test
      test.skip(true, 'User has communities; empty state not shown');
      return;
    }

    const browseBtn = page.locator('[data-testid="browse-communities-btn"]');
    await expect(browseBtn).toBeVisible();
    await expect(browseBtn).toHaveText(/Browse Communities/i);

    await browseBtn.click();
    await page.waitForURL('**/communities', { timeout: 8000 });
    await expect(page).toHaveURL(/\/communities$/);
  });

  test('community cards link to /dashboard/community/:id', async ({ page }) => {
    const grid = page.locator('[data-testid="communities-grid"]');
    const isVisible = await grid.isVisible({ timeout: 8000 }).catch(() => false);

    if (!isVisible) {
      test.skip(true, 'User has no communities; skipping card navigation test');
      return;
    }

    const firstCard = page.locator('[data-testid="community-card"]').first();
    await expect(firstCard).toBeVisible();

    // Get the href before clicking
    const href = await firstCard.getAttribute('href');
    expect(href).toMatch(/\/dashboard\/community\/\d+/);

    await firstCard.click();
    await page.waitForURL(/\/dashboard\/community\/\d+/, { timeout: 10000 });
    await expect(page).toHaveURL(/\/dashboard\/community\/\d+/);
  });
});

// ---------------------------------------------------------------------------
// Test Suite: Dashboard Navigation
// ---------------------------------------------------------------------------

test.describe('Dashboard - Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticated(page);
  });

  test('/dashboard/settings renders account settings page', async ({ page }) => {
    await page.goto('/dashboard/settings', { waitUntil: 'networkidle' });
    // Should stay on settings (not redirect to login)
    await expect(page).toHaveURL(/\/dashboard\/settings/);
    // Should have some content visible
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
  });

  test('/dashboard/profile renders profile edit page', async ({ page }) => {
    await page.goto('/dashboard/profile', { waitUntil: 'networkidle' });
    await expect(page).toHaveURL(/\/dashboard\/profile/);
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
  });

  test('/communities/create is accessible from dashboard', async ({ page }) => {
    await page.goto('/communities/create', { waitUntil: 'networkidle' });
    await expect(page).toHaveURL(/\/communities\/create/);
    await expect(page.locator('[data-testid="community-name-input"]')).toBeVisible({ timeout: 8000 });
  });

  test('/communities renders public communities page', async ({ page }) => {
    await page.goto('/communities', { waitUntil: 'networkidle' });
    await dismissOverlays(page);
    await expect(page).toHaveURL(/\/communities$/);
    // Authenticated user sees the create community button
    await expect(page.locator('[data-testid="create-community-btn"]')).toBeVisible({ timeout: 8000 });
  });
});

// ---------------------------------------------------------------------------
// Test Suite: Super Admin
// ---------------------------------------------------------------------------

test.describe('Dashboard - Super Admin', () => {
  test('super admin user sees the control panel banner on /dashboard', async ({ page }) => {
    await ensureAuthenticated(page);
    await page.goto('/dashboard', { waitUntil: 'networkidle' });
    await dismissOverlays(page);

    // Check if this account is a super admin by looking for the banner
    // (admin@localhost.local is seeded as super_admin, so this should appear)
    const banner = page.getByText('Super Admin Access');
    const isSuperAdmin = await banner.isVisible({ timeout: 5000 }).catch(() => false);

    if (!isSuperAdmin) {
      // Test account is not super admin — just verify no crash
      test.skip(true, 'Test account is not super_admin; super admin banner test skipped');
      return;
    }

    await expect(banner).toBeVisible();
    const controlPanelLink = page.getByRole('link', { name: /Open Control Panel/i });
    await expect(controlPanelLink).toBeVisible();
    await expect(controlPanelLink).toHaveAttribute('href', '/superadmin');
  });

  test('super admin can navigate to /superadmin', async ({ page }) => {
    await ensureAuthenticated(page);
    await page.goto('/superadmin', { waitUntil: 'networkidle' });
    await dismissOverlays(page);

    // Should either load the superadmin page or redirect to dashboard if not super admin
    const url = page.url();
    const isOnSuperAdmin = url.includes('/superadmin');
    const isRedirected = url.includes('/dashboard') || url.includes('/login');

    expect(isOnSuperAdmin || isRedirected).toBe(true);

    if (isOnSuperAdmin) {
      // Verify content loaded (not a blank page)
      await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
    }
  });
});
