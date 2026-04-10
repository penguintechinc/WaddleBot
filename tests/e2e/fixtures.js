/**
 * Custom Playwright fixtures for WaddleBot E2E tests
 *
 * Extends the base `test` object with:
 *   - Inter-test cooldown to prevent rate-limit (429) cascades
 *   - Automatic rate-limit retry on all API routes
 *
 * Usage — replace this in spec files:
 *   const { test, expect } = require('@playwright/test');
 * with:
 *   const { test, expect } = require('./fixtures');
 */
const base = require('@playwright/test');
const { installRateLimitRetry } = require('./test-helpers');

// Cooldown between tests (ms).  Each page navigation fires 4-5 parallel API
// requests; back-to-back navigations overwhelm beta's per-IP rate limiter.
const TEST_COOLDOWN_MS = parseInt(process.env.TEST_COOLDOWN_MS || '2000', 10);

const test = base.test.extend({
  // Override the built-in `page` fixture to auto-install rate-limit retry
  // and add an inter-test cooldown.
  page: async ({ page }, use) => {
    // Install rate-limit retry handler on every page automatically
    await installRateLimitRetry(page);

    // Hand the page to the test
    await use(page);

    // After each test, wait before the next one starts to let the rate-limit
    // window recover.  This runs even if the test fails.
    if (TEST_COOLDOWN_MS > 0) {
      await new Promise((r) => setTimeout(r, TEST_COOLDOWN_MS));
    }
  },
});

const expect = base.expect;

module.exports = { test, expect };
