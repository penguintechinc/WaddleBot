/**
 * Regression guard: the OAuth callback handlers must validate `platform`
 * against the same allowlist their sibling start/link handlers already
 * use, before splicing it into an internal Identity Core URL.
 *
 * This reads authController.js as source text rather than importing it.
 * The module imports config/database.js, which opens a real pg Pool and
 * an un-refed setInterval — importing it here would leave the test
 * runner unable to exit cleanly. Reading the file avoids that while still
 * proving the fix is wired into the two vulnerable functions (not just
 * present as a stray, unused snippet).
 *
 * Run with the repo's configured runner: `npm test` (node --test).
 */
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(__dirname, 'authController.js'), 'utf8');

/** Extract an exported async function's body by name. */
function extractFunction(name) {
  const marker = `export async function ${name}(`;
  const start = source.indexOf(marker);
  assert.ok(start !== -1, `function not found: ${name}`);
  const nextExport = source.indexOf('\nexport ', start + marker.length);
  return source.slice(start, nextExport === -1 ? source.length : nextExport);
}

describe('authController.js OAuth callbacks validate platform before proxying', () => {
  for (const name of ['oauthCallback', 'oauthLinkCallback']) {
    it(`${name} rejects an unknown platform before any axios call`, () => {
      const body = extractFunction(name);

      // Same allowlist the sibling startOAuth/startOAuthLink handlers use.
      assert.match(
        body,
        /validPlatforms\s*=\s*\[\s*'discord'\s*,\s*'twitch'\s*,\s*'slack'\s*,\s*'youtube'\s*,\s*'kick'\s*\]/,
        `${name} must define the same validPlatforms allowlist as its sibling start handler`
      );

      const guardIndex = body.search(/if\s*\(\s*!validPlatforms\.includes\(platform\)\s*\)/);
      const axiosIndex = body.search(/axios\.(get|post|put|delete)\(/);

      assert.ok(guardIndex !== -1, `${name} has no validPlatforms guard`);
      assert.ok(axiosIndex !== -1, `${name} never calls axios`);
      assert.ok(guardIndex < axiosIndex, `${name} must validate platform before calling axios`);
    });
  }
});
