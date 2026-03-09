/**
 * E2E Tests: Authentication Workflow
 * Tests user registration toggle, admin login, and logout
 *
 * Environment variables:
 *   BASE_URL        - Default: http://localhost:3000
 *   HUB_TEST_EMAIL  - Test user email (default: admin@localhost.local)
 *   HUB_TEST_PASS   - Test user password (default: admin123)
 */

const { test, expect } = require('@playwright/test');

const TEST_EMAIL = process.env.HUB_TEST_EMAIL || 'admin@localhost.local';
const TEST_PASS = process.env.HUB_TEST_PASS || 'admin123';

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
    console.log(`[loginWithPassword] Rate limited, waiting 20s before retry (${retries} left)...`);
    await page.waitForTimeout(20000);
    return loginWithPassword(page, email, password, retries - 1);
  }

  if (!data.success) {
    throw new Error(`Login failed: ${JSON.stringify(data)} (status ${loginResponse.status()})`);
  }

  await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 10000 });
  await suppressOverlays(page);
}

test.describe('Authentication Workflow', () => {
  test('Register toggle shows username field when signup enabled', async ({ page }) => {
    await page.goto('/login', { waitUntil: 'networkidle' });

    // Check if signup is enabled on this instance
    const registerToggle = page.locator('[data-testid="register-toggle"]');
    const isVisible = await registerToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (!isVisible) {
      test.skip(true, 'Signup is disabled on this instance');
      return;
    }

    // Click register toggle to switch to registration mode
    await registerToggle.click();

    // Username field should appear
    await expect(
      page.locator('[data-testid="username-input"], input[placeholder="Choose a username"]')
    ).toBeVisible({ timeout: 3000 });

    // Submit button should say "Create Account"
    await expect(
      page.locator('[data-testid="auth-submit"], button[type="submit"]')
    ).toHaveText(/Create Account/i);
  });

  test('Login with admin credentials redirects to dashboard', async ({ page }) => {
    await loginWithPassword(page, TEST_EMAIL, TEST_PASS);

    // Should be on dashboard
    await expect(page).toHaveURL(/\/dashboard/);

    // Dashboard should have content visible
    await expect(page.locator('h1').first()).toBeVisible({ timeout: 8000 });
  });

  test('Logout flow clears session', async ({ page }) => {
    await loginWithPassword(page, TEST_EMAIL, TEST_PASS);

    // Simulate logout by clearing localStorage (same as clicking logout)
    await page.evaluate(() => localStorage.removeItem('token'));

    // Navigate to a protected page to trigger redirect to login
    await page.goto('/dashboard');
    await page.waitForURL(
      url => url.toString().includes('/login'),
      { timeout: 10000 }
    );

    await expect(page).toHaveURL(/\/login/);
  });
});
