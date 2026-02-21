/**
 * Playwright Test Configuration
 * @see https://playwright.dev/docs/test-configuration
 *
 * --- Usage ---
 *
 * Local dev server (default):
 *   cd tests/e2e && npx playwright test
 *   Requires: hub frontend running on http://localhost:3000
 *
 * Against beta via kubectl port-forward (bypasses Cloudflare WAF):
 *   # Forward hub service to local port 3001
 *   kubectl port-forward svc/hub 3001:8060 -n waddlebot --context dal2-beta &
 *   BASE_URL=http://localhost:3001 npx playwright test
 *
 * NOTE: Playwright cannot bypass Cloudflare using the ALB Host-header trick
 * that curl uses — browsers block overriding the Host header (forbidden header).
 * Use kubectl port-forward or run against a non-Cloudflare-proxied endpoint.
 *
 * Environment variables:
 *   BASE_URL          - Target URL (default: http://localhost:3000)
 *   HUB_TEST_EMAIL    - Login email (default: admin@localhost.local)
 *   HUB_TEST_PASS     - Login password (default: admin123)
 */

const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './',
  fullyParallel: false, // Run sequentially to avoid conflicts
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Run one test at a time
  reporter: 'html',

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ignoreHTTPSErrors: true, // For self-signed / internal certs
  },

  timeout: 60000, // 60 seconds per test

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Auto-start local dev server when running locally (uncomment to enable):
  // webServer: {
  //   command: 'npm run dev --prefix admin/hub_module/frontend',
  //   port: 3000,
  //   reuseExistingServer: !process.env.CI,
  // },
});
