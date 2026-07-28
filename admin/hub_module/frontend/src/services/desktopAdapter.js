/**
 * Desktop mode adapter — routes API calls through Tauri when in desktop context
 * Detects Tauri at runtime and provides a transport abstraction for both browser and desktop paths
 * Browser: axios + localStorage (unchanged)
 * Desktop: Tauri invoke('api_request') + keychain (token never in JS)
 */

/**
 * Get Tauri invoke function — uses global Tauri API available in webview
 * The desktop app injects __TAURI__ when loading the webui
 */
function getInvoke() {
  // Tauri v2 makes invoke available on window.__TAURI__
  if (typeof window !== 'undefined' && window.__TAURI__?.invoke) {
    return window.__TAURI__.invoke;
  }

  // Fallback: check internal API
  if (typeof window !== 'undefined' && window.__TAURI_INTERNALS__?.commands?.invoke) {
    return window.__TAURI_INTERNALS__.commands.invoke;
  }

  throw new Error('Tauri invoke not available — not running in Tauri desktop context');
}

/**
 * Detect if running inside Tauri webview
 * Check for __TAURI__ globals injected by Tauri v2
 */
export function isDesktopMode() {
  if (typeof window === 'undefined') return false;
  // Check for Tauri globals that indicate we're in the Tauri webview
  return !!(
    window.__TAURI__ ||
    window.__TAURI_INTERNALS__ ||
    window.__TAURI_METADATA__
  );
}

/**
 * Desktop transport adapter — replaces axios for desktop mode
 * Calls Tauri's api_request command (Rust-proxied, token injected server-side)
 */
export async function desktopRequest(config) {
  if (!isDesktopMode()) {
    throw new Error('desktopRequest called outside desktop mode');
  }

  const invoke = getInvoke();
  const method = config.method?.toUpperCase() || 'GET';
  const path = config.url || '';
  const body = config.data ? JSON.stringify(config.data) : null;

  console.log(`[desktopAdapter] ${method} ${path}`);

  try {
    const response = await invoke('api_request', {
      method,
      path,
      body
    });

    // Response: { status, body }
    return {
      data: response.body ? JSON.parse(response.body) : null,
      status: response.status,
      statusText: response.status < 400 ? 'OK' : 'Error',
      headers: {},
      config,
      request: {}
    };
  } catch (err) {
    console.error(`[desktopAdapter] Error: ${err}`);
    const error = new Error(err);
    error.response = {
      status: 0,
      data: { error: err },
      statusText: 'Transport Error'
    };
    throw error;
  }
}

/**
 * Desktop auth adapter — Tauri commands for token storage + login/logout
 * Token stored in OS keychain; login/logout via Tauri commands
 */
export async function desktopLogin(email, password) {
  const invoke = getInvoke();

  console.log('[desktopAdapter] login');
  try {
    const response = await invoke('login', { email, password });
    // Rust returns { email, role, success }; token is in keychain
    return {
      success: response.success,
      email: response.email,
      role: response.role,
      user: {
        email: response.email,
        roles: response.role ? [response.role] : ['user']
      }
    };
  } catch (err) {
    console.error(`[desktopAdapter] login error: ${err}`);
    throw new Error(err);
  }
}

export async function desktopLogout() {
  const invoke = getInvoke();

  console.log('[desktopAdapter] logout');
  try {
    await invoke('logout');
  } catch (err) {
    console.error(`[desktopAdapter] logout error: ${err}`);
    // Non-fatal: proceed with logout even if keychain clear fails
  }
}

export async function desktopGetToken() {
  const invoke = getInvoke();

  try {
    return await invoke('get_token');
  } catch (err) {
    console.error(`[desktopAdapter] get_token error: ${err}`);
    return null;
  }
}

export async function desktopGetCurrentUser() {
  const invoke = getInvoke();

  console.log('[desktopAdapter] fetching current user');
  try {
    const response = await invoke('api_request', {
      method: 'GET',
      path: '/api/v1/auth/me',
      body: null
    });

    const userData = response.body ? JSON.parse(response.body) : null;
    return userData?.user || userData;
  } catch (err) {
    console.error(`[desktopAdapter] get current user error: ${err}`);
    return null;
  }
}
