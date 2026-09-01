/**
 * Data Privacy Controller - GDPR data subject rights and CCPA/CPRA opt-out.
 *
 * Art. 15 access and Art. 20 portability: exportUserData.
 * Art. 16 rectification: profileController.updateMyProfile (PUT /user/profile).
 * Art. 17 erasure: requestDataDeletion.
 *
 * Erasure retains, on legitimate interest: user ID, linked identities (account
 * reclaim), reputation scores/events (anti-gaming, explicitly disclosed).
 * Retained data is still personal data, so the export discloses it.
 */
import bcrypt from 'bcrypt';
import { query, transaction } from '../config/database.js';
import { logger } from '../utils/logger.js';
import { errors } from '../middleware/errorHandler.js';
import { collectUserData } from '../utils/userDataExport.js';

/**
 * DELETE /api/v1/user/me/data
 * Anonymize and delete personal data for the authenticated user.
 */
export async function requestDataDeletion(req, res, next) {
  const userId = req.user.userId;

  try {
    // Check if already deleted
    const userCheck = await query(
      'SELECT email, password_hash FROM hub_users WHERE id = $1',
      [userId]
    );

    if (!userCheck.rows.length) {
      return next(errors.notFound('User not found'));
    }

    const user = userCheck.rows[0];
    const alreadyDeleted = user.email && user.email.startsWith(`deleted_${userId}@`);
    if (alreadyDeleted) {
      return res.json({ success: true, already_deleted: true });
    }

    // Require password confirmation if user has a password
    if (user.password_hash) {
      const { password } = req.body;
      if (!password) {
        return next(errors.badRequest('Password confirmation required'));
      }
      const valid = await bcrypt.compare(password, user.password_hash);
      if (!valid) {
        return next(errors.unauthorized('Password confirmation failed'));
      }
    }

    // GDPR deletion transaction
    const deletionCounts = {};
    try {
      await transaction(async (client) => {
        // 1. Delete profile PII
        const profiles = await client.query('DELETE FROM hub_user_profiles WHERE hub_user_id = $1', [userId]);
        deletionCounts.profiles = profiles.rowCount;

        // 2. Delete sessions
        const sessions = await client.query('DELETE FROM hub_sessions WHERE user_id = $1', [userId]);
        deletionCounts.sessions = sessions.rowCount;

        // 3. Delete temp passwords
        const tempPw = await client.query(
          'DELETE FROM hub_temp_passwords WHERE user_identifier = (SELECT email FROM hub_users WHERE id = $1)',
          [userId]
        );
        deletionCounts.temp_passwords = tempPw.rowCount;

        // 4. Delete passkeys
        const passkeys = await client.query('DELETE FROM user_passkeys WHERE user_id = $1', [userId]);
        deletionCounts.passkeys = passkeys.rowCount;

        // 5. Delete activity data
        const messages = await client.query('DELETE FROM activity_message_events WHERE hub_user_id = $1', [userId]);
        deletionCounts.message_events = messages.rowCount;

        const watchSessions = await client.query('DELETE FROM activity_watch_sessions WHERE hub_user_id = $1', [userId]);
        deletionCounts.watch_sessions = watchSessions.rowCount;

        // 6. Anonymize hub_users in-place (retain row for FK integrity)
        await client.query(
          `UPDATE hub_users SET
             email = $1,
             username = $2,
             display_name = NULL,
             password_hash = NULL,
             avatar_url = NULL,
             email_verification_token = NULL,
             password_reset_token = NULL,
             is_active = FALSE,
             updated_at = NOW()
           WHERE id = $3`,
          [`deleted_${userId}@deleted.waddlebot`, `deleted_${userId}`, userId]
        );
        deletionCounts.hub_users_anonymized = 1;
      });

      // Audit record (outside transaction — always write even if tx succeeded)
      await query(
        `INSERT INTO data_deletion_requests
           (hub_user_id, requested_at, completed_at, status, deletion_scope)
         VALUES ($1, NOW(), NOW(), 'completed', $2)`,
        [userId, JSON.stringify(deletionCounts)]
      );

      logger.audit('Data deletion completed', {
        user: userId,
        action: 'data_deletion',
        result: 'success',
        community: 'platform',
      });

      return res.json({ success: true, deleted: true });

    } catch (txErr) {
      // Transaction failed — record failure
      await query(
        `INSERT INTO data_deletion_requests
           (hub_user_id, requested_at, status, error_detail)
         VALUES ($1, NOW(), 'failed', $2)`,
        [userId, txErr.message]
      ).catch(() => {}); // Don't mask original error

      throw txErr;
    }

  } catch (err) {
    logger.error('Data deletion failed', { userId, error: err.message });
    next(err);
  }
}


/**
 * GET /api/v1/user/me/data
 * Export the authenticated user's personal data (GDPR Art. 15 and Art. 20).
 *
 * Served as JSON so it satisfies portability's "structured, commonly used and
 * machine-readable" requirement rather than access alone.
 */
export async function exportUserData(req, res, next) {
  const userId = req.user.userId;

  try {
    const exists = await query('SELECT id FROM hub_users WHERE id = $1', [userId]);
    if (!exists.rows.length) {
      return next(errors.notFound('User not found'));
    }

    const { data, failures } = await collectUserData(query, userId);

    logger.audit('Data export completed', {
      user: userId,
      action: 'data_export',
      result: failures.length ? 'partial' : 'success',
      community: 'platform',
    });

    res.setHeader('Content-Disposition', `attachment; filename="waddles-data-${userId}.json"`);
    return res.json({
      success: true,
      exported_at: new Date().toISOString(),
      subject_id: userId,
      data,
      ...(failures.length ? { incomplete: failures } : {}),
    });
  } catch (err) {
    logger.error('Data export failed', { userId, error: err.message });
    next(err);
  }
}
