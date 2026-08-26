import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';

const CookieConsentContext = createContext(null);

/**
 * Default consent object structure
 */
const DEFAULT_CONSENT = {
  essential_cookies: true,
  functional_cookies: false,
  analytics_cookies: false,
  marketing_cookies: false,
  // CCPA/CPRA opt-out from the sale or sharing of personal information. Distinct
  // from the cookie categories: it is a statutory right rather than a consent
  // choice, and a Global Privacy Control signal can set it without the UI.
  do_not_sell: false,
  consent_version: '1.0',
};

/**
 * Translate the context's consent shape into the API's request body.
 *
 * The API groups the categories under `preferences` and names them without the
 * `_cookies` suffix; `necessary` is server-enforced and never sent.
 */
function toApiPayload(consent, consentMethod) {
  return {
    preferences: {
      functional: Boolean(consent.functional_cookies),
      analytics: Boolean(consent.analytics_cookies),
      marketing: Boolean(consent.marketing_cookies),
      doNotSell: Boolean(consent.do_not_sell),
    },
    consentMethod,
  };
}

/**
 * Translate an API consent record back into the context's consent shape.
 *
 * Returns null when the payload has no preferences, so callers can tell an
 * absent record from one that genuinely denies every category.
 */
function fromApiConsent(data) {
  if (!data?.preferences) return null;
  return {
    essential_cookies: true,
    functional_cookies: Boolean(data.preferences.functional),
    analytics_cookies: Boolean(data.preferences.analytics),
    marketing_cookies: Boolean(data.preferences.marketing),
    do_not_sell: Boolean(data.preferences.doNotSell),
    consent_version: data.version ?? DEFAULT_CONSENT.consent_version,
  };
}

