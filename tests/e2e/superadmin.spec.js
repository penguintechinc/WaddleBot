/**
 * Super Admin E2E Tests
 *
 * Covers the super admin panel surfaces:
 *   - User Management: page loads, list renders, create user via FormModalBuilder
 *   - Communities: page loads, list renders
 *   - Platform Config: page loads
 *   - Module Registry: page loads
 *
 * These tests require the logged-in user to have super_admin role.
 * Tests are skipped gracefully if the user is not a super admin.
 *
 * Environment variables:
 *   BASE_URL        - Default: http://localhost:3000
 *   HUB_TEST_EMAIL  - Test user email (default: admin@localhost.local)
 *   HUB_TEST_PASS   - Test user password (default: admin123)
 */

const { test, expect } = require('@playwright/test');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Dismiss overlays if visible */
async function dismissOverlays(page) {
  const acceptBtn = page.locator('button[aria-label="Accept all cookies"], button:has-text("Accept All")').first();
  if (await acceptBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    await acceptBtn.click();
    await acceptBtn.waitFor({ state: 'hidden', timeout: 3000 }).catch(() => {});
  }
  const vendorDismiss = page.locator('button[title="Dismiss"]').first();
  if (await vendorDismiss.isVisible({ timeout: 1000 }).catch(() => false)) {
    await vendorDismiss.click();
    await vendorDismiss.waitFor({ state: 'hidden', timeout: 3000 }).catch(() => {});
  }
}

