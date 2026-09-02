/**
 * Regression tests for the OAuth callback exchange-code handoff AND
 * security.md's C4 fix (session JWT moved out of localStorage).
 *
 * `handleOAuthCallback` used to receive the session JWT directly (read off
 * the callback redirect's `?token=...` query string) and store it as-is.
 * The backend hotfix (hub_api/blueprints/v1/auth.py::oauth_callback) no
 * longer puts the JWT in the URL -- it redirects with a short-lived,
 * single-use opaque `code` instead, and the frontend must POST that code to
 * `/api/v1/auth/exchange` to get the real JWT back over the response body.
 * This file pins two separate things: (1) the value passed in is a CODE,
 * never conflated with a token, and (2) the C4 fix -- whatever `/exchange`
 * (or `/login`, `/admin`, `/temp-password`, `/refresh`) returns is NEVER
 * written to localStorage; the session lives only in the HttpOnly cookie
 * the server set on the same response, and the client picks it up by
 * asking `/api/v1/auth/me`, not by reading anything out of the JSON body.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, waitFor } from '@testing-library/react';

import api from '../../services/api';
import { AuthProvider, useAuth } from '../AuthContext';

vi.mock('../../services/api', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

function installLocalStorage() {
  const store = new Map();
  vi.stubGlobal('localStorage', {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
    clear: () => store.clear(),
    key: (i) => Array.from(store.keys())[i] ?? null,
    get length() {
      return store.size;
    },
  });
  return store;
}

/** Renders the provider and exposes its context value for assertions. */
function harness() {
  const captured = {};
  function Probe() {
    Object.assign(captured, useAuth());
    return <div data-testid="ready" />;
  }
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );
  return captured;
}

let store;

beforeEach(() => {
  store = installLocalStorage();
  api.get.mockResolvedValue({ data: { success: true, user: { id: 1, roles: [] } } });
});

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe('handleOAuthCallback', () => {
  it('POSTs the code to /api/v1/auth/exchange rather than trusting it as a token', async () => {
    api.post.mockResolvedValue({ data: { success: true, token: 'real-session-jwt' } });
    const ctx = harness();

    await act(async () => {
      await ctx.handleOAuthCallback('the-opaque-exchange-code');
    });

    expect(api.post).toHaveBeenCalledWith('/api/v1/auth/exchange', {
      code: 'the-opaque-exchange-code',
    });
  });

  it('never writes the exchange JWT (or anything else) to localStorage', async () => {
    api.post.mockResolvedValue({ data: { success: true, token: 'real-session-jwt' } });
    const ctx = harness();

    await act(async () => {
      await ctx.handleOAuthCallback('the-opaque-exchange-code');
    });

    // security.md C4: the JWT hub-api returned in the body was ALSO set as
    // an HttpOnly cookie on this same response -- the frontend must never
    // additionally persist it somewhere an XSS payload could read it back.
    expect(store.get('token')).toBeUndefined();
    expect(store.size).toBe(0);
  });

  it('fetches the current user after a successful exchange', async () => {
    api.post.mockResolvedValue({ data: { success: true, token: 'real-session-jwt' } });
    const ctx = harness();

    await act(async () => {
      await ctx.handleOAuthCallback('the-opaque-exchange-code');
    });

    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/api/v1/auth/me'));
  });

  it('does not store anything when the exchange fails', async () => {
    api.post.mockRejectedValue(new Error('invalid or expired exchange code'));
    const ctx = harness();

    await expect(
      act(async () => {
        await ctx.handleOAuthCallback('the-opaque-exchange-code');
      }),
    ).rejects.toThrow();

    expect(store.get('token')).toBeUndefined();
  });

  it('is a no-op when called without a code', async () => {
    const ctx = harness();

    await act(async () => {
      await ctx.handleOAuthCallback(undefined);
    });

    expect(api.post).not.toHaveBeenCalled();
  });
});

describe('login (security.md C4 -- session cookie, not localStorage)', () => {
  it('never writes the returned JWT to localStorage', async () => {
    api.post.mockResolvedValue({
      data: { success: true, token: 'password-login-jwt', user: { id: 1, roles: [] } },
    });
    const ctx = harness();

    await act(async () => {
      await ctx.login('user@example.com', 'hunter2');
    });

    expect(store.get('token')).toBeUndefined();
    expect(store.size).toBe(0);
  });

  it('sets user state directly from the login response body', async () => {
    const user = { id: 1, email: 'user@example.com', roles: [] };
    api.post.mockResolvedValue({ data: { success: true, token: 'password-login-jwt', user } });
    const ctx = harness();

    await act(async () => {
      await ctx.login('user@example.com', 'hunter2');
    });

    expect(ctx.user).toEqual(user);
  });
});

describe('mount behavior (security.md C4 -- no client-side session signal)', () => {
  it('always calls /api/v1/auth/me on mount, regardless of localStorage state', async () => {
    // The old implementation skipped this call entirely when
    // localStorage had no token; there is no equivalent client-side
    // signal anymore (the session cookie is HttpOnly), so the mount
    // effect has to ask the server unconditionally.
    await act(async () => {
      harness();
    });

    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/api/v1/auth/me'));
  });
});

describe('logout (security.md C4)', () => {
  it('clears user state without touching localStorage', async () => {
    api.post.mockResolvedValue({ data: { success: true } });
    const ctx = harness();
    await act(async () => {
      await ctx.login('user@example.com', 'hunter2');
    });

    await act(async () => {
      await ctx.logout();
    });

    expect(store.size).toBe(0);
    expect(api.post).toHaveBeenCalledWith('/api/v1/auth/logout');
  });
});
