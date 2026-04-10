const { test, expect } = require('./fixtures');

/**
 * Admin Sidebar Collapsible Sections E2E Tests
 *
 * Verifies that the reorganized admin sidebar works correctly:
 * - Sections expand and collapse on click
 * - Active route auto-expands its section
 * - All nav items within sections are reachable
 * - Platform/superadmin flat nav still works
 */

/**
 * Navigate to an admin page and wait for auth to resolve.
 * The ProtectedRoute briefly redirects to /login while loading=true,
 * then redirects back once the auth API call completes. We wait for
 * the URL to stabilize on the intended path before proceeding.
 */
async function gotoAdmin(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  // Wait until the URL is NOT the login page (auth resolved) or 15s timeout
  await page.waitForFunction(
    () => !window.location.pathname.startsWith('/login'),
    { timeout: 15000 }
  ).catch(() => {});
  // Wait for the sidebar to appear, confirming admin page is rendered
  await page.locator('aside').first().waitFor({ timeout: 10000 }).catch(() => {});
}

test.describe('Admin Sidebar Collapsible Sections', () => {
  test.setTimeout(60000);
  let communityId;

  test.beforeEach(async ({ page }) => {
    // 1. Use env var if set
    if (process.env.TEST_COMMUNITY_ID) {
      communityId = process.env.TEST_COMMUNITY_ID;
      return;
    }
    // 2. Navigate to root (loads storageState including localStorage JWT token),
    //    then read token and call API with Authorization header
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {}); // ensure prior API calls settle
    const token = await page.evaluate(() => localStorage.getItem('token')).catch(() => null);
    if (token) {
      try {
        const response = await page.request.get('/api/v1/auth/me', {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await response.json();
        const communities = data?.user?.communities || [];
        if (communities.length > 0) {
          communityId = String(communities[0].id);
          return;
        }
      } catch { /* fall through */ }
    }
    // 3. Fall back: look for admin link on dashboard
    await page.goto('/dashboard');
    const adminLink = page.locator('a[href*="/admin/"]').first();
    if (await adminLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await adminLink.getAttribute('href');
      communityId = href.match(/\/admin\/(\w+)/)?.[1];
    }
  });

  test('Sidebar renders section headers for community admin', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}`);

    const sectionLabels = ['Community', 'Engagement', 'Media', 'Modules', 'Loyalty', 'Moderation', 'AI', 'Platform', 'Settings'];
    for (const label of sectionLabels) {
      await expect(page.locator(`aside button:has-text("${label}")`).first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('Clicking a section header expands it', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}`);

    const engagementBtn = page.locator('aside button:has-text("Engagement")').first();
    await engagementBtn.click();

    await expect(page.locator('aside a:has-text("Forms")')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('aside a:has-text("Polls")')).toBeVisible({ timeout: 5000 });
  });

  test('Clicking expanded section collapses it', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}`);

    const engagementBtn = page.locator('aside button:has-text("Engagement")').first();

    // Expand
    await engagementBtn.click();
    await expect(page.locator('aside a:has-text("Forms")')).toBeVisible({ timeout: 5000 });

    // Collapse
    await engagementBtn.click();
    await expect(page.locator('aside a:has-text("Forms")')).not.toBeVisible({ timeout: 5000 });
  });

  test('Active section auto-expands on navigation', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }

    // Navigate directly to a page within Moderation section
    await gotoAdmin(page, `/admin/${communityId}/reputation`);

    // Moderation section should have auto-expanded via useEffect
    await expect(page.locator('aside a:has-text("Reputation")')).toBeVisible({ timeout: 8000 });
    await expect(page.locator('aside a:has-text("Bot Detection")')).toBeVisible({ timeout: 3000 });
  });

  test('Modules section contains Modules & Marketplace link', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}/modules`);

    await expect(page.locator('aside a:has-text("Modules & Marketplace")')).toBeVisible({ timeout: 8000 });
  });

  test('Community section contains expected items', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}`);

    // Community section auto-expands on /admin/:id (the overview URL).
    // Do NOT click — clicking would collapse it. Just verify items are visible.
    const expectedItems = ['Overview', 'Members', 'Announcements', 'Channels'];
    for (const label of expectedItems) {
      await expect(page.locator(`aside a:has-text("${label}")`).first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('Sidebar is scrollable (overflow-y-auto)', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}`);

    const aside = page.locator('aside').first();
    // SidebarMenu (react-libs) may use an inner scroll container rather than
    // putting overflow on the <aside> itself — check both.
    const overflowY = await aside.evaluate((el) => {
      const own = getComputedStyle(el).overflowY;
      if (['auto', 'scroll'].includes(own)) return own;
      for (const child of el.children) {
        const childOverflow = getComputedStyle(child).overflowY;
        if (['auto', 'scroll'].includes(childOverflow)) return childOverflow;
      }
      return own;
    });
    expect(['auto', 'scroll']).toContain(overflowY);
  });
});
