const { test, expect } = require('@playwright/test');

/**
 * Module Config Pages E2E Tests
 *
 * Verifies the 6 new module config pages:
 * - AdminLfgConfig (/modules/lfg/config)
 * - AdminClipConfig (/modules/clip/config)
 * - AdminAliasConfig (/modules/alias/config)
 * - AdminMemoriesConfig (/modules/memories/config)
 * - AdminServerStatusConfig (/modules/server-status/config)
 * - AdminServerManagerConfig (/modules/server-manager/config)
 *
 * Each test verifies: page loads, has back link to /modules,
 * shows expected form fields, and Save button is present.
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

const CONFIG_PAGES = [
  {
    slug: 'lfg',
    title: 'LFG Configuration',
    fields: ['Max Party Size', 'Timeout'],
  },
  {
    slug: 'clip',
    title: 'Clip Configuration',
    fields: ['Max Clip Duration', 'Storage Retention'],
  },
  {
    slug: 'alias',
    title: 'Alias Configuration',
    fields: ['Max Aliases Per User'],
  },
  {
    slug: 'memories',
    title: 'Memories Configuration',
    fields: ['Retention', 'Max Memories Per User'],
  },
  {
    slug: 'server-status',
    title: 'Server Status Configuration',
    fields: ['Polling Interval', 'Monitored Servers'],
  },
  {
    slug: 'server-manager',
    title: 'Server Manager Configuration',
    fields: ['Allowed Commands', 'RCON Timeout'],
  },
];

test.describe('Module Config Pages', () => {
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

  for (const { slug, title, fields } of CONFIG_PAGES) {
    test(`${title} page loads with form fields`, async ({ page }) => {
      if (!communityId) { test.skip('No community found'); return; }

      await gotoAdmin(page, `/admin/${communityId}/modules/${slug}/config`);

      await expect(page.locator(`h1:has-text("${title}")`)).toBeVisible({ timeout: 10000 });

      const backLink = page.locator('a[href*="/modules"]').first();
      await expect(backLink).toBeVisible({ timeout: 5000 });

      await expect(page.locator('button:has-text("Save Configuration")')).toBeVisible({ timeout: 5000 });

      for (const fieldLabel of fields) {
        await expect(page.locator(`text=${fieldLabel}`).first()).toBeVisible({ timeout: 5000 });
      }
    });

    test(`${title} back link navigates to /modules`, async ({ page }) => {
      if (!communityId) { test.skip('No community found'); return; }

      await gotoAdmin(page, `/admin/${communityId}/modules/${slug}/config`);
      await page.locator('h1').first().waitFor({ timeout: 10000 });

      const backLink = page.locator('a[href*="/modules"]').first();
      if (await backLink.isVisible({ timeout: 5000 }).catch(() => false)) {
        await backLink.click();
        await page.waitForLoadState('networkidle');
        expect(page.url()).toContain(`/admin/${communityId}/modules`);
        expect(page.url()).not.toContain(`/${slug}/config`);
      }
    });
  }

  test('LFG config has Enabled toggle', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}/modules/lfg/config`);

    await expect(page.locator('h1:has-text("LFG")').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Enabled').first()).toBeVisible({ timeout: 5000 });
  });

  test('Server Status config has Add Server button', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}/modules/server-status/config`);

    await expect(page.locator('h1:has-text("Server Status")').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('button:has-text("Add Server")')).toBeVisible({ timeout: 5000 });
  });

  test('Server Status config can add and display a server entry', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}/modules/server-status/config`);
    await page.locator('h1').first().waitFor({ timeout: 10000 });

    const addBtn = page.locator('button:has-text("Add Server")');
    if (await addBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await addBtn.click();
      await expect(page.locator('input[placeholder="Name"]')).toBeVisible({ timeout: 3000 });
      await expect(page.locator('input[placeholder="Host"]')).toBeVisible({ timeout: 3000 });
    }
  });

  test('Server Manager config has RCON Allowed Commands field', async ({ page }) => {
    if (!communityId) { test.skip('No community found'); return; }
    await gotoAdmin(page, `/admin/${communityId}/modules/server-manager/config`);

    await expect(page.locator('h1:has-text("Server Manager")').first()).toBeVisible({ timeout: 10000 });
    await expect(
      page.locator('input[placeholder*="status"]').or(page.locator('text=Allowed Commands')).first()
    ).toBeVisible({ timeout: 5000 });
  });
});
