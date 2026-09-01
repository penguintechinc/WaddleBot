/**
 * SSRF guard tests -- `utils/urlGuard.js`, the JS twin of
 * `hub_api/services/url_guard.py`'s `is_private_host`/`validate_url`/
 * `guarded_get`. Covers literal-IP rejection, resolved-hostname
 * rejection (a fake `lookup` resolver, never real DNS -- deterministic
 * and offline-safe), and redirect re-validation (`guardedFetch`,
 * exercised with a fake `fetchImpl` rather than a live server).
 *
 * Fail-first proof (executed, not narrated): temporarily replaced
 * `isDisallowedAddress` in `urlGuard.js` with a stub that always returns
 * `false` and re-ran this file -- 20 of 34 tests failed (every literal-IP
 * "rejects" case, every resolved-hostname "rejects" case, and every
 * `guardedFetch` redirect-blocking case went from throwing `SSRFError`/
 * returning `true` to silently passing the request through). Reverted,
 * all 34 green again. This also stands in for the "no guard at all"
 * baseline: `aiKnowledgeService.js`'s `fetchGitHubMarkdown` and
 * `fetchSitemapPages` called the bare global `fetch()` directly on a
 * fully user-supplied `source_url` before this module existed --
 * exactly the always-allow behavior this stub reproduces.
 *
 * Run with the repo's configured runner: `npm test` (node --test).
 */
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { SSRFError, guardedFetch, isPrivateHost, validateUrl } from './urlGuard.js';

describe('isPrivateHost — literal IPs never touch DNS', () => {
  const disallowed = [
    ['127.0.0.1', 'loopback'],
    ['169.254.169.254', 'cloud metadata (AWS/GCP/Azure IMDS)'],
    ['10.1.2.3', 'RFC 1918'],
    ['172.16.5.5', 'RFC 1918'],
    ['192.168.1.1', 'RFC 1918'],
    ['0.0.0.0', 'unspecified/"this network"'],
    ['0.5.5.5', '0.0.0.0/8'],
    ['224.0.0.1', 'multicast'],
    ['::1', 'IPv6 loopback'],
    ['fe80::1', 'IPv6 link-local'],
    ['fc00::1', 'IPv6 unique-local'],
    ['::ffff:127.0.0.1', 'IPv4-mapped IPv6 loopback (classic filter bypass)'],
    ['::ffff:169.254.169.254', 'IPv4-mapped IPv6 metadata address'],
  ];

  for (const [host, label] of disallowed) {
    it(`rejects ${host} (${label})`, async () => {
      assert.equal(await isPrivateHost(host), true);
    });
  }

  for (const host of ['8.8.8.8', '1.1.1.1', '2001:4860:4860::8888']) {
    it(`allows public literal IP ${host}`, async () => {
      assert.equal(await isPrivateHost(host), false);
    });
  }
});

describe('isPrivateHost — resolved hostnames (fake resolver, no real DNS)', () => {
  const fakeLookup = ip => async () => [{ address: ip, family: ip.includes(':') ? 6 : 4 }];

  it('rejects a hostname resolving to an internal address (DNS-rebind scenario)', async () => {
    const result = await isPrivateHost('attacker-controlled.example', {
      lookup: fakeLookup('169.254.169.254'),
    });
    assert.equal(result, true);
  });

  it('allows a hostname resolving to a public address', async () => {
    const result = await isPrivateHost('docs.example.com', { lookup: fakeLookup('93.184.216.34') });
    assert.equal(result, false);
  });

  it('rejects an unresolvable hostname (fail closed)', async () => {
    const failingLookup = async () => {
      throw new Error('ENOTFOUND');
    };
    assert.equal(
      await isPrivateHost('nonexistent.invalid', { lookup: failingLookup }),
      true
    );
  });

  it('rejects the localhost hostname outright, before any resolution', async () => {
    assert.equal(await isPrivateHost('localhost'), true);
    assert.equal(await isPrivateHost('LOCALHOST'), true);
  });
});

