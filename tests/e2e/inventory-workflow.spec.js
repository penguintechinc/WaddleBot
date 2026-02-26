const { test, expect } = require('@playwright/test');

test.describe('Inventory (Quartermaster) System', () => {
  test('should load admin inventory page', async ({ page }) => {
    await page.goto('/dashboard');
    const communityLink = page.locator('a[href*="/admin/"]').first();
    if (await communityLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await communityLink.getAttribute('href');
      const communityId = href.match(/admin\/(\d+)/)?.[1];
      if (communityId) {
        await page.goto(`/admin/${communityId}/inventory`);
        await expect(
          page.locator('text=Inventory').or(page.locator('text=Items')).or(page.locator('text=Quartermaster'))
        ).toBeVisible({ timeout: 10000 });
      }
    }
  });

  test('should show Items and Claims tabs', async ({ page }) => {
    await page.goto('/dashboard');
    const communityLink = page.locator('a[href*="/admin/"]').first();
    if (await communityLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await communityLink.getAttribute('href');
      const communityId = href.match(/admin\/(\d+)/)?.[1];
      if (communityId) {
        await page.goto(`/admin/${communityId}/inventory`);
        await expect(page.locator('text=Items')).toBeVisible({ timeout: 10000 });
        await expect(page.locator('text=Claims')).toBeVisible({ timeout: 10000 });
      }
    }
  });

  test('should load community inventory browse page', async ({ page }) => {
    await page.goto('/dashboard');
    const communityLink = page.locator('a[href*="/admin/"]').first();
    if (await communityLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await communityLink.getAttribute('href');
      const communityId = href.match(/admin\/(\d+)/)?.[1];
      if (communityId) {
        await page.goto(`/community/${communityId}/inventory`);
        await expect(
          page.locator('text=Inventory').or(page.locator('text=Available')).or(page.locator('text=Browse'))
        ).toBeVisible({ timeout: 10000 });
      }
    }
  });

  test('should load my items page', async ({ page }) => {
    await page.goto('/dashboard');
    const communityLink = page.locator('a[href*="/admin/"]').first();
    if (await communityLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await communityLink.getAttribute('href');
      const communityId = href.match(/admin\/(\d+)/)?.[1];
      if (communityId) {
        await page.goto(`/community/${communityId}/inventory/my-items`);
        await expect(
          page.locator('text=My Items').or(page.locator('text=Claims')).or(page.locator('text=Checked Out'))
        ).toBeVisible({ timeout: 10000 });
      }
    }
  });
});
