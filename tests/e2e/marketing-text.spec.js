const { test, expect } = require('@playwright/test');

test.describe('Marketing Text Updates', () => {
  test('should show workforce language in hero', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Workforce')).toBeVisible();
  });

  test('should show updated features heading', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Community or Workforce')).toBeVisible();
  });

  test('should mention all platforms in features', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Telegram')).toBeVisible();
  });

  test('should show updated CTA text', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Community or Workforce?')).toBeVisible();
  });

  test('should show updated footer text', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=workforce management')).toBeVisible();
  });
});
