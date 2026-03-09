/**
 * Global Auth Setup
 *
 * Logs in once and saves browser storage state (cookies + localStorage)
 * so that subsequent test files can skip the login flow entirely.
 * This dramatically reduces the number of login API calls, avoiding
 * rate limiting when running the full test suite.
 */

const { test: setup, expect } = require('@playwright/test');
const path = require('path');

const TEST_EMAIL = process.env.HUB_TEST_EMAIL || 'admin@localhost.local';
const TEST_PASS = process.env.HUB_TEST_PASS || 'admin123';

const AUTH_STATE_PATH = path.join(__dirname, '.auth-state.json');

async function injectCsrfCookie(page) {
  // Navigate to the login page. The static HTML is served by hub-webui (nginx),
  // so no hub-api response fires here — the XSRF-TOKEN cookie is not yet set.
  await page.goto('/login', { waitUntil: 'networkidle' });

  // Make a same-origin fetch from inside the browser to any hub-api endpoint.
  // hub-api's setCsrfToken middleware sets XSRF-TOKEN on every response when
  // the cookie is absent. The browser automatically stores the Set-Cookie.
  // The endpoint doesn't need to exist (404 still sets the cookie).
  await page.evaluate(() =>
    fetch('/api/v1/auth/status', { credentials: 'include' }).catch(() => {})
  );

  // Read the token back from the browser cookie jar.
  const cookies = await page.context().cookies();
  const csrfCookie = cookies.find(c => c.name === 'XSRF-TOKEN');
  return csrfCookie?.value || null;
}

setup('authenticate', async ({ page }) => {
  // Pre-seed localStorage before page load so LoginPageBuilder mounts with
  // consent already set (inputs are disabled until gdpr_consent.accepted=true).
  // addInitScript runs before any page script — React never sees missing consent.
  await page.addInitScript(() => {
    localStorage.setItem('gdpr_consent', JSON.stringify({
      accepted: true, essential: true, functional: true, analytics: true, marketing: true,
      timestamp: new Date().toISOString(), policyVersion: '1.0',
    }));
    localStorage.setItem('vendor-request-dismissed', 'true');
  });

  const csrfToken = await injectCsrfCookie(page);

  // Intercept the login POST to inject X-XSRF-TOKEN header.
  // LoginPageBuilder uses its own HTTP client (not the frontend axios instance),
  // so it never reads document.cookie to add the CSRF header. We add it here.
  if (csrfToken) {
    await page.route('**/api/v1/auth/login', async (route) => {
      const request = route.request();
      if (request.method() === 'POST') {
        await route.continue({
          headers: { ...request.headers(), 'x-xsrf-token': csrfToken },
        });
      } else {
        await route.continue();
      }
    });
  }

  await page.waitForSelector('input[type="email"]:not([disabled])', { timeout: 15000 });
  await page.fill('[data-testid="email-input"], input[type="email"]', TEST_EMAIL);
  await page.fill('[data-testid="password-input"], input[type="password"]', TEST_PASS);

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

  if (!data.success) {
    throw new Error(`Setup login failed: ${JSON.stringify(data)} (status ${loginResponse.status()})`);
  }

  await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 10000 });

  // Save the authenticated state (cookies + localStorage with JWT token)
  await page.context().storageState({ path: AUTH_STATE_PATH });
});

module.exports = { AUTH_STATE_PATH };
