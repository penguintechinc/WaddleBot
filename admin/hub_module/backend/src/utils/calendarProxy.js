/**
 * Calendar Proxy Utility
 * Shared helpers for proxying requests to the calendar-interaction service.
 */
import { config } from '../config/index.js';
import { logger } from '../utils/logger.js';

const CALENDAR_API_URL = process.env.CALENDAR_API_URL || 'http://calendar-interaction:8038';

/**
 * Proxy a request to the calendar module.
 * @param {string} path - API path (e.g. /api/v1/calendar/...)
 * @param {object} options - fetch options (method, body, headers, etc.)
 * @returns {Promise<object>} parsed JSON response
 */
export async function proxyToCalendar(path, options = {}) {
  try {
    const url = `${CALENDAR_API_URL}${path}`;
    const controller = new AbortController();
    const timeoutMs = parseInt(process.env.CALENDAR_PROXY_TIMEOUT_MS || '5000', 10);
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    let response;
    try {
      response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': config.serviceApiKey,
          ...options.headers,
        },
      });
    } finally {
      clearTimeout(timeoutId);
    }

    const data = await response.json();

    if (!response.ok) {
      const error = new Error(data.error || data.message || 'Calendar module request failed');
      error.status = response.status;
      throw error;
    }

    return data;
  } catch (err) {
    logger.error('Calendar module proxy error', {
      path,
      error: err.message,
    });
    throw err;
  }
}

/**
 * Build X-User-Context header from the Express request.
 * Handles unauthenticated (public booking) requests gracefully.
 */
export function buildUserContext(req) {
  return JSON.stringify({
    user_id: req.user?.id || null,
    username: req.user?.username || null,
    platform: 'hub',
    platform_user_id: String(req.user?.id || 'anonymous'),
    role: req.user?.isSuperAdmin ? 'super_admin' : (req.user ? 'admin' : 'anonymous'),
  });
}
