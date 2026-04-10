/**
 * Shared E2E test helpers
 *
 * Centralises rate-limit retry logic, overlay dismissal, and other utilities
 * that were previously copy-pasted across spec files.
 */

// ---------------------------------------------------------------------------
// Rate-limit retry — intercept all API calls and retry on 429
// ---------------------------------------------------------------------------

/**
 * Install a Playwright route handler that automatically retries API requests
 * receiving HTTP 429 (Too Many Requests).
 *
 * @param {import('@playwright/test').Page} page
 * @param {object} [opts]
 * @param {number} [opts.retries=2]       Max retry attempts per request
 * @param {number} [opts.delayMs=15000]   Delay between retries (ms)
 */
async function installRateLimitRetry(page, { retries = 2, delayMs = 15000 } = {}) {
  await page.route('**/api/**', async (route) => {
    try {
      let response = await route.fetch();
      let left = retries;
      while (response.status() === 429 && left > 0) {
        console.log(
          `[rate-limit-retry] 429 on ${route.request().url()}, waiting ${delayMs / 1000}s (${left} left)...`
        );
        await new Promise((r) => setTimeout(r, delayMs));
        response = await route.fetch();
        left--;
      }
      await route.fulfill({ response });
    } catch {
      // Context/page closed while route was in-flight — ignore gracefully
    }
  });
}

// ---------------------------------------------------------------------------
// Overlay helpers
// ---------------------------------------------------------------------------

/** Suppress cookie-consent and vendor-request overlays via localStorage. */
async function suppressOverlays(page) {
  await page.evaluate(() => {
    try {
      const consent = JSON.stringify({
        accepted: true,
        essential: true,
        functional: true,
        analytics: true,
        marketing: true,
        timestamp: new Date().toISOString(),
      });
      localStorage.setItem('gdpr_consent', consent);
      localStorage.setItem(
        'cookie_consent',
        JSON.stringify({
          essential_cookies: true,
          functional_cookies: true,
          analytics_cookies: true,
          marketing_cookies: true,
        })
      );
      localStorage.setItem(
        'cookieConsent',
        JSON.stringify({
          essential: true,
          analytics: true,
          marketing: true,
          preferences: true,
          timestamp: new Date().toISOString(),
        })
      );
      localStorage.setItem('vendor-request-dismissed', 'true');
    } catch {
      // page not ready — ignore
    }
  });
}

/** Click away any visible overlay / dismiss buttons. */
async function dismissOverlays(page) {
  const selectors = [
    '[data-testid="cookie-banner-accept"]',
    '[data-testid="dismiss-overlay"]',
    'button:has-text("Accept")',
    'button:has-text("Got it")',
    'button:has-text("Dismiss")',
  ];
  for (const sel of selectors) {
    const el = page.locator(sel).first();
    if (await el.isVisible({ timeout: 500 }).catch(() => false)) {
      await el.click().catch(() => {});
    }
  }
}

// ---------------------------------------------------------------------------
// Inter-test cooldown
// ---------------------------------------------------------------------------

/**
 * Wait between tests to avoid rate-limit cascades.  Each page navigation
 * fires 4-5 parallel API requests; back-to-back navigations overwhelm the
 * per-IP rate limiter on beta.
 *
 * @param {number} [ms=2000] Cooldown in milliseconds
 */
function sleep(ms = 2000) {
  return new Promise((r) => setTimeout(r, ms));
}

module.exports = {
  installRateLimitRetry,
  suppressOverlays,
  dismissOverlays,
  sleep,
};
