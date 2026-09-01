/**
 * Tests for the security/analytics downstream proxy allowlist.
 *
 * Run with the repo's configured runner: `npm test` (node --test).
 *
 * This is the core fix for the CRITICAL SSRF alert in routes/admin.js: the
 * `/:communityId/{security,analytics}/*` proxy routes used to splice the
 * Express wildcard capture straight into an internal service URL with no
 * check on where it could point. These tests assert the allowlist rejects
 * everything outside the known-safe, community-scoped downstream routes
 * (including the internal-only endpoints and path-traversal payloads an
 * attacker would use to reach them) while every legitimate admin-UI call
 * still passes.
 */
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { isAllowedProxyPath } from './proxyAllowlist.js';

describe('isAllowedProxyPath — attacker paths are rejected', () => {
  it('blocks path traversal into the internal-only API surface', () => {
    // These are the exact internal service-to-service endpoints
    // (never meant to be reachable from a community admin) that a
    // vulnerable proxy would forward to via ../ segments.
    const traversalPayloads = [
      '../internal/check',
      '../../internal/check',
      '../../internal/warn',
      '../../internal/sync-action',
      '../../internal/events',
      '../../internal/aggregate',
      'config/../../internal/check',
    ];

    for (const payload of traversalPayloads) {
      for (const service of ['analytics', 'security']) {
        for (const method of ['GET', 'PUT', 'POST', 'DELETE']) {
          assert.equal(
            isAllowedProxyPath(service, method, payload),
            false,
            `${service} ${method} ${payload} must be rejected`
          );
        }
      }
    }
  });

  it('blocks arbitrary/off-list downstream paths', () => {
    const offListPaths = [
      'admin/delete-everything',
      'status/../internal/check',
      'config/extra',
      'not-a-real-endpoint',
      'blocked-words/not-a-number',
      'warnings/abc',
    ];

    for (const path of offListPaths) {
      assert.equal(isAllowedProxyPath('security', 'GET', path), false, path);
    }
  });

  it('blocks host/authority confusion attempts (double slash, @, colon)', () => {
    const hostConfusionPayloads = [
      '//evil.com/config',
      'config@evil.com',
      'config:8080/../config',
    ];

    for (const payload of hostConfusionPayloads) {
      assert.equal(isAllowedProxyPath('security', 'GET', payload), false, payload);
    }
  });

  it('rejects a method that is not permitted for an otherwise-known path', () => {
    // blocked-words/:id is only PUT/DELETE, never GET/POST directly.
    assert.equal(isAllowedProxyPath('security', 'GET', 'blocked-words/5'), false);
    assert.equal(isAllowedProxyPath('security', 'POST', 'blocked-words/5'), false);
  });

  it('rejects unknown services', () => {
    assert.equal(isAllowedProxyPath('unknown-service', 'GET', 'config'), false);
  });

  it('rejects empty, non-string, or missing path tails', () => {
    assert.equal(isAllowedProxyPath('security', 'GET', ''), false);
    assert.equal(isAllowedProxyPath('security', 'GET', undefined), false);
    assert.equal(isAllowedProxyPath('security', 'GET', null), false);
  });
});

describe('isAllowedProxyPath — legitimate admin-UI paths still work', () => {
  it('allows every analytics GET path the admin frontend calls', () => {
    const legitimate = ['basic', 'poll', 'health-score', 'bad-actors', 'retention', 'config', 'metrics', 'bot-score'];
    for (const path of legitimate) {
      assert.equal(isAllowedProxyPath('analytics', 'GET', path), true, path);
    }
  });

  it('allows every security path/method the admin frontend calls', () => {
    assert.equal(isAllowedProxyPath('security', 'GET', 'config'), true);
    assert.equal(isAllowedProxyPath('security', 'PUT', 'config'), true);
    assert.equal(isAllowedProxyPath('security', 'GET', 'blocked-words'), true);
    assert.equal(isAllowedProxyPath('security', 'POST', 'blocked-words'), true);
    assert.equal(isAllowedProxyPath('security', 'PUT', 'blocked-words/42'), true);
    assert.equal(isAllowedProxyPath('security', 'DELETE', 'blocked-words/42'), true);
    assert.equal(isAllowedProxyPath('security', 'GET', 'warnings'), true);
    assert.equal(isAllowedProxyPath('security', 'DELETE', 'warnings/7'), true);
    assert.equal(isAllowedProxyPath('security', 'GET', 'moderation-log'), true);
  });

  it('is case-insensitive on HTTP method', () => {
    assert.equal(isAllowedProxyPath('security', 'get', 'config'), true);
  });
});
