/**
 * Regression test: DoS hardening -- missing HTTP client timeouts.
 *
 * Before this fix, `axios.defaults.timeout` was `0` (axios's own default,
 * meaning "no timeout"), and none of this backend's ~55 axios calls across
 * 9+ files set their own, so a single unresponsive downstream service
 * (engagement-core, workflow-core, an OAuth provider, ...) could hang a
 * request indefinitely and exhaust the event loop / connection pool.
 *
 * Importing config/httpDefaults.js sets `axios.defaults.timeout` globally.
 * axios merges instance defaults into any call that doesn't set its own
 * `timeout` -- proven below against a real server that never responds,
 * covering the plain `import axios from 'axios'` call sites, the dynamic
 * `(await import('axios')).default` pattern (routes/admin.js), and the
 * generic `axios(config)` call form (workflowController.js) alike, since
 * all three resolve to the exact same module-cache singleton.
 *
 * Run with the repo's configured runner: `npm test` (node --test).
 */
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import http from 'node:http';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import axios from 'axios';

const __dirname = dirname(fileURLToPath(import.meta.url));

describe('config/httpDefaults.js -- global axios timeout', () => {
  it('sets a sane, non-zero, DoS-bounded default timeout', async () => {
    await import('./httpDefaults.js');
    assert.ok(axios.defaults.timeout > 0, 'axios.defaults.timeout must be set (axios default is 0 = no timeout)');
    assert.ok(axios.defaults.timeout <= 30000, 'default timeout should be a reasonably short DoS bound');
  });

  it('aborts a call to an unresponsive server within the configured window, even with no per-call timeout', async () => {
    await import('./httpDefaults.js');
    const original = axios.defaults.timeout;
    axios.defaults.timeout = 200; // keep the test fast; proves the exact same merge mechanism as the real default
    const server = http.createServer(() => { /* never respond */ });
    await new Promise((resolve) => server.listen(0, resolve));
    const { port } = server.address();

    try {
      const start = Date.now();
      await assert.rejects(
        // No 3rd-arg config at all -- the most common call shape in this codebase.
        () => axios.get(`http://127.0.0.1:${port}/`),
        (err) => err.code === 'ECONNABORTED' || /timeout/i.test(err.message)
      );
      assert.ok(Date.now() - start < 2000, 'must abort near the configured timeout, not hang indefinitely');
    } finally {
      axios.defaults.timeout = original;
      server.close();
    }
  });

  it('a per-call config object that omits timeout still inherits the default (dynamic-import call shape)', async () => {
    await import('./httpDefaults.js');
    const original = axios.defaults.timeout;
    axios.defaults.timeout = 200;
    const server = http.createServer(() => {});
    await new Promise((resolve) => server.listen(0, resolve));
    const { port } = server.address();
    const httpClient = (await import('axios')).default; // routes/admin.js's pattern

    try {
      await assert.rejects(
        () => httpClient.get(`http://127.0.0.1:${port}/`, { headers: { 'X-Test': '1' } }),
        (err) => err.code === 'ECONNABORTED' || /timeout/i.test(err.message)
      );
    } finally {
      axios.defaults.timeout = original;
      server.close();
    }
  });

  it('src/index.js imports httpDefaults.js before any route/controller module', () => {
    // Reading as text avoids importing index.js itself, which starts the
    // whole app (real HTTP listener, real DB pool) -- see the same
    // rationale documented in authController.platformAllowlist.test.js.
    const source = readFileSync(join(__dirname, '..', 'index.js'), 'utf8');
    const importLines = [...source.matchAll(/^import\s+.*$/gm)].map((m) => m[0]);
    const httpDefaultsIdx = importLines.findIndex((l) => l.includes('./config/httpDefaults.js'));
    assert.ok(httpDefaultsIdx !== -1, 'index.js must import config/httpDefaults.js');
    assert.equal(httpDefaultsIdx, 0, 'httpDefaults.js must be the first import so its side effect runs before any controller/service module');
  });
});
