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

const { test, expect } = require('./fixtures');

const TEST_EMAIL = process.env.HUB_TEST_EMAIL || 'admin@localhost.local';
const TEST_PASS = process.env.HUB_TEST_PASS || process.env.INITIAL_ADMIN_PASSWORD || 'admin123';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Pre-seed localStorage with GDPR consent and dismissed overlays BEFORE any
 * page navigation. LoginPageBuilder gates the email/password inputs on
 * gdpr_consent.accepted === true — if the key is absent when React mounts,
 * the inputs render as disabled and are invisible to the test. Using
 * addInitScript ensures the key is present before any page script runs.
 *
 * Call this once per page object before the first navigation.
 */
async function addConsentInitScript(page) {
  await page.addInitScript(() => {
    localStorage.setItem('gdpr_consent', JSON.stringify({
      accepted: true, essential: true, functional: true, analytics: true, marketing: true,
      timestamp: new Date().toISOString(), policyVersion: '1.0',
    }));
    localStorage.setItem('vendor-request-dismissed', 'true');
  });
}

/**
 * Extract XSRF-TOKEN from Set-Cookie headers and inject it as an accessible
 * cookie. Required when testing over HTTP (port-forward) because the backend
 * sets Secure cookies in production mode, which browsers silently drop on HTTP.
 * Playwright sees raw network responses, so we can recover and re-inject the token.
 *
 * IMPORTANT: call addConsentInitScript(page) BEFORE calling this function so
 * that the gdpr_consent key is in localStorage when the /login page loads.
 */
async function injectCsrfCookie(page) {
  let csrfToken = null;

  // Capture XSRF-TOKEN from any hub-api response fired during page load
  const handler = async (response) => {
    const raw = response.headers()['set-cookie'] || '';
    const match = raw.match(/XSRF-TOKEN=([^;]+)/);
    if (match) csrfToken = match[1];
  };
  page.on('response', handler);
  await page.goto('/login', { waitUntil: 'networkidle' });
  page.off('response', handler);

  // Strategy 1: React app calls hub-api on page load; Playwright stores the Secure
  // cookie in its CDP store even though browser JS can't read it over HTTP.
  if (!csrfToken) {
    const existing = await page.context().cookies();
    const xsrf = existing.find(c => c.name === 'XSRF-TOKEN');
    if (xsrf) csrfToken = xsrf.value;
  }

  // Strategy 2: No cookie found — make a fresh hub-api call to generate one.
  if (!csrfToken) {
    try {
      const resp = await page.request.get('/api/v1/health');
      const allHeaders = await resp.headersArray();
      const setCookieText = allHeaders
        .filter(h => h.name.toLowerCase() === 'set-cookie')
        .map(h => h.value).join('\n') || resp.headers()['set-cookie'] || '';
      const match = setCookieText.match(/XSRF-TOKEN=([^;]+)/);
      if (match) csrfToken = match[1];
    } catch (_) { /* ignore */ }
  }

  if (csrfToken) {
    const url = new URL(page.url());
    await page.context().addCookies([{
      name: 'XSRF-TOKEN',
      value: decodeURIComponent(csrfToken),
      domain: url.hostname,
      path: '/',
      httpOnly: false,
      secure: false, // allow on HTTP (port-forward scenario)
      sameSite: 'Lax',
    }]);
  }
  return csrfToken;
}

/**
 * Suppress all fixed-position overlays (cookie banner, vendor footer) by
 * injecting the localStorage keys they check. This is a best-effort fallback
 * for overlays that may appear after navigation. For reliable suppression,
 * prefer addConsentInitScript() which runs before React mounts.
 */
async function suppressOverlays(page) {
  await page.evaluate(() => {
    // Cookie consent banner checks this key
    if (!localStorage.getItem('gdpr_consent')) {
      localStorage.setItem('gdpr_consent', JSON.stringify({
        accepted: true, essential: true, functional: true, analytics: true, marketing: true,
        timestamp: new Date().toISOString(), policyVersion: '1.0'
      }));
    }
    // Vendor request footer checks this key
    localStorage.setItem('vendor-request-dismissed', 'true');
  });
}

