/**
 * Tests for the consent banner.
 *
 * The banner was previously a mockup: it was never mounted, wrote to its own
 * `cookieConsent` localStorage key instead of the context's `cookie_consent`,
 * and its Customise button was a console.log. Consent was therefore only
 * reachable by navigating to /cookie-policy — there was no banner on first
 * visit at all.
 *
 * These tests pin it to the context, and pin the three properties that decide
 * whether a banner is compliant or decorative: refusing is as easy as
 * accepting, it cannot be dismissed without answering, and the CCPA opt-out is
 * present on it.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import CookieBanner from '../CookieBanner';
import * as consentHook from '../../hooks/useCookieConsent';

const actions = {
  acceptAll: vi.fn(),
  rejectNonEssential: vi.fn(),
  openPreferences: vi.fn(),
  setDoNotSell: vi.fn(),
};

function mountBanner({ showBanner = true, doNotSell = false } = {}) {
  vi.spyOn(consentHook, 'useCookieConsent').mockReturnValue({
    showBanner,
    consent: { do_not_sell: doNotSell },
    ...actions,
  });

  return render(
    <MemoryRouter>
      <CookieBanner />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('CookieBanner', () => {
  it('renders when the context asks for a decision', () => {
    mountBanner({ showBanner: true });
    expect(screen.getByTestId('cookie-banner')).toBeInTheDocument();
  });

  it('stays hidden once a decision exists', () => {
    mountBanner({ showBanner: false });
    expect(screen.queryByTestId('cookie-banner')).not.toBeInTheDocument();
  });

  it('routes every action through the consent context', () => {
    mountBanner();

    fireEvent.click(screen.getByTestId('banner-accept'));
    expect(actions.acceptAll).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('banner-reject'));
    expect(actions.rejectNonEssential).toHaveBeenCalledTimes(1);

    // Previously a console.log, so the Customise button did nothing at all.
    fireEvent.click(screen.getByTestId('banner-customize'));
    expect(actions.openPreferences).toHaveBeenCalledTimes(1);
  });

  it('offers the CCPA opt-out on the banner itself', () => {
    mountBanner({ doNotSell: false });

    const optOut = screen.getByTestId('banner-do-not-sell');
    expect(optOut).toHaveTextContent(/do not sell or share/i);
    expect(optOut).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(optOut);
    expect(actions.setDoNotSell).toHaveBeenCalledWith(true);
  });

  it('reflects a standing opt-out rather than re-offering it', () => {
    mountBanner({ doNotSell: true });
    const optOut = screen.getByTestId('banner-do-not-sell');
    expect(optOut).toHaveAttribute('aria-pressed', 'true');
    expect(optOut).toHaveTextContent(/opted out/i);
  });

  it('gives reject the same visual weight as accept', () => {
    mountBanner();
    const accept = screen.getByTestId('banner-accept');
    const reject = screen.getByTestId('banner-reject');

    // Refusing must be as easy as accepting. A filled Accept beside an outlined
    // Reject is the standard dark-pattern finding, so the classes must match.
    expect(reject.className).toBe(accept.className);
  });

  it('cannot be dismissed without answering', () => {
    mountBanner();
    // A close control would leave non-essential cookies neither consented nor
    // refused, and invites treating silence as agreement.
    expect(screen.queryByLabelText(/dismiss/i)).not.toBeInTheDocument();
  });

  it('does not write consent to its own localStorage key', () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem');
    mountBanner();

    fireEvent.click(screen.getByTestId('banner-accept'));

    // The old banner wrote 'cookieConsent', which nothing else read.
    const keys = setItem.mock.calls.map(([key]) => key);
    expect(keys).not.toContain('cookieConsent');
    setItem.mockRestore();
  });
});