/** Check if user is on a super admin page (not redirected away) */
async function verifySuperAdminAccess(page) {
  const url = page.url();
  if (!url.includes('/superadmin')) {
    test.skip(true, 'Test account does not have super_admin access');
    return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
// Test Suite: Super Admin - User Management
// ---------------------------------------------------------------------------

test.describe('Super Admin - User Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/superadmin/users', { waitUntil: 'networkidle' });
    await dismissOverlays(page);
  });

  test('user management page loads with heading and table', async ({ page }) => {
    if (!await verifySuperAdminAccess(page)) return;

    // Heading
    const heading = page.getByRole('heading', { name: /User Management/i });
    await expect(heading).toBeVisible({ timeout: 8000 });

    // "New User" button
    const newUserBtn = page.getByRole('button', { name: /New User/i });
    await expect(newUserBtn).toBeVisible();

    // Users table or "No users found" message
    const table = page.locator('table');
    const noUsers = page.getByText('No users found');
    const hasTable = await table.isVisible({ timeout: 5000 }).catch(() => false);
    const hasEmpty = await noUsers.isVisible({ timeout: 2000 }).catch(() => false);
    expect(hasTable || hasEmpty).toBe(true);
  });

  test('user list shows at least one user with email column', async ({ page }) => {
    if (!await verifySuperAdminAccess(page)) return;

    // Wait for table to render
    const table = page.locator('table');
    const isVisible = await table.isVisible({ timeout: 8000 }).catch(() => false);
    if (!isVisible) {
      test.skip(true, 'No users table rendered (empty database)');
      return;
    }

    // Should have at least one row (the seeded admin)
    const rows = page.locator('table tbody tr');
    await expect(rows.first()).toBeVisible({ timeout: 5000 });
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);

    // Table headers should include Email, Username, Status, Roles, Actions
    await expect(page.locator('th:has-text("Email")')).toBeVisible();
    await expect(page.locator('th:has-text("Username")')).toBeVisible();
    await expect(page.locator('th:has-text("Status")')).toBeVisible();
  });

  test('create user modal opens and has email + password fields', async ({ page }) => {
    if (!await verifySuperAdminAccess(page)) return;

    // Click "New User"
    await page.getByRole('button', { name: /New User/i }).click();

    // FormModalBuilder should open with "Create New User" title
    const modalTitle = page.getByText('Create New User');
    await expect(modalTitle).toBeVisible({ timeout: 5000 });

    // Should have email and password fields
    const emailField = page.locator('input[type="email"], input[name="email"]');
    const passwordField = page.locator('input[type="password"], input[name="password"]');
    await expect(emailField).toBeVisible();
    await expect(passwordField).toBeVisible();

    // Should have Create and Cancel buttons
    await expect(page.getByRole('button', { name: /^Create$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Cancel/i })).toBeVisible();
  });

  test('create user modal validates required fields', async ({ page }) => {
    if (!await verifySuperAdminAccess(page)) return;

    // Open modal
    await page.getByRole('button', { name: /New User/i }).click();
    await expect(page.getByText('Create New User')).toBeVisible({ timeout: 5000 });

    // Click Create without filling fields
    await page.getByRole('button', { name: /^Create$/i }).click();

    // Should show validation errors (not crash with TypeError)
    // FormModalBuilder shows error text below fields
    await page.waitForTimeout(500);

    // The modal should still be open (no crash)
    await expect(page.getByText('Create New User')).toBeVisible();

    // Should show "required" validation messages
    const errors = page.locator('text=/required|must be/i');
    await expect(errors.first()).toBeVisible({ timeout: 3000 });
  });

  test('create user with valid data submits successfully', async ({ page }) => {
    if (!await verifySuperAdminAccess(page)) return;

    const testEmail = `e2etest+${Date.now()}@test.local`;
    const testPassword = 'TestPassword123!';

    // Open modal
    await page.getByRole('button', { name: /New User/i }).click();
    await expect(page.getByText('Create New User')).toBeVisible({ timeout: 5000 });

    // Fill form
    await page.locator('input[type="email"], input[name="email"]').fill(testEmail);
    await page.locator('input[type="password"], input[name="password"]').fill(testPassword);

    // Capture API response
    const [apiResponse] = await Promise.all([
      page.waitForResponse(
        r => r.url().includes('/api/v1/superadmin/users') && r.request().method() === 'POST',
        { timeout: 15000 }
      ),
      page.getByRole('button', { name: /^Create$/i }).click(),
    ]);

    const status = apiResponse.status();

    if (status === 429) {
      test.skip(true, 'Rate limited during user creation');
      return;
    }

    // Should succeed (201 or 200)
    expect([200, 201]).toContain(status);

    // Modal should close on success
    await expect(page.getByText('Create New User')).not.toBeVisible({ timeout: 5000 });

    // New user should appear in the table (use .first() since email may appear in multiple columns)
    await expect(page.getByText(testEmail).first()).toBeVisible({ timeout: 8000 });
  });

  test('create user cancel button closes modal without submitting', async ({ page }) => {
    if (!await verifySuperAdminAccess(page)) return;

    // Open modal
    await page.getByRole('button', { name: /New User/i }).click();
    await expect(page.getByText('Create New User')).toBeVisible({ timeout: 5000 });

    // Fill something
    await page.locator('input[type="email"], input[name="email"]').fill('cancel@test.local');

    // Click Cancel
    await page.getByRole('button', { name: /Cancel/i }).click();

    // Modal should close
    await expect(page.getByText('Create New User')).not.toBeVisible({ timeout: 3000 });

    // No API call should have been made (user shouldn't appear)
    await expect(page.getByText('cancel@test.local')).not.toBeVisible({ timeout: 2000 });
  });

  test('verify button visible in actions column', async ({ page }) => {
    if (!await verifySuperAdminAccess(page)) return;

    const table = page.locator('table');
    const isVisible = await table.isVisible({ timeout: 8000 }).catch(() => false);
    if (!isVisible) {
      test.skip(true, 'No users table rendered (empty database)');
      return;
    }

    // CheckBadgeIcon button should be in the first row with verify/unverify title
    const verifyBtn = page.locator('table tbody tr').first()
      .locator('button[title="Verify email"], button[title="Remove email verification"]');
    await expect(verifyBtn).toBeVisible({ timeout: 5000 });
  });

  test('verify modal opens with Cancel and Verify buttons, cancel closes it', async ({ page }) => {
    if (!await verifySuperAdminAccess(page)) return;

    const table = page.locator('table');
    const isVisible = await table.isVisible({ timeout: 8000 }).catch(() => false);
    if (!isVisible) {
      test.skip(true, 'No users table rendered (empty database)');
      return;
    }

    // Click the verify button on the first row
    const verifyBtn = page.locator('table tbody tr').first()
      .locator('button[title="Verify email"], button[title="Remove email verification"]');
    await verifyBtn.click();

    // Modal should appear with "Email Verification" heading
    await expect(page.getByText('Email Verification')).toBeVisible({ timeout: 5000 });

    // Should have Cancel and Verify/Unverify buttons
    await expect(page.getByRole('button', { name: /Cancel/i })).toBeVisible();
    const actionBtn = page.getByRole('button', { name: /^(Verify|Unverify)$/i });
    await expect(actionBtn).toBeVisible();

    // Cancel should close the modal
    await page.getByRole('button', { name: /Cancel/i }).click();
    await expect(page.getByText('Email Verification')).not.toBeVisible({ timeout: 3000 });
  });

  test('verification status badge shown in status column', async ({ page }) => {
    if (!await verifySuperAdminAccess(page)) return;

    const table = page.locator('table');
    const isVisible = await table.isVisible({ timeout: 8000 }).catch(() => false);
    if (!isVisible) {
      test.skip(true, 'No users table rendered (empty database)');
      return;
    }

    // Each row should have either "Verified" or "Unverified" badge
    const firstRow = page.locator('table tbody tr').first();
    const verifiedBadge = firstRow.locator('text=/^Verified$|^Unverified$/');
    await expect(verifiedBadge).toBeVisible({ timeout: 5000 });
  });

  test('verify email API call succeeds via modal confirm', async ({ page }) => {
    if (!await verifySuperAdminAccess(page)) return;

    const table = page.locator('table');
    const isVisible = await table.isVisible({ timeout: 8000 }).catch(() => false);
    if (!isVisible) {
      test.skip(true, 'No users table rendered (empty database)');
      return;
    }

    // Click the verify button on the first row
    const verifyBtn = page.locator('table tbody tr').first()
      .locator('button[title="Verify email"], button[title="Remove email verification"]');
    await verifyBtn.click();

    // Modal should appear
    await expect(page.getByText('Email Verification')).toBeVisible({ timeout: 5000 });

    // Click Verify/Unverify and capture the API response
    const actionBtn = page.getByRole('button', { name: /^(Verify|Unverify)$/i });
    const [apiResponse] = await Promise.all([
      page.waitForResponse(
        r => r.url().includes('/verify-email') && r.request().method() === 'POST',
        { timeout: 15000 }
      ),
      actionBtn.click(),
    ]);

    const status = apiResponse.status();

    if (status === 429) {
      test.skip(true, 'Rate limited during verify email');
      return;
    }

    // Should succeed (200)
    expect(status).toBe(200);

    // Modal should close on success
    await expect(page.getByText('Email Verification')).not.toBeVisible({ timeout: 5000 });
  });

  test('search filter narrows user list', async ({ page }) => {
    if (!await verifySuperAdminAccess(page)) return;

    // Wait for initial load
    const table = page.locator('table');
    const isVisible = await table.isVisible({ timeout: 8000 }).catch(() => false);
    if (!isVisible) {
      test.skip(true, 'No users table rendered');
      return;
    }

    // Get initial row count
    await page.waitForTimeout(500);
    const initialCount = await page.locator('table tbody tr').count();

    // Search for something specific
    const searchInput = page.locator('input[placeholder*="Search"]');
    await searchInput.fill('admin');
    await page.waitForTimeout(1000); // debounce

    // Wait for table to update
    await page.waitForLoadState('networkidle');

    // Should still have results (admin user exists)
    const filteredCount = await page.locator('table tbody tr').count();
    expect(filteredCount).toBeGreaterThan(0);
    expect(filteredCount).toBeLessThanOrEqual(initialCount);
  });
});

