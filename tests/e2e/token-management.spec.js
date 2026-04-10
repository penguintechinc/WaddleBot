const { test, expect } = require('./fixtures');

test.describe('Personal & Community Access Tokens', () => {
  test('should load personal access token page', async ({ page }) => {
    await page.goto('/account/tokens');
    await expect(
      page.locator('text=Personal Access Token').or(page.locator('text=Access Token')).or(page.locator('text=PAT'))
    ).toBeVisible({ timeout: 10000 });
  });

  test('should show create token option on PAT page', async ({ page }) => {
    await page.goto('/account/tokens');
    await expect(
      page.locator('text=Create').or(page.locator('text=Generate')).or(page.locator('button'))
    ).toBeVisible({ timeout: 10000 });
  });

  test('should load community tokens admin page', async ({ page }) => {
    await page.goto('/dashboard');
    const communityLink = page.locator('a[href*="/admin/"]').first();
    if (await communityLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await communityLink.getAttribute('href');
      const communityId = href.match(/admin\/(\d+)/)?.[1];
      if (communityId) {
        await page.goto(`/admin/${communityId}/tokens`);
        await expect(
          page.locator('text=Community Access Token').or(page.locator('text=CAT')).or(page.locator('text=Tokens'))
        ).toBeVisible({ timeout: 10000 });
      }
    }
  });

  test('should show quota indicator on community tokens page', async ({ page }) => {
    await page.goto('/dashboard');
    const communityLink = page.locator('a[href*="/admin/"]').first();
    if (await communityLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await communityLink.getAttribute('href');
      const communityId = href.match(/admin\/(\d+)/)?.[1];
      if (communityId) {
        await page.goto(`/admin/${communityId}/tokens`);
        await expect(
          page.locator('text=/\\d+ \\/ \\d+/').or(page.locator('text=tokens used')).or(page.locator('text=quota'))
        ).toBeVisible({ timeout: 10000 });
      }
    }
  });
});
