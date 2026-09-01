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

  // Use page.request (Playwright's APIRequestContext) to call hub-api directly.
  // This bypasses the browser's Secure-cookie-over-HTTP restriction:
  // browsers silently drop Set-Cookie headers with Secure flag on HTTP connections,
  // so page.evaluate(fetch(...)) + context.cookies() returns nothing over HTTP.
  // page.request reads raw response headers without that restriction.
  let csrfToken = null;

  // Strategy 1: React app calls hub-api on page load; Playwright stores the Secure
  // cookie in its CDP store even though browser JS can't read it over HTTP.
  const existingCookies = await page.context().cookies();
  const existingXsrf = existingCookies.find(c => c.name === 'XSRF-TOKEN');
  if (existingXsrf) {
    csrfToken = existingXsrf.value;
  }

  // Strategy 2: If not found (e.g., React made no initial API calls), trigger hub-api
  // directly via page.request to get the token.
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

  // Inject the token as a non-Secure cookie so the browser JS can read it.
  if (csrfToken) {
    const url = new URL(page.url());
    await page.context().addCookies([{
      name: 'XSRF-TOKEN',
      value: decodeURIComponent(csrfToken),
      domain: url.hostname,
      path: '/',
      httpOnly: false,
      secure: false,
      sameSite: 'Lax',
    }]);
  }
  return csrfToken;
}

setup('authenticate', async ({ page }) => {
  // Pre-seed localStorage before page load so LoginPageBuilder mounts with
  // consent already set (inputs are disabled until gdpr_consent.accepted=true).
  // addInitScript runs before any page script — React never sees missing consent.
  await page.addInitScript(() => {
    // gdpr_consent: gates LoginPageBuilder form inputs
    localStorage.setItem('gdpr_consent', JSON.stringify({
      accepted: true, essential: true, functional: true, analytics: true, marketing: true,
      timestamp: new Date().toISOString(), policyVersion: '1.0',
    }));
    // cookieConsent: suppresses CookieBanner.jsx overlay (checks this key on mount)
    localStorage.setItem('cookieConsent', JSON.stringify({
      essential: true, analytics: true, marketing: true, preferences: true,
      timestamp: new Date().toISOString(), policyVersion: '1.0',
    }));
    // cookie_consent: suppresses CookieConsentContext banner state
    localStorage.setItem('cookie_consent', JSON.stringify({
      essential_cookies: true, functional_cookies: true, analytics_cookies: true,
      marketing_cookies: true, consent_version: '1.0',
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
        const newHeaders = { ...request.headers(), 'x-xsrf-token': csrfToken };
        await route.continue({ headers: newHeaders });
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
