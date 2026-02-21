/**
 * Authentication Smoke Tests
 *
 * Covers the complete auth surface:
 *   - Login form renders correctly
 *   - Login success → dashboard redirect
 *   - Login failure → error message
 *   - Unauthenticated access to protected routes → redirect to /login
 *   - Already-authenticated visit to /login → redirect to /dashboard
 *   - Logout (token cleared) → /login
 *   - Register mode toggle (visible when signup enabled)
 *   - OAuth provider buttons visible
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
 * Extract XSRF-TOKEN from Set-Cookie headers and inject it as an accessible
 * cookie. Required when testing over HTTP (port-forward) because the backend
 * sets Secure cookies in production mode, which browsers silently drop on HTTP.
 * Playwright sees raw network responses, so we can recover and re-inject the token.
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
      secure: false, // allow on HTTP (port-forward scenario)
      sameSite: 'Lax',
    }]);
  }
}

/**
 * Log in via the email/password form and wait for navigation to /dashboard.
 * Returns the JWT token stored in localStorage.
 */
async function loginWithPassword(page, email, password) {
  await injectCsrfCookie(page);

  // Use resilient selectors that work with or without data-testids deployed
  await page.fill('[data-testid="email-input"], input[type="email"]', email);
  await page.fill('[data-testid="password-input"], input[type="password"]', password);

  const [loginResponse] = await Promise.all([
    page.waitForResponse(
      r => r.url().includes('/api/v1/auth/login') && r.request().method() === 'POST'
    ),
    page.click('[data-testid="auth-submit"], button[type="submit"]'),
  ]);

  const bodyText = await loginResponse.text().catch(() => '(unreadable)');
  console.log(`[loginWithPassword] status=${loginResponse.status()} url=${loginResponse.url()} body=${bodyText.slice(0, 200)}`);
  let data;
  try {
    data = JSON.parse(bodyText);
  } catch {
    data = {};
  }
  if (!data.success) {
    throw new Error(`Login failed: ${JSON.stringify(data)} (status ${loginResponse.status()})`);
  }

  await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 10000 });
  return page.evaluate(() => localStorage.getItem('token'));
}

/**
 * Inject a JWT directly into localStorage to simulate an authenticated session
 * without going through the login UI (faster for tests that only need auth context).
 */
async function injectToken(page, token) {
  await page.goto('/', { waitUntil: 'networkidle' });
  await page.evaluate((t) => localStorage.setItem('token', t), token);
}

// ---------------------------------------------------------------------------
// Test Suite: Login Page Structure
// ---------------------------------------------------------------------------