export function CookieConsentProvider({ children }) {
  const [consent, setConsent] = useState(null);
  const [showBanner, setShowBanner] = useState(false);
  const [showPreferences, setShowPreferences] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [consentId, setConsentId] = useState(null);

  // Load consent from localStorage or API on mount
  useEffect(() => {
    const loadConsent = async () => {
      try {
        setLoading(true);
        setError(null);

        // Get current policy version from server
        const policyResponse = await api.get('/api/v1/cookie/policy');
        const currentVersion = policyResponse.data?.version || '1.0';

        // Check localStorage for existing consent
        const storedConsent = localStorage.getItem('cookie_consent');

        if (storedConsent) {
          const parsedConsent = JSON.parse(storedConsent);

          // Check if consent is still valid (version matches)
          if (parsedConsent.consent_version === currentVersion) {
            setConsent(parsedConsent);
            setShowBanner(false);
          } else {
            // Version mismatch - show banner again
            setShowBanner(true);
          }
        } else {
          // No consent stored - first visit
          setShowBanner(true);
        }

        // The consent endpoint is public: it resolves an anonymous visitor via
        // the waddlebot_consent_id cookie, so this is not gated on a token.
        try {
          const userConsentResponse = await api.get('/api/v1/cookie');
          const serverConsent = fromApiConsent(userConsentResponse.data?.data);
          if (serverConsent) {
            setConsent(serverConsent);
            setConsentId(userConsentResponse.data?.data?.consentId ?? null);
            setShowBanner(serverConsent.consent_version !== currentVersion);
          }
        } catch (err) {
          console.warn('[CookieConsent] Load failed', { reason: err.message });
        }
      } catch (err) {
        console.error('Error loading cookie consent:', err);
        setError(err.message);
        // Default to showing banner on error
        setShowBanner(true);
      } finally {
        setLoading(false);
      }
    };

    loadConsent();
  }, []);

  /**
   * Persist a consent decision to the API.
   *
   * The endpoint is public, so anonymous visitors are recorded too — GDPR
   * Art. 7(1) requires being able to demonstrate consent, and the majority of
   * banner interactions are unauthenticated. A failure surfaces through `error`
   * rather than being swallowed: a consent record that silently failed to save
   * is indistinguishable from one that was never given.
   */
  const persistConsent = useCallback(async (newConsent, consentMethod) => {
    try {
      const response = await api.post(
        '/api/v1/cookie',
        toApiPayload(newConsent, consentMethod),
      );
      const saved = response.data?.data;
      if (saved?.consentId) {
        setConsentId(saved.consentId);
      }
      return true;
    } catch (err) {
      console.error('[CookieConsent] Save failed', { consentMethod, reason: err.message });
      setError('Your cookie preferences could not be saved. Please try again.');
      return false;
    }
  }, []);

  /**
   * Accept all cookie categories
   */
  const acceptAll = useCallback(async () => {
    try {
      const newConsent = {
        ...DEFAULT_CONSENT,
        ...consent,
        essential_cookies: true,
        functional_cookies: true,
        analytics_cookies: true,
        // "Accept all" is a cookie choice and does not revoke a CCPA opt-out;
        // sharing stays off while the opt-out stands.
        marketing_cookies: !consent?.do_not_sell,
        do_not_sell: Boolean(consent?.do_not_sell),
      };

      await persistConsent(newConsent, 'banner');

      // Save to localStorage
      localStorage.setItem('cookie_consent', JSON.stringify(newConsent));
      setConsent(newConsent);
      setShowBanner(false);
    } catch (err) {
      console.error('Error accepting all cookies:', err);
      setError(err.message);
    }
  }, [persistConsent, consent]);

  /**
   * Reject all non-essential cookies
   */
  const rejectNonEssential = useCallback(async () => {
    try {
      const newConsent = {
        ...DEFAULT_CONSENT,
        essential_cookies: true,
        functional_cookies: false,
        analytics_cookies: false,
        marketing_cookies: false,
      };

      await persistConsent(newConsent, 'banner');

      // Save to localStorage
      localStorage.setItem('cookie_consent', JSON.stringify(newConsent));
      setConsent(newConsent);
      setShowBanner(false);
    } catch (err) {
      console.error('Error rejecting non-essential cookies:', err);
      setError(err.message);
    }
  }, [persistConsent]);

  /**
   * Save custom preference selections
   */
  const savePreferences = useCallback(async (preferences) => {
    try {
      // Merge with default to ensure all fields are present
      const newConsent = {
        ...DEFAULT_CONSENT,
        ...preferences,
        essential_cookies: true, // Essential is always required
      };

      await persistConsent(newConsent, 'preferences');

      // Save to localStorage
      localStorage.setItem('cookie_consent', JSON.stringify(newConsent));
      setConsent(newConsent);
      setShowBanner(false);
      setShowPreferences(false);
    } catch (err) {
      console.error('Error saving preferences:', err);
      setError(err.message);
    }
  }, [persistConsent]);

  /**
   * Set the CCPA/CPRA "Do Not Sell or Share" opt-out.
   *
   * Opting out also turns marketing off, since that is the mechanism sharing
   * happens through — leaving it on would make the opt-out cosmetic.
   */
  const setDoNotSell = useCallback(async (optedOut) => {
    try {
      const newConsent = {
        ...DEFAULT_CONSENT,
        ...consent,
        essential_cookies: true,
        do_not_sell: Boolean(optedOut),
        marketing_cookies: optedOut ? false : Boolean(consent?.marketing_cookies),
      };

      await persistConsent(newConsent, 'do_not_sell');

      localStorage.setItem('cookie_consent', JSON.stringify(newConsent));
      setConsent(newConsent);
    } catch (err) {
      console.error('[CookieConsent] Opt-out failed', { reason: err.message });
      setError(err.message);
    }
  }, [consent, persistConsent]);

  /**
   * Open the preferences modal
   */
  const openPreferences = useCallback(() => {
    setShowPreferences(true);
  }, []);

  /**
   * Close the cookie banner
   */
  const closeBanner = useCallback(() => {
    setShowBanner(false);
  }, []);

  const value = {
    consent,
    showBanner,
    showPreferences,
    loading,
    error,
    consentId,
    acceptAll,
    rejectNonEssential,
    savePreferences,
    setDoNotSell,
    openPreferences,
    closeBanner,
    setShowPreferences,
  };

  return (
    <CookieConsentContext.Provider value={value}>
      {children}
    </CookieConsentContext.Provider>
  );
}

export function useCookieConsentContext() {
  const context = useContext(CookieConsentContext);
  if (!context) {
    throw new Error('useCookieConsentContext must be used within CookieConsentProvider');
  }
  return context;
}

export default CookieConsentContext;
