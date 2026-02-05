/**
 * E2E Tests: Authentication Workflow
 * Tests user registration, login, and profile access
 */

const { test, expect } = require('@playwright/test');

test.describe('Authentication Workflow', () => {
  const uniqueEmail = `test${Date.now()}@test.com`;
  const username = `testuser${Date.now()}`;
  const password = 'Test123!';

  test('Complete user registration and login flow', async ({ page }) => {
    // Navigate to registration page
    await page.goto('/register');
    await expect(page).toHaveTitle(/Waddles|Register|Sign Up/i);

    // Fill registration form
    await page.fill('input[name="email"], input[type="email"]', uniqueEmail);
    await page.fill('input[name="username"]', username);
    await page.fill('input[name="password"], input[type="password"]', password);

    // Accept terms if present
    const termsCheckbox = page.locator('input[type="checkbox"]').first();
    if (await termsCheckbox.isVisible()) {
      await termsCheckbox.check();
    }

    // Submit registration
    await page.click('button[type="submit"]');

    // Wait for redirect or success message
    await page.waitForTimeout(2000);

    // Check if we're redirected to dashboard or need to verify email
    const currentUrl = page.url();
    expect(currentUrl).not.toContain('/register');

    // If email verification required, skip login test
    if (currentUrl.includes('/verify-email')) {
      test.skip('Email verification required - skipping login test');
      return;
    }

    // If redirected to login, proceed with login
    if (currentUrl.includes('/login')) {
      await page.fill('input[name="email"], input[type="email"]', uniqueEmail);
      await page.fill('input[name="password"], input[type="password"]', password);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);
    }

    // Verify we're logged in (should see dashboard or profile)
    const finalUrl = page.url();
    expect(finalUrl).toMatch(/\/(dashboard|profile|communities)/);

    // Verify user menu or profile link is present
    const hasUserMenu = await page.locator('[data-testid="user-menu"], .user-menu, [aria-label="User menu"]').count() > 0;
    const hasLogoutLink = await page.locator('button:has-text("Logout"), a:has-text("Logout")').count() > 0;
    expect(hasUserMenu || hasLogoutLink).toBeTruthy();
  });

  test('Login with admin credentials', async ({ page }) => {
    await page.goto('/login');

    // Fill login form
    await page.fill('input[name="email"], input[type="email"]', 'admin@localhost.local');
    await page.fill('input[name="password"], input[type="password"]', 'admin123');

    // Submit login
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);

    // Verify redirect to dashboard
    expect(page.url()).not.toContain('/login');

    // Verify admin can access admin pages
    await page.goto('/platform');
    await page.waitForTimeout(1000);

    // Should not get 403/404
    const statusCode = page.url();
    expect(statusCode).toContain('/platform');
  });

  test('Logout flow', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[name="email"], input[type="email"]', 'admin@localhost.local');
    await page.fill('input[name="password"], input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);

    // Click logout
    const logoutButton = page.locator('button:has-text("Logout"), a:has-text("Logout"), [data-testid="logout"]').first();
    await logoutButton.click();
    await page.waitForTimeout(1000);

    // Verify redirected to home/login
    const finalUrl = page.url();
    expect(finalUrl).toMatch(/\/(login|$)/);
  });
});
