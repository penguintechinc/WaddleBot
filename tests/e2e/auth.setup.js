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

setup('authenticate', async ({ page }) => {
  await injectCsrfCookie(page);

  // Suppress overlays
  await page.evaluate(() => {
    if (!localStorage.getItem('cookieConsent')) {
      localStorage.setItem('cookieConsent', JSON.stringify({
        essential: true, analytics: true, marketing: true, preferences: true,
        timestamp: new Date().toISOString(), policyVersion: '1.0'
      }));
    }
    localStorage.setItem('vendor-request-dismissed', 'true');
  });

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
