/**
 * Cookie Consent Service
 * Business logic for cookie consent management and GDPR compliance
 */
import { v4 as uuidv4 } from 'uuid';
import { query } from '../config/database.js';
import { logger } from '../utils/logger.js';

export class CookieConsentService {
  /**
   * Get or create consent record for user/session
   */
  async getOrCreateConsent(userId, consentId) {
    try {
      let result;

      if (userId) {
        // Find by user ID
        result = await query(
          `SELECT id, user_id, consent_id, preferences, consent_version,
                  consented_at, updated_at, expires_at
           FROM cookie_consent
           WHERE user_id = $1
           ORDER BY updated_at DESC
           LIMIT 1`,
          [userId]
        );
      } else if (consentId) {
        // Find by consent ID (anonymous user)
        result = await query(
          `SELECT id, user_id, consent_id, preferences, consent_version,
                  consented_at, updated_at, expires_at
           FROM cookie_consent
           WHERE consent_id = $1
           ORDER BY updated_at DESC
           LIMIT 1`,
          [consentId]
        );
      }

      if (result && result.rows.length > 0) {
        const row = result.rows[0];
        const prefs = typeof row.preferences === 'string'
          ? JSON.parse(row.preferences)
          : row.preferences;

        return {
          consentId: row.consent_id,
          userId: row.user_id,
          preferences: prefs,
          version: row.consent_version,
          consentedAt: row.consented_at,
          expiresAt: row.expires_at,
          updatedAt: row.updated_at,
          requiresUpdate: this.checkPolicyUpdate(row.consent_version),
        };
      }

      // Return default for new user
      return {
        consentId: null,
        userId: null,
        preferences: {
          necessary: true,
          functional: false,
          analytics: false,
          marketing: false,
          doNotSell: false,
        },
        version: process.env.COOKIE_CONSENT_VERSION || '1.0.0',
        consentedAt: null,
        expiresAt: null,
        requiresUpdate: false,
      };
    } catch (err) {
      logger.error('Error getting consent', { error: err.message });
      throw err;
    }
  }

