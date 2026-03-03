/**
 * Analytics Platform & AIChatter E2E Tests
 *
 * Covers new surfaces added in feature/analytics-aichatter:
 *
 * Analytics (Issue #9):
 *   - MyAnalytics page (/dashboard/my-analytics) — any authenticated user
 *   - PlatformAnalytics page (/platform/analytics) — analytics-consumer + superadmin
 *   - AdminMemberAnalytics page (/admin/:communityId/members/:userId/analytics) — community admin
 *   - SuperAdminAnalytics updated page — shared components render
 *   - SuperAdminUsers analytics-consumer role toggle button
 *
 * AIChatter (Issue #12):
 *   - AdminAIChatterConfig page (/admin/:communityId/ai-chatter) — community admin
 *     - Page loads with all 6 config controls
 *     - Enable toggle present
 *     - Save button present
 *
 * Environment variables:
 *   BASE_URL             - Default: http://localhost:3000
 *   HUB_TEST_EMAIL       - Test user email (default: admin@localhost.local)
 *   HUB_TEST_PASS        - Test user password (default: admin123)
 *   TEST_COMMUNITY_ID    - Community ID to use for admin tests
 *   TEST_MEMBER_USER_ID  - Member user ID for member analytics tests
 */

const { test, expect } = require('@playwright/test');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Suppress fixed-position overlays (cookie banner, vendor footer) */
async function suppressOverlays(page) {
  await page.addInitScript(() => {
    try {
      localStorage.setItem('cookie_consent_dismissed', 'true');
      localStorage.setItem('vendor_footer_dismissed', 'true');
    } catch (_) {}
  });
}

/** Navigate and wait for auth redirect to settle */
async function gotoAuthenticated(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(
    () => !window.location.pathname.startsWith('/login'),
    { timeout: 15000 }
  ).catch(() => {});
}

/** Dismiss overlays if already visible */
async function dismissOverlays(page) {
  const acceptBtn = page
    .locator('button[aria-label="Accept all cookies"], button:has-text("Accept All")')
    .first();
  if (await acceptBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    await acceptBtn.click();
    await acceptBtn.waitFor({ state: 'hidden', timeout: 3000 }).catch(() => {});
  }
}

