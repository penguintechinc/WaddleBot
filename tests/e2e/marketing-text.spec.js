const { test, expect } = require('./fixtures');

test.describe('Marketing Text Updates', () => {
  test('should show workforce language in hero', async ({ page }) => {
    await page.goto('/');
    // The hero h1 contains "Workforce" but so do the features and CTA headings.
    // Use getByRole to scope to the h1 specifically.
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Workforce');
  });

  test('should show updated features heading', async ({ page }) => {
    await page.goto('/');
    // "Community or Workforce" appears in both the features h2 and the CTA h2.
    // Use .first() to avoid strict-mode violation.
    await expect(page.locator('text=Community or Workforce').first()).toBeVisible();
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
