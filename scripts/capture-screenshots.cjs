const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const BASE_URL = 'http://localhost:8060';
const OUTPUT_DIR = path.join(__dirname, '..', 'docs', 'screenshots');

// Waddles Hub pages to capture
// Note: Community ID 2 is the first real community (ID 1 may not exist)
const COMMUNITY_ID = 2;
const TENANT_SLUG = 'default';

// tier: 'premium' pages are gated behind isPremium checks or premium: true sidebar flags
// tier: 'freemium' pages are available to all users
const pages = [
  // ── Public / Auth ──────────────────────────────────────────────────
  { name: 'home', path: '/', tier: 'freemium' },
  { name: 'login', path: '/login', tier: 'freemium' },
  { name: 'communities', path: '/communities', tier: 'freemium' },
  { name: 'live-streams', path: '/live', tier: 'freemium' },
  { name: 'cookie-policy', path: '/cookie-policy', tier: 'freemium' },

  // ── Dashboard ──────────────────────────────────────────────────────
  { name: 'dashboard', path: '/dashboard', tier: 'freemium' },
  { name: 'dashboard-settings', path: '/dashboard/settings', tier: 'freemium' },
  { name: 'dashboard-profile', path: '/dashboard/profile', tier: 'freemium' },
  { name: 'dashboard-my-channels', path: '/dashboard/my-channels', tier: 'freemium' },
  { name: 'dashboard-personal-access-token', path: '/account/tokens', tier: 'freemium' },
  { name: 'communities-create', path: '/communities/create', tier: 'freemium' },

  // ── Calendar / Booking ─────────────────────────────────────────────
  { name: 'calendar-settings', path: '/calendar/settings', tier: 'freemium' },
  { name: 'calendar-booking-pages', path: '/calendar/booking-pages', tier: 'freemium' },
  { name: 'calendar-my-bookings', path: '/calendar/my-bookings', tier: 'freemium' },

  // ── Vendor ─────────────────────────────────────────────────────────
  { name: 'vendor-submit', path: '/vendor/submit', tier: 'freemium' },
  { name: 'vendor-submission-status', path: '/vendor/submission-status', tier: 'freemium' },
  { name: 'vendor-dashboard', path: '/vendor/dashboard', tier: 'freemium' },
  { name: 'vendor-request', path: '/vendor/request', tier: 'freemium' },

  // ── Community Member ───────────────────────────────────────────────
  { name: 'community-dashboard', path: `/dashboard/community/${COMMUNITY_ID}`, tier: 'freemium' },
  { name: 'community-settings', path: `/dashboard/community/${COMMUNITY_ID}/settings`, tier: 'freemium' },
  { name: 'community-chat', path: `/dashboard/community/${COMMUNITY_ID}/chat`, tier: 'freemium' },
  { name: 'community-leaderboard', path: `/dashboard/community/${COMMUNITY_ID}/leaderboard`, tier: 'freemium' },
  { name: 'community-members', path: `/dashboard/community/${COMMUNITY_ID}/members`, tier: 'freemium' },
  { name: 'community-support-submit', path: `/community/${COMMUNITY_ID}/support/submit`, tier: 'freemium' },
  { name: 'community-support-my-tickets', path: `/community/${COMMUNITY_ID}/support/my-tickets`, tier: 'freemium' },
  { name: 'community-game-servers', path: `/community/${COMMUNITY_ID}/game-servers`, tier: 'freemium' },
  { name: 'community-interaction', path: `/community/${COMMUNITY_ID}/interact`, tier: 'freemium' },
  { name: 'community-inventory-browse', path: `/community/${COMMUNITY_ID}/inventory`, tier: 'freemium' },
  { name: 'community-inventory-my-items', path: `/community/${COMMUNITY_ID}/inventory/my-items`, tier: 'freemium' },

  // ── Admin Core ─────────────────────────────────────────────────────
  { name: 'admin-overview', path: `/admin/${COMMUNITY_ID}`, tier: 'freemium' },
  { name: 'admin-members', path: `/admin/${COMMUNITY_ID}/members`, tier: 'freemium' },
  { name: 'admin-modules', path: `/admin/${COMMUNITY_ID}/modules`, tier: 'freemium' },
  { name: 'admin-stream-overlays', path: `/admin/${COMMUNITY_ID}/stream-overlays`, tier: 'freemium' },
  { name: 'admin-domains', path: `/admin/${COMMUNITY_ID}/domains`, tier: 'freemium' },
  { name: 'admin-servers', path: `/admin/${COMMUNITY_ID}/servers`, tier: 'freemium' },
  { name: 'admin-connected-platforms', path: `/admin/${COMMUNITY_ID}/connected-platforms`, tier: 'freemium' },
  { name: 'admin-mirror-groups', path: `/admin/${COMMUNITY_ID}/mirror-groups`, tier: 'freemium' },
  { name: 'admin-leaderboard-config', path: `/admin/${COMMUNITY_ID}/leaderboard`, tier: 'freemium' },
  { name: 'admin-community-profile', path: `/admin/${COMMUNITY_ID}/profile`, tier: 'freemium' },
  { name: 'admin-reputation', path: `/admin/${COMMUNITY_ID}/reputation`, tier: 'freemium' },
  { name: 'admin-announcements', path: `/admin/${COMMUNITY_ID}/announcements`, tier: 'freemium' },
  { name: 'admin-analytics', path: `/admin/${COMMUNITY_ID}/analytics`, tier: 'freemium' },
  { name: 'admin-security', path: `/admin/${COMMUNITY_ID}/security`, tier: 'freemium' },
  { name: 'admin-roles', path: `/admin/${COMMUNITY_ID}/roles`, tier: 'freemium' },
  { name: 'admin-platform-settings', path: `/admin/${COMMUNITY_ID}/platform-settings`, tier: 'freemium' },

  // ── Admin Content & Engagement ─────────────────────────────────────
  { name: 'admin-shoutouts', path: `/admin/${COMMUNITY_ID}/shoutouts`, tier: 'freemium' },
  { name: 'admin-translation', path: `/admin/${COMMUNITY_ID}/translation`, tier: 'freemium' },
  { name: 'admin-live-streaming', path: `/admin/${COMMUNITY_ID}/live-streaming`, tier: 'freemium' },
  { name: 'admin-calls', path: `/admin/${COMMUNITY_ID}/calls`, tier: 'freemium' },
  { name: 'admin-polls', path: `/admin/${COMMUNITY_ID}/polls`, tier: 'freemium' },
  { name: 'admin-forms', path: `/admin/${COMMUNITY_ID}/forms`, tier: 'freemium' },
  { name: 'admin-commands', path: `/admin/${COMMUNITY_ID}/commands`, tier: 'freemium' },

  // ── Admin AI ───────────────────────────────────────────────────────
  { name: 'admin-ai-insights', path: `/admin/${COMMUNITY_ID}/ai-insights`, tier: 'freemium' },
  { name: 'admin-ai-config', path: `/admin/${COMMUNITY_ID}/ai-config`, tier: 'premium' },

  // ── Admin Module Configs ───────────────────────────────────────────
  { name: 'admin-module-lfg-config', path: `/admin/${COMMUNITY_ID}/modules/lfg/config`, tier: 'freemium' },
  { name: 'admin-module-clip-config', path: `/admin/${COMMUNITY_ID}/modules/clip/config`, tier: 'freemium' },
  { name: 'admin-module-alias-config', path: `/admin/${COMMUNITY_ID}/modules/alias/config`, tier: 'freemium' },
  { name: 'admin-module-memories-config', path: `/admin/${COMMUNITY_ID}/modules/memories/config`, tier: 'freemium' },
  { name: 'admin-module-server-status-config', path: `/admin/${COMMUNITY_ID}/modules/server-status/config`, tier: 'freemium' },
  { name: 'admin-module-server-manager-config', path: `/admin/${COMMUNITY_ID}/modules/server-manager/config`, tier: 'freemium' },

  // ── Admin Loyalty ──────────────────────────────────────────────────
  { name: 'admin-loyalty', path: `/admin/${COMMUNITY_ID}/loyalty`, tier: 'freemium' },
  { name: 'admin-loyalty-leaderboard', path: `/admin/${COMMUNITY_ID}/loyalty/leaderboard`, tier: 'freemium' },
  { name: 'admin-loyalty-giveaways', path: `/admin/${COMMUNITY_ID}/loyalty/giveaways`, tier: 'freemium' },
  { name: 'admin-loyalty-games', path: `/admin/${COMMUNITY_ID}/loyalty/games`, tier: 'freemium' },
  { name: 'admin-loyalty-gear', path: `/admin/${COMMUNITY_ID}/loyalty/gear`, tier: 'freemium' },

  // ── Admin Music ────────────────────────────────────────────────────
  { name: 'admin-music', path: `/admin/${COMMUNITY_ID}/music`, tier: 'freemium' },
  { name: 'admin-music-settings', path: `/admin/${COMMUNITY_ID}/music/settings`, tier: 'freemium' },
  { name: 'admin-music-providers', path: `/admin/${COMMUNITY_ID}/music/providers`, tier: 'freemium' },
  { name: 'admin-music-radio', path: `/admin/${COMMUNITY_ID}/music/radio`, tier: 'freemium' },

  // ── Admin Calendar ─────────────────────────────────────────────────
  { name: 'admin-calendar-events', path: `/admin/${COMMUNITY_ID}/calendar/events`, tier: 'freemium' },

  // ── Admin Support & Operations ─────────────────────────────────────
  { name: 'admin-support', path: `/admin/${COMMUNITY_ID}/support`, tier: 'freemium' },
  { name: 'admin-join-requests', path: `/admin/${COMMUNITY_ID}/join-requests`, tier: 'freemium' },
  { name: 'admin-inventory', path: `/admin/${COMMUNITY_ID}/inventory`, tier: 'freemium' },
  { name: 'admin-tokens', path: `/admin/${COMMUNITY_ID}/tokens`, tier: 'freemium' },
  { name: 'admin-interaction-channels', path: `/admin/${COMMUNITY_ID}/interaction-channels`, tier: 'freemium' },
  { name: 'admin-rcon', path: `/admin/${COMMUNITY_ID}/rcon`, tier: 'premium' },

  // ── Admin Premium-Only ─────────────────────────────────────────────
  { name: 'admin-bot-detection', path: `/admin/${COMMUNITY_ID}/bot-detection`, tier: 'premium' },
  { name: 'admin-workflows', path: `/admin/${COMMUNITY_ID}/workflows`, tier: 'premium' },

  // ── Platform Admin ─────────────────────────────────────────────────
  { name: 'platform-dashboard', path: '/platform', tier: 'freemium' },
  { name: 'platform-users', path: '/platform/users', tier: 'freemium' },
  { name: 'platform-communities', path: '/platform/communities', tier: 'freemium' },

  // ── Super Admin ────────────────────────────────────────────────────
  { name: 'superadmin-dashboard', path: '/superadmin', tier: 'freemium' },
  { name: 'superadmin-communities', path: '/superadmin/communities', tier: 'freemium' },
  { name: 'superadmin-create-community', path: '/superadmin/communities/new', tier: 'freemium' },
  { name: 'superadmin-modules', path: '/superadmin/modules', tier: 'freemium' },
  { name: 'superadmin-vendor-submissions', path: '/superadmin/vendor-submissions', tier: 'freemium' },
  { name: 'superadmin-vendor-requests', path: '/superadmin/vendor-requests', tier: 'freemium' },
  { name: 'superadmin-users', path: '/superadmin/users', tier: 'freemium' },
  { name: 'superadmin-platform-config', path: '/superadmin/platform-config', tier: 'freemium' },
  { name: 'superadmin-kong', path: '/superadmin/kong', tier: 'freemium' },
  { name: 'superadmin-software-discovery', path: '/superadmin/software-discovery', tier: 'freemium' },
  { name: 'superadmin-services', path: '/superadmin/services', tier: 'freemium' },
  { name: 'superadmin-analytics', path: '/superadmin/analytics', tier: 'freemium' },
  { name: 'superadmin-tenants', path: '/superadmin/tenants', tier: 'freemium' },

  // ── Tenant Admin ───────────────────────────────────────────────────
  { name: 'tenant-dashboard', path: `/tenant/${TENANT_SLUG}`, tier: 'freemium' },
  { name: 'tenant-modules', path: `/tenant/${TENANT_SLUG}/modules`, tier: 'freemium' },
  { name: 'tenant-admins', path: `/tenant/${TENANT_SLUG}/admins`, tier: 'freemium' },
  { name: 'tenant-communities', path: `/tenant/${TENANT_SLUG}/communities`, tier: 'freemium' },
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
  const loginEntry = pages.find(p => p.name === 'login');
  const loginFilename = `${loginEntry.tier}-login.png`;
  if (!loginSuccess) {
    console.log('\nCapturing login page...');
    try {
      await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await sleep(1000);
      await page.screenshot({ path: path.join(OUTPUT_DIR, loginFilename) });
      console.log(`  ✓ Saved ${loginFilename}`);
    } catch (error) {
      console.error('  ✗ Error capturing login:', error.message);
    }
    console.log('\n⚠️  Could not log in, will capture public pages only');
  } else {
    console.log('\n✓ Successfully authenticated, capturing authenticated pages...');
  }

  // Capture all pages
  console.log(`\nCapturing ${pages.length} pages...`);
  let captured = 0;
  let skipped = 0;
  let errors = 0;
  for (const pageInfo of pages) {
    if (pageInfo.name === 'login') continue;

    const filename = `${pageInfo.tier}-${pageInfo.name}.png`;
    try {
      console.log(`  [${pageInfo.tier}] ${pageInfo.name}...`);
      await page.goto(`${BASE_URL}${pageInfo.path}`, {
        waitUntil: 'networkidle0',
        timeout: 60000
      });
      await sleep(2000); // Wait for data to load

      // Check if we got redirected to login
      const currentUrl = page.url();
      if (currentUrl.includes('/login')) {
        console.log(`    ⚠️  Redirected to login, skipping`);
        skipped++;
        continue;
      }

      await page.screenshot({
        path: path.join(OUTPUT_DIR, filename),
        fullPage: false,
      });
      console.log(`    ✓ Saved ${filename}`);
      captured++;
    } catch (error) {
      console.error(`    ✗ Error: ${error.message}`);
      errors++;
    }
  }

  await browser.close();
  const premiumCount = pages.filter(p => p.tier === 'premium').length;
  const freemiumCount = pages.filter(p => p.tier === 'freemium').length;
  console.log(`\n✓ Done! ${captured} captured, ${skipped} skipped, ${errors} errors`);
  console.log(`  Total pages: ${pages.length} (${freemiumCount} freemium, ${premiumCount} premium)`);
  console.log('  Screenshots saved to:', OUTPUT_DIR);
}

captureScreenshots().catch(console.error);