/** Resolve communityId from API if TEST_COMMUNITY_ID not set */
async function resolveCommunityId(page) {
  if (process.env.TEST_COMMUNITY_ID) return process.env.TEST_COMMUNITY_ID;
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  const token = await page.evaluate(() => localStorage.getItem('token')).catch(() => null);
  if (!token) return null;
  try {
    const res = await page.request.get('/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    const communities = data?.user?.communities || [];
    return communities.length > 0 ? String(communities[0].id || communities[0]) : null;
  } catch (_) {
    return null;
  }
}

/** Skip if test user is not superadmin */
async function requireSuperAdmin(page) {
  const url = page.url();
  if (url.includes('/login') || url.includes('/dashboard')) {
    test.skip(true, 'Test account does not have super_admin access');
    return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
// Suite: My Analytics (Scenario 1 — any authenticated user)
// ---------------------------------------------------------------------------

test.describe('My Analytics page', () => {
  test.beforeEach(async ({ page }) => {
    await suppressOverlays(page);
    await gotoAuthenticated(page, '/dashboard/my-analytics');
    await dismissOverlays(page);
  });

  test('page loads without crashing', async ({ page }) => {
    // Should not redirect to login
    const url = page.url();
    expect(url).not.toContain('/login');
  });

  test('shows analytics summary cards', async ({ page }) => {
    // Expect stat cards to render — look for common labels
    const messageCard = page.getByText(/messages|total messages/i).first();
    const watchCard = page.getByText(/watch hours|watch time/i).first();

    const hasMessages = await messageCard.isVisible({ timeout: 8000 }).catch(() => false);
    const hasWatch = await watchCard.isVisible({ timeout: 3000 }).catch(() => false);

    // At minimum one summary stat should be visible
    expect(hasMessages || hasWatch).toBe(true);
  });

  test('My Analytics link is present in navigation', async ({ page }) => {
    await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
    await dismissOverlays(page);

    const navLink = page.locator('a[href="/dashboard/my-analytics"], nav a:has-text("My Analytics")');
    const isVisible = await navLink.first().isVisible({ timeout: 8000 }).catch(() => false);
    expect(isVisible).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Suite: Platform Analytics (Scenario 4 — analytics-consumer + superadmin)
// ---------------------------------------------------------------------------

test.describe('Platform Analytics page', () => {
  test.beforeEach(async ({ page }) => {
    await suppressOverlays(page);
    await gotoAuthenticated(page, '/platform/analytics');
    await dismissOverlays(page);
  });

  test('accessible to superadmin — page loads without crashing', async ({ page }) => {
    const url = page.url();
    // If redirected to /dashboard or /login the user lacks access
    if (url.includes('/login')) {
      test.skip(true, 'Test account is not logged in');
      return;
    }
    if (!url.includes('/platform/analytics')) {
      test.skip(true, 'Test account lacks analytics-consumer or super_admin role');
      return;
    }
    // Page should not show a hard error
    const errorText = page.getByText(/something went wrong|500|internal server error/i);
    const hasError = await errorText.isVisible({ timeout: 3000 }).catch(() => false);
    expect(hasError).toBe(false);
  });

  test('platform summary section renders', async ({ page }) => {
    if (!page.url().includes('/platform/analytics')) {
      test.skip(true, 'Test account lacks analytics-consumer or super_admin role');
      return;
    }

    // Summary cards should show numeric values
    const totalUsers = page.getByText(/total users/i).first();
    const isVisible = await totalUsers.isVisible({ timeout: 10000 }).catch(() => false);
    expect(isVisible).toBe(true);
  });

  test('community health table renders', async ({ page }) => {
    if (!page.url().includes('/platform/analytics')) {
      test.skip(true, 'Test account lacks analytics-consumer or super_admin role');
      return;
    }

    const healthSection = page.getByText(/community health/i).first();
    const isVisible = await healthSection.isVisible({ timeout: 10000 }).catch(() => false);
    expect(isVisible).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Suite: Admin Member Analytics (Scenario 2 — community admin)
// ---------------------------------------------------------------------------

test.describe('Admin Member Analytics page', () => {
  let communityId;
  const memberId = process.env.TEST_MEMBER_USER_ID || '1';

  test.beforeEach(async ({ page }) => {
    await suppressOverlays(page);
    communityId = await resolveCommunityId(page);
    if (!communityId) {
      test.skip(true, 'No community available for test account');
      return;
    }
    await gotoAuthenticated(
      page,
      `/admin/${communityId}/members/${memberId}/analytics`
    );
    await dismissOverlays(page);
  });

  test('page loads or redirects gracefully', async ({ page }) => {
    if (!communityId) return;
    const url = page.url();

    // If the user is not a community admin they should be redirected, not crash
    const errorText = page.getByText(/something went wrong|500|internal server error/i);
    const hasError = await errorText.isVisible({ timeout: 3000 }).catch(() => false);
    expect(hasError).toBe(false);
  });

  test('shows member stats heading when admin', async ({ page }) => {
    if (!communityId) return;
    const url = page.url();
    if (url.includes('/login') || !url.includes('/analytics')) {
      test.skip(true, 'Test account lacks community admin access or member not found');
      return;
    }

    // Heading should contain "Analytics" for member
    const heading = page.getByRole('heading', { name: /analytics/i }).first();
    const isVisible = await heading.isVisible({ timeout: 8000 }).catch(() => false);
    expect(isVisible).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Suite: SuperAdmin Analytics — shared components
// ---------------------------------------------------------------------------

test.describe('SuperAdmin Analytics page — shared components', () => {
  test.beforeEach(async ({ page }) => {
    await suppressOverlays(page);
    await gotoAuthenticated(page, '/superadmin/analytics');
    await dismissOverlays(page);
  });

  test('analytics page loads for superadmin', async ({ page }) => {
    if (!await requireSuperAdmin(page)) return;

    const heading = page.getByRole('heading', { name: /analytics/i }).first();
    const isVisible = await heading.isVisible({ timeout: 10000 }).catch(() => false);
    expect(isVisible).toBe(true);
  });

  test('platform summary cards render', async ({ page }) => {
    if (!await requireSuperAdmin(page)) return;

    const summarySection = page.getByText(/total users/i).first();
    const isVisible = await summarySection.isVisible({ timeout: 10000 }).catch(() => false);
    expect(isVisible).toBe(true);
  });

  test('community health section is present', async ({ page }) => {
    if (!await requireSuperAdmin(page)) return;

    const healthSection = page.getByText(/community health/i).first();
    const isVisible = await healthSection.isVisible({ timeout: 10000 }).catch(() => false);
    expect(isVisible).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Suite: SuperAdmin Users — analytics-consumer role toggle
// ---------------------------------------------------------------------------

test.describe('SuperAdmin Users — analytics-consumer toggle', () => {
  test.beforeEach(async ({ page }) => {
    await suppressOverlays(page);
    await gotoAuthenticated(page, '/superadmin/users');
    await dismissOverlays(page);
  });

  test('analytics-consumer toggle button is present in user table actions', async ({ page }) => {
    if (!await requireSuperAdmin(page)) return;

    const table = page.locator('table');
    const isVisible = await table.isVisible({ timeout: 8000 }).catch(() => false);
    if (!isVisible) {
      test.skip(true, 'No users table rendered (empty database)');
      return;
    }

    // Actions column should include chart/analytics icon button for the first row
    // The button may have title, aria-label, or tooltip text referencing "Analytics Consumer"
    const analyticsToggle = page
      .locator(
        'button[title*="Analytics"], button[aria-label*="Analytics"], button[title*="analytics"]'
      )
      .first();
    const hasToggle = await analyticsToggle.isVisible({ timeout: 5000 }).catch(() => false);
    expect(hasToggle).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Suite: AI Chatter Config Page (community admin setting)
// ---------------------------------------------------------------------------

test.describe('Admin AIChatter Config page', () => {
  let communityId;

  test.beforeEach(async ({ page }) => {
    await suppressOverlays(page);
    communityId = await resolveCommunityId(page);
    if (!communityId) {
      test.skip(true, 'No community available for test account');
      return;
    }
    await gotoAuthenticated(page, `/admin/${communityId}/ai-chatter`);
    await dismissOverlays(page);
  });

  test('page loads without crashing', async ({ page }) => {
    if (!communityId) return;
    const url = page.url();
    if (url.includes('/login')) {
      test.skip(true, 'Test account is not logged in');
      return;
    }

    const errorText = page.getByText(/something went wrong|500|internal server error/i);
    const hasError = await errorText.isVisible({ timeout: 3000 }).catch(() => false);
    expect(hasError).toBe(false);
  });

  test('AI Chatter heading is visible', async ({ page }) => {
    if (!communityId) return;
    const url = page.url();
    if (url.includes('/login') || !url.includes('/ai-chatter')) {
      test.skip(true, 'Test account lacks community admin access');
      return;
    }

    const heading = page.getByRole('heading', { name: /AI Chatter/i }).first();
    const isVisible = await heading.isVisible({ timeout: 8000 }).catch(() => false);
    expect(isVisible).toBe(true);
  });

  test('enable toggle is present', async ({ page }) => {
    if (!communityId) return;
    const url = page.url();
    if (url.includes('/login') || !url.includes('/ai-chatter')) {
      test.skip(true, 'Test account lacks community admin access');
      return;
    }

    const toggle = page
      .locator('input[type="checkbox"], button[role="switch"]')
      .first();
    const isVisible = await toggle.isVisible({ timeout: 8000 }).catch(() => false);
    expect(isVisible).toBe(true);
  });

  test('all config controls are present', async ({ page }) => {
    if (!communityId) return;
    const url = page.url();
    if (url.includes('/login') || !url.includes('/ai-chatter')) {
      test.skip(true, 'Test account lacks community admin access');
      return;
    }

    // Check for key labels
    const labels = [
      /max.*responses/i,
      /window.*duration|time window/i,
      /per.user/i,
      /probability/i,
      /message length/i,
    ];

    for (const label of labels) {
      const el = page.getByText(label).first();
      const isVisible = await el.isVisible({ timeout: 5000 }).catch(() => false);
      expect(isVisible, `Expected label matching ${label} to be visible`).toBe(true);
    }
  });

  test('Save button is present', async ({ page }) => {
    if (!communityId) return;
    const url = page.url();
    if (url.includes('/login') || !url.includes('/ai-chatter')) {
      test.skip(true, 'Test account lacks community admin access');
      return;
    }

    const saveBtn = page.getByRole('button', { name: /save/i }).first();
    const isVisible = await saveBtn.isVisible({ timeout: 8000 }).catch(() => false);
    expect(isVisible).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Suite: Data & Privacy — deletion flow entry point
// ---------------------------------------------------------------------------

test.describe('Account Settings — Data & Privacy section', () => {
  test.beforeEach(async ({ page }) => {
    await suppressOverlays(page);
    await gotoAuthenticated(page, '/dashboard/account');
    await dismissOverlays(page);
  });

  test('Data & Privacy section is present in account settings', async ({ page }) => {
    const url = page.url();
    if (url.includes('/login')) {
      test.skip(true, 'Test account is not logged in');
      return;
    }

    const privacySection = page.getByText(/data.*privacy|privacy.*data/i).first();
    const isVisible = await privacySection.isVisible({ timeout: 8000 }).catch(() => false);
    expect(isVisible).toBe(true);
  });

  test('"Delete My Data" button is present', async ({ page }) => {
    const url = page.url();
    if (url.includes('/login')) {
      test.skip(true, 'Test account is not logged in');
      return;
    }

    const deleteBtn = page
      .getByRole('button', { name: /delete.*data|request.*deletion/i })
      .first();
    const isVisible = await deleteBtn.isVisible({ timeout: 8000 }).catch(() => false);
    expect(isVisible).toBe(true);
  });
});