/** Dismiss overlays if they are already visible on the page */
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

/**
 * Log in via the email/password form and wait for navigation to /dashboard.
 * Returns the JWT token stored in localStorage.
 */
async function loginWithPassword(page, email, password, retries = 3) {
  // Pre-seed gdpr_consent before any navigation so LoginPageBuilder mounts
  // with the form inputs enabled (not gated behind the consent banner).
  await addConsentInitScript(page);
  const csrfToken = await injectCsrfCookie(page);
  await suppressOverlays(page);
  await dismissOverlays(page);

  // LoginPageBuilder doesn't read document.cookie to build the X-XSRF-TOKEN header.
  // Inject it via page.route() so the login POST carries the required CSRF header.
  if (csrfToken) {
    await page.route('**/api/v1/auth/login', async (route) => {
      const request = route.request();
      if (request.method() === 'POST') {
        await route.continue({ headers: { ...request.headers(), 'x-xsrf-token': csrfToken } });
      } else {
        await route.continue();
      }
    });
  }

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
  console.log(`[loginWithPassword] status=${loginResponse.status()} body=${bodyText.slice(0, 200)}`);
  let data;
  try {
    data = JSON.parse(bodyText);
  } catch {
    data = {};
  }

  // Retry on rate limit
  if (data?.error?.code === 'RATE_LIMITED' && retries > 0) {
    console.log(`[loginWithPassword] Rate limited, waiting 20s before retry (${retries} left)...`);
    await page.waitForTimeout(20000);
    return loginWithPassword(page, email, password, retries - 1);
  }

  if (!data.success) {
    throw new Error(`Login failed: ${JSON.stringify(data)} (status ${loginResponse.status()})`);
  }

  await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 10000 });
  // Suppress overlays on the destination page too
  await suppressOverlays(page);
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
    // Must addInitScript BEFORE navigating so React mounts with consent set.
    await addConsentInitScript(page);
    await page.goto('/login', { waitUntil: 'networkidle' });
    await dismissOverlays(page);
  });

  test('login page renders email and password fields', async ({ page }) => {
    await expect(page.locator('input#email')).toBeVisible();
    await expect(page.locator('input#password')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('login page shows "Sign In" on submit button by default', async ({ page }) => {
    await expect(page.locator('button[type="submit"]')).toHaveText(/Sign in/i);
  });

  test('login page shows OAuth provider buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Continue with Discord/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Continue with Twitch/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Continue with Slack/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Continue with YouTube/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Continue with KICK/i })).toBeVisible();
  });

  test('login page shows "or continue with platform or email" divider', async ({ page }) => {
    // The divider text rendered by LoginPage.jsx is "or continue with platform or email"
    await expect(page.getByText(/or continue with platform or email/i)).toBeVisible();
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

  test('login with wrong password returns error response', async ({ page }) => {
    await addConsentInitScript(page);
    await injectCsrfCookie(page);
    await suppressOverlays(page);
    await dismissOverlays(page);

    await page.fill('[data-testid="email-input"], input[type="email"]', TEST_EMAIL);
    await page.fill('[data-testid="password-input"], input[type="password"]', 'definitely-wrong-password');

    // Capture the API response directly — the axios 401 interceptor reloads the page,
    // so we cannot rely on the React error element rendering in the DOM.
    const [loginResponse] = await Promise.all([
      page.waitForResponse(
        r => r.url().includes('/api/v1/auth/login') && r.request().method() === 'POST'
      ),
      page.click('[data-testid="auth-submit"], button[type="submit"]'),
    ]);

    const status = loginResponse.status();
    expect([401, 403, 429]).toContain(status);

    // After the interceptor's forced reload, we should still be on /login
    await page.waitForURL(/\/login/, { timeout: 8000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test('login with non-existent email returns error response', async ({ page }) => {
    await addConsentInitScript(page);
    await injectCsrfCookie(page);
    await suppressOverlays(page);
    await dismissOverlays(page);

    await page.fill('[data-testid="email-input"], input[type="email"]', 'nobody@nowhere.invalid');
    await page.fill('[data-testid="password-input"], input[type="password"]', 'somepassword123');

    const [loginResponse] = await Promise.all([
      page.waitForResponse(
        r => r.url().includes('/api/v1/auth/login') && r.request().method() === 'POST'
      ),
      page.click('[data-testid="auth-submit"], button[type="submit"]'),
    ]);

    const status = loginResponse.status();
    expect([401, 403, 404, 429]).toContain(status);

    await page.waitForURL(/\/login/, { timeout: 8000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test('login API sends correct request body', async ({ page }) => {
    await addConsentInitScript(page);
    const csrfToken1 = await injectCsrfCookie(page);
    if (csrfToken1) {
      await page.route('**/api/v1/auth/login', async (route) => {
        const req = route.request();
        if (req.method() === 'POST') {
          await route.continue({ headers: { ...req.headers(), 'x-xsrf-token': csrfToken1 } });
        } else { await route.continue(); }
      });
    }

    await page.fill('[data-testid="email-input"], input[type="email"]', TEST_EMAIL);
    await page.fill('[data-testid="password-input"], input[type="password"]', TEST_PASS);

    let requestBody = null;
    page.on('request', (req) => {
      if (req.url().includes('/api/v1/auth/login') && req.method() === 'POST') {
        try { requestBody = JSON.parse(req.postData()); } catch { /* ignore */ }
      }
    });

    await page.click('[data-testid="auth-submit"], button[type="submit"]');
    // Increased timeout to accommodate rate-limit retries (installRateLimitRetry waits 15s per retry)
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 60000 });

    expect(requestBody).not.toBeNull();
    expect(requestBody.email).toBe(TEST_EMAIL);
    expect(requestBody.password).toBe(TEST_PASS);
  });

  test('login API returns success structure', async ({ page }) => {
    await addConsentInitScript(page);
    const csrfToken2 = await injectCsrfCookie(page);
    if (csrfToken2) {
      await page.route('**/api/v1/auth/login', async (route) => {
        const req = route.request();
        if (req.method() === 'POST') {
          await route.continue({ headers: { ...req.headers(), 'x-xsrf-token': csrfToken2 } });
        } else { await route.continue(); }
      });
    }

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
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 15000 });
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

test.describe('Auth - Registration', () => {
  test('registration link appears when signup is enabled', async ({ page }) => {
    await addConsentInitScript(page);
    await page.goto('/login', { waitUntil: 'networkidle' });
    await dismissOverlays(page);

    // Wait for signup settings to load (button only shows if signupEnabled=true)
    const registerLink = page.locator('[data-testid="register-link"]');
    const isVisible = await registerLink.isVisible({ timeout: 5000 }).catch(() => false);

    if (!isVisible) {
      // Signup is disabled on this instance — skip gracefully
      test.skip(true, 'Signup is disabled on this instance');
      return;
    }

    await registerLink.click();
    await expect(page).toHaveURL(/\/register/);

    // Register mode: username field should appear, button should say "Create Account"
    await expect(page.locator('[data-testid="username-input"]')).toBeVisible({ timeout: 3000 });
    await expect(page.locator('[data-testid="auth-submit"]')).toHaveText(/Create Account/i);
  });

  test('registration page links back to sign in', async ({ page }) => {
    await addConsentInitScript(page);
    await page.goto('/login', { waitUntil: 'networkidle' });
    await dismissOverlays(page);

    const registerLink = page.locator('[data-testid="register-link"]');
    const isVisible = await registerLink.isVisible({ timeout: 5000 }).catch(() => false);
    if (!isVisible) {
      test.skip(true, 'Signup is disabled on this instance');
      return;
    }

    await registerLink.click();
    await expect(page.locator('[data-testid="username-input"]')).toBeVisible({ timeout: 3000 });

    await page.getByRole('link', { name: /Sign in/i }).click();
    await expect(page).toHaveURL(/\/login/);
    await expect(page.locator('[data-testid="username-input"]')).not.toBeVisible();
  });
});
