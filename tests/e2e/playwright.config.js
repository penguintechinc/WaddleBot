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
const path = require('path');

const AUTH_STATE_PATH = path.join(__dirname, '.auth-state.json');

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

  timeout: 90000, // 90 seconds per test (allows for rate-limit retries)

  projects: [
    // Setup project: logs in once and saves auth state for reuse
    {
      name: 'setup',
      testMatch: 'auth.setup.js',
      use: { ...devices['Desktop Chrome'] },
    },
    // Authenticated tests run FIRST: reuse storageState (no login API calls)
    // This keeps the rate limit counter low for the auth tests that follow.
    {
      name: 'authenticated-tests',
      testMatch: ['community-creation.spec.js', 'community-workflow.spec.js', 'dashboard.spec.js', 'vendor-workflow.spec.js', 'superadmin.spec.js'],
      use: {
        ...devices['Desktop Chrome'],
        storageState: AUTH_STATE_PATH,
      },
      dependencies: ['setup'],
    },
    // Auth tests: test login/logout flows with fresh (unauthenticated) contexts.
    // Depends on setup completing, runs after authenticated-tests (which use
    // storageState and don't make login calls) to minimize rate limit pressure.
    {
      name: 'auth-tests',
      testMatch: ['auth.spec.js', 'auth-workflow.spec.js'],
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },
  ],

  // Auto-start local dev server when running locally (uncomment to enable):
  // webServer: {
  //   command: 'npm run dev --prefix admin/hub_module/frontend',
  //   port: 3000,
  //   reuseExistingServer: !process.env.CI,
  // },
});
