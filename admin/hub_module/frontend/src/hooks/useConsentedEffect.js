import { useEffect, useRef } from 'react';

import { useCookieConsent } from './useCookieConsent';

/**
 * Run an effect only while the user consents to a cookie category.
 *
 * This is the required path for anything non-essential — analytics, marketing
 * pixels, session recording, third-party embeds. Calling such an SDK directly
 * bypasses consent, and the usual way that happens is not malice but ordering:
 * an SDK initialised at module import runs before the banner is even rendered.
 *
 * The effect's cleanup runs when consent is withdrawn, not only on unmount, so
 * a user moving from "accept all" to "reject" actually tears the integration
 * down rather than leaving it running until the next reload.
 *
 * Nothing runs while consent is still loading, and an unknown or absent
 * decision is treated as refusal — the gate fails closed.
 *
 * @param {string} category - 'analytics', 'marketing', or 'functional'.
 *   'essential' is rejected: essential work needs no gate, and routing it
 *   through one implies a consent decision that is never actually asked.
 * @param {() => (void | (() => void))} setup - Runs on consent. May return a
 *   cleanup function, which runs on withdrawal or unmount.
 */
export function useConsentedEffect(category, setup) {
  const { hasConsent, loading } = useCookieConsent();

  if (category === 'essential' || category === 'essential_cookies') {
    throw new Error(
      'useConsentedEffect is for non-essential categories; essential work needs no consent gate',
    );
  }

  const granted = !loading && hasConsent(category);
  const setupRef = useRef(setup);
  setupRef.current = setup;

  useEffect(() => {
    if (!granted) return undefined;

    const cleanup = setupRef.current();
    return typeof cleanup === 'function' ? cleanup : undefined;
  }, [granted]);
}

export default useConsentedEffect;