  /**
   * Save new consent record
   */
  async saveConsent(options) {
    try {
      const {
        userId,
        consentId,
        preferences,
        consentMethod,
        ipAddress,
        userAgent,
      } = options;

      const version = process.env.COOKIE_CONSENT_VERSION || '1.0.0';
      const expiresAt = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000); // 12 months

      // Generate new consent ID if not provided
      const finalConsentId = consentId || uuidv4();

      // Insert new consent record
      const result = await query(
        `INSERT INTO cookie_consent
         (user_id, consent_id, preferences, consent_version, consent_method,
          ip_address, user_agent, consented_at, updated_at, expires_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW(), $8)
         ON CONFLICT (consent_id) DO UPDATE
         SET user_id = $1, preferences = $3, updated_at = NOW()
         RETURNING id, consent_id, user_id, preferences, consent_version,
                   consented_at, updated_at, expires_at`,
        [
          userId,
          finalConsentId,
          JSON.stringify(preferences),
          version,
          consentMethod,
          ipAddress,
          userAgent,
          expiresAt,
        ]
      );

      const row = result.rows[0];
      const prefs = typeof row.preferences === 'string'
        ? JSON.parse(row.preferences)
        : row.preferences;

      // Log to audit trail
      await this.logAuditEvent({
        consentId: row.consent_id,
        userId: row.user_id,
        action: 'ACCEPT',
        preferences,
        version,
        ipAddress,
        userAgent,
      });

      return {
        consentId: row.consent_id,
        userId: row.user_id,
        preferences: prefs,
        version: row.consent_version,
        consentedAt: row.consented_at,
        expiresAt: row.expires_at,
        updatedAt: row.updated_at,
      };
    } catch (err) {
      logger.error('Error saving consent', { error: err.message });
      throw err;
    }
  }

  /**
   * Update specific preferences for authenticated user
   */
  async updatePreferences(userId, preferences) {
    try {
      // Get current preferences
      const currentResult = await query(
        `SELECT consent_id, preferences FROM cookie_consent
         WHERE user_id = $1
         ORDER BY updated_at DESC LIMIT 1`,
        [userId]
      );

      if (currentResult.rows.length === 0) {
        throw new Error('No consent record found for user');
      }

      const row = currentResult.rows[0];
      const consentId = row.consent_id;
      const previousPrefs = typeof row.preferences === 'string'
        ? JSON.parse(row.preferences)
        : row.preferences;

      // Update consent record
      const updateResult = await query(
        `UPDATE cookie_consent
         SET preferences = $1, updated_at = NOW()
         WHERE user_id = $2
         RETURNING id, consent_id, user_id, preferences, consent_version,
                   consented_at, updated_at, expires_at`,
        [JSON.stringify(preferences), userId]
      );

      const updatedRow = updateResult.rows[0];
      const updatedPrefs = typeof updatedRow.preferences === 'string'
        ? JSON.parse(updatedRow.preferences)
        : updatedRow.preferences;

      // Log each category change
      const version = process.env.COOKIE_CONSENT_VERSION || '1.0.0';
      const categories = ['functional', 'analytics', 'marketing'];

      for (const category of categories) {
        if (previousPrefs[category] !== preferences[category]) {
          await this.logAuditEvent({
            consentId,
            userId,
            action: 'UPDATE',
            category,
            previousValue: previousPrefs[category],
            newValue: preferences[category],
            version,
          });
        }
      }

      return {
        consentId: updatedRow.consent_id,
        userId: updatedRow.user_id,
        preferences: updatedPrefs,
        version: updatedRow.consent_version,
        consentedAt: updatedRow.consented_at,
        expiresAt: updatedRow.expires_at,
        updatedAt: updatedRow.updated_at,
      };
    } catch (err) {
      logger.error('Error updating preferences', { error: err.message });
      throw err;
    }
  }

  /**
   * Revoke all non-essential cookies for user
   */
  async revokeConsent(userId) {
    try {
      const revokedPreferences = {
        necessary: true,
        functional: false,
        analytics: false,
        marketing: false,
      };

      // Get current consent record
      const currentResult = await query(
        `SELECT consent_id FROM cookie_consent
         WHERE user_id = $1
         ORDER BY updated_at DESC LIMIT 1`,
        [userId]
      );

      if (currentResult.rows.length === 0) {
        throw new Error('No consent record found for user');
      }

      const consentId = currentResult.rows[0].consent_id;

      // Update to revoked state
      const updateResult = await query(
        `UPDATE cookie_consent
         SET preferences = $1, updated_at = NOW()
         WHERE user_id = $2
         RETURNING id, consent_id, user_id, preferences, consent_version,
                   consented_at, updated_at, expires_at`,
        [JSON.stringify(revokedPreferences), userId]
      );

      const row = updateResult.rows[0];

      // Log revocation
      const version = process.env.COOKIE_CONSENT_VERSION || '1.0.0';
      await this.logAuditEvent({
        consentId,
        userId,
        action: 'REVOKE',
        version,
      });

      return {
        consentId: row.consent_id,
        userId: row.user_id,
        preferences: revokedPreferences,
        version: row.consent_version,
        updatedAt: row.updated_at,
      };
    } catch (err) {
      logger.error('Error revoking consent', { error: err.message });
      throw err;
    }
  }

  /**
   * Get current active cookie policy
   */
  async getCurrentPolicy() {
    try {
      const result = await query(
        `SELECT id, version, content, changes_summary, is_active,
                effective_date, created_at
         FROM cookie_policy_versions
         WHERE is_active = true
         LIMIT 1`
      );

      if (result.rows.length === 0) {
        return null;
      }

      return result.rows[0];
    } catch (err) {
      logger.error('Error getting current policy', { error: err.message });
      throw err;
    }
  }

  /**
   * Check if user needs to update to new policy version
   */
  checkPolicyUpdate(consentVersion) {
    const currentVersion = process.env.COOKIE_CONSENT_VERSION || '1.0.0';
    return consentVersion !== currentVersion;
  }

  /**
   * Check if user has consented to specific category
   */
  async hasConsent(userId, consentId, category) {
    try {
      let result;

      if (userId) {
        result = await query(
          `SELECT preferences FROM cookie_consent
           WHERE user_id = $1
           ORDER BY updated_at DESC LIMIT 1`,
          [userId]
        );
      } else if (consentId) {
        result = await query(
          `SELECT preferences FROM cookie_consent
           WHERE consent_id = $1
           ORDER BY updated_at DESC LIMIT 1`,
          [consentId]
        );
      } else {
        return false;
      }

      if (result.rows.length === 0) {
        return false;
      }

      const prefs = typeof result.rows[0].preferences === 'string'
        ? JSON.parse(result.rows[0].preferences)
        : result.rows[0].preferences;

      return Boolean(prefs[category]);
    } catch (err) {
      logger.error('Error checking consent', { error: err.message });
      return false;
    }
  }

  /**
   * Log consent action to audit trail
   */
  async logAuditEvent(options) {
    try {
      const {
        consentId,
        userId,
        action,
        category,
        previousValue,
        newValue,
        version,
        ipAddress,
        userAgent,
      } = options;

      await query(
        `INSERT INTO cookie_audit_log
         (consent_id, user_id, action, category, previous_value, new_value,
          consent_version, ip_address, user_agent, created_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())`,
        [
          consentId,
          userId || null,
          action,
          category || null,
          previousValue !== undefined ? previousValue : null,
          newValue !== undefined ? newValue : null,
          version,
          ipAddress || null,
          userAgent || null,
        ]
      );
    } catch (err) {
      logger.error('Error logging audit event', { error: err.message });
      // Don't throw - audit logging failure shouldn't break main flow
    }
  }

  /**
   * Clean up expired consent records (scheduled task)
   */
  async cleanupExpiredConsent() {
    try {
      const result = await query(
        `DELETE FROM cookie_consent
         WHERE expires_at < NOW()
         RETURNING id, consent_id`
      );

      const deletedCount = result.rows.length;

      if (deletedCount > 0) {
        logger.system('CONSENT_CLEANUP', {
          deletedCount,
        });

        // Log cleanup to audit
        for (const row of result.rows) {
          await this.logAuditEvent({
            consentId: row.consent_id,
            action: 'EXPIRE',
            version: process.env.COOKIE_CONSENT_VERSION || '1.0.0',
          });
        }
      }

      return deletedCount;
    } catch (err) {
      logger.error('Error cleaning up expired consent', { error: err.message });
      throw err;
    }
  }

  /**
   * Get consent statistics for admin dashboard
   */
  async getConsentStats(filters = {}) {
    try {
      const timeRange = filters.timeRange || '30 days';

      const result = await query(
        `SELECT
           COUNT(DISTINCT consent_id) as total_consents,
           SUM(CASE WHEN preferences->>'functional' = 'true' THEN 1 ELSE 0 END) as functional_accepted,
           SUM(CASE WHEN preferences->>'analytics' = 'true' THEN 1 ELSE 0 END) as analytics_accepted,
           SUM(CASE WHEN preferences->>'marketing' = 'true' THEN 1 ELSE 0 END) as marketing_accepted,
           (SELECT COUNT(*) FROM cookie_audit_log WHERE action = 'REVOKE'
            AND created_at > NOW() - INTERVAL $1) as revocations
         FROM cookie_consent
         WHERE consented_at > NOW() - INTERVAL $2`,
        [timeRange, timeRange]
      );

      return result.rows[0];
    } catch (err) {
      logger.error('Error getting consent stats', { error: err.message });
      throw err;
    }
  }
}

export default CookieConsentService;
