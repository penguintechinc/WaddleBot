const { test, expect } = require('./fixtures');

// ---------------------------------------------------------------------------
// Helper: skip gracefully if the test user lacks platform-admin role.
// Navigating to /platform redirects to /dashboard when the role is absent.
// ---------------------------------------------------------------------------
async function verifyPlatformAdminAccess(page) {
  const url = page.url();
  if (!url.includes('/platform')) {
    test.skip(true, 'Test account does not have platform-admin access');
    return false;
  }
  return true;
}

test.describe('Platform Dashboard - All Platforms', () => {
  test('should display all 10 platforms in Users by Platform section', async ({ page }) => {
    await page.goto('/platform', { waitUntil: 'networkidle' });
    if (!await verifyPlatformAdminAccess(page)) return;

    await expect(page.locator('text=Users by Platform')).toBeVisible();

    // platformConfig.js defines exactly these 10 platforms (labels from label field)
    const platforms = ['Discord', 'Twitch', 'Slack', 'YouTube', 'KICK', 'Telegram', 'Matrix', 'Guilded', 'Revolt', 'Hub Chat'];
    for (const platform of platforms) {
      await expect(page.locator(`text=${platform}`)).toBeVisible();
    }
  });

  test('should show count values for each platform', async ({ page }) => {
    await page.goto('/platform', { waitUntil: 'networkidle' });
    if (!await verifyPlatformAdminAccess(page)) return;

    await expect(page.locator('text=Users by Platform')).toBeVisible();
    // Each platform renders a numeric count (0 or higher) inside the platform grid.
    // Use a locator scoped to the platform grid section to count numeric values.
    const platformSection = page.locator('.card').filter({ hasText: 'Users by Platform' });
    const numericCells = platformSection.locator('.text-2xl.font-bold');
    const count = await numericCells.count();
    expect(count).toBeGreaterThanOrEqual(10);
  });
});
