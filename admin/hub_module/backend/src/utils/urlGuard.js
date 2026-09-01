/**
 * Shared SSRF guard for the AI-knowledge crawler -- JS twin of
 * `hub_api/services/url_guard.py`'s `validate_url`/`guarded_get`. Neither
 * `fetchGitHubMarkdown` nor `fetchSitemapPages` in `aiKnowledgeService.js`
 * had any SSRF protection at all (the Python port gained one in commit
 * 054db298; this module brings the JS crawler to parity).
 *
 * `source_url` is fully user-supplied (`mkdocs`/`docusaurus`/`generic_url`
 * source types) and every `<loc>` entry in its `sitemap.xml` is
 * attacker-controlled content on that same user-supplied origin -- both
 * the sitemap fetch and every per-page fetch must go through
 * `guardedFetch`, never a bare `fetch()`.
 *
 * Security posture (fail closed throughout), matching the Python guard:
 * - Scheme allowlist: `http`/`https` only.
 * - Hostname resolution: every hostname (and literal IP) is checked by
 *   its *resolved* address via `dns.lookup`, not by pattern-matching the
 *   string -- catches a hostname that currently resolves publicly but is
 *   re-pointed at an internal address later (DNS rebind), because the
 *   guard runs immediately before every request and before following
 *   every redirect, not just once.
 * - Disallowed ranges (via `ipaddr.js`'s `.range()` classification,
 *   after unwrapping IPv4-mapped IPv6 addresses like `::ffff:127.0.0.1`
 *   to their IPv4 form first): unspecified, broadcast, multicast,
 *   link-local (including the cloud metadata address 169.254.169.254),
 *   loopback, carrier-grade NAT, RFC1918 private, IPv6 unique-local, and
 *   reserved.
 * - A blocked-hostname list (`localhost`, `metadata.google.internal`)
 *   catches names some resolvers special-case rather than resolving to
 *   a literal loopback/link-local address.
 * - A hostname that fails to resolve at all is treated as disallowed
 *   (fail closed).
 */
import dns from 'node:dns/promises';
import ipaddr from 'ipaddr.js';

/** Only these two schemes are ever fetched -- rejects `file:`/`gopher:`/`ftp:`/etc. */
const ALLOWED_SCHEMES = new Set(['http:', 'https:']);

/** 3xx redirect hops re-validated before following; bounds redirect-loop DNS resolutions. */
const MAX_REDIRECTS = 5;

const REDIRECT_STATUS_CODES = new Set([301, 302, 303, 307, 308]);

/**
 * Never treated as safe outbound targets, even if a naive resolved-IP
 * check would otherwise pass -- some resolvers special-case these names.
 */
const BLOCKED_HOSTNAMES = new Set(['localhost', 'metadata.google.internal']);

/** `ipaddr.js` range classifications that are never a safe crawl target. */
const DISALLOWED_RANGES = new Set([
  'unspecified',
  'broadcast',
  'multicast',
  'linkLocal',
  'loopback',
  'carrierGradeNat',
  'private',
  'uniqueLocal',
  'reserved',
]);

/** A URL/host failed the SSRF guard -- reject at fetch time. */
export class SSRFError extends Error {
  constructor(message) {
    super(message);
    this.name = 'SSRFError';
  }
}

/**
 * Strip the `[...]` brackets the WHATWG URL parser puts around an IPv6
 * literal host (`new URL('http://[::1]/').hostname === '[::1]'`) so the
 * bare address can be handed to `ipaddr.js`/`dns.lookup`.
 * @param {string} host
 * @returns {string}
 */
function stripIpv6Brackets(host) {
  if (host.startsWith('[') && host.endsWith(']')) {
    return host.slice(1, -1);
  }
  return host;
}

/**
 * True if `address` (a literal IP string) is in a disallowed range.
 * Unwraps IPv4-mapped IPv6 addresses to their IPv4 form first, matching
 * Python's `ipaddress` stdlib behavior for `::ffff:127.0.0.1`-style
 * bypass attempts.
 * @param {string} address
 * @returns {boolean}
 */
