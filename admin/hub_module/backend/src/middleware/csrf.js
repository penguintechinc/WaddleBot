/**
 * CSRF Protection Middleware
 * Implements Double Submit Cookie pattern for CSRF protection
 */
import crypto from 'crypto';
import { logger } from '../utils/logger.js';

const CSRF_TOKEN_LENGTH = 32;
const CSRF_COOKIE_NAME = 'XSRF-TOKEN';
const CSRF_HEADER_NAME = 'X-XSRF-TOKEN';

/**
 * Generate a cryptographically secure CSRF token
 * @returns {string} CSRF token
 */
function generateCsrfToken() {
  return crypto.randomBytes(CSRF_TOKEN_LENGTH).toString('hex');
}

/**
 * Middleware to generate and set CSRF token cookie
 * This should be applied to routes that serve HTML forms
 */
export function setCsrfToken(req, res, next) {
  // Skip if CSRF token already exists in cookie
  if (req.cookies && req.cookies[CSRF_COOKIE_NAME]) {
    return next();
  }

  // Generate new CSRF token
  const csrfToken = generateCsrfToken();

  // Set CSRF token in cookie (httpOnly: false so JavaScript can read it)
  res.cookie(CSRF_COOKIE_NAME, csrfToken, {
    httpOnly: false, // JavaScript needs to read this
    secure: process.env.NODE_ENV === 'production', // HTTPS only in production
    sameSite: 'strict',
    maxAge: 3600000, // 1 hour
  });

  next();
}

/**
 * Middleware to verify CSRF token on state-changing requests
 * Should be applied to POST, PUT, PATCH, DELETE routes
 */
// Paths exempt from CSRF verification — pre-authentication endpoints where no
// session exists yet to forge (login CSRF is low-risk: attacker still needs
// victim's credentials, and most auth libs don't send CSRF headers on login).
const CSRF_EXEMPT_PATHS = [
  '/api/v1/auth/login',
  '/api/v1/auth/register',
  '/api/v1/auth/passkey/login/start',
  '/api/v1/auth/passkey/login/finish',
];

export function verifyCsrfToken(req, res, next) {
  // Skip CSRF check for GET, HEAD, OPTIONS requests
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) {
    return next();
  }

  // Skip CSRF check for pre-authentication endpoints (no session to forge)
  if (CSRF_EXEMPT_PATHS.includes(req.path)) {
    return next();
  }

  // Skip CSRF check for API endpoints using Bearer token authentication
  // (CSRF is not needed for bearer token APIs)
  const authHeader = req.headers.authorization;
  if (authHeader && authHeader.startsWith('Bearer ')) {
    return next();
  }

  // Skip CSRF check for service-to-service requests
  if (req.headers['x-service-key']) {
    return next();
  }

  // Get CSRF token from cookie
  const cookieToken = req.cookies ? req.cookies[CSRF_COOKIE_NAME] : null;

  // Get CSRF token from header or body
  const requestToken = req.headers[CSRF_HEADER_NAME.toLowerCase()] || req.body?._csrf;

  // Validate tokens exist
  if (!cookieToken || !requestToken) {
    logger.authz('CSRF validation failed: Missing token', {
      user: req.user?.id || 'anonymous',
      method: req.method,
      path: req.path,
      result: 'FAILURE',
    });

    return res.status(403).json({
      success: false,
      error: {
        code: 'CSRF_ERROR',
        message: 'CSRF token missing or invalid',
      },
    });
  }

  // Use constant-time comparison to prevent timing attacks
  const tokensMatch = crypto.timingSafeEqual(
    Buffer.from(cookieToken),
    Buffer.from(requestToken)
  );

  if (!tokensMatch) {
    logger.authz('CSRF validation failed: Token mismatch', {
      user: req.user?.id || 'anonymous',
      method: req.method,
      path: req.path,
      result: 'FAILURE',
    });

    return res.status(403).json({
      success: false,
      error: {
        code: 'CSRF_ERROR',
        message: 'CSRF token mismatch',
      },
    });
  }

  // CSRF token is valid
  next();
}

/**
 * Middleware to refresh CSRF token after successful authentication
 * Call this after login/register to prevent CSRF token fixation
 */
export function refreshCsrfToken(req, res, next) {
  const newToken = generateCsrfToken();

  res.cookie(CSRF_COOKIE_NAME, newToken, {
    httpOnly: false,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 3600000,
  });

  logger.system('CSRF token refreshed', {
    user: req.user?.id || 'anonymous',
  });

  next();
}

/**
 * Helper function to get CSRF token from request
 * Useful for including in API responses
 */
export function getCsrfToken(req) {
  return req.cookies ? req.cookies[CSRF_COOKIE_NAME] : null;
}

export default {
  setCsrfToken,
  verifyCsrfToken,
  refreshCsrfToken,
  getCsrfToken,
  CSRF_HEADER_NAME,
  CSRF_COOKIE_NAME,
};
