/**
 * Regression test: OAuth-JWT-in-URL leak (OWASP A07).
 *
 * oauthCallback() used to redirect the browser to
 * `${frontendOrigin}/auth/callback?token=${sessionToken}` -- the full
 * session JWT, in a URL query string, which leaks into proxy/access logs,
 * browser history, and the Referer header of any outbound request the
 * callback page happens to make.
 *
 * It now mints a short-lived, single-use opaque exchange code instead and
 * redirects with THAT (`?code=`); the frontend immediately POSTs it to
 * `/api/v1/auth/exchange` (redeemOAuthExchangeCode) to redeem the real JWT,
 * delivered over the response body plus an HttpOnly `wb_session` cookie,
 * never the URL. Mirrors hub_api's oauth_callback / exchange_oauth_code
 * (PR #227/#258).
 *
 * Uses node:test's module mocking (`--experimental-test-module-mocks`,
 * wired into package.json's `test` script) to swap out
 * config/database.js's query()/transaction() before importing the
 * controller -- importing the real module opens a live pg Pool with an
 * un-refed setInterval that hangs the test runner (see
 * authController.platformAllowlist.test.js).
 *
 * Run with the repo's configured runner: `npm test` (node --test).
 */
import assert from 'node:assert/strict';
import { describe, it, mock } from 'node:test';
import axios from 'axios';

// FIFO queue of query() responses -- each call to the mocked query()
// shifts the next queued response off the front. Simpler and far less
// fragile than node:test's mockImplementationOnce(impl, onCall), whose
// `onCall` index is an absolute invocation count shared across every test
// in this file (since queryMock is set up once at module scope).
const queryResponses = [];
const queryMock = mock.fn(async (text) => {
  if (queryResponses.length === 0) {
    throw new Error(`Unexpected query() call with no queued response: ${text}`);
  }
  return queryResponses.shift();
});

mock.module('../config/database.js', {
  exports: {
    query: queryMock,
    transaction: async (cb) => cb({}),
  },
});

const { oauthCallback, redeemOAuthExchangeCode } = await import('./authController.js');

/** Minimal Express response double capturing status/json/redirect/cookie calls. */
function mockRes() {
  return {
    statusCode: 200,
    body: undefined,
    redirectedTo: undefined,
    cookies: [],
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    },
    redirect(url) {
      this.redirectedTo = url;
    },
    cookie(name, value, options) {
      this.cookies.push({ name, value, options });
    },
  };
}

function capturingNext() {
  const calls = [];
  const next = (err) => calls.push(err);
  next.calls = calls;
  return next;
}

describe('authController — OAuth callback no longer puts the JWT in the redirect URL', () => {
  it('oauthCallback redirects with an opaque exchange code, not the session JWT', async () => {
    queryResponses.length = 0;
    // Ordered query() calls exercised by the "existing linked identity"
    // happy path: state lookup, state cleanup, identity lookup (found),
    // identity update, tenant lookup (not found), session insert, exchange
    // code insert.
    queryResponses.push(
      { rows: [{ mode: 'login', metadata: { tenantSlug: 'global' } }] }, // SELECT ... FROM hub_oauth_states
      { rows: [] }, // DELETE FROM hub_oauth_states
      {
        rows: [{
          hub_user_id: 7,
          id: 7,
          email: 'someuser@example.com',
          username: 'someuser',
          avatar_url: null,
          is_super_admin: false,
          is_analytics_consumer: false,
        }],
      }, // SELECT ... FROM hub_user_identities (existing identity found)
      { rows: [] }, // UPDATE hub_user_identities
      { rows: [] }, // SELECT id FROM tenants (not found)
      { rows: [] }, // INSERT INTO hub_sessions
      { rows: [] } // INSERT INTO hub_oauth_exchange_codes
    );

    const axiosPostMock = mock.method(axios, 'post', async () => ({
      data: { user: { id: 'discord-123', username: 'someuser', email: 'someuser@example.com', avatar_url: null } },
    }));

    try {
      const req = { params: { platform: 'discord' }, query: { code: 'provider-code', state: 'state-xyz' } };
      const res = mockRes();
      const next = capturingNext();

      await oauthCallback(req, res, next);

      assert.equal(next.calls.length, 0, `unexpected next(err): ${next.calls[0]?.message}`);
      assert.ok(res.redirectedTo, 'must redirect');

      const location = new URL(res.redirectedTo);
      assert.equal(location.pathname, '/auth/callback');
      assert.ok(location.searchParams.has('code'), 'redirect must carry the opaque exchange code');
      assert.ok(!location.searchParams.has('token'), 'redirect must NOT carry a token param');

      // The hard security assertion: no JWT anywhere in the redirect target.
      // A JWT is three base64url segments joined by dots; the exchange code
      // is a single opaque base64url blob with no dots, and the default
      // test origin (http://localhost:5173) has none either.
      assert.doesNotMatch(
        res.redirectedTo,
        /[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/,
        'Location header must not contain a JWT'
      );

      const exchangeCode = location.searchParams.get('code');
      assert.ok(exchangeCode.length >= 32, 'exchange code should be high-entropy');

      // Confirm it was persisted for single-use redemption.
      const insertCall = queryMock.mock.calls.at(-1);
      assert.match(insertCall.arguments[0], /INSERT INTO hub_oauth_exchange_codes/);
      assert.equal(insertCall.arguments[1][0], exchangeCode);
    } finally {
      axiosPostMock.mock.restore();
    }
  });
});

describe('authController — redeemOAuthExchangeCode (POST /api/v1/auth/exchange)', () => {
  it('rejects a request with no code', async () => {
    queryResponses.length = 0;
    const req = { body: {} };
    const res = mockRes();
    const next = capturingNext();

    await redeemOAuthExchangeCode(req, res, next);

    assert.equal(next.calls.length, 1);
    assert.equal(next.calls[0].statusCode, 400);
  });

  it('rejects an invalid or already-used code without setting a session cookie', async () => {
    queryResponses.length = 0;
    queryResponses.push({ rows: [] }); // atomic claim matched nothing

    const req = { body: { code: 'bogus-or-reused' } };
    const res = mockRes();
    const next = capturingNext();

    await redeemOAuthExchangeCode(req, res, next);

    assert.equal(next.calls.length, 1);
    assert.equal(next.calls[0].statusCode, 400);
    assert.equal(res.cookies.length, 0);
  });

  it('redeems a valid code exactly once: sets the wb_session cookie and returns the JWT in the body', async () => {
    queryResponses.length = 0;
    queryResponses.push({ rows: [{ token: 'the-real-session-jwt' }] });

    const req = { body: { code: 'good-code' } };
    const res = mockRes();
    const next = capturingNext();

    await redeemOAuthExchangeCode(req, res, next);

    const updateCall = queryMock.mock.calls.at(-1);
    assert.match(updateCall.arguments[0], /UPDATE hub_oauth_exchange_codes/);
    assert.match(updateCall.arguments[0], /used = false/);
    assert.equal(updateCall.arguments[1][0], 'good-code');

    assert.equal(next.calls.length, 0);
    assert.equal(res.body.success, true);
    assert.equal(res.body.token, 'the-real-session-jwt');

    assert.equal(res.cookies.length, 1);
    const sessionCookie = res.cookies[0];
    assert.equal(sessionCookie.name, 'wb_session');
    assert.equal(sessionCookie.value, 'the-real-session-jwt');
    assert.equal(sessionCookie.options.httpOnly, true);
    assert.equal(sessionCookie.options.secure, true);
    assert.equal(sessionCookie.options.sameSite, 'lax');
  });
});
