/**
 * Tests for the consent gate.
 *
 * The consent categories have recorded correctly since the persistence fix, but
 * nothing consumed them — there is no analytics SDK in this app yet. This hook
 * exists so that when one arrives it is gated by construction rather than by
 * remembering to check, and these tests pin the three behaviours that make that
 * true: it does not run before consent, it runs on grant, and it tears down on
 * withdrawal rather than lingering until the next page load.
 */
import { describe, expect, it, vi } from 'vitest';
import { act, render } from '@testing-library/react';

import { useConsentedEffect } from '../useConsentedEffect';
import * as consentHook from '../useCookieConsent';

/** Drives the hook with a controllable consent state. */
function setup({ analytics = false, loading = false } = {}) {
  const start = vi.fn();
  const stop = vi.fn();

  vi.spyOn(consentHook, 'useCookieConsent').mockReturnValue({
    loading,
    consent: analytics ? { analytics_cookies: true } : { analytics_cookies: false },
    hasConsent: (category) => category.startsWith('analytics') && analytics,
  });

  function Probe() {
    useConsentedEffect('analytics', () => {
      start();
      return stop;
    });
    return null;
  }

  const view = render(<Probe />);
  return { start, stop, view };
}

describe('useConsentedEffect', () => {
  it('does not run before consent is given', () => {
    const { start } = setup({ analytics: false });
    expect(start).not.toHaveBeenCalled();
  });

  it('does not run while the consent decision is still loading', () => {
    const { start } = setup({ analytics: true, loading: true });
    expect(start).not.toHaveBeenCalled();
  });

  it('runs once consent is granted', () => {
    const { start } = setup({ analytics: true });
    expect(start).toHaveBeenCalledTimes(1);
  });

  it('tears down when consent is withdrawn, not only on unmount', () => {
    const start = vi.fn();
    const stop = vi.fn();
    let granted = true;

    vi.spyOn(consentHook, 'useCookieConsent').mockImplementation(() => ({
      loading: false,
      consent: { analytics_cookies: granted },
      hasConsent: (category) => category.startsWith('analytics') && granted,
    }));

    function Probe() {
      useConsentedEffect('analytics', () => {
        start();
        return stop;
      });
      return null;
    }

    const { rerender } = render(<Probe />);
    expect(start).toHaveBeenCalledTimes(1);
    expect(stop).not.toHaveBeenCalled();

    // The user opens preferences and turns analytics off.
    granted = false;
    act(() => {
      rerender(<Probe />);
    });

    expect(stop).toHaveBeenCalledTimes(1);
    expect(start).toHaveBeenCalledTimes(1);
  });

  it('cleans up on unmount while consented', () => {
    const { stop, view } = setup({ analytics: true });
    expect(stop).not.toHaveBeenCalled();
    act(() => {
      view.unmount();
    });
    expect(stop).toHaveBeenCalledTimes(1);
  });

  it('refuses the essential category, which needs no gate', () => {
    vi.spyOn(consentHook, 'useCookieConsent').mockReturnValue({
      loading: false,
      consent: {},
      hasConsent: () => true,
    });

    function Probe() {
      useConsentedEffect('essential', () => {});
      return null;
    }

    // Rendering must throw rather than quietly treating essential as consented.
    expect(() => render(<Probe />)).toThrow(/essential/i);
  });
});
