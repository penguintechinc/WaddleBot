const { test, expect } = require('@playwright/test');

test.describe('Platform Dashboard - All Platforms', () => {
  test('should display all 10 platforms in Users by Platform section', async ({ page }) => {
    await page.goto('/platform');
    await expect(page.locator('text=Users by Platform')).toBeVisible();

    const platforms = ['Discord', 'Twitch', 'Slack', 'YouTube', 'KICK', 'Telegram', 'Matrix', 'Guilded', 'Revolt', 'Hub Chat'];
    for (const platform of platforms) {
      await expect(page.locator(`text=${platform}`)).toBeVisible();
    }
  });

  test('should show count values for each platform', async ({ page }) => {
    await page.goto('/platform');
    await expect(page.locator('text=Users by Platform')).toBeVisible();
    // Each platform should have a numeric count (even if 0)
    const platformCards = page.locator('.grid >> text=/^\\d+$/');
    const count = await platformCards.count();
    expect(count).toBeGreaterThanOrEqual(10);
  });
});
