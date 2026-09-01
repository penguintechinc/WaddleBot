/**
 * Regression guard: identityLinkCallback must validate `platform` against
 * the same allowlist its sibling startIdentityLink handler already uses,
 * before splicing it into an internal Identity Core URL.
 *
 * This reads identityController.js as source text rather than importing
 * it. The module imports config/database.js, which opens a real pg Pool
 * and an un-refed setInterval — importing it here would leave the test
 * runner unable to exit cleanly. Reading the file avoids that while still
 * proving the fix is wired into the vulnerable function.
 *
 * Unlike authController.js, `state` here is a client-supplied base64 JSON
 * blob (not looked up server-side), so `platform` was fully attacker
 * controlled before this fix — the most directly exploitable of the four
 * unvalidated callback handlers.
 *
 * Run with the repo's configured runner: `npm test` (node --test).
 */
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(__dirname, 'identityController.js'), 'utf8');

/** Extract an exported async function's body by name. */
function extractFunction(name) {
  const marker = `export async function ${name}(`;
  const start = source.indexOf(marker);
  assert.ok(start !== -1, `function not found: ${name}`);
  const nextExport = source.indexOf('\nexport ', start + marker.length);
  return source.slice(start, nextExport === -1 ? source.length : nextExport);
}

describe('identityController.js identityLinkCallback validates platform before proxying', () => {
  it('rejects an unknown platform before calling axios', () => {
    const body = extractFunction('identityLinkCallback');

    // Same allowlist the sibling startIdentityLink handler uses.
    assert.match(
      body,
      /validPlatforms\s*=\s*\[\s*'discord'\s*,\s*'twitch'\s*,\s*'slack'\s*\]/,
      'identityLinkCallback must define the same validPlatforms allowlist as startIdentityLink'
    );

    const guardIndex = body.search(/if\s*\(\s*!validPlatforms\.includes\(platform\)\s*\)/);
    const axiosIndex = body.search(/axios\.(get|post|put|delete)\(/);

    assert.ok(guardIndex !== -1, 'identityLinkCallback has no validPlatforms guard');
    assert.ok(axiosIndex !== -1, 'identityLinkCallback never calls axios');
    assert.ok(guardIndex < axiosIndex, 'identityLinkCallback must validate platform before calling axios');
  });

  it('startIdentityLink and identityLinkCallback agree on the allowlist', () => {
    const start = extractFunction('startIdentityLink');
    const callback = extractFunction('identityLinkCallback');

    const startMatch = start.match(/validPlatforms\s*=\s*(\[[^\]]*\])/);
    const callbackMatch = callback.match(/validPlatforms\s*=\s*(\[[^\]]*\])/);

    assert.ok(startMatch, 'startIdentityLink has no validPlatforms array');
    assert.ok(callbackMatch, 'identityLinkCallback has no validPlatforms array');
    assert.equal(callbackMatch[1], startMatch[1], 'callback allowlist must match the start handler exactly');
  });
});
