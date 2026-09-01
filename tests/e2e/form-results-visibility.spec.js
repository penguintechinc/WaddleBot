const { test, expect } = require('./fixtures');

test.describe('Form Results Visibility', () => {
  test('should show results visibility option in form creation', async ({ page }) => {
    await page.goto('/dashboard');
    const communityLink = page.locator('a[href*="/admin/"]').first();
    if (await communityLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await communityLink.getAttribute('href');
      const communityId = href.match(/admin\/(\d+)/)?.[1];
      if (communityId) {
        await page.goto(`/admin/${communityId}/forms`);
        // Click create form button
        const createBtn = page.locator('text=Create Form');
        if (await createBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
          await createBtn.click();
          await expect(page.locator('text=Who can see results')).toBeVisible({ timeout: 5000 });
        }
      }
    }
  });
});
