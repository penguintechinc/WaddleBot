/**
 * Regression test for the OAuth callback exchange-code handoff.
 *
 * `handleOAuthCallback` used to receive the session JWT directly (read off
 * the callback redirect's `?token=...` query string) and store it as-is.
 * The backend hotfix (hub_api/blueprints/v1/auth.py::oauth_callback) no
 * longer puts the JWT in the URL -- it redirects with a short-lived,
 * single-use opaque `code` instead, and the frontend must POST that code to
 * `/api/v1/auth/exchange` to get the real JWT back over the response body.
 * This pins that wire contract: the value passed in is a CODE, the value
 * persisted to localStorage is whatever `/exchange` returned, and the two
 * are never conflated.
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

  it('stores the JWT the exchange endpoint returned, never the code itself', async () => {
    api.post.mockResolvedValue({ data: { success: true, token: 'real-session-jwt' } });
    const ctx = harness();

    await act(async () => {
      await ctx.handleOAuthCallback('the-opaque-exchange-code');
    });

    expect(store.get('token')).toBe('real-session-jwt');
    expect(store.get('token')).not.toBe('the-opaque-exchange-code');
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
