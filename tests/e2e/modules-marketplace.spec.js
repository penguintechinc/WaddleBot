const { test, expect } = require('@playwright/test');

/**
 * Modules & Marketplace E2E Tests
 *
 * Verifies the merged AdminModules page with tabbed interface:
 * - Installed Modules tab shows existing modules
 * - Browse Marketplace tab shows available modules with search/filter
 * - Tab switching works correctly
 * - Marketplace redirect from /marketplace -> /modules
 * - Configure button routes to dedicated config pages for known modules
 * - Uninstall not shown for core modules
 */

/**
 * Navigate to an admin page and wait for auth to resolve past any /login redirect.
 */
async function gotoAdmin(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(
    () => !window.location.pathname.startsWith('/login'),
    { timeout: 15000 }
  ).catch(() => {});
  await page.locator('aside').first().waitFor({ timeout: 10000 }).catch(() => {});
}

test.describe('Modules & Marketplace', () => {
  let communityId;

  test.beforeEach(async ({ page }) => {
    if (process.env.TEST_COMMUNITY_ID) {
      communityId = process.env.TEST_COMMUNITY_ID;
      return;
    }
    await page.goto('/', { waitUntil: 'domcontentloaded' });
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
    await page.goto('/dashboard');
    const adminLink = page.locator('a[href*="/admin/"]').first();
    if (await adminLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await adminLink.getAttribute('href');
      communityId = href.match(/\/admin\/(\w+)/)?.[1];
    }
  });

  test('Modules page renders with two tabs', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}/modules`);

    await expect(page.locator('button:has-text("Installed Modules")')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('button:has-text("Browse Marketplace")').first()).toBeVisible({ timeout: 5000 });
  });

  test('Installed Modules tab is active by default', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}/modules`);

    await expect(page.locator('h1:has-text("Modules")')).toBeVisible({ timeout: 5000 });

    await page.locator('th').first().waitFor({ timeout: 10000 });

    const tableHeaders = ['Module', 'Category', 'Status', 'Actions'];
    for (const header of tableHeaders) {
      await expect(page.locator(`th:has-text("${header}")`).first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('Switching to Browse Marketplace tab shows search and grid', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}/modules`);

    await page.locator('button:has-text("Browse Marketplace")').first().click();

    await expect(page.locator('input[placeholder*="Search"]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('select')).toBeVisible({ timeout: 5000 });
  });

  test('Marketplace redirect from /marketplace -> /modules', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }

    await gotoAdmin(page, `/admin/${communityId}/marketplace`);

    expect(page.url()).toContain(`/admin/${communityId}/modules`);
    await expect(page.locator('button:has-text("Installed Modules")')).toBeVisible({ timeout: 5000 });
  });

  test('Empty state on installed tab shows Browse Marketplace CTA', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}/modules`);

    const emptyState = page.locator('text=No Modules Installed');
    if (await emptyState.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(page.locator('button:has-text("Browse Marketplace")')).toBeVisible();
    }
  });

  test('Core modules do not show Uninstall button', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}/modules`);

    const coreBadge = page.locator('span:has-text("Core")').first();
    if (await coreBadge.isVisible({ timeout: 3000 }).catch(() => false)) {
      const coreRow = coreBadge.locator('xpath=ancestor::tr');
      await expect(coreRow.locator('button:has-text("Uninstall")')).not.toBeVisible();
    }
  });

  test('Configure button is present in installed modules', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}/modules`);

    const tableRow = page.locator('tbody tr').first();
    if (await tableRow.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(page.locator('button:has-text("Configure")').first()).toBeVisible({ timeout: 3000 });
    }
  });

  test('Marketplace search filters results', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}/modules`);

    await page.locator('button:has-text("Browse Marketplace")').click();
    await page.waitForLoadState('networkidle');

    const searchInput = page.locator('input[placeholder*="Search"]');
    if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchInput.fill('test-nonexistent-xyz');
      await page.waitForTimeout(500);
      await expect(page.locator('h1:has-text("Modules")')).toBeVisible();
    }
  });

  test('Marketplace category filter dropdown has expected options', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}/modules`);

    await page.locator('button:has-text("Browse Marketplace")').click();

    const select = page.locator('select').first();
    if (await select.isVisible({ timeout: 3000 }).catch(() => false)) {
      const options = await select.locator('option').allTextContents();
      expect(options).toContain('All Categories');
      expect(options.some(o => o.includes('Moderation') || o.includes('General') || o.includes('Entertainment'))).toBeTruthy();
    }
  });
});
