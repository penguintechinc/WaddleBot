/**
 * Browser-SPA session cookie -- security.md C4 fix (OWASP A07).
 *
 * The session JWT used to be handed to the frontend only in the response
 * body (or, for the OAuth callback, directly in the redirect URL query
 * string), which the SPA persisted client-side. A query-string token leaks
 * into proxy/access logs, browser history, and the `Referer` header of any
 * outbound request the callback page happens to make -- no XSS required.
 *
 * This mirrors hub_api's `services/session_cookie.py` (PR #227/#258) so the
 * two backends set/clear the exact same `wb_session` cookie the frontend
 * already expects (`admin/hub_module/frontend/src/services/api.js` sends
 * it automatically via `withCredentials: true`).
 */

/** HttpOnly cookie carrying the session JWT for the browser SPA. */
export const SESSION_COOKIE_NAME = 'wb_session';

/**
 * Set the HttpOnly session cookie on `res`, carrying `token`.
 *
 * `SameSite=Lax` is the CSRF mitigation: a cross-site page cannot trigger an
 * authenticated state-changing request because the browser omits a Lax
 * cookie on cross-site subrequests (fetch/XHR/form-POST) -- the forged
 * request arrives with no session and is rejected by the normal 401/403
 * path. Lax (not Strict) is required so the cookie survives the OAuth
 * provider's redirect back to our own origin.
 */
export function setSessionCookie(res, token, { maxAgeMs } = {}) {
  res.cookie(SESSION_COOKIE_NAME, token, {
    maxAge: maxAgeMs ?? 24 * 60 * 60 * 1000,
    path: '/',
    secure: true,
    httpOnly: true,
    sameSite: 'lax',
  });
}

/** Clear the session cookie on `res` -- logout. */
export function clearSessionCookie(res) {
  res.clearCookie(SESSION_COOKIE_NAME, { path: '/' });
}
