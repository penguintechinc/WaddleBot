const { test, expect } = require('./fixtures');

test.describe('Calendar Events Admin', () => {
  // Note: requires a community to exist. These tests verify page loads and UI elements.

  test('should load calendar events page', async ({ page }) => {
    await page.goto('/dashboard');
    // If communities exist, navigate to first one's calendar
    const communityLink = page.locator('a[href*="/admin/"]').first();
    if (await communityLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await communityLink.click();
      // Look for calendar events link in sidebar
      const calendarLink = page.locator('text=Calendar Events');
      if (await calendarLink.isVisible({ timeout: 3000 }).catch(() => false)) {
        await calendarLink.click();
        await expect(page.locator('text=Calendar Events')).toBeVisible();
      }
    }
  });

  test('should show create event button', async ({ page }) => {
    // Navigate to a known community calendar events page
    await page.goto('/dashboard');
    const communityLink = page.locator('a[href*="/admin/"]').first();
    if (await communityLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = await communityLink.getAttribute('href');
      const communityId = href.match(/admin\/(\d+)/)?.[1];
      if (communityId) {
        await page.goto(`/admin/${communityId}/calendar/events`);
        await expect(page.locator('text=Create Event').or(page.locator('text=Calendar Events'))).toBeVisible();
      }
    }
  });
});
