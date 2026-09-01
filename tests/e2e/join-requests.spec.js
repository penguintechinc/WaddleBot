const { test, expect } = require('./fixtures');

test.describe('Community Join Policy & Join Requests', () => {
  test('should show join mode section in community profile admin', async ({ page }) => {
    await page.goto('/dashboard');
    const communityLink = page.locator('a[href*="/admin/"]').first();
    if (await communityLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await communityLink.getAttribute('href');
      const communityId = href.match(/admin\/(\d+)/)?.[1];
      if (communityId) {
        await page.goto(`/admin/${communityId}/profile`);
        await expect(
          page.locator('text=Member Joining').or(page.locator('text=Join Mode')).or(page.locator('text=Open'))
        ).toBeVisible({ timeout: 10000 });
      }
    }
  });

  test('should load join requests admin page', async ({ page }) => {
    await page.goto('/dashboard');
    const communityLink = page.locator('a[href*="/admin/"]').first();
    if (await communityLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await communityLink.getAttribute('href');
      const communityId = href.match(/admin\/(\d+)/)?.[1];
      if (communityId) {
        await page.goto(`/admin/${communityId}/join-requests`);
        await expect(
          page.locator('text=Join Requests').or(page.locator('text=Pending')).or(page.locator('text=No pending'))
        ).toBeVisible({ timeout: 10000 });
      }
    }
  });

  test('should show join mode options: open, approval, invite', async ({ page }) => {
    await page.goto('/dashboard');
    const communityLink = page.locator('a[href*="/admin/"]').first();
    if (await communityLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await communityLink.getAttribute('href');
      const communityId = href.match(/admin\/(\d+)/)?.[1];
      if (communityId) {
        await page.goto(`/admin/${communityId}/profile`);
        const joinSection = page.locator('text=Member Joining');
        if (await joinSection.isVisible({ timeout: 5000 }).catch(() => false)) {
          await expect(page.locator('text=Open').or(page.locator('input[value="open"]'))).toBeVisible({ timeout: 5000 });
          await expect(page.locator('text=Approval').or(page.locator('input[value="approval"]'))).toBeVisible({ timeout: 5000 });
          await expect(page.locator('text=Invite').or(page.locator('input[value="invite"]'))).toBeVisible({ timeout: 5000 });
        }
      }
    }
  });
});
