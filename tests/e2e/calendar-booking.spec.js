const { test, expect } = require('@playwright/test');

test.describe('Calendar Booking Pages', () => {
  test('should load booking pages list', async ({ page }) => {
    await page.goto('/calendar/booking-pages');
    await expect(
      page.locator('text=Booking').or(page.locator('text=No booking pages'))
    ).toBeVisible({ timeout: 10000 });
  });

  test('should load my bookings page', async ({ page }) => {
    await page.goto('/calendar/my-bookings');
    await expect(
      page.locator('text=Bookings').or(page.locator('text=No bookings'))
    ).toBeVisible({ timeout: 10000 });
  });
});
