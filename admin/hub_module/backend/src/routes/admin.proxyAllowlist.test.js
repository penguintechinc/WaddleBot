/**
 * Regression guard: the security/analytics proxy routes in admin.js must
 * gate on the shared allowlist before ever building the downstream URL.
 *
 * This intentionally reads admin.js as source text rather than importing
 * the module. admin.js pulls in ~30 controllers that each import
 * config/database.js, which opens a real pg Pool and an un-refed
 * setInterval — importing it here would leave the test runner unable to
 * exit cleanly. Reading the file avoids that entirely while still proving
 * the fix is actually wired into the route handlers (not just present in
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

describe('admin.js proxy routes are gated by isAllowedProxyPath', () => {
  it('imports the shared allowlist helper', () => {
    assert.match(source, /import\s*\{\s*isAllowedProxyPath\s*\}\s*from\s*'\.\.\/utils\/proxyAllowlist\.js'/);
  });

  const cases = [
    ['get', '/:communityId/analytics/*', 'analytics', 'analyticsPath', "'GET'"],
    ['get', '/:communityId/security/*', 'security', 'securityPath', "'GET'"],
    ['put', '/:communityId/security/*', 'security', 'securityPath', "'PUT'"],
    ['post', '/:communityId/security/*', 'security', 'securityPath', "'POST'"],
    ['delete', '/:communityId/security/*', 'security', 'securityPath', "'DELETE'"],
  ];

  for (const [routerMethod, path, service, pathVar, methodLiteral] of cases) {
    it(`${routerMethod.toUpperCase()} ${path} rejects a disallowed path before proxying`, () => {
      // security registers 4 handlers (get/put/post/delete) on the same
      // path — the routerMethod in the marker disambiguates which one.
      const handler = extractHandler(routerMethod, path);

      assert.match(
        handler,
        new RegExp(`isAllowedProxyPath\\(\\s*'${service}'\\s*,\\s*${methodLiteral}\\s*,\\s*${pathVar}\\s*\\)`),
        `handler must call isAllowedProxyPath('${service}', ${methodLiteral}, ${pathVar})`
      );

      // The guard must reject with a client error and must appear BEFORE
      // the axios call is issued — otherwise the request already went out.
      const guardIndex = handler.search(/if\s*\(\s*!isAllowedProxyPath/);
      const axiosCallIndex = handler.search(/httpClient\.(get|put|post|delete)\(/);
      assert.ok(guardIndex !== -1, 'no rejection guard found');
      assert.ok(axiosCallIndex !== -1, 'no downstream axios call found');
      assert.ok(guardIndex < axiosCallIndex, 'guard must run before the downstream request is made');

      assert.match(handler, /res\.status\(403\)/, 'disallowed paths must be rejected with 403');
    });
  }
});
