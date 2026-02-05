const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const BASE_URL = 'http://localhost:8060';
const OUTPUT_DIR = path.join(__dirname, '..', 'docs', 'screenshots');

// Waddles Hub pages to capture
// Note: Community ID 2 is the first real community (ID 1 may not exist)
const COMMUNITY_ID = 2;
const pages = [
  // Public/Auth pages
  { name: 'login', path: '/login' },

  // Dashboard pages
  { name: 'dashboard', path: '/dashboard' },
  { name: 'dashboard-settings', path: '/dashboard/settings' },
  { name: 'dashboard-profile', path: '/dashboard/profile' },

  // Community pages
  { name: 'communities', path: '/communities' },
  { name: 'community-dashboard', path: `/dashboard/community/${COMMUNITY_ID}` },
  { name: 'community-settings', path: `/dashboard/community/${COMMUNITY_ID}/settings` },
  { name: 'community-chat', path: `/dashboard/community/${COMMUNITY_ID}/chat` },
  { name: 'community-leaderboard', path: `/dashboard/community/${COMMUNITY_ID}/leaderboard` },
  { name: 'community-members', path: `/dashboard/community/${COMMUNITY_ID}/members` },

  // Admin pages
  { name: 'admin-overview', path: `/admin/${COMMUNITY_ID}` },
  { name: 'admin-members', path: `/admin/${COMMUNITY_ID}/members` },
  { name: 'admin-workflows', path: `/admin/${COMMUNITY_ID}/workflows` },
  { name: 'admin-modules', path: `/admin/${COMMUNITY_ID}/modules` },
  { name: 'admin-marketplace', path: `/admin/${COMMUNITY_ID}/marketplace` },
  { name: 'admin-browser-sources', path: `/admin/${COMMUNITY_ID}/browser-sources` },
  { name: 'admin-domains', path: `/admin/${COMMUNITY_ID}/domains` },
  { name: 'admin-servers', path: `/admin/${COMMUNITY_ID}/servers` },
  { name: 'admin-mirror-groups', path: `/admin/${COMMUNITY_ID}/mirror-groups` },
  { name: 'admin-leaderboard-config', path: `/admin/${COMMUNITY_ID}/leaderboard` },
  { name: 'admin-community-profile', path: `/admin/${COMMUNITY_ID}/profile` },
  { name: 'admin-reputation', path: `/admin/${COMMUNITY_ID}/reputation` },
  { name: 'admin-ai-insights', path: `/admin/${COMMUNITY_ID}/ai-insights` },
  { name: 'admin-ai-config', path: `/admin/${COMMUNITY_ID}/ai-config` },

  // SuperAdmin pages
  { name: 'superadmin-dashboard', path: '/superadmin' },
  { name: 'superadmin-communities', path: '/superadmin/communities' },
];

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function getAuthToken(page) {
  try {
    console.log('  Step 1: Navigating to login page...');
    // Navigate to login to get CSRF token set in cookies
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await sleep(800);

    console.log('  Step 2: Getting CSRF token from cookies...');
    // Extract CSRF token from Puppeteer's cookie store
    const cookies = await page.cookies();
    let csrfToken = null;
    for (const cookie of cookies) {
      if (cookie.name === 'XSRF-TOKEN') {
        csrfToken = cookie.value;
        console.log(`  ✓ CSRF token found: ${csrfToken.substring(0, 8)}...`);
        break;
      }
    }

    if (!csrfToken) {
      console.log('  ✗ No CSRF token in cookies, cannot proceed');
      return false;
    }

    console.log('  Step 3: Logging in via API call from within page...');
    // Use page.evaluate to make the API call from within the browser context
    // This ensures cookies are properly handled
    const result = await page.evaluate(
      async (baseUrl, email, password, token) => {
        try {
          const response = await fetch(`${baseUrl}/api/v1/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-XSRF-TOKEN': token,
            },
            credentials: 'include', // Include cookies
            body: JSON.stringify({ email, password }),
          });

          if (response.ok) {
            const data = await response.json();
            if (data.success && data.token) {
              localStorage.setItem('token', data.token);
              return { success: true, token: data.token };
            }
          } else {
            const error = await response.text();
            return { success: false, error: `HTTP ${response.status}: ${error}` };
          }
        } catch (err) {
          return { success: false, error: err.message };
        }
      },
      BASE_URL,
      'admin@localhost.net',
      'admin123',
      csrfToken
    );

    if (result.success) {
      console.log('  ✓ Login successful! Token stored in localStorage');
      await sleep(500);

      // Verify we can access protected pages
      try {
        await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'domcontentloaded', timeout: 15000 });
        const currentUrl = page.url();
        if (!currentUrl.includes('/login')) {
          console.log(`  ✓ Verified access to dashboard`);
          return true;
        }
      } catch (e) {
        console.log(`  ⚠️  Could not verify dashboard access: ${e.message}`);
        // Still consider login successful if token is stored
        return true;
      }
    } else {
      console.error(`  ✗ Login failed: ${result.error}`);
      return false;
    }
  } catch (error) {
    console.error(`  ✗ Error during login: ${error.message}`);
    return false;
  }
}

async function captureScreenshots() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  console.log('Launching browser...');
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });

  // Log in via UI (this also shows the login page)
  console.log('Attempting to log in...');
  const loginSuccess = await getAuthToken(page);

  // Capture login page screenshot (take it after login attempt)
  if (!loginSuccess) {
    console.log('\nCapturing login page...');
    try {
      // Refresh login page if login failed
      await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await sleep(1000);
      await page.screenshot({ path: path.join(OUTPUT_DIR, 'login.png') });
      console.log('  ✓ Saved login.png');
    } catch (error) {
      console.error('  ✗ Error capturing login:', error.message);
    }
    console.log('\n⚠️  Could not log in, will capture public pages only');
  } else {
    console.log('\n✓ Successfully authenticated, capturing authenticated pages...');
  }

  // Capture all other pages
  console.log('\nCapturing pages...');
  for (const pageInfo of pages) {
    if (pageInfo.name === 'login') continue;

    try {
      console.log(`  ${pageInfo.name}...`);
      await page.goto(`${BASE_URL}${pageInfo.path}`, {
        waitUntil: 'networkidle0',
        timeout: 60000
      });
      await sleep(2000); // Wait for data to load

      // Check if we got redirected to login
      const currentUrl = page.url();
      if (currentUrl.includes('/login')) {
        console.log(`    ⚠️  Redirected to login, skipping`);
        continue;
      }

      await page.screenshot({
        path: path.join(OUTPUT_DIR, `${pageInfo.name}.png`),
        fullPage: false,
      });
      console.log(`    ✓ Saved ${pageInfo.name}.png`);
    } catch (error) {
      console.error(`    ✗ Error: ${error.message}`);
    }
  }

  await browser.close();
  console.log('\n✓ Screenshots saved to:', OUTPUT_DIR);
}

captureScreenshots().catch(console.error);
