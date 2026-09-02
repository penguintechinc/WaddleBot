/**
 * Regression test: OWASP A01 cross-community BOLA in the RCON proxy.
 *
 * executeCommand (and its siblings) proxy straight to the server-manager
 * module keyed by `:serverId` from the URL. `requireCommunityAdmin`/
 * `requireAuth` only confirm the caller is authorized on `:communityId` --
 * before the fix, nothing confirmed `:serverId` actually belonged to that
 * community, so an admin of community A could operate community B's server
 * (run RCON commands, kick/ban players, move voice users) just by supplying
 * its numeric id in the URL.
 *
 * Uses node:test's module mocking (`--experimental-test-module-mocks`,
 * wired into package.json's `test` script) to swap out
 * `config/database.js`'s `query()` before importing the controller --
 * importing the real module opens a live pg Pool with an un-refed
 * `setInterval` that hangs the test runner (see the same rationale in
 * `authController.platformAllowlist.test.js`).
 *
 * Run with the repo's configured runner: `npm test` (node --test).
 */
import assert from 'node:assert/strict';
import { describe, it, mock } from 'node:test';

const queryMock = mock.fn(async () => ({ rows: [] }));

mock.module('../config/database.js', {
  exports: { query: queryMock },
});

const { executeCommand, getServerStatus, kickPlayer, listServers } =
  await import('./rconController.js');

/** Minimal Express response double capturing status/json calls. */
function mockRes() {
  return {
    statusCode: 200,
    body: undefined,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    },
  };
}

function unreachableNext() {
  assert.fail('next(err) should not be called for an authz rejection');
}

describe('rconController — serverId must belong to :communityId (cross-community BOLA)', () => {
  it('executeCommand returns 403 for a serverId owned by a different community, without proxying', async () => {
    queryMock.mock.mockImplementationOnce(async () => ({ rows: [] })); // not found under this community

    const fetchMock = mock.method(globalThis, 'fetch', async () => {
      throw new Error('fetch should not have been called for a cross-community serverId');
    });
    try {
      const req = {
        params: { communityId: '1', serverId: '999' },
        body: { command: 'say hi' },
        user: { id: 42 },
      };
      const res = mockRes();
      await executeCommand(req, res, unreachableNext);

      assert.equal(fetchMock.mock.callCount(), 0, 'must not proxy to server-manager');
      assert.equal(res.statusCode, 403);
      assert.match(res.body.error, /does not belong to this community/);
    } finally {
      fetchMock.mock.restore();
    }
  });

  it('executeCommand proxies once ownership under the community is confirmed', async () => {
    queryMock.mock.mockImplementationOnce(async () => ({ rows: [{ id: 5 }] })); // owned by this community

    const fetchMock = mock.method(globalThis, 'fetch', async () => ({
      json: async () => ({ success: true }),
    }));
    try {
      const req = {
        params: { communityId: '1', serverId: '5' },
        body: { command: 'say hi' },
        user: { id: 42 },
      };
      const res = mockRes();
      await executeCommand(req, res, unreachableNext);

      assert.equal(fetchMock.mock.callCount(), 1);
      assert.equal(res.body.success, true);
    } finally {
      fetchMock.mock.restore();
    }
  });

  it('getServerStatus (member-tier route) also rejects a cross-community serverId', async () => {
    queryMock.mock.mockImplementationOnce(async () => ({ rows: [] }));
    const fetchMock = mock.method(globalThis, 'fetch', async () => {
      throw new Error('fetch should not have been called');
    });
    try {
      const req = { params: { communityId: '1', serverId: '999' } };
      const res = mockRes();
      await getServerStatus(req, res, unreachableNext);

      assert.equal(fetchMock.mock.callCount(), 0);
      assert.equal(res.statusCode, 403);
    } finally {
      fetchMock.mock.restore();
    }
  });

  it('kickPlayer rejects a cross-community serverId before proxying', async () => {
    queryMock.mock.mockImplementationOnce(async () => ({ rows: [] }));
    const fetchMock = mock.method(globalThis, 'fetch', async () => {
      throw new Error('fetch should not have been called');
    });
    try {
      const req = {
        params: { communityId: '1', serverId: '999' },
        body: { player: 'griefer' },
        user: { id: 42 },
      };
      const res = mockRes();
      await kickPlayer(req, res, unreachableNext);

      assert.equal(fetchMock.mock.callCount(), 0);
      assert.equal(res.statusCode, 403);
    } finally {
      fetchMock.mock.restore();
    }
  });

  it('listServers stays scoped to :communityId via SQL (control case, unaffected by the fix)', async () => {
    queryMock.mock.mockImplementationOnce(async (text, params) => {
      assert.match(text, /WHERE community_id = \$1/);
      assert.deepEqual(params, ['1']);
      return { rows: [{ id: 5, display_name: 'Server A' }] };
    });
    const req = { params: { communityId: '1' }, isCommunityAdmin: false };
    const res = mockRes();
    await listServers(req, res, unreachableNext);

    assert.equal(res.body.servers.length, 1);
  });
});
