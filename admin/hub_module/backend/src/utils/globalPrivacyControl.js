/**
 * Global Privacy Control (CCPA/CPRA opt-out signal).
 *
 * CPRA requires an opt-out preference signal to be treated as a valid request
 * to opt out of the sale or sharing of personal information. GPC sends that
 * signal as `Sec-GPC: 1`, and it must be honoured without asking the user to
 * repeat themselves in the UI.
 *
 * The signal is one-way on purpose: its absence means the user has not opted
 * out *by this mechanism*, not that they have opted in. Treating a missing
 * header as consent would turn every non-GPC browser into an opt-in.
 */

/** True when the request carries a Global Privacy Control opt-out signal. */
export function hasGlobalPrivacyControl(req) {
  const header = req?.headers?.['sec-gpc'];
  // The spec defines "1" as the only affirmative value.
  return header === '1' || header === 1;
}

/**
 * Apply a GPC signal to a set of consent preferences.
 *
 * Forces `doNotSell` on, and `marketing` off because marketing cookies are the
 * mechanism through which sharing happens here — honouring the opt-out while
 * leaving those enabled would be an opt-out in name only.
 *
 * Returns the preferences unchanged when no signal is present, so a user who
 * has explicitly opted in is never silently reset by a browser default.
 */
export function applyGlobalPrivacyControl(req, preferences) {
  if (!hasGlobalPrivacyControl(req)) {
    return { preferences, applied: false };
  }

  return {
    preferences: { ...preferences, doNotSell: true, marketing: false },
    applied: true,
  };
}

export default { hasGlobalPrivacyControl, applyGlobalPrivacyControl };
