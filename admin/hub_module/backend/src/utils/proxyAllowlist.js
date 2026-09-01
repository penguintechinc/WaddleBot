/**
 * Downstream Proxy Allowlist
 *
 * The `/:communityId/{security,analytics}/*` admin routes forward a
 * community admin's request to internal-only services (security-core,
 * analytics-core) by splicing the Express wildcard capture directly into
 * the downstream URL. `requireCommunityAdmin` only proves the caller
 * administers `communityId` — it says nothing about which downstream path
 * they are allowed to reach, so without a second check a community admin
 * (or a path-traversal payload such as `../../internal/check`) can reach
 * ANY path on that internal service, including service-to-service-only
 * `/api/v1/internal/*` endpoints that assume the caller is already
 * trusted.
 *
 * Each exported pattern is a single, fully-anchored (`^...$`) allowlist
 * regex covering the exact, known-safe community-scoped sub-paths the
 * admin UI actually calls for that downstream service + HTTP method.
 * Callers must run `PATTERN.test(pathTail)` directly against the raw
 * Express wildcard capture — inline, in the same function as the
 * downstream request — before proxying; anything that doesn't match is
 * rejected with 403. Being fully anchored, none of these patterns can
 * ever match a traversal segment (`..`), a doubled slash, or a
 * scheme/authority marker (`@`, `:`): the allowlist is closed by
 * construction rather than relying on a separate blocklist check.
 */

export const ANALYTICS_GET_PATH =
  /^(status|basic|metrics|poll|config|bot-score|suspected-bots|suspected-bots\/\d+\/review|health-score|bad-actors|retention)$/;

export const SECURITY_GET_PATH = /^(config|warnings|moderation-log|filter-matches|blocked-words)$/;
export const SECURITY_PUT_PATH = /^(config|blocked-words\/\d+)$/;
export const SECURITY_POST_PATH = /^(warnings|blocked-words)$/;
export const SECURITY_DELETE_PATH = /^(warnings\/\d+|blocked-words|blocked-words\/\d+)$/;

const ALLOWLIST = {
  analytics: { GET: ANALYTICS_GET_PATH },
  security: {
    GET: SECURITY_GET_PATH,
    PUT: SECURITY_PUT_PATH,
    POST: SECURITY_POST_PATH,
    DELETE: SECURITY_DELETE_PATH,
  },
};

/**
 * Convenience wrapper over the exported patterns, for callers that don't
 * need the CodeQL-visible inline `.test()` idiom (e.g. tests). The live
 * route handlers in routes/admin.js call `PATTERN.test(pathTail)` inline
 * instead of through this function — see the module doc comment above.
 */
export function isAllowedProxyPath(service, method, pathTail) {
  if (typeof pathTail !== 'string' || pathTail.length === 0) {
    return false;
  }

  const pattern = ALLOWLIST[service]?.[method?.toUpperCase()];
  if (!pattern) {
    return false;
  }

  return pattern.test(pathTail);
}