// ---------------------------------------------------------------------------
// Test Suite: Super Admin - Page Navigation
// ---------------------------------------------------------------------------

test.describe('Super Admin - Page Navigation', () => {
  test('/superadmin loads dashboard page', async ({ page }) => {
    await page.goto('/superadmin', { waitUntil: 'networkidle' });
    await dismissOverlays(page);
    if (!await verifySuperAdminAccess(page)) return;

    // Should have some heading content
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
  });

  test('/superadmin/communities loads communities list', async ({ page }) => {
    await page.goto('/superadmin/communities', { waitUntil: 'networkidle' });
    await dismissOverlays(page);
    if (!await verifySuperAdminAccess(page)) return;

    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
  });

  test('/superadmin/modules loads module registry', async ({ page }) => {
    await page.goto('/superadmin/modules', { waitUntil: 'networkidle' });
    await dismissOverlays(page);
    if (!await verifySuperAdminAccess(page)) return;

    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
  });

  test('/superadmin/platform-config loads platform config', async ({ page }) => {
    await page.goto('/superadmin/platform-config', { waitUntil: 'networkidle' });
    await dismissOverlays(page);
    if (!await verifySuperAdminAccess(page)) return;

    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
  });

  test('/superadmin/vendor-requests loads vendor requests', async ({ page }) => {
    await page.goto('/superadmin/vendor-requests', { waitUntil: 'networkidle' });
    await dismissOverlays(page);
    if (!await verifySuperAdminAccess(page)) return;

    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
  });
});
