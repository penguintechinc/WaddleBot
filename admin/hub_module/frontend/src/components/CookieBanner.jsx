import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { useCookieConsent } from '../hooks/useCookieConsent';

/**
 * CookieBanner Component
 *
 * The first-visit consent surface. Reads and writes through the cookie consent
 * context, so a choice made here is recorded server-side rather than only in
 * this browser.
 *
 * Three deliberate choices, each with a compliance reason:
 *
 * - Accept and Reject have identical visual weight. Refusing has to be as easy
 *   as accepting; a prominent Accept beside a muted Reject is the standard
 *   dark-pattern finding.
 * - There is no dismiss control. A banner that can be closed without answering
 *   leaves non-essential cookies neither consented nor refused, and invites
 *   treating silence as agreement.
 * - "Do Not Sell or Share" sits here rather than only on a privacy page,
 *   because CCPA/CPRA expects it to be conspicuous on the pages a consumer
 *   actually lands on.
 */
function CookieBanner() {
  const {
    showBanner,
    consent,
    acceptAll,
    rejectNonEssential,
    openPreferences,
    setDoNotSell,
  } = useCookieConsent();

  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    if (!showBanner) {
      setIsAnimating(false);
      return undefined;
    }
    const timer = setTimeout(() => setIsAnimating(true), 50);
    return () => clearTimeout(timer);
  }, [showBanner]);

  if (!showBanner) {
    return null;
  }

  const optedOut = Boolean(consent?.do_not_sell);

  const actionClasses =
    'px-4 py-2 text-sm font-medium rounded-lg bg-navy-800 border border-navy-600 ' +
    'text-sky-100 hover:bg-navy-700 hover:border-navy-500 transition-colors ' +
    'focus:outline-none focus:ring-2 focus:ring-sky-400 focus:ring-offset-2 ' +
    'focus:ring-offset-navy-900 whitespace-nowrap';

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 z-50 transition-transform duration-300 ${
        isAnimating ? 'translate-y-0' : 'translate-y-full'
      }`}
      role="region"
      aria-label="Cookie Consent Banner"
      aria-live="polite"
      data-testid="cookie-banner"
    >
      <div className="bg-navy-900 border-t border-navy-700 shadow-2xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row gap-4 md:gap-6">
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-sky-100 mb-2">Cookie Preferences</h2>
              <p className="text-sm text-navy-300 leading-relaxed">
                We use cookies to enhance your experience. Essential cookies are required for
                the site to function. You can customise your preferences, accept all, or
                reject everything non-essential.{' '}
                <Link
                  to="/cookie-policy"
                  className="text-sky-400 hover:text-sky-300 underline transition-colors"
                >
                  Learn more about our cookie policy
                </Link>
              </p>

              <button
                type="button"
                onClick={() => setDoNotSell(!optedOut)}
                aria-pressed={optedOut}
                data-testid="banner-do-not-sell"
                className="mt-3 text-sm text-gold-400 underline hover:text-gold-300 transition-colors focus:outline-none focus:ring-2 focus:ring-sky-400 rounded"
              >
                {optedOut
                  ? 'You have opted out of the sale or sharing of your personal information'
                  : 'Do Not Sell or Share My Personal Information'}
              </button>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 sm:gap-2 md:items-end md:flex-shrink-0">
              <button
                type="button"
                onClick={rejectNonEssential}
                className={actionClasses}
                data-testid="banner-reject"
                aria-label="Reject non-essential cookies"
              >
                Reject Non-Essential
              </button>

              <button
                type="button"
                onClick={openPreferences}
                className={`${actionClasses} border-sky-500 text-sky-400 hover:border-sky-400`}
                data-testid="banner-customize"
                aria-label="Customise cookie preferences"
              >
                Customise
              </button>

              <button
                type="button"
                onClick={acceptAll}
                className={actionClasses}
                data-testid="banner-accept"
                aria-label="Accept all cookies"
              >
                Accept All
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CookieBanner;
