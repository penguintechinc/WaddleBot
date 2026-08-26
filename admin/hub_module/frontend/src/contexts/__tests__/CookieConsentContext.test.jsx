/**
 * Regression tests for cookie consent persistence.
 *
 * Consent used to never reach the server: the context posted its own shape
 * (`{analytics_cookies: true}`) while the API expects `{preferences: {analytics: true}}`,
 * so every save returned 400 — and the rejection was swallowed by a console.debug.
 * The banner looked like it worked while consent lived only in localStorage.
 *
 * GDPR Art. 7(1) requires being able to demonstrate that a subject consented,
 * which a record that was never written cannot do. These tests assert the wire
 * contract rather than the internal shape, because the internal shape was never
 * the thing that was broken.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';

import api from '../../services/api';
import { CookieConsentProvider, useCookieConsentContext } from '../CookieConsentContext';

vi.mock('../../services/api', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

/** Renders the provider and exposes its context value for assertions. */
function harness() {
  const captured = {};
  function Probe() {
    Object.assign(captured, useCookieConsentContext());
    return <div data-testid="ready" />;
  }
  render(
    <CookieConsentProvider>
      <Probe />
    </CookieConsentProvider>,
  );
  return captured;
}

const serverConsent = (preferences) => ({
  data: {
    success: true,
    data: {
      consentId: 'consent-abc',
      userId: null,
      preferences: { necessary: true, ...preferences },
      version: '1.0',
      consentedAt: '2026-08-26T00:00:00Z',
      expiresAt: null,
      requiresUpdate: false,
    },
  },
});

/**
 * An explicit in-memory localStorage.
 *
 * jsdom does not reliably expose one across Node majors — this suite passed on
 * Node 24 and failed on Node 26 with `localStorage` undefined — and a test that
 * depends on ambient browser storage is at the mercy of the runtime anyway.
 * Providing it here keeps the suite hermetic and the failure mode obvious.
 */
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
}

beforeEach(() => {
  installLocalStorage();
  api.get.mockImplementation((url) => {
    if (url === '/api/v1/cookie/policy') return Promise.resolve({ data: { version: '1.0' } });
    return Promise.resolve(serverConsent({ functional: false, analytics: false, marketing: false }));
  });
  api.post.mockResolvedValue(
    serverConsent({ functional: true, analytics: true, marketing: true }),
  );
});

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe('cookie consent persistence', () => {
  it('posts the API preferences shape, not the context shape', async () => {
    const ctx = harness();
    await screen.findByTestId('ready');

    await act(async () => {
      await ctx.acceptAll();
    });

    expect(api.post).toHaveBeenCalledWith('/api/v1/cookie', {
      preferences: { functional: true, analytics: true, marketing: true, doNotSell: false },
      consentMethod: 'banner',
    });

    // The old payload shape would have 400'd; assert it is gone for good.
    const [, body] = api.post.mock.calls[0];
    expect(body).not.toHaveProperty('analytics_cookies');
    expect(body.preferences).not.toHaveProperty('necessary');
  });

  it('records a rejection as an explicit denial, not as an absent record', async () => {
    const ctx = harness();
    await screen.findByTestId('ready');

    await act(async () => {
      await ctx.rejectNonEssential();
    });

    expect(api.post).toHaveBeenCalledWith('/api/v1/cookie', {
      preferences: { functional: false, analytics: false, marketing: false, doNotSell: false },
      consentMethod: 'banner',
    });
  });

  it('persists for anonymous visitors, who are most of the banner traffic', async () => {
    localStorage.removeItem('token');
    const ctx = harness();
    await screen.findByTestId('ready');

    await act(async () => {
      await ctx.acceptAll();
    });

    expect(api.post).toHaveBeenCalledTimes(1);
  });

  it('marks a custom selection with the preferences consent method', async () => {
    const ctx = harness();
    await screen.findByTestId('ready');

    await act(async () => {
      await ctx.savePreferences({ analytics_cookies: true, marketing_cookies: false });
    });

    expect(api.post).toHaveBeenCalledWith('/api/v1/cookie', {
      preferences: { functional: false, analytics: true, marketing: false, doNotSell: false },
      consentMethod: 'preferences',
    });
  });

  it('reads the server record back into the context shape', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/api/v1/cookie/policy') return Promise.resolve({ data: { version: '1.0' } });
      return Promise.resolve(
        serverConsent({ functional: true, analytics: false, marketing: false }),
      );
    });

    const ctx = harness();
    await waitFor(() => expect(ctx.consent).toBeTruthy());

    expect(ctx.consent).toMatchObject({
      essential_cookies: true,
      functional_cookies: true,
      analytics_cookies: false,
      marketing_cookies: false,
    });
    expect(ctx.consentId).toBe('consent-abc');
  });

  it('records a CCPA opt-out and turns sharing off with it', async () => {
    const ctx = harness();
    await screen.findByTestId('ready');

    await act(async () => {
      await ctx.setDoNotSell(true);
    });

    const [, body] = api.post.mock.calls[0];
    expect(body.preferences.doNotSell).toBe(true);
    // Marketing is the mechanism sharing happens through; leaving it on would
    // make the opt-out cosmetic.
    expect(body.preferences.marketing).toBe(false);
    expect(body.consentMethod).toBe('do_not_sell');
  });

  it('does not revoke a standing opt-out when the user later accepts all cookies', async () => {
    const ctx = harness();
    await screen.findByTestId('ready');

    await act(async () => {
      await ctx.setDoNotSell(true);
    });
    await act(async () => {
      await ctx.acceptAll();
    });

    const [, body] = api.post.mock.calls[1];
    // "Accept all" is a cookie choice; it is not consent to sale or sharing.
    expect(body.preferences.doNotSell).toBe(true);
    expect(body.preferences.marketing).toBe(false);
    expect(body.preferences.analytics).toBe(true);
  });

  it('surfaces a save failure instead of swallowing it', async () => {
    api.post.mockRejectedValue(new Error('Request failed with status code 400'));
    const ctx = harness();
    await screen.findByTestId('ready');

    await act(async () => {
      await ctx.acceptAll();
    });

    // The original defect was precisely that this stayed null while the banner
    // dismissed itself, leaving the user believing their choice was recorded.
    await waitFor(() => expect(ctx.error).toBeTruthy());
  });
});
