/**
 * Regression guard: the security/analytics proxy routes in admin.js must
 * gate on the shared allowlist pattern — via a direct, inline
 * `PATTERN.test(pathTail)` call on the raw Express wildcard capture, in
 * the same function as the downstream request — before ever building the
 * proxied URL.
 *
 * The inline-`.test()`-on-the-tainted-variable shape matters: CodeQL's
 * js/request-forgery query recognizes a direct `regex.test(taintedVar)`
 * (or `array.includes(taintedVar)`) guard in the same function as a
 * sanitizing barrier, but does NOT reliably recognize a boolean returned
 * from a call to a separately-defined helper function as one. An earlier
 * version of this fix called `isAllowedProxyPath(...)` from
 * utils/proxyAllowlist.js and left all 5 of these CodeQL alerts open even
 * though the runtime behavior was already correct — this test pins the
 * shape that actually clears them.
 *
 * This intentionally reads admin.js as source text rather than importing
 * the module. admin.js pulls in ~30 controllers that each import
 * config/database.js, which opens a real pg Pool and an un-refed
 * setInterval — importing it here would leave the test runner unable to
 * exit cleanly. Reading the file avoids that entirely while still proving
 * the fix is wired into the route handlers (not just present in
 * proxyAllowlist.js and unused).
 *
 * Run with the repo's configured runner: `npm test` (node --test).
 */
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(__dirname, 'admin.js'), 'utf8');

/** Pull the body of a route handler registered with `router.<method>(path, ...)`. */
function extractHandler(routerMethod, path) {
  const marker = `router.${routerMethod}('${path}'`;
  const start = source.indexOf(marker);
  assert.ok(start !== -1, `route not found: ${routerMethod.toUpperCase()} ${path}`);
  // Grab up to the next top-level `router.` registration (or EOF) so we
  // only inspect this handler's body.
  const nextRouterCall = source.indexOf('\nrouter.', start + marker.length);
  return source.slice(start, nextRouterCall === -1 ? source.length : nextRouterCall);
}

describe('admin.js proxy routes are gated by an inline allowlist regex test', () => {
  it('imports the shared allowlist patterns', () => {
    assert.match(source, /import\s*\{[^}]*ANALYTICS_GET_PATH[^}]*\}\s*from\s*'\.\.\/utils\/proxyAllowlist\.js'/s);
  });

  const cases = [
    ['get', '/:communityId/analytics/*', 'ANALYTICS_GET_PATH', 'analyticsPath'],
    ['get', '/:communityId/security/*', 'SECURITY_GET_PATH', 'securityPath'],
    ['put', '/:communityId/security/*', 'SECURITY_PUT_PATH', 'securityPath'],
    ['post', '/:communityId/security/*', 'SECURITY_POST_PATH', 'securityPath'],
    ['delete', '/:communityId/security/*', 'SECURITY_DELETE_PATH', 'securityPath'],
  ];

  for (const [routerMethod, path, patternName, pathVar] of cases) {
    it(`${routerMethod.toUpperCase()} ${path} rejects a disallowed path before proxying`, () => {
      // security registers 4 handlers (get/put/post/delete) on the same
      // path — the routerMethod in the marker disambiguates which one.
      const handler = extractHandler(routerMethod, path);

      // Must be a direct `PATTERN.test(pathVar)` call — not routed through
      // an intermediate helper function — so CodeQL's local barrier-guard
      // analysis sees the tainted variable gated in this same function.
      assert.match(
        handler,
        new RegExp(`if\\s*\\(\\s*!${patternName}\\.test\\(${pathVar}\\)\\s*\\)`),
        `handler must inline-guard with if (!${patternName}.test(${pathVar}))`
      );

      const guardIndex = handler.search(new RegExp(`if\\s*\\(\\s*!${patternName}\\.test`));
      const axiosCallIndex = handler.search(/httpClient\.(get|put|post|delete)\(/);
      assert.ok(guardIndex !== -1, 'no rejection guard found');
      assert.ok(axiosCallIndex !== -1, 'no downstream axios call found');
      assert.ok(guardIndex < axiosCallIndex, 'guard must run before the downstream request is made');

      assert.match(handler, /res\.status\(403\)/, 'disallowed paths must be rejected with 403');
    });
  }
});

describe('admin.js proxy routes also guard communityId before proxying', () => {
  // CodeQL's js/request-forgery query flagged req.params.communityId as a
  // SECOND, independent taint source into the same URL template literal —
  // requireCommunityAdmin authorizes it but never rewrites req.params
  // itself, so the raw string still reached the downstream URL even after
  // analyticsPath/securityPath were guarded. Confirmed via the
  // code-scanning API: alerts 383-387 stayed open after the inline-regex
  // rework above, with every remaining code flow citing
  // `req.params.communityId` (not analyticsPath/securityPath) as the
  // source.
  const cases = [
    ['get', '/:communityId/analytics/*'],
    ['get', '/:communityId/security/*'],
    ['put', '/:communityId/security/*'],
    ['post', '/:communityId/security/*'],
    ['delete', '/:communityId/security/*'],
  ];

  for (const [routerMethod, path] of cases) {
    it(`${routerMethod.toUpperCase()} ${path} validates communityId before proxying`, () => {
      const handler = extractHandler(routerMethod, path);

      assert.match(
        handler,
        /const\s*\{\s*communityId\s*\}\s*=\s*req\.params\s*;/,
        'handler must destructure communityId into a local before use'
      );
      assert.match(
        handler,
        /if\s*\(\s*!\/\^\\d\+\$\/\.test\(communityId\)\s*\)/,
        'handler must inline-guard communityId with /^\\d+$/.test(communityId)'
      );

      const guardIndex = handler.search(/if\s*\(\s*!\/\^\\d\+\$\/\.test\(communityId\)/);
      const axiosCallIndex = handler.search(/httpClient\.(get|put|post|delete)\(/);
      assert.ok(guardIndex < axiosCallIndex, 'communityId guard must run before the downstream request');

      // The URL/header construction must use the guarded local, never the
      // raw, unvalidated req.params.communityId directly.
      const sinkSection = handler.slice(axiosCallIndex, handler.indexOf(');', axiosCallIndex));
      assert.doesNotMatch(
        sinkSection,
        /req\.params\.communityId/,
        'downstream request must use the guarded local communityId, not req.params.communityId directly'
      );
    });
  }
});
