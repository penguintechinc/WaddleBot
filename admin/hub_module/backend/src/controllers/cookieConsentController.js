/**
 * Cookie Consent Controller - GDPR Compliance
 * Manages cookie consent preferences and policy versions
 */
import { v4 as uuidv4 } from 'uuid';
import { query } from '../config/database.js';
import { errors } from '../middleware/errorHandler.js';
import { logger } from '../utils/logger.js';
import { applyGlobalPrivacyControl } from '../utils/globalPrivacyControl.js';
import { CookieConsentService } from '../services/cookieConsentService.js';

const service = new CookieConsentService();

/**
 * Get current user/session consent status
 * GET /api/v1/cookie-consent
 */
export async function getConsent(req, res, next) {
  try {
    const userId = req.user?.id || null;
    const consentId = req.cookies?.waddlebot_consent_id || null;

    if (!userId && !consentId) {
      // Return default consent for new visitors
      return res.json({
        success: true,
        data: {
          consentId: null,
          userId: null,
          preferences: applyGlobalPrivacyControl(req, {
            necessary: true,
            functional: false,
            analytics: false,
            marketing: false,
            doNotSell: false,
          }).preferences,
          version: process.env.COOKIE_CONSENT_VERSION || '1.0.0',
          consentedAt: null,
          expiresAt: null,
          requiresUpdate: false,
        },
      });
    }

    const consent = await service.getOrCreateConsent(userId, consentId);

    // A stored record predates this request, so a GPC signal sent now still has
    // to be reflected in what the client is told — otherwise the UI would show
    // sharing as permitted while the signal says otherwise.
    const { preferences, applied } = applyGlobalPrivacyControl(req, consent.preferences);

    res.json({
      success: true,
      data: { ...consent, preferences, gpcApplied: applied },
    });
  } catch (err) {
    logger.error('Error getting consent', { error: err.message });
    next(err);
  }
}

/**
 * Save or update consent preferences
 * POST /api/v1/cookie-consent
 */
export async function saveConsent(req, res, next) {
  try {
    const userId = req.user?.id || null;
    const { preferences, consentMethod = 'banner' } = req.body;
    const ipAddress = req.ip;
    const userAgent = req.headers['user-agent'];

    // Validate preferences
    if (!preferences || typeof preferences !== 'object') {
      return next(errors.badRequest('Invalid preferences object'));
    }

    // Necessary is always true
    const requested = {
      necessary: true,
      functional: Boolean(preferences.functional),
      analytics: Boolean(preferences.analytics),
      marketing: Boolean(preferences.marketing),
      doNotSell: Boolean(preferences.doNotSell),
    };

    // A GPC signal is itself a valid opt-out request under CPRA, so it wins over
    // whatever the form submitted — including a stale form rendered before the
    // signal was set.
    const { preferences: validated, applied: gpcApplied } =
      applyGlobalPrivacyControl(req, requested);

    // Get or create consent record
    const consentId = req.cookies?.waddlebot_consent_id || uuidv4();
    const consent = await service.saveConsent({
      userId,
      consentId,
      preferences: validated,
      consentMethod,
      ipAddress,
      userAgent,
    });

    // Set cookie with consent ID
    res.cookie('waddlebot_consent_id', consentId, {
      maxAge: 365 * 24 * 60 * 60 * 1000, // 12 months
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'Lax',
      path: '/',
      httpOnly: false,
    });

    logger.audit('CONSENT_SAVED', {
      userId,
      consentId,
      preferences: validated,
      method: gpcApplied ? 'global_privacy_control' : consentMethod,
      gpcApplied,
    });

    res.json({
      success: true,
      message: 'Cookie preferences saved successfully',
      data: consent,
    });
  } catch (err) {
    logger.error('Error saving consent', { error: err.message });
    next(err);
  }
}

/**
 * Update specific consent categories
 * PATCH /api/v1/cookie-consent/preferences
 */
export async function updatePreferences(req, res, next) {
  try {
    const userId = req.user?.id;
    const { preferences } = req.body;

    if (!userId) {
      return next(errors.unauthorized('Authentication required'));
    }

    if (!preferences || typeof preferences !== 'object') {
      return next(errors.badRequest('Invalid preferences object'));
    }

    // Necessary is always true
    const validated = {
      necessary: true,
      functional: Boolean(preferences.functional),
      analytics: Boolean(preferences.analytics),
      marketing: Boolean(preferences.marketing),
    };

    const updatedConsent = await service.updatePreferences(userId, validated);

    logger.audit('CONSENT_UPDATED', {
      userId,
      preferences: validated,
    });

    res.json({
      success: true,
      message: 'Preferences updated successfully',
      data: updatedConsent,
    });
  } catch (err) {
    logger.error('Error updating preferences', { error: err.message });
    next(err);
  }
}

/**
 * Revoke all non-essential cookies
 * DELETE /api/v1/cookie-consent
 */
export async function revokeConsent(req, res, next) {
  try {
    const userId = req.user?.id;

    if (!userId) {
      return next(errors.unauthorized('Authentication required'));
    }

    const revokedConsent = await service.revokeConsent(userId);

    logger.audit('CONSENT_REVOKED', { userId });

    res.json({
      success: true,
      message: 'All non-essential cookies revoked',
      data: revokedConsent,
    });
  } catch (err) {
    logger.error('Error revoking consent', { error: err.message });
    next(err);
  }
}

