/**
 * Regression guard: utils/certificates.js command injection (OWASP A03).
 *
 * The removed module built shell command strings by directly interpolating
 * request-shaped input (domain, email, webroot, dnsPlugin) into
 * `child_process.exec()` via `util.promisify` -- e.g.
 * `certbot certonly ... -d ${domain} ... --email ${email} ...` -- so a
 * value like `example.com; rm -rf /` would execute as a second shell
 * command. The module had zero callers anywhere in the codebase (no route,
 * controller, or service imported it), so it was removed outright rather
 * than rewritten with execFile/spawn + an argument array, per the finding's
 * "if genuinely dead code, remove it" guidance.
 *
 * This test asserts the vulnerable module stays gone, and that nothing
 * silently reintroduces a shell-metacharacter-vulnerable exec() call
 * anywhere in src/ built from unsanitized template-string interpolation of
 * a domain/email/webroot-shaped variable.
 *
 * Run with the repo's configured runner: `npm test` (node --test).
 */
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const srcDir = join(__dirname, '..');

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      out.push(...walk(full));
    } else if (entry.endsWith('.js') && !entry.endsWith('.test.js')) {
      out.push(full);
    }
  }
  return out;
}

describe('certificates.js command injection -- removed as dead code', () => {
  it('utils/certificates.js no longer exists', () => {
    assert.equal(existsSync(join(__dirname, 'certificates.js')), false);
  });

  it('no source file imports the removed certificate-generation functions', () => {
    const removedExports = [
      'generateSelfSignedCertificate',
      'generateCertbotCertificate',
      'renewCertbotCertificate',
      'getCertbotCertificates',
    ];
    const offenders = [];
    for (const file of walk(srcDir)) {
      const contents = readFileSync(file, 'utf8');
      for (const name of removedExports) {
        if (contents.includes(name)) {
          offenders.push(`${file}: ${name}`);
        }
      }
    }
    assert.deepEqual(offenders, [], 'a removed certificate-generation export was reintroduced without going through this file');
  });

  it('no source file builds an exec()/execSync() shell string via template-literal interpolation of a domain/email/webroot-shaped variable', () => {
    const dangerousPattern = /exec(?:Async)?\s*\(\s*`[^`]*\$\{\s*(domain|email|webroot|dnsPlugin|altDomains)\b/;
    const offenders = [];
    for (const file of walk(srcDir)) {
      const contents = readFileSync(file, 'utf8');
      if (dangerousPattern.test(contents)) {
        offenders.push(file);
      }
    }
    assert.deepEqual(offenders, [], 'found a shell-string exec() built from unsanitized template interpolation');
  });
});
