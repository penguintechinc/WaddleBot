import { useCookieConsentContext } from '../contexts/CookieConsentContext';

/**
 * Custom hook for managing cookie consent
 *
 * Returns consent state, helper functions, and preference management methods
 *
 * Example usage:
 *   const { hasConsent, acceptAll, loading } = useCookieConsent();
 *   if (hasConsent('analytics')) {
 *     // Load analytics scripts
 *   }
 */
export function useCookieConsent() {
  const context = useCookieConsentContext();

  /**
   * Check if a specific cookie category has been consented to
   *
   * @param {string} category - Cookie category to check
   *   - 'essential' or 'essential_cookies'
   *   - 'functional' or 'functional_cookies'
   *   - 'analytics' or 'analytics_cookies'
   *   - 'marketing' or 'marketing_cookies'
   * @returns {boolean} True if user has consented to this category
   */
  const hasConsent = (category) => {
    if (!context.consent) {
      return category === 'essential' || category === 'essential_cookies';
    }

    const categoryKey = category.endsWith('_cookies')
      ? category
      : `${category}_cookies`;

    // Essential cookies are always assumed to be consented
    if (categoryKey === 'essential_cookies') {
      return true;
    }

    return context.consent[categoryKey] === true;
  };

  /**
   * Check if any non-essential cookies have been consented to
   *
   * @returns {boolean} True if user has consented to any non-essential category
   */
  const hasAnyNonEssentialConsent = () => {
    if (!context.consent) {
      return false;
    }

    return (
      context.consent.functional_cookies === true ||
      context.consent.analytics_cookies === true ||
      context.consent.marketing_cookies === true
    );
  };

  /**
   * Check if all cookies have been accepted
   *
   * @returns {boolean} True if all categories are enabled
   */
  const hasAllConsents = () => {
    if (!context.consent) {
      return false;
    }

    return (
      context.consent.essential_cookies === true &&
      context.consent.functional_cookies === true &&
      context.consent.analytics_cookies === true &&
      context.consent.marketing_cookies === true
    );
  };

  /**
   * Get current preference for a category
   *
   * @param {string} category - Cookie category
   * @returns {boolean|null} Current preference or null if not loaded
   */
  const getConsentValue = (category) => {
    if (!context.consent) {
      return null;
    }

    const categoryKey = category.endsWith('_cookies')
      ? category
      : `${category}_cookies`;

    return context.consent[categoryKey] || false;
  };

  return {
    // State
    consent: context.consent,
    loading: context.loading,
    error: context.error,
    showBanner: context.showBanner,
    showPreferences: context.showPreferences,
    consentId: context.consentId,

    // Methods
    acceptAll: context.acceptAll,
    rejectNonEssential: context.rejectNonEssential,
    savePreferences: context.savePreferences,
    setDoNotSell: context.setDoNotSell,
    openPreferences: context.openPreferences,
    closeBanner: context.closeBanner,
    setShowPreferences: context.setShowPreferences,

    // Helper functions
    hasConsent,
    hasAnyNonEssentialConsent,
    hasAllConsents,
    getConsentValue,
  };
}

export default useCookieConsent;