/**
 * Get current active cookie policy
 * GET /api/v1/cookie-policy
 */
export async function getCurrentPolicy(req, res, next) {
  try {
    const policy = await service.getCurrentPolicy();

    if (!policy) {
      return next(errors.notFound('No active cookie policy found'));
    }

    res.json({
      success: true,
      data: policy,
    });
  } catch (err) {
    logger.error('Error getting current policy', { error: err.message });
    next(err);
  }
}

/**
 * Get all policy versions
 * GET /api/v1/cookie-policy/history
 */
export async function getPolicyHistory(req, res, next) {
  try {
    const limit = Math.min(50, Math.max(1, parseInt(req.query.limit || '10', 10)));
    const offset = Math.max(0, parseInt(req.query.offset || '0', 10));

    const result = await query(
      `SELECT id, version, changes_summary, is_active, effective_date, created_at
       FROM cookie_policy_versions
       ORDER BY created_at DESC
       LIMIT $1 OFFSET $2`,
      [limit, offset]
    );

    const countResult = await query(
      'SELECT COUNT(*) as count FROM cookie_policy_versions'
    );

    res.json({
      success: true,
      data: {
        versions: result.rows,
        total: parseInt(countResult.rows[0]?.count || 0, 10),
        limit,
        offset,
      },
    });
  } catch (err) {
    logger.error('Error getting policy history', { error: err.message });
    next(err);
  }
}

/**
 * Get user's consent audit log
 * GET /api/v1/cookie-consent/audit
 */
export async function getAuditLog(req, res, next) {
  try {
    const userId = req.user?.id;

    if (!userId) {
      return next(errors.unauthorized('Authentication required'));
    }

    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '50', 10)));
    const offset = Math.max(0, parseInt(req.query.offset || '0', 10));

    const result = await query(
      `SELECT id, action, category, previous_value, new_value,
              consent_version, created_at
       FROM cookie_audit_log
       WHERE user_id = $1
       ORDER BY created_at DESC
       LIMIT $2 OFFSET $3`,
      [userId, limit, offset]
    );

    const countResult = await query(
      'SELECT COUNT(*) as count FROM cookie_audit_log WHERE user_id = $1',
      [userId]
    );

    logger.audit('AUDIT_LOG_VIEWED', { userId });

    res.json({
      success: true,
      data: {
        logs: result.rows,
        total: parseInt(countResult.rows[0]?.count || 0, 10),
        limit,
        offset,
      },
    });
  } catch (err) {
    logger.error('Error getting audit log', { error: err.message });
    next(err);
  }
}

/**
 * Create new policy version (Super admin only)
 * POST /api/v1/cookie-policy
 */
export async function createPolicyVersion(req, res, next) {
  try {
    const userId = req.user?.id;
    const { version, content, changesSummary } = req.body;

    if (!version || !content) {
      return next(errors.badRequest('Version and content are required'));
    }

    // Deactivate current active policy
    await query(
      'UPDATE cookie_policy_versions SET is_active = false WHERE is_active = true'
    );

    // Create new policy version
    const result = await query(
      `INSERT INTO cookie_policy_versions
       (version, content, changes_summary, is_active, effective_date, created_by)
       VALUES ($1, $2, $3, true, NOW(), $4)
       RETURNING id, version, is_active, effective_date, created_at`,
      [version, content, changesSummary || null, userId]
    );

    logger.audit('POLICY_VERSION_CREATED', {
      userId,
      version,
    });

    res.status(201).json({
      success: true,
      message: 'Policy version created and activated',
      data: result.rows[0],
    });
  } catch (err) {
    logger.error('Error creating policy version', { error: err.message });
    next(err);
  }
}

/**
 * Activate existing policy version (Super admin only)
 * PUT /api/v1/cookie-policy/:version/activate
 */
export async function activatePolicyVersion(req, res, next) {
  try {
    const userId = req.user?.id;
    const { version } = req.params;

    const policyResult = await query(
      'SELECT id FROM cookie_policy_versions WHERE version = $1',
      [version]
    );

    if (policyResult.rows.length === 0) {
      return next(errors.notFound('Policy version not found'));
    }

    // Deactivate all other versions
    await query(
      'UPDATE cookie_policy_versions SET is_active = false WHERE version != $1',
      [version]
    );

    // Activate requested version
    await query(
      'UPDATE cookie_policy_versions SET is_active = true WHERE version = $1',
      [version]
    );

    logger.audit('POLICY_VERSION_ACTIVATED', {
      userId,
      version,
    });

    res.json({
      success: true,
      message: 'Policy version activated',
    });
  } catch (err) {
    logger.error('Error activating policy version', { error: err.message });
    next(err);
  }
}

export default {
  getConsent,
  saveConsent,
  updatePreferences,
  revokeConsent,
  getCurrentPolicy,
  getPolicyHistory,
  getAuditLog,
  createPolicyVersion,
  activatePolicyVersion,
};
