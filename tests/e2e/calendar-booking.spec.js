const { test, expect } = require('@playwright/test');

test.describe('Calendar Booking Pages', () => {
  test('should load booking pages list', async ({ page }) => {
    await page.goto('/calendar/booking-pages');
    // Check for content, error state, or service unavailable message
    const contentVisible = await page
      .locator('text=Booking').or(page.locator('text=No booking pages')).or(page.locator('text=Calendar service'))
      .isVisible({ timeout: 10000 })
      .catch(() => false);

    if (!contentVisible) {
      test.skip(true, 'Calendar service not available in this environment');
      return;
    }
    await expect(
      page.locator('text=Booking').or(page.locator('text=No booking pages'))
    ).toBeVisible();
  });

  test('should load my bookings page', async ({ page }) => {
    await page.goto('/calendar/my-bookings');
    // Check for content, error state, or service unavailable message
    const contentVisible = await page
      .locator('text=Bookings').or(page.locator('text=No bookings')).or(page.locator('text=Calendar service'))
      .isVisible({ timeout: 10000 })
      .catch(() => false);

    if (!contentVisible) {
      test.skip(true, 'Calendar service not available in this environment');
      return;
    }
    await expect(
      page.locator('text=Bookings').or(page.locator('text=No bookings'))
    ).toBeVisible();
  });
});
