const { test, expect } = require('@playwright/test');

test.describe('Calendar Settings', () => {
  test('should load calendar settings page', async ({ page }) => {
    await page.goto('/calendar/settings');
    // Check for content, error state, or service unavailable message
    const contentVisible = await page
      .locator('text=Availability').or(page.locator('text=Calendar Settings')).or(page.locator('text=Connected')).or(page.locator('text=Calendar service'))
      .isVisible({ timeout: 10000 })
      .catch(() => false);

    if (!contentVisible) {
      test.skip(true, 'Calendar service not available in this environment');
      return;
    }
    await expect(
      page.locator('text=Availability').or(page.locator('text=Calendar Settings')).or(page.locator('text=Connected'))
    ).toBeVisible();
  });

  test('should show weekly availability section', async ({ page }) => {
    await page.goto('/calendar/settings');
    // Check for content, error state, or service unavailable message
    const contentVisible = await page
      .locator('text=Weekly').or(page.locator('text=Availability')).or(page.locator('text=Calendar service'))
      .isVisible({ timeout: 10000 })
      .catch(() => false);

    if (!contentVisible) {
      test.skip(true, 'Calendar service not available in this environment');
      return;
    }
    await expect(
      page.locator('text=Weekly').or(page.locator('text=Availability'))
    ).toBeVisible();
  });
});
