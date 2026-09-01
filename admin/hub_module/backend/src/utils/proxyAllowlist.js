/**
 * Downstream Proxy Allowlist
 *
 * The `/:communityId/{security,analytics}/*` admin routes forward a
 * community admin's request to internal-only services (security-core,
 * analytics-core) by splicing the Express wildcard capture directly into
 * the downstream URL. `requireCommunityAdmin` only proves the caller
 * administers `communityId` — it says nothing about which downstream path
 * they are allowed to reach, so without a second check a community admin
 * (or path-traversal payload such as `../../internal/check`) can reach
 * ANY path on that internal service, including service-to-service-only
 * `/api/v1/internal/*` endpoints that assume the caller is already
 * trusted.
 *
 * `isAllowedProxyPath` is a strict allowlist: only the exact, known-safe
 * community-scoped sub-paths that the admin UI actually calls are
 * permitted, per downstream service + HTTP method. Everything else is
 * rejected before a request is ever made.
 */

// Path tail is everything after `/:communityId/security/` or
// `/:communityId/analytics/` — no leading/trailing slash, already
// URL-decoded by Express. Each pattern matches the full tail exactly.
const ALLOWLIST = {
  analytics: {
    GET: [
      /^status$/,
      /^basic$/,
      /^metrics$/,
      /^poll$/,
      /^config$/,
      /^bot-score$/,
      /^suspected-bots$/,
      /^suspected-bots\/\d+\/review$/,
      /^health-score$/,
      /^bad-actors$/,
      /^retention$/,
    ],
  },
  security: {
    GET: [
      /^config$/,
      /^warnings$/,
      /^moderation-log$/,
      /^filter-matches$/,
      /^blocked-words$/,
    ],
    PUT: [
      /^config$/,
      /^blocked-words\/\d+$/,
    ],
    POST: [
      /^warnings$/,
      /^blocked-words$/,
    ],
    DELETE: [
      /^warnings\/\d+$/,
      /^blocked-words$/,
      /^blocked-words\/\d+$/,
    ],
  },
};

/**
 * Check whether `pathTail` is a permitted downstream path for `service`
 * under the given HTTP `method`. Rejects anything containing traversal
 * segments, a doubled slash, or a scheme/authority marker outright before
 * ever consulting the allowlist — normalization tricks (`..`, `//`, `@`,
 * `:`) must never reach the regex stage.
 */
export function isAllowedProxyPath(service, method, pathTail) {
  if (typeof pathTail !== 'string' || pathTail.length === 0) {
    return false;
  }

  // Reject encoded or literal traversal/host-confusion payloads outright.
  if (/\.\.|\/\/|[@:]/.test(pathTail)) {
    return false;
  }

  const servicePatterns = ALLOWLIST[service];
  if (!servicePatterns) {
    return false;
  }

  const methodPatterns = servicePatterns[method?.toUpperCase()];
  if (!methodPatterns) {
    return false;
  }

  return methodPatterns.some((pattern) => pattern.test(pathTail));
}
