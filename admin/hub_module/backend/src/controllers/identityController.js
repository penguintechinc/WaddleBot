/**
 * Identity Controller - Cross-platform identity linking
 * Allows users to link multiple platform accounts (Discord, Twitch, Slack)
 * to their hub account for unified identity management.
 */
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import { query, transaction } from '../config/database.js';
import { config } from '../config/index.js';
import { errors } from '../middleware/errorHandler.js';
import { logger } from '../utils/logger.js';

/**
 * Get linked identities for authenticated user
 * GET /api/v1/user/identities
 */
export async function getLinkedIdentities(req, res, next) {
  try {
    if (!req.user) {
      return next(errors.unauthorized());
    }

    // Get hub user ID from platform identity
    const hubUserId = await getOrCreateHubUser(req.user);

    // Get all linked identities for this hub user
    const result = await query(
      `SELECT id, platform, platform_user_id, platform_username,
              avatar_url, is_primary, linked_at, last_used
       FROM hub_user_identities
       WHERE hub_user_id = $1
       ORDER BY is_primary DESC, linked_at DESC`,
      [hubUserId]
    );

    logger.audit('Listed linked identities', {
      hubUserId,
      username: req.user.username,
      identityCount: result.rows.length,
    });

    res.json({
      success: true,
      identities: result.rows.map(row => ({
        id: row.id,
        platform: row.platform,
        platformUserId: row.platform_user_id,
        platformUsername: row.platform_username,
        avatarUrl: row.avatar_url,
        isPrimary: row.is_primary,
        linkedAt: row.linked_at,
        lastUsed: row.last_used,
      })),
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get primary identity for authenticated user
 * GET /api/v1/user/identities/primary
 */
export async function getPrimaryIdentity(req, res, next) {
  try {
    if (!req.user) {
      return next(errors.unauthorized());
    }

    const hubUserId = await getOrCreateHubUser(req.user);

    const result = await query(
      `SELECT id, platform, platform_user_id, platform_username,
              avatar_url, linked_at, last_used
       FROM hub_user_identities
       WHERE hub_user_id = $1 AND is_primary = true
       LIMIT 1`,
      [hubUserId]
    );

    if (result.rows.length === 0) {
      return res.json({ success: true, identity: null });
    }

    const row = result.rows[0];
    res.json({
      success: true,
      identity: {
        id: row.id,
        platform: row.platform,
        platformUserId: row.platform_user_id,
        platformUsername: row.platform_username,
        avatarUrl: row.avatar_url,
        linkedAt: row.linked_at,
        lastUsed: row.last_used,
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Set primary identity
 * PUT /api/v1/user/identities/primary
 * Body: { platform }
 */
export async function setPrimaryIdentity(req, res, next) {
  try {
    if (!req.user) {
      return next(errors.unauthorized());
    }

    const { platform } = req.body;

    if (!platform) {
      return next(errors.badRequest('Platform required'));
    }

    const hubUserId = await getOrCreateHubUser(req.user);

    // Verify the identity exists and belongs to this user
    const checkResult = await query(
      `SELECT id FROM hub_user_identities
       WHERE hub_user_id = $1 AND platform = $2`,
      [hubUserId, platform]
    );

    if (checkResult.rows.length === 0) {
      return next(errors.notFound('Identity not found'));
    }

    // Update primary status in a transaction
    await transaction(async (client) => {
      // Clear all primary flags for this user
      await client.query(
        'UPDATE hub_user_identities SET is_primary = false WHERE hub_user_id = $1',
        [hubUserId]
      );

      // Set new primary
      await client.query(
        'UPDATE hub_user_identities SET is_primary = true WHERE hub_user_id = $1 AND platform = $2',
        [hubUserId, platform]
      );
    });

    logger.audit('Primary identity updated', {
      hubUserId,
      username: req.user.username,
      platform,
    });

    res.json({ success: true, message: 'Primary identity updated' });
  } catch (err) {
    next(err);
  }
}

/**
 * Start OAuth flow for identity linking
 * POST /api/v1/user/identities/link/:platform
 */
export async function startIdentityLink(req, res, next) {
  try {
    if (!req.user) {
      return next(errors.unauthorized());
    }

    const { platform } = req.params;
    const validPlatforms = ['discord', 'twitch', 'slack'];

    if (!validPlatforms.includes(platform)) {
      return next(errors.badRequest('Invalid platform'));
    }

    // Check if user already has this platform linked
    const hubUserId = await getOrCreateHubUser(req.user);
    const existingResult = await query(
      'SELECT id FROM hub_user_identities WHERE hub_user_id = $1 AND platform = $2',
      [hubUserId, platform]
    );

    if (existingResult.rows.length > 0) {
      return next(errors.badRequest(`${platform} account already linked`));
    }

    // Generate state token with hub user ID for verification
    const state = Buffer.from(JSON.stringify({
      hubUserId,
      linkingFlow: true,
      timestamp: Date.now(),
      nonce: uuidv4(),
    })).toString('base64');

    const redirectUri = `${config.identity.callbackBaseUrl}/api/v1/user/identities/link/${platform}/callback`;

    // Get OAuth URL from Identity Core
    const response = await axios.get(
      `${config.identity.apiUrl}/auth/oauth/${platform}/authorize`,
      { params: { redirect_uri: redirectUri, state } }
    );

    logger.auth('Identity linking OAuth flow started', {
      platform,
      hubUserId,
      username: req.user.username,
    });

    res.json({
      success: true,
      authorizeUrl: response.data.authorize_url,
      state,
    });
  } catch (err) {
    logger.error('Identity linking start error', { error: err.message });
    next(err);
  }
}

/**
 * OAuth callback for identity linking
 * GET /api/v1/user/identities/link/:platform/callback
 */
export async function identityLinkCallback(req, res, next) {
  try {
    const { platform } = req.params;
    const { code, state } = req.query;
    const validPlatforms = ['discord', 'twitch', 'slack'];

    if (!validPlatforms.includes(platform)) {
      return res.redirect(`${config.cors.origin}/settings/identities?error=invalid_platform`);
    }

    if (!code || !state) {
      return res.redirect(`${config.cors.origin}/settings/identities?error=missing_params`);
    }

    // Decode and verify state
    let stateData;
    try {
      stateData = JSON.parse(Buffer.from(state, 'base64').toString());
    } catch {
      return res.redirect(`${config.cors.origin}/settings/identities?error=invalid_state`);
    }

    if (!stateData.linkingFlow || !stateData.hubUserId) {
      return res.redirect(`${config.cors.origin}/settings/identities?error=invalid_state`);
    }

    // Verify state is recent (within 10 minutes)
    if (Date.now() - stateData.timestamp > 10 * 60 * 1000) {
      return res.redirect(`${config.cors.origin}/settings/identities?error=state_expired`);
    }

    const hubUserId = stateData.hubUserId;
    const redirectUri = `${config.identity.callbackBaseUrl}/api/v1/user/identities/link/${platform}/callback`;

    // Exchange code with Identity Core
    const response = await axios.post(
      `${config.identity.apiUrl}/auth/oauth/${platform}/callback`,
      { code, redirect_uri: redirectUri, state }
    );

    const userData = response.data.user;

    // Check if this platform account is already linked to another user
    const existingLink = await query(
      'SELECT hub_user_id FROM hub_user_identities WHERE platform = $1 AND platform_user_id = $2',
      [platform, userData.id]
    );

    if (existingLink.rows.length > 0) {
      if (existingLink.rows[0].hub_user_id !== hubUserId) {
        logger.authz('Identity link failed - already linked to another user', {
          platform,
          platformUserId: userData.id,
          attemptedHubUserId: hubUserId,
          existingHubUserId: existingLink.rows[0].hub_user_id,
        });
        return res.redirect(`${config.cors.origin}/settings/identities?error=already_linked`);
      }
      // Already linked to this user, just redirect
      return res.redirect(`${config.cors.origin}/settings/identities?success=already_linked`);
    }

    // Count existing identities
    const countResult = await query(
      'SELECT COUNT(*) as count FROM hub_user_identities WHERE hub_user_id = $1',
      [hubUserId]
    );
    const isFirstIdentity = parseInt(countResult.rows[0].count, 10) === 0;

    // Link the identity
    await query(
      `INSERT INTO hub_user_identities
       (hub_user_id, platform, platform_user_id, platform_username, avatar_url, is_primary, last_used)
       VALUES ($1, $2, $3, $4, $5, $6, NOW())`,
      [hubUserId, platform, userData.id, userData.username, userData.avatar_url, isFirstIdentity]
    );

    logger.audit('Identity linked successfully', {
      hubUserId,
      platform,
      platformUserId: userData.id,
      platformUsername: userData.username,
      isPrimary: isFirstIdentity,
    });

    res.redirect(`${config.cors.origin}/settings/identities?success=linked&platform=${platform}`);
  } catch (err) {
    logger.error('Identity linking callback error', { error: err.message });
    res.redirect(`${config.cors.origin}/settings/identities?error=linking_failed`);
  }
}

/**
 * Unlink identity from hub account
 * DELETE /api/v1/user/identities/:platform
 */
export async function unlinkIdentity(req, res, next) {
  try {
    if (!req.user) {
      return next(errors.unauthorized());
    }

    const { platform } = req.params;

    const hubUserId = await getOrCreateHubUser(req.user);

    // Check if this is the last/only identity
    const countResult = await query(
      'SELECT COUNT(*) as count FROM hub_user_identities WHERE hub_user_id = $1',
      [hubUserId]
    );

    const identityCount = parseInt(countResult.rows[0].count, 10);

    if (identityCount <= 1) {
      return next(errors.badRequest('Cannot unlink last identity'));
    }

    // Check if this is the primary identity
    const primaryCheck = await query(
      'SELECT is_primary FROM hub_user_identities WHERE hub_user_id = $1 AND platform = $2',
      [hubUserId, platform]
    );

    if (primaryCheck.rows.length === 0) {
      return next(errors.notFound('Identity not found'));
    }

    const isPrimary = primaryCheck.rows[0].is_primary;

    await transaction(async (client) => {
      // Delete the identity
      await client.query(
        'DELETE FROM hub_user_identities WHERE hub_user_id = $1 AND platform = $2',
        [hubUserId, platform]
      );

      // If this was primary, set another identity as primary
      if (isPrimary) {
        await client.query(
          `UPDATE hub_user_identities
           SET is_primary = true
           WHERE hub_user_id = $1
           AND id = (SELECT id FROM hub_user_identities WHERE hub_user_id = $1 ORDER BY linked_at ASC LIMIT 1)`,
          [hubUserId]
        );
      }
    });

    logger.audit('Identity unlinked', {
      hubUserId,
      username: req.user.username,
      platform,
      wasPrimary: isPrimary,
    });

    res.json({ success: true, message: 'Identity unlinked successfully' });
  } catch (err) {
    next(err);
  }
}

/**
 * Helper: Get or create hub_user record for a platform identity
 */
async function getOrCreateHubUser(user) {
  // For admin users, check if they have a hub_user record
  if (user.platform === 'admin') {
    // Try to find existing hub_user by admin email
    const adminResult = await query(
      'SELECT email FROM hub_admins WHERE id = $1',
      [parseInt(user.platformUserId, 10)]
    );

    if (adminResult.rows.length > 0 && adminResult.rows[0].email) {
      const existingUser = await query(
        'SELECT id FROM hub_users WHERE email = $1',
        [adminResult.rows[0].email]
      );

      if (existingUser.rows.length > 0) {
        return existingUser.rows[0].id;
      }
    }

    // Create new hub_user for admin
    const createResult = await query(
      `INSERT INTO hub_users (display_name, email, created_at, updated_at)
       VALUES ($1, $2, NOW(), NOW())
       RETURNING id`,
      [user.username, adminResult.rows[0]?.email || null]
    );

    return createResult.rows[0].id;
  }

  // For platform users, check if identity already exists
  const existingIdentity = await query(
    `SELECT hub_user_id FROM hub_user_identities
     WHERE platform = $1 AND platform_user_id = $2`,
    [user.platform, user.platformUserId]
  );

  if (existingIdentity.rows.length > 0) {
    return existingIdentity.rows[0].hub_user_id;
  }

  // Create new hub_user and link first identity
  return await transaction(async (client) => {
    const userResult = await client.query(
      `INSERT INTO hub_users (display_name, created_at, updated_at)
       VALUES ($1, NOW(), NOW())
       RETURNING id`,
      [user.username]
    );

    const hubUserId = userResult.rows[0].id;

    await client.query(
      `INSERT INTO hub_user_identities
       (hub_user_id, platform, platform_user_id, platform_username, avatar_url, is_primary, linked_at, last_used)
       VALUES ($1, $2, $3, $4, $5, true, NOW(), NOW())`,
      [hubUserId, user.platform, user.platformUserId, user.username, user.avatarUrl]
    );

    return hubUserId;
  });
}
