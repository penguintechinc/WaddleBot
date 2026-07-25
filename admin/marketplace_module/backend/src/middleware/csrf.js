/**
 * CSRF protection for cookie-authenticated browser requests.
 *
 * Uses the cookie-to-header double-submit pattern, validates the browser
 * Origin/Referer against the configured CORS origins, and rejects cross-site
 * Fetch Metadata. Requests authenticated with an explicit Bearer token or
 * service key are not vulnerable to CSRF because browsers cannot attach those
 * credentials without triggering CORS.
 */
import crypto from 'crypto';

import { config } from '../config/index.js';
import { logger } from '../utils/logger.js';

export const CSRF_COOKIE_NAME = 'XSRF-TOKEN';
export const CSRF_HEADER_NAME = 'X-XSRF-TOKEN';

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);
const WEBHOOK_PREFIX = '/api/v1/webhooks/';
const TOKEN_BYTES = 32;
const TOKEN_MAX_AGE_MS = 60 * 60 * 1000;

function configuredOrigins() {
  return String(config.cors.origin)
    .split(',')
    .map((origin) => origin.trim())
    .filter(Boolean);
}

function sourceOrigin(req) {
  const origin = req.get('origin');
  if (origin) {
    return origin;
  }

  const referer = req.get('referer');
  if (!referer) {
    return null;
  }

  try {
    return new URL(referer).origin;
  } catch {
    return null;
  }
}

function isAllowedOrigin(req) {
  const origin = sourceOrigin(req);
  if (!origin) {
    return false;
  }

  return configuredOrigins().includes(origin);
}

function verifyCsrfTokens(cookieToken, requestToken) {
  if (typeof cookieToken !== 'string' || typeof requestToken !== 'string') {
    return false;
  }

  const cookieBuffer = Buffer.from(cookieToken);
  const requestBuffer = Buffer.from(requestToken);
  return cookieBuffer.length === requestBuffer.length
    && crypto.timingSafeEqual(cookieBuffer, requestBuffer);
}

function rejectCsrf(req, res, reason) {
  logger.authz('CSRF validation failed', {
    method: req.method,
    path: req.path,
    reason,
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

/**
 * Ensure browser clients have a readable token to echo in X-XSRF-TOKEN.
 */
export function setCsrfToken(req, res, next) {
  if (!req.cookies?.[CSRF_COOKIE_NAME]) {
    res.cookie(
      CSRF_COOKIE_NAME,
      crypto.randomBytes(TOKEN_BYTES).toString('hex'),
      {
        httpOnly: false,
        maxAge: TOKEN_MAX_AGE_MS,
        path: '/',
        sameSite: 'strict',
        secure: config.env === 'production',
      },
    );
  }

  next();
}

/**
 * Validate state-changing requests that rely on the ambient JWT cookie.
 */
export function verifyCsrfToken(req, res, next) {
  if (SAFE_METHODS.has(req.method)) {
    return next();
  }

  const authorization = req.get('authorization');
  if (authorization?.startsWith('Bearer ')) {
    return next();
  }

  if (req.get('x-api-key') || req.get('x-service-key')) {
    return next();
  }

  if (req.path.startsWith(WEBHOOK_PREFIX)) {
    return next();
  }

  // Without an authentication cookie there are no ambient credentials for a
  // cross-site request to exploit. Authentication/authorization middleware
  // remains responsible for rejecting unauthenticated operations.
  if (!req.cookies?.token) {
    return next();
  }

  if (req.get('sec-fetch-site') === 'cross-site') {
    return rejectCsrf(req, res, 'cross-site request');
  }

  if (!isAllowedOrigin(req)) {
    return rejectCsrf(req, res, 'untrusted or missing origin');
  }

  const cookieToken = req.cookies[CSRF_COOKIE_NAME];
  const requestToken = req.get(CSRF_HEADER_NAME);
  if (!verifyCsrfTokens(cookieToken, requestToken)) {
    return rejectCsrf(req, res, 'token mismatch');
  }

  return next();
}

export default {
  setCsrfToken,
  verifyCsrfToken,
};