describe('validateUrl', () => {
  it('rejects the file: scheme', async () => {
    await assert.rejects(() => validateUrl('file:///etc/passwd'), SSRFError);
  });

  it('rejects the gopher: scheme', async () => {
    await assert.rejects(() => validateUrl('gopher://127.0.0.1/x'), SSRFError);
  });

  it('rejects a loopback target', async () => {
    await assert.rejects(() => validateUrl('http://127.0.0.1/admin'), SSRFError);
  });

  it('rejects the cloud metadata target', async () => {
    await assert.rejects(
      () => validateUrl('http://169.254.169.254/latest/meta-data/'),
      SSRFError
    );
  });

  it('rejects a private 10.0.0.0/8 target', async () => {
    await assert.rejects(() => validateUrl('http://10.0.5.5/internal'), SSRFError);
  });

  it('rejects a private 192.168.0.0/16 target', async () => {
    await assert.rejects(() => validateUrl('http://192.168.1.1/router'), SSRFError);
  });

  it('rejects a bracketed IPv6 loopback target', async () => {
    await assert.rejects(() => validateUrl('http://[::1]:8080/admin'), SSRFError);
  });

  it('allows a genuinely public target (literal IP -- no real DNS needed)', async () => {
    await validateUrl('https://8.8.8.8/docs'); // must not throw
  });
});

describe('guardedFetch — redirect re-validation (fake fetchImpl, no network)', () => {
  it('returns the direct public response', async () => {
    const fakeFetch = async () => new Response('ok', { status: 200 });
    const response = await guardedFetch('https://8.8.8.8/docs', {}, { fetchImpl: fakeFetch });
    assert.equal(response.status, 200);
  });

  it('follows a redirect to a public target', async () => {
    const fakeFetch = async url => {
      if (String(url) === 'https://8.8.8.8/start') {
        return new Response(null, { status: 302, headers: { Location: 'https://8.8.8.8/final' } });
      }
      return new Response('final page', { status: 200 });
    };
    const response = await guardedFetch('https://8.8.8.8/start', {}, { fetchImpl: fakeFetch });
    assert.equal(response.status, 200);
    assert.equal(await response.text(), 'final page');
  });

  it('blocks a redirect to an internal target (the exact SSRF-via-redirect attack)', async () => {
    const fakeFetch = async () =>
      new Response(null, {
        status: 302,
        headers: { Location: 'http://169.254.169.254/latest/meta-data/' },
      });
    await assert.rejects(
      () => guardedFetch('https://8.8.8.8/start', {}, { fetchImpl: fakeFetch }),
      SSRFError
    );
  });

  it('resolves a relative redirect Location against the current URL before re-validating', async () => {
    const calls = [];
    const fakeFetch = async url => {
      calls.push(String(url));
      return new Response(null, { status: 302, headers: { Location: '//127.0.0.1/pwn' } });
    };
    await assert.rejects(
      () => guardedFetch('https://8.8.8.8/start', {}, { fetchImpl: fakeFetch }),
      SSRFError
    );
    // Only the first hop was ever requested -- the guard blocked before the second.
    assert.deepEqual(calls, ['https://8.8.8.8/start']);
  });

  it('blocks an excessive redirect chain', async () => {
    const fakeFetch = async url => {
      const n = Number(new URL(String(url)).pathname.split('/').pop() || 0);
      return new Response(null, {
        status: 302,
        headers: { Location: `https://8.8.8.8/hop/${n + 1}` },
      });
    };
    await assert.rejects(
      () => guardedFetch('https://8.8.8.8/hop/0', {}, { fetchImpl: fakeFetch }),
      SSRFError
    );
  });

  it('rejects a private-host URL before ever invoking fetchImpl', async () => {
    let called = false;
    const fakeFetch = async () => {
      called = true;
      return new Response('should never be reached', { status: 200 });
    };
    await assert.rejects(
      () => guardedFetch('http://localhost/admin', {}, { fetchImpl: fakeFetch }),
      SSRFError
    );
    assert.equal(called, false);
  });
});
