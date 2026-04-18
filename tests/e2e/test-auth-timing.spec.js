import { test, expect } from '@playwright/test';
import { AUTH_STATE_PATH } from './auth.setup';
import { storageState } from './playwright.config';

test.describe('CommunitiesPage Auth Timing', () => {
  test.use({ storageState: AUTH_STATE_PATH });

  test('Create community button visible to authenticated users', async ({ page }) => {
    // Navigate to /communities with authentication already loaded
    await page.goto('/communities', { waitUntil: 'networkidle' });
    
    // The button should be visible without race condition
    const button = page.locator('[data-testid="create-community-btn"]');
    
    // With the fix: button appears without loading state delay
    await expect(button).toBeVisible({ timeout: 5000 });
    
    // Verify button text
    await expect(button).toContainText('Create a Community');
  });
});