test.describe('Auth - Login Page Structure', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login', { waitUntil: 'networkidle' });
  });

  test('login page renders email and password fields', async ({ page }) => {
    await expect(page.locator('[data-testid="email-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="password-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="auth-submit"]')).toBeVisible();
  });

  test('login page shows "Sign In" on submit button by default', async ({ page }) => {
    await expect(page.locator('[data-testid="auth-submit"]')).toHaveText(/Sign In/i);
  });

  test('login page shows OAuth provider buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Continue with Discord/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Continue with Twitch/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Continue with Slack/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Continue with YouTube/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Continue with KICK/i })).toBeVisible();
  });

  test('login page shows "or continue with email" divider', async ({ page }) => {
    await expect(page.getByText(/or continue with email/i)).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Test Suite: Login Flow
// ---------------------------------------------------------------------------

test.describe('Auth - Login Flow', () => {
  test('successful login redirects to /dashboard', async ({ page }) => {
    await loginWithPassword(page, TEST_EMAIL, TEST_PASS);
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('successful login stores token in localStorage', async ({ page }) => {
    const token = await loginWithPassword(page, TEST_EMAIL, TEST_PASS);
    expect(token).toBeTruthy();
    expect(token).toMatch(/^[\w-]+\.[\w-]+\.[\w-]+$/); // basic JWT shape
  });

  test('login with wrong password shows error', async ({ page }) => {
    await injectCsrfCookie(page);

    await page.fill('[data-testid="email-input"], input[type="email"]', TEST_EMAIL);
    await page.fill('[data-testid="password-input"], input[type="password"]', 'definitely-wrong-password');
    await page.click('[data-testid="auth-submit"], button[type="submit"]');

    // Error displayed either via data-testid (new) or any red/error element (fallback)
    const error = page.locator('[data-testid="auth-error"], .text-red-300').first();
    await expect(error).toBeVisible({ timeout: 8000 });
    // Should still be on login page
    await expect(page).toHaveURL(/\/login/);
  });

  test('login with non-existent email shows error', async ({ page }) => {
    await injectCsrfCookie(page);

    await page.fill('[data-testid="email-input"], input[type="email"]', 'nobody@nowhere.invalid');
    await page.fill('[data-testid="password-input"], input[type="password"]', 'somepassword123');
    await page.click('[data-testid="auth-submit"], button[type="submit"]');

    const error = page.locator('[data-testid="auth-error"], .text-red-300').first();
    await expect(error).toBeVisible({ timeout: 8000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test('login API sends correct request body', async ({ page }) => {
    await injectCsrfCookie(page);

    await page.fill('[data-testid="email-input"], input[type="email"]', TEST_EMAIL);
    await page.fill('[data-testid="password-input"], input[type="password"]', TEST_PASS);

    let requestBody = null;
    page.on('request', (req) => {
      if (req.url().includes('/api/v1/auth/login') && req.method() === 'POST') {
        try { requestBody = JSON.parse(req.postData()); } catch { /* ignore */ }
      }
    });

    await page.click('[data-testid="auth-submit"], button[type="submit"]');
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 10000 });

    expect(requestBody).not.toBeNull();
    expect(requestBody.email).toBe(TEST_EMAIL);
    expect(requestBody.password).toBe(TEST_PASS);
  });

  test('login API returns success structure', async ({ page }) => {
    await page.goto('/login', { waitUntil: 'networkidle' });

    await page.fill('[data-testid="email-input"], input[type="email"]', TEST_EMAIL);
    await page.fill('[data-testid="password-input"], input[type="password"]', TEST_PASS);

    const [response] = await Promise.all([
      page.waitForResponse(
        r => r.url().includes('/api/v1/auth/login') && r.request().method() === 'POST',
        { timeout: 15000 }
      ),
      page.click('[data-testid="auth-submit"], button[type="submit"]'),
    ]);

    const body = await response.json().catch(() => null);
    expect(response.status()).toBe(200);
    expect(body).not.toBeNull();
    expect(body.success).toBe(true);
    expect(body.token).toBeTruthy();
    expect(body.user).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Test Suite: Auth Redirects
// ---------------------------------------------------------------------------

test.describe('Auth - Redirects', () => {
  test('unauthenticated user accessing /dashboard redirects to /login', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());

    await page.goto('/dashboard');
    await page.waitForURL(url => url.toString().includes('/login'), { timeout: 8000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test('unauthenticated user accessing /dashboard/settings redirects to /login', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());

    await page.goto('/dashboard/settings');
    await page.waitForURL(url => url.toString().includes('/login'), { timeout: 8000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test('authenticated user visiting /login is redirected to /dashboard', async ({ page }) => {
    const token = await loginWithPassword(page, TEST_EMAIL, TEST_PASS);
    expect(token).toBeTruthy();

    await page.goto('/login', { waitUntil: 'networkidle' });
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 8000 });
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('clearing token and visiting /dashboard redirects to /login', async ({ page }) => {
    await loginWithPassword(page, TEST_EMAIL, TEST_PASS);

    // Simulate logout by clearing localStorage
    await page.evaluate(() => localStorage.clear());
    await page.goto('/dashboard');
    await page.waitForURL(url => url.toString().includes('/login'), { timeout: 8000 });
    await expect(page).toHaveURL(/\/login/);
  });
});

// ---------------------------------------------------------------------------
// Test Suite: Register Mode Toggle
// ---------------------------------------------------------------------------

test.describe('Auth - Register Mode', () => {
  test('register toggle button appears when signup is enabled', async ({ page }) => {
    await page.goto('/login', { waitUntil: 'networkidle' });

    // Wait for signup settings to load (button only shows if signupEnabled=true)
    const registerToggle = page.locator('[data-testid="register-toggle"]');
    const isVisible = await registerToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (!isVisible) {
      // Signup is disabled on this instance — skip gracefully
      test.skip(true, 'Signup is disabled on this instance');
      return;
    }

    await registerToggle.click();

    // Register mode: username field should appear, button should say "Create Account"
    await expect(page.locator('[data-testid="username-input"]')).toBeVisible({ timeout: 3000 });
    await expect(page.locator('[data-testid="auth-submit"]')).toHaveText(/Create Account/i);
  });

  test('switching back to login mode hides username field', async ({ page }) => {
    await page.goto('/login', { waitUntil: 'networkidle' });

    const registerToggle = page.locator('[data-testid="register-toggle"]');
    const isVisible = await registerToggle.isVisible({ timeout: 5000 }).catch(() => false);
    if (!isVisible) {
      test.skip(true, 'Signup is disabled on this instance');
      return;
    }

    await registerToggle.click();
    await expect(page.locator('[data-testid="username-input"]')).toBeVisible({ timeout: 3000 });

    // Switch back to login
    await page.getByRole('button', { name: /Sign in/i }).last().click();
    await expect(page.locator('[data-testid="username-input"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="auth-submit"]')).toHaveText(/Sign In/i);
  });
});
