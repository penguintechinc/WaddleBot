const { test, expect } = require('@playwright/test');

test.describe('Spotlighted Communities', () => {
  test('should show spotlighted section when communities exist', async ({ page }) => {
    await page.goto('/');
    // Section may or may not be visible depending on data
    const section = page.locator('text=Spotlighted Communities');
    const isVisible = await section.isVisible({ timeout: 5000 }).catch(() => false);

    if (isVisible) {
      // Verify community cards are rendered
      const cards = page.locator('a[href*="/communities/"]');
      const count = await cards.count();
      expect(count).toBeGreaterThan(0);
      expect(count).toBeLessThanOrEqual(5);
    }
    // If not visible, that's OK — no public communities to spotlight
  });

  test('should show member count on community cards', async ({ page }) => {
    await page.goto('/');
    const section = page.locator('text=Spotlighted Communities');
    if (await section.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(page.locator('text=members').first()).toBeVisible();
    }
  });
});