function isDisallowedAddress(address) {
  let addr;
  try {
    addr = ipaddr.parse(address);
  } catch {
    return true; // unparseable -- fail closed
  }
  if (addr.kind() === 'ipv6' && addr.isIPv4MappedAddress()) {
    addr = addr.toIPv4Address();
  }
  return DISALLOWED_RANGES.has(addr.range());
}

/**
 * True if `host` (a literal IP or a hostname) resolves to a disallowed
 * address. Resolution-aware (via `dns.lookup`), not a regex/string
 * pattern over the hostname -- a hostname pointing at an internal IP is
 * caught even though the hostname itself doesn't look private.
 * @param {string} host
 * @param {{ lookup?: typeof dns.lookup }} [deps] `lookup` is injectable so tests
 *   can supply a fake resolver instead of hitting real DNS (mirrors the
 *   Python guard's `socket.getaddrinfo` monkeypatch tests).
 * @returns {Promise<boolean>}
 */
export async function isPrivateHost(host, { lookup = dns.lookup } = {}) {
  const bare = stripIpv6Brackets(host);
  if (BLOCKED_HOSTNAMES.has(bare.toLowerCase())) {
    return true;
  }
  if (ipaddr.isValid(bare)) {
    return isDisallowedAddress(bare);
  }

  let records;
  try {
    records = await lookup(bare, { all: true, verbatim: true });
  } catch {
    return true; // cannot resolve -- fail closed
  }
  if (records.length === 0) {
    return true;
  }
  return records.some(record => isDisallowedAddress(record.address));
}

/**
 * Throw `SSRFError` unless `urlString` is `http(s)` and its host resolves
 * to a public address. Call before every request and before following
 * every redirect (see `guardedFetch`).
 * @param {string} urlString
 * @param {{ lookup?: typeof dns.lookup }} [deps]
 * @returns {Promise<URL>}
 */
export async function validateUrl(urlString, deps = {}) {
  let parsed;
  try {
    parsed = new URL(urlString);
  } catch {
    throw new SSRFError(`Invalid URL: ${urlString}`);
  }
  if (!ALLOWED_SCHEMES.has(parsed.protocol)) {
    throw new SSRFError(`URL scheme must be http or https, got ${parsed.protocol}`);
  }
  if (!parsed.hostname) {
    throw new SSRFError(`URL has no host: ${urlString}`);
  }
  if (await isPrivateHost(parsed.hostname, deps)) {
    throw new SSRFError(`URL host ${parsed.hostname} resolves to a disallowed address`);
  }
  return parsed;
}

/**
 * `fetchImpl(url, options)` re-validating the SSRF guard before every
 * hop. `fetchImpl`/`lookup` are injected (default to the global `fetch`
 * and `dns.lookup`) so tests can supply stubs instead of hitting the
 * network -- mirrors the Python guard's `client` parameter. Always
 * issues the request with manual redirect handling
 * (`redirect: 'manual'`) -- this function owns the redirect loop so each
 * hop's `Location` can be re-validated before it's fetched.
 * @param {string} url
 * @param {RequestInit} [options]
 * @param {{ fetchImpl?: typeof fetch, lookup?: typeof dns.lookup }} [deps]
 * @returns {Promise<Response>}
 */
export async function guardedFetch(url, options = {}, deps = {}) {
  const { fetchImpl = fetch, lookup } = deps;
  let currentUrl = url;
  for (let hop = 0; hop <= MAX_REDIRECTS; hop += 1) {
    await validateUrl(currentUrl, { lookup });
    const response = await fetchImpl(currentUrl, { ...options, redirect: 'manual' });
    if (!REDIRECT_STATUS_CODES.has(response.status)) {
      return response;
    }
    const location = response.headers.get('location');
    if (!location) {
      return response;
    }
    currentUrl = new URL(location, currentUrl).toString();
  }
  throw new SSRFError(`too many redirects (> ${MAX_REDIRECTS}) starting from ${url}`);
}
