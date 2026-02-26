const { test, expect } = require('@playwright/test');

test.describe('Calendar Settings', () => {
  test('should load calendar settings page', async ({ page }) => {
    await page.goto('/calendar/settings');
    // Should show availability or connected calendars section
    await expect(
      page.locator('text=Availability').or(page.locator('text=Calendar Settings')).or(page.locator('text=Connected'))
    ).toBeVisible({ timeout: 10000 });
  });

  test('should show weekly availability section', async ({ page }) => {
    await page.goto('/calendar/settings');
    await expect(
      page.locator('text=Weekly').or(page.locator('text=Availability'))
    ).toBeVisible({ timeout: 10000 });
  });
});
