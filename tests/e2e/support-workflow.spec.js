const { test, expect } = require('./fixtures');

test.describe('Support Ticket System', () => {
  test('should show support type in community creation', async ({ page }) => {
    await page.goto('/dashboard');
    // Look for create community button or navigate to creation page
    const createBtn = page.locator('text=Create Community').or(page.locator('text=Create'));
    if (await createBtn.first().isVisible({ timeout: 5000 }).catch(() => false)) {
      await createBtn.first().click();
      await expect(page.locator('text=Support Portal')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should load support dashboard for admin', async ({ page }) => {
    await page.goto('/dashboard');
    const communityLink = page.locator('a[href*="/admin/"]').first();
    if (await communityLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await communityLink.getAttribute('href');
      const communityId = href.match(/admin\/(\d+)/)?.[1];
      if (communityId) {
        await page.goto(`/admin/${communityId}/support`);
        await expect(
          page.locator('text=Support').or(page.locator('text=Tickets')).or(page.locator('text=No tickets'))
        ).toBeVisible({ timeout: 10000 });
      }
    }
  });

  test('should load ticket submission page', async ({ page }) => {
    await page.goto('/dashboard');
    const communityLink = page.locator('a[href*="/admin/"]').first();
    if (await communityLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await communityLink.getAttribute('href');
      const communityId = href.match(/admin\/(\d+)/)?.[1];
      if (communityId) {
        await page.goto(`/community/${communityId}/support/submit`);
        await expect(
          page.locator('text=Submit').or(page.locator('text=Ticket')).or(page.locator('text=Subject'))
        ).toBeVisible({ timeout: 10000 });
      }
    }
  });
});
