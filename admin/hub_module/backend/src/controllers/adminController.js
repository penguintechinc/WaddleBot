/**
 * Admin Controller - Community admin features
 */
import { query } from '../config/database.js';
import { config } from '../config/index.js';
import { errors } from '../middleware/errorHandler.js';
import { logger } from '../utils/logger.js';
import { formatReputation, clampReputation, REPUTATION_MIN, REPUTATION_MAX } from '../utils/reputation.js';
import bcrypt from 'bcrypt';
import { v4 as uuidv4 } from 'uuid';
import crypto from 'crypto';

const SALT_ROUNDS = 12;
const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY || crypto.randomBytes(32).toString('hex');
const ENCRYPTION_ALGORITHM = 'aes-256-gcm';

/**
 * PostgreSQL error codes for missing schema objects:
 * 42P01 = undefined_table, 42703 = undefined_column, 42883 = undefined operator/type mismatch
 * When these occur, return graceful empty data instead of a 500 error.
 */
const SCHEMA_ERROR_CODES = ['42P01', '42703', '42883'];

function isSchemaError(err) {
  return SCHEMA_ERROR_CODES.includes(err?.code);
}

/**
 * Parse a value that may be a JSON string or already a JS object (e.g. from JSONB columns).
 * PostgreSQL's node-postgres driver auto-parses JSONB to objects, but sometimes values
 * are stored as text, so we need to handle both cases.
 */
function safeJsonParse(val, fallback = {}) {
  if (val === null || val === undefined) return fallback;
  if (typeof val === 'object') return val;
  try { return JSON.parse(val); } catch { return fallback; }
}

/**
 * Encrypt sensitive data (API keys)
 */
function encryptData(text) {
  const iv = crypto.randomBytes(16);
  const cipher = crypto.createCipheriv(ENCRYPTION_ALGORITHM, Buffer.from(ENCRYPTION_KEY, 'hex'), iv);
  let encrypted = cipher.update(text, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  const authTag = cipher.getAuthTag();
  return JSON.stringify({
    iv: iv.toString('hex'),
    data: encrypted,
    tag: authTag.toString('hex')
  });
}

/**
 * Decrypt sensitive data (API keys)
 */
function decryptData(encrypted) {
  const { iv, data, tag } = JSON.parse(encrypted);
  const decipher = crypto.createDecipheriv(
    ENCRYPTION_ALGORITHM,
    Buffer.from(ENCRYPTION_KEY, 'hex'),
    Buffer.from(iv, 'hex')
  );
  decipher.setAuthTag(Buffer.from(tag, 'hex'));
  let decrypted = decipher.update(data, 'hex', 'utf8');
  decrypted += decipher.final('utf8');
  return decrypted;
}

/**
 * Get community members
 */
export async function getMembers(req, res, next) {
  const page = Math.max(1, parseInt(req.query.page || '1', 10));
  const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '25', 10)));
  const offset = (page - 1) * limit;

  try {
    const communityId = parseInt(req.params.communityId, 10);
    const search = req.query.search || '';
    const role = req.query.role;

    let whereClause = 'WHERE cm.community_id = $1 AND cm.is_active = true';
    const params = [communityId];
    let paramIndex = 2;

    if (search) {
      whereClause += ` AND (u.username ILIKE $${paramIndex} OR u.email ILIKE $${paramIndex})`;
      params.push(`%${search}%`);
      paramIndex++;
    }

    if (role) {
      whereClause += ` AND cm.role = $${paramIndex}`;
      params.push(role);
      paramIndex++;
    }

    // user_id is VARCHAR in community_members but INTEGER in hub_users — cast for JOIN
    const countResult = await query(
      `SELECT COUNT(*) as count FROM community_members cm
       LEFT JOIN hub_users u ON u.id = cm.user_id::integer
       ${whereClause}`,
      params
    );
    const total = parseInt(countResult.rows[0]?.count || 0, 10);

    const result = await query(
      `SELECT cm.id, cm.user_id, u.username, u.email, u.avatar_url,
              cm.role, cm.reputation, cm.joined_at
       FROM community_members cm
       LEFT JOIN hub_users u ON u.id = cm.user_id::integer
       ${whereClause}
       ORDER BY cm.reputation DESC, cm.joined_at ASC
       LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`,
      [...params, limit, offset]
    );

    const members = result.rows.map(row => ({
      id: row.id,
      userId: row.user_id,
      username: row.username,
      email: row.email,
      avatarUrl: row.avatar_url,
      role: row.role,
      reputation: formatReputation(row.reputation),
      joinedAt: row.joined_at?.toISOString(),
    }));

    res.json({
      success: true,
      members,
      pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
    });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, members: [], pagination: { page, limit, total: 0, totalPages: 0 } });
    }
    next(err);
  }
}

/**
 * Update member role
 */
export async function updateMemberRole(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const userId = parseInt(req.params.userId, 10);
    const { role } = req.body;

    const validRoles = ['community-admin', 'moderator', 'vip', 'member'];
    if (!validRoles.includes(role)) {
      return next(errors.badRequest('Invalid role'));
    }

    // Check target user exists and isn't owner
    const targetResult = await query(
      `SELECT role FROM community_members
       WHERE community_id = $1 AND user_id = $2 AND is_active = true`,
      [communityId, userId]
    );

    if (targetResult.rows.length === 0) {
      return next(errors.notFound('Member not found'));
    }

    if (targetResult.rows[0].role === 'community-owner') {
      return next(errors.forbidden('Cannot change owner role'));
    }

    // Check permission hierarchy
    const adminRoles = ['community-owner', 'community-admin'];
    if (role === 'community-admin' && !adminRoles.includes(req.communityRole)) {
      return next(errors.forbidden('Only owners can promote to admin'));
    }

    // Look up community_role_id for the new role
    const roleResult = await query(
      'SELECT id FROM community_roles WHERE community_id = $1 AND name = $2',
      [communityId, role]
    );
    const communityRoleId = roleResult.rows[0]?.id || null;

    await query(
      `UPDATE community_members SET role = $1, community_role_id = $2, claims_cache = NULL, updated_at = NOW()
       WHERE community_id = $3 AND user_id = $4`,
      [role, communityRoleId, communityId, userId]
    );

    logger.audit('Member role updated', {
      adminId: req.user.id,
      communityId,
      targetUserId: userId,
      newRole: role,
    });

    res.json({ success: true, message: 'Role updated' });
  } catch (err) {
    next(err);
  }
}

/**
 * Adjust member reputation
 * Community admins can adjust reputation within the credit score bounds (300-850)
 */
export async function adjustReputation(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const userId = parseInt(req.params.userId, 10);
    const { amount, reason, setTo } = req.body;

    // Support both relative adjustment (amount) and absolute set (setTo)
    if (setTo !== undefined) {
      // Absolute set - clamp to valid range
      const newScore = clampReputation(setTo);

      const result = await query(
        `UPDATE community_members
         SET reputation = $1
         WHERE community_id = $2 AND user_id = $3
         RETURNING reputation`,
        [newScore, communityId, userId]
      );

      if (result.rows.length === 0) {
        return next(errors.notFound('Member not found'));
      }

      logger.audit('Reputation set', {
        adminId: req.user.id,
        communityId,
        targetUserId: userId,
        newScore,
        reason,
      });

      res.json({
        success: true,
        reputation: formatReputation(result.rows[0].reputation),
      });
    } else {
      // Relative adjustment
      if (typeof amount !== 'number' || amount === 0) {
        return next(errors.badRequest('Invalid amount - provide amount (relative) or setTo (absolute)'));
      }

      // Get current reputation and calculate new value with clamp
      const currentResult = await query(
        `SELECT reputation FROM community_members
         WHERE community_id = $1 AND user_id = $2`,
        [communityId, userId]
      );

      if (currentResult.rows.length === 0) {
        return next(errors.notFound('Member not found'));
      }

      const currentRep = currentResult.rows[0].reputation || 600;
      const newScore = clampReputation(currentRep + amount);

      const result = await query(
        `UPDATE community_members
         SET reputation = $1
         WHERE community_id = $2 AND user_id = $3
         RETURNING reputation`,
        [newScore, communityId, userId]
      );

      logger.audit('Reputation adjusted', {
        adminId: req.user.id,
        communityId,
        targetUserId: userId,
        change: amount,
        oldScore: currentRep,
        newScore,
        reason,
      });

      res.json({
        success: true,
        reputation: formatReputation(result.rows[0].reputation),
        change: newScore - currentRep,
      });
    }
  } catch (err) {
    next(err);
  }
}

/**
 * Remove member from community
 */
export async function removeMember(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const userId = parseInt(req.params.userId, 10);
    const { reason } = req.body;

    // Check target isn't owner
    const targetResult = await query(
      `SELECT role FROM community_members
       WHERE community_id = $1 AND user_id = $2 AND is_active = true`,
      [communityId, userId]
    );

    if (targetResult.rows.length === 0) {
      return next(errors.notFound('Member not found'));
    }

    if (targetResult.rows[0].role === 'community-owner') {
      return next(errors.forbidden('Cannot remove owner'));
    }

    // Deactivate membership
    await query(
      `UPDATE community_members
       SET is_active = false, removed_at = NOW(), removed_by = $1, removal_reason = $2
       WHERE community_id = $3 AND user_id = $4`,
      [req.user.id, reason, communityId, userId]
    );

    // Update member count
    await query(
      `UPDATE communities SET member_count = member_count - 1 WHERE id = $1`,
      [communityId]
    );

    logger.audit('Member removed', {
      adminId: req.user.id,
      communityId,
      targetUserId: userId,
      reason,
    });

    res.json({ success: true, message: 'Member removed' });
  } catch (err) {
    next(err);
  }
}

/**
 * Get installed modules
 */
export async function getModules(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const result = await query(
      `SELECT mi.id, mi.module_id, m.name, m.display_name, m.description,
              m.category, mi.is_enabled, mi.config, mi.installed_at
       FROM module_installations mi
       JOIN modules m ON m.id::text = mi.module_id
       WHERE mi.community_id = $1
       ORDER BY m.name ASC`,
      [communityId]
    );

    const modules = result.rows.map(row => ({
      installationId: row.id,
      moduleId: row.module_id,
      name: row.name,
      displayName: row.display_name || row.name,
      description: row.description,
      category: row.category,
      isEnabled: row.is_enabled,
      config: row.config,
      installedAt: row.installed_at?.toISOString(),
    }));

    res.json({ success: true, modules });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, modules: [] });
    }
    next(err);
  }
}

/**
 * Update module configuration
 */
export async function updateModuleConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const moduleId = parseInt(req.params.moduleId, 10);
    const { config: moduleConfig, isEnabled } = req.body;

    // Prevent disabling truly non-disableable core modules (identity, workflow)
    if (isEnabled === false) {
      const coreCheck = await query(
        'SELECT is_core FROM hub_modules WHERE id = $1',
        [moduleId]
      );
      if (coreCheck.rows[0]?.is_core === true) {
        return res.status(403).json({
          error: 'Cannot disable a core module. This module is required for WaddleBot to function correctly.',
        });
      }
    }

    const updates = [];
    const params = [communityId, moduleId];
    let paramIndex = 3;

    if (moduleConfig !== undefined) {
      updates.push(`config = $${paramIndex}`);
      params.push(JSON.stringify(moduleConfig));
      paramIndex++;
    }

    if (isEnabled !== undefined) {
      updates.push(`is_enabled = $${paramIndex}`);
      params.push(isEnabled);
      paramIndex++;
    }

    if (updates.length === 0) {
      return next(errors.badRequest('No updates provided'));
    }

    updates.push('updated_at = NOW()');

    const result = await query(
      `UPDATE module_installations
       SET ${updates.join(', ')}
       WHERE community_id = $1 AND module_id = $2
       RETURNING id`,
      params
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Module installation not found'));
    }

    logger.audit('Module config updated', {
      adminId: req.user.id,
      communityId,
      moduleId,
    });

    res.json({ success: true, message: 'Module configuration updated' });
  } catch (err) {
    next(err);
  }
}

/**
 * Get browser source URLs
 */
export async function getBrowserSources(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const result = await query(
      `SELECT source_type, token, is_active, created_at
       FROM browser_source_tokens
       WHERE community_id = $1`,
      [communityId]
    );

    const baseUrl = config.modules.browserSource || 'http://localhost:8027';
    const sources = result.rows.map(row => ({
      sourceType: row.source_type,
      url: `${baseUrl}/browser/source/${row.token}/${row.source_type}`,
      token: row.token,
      isActive: row.is_active,
      createdAt: row.created_at?.toISOString(),
    }));

    // Ensure all three types exist
    const sourceTypes = ['ticker', 'media', 'general'];
    for (const type of sourceTypes) {
      if (!sources.find(s => s.sourceType === type)) {
        // Create missing token
        const token = uuidv4().replace(/-/g, '');
        await query(
          `INSERT INTO browser_source_tokens (community_id, source_type, token)
           VALUES ($1, $2, $3)`,
          [communityId, type, token]
        );
        sources.push({
          sourceType: type,
          url: `${baseUrl}/browser/source/${token}/${type}`,
          token,
          isActive: true,
          createdAt: new Date().toISOString(),
        });
      }
    }

    res.json({ success: true, sources });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, sources: [] });
    }
    next(err);
  }
}

/**
 * Regenerate browser source tokens
 */
export async function regenerateBrowserSources(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const { sourceType } = req.body;

    const sourceTypes = sourceType ? [sourceType] : ['ticker', 'media', 'general'];

    for (const type of sourceTypes) {
      const newToken = uuidv4().replace(/-/g, '');
      await query(
        `UPDATE browser_source_tokens
         SET token = $1, updated_at = NOW()
         WHERE community_id = $2 AND source_type = $3`,
        [newToken, communityId, type]
      );
    }

    logger.audit('Browser source tokens regenerated', {
      adminId: req.user.id,
      communityId,
      sourceTypes,
    });

    res.json({ success: true, message: 'Tokens regenerated' });
  } catch (err) {
    next(err);
  }
}

/**
 * Get custom domains
 */
export async function getDomains(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const result = await query(
      `SELECT id, domain, is_verified, verification_token, verified_at, created_at
       FROM community_domains
       WHERE community_id = $1
       ORDER BY created_at DESC`,
      [communityId]
    );

    const domains = result.rows.map(row => ({
      id: row.id,
      domain: row.domain,
      isVerified: row.is_verified,
      verificationToken: row.is_verified ? null : row.verification_token,
      verifiedAt: row.verified_at?.toISOString(),
      createdAt: row.created_at?.toISOString(),
    }));

    res.json({ success: true, domains });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, domains: [] });
    }
    next(err);
  }
}

/**
 * Add custom domain
 */
export async function addDomain(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const { domain } = req.body;

    if (!domain || !/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(domain)) {
      return next(errors.badRequest('Invalid domain format'));
    }

    // Check if domain already exists
    const existingResult = await query(
      `SELECT id FROM community_domains WHERE domain = $1`,
      [domain.toLowerCase()]
    );

    if (existingResult.rows.length > 0) {
      return next(errors.conflict('Domain already registered'));
    }

    // Generate verification token
    const verificationToken = `waddlebot-verify-${uuidv4()}`;

    const result = await query(
      `INSERT INTO community_domains (community_id, domain, verification_token)
       VALUES ($1, $2, $3)
       RETURNING id, domain, verification_token`,
      [communityId, domain.toLowerCase(), verificationToken]
    );

    logger.audit('Custom domain added', {
      adminId: req.user.id,
      communityId,
      domain,
    });

    res.status(201).json({
      success: true,
      domain: {
        id: result.rows[0].id,
        domain: result.rows[0].domain,
        verificationToken: result.rows[0].verification_token,
        isVerified: false,
      },
      instructions: {
        type: 'TXT',
        name: `_waddlebot.${domain}`,
        value: verificationToken,
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Verify domain ownership via DNS
 */
export async function verifyDomain(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const domainId = parseInt(req.params.domainId, 10);

    const domainResult = await query(
      `SELECT domain, verification_token FROM community_domains
       WHERE id = $1 AND community_id = $2 AND is_verified = false`,
      [domainId, communityId]
    );

    if (domainResult.rows.length === 0) {
      return next(errors.notFound('Domain not found or already verified'));
    }

    const { domain, verification_token } = domainResult.rows[0];

    // DNS lookup would happen here in production
    // For now, mark as verified if token matches
    const { resolveTxt } = await import('dns').then(m => m.promises);
    try {
      const records = await resolveTxt(`_waddlebot.${domain}`);
      const found = records.flat().includes(verification_token);

      if (!found) {
        return res.json({
          success: false,
          message: 'Verification token not found in DNS records',
        });
      }
    } catch {
      return res.json({
        success: false,
        message: 'Could not resolve DNS records. Please check your configuration.',
      });
    }

    // Mark as verified
    await query(
      `UPDATE community_domains SET is_verified = true, verified_at = NOW() WHERE id = $1`,
      [domainId]
    );

    logger.audit('Custom domain verified', {
      adminId: req.user.id,
      communityId,
      domain,
    });

    res.json({ success: true, message: 'Domain verified successfully' });
  } catch (err) {
    next(err);
  }
}

/**
 * Remove custom domain
 */
export async function removeDomain(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const domainId = parseInt(req.params.domainId, 10);

    const result = await query(
      `DELETE FROM community_domains
       WHERE id = $1 AND community_id = $2
       RETURNING domain`,
      [domainId, communityId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Domain not found'));
    }

    logger.audit('Custom domain removed', {
      adminId: req.user.id,
      communityId,
      domain: result.rows[0].domain,
    });

    res.json({ success: true, message: 'Domain removed' });
  } catch (err) {
    next(err);
  }
}

/**
 * Get pending join requests for community
 */
export async function getJoinRequests(req, res, next) {
  const page = Math.max(1, parseInt(req.query.page || '1', 10));
  const limit = Math.min(50, Math.max(1, parseInt(req.query.limit || '20', 10)));
  const offset = (page - 1) * limit;

  try {
    const communityId = parseInt(req.params.communityId, 10);
    const status = req.query.status || 'pending';

    const countResult = await query(
      `SELECT COUNT(*) as count FROM join_requests
       WHERE community_id = $1 AND status = $2`,
      [communityId, status]
    );
    const total = parseInt(countResult.rows[0]?.count || 0, 10);

    const result = await query(
      `SELECT jr.id, jr.user_id, jr.message, jr.status, jr.created_at,
              jr.reviewed_by, jr.reviewed_at, jr.review_note,
              u.username, u.email, u.avatar_url
       FROM join_requests jr
       JOIN hub_users u ON u.id = jr.user_id
       WHERE jr.community_id = $1 AND jr.status = $2
       ORDER BY jr.created_at ASC
       LIMIT $3 OFFSET $4`,
      [communityId, status, limit, offset]
    );

    const requests = result.rows.map(row => ({
      id: row.id,
      userId: row.user_id,
      username: row.username,
      email: row.email,
      avatarUrl: row.avatar_url,
      message: row.message,
      status: row.status,
      createdAt: row.created_at?.toISOString(),
      reviewedBy: row.reviewed_by,
      reviewedAt: row.reviewed_at?.toISOString(),
      reviewNote: row.review_note,
    }));

    res.json({
      success: true,
      requests,
      pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
    });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, requests: [], pagination: { page, limit, total: 0, totalPages: 0 } });
    }
    next(err);
  }
}

/**
 * Approve join request
 */
export async function approveJoinRequest(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const requestId = parseInt(req.params.requestId, 10);
    const { note } = req.body;

    // Get join request
    const requestResult = await query(
      `SELECT user_id FROM join_requests
       WHERE id = $1 AND community_id = $2 AND status = 'pending'`,
      [requestId, communityId]
    );

    if (requestResult.rows.length === 0) {
      return next(errors.notFound('Join request not found or already processed'));
    }

    const userId = requestResult.rows[0].user_id;

    // Update join request
    await query(
      `UPDATE join_requests
       SET status = 'approved', reviewed_by = $1, reviewed_at = NOW(), review_note = $2
       WHERE id = $3`,
      [req.user.id, note || null, requestId]
    );

    // Add user as member
    await query(
      `INSERT INTO community_members (community_id, user_id, role, is_active, joined_at)
       VALUES ($1, $2, 'member', true, NOW())
       ON CONFLICT (community_id, user_id)
       DO UPDATE SET is_active = true, joined_at = NOW()`,
      [communityId, userId]
    );

    // Set community_role_id for the default 'member' role
    const defaultRole = await query(
      'SELECT id FROM community_roles WHERE community_id = $1 AND name = $2',
      [communityId, 'member']
    );
    if (defaultRole.rows.length) {
      await query(
        'UPDATE community_members SET community_role_id = $1 WHERE community_id = $2 AND user_id = $3',
        [defaultRole.rows[0].id, communityId, userId]
      );
    }

    // Update member count
    await query(
      `UPDATE communities SET member_count = member_count + 1 WHERE id = $1`,
      [communityId]
    );

    logger.audit('Join request approved', {
      adminId: req.user.id,
      communityId,
      requestId,
      userId,
    });

    res.json({ success: true, message: 'Join request approved' });
  } catch (err) {
    next(err);
  }
}

/**
 * Reject join request
 */
export async function rejectJoinRequest(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const requestId = parseInt(req.params.requestId, 10);
    const { note } = req.body;

    const result = await query(
      `UPDATE join_requests
       SET status = 'rejected', reviewed_by = $1, reviewed_at = NOW(), review_note = $2
       WHERE id = $3 AND community_id = $4 AND status = 'pending'
       RETURNING user_id`,
      [req.user.id, note || null, requestId, communityId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Join request not found or already processed'));
    }

    logger.audit('Join request rejected', {
      adminId: req.user.id,
      communityId,
      requestId,
      userId: result.rows[0].user_id,
      reason: note,
    });

    res.json({ success: true, message: 'Join request rejected' });
  } catch (err) {
    next(err);
  }
}

/**
 * Get community settings (including join mode)
 */
export async function getCommunitySettings(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const result = await query(
      `SELECT name, display_name, description, platform, is_public, join_mode, config
       FROM communities WHERE id = $1`,
      [communityId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Community not found'));
    }

    const row = result.rows[0];
    res.json({
      success: true,
      settings: {
        name: row.name,
        displayName: row.display_name,
        description: row.description,
        platform: row.platform,
        isPublic: row.is_public,
        joinMode: row.join_mode || 'open',
        channelCreationPolicy: (row.config || {}).channel_creation_policy || 'admin_only',
        config: row.config || {},
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Update community settings
 */
export async function updateCommunitySettings(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const { displayName, description, isPublic, joinMode, channelCreationPolicy, config } = req.body;

    const updates = [];
    const params = [];
    let paramIndex = 1;

    if (displayName !== undefined) {
      updates.push(`display_name = $${paramIndex}`);
      params.push(displayName);
      paramIndex++;
    }

    if (description !== undefined) {
      updates.push(`description = $${paramIndex}`);
      params.push(description);
      paramIndex++;
    }

    if (isPublic !== undefined) {
      updates.push(`is_public = $${paramIndex}`);
      params.push(isPublic);
      paramIndex++;
    }

    if (joinMode !== undefined) {
      const validModes = ['open', 'approval', 'invite'];
      if (!validModes.includes(joinMode)) {
        return next(errors.badRequest('Invalid join mode'));
      }
      updates.push(`join_mode = $${paramIndex}`);
      params.push(joinMode);
      paramIndex++;
    }

    if (channelCreationPolicy !== undefined) {
      const validPolicies = ['admin_only', 'communicator', 'all_members'];
      if (!validPolicies.includes(channelCreationPolicy)) {
        return next(errors.badRequest('Invalid channel creation policy'));
      }
      updates.push(`config = COALESCE(config, '{}')::jsonb || $${paramIndex}::jsonb`);
      params.push(JSON.stringify({ channel_creation_policy: channelCreationPolicy }));
      paramIndex++;
    }

    if (config !== undefined) {
      updates.push(`config = COALESCE(config, '{}')::jsonb || $${paramIndex}::jsonb`);
      params.push(JSON.stringify(config));
      paramIndex++;
    }

    if (updates.length === 0) {
      return next(errors.badRequest('No updates provided'));
    }

    updates.push('updated_at = NOW()');
    params.push(communityId);

    await query(
      `UPDATE communities SET ${updates.join(', ')} WHERE id = $${paramIndex}`,
      params
    );

    logger.audit('Community settings updated', {
      adminId: req.user.id,
      communityId,
      fields: Object.keys(req.body),
    });

    res.json({ success: true, message: 'Settings updated' });
  } catch (err) {
    next(err);
  }
}

/**
 * Generate temp password for user
 */
export async function generateTempPassword(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const { userIdentifier, forceOAuthLink = true, expiresInHours = 24 } = req.body;

    if (!userIdentifier) {
      return next(errors.badRequest('User identifier required'));
    }

    // Generate random password
    const tempPassword = uuidv4().split('-').slice(0, 2).join('-');
    const passwordHash = await bcrypt.hash(tempPassword, SALT_ROUNDS);
    const expiresAt = new Date(Date.now() + expiresInHours * 60 * 60 * 1000);

    await query(
      `INSERT INTO hub_temp_passwords
       (community_id, user_identifier, password_hash, expires_at, force_oauth_link, created_by)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [communityId, userIdentifier, passwordHash, expiresAt, forceOAuthLink, req.user.id]
    );

    logger.audit('Temp password generated', {
      adminId: req.user.id,
      communityId,
      userIdentifier,
    });

    res.status(201).json({
      success: true,
      tempPassword,
      expiresAt: expiresAt.toISOString(),
      instructions: `Share this password with the user. It expires in ${expiresInHours} hours and can only be used once.`,
    });
  } catch (err) {
    next(err);
  }
}

// ===== Server Linking Admin Endpoints =====

/**
 * Get linked servers for community (admin view - includes pending)
 */
export async function getLinkedServers(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const status = req.query.status; // optional filter

    let whereClause = 'WHERE cs.community_id = $1';
    const params = [communityId];

    if (status) {
      whereClause += ' AND cs.status = $2';
      params.push(status);
    }

    const result = await query(
      `SELECT cs.id, cs.platform, cs.platform_server_id, cs.platform_server_name,
              cs.link_type, cs.status, cs.is_primary, cs.config, cs.verified_at, cs.created_at,
              u1.username as added_by_username,
              u2.username as approved_by_username
       FROM community_servers cs
       LEFT JOIN hub_users u1 ON u1.id = cs.added_by
       LEFT JOIN hub_users u2 ON u2.id = cs.approved_by
       ${whereClause}
       ORDER BY cs.is_primary DESC, cs.status ASC, cs.created_at ASC`,
      params
    );

    const servers = result.rows.map(row => ({
      id: row.id,
      platform: row.platform,
      platformServerId: row.platform_server_id,
      platformServerName: row.platform_server_name,
      linkType: row.link_type,
      status: row.status,
      isPrimary: row.is_primary,
      config: row.config || {},
      verifiedAt: row.verified_at?.toISOString(),
      addedBy: row.added_by_username,
      approvedBy: row.approved_by_username,
      createdAt: row.created_at?.toISOString(),
    }));

    res.json({ success: true, servers });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, servers: [] });
    }
    next(err);
  }
}

/**
 * Create a server link request from the community side
 * Called when a community admin wants to initiate a link to a platform server
 */
export async function createServerLinkRequest(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const { platform, platformServerId, platformServerName, linkType } = req.body;

    if (!platform || !platformServerId) {
      return next(errors.badRequest('platform and platformServerId are required'));
    }

    const validPlatforms = ['discord', 'slack', 'twitch', 'kick', 'youtube'];
    if (!validPlatforms.includes(platform)) {
      return next(errors.badRequest(`platform must be one of: ${validPlatforms.join(', ')}`));
    }

    const validLinkTypes = ['standard', 'read_only', 'announcement_only'];
    const resolvedLinkType = validLinkTypes.includes(linkType) ? linkType : 'standard';

    // Check for existing approved link
    const existingLink = await query(
      `SELECT id FROM community_servers
       WHERE community_id = $1 AND platform = $2 AND platform_server_id = $3`,
      [communityId, platform, platformServerId]
    );
    if (existingLink.rows.length > 0) {
      return res.status(409).json({ error: 'This server is already linked to this community' });
    }

    // Check for existing pending request
    const existingRequest = await query(
      `SELECT id FROM server_link_requests
       WHERE community_id = $1 AND platform = $2 AND platform_server_id = $3 AND status = 'pending'`,
      [communityId, platform, platformServerId]
    );
    if (existingRequest.rows.length > 0) {
      return res.status(409).json({ error: 'A pending request for this server already exists' });
    }

    const result = await query(
      `INSERT INTO server_link_requests
         (community_id, platform, platform_server_id, platform_server_name,
          requested_by, status, initiated_by, link_type)
       VALUES ($1, $2, $3, $4, $5, 'pending', 'community', $6)
       RETURNING id`,
      [communityId, platform, platformServerId, platformServerName || null, req.user.id, resolvedLinkType]
    );

    logger.audit('Server link request created (community-initiated)', {
      adminId: req.user.id,
      communityId,
      platform,
      platformServerId,
      linkType: resolvedLinkType,
    });

    res.status(201).json({ success: true, requestId: result.rows[0].id });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.status(503).json({ error: 'Server link requests are not yet available' });
    }
    next(err);
  }
}

/**
 * Get pending server link requests for community
 */
export async function getServerLinkRequests(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const status = req.query.status || 'pending';

    const result = await query(
      `SELECT slr.id, slr.platform, slr.platform_server_id, slr.platform_server_name,
              slr.status, slr.review_note, slr.created_at, slr.reviewed_at,
              slr.initiated_by, slr.link_type,
              slr.initiator_platform_username,
              u1.username as requested_by_username, u1.email as requested_by_email,
              u2.username as reviewed_by_username
       FROM server_link_requests slr
       LEFT JOIN hub_users u1 ON u1.id = slr.requested_by
       LEFT JOIN hub_users u2 ON u2.id = slr.reviewed_by
       WHERE slr.community_id = $1 AND slr.status = $2
       ORDER BY slr.created_at ASC`,
      [communityId, status]
    );

    const requests = result.rows.map(row => ({
      id: row.id,
      platform: row.platform,
      platformServerId: row.platform_server_id,
      platformServerName: row.platform_server_name,
      status: row.status,
      reviewNote: row.review_note,
      initiatedBy: row.initiated_by || 'community',
      linkType: row.link_type || 'standard',
      initiatorPlatformUsername: row.initiator_platform_username,
      requestedBy: row.requested_by_username,
      requestedByEmail: row.requested_by_email,
      reviewedBy: row.reviewed_by_username,
      createdAt: row.created_at?.toISOString(),
      reviewedAt: row.reviewed_at?.toISOString(),
    }));

    res.json({ success: true, requests });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, requests: [] });
    }
    next(err);
  }
}

/**
 * Approve server link request
 */
export async function approveServerLinkRequest(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const requestId = parseInt(req.params.requestId, 10);
    const { note } = req.body;

    // Get the request
    const requestResult = await query(
      `SELECT platform, platform_server_id, platform_server_name, requested_by
       FROM server_link_requests
       WHERE id = $1 AND community_id = $2 AND status = 'pending'`,
      [requestId, communityId]
    );

    if (requestResult.rows.length === 0) {
      return next(errors.notFound('Server link request not found or already processed'));
    }

    const request = requestResult.rows[0];

    // Update request status
    await query(
      `UPDATE server_link_requests
       SET status = 'approved', reviewed_by = $1, reviewed_at = NOW(), review_note = $2
       WHERE id = $3`,
      [req.user.id, note || null, requestId]
    );

    // Add server to community_servers
    await query(
      `INSERT INTO community_servers
       (community_id, platform, platform_server_id, platform_server_name, added_by, approved_by, status, verified_at)
       VALUES ($1, $2, $3, $4, $5, $6, 'approved', NOW())
       ON CONFLICT (community_id, platform, platform_server_id)
       DO UPDATE SET status = 'approved', approved_by = $6, verified_at = NOW()`,
      [communityId, request.platform, request.platform_server_id, request.platform_server_name, request.requested_by, req.user.id]
    );

    logger.audit('Server link request approved', {
      adminId: req.user.id,
      communityId,
      requestId,
      platform: request.platform,
      platformServerId: request.platform_server_id,
    });

    res.json({ success: true, message: 'Server link request approved' });
  } catch (err) {
    next(err);
  }
}

/**
 * Reject server link request
 */
export async function rejectServerLinkRequest(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const requestId = parseInt(req.params.requestId, 10);
    const { note } = req.body;

    const result = await query(
      `UPDATE server_link_requests
       SET status = 'rejected', reviewed_by = $1, reviewed_at = NOW(), review_note = $2
       WHERE id = $3 AND community_id = $4 AND status = 'pending'
       RETURNING platform, platform_server_id`,
      [req.user.id, note || null, requestId, communityId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Server link request not found or already processed'));
    }

    logger.audit('Server link request rejected', {
      adminId: req.user.id,
      communityId,
      requestId,
      platform: result.rows[0].platform,
      platformServerId: result.rows[0].platform_server_id,
      reason: note,
    });

    res.json({ success: true, message: 'Server link request rejected' });
  } catch (err) {
    next(err);
  }
}

/**
 * Remove server from community
 */
export async function removeServer(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const serverId = parseInt(req.params.serverId, 10);

    const result = await query(
      `DELETE FROM community_servers
       WHERE id = $1 AND community_id = $2
       RETURNING platform, platform_server_id, platform_server_name`,
      [serverId, communityId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Server not found'));
    }

    logger.audit('Server removed from community', {
      adminId: req.user.id,
      communityId,
      serverId,
      platform: result.rows[0].platform,
      platformServerId: result.rows[0].platform_server_id,
    });

    res.json({ success: true, message: 'Server removed from community' });
  } catch (err) {
    next(err);
  }
}

/**
 * Update server settings (e.g., set as primary)
 */
export async function updateServer(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const serverId = parseInt(req.params.serverId, 10);
    const { isPrimary, config } = req.body;

    const updates = [];
    const params = [];
    let paramIndex = 1;

    if (isPrimary !== undefined) {
      // If setting as primary, first unset any existing primary for this platform
      if (isPrimary) {
        const serverResult = await query(
          `SELECT platform FROM community_servers WHERE id = $1 AND community_id = $2`,
          [serverId, communityId]
        );
        if (serverResult.rows.length > 0) {
          await query(
            `UPDATE community_servers SET is_primary = false
             WHERE community_id = $1 AND platform = $2`,
            [communityId, serverResult.rows[0].platform]
          );
        }
      }
      updates.push(`is_primary = $${paramIndex}`);
      params.push(isPrimary);
      paramIndex++;
    }

    if (config !== undefined) {
      updates.push(`config = $${paramIndex}`);
      params.push(JSON.stringify(config));
      paramIndex++;
    }

    if (updates.length === 0) {
      return next(errors.badRequest('No updates provided'));
    }

    params.push(serverId, communityId);

    const result = await query(
      `UPDATE community_servers SET ${updates.join(', ')}
       WHERE id = $${paramIndex} AND community_id = $${paramIndex + 1}
       RETURNING id`,
      params
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Server not found'));
    }

    logger.audit('Server settings updated', {
      adminId: req.user.id,
      communityId,
      serverId,
      updates: Object.keys(req.body),
    });

    res.json({ success: true, message: 'Server settings updated' });
  } catch (err) {
    next(err);
  }
}

// ===== Commands Endpoint =====

/**
 * Get all platform commands for a community, with module-level enabled/disabled status
 */
export async function getCommands(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    if (!Number.isFinite(communityId)) {
      return next(errors.badRequest('Invalid community ID'));
    }

    // Join commands with hub_module_installations to get enabled status per community.
    // community_id = NULL rows are global defaults (applies to all communities).
    // A command is considered enabled if the module is installed and enabled for this community,
    // or if no installation record exists (module not installed → default to enabled).
    const result = await query(
      `SELECT
         c.id,
         c.command,
         c.module_name,
         c.description,
         c.category,
         c.permission_level,
         c.platforms,
         COALESCE(hmi.is_enabled, true) AS is_enabled
       FROM commands c
       LEFT JOIN hub_module_installations hmi
         ON hmi.community_id = $1
         AND hmi.module_name = c.module_name
       WHERE c.community_id = $1
          OR c.community_id IS NULL
       ORDER BY c.module_name, c.command`,
      [communityId]
    );

    res.json({ commands: result.rows });
  } catch (err) {
    next(err);
  }
}

// ===== Mirror Group Admin Endpoints =====

/**
 * Get mirror groups for community
 */
export async function getMirrorGroups(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const result = await query(
      `SELECT mg.id, mg.name, mg.description, mg.is_active, mg.config, mg.created_at,
              u.username as created_by_username,
              COUNT(mgm.id) as member_count
       FROM mirror_groups mg
       LEFT JOIN hub_users u ON u.id = mg.created_by
       LEFT JOIN mirror_group_members mgm ON mgm.mirror_group_id = mg.id AND mgm.is_active = true
       WHERE mg.community_id = $1
       GROUP BY mg.id, u.username
       ORDER BY mg.created_at ASC`,
      [communityId]
    );

    const groups = result.rows.map(row => ({
      id: row.id,
      name: row.name,
      description: row.description,
      isActive: row.is_active,
      config: row.config || {},
      memberCount: parseInt(row.member_count, 10) || 0,
      createdBy: row.created_by_username,
      createdAt: row.created_at?.toISOString(),
    }));

    res.json({ success: true, groups });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, groups: [] });
    }
    next(err);
  }
}

/**
 * Get single mirror group with members
 */
export async function getMirrorGroup(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const groupId = parseInt(req.params.groupId, 10);

    // Get group
    const groupResult = await query(
      `SELECT mg.id, mg.name, mg.description, mg.is_active, mg.config, mg.created_at,
              u.username as created_by_username
       FROM mirror_groups mg
       LEFT JOIN hub_users u ON u.id = mg.created_by
       WHERE mg.id = $1 AND mg.community_id = $2`,
      [groupId, communityId]
    );

    if (groupResult.rows.length === 0) {
      return next(errors.notFound('Mirror group not found'));
    }

    const group = groupResult.rows[0];

    // Get members
    const membersResult = await query(
      `SELECT mgm.id, mgm.direction, mgm.is_active, mgm.created_at,
              cs.id as server_id, cs.platform, cs.platform_server_id, cs.platform_server_name,
              csc.id as channel_id, csc.platform_channel_id, csc.platform_channel_name
       FROM mirror_group_members mgm
       JOIN community_servers cs ON cs.id = mgm.community_server_id
       LEFT JOIN community_server_channels csc ON csc.id = mgm.community_server_channel_id
       WHERE mgm.mirror_group_id = $1
       ORDER BY mgm.created_at ASC`,
      [groupId]
    );

    const members = membersResult.rows.map(row => ({
      id: row.id,
      direction: row.direction,
      isActive: row.is_active,
      server: {
        id: row.server_id,
        platform: row.platform,
        platformServerId: row.platform_server_id,
        platformServerName: row.platform_server_name,
      },
      channel: row.channel_id ? {
        id: row.channel_id,
        platformChannelId: row.platform_channel_id,
        platformChannelName: row.platform_channel_name,
      } : null,
      createdAt: row.created_at?.toISOString(),
    }));

    res.json({
      success: true,
      group: {
        id: group.id,
        name: group.name,
        description: group.description,
        isActive: group.is_active,
        config: group.config || {},
        createdBy: group.created_by_username,
        createdAt: group.created_at?.toISOString(),
        members,
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Create mirror group
 */
export async function createMirrorGroup(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const { name, description, config } = req.body;

    if (!name || name.trim().length === 0) {
      return next(errors.badRequest('Name is required'));
    }

    const defaultConfig = { messageTypes: ['chat'] };
    const groupConfig = config ? { ...defaultConfig, ...config } : defaultConfig;

    const result = await query(
      `INSERT INTO mirror_groups (community_id, name, description, config, created_by)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING id, name, description, is_active, config, created_at`,
      [communityId, name.trim(), description || null, JSON.stringify(groupConfig), req.user.id]
    );

    const row = result.rows[0];

    logger.audit('Mirror group created', {
      adminId: req.user.id,
      communityId,
      groupId: row.id,
      name: row.name,
    });

    res.status(201).json({
      success: true,
      group: {
        id: row.id,
        name: row.name,
        description: row.description,
        isActive: row.is_active,
        config: row.config,
        createdAt: row.created_at?.toISOString(),
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Update mirror group
 */
export async function updateMirrorGroup(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const groupId = parseInt(req.params.groupId, 10);
    const { name, description, config, isActive } = req.body;

    const updates = [];
    const params = [];
    let paramIndex = 1;

    if (name !== undefined) {
      updates.push(`name = $${paramIndex}`);
      params.push(name.trim());
      paramIndex++;
    }

    if (description !== undefined) {
      updates.push(`description = $${paramIndex}`);
      params.push(description);
      paramIndex++;
    }

    if (config !== undefined) {
      updates.push(`config = $${paramIndex}`);
      params.push(JSON.stringify(config));
      paramIndex++;
    }

    if (isActive !== undefined) {
      updates.push(`is_active = $${paramIndex}`);
      params.push(isActive);
      paramIndex++;
    }

    if (updates.length === 0) {
      return next(errors.badRequest('No updates provided'));
    }

    updates.push('updated_at = NOW()');
    params.push(groupId, communityId);

    const result = await query(
      `UPDATE mirror_groups SET ${updates.join(', ')}
       WHERE id = $${paramIndex} AND community_id = $${paramIndex + 1}
       RETURNING id`,
      params
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Mirror group not found'));
    }

    logger.audit('Mirror group updated', {
      adminId: req.user.id,
      communityId,
      groupId,
      updates: Object.keys(req.body),
    });

    res.json({ success: true, message: 'Mirror group updated' });
  } catch (err) {
    next(err);
  }
}

/**
 * Delete mirror group
 */
export async function deleteMirrorGroup(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const groupId = parseInt(req.params.groupId, 10);

    const result = await query(
      `DELETE FROM mirror_groups WHERE id = $1 AND community_id = $2 RETURNING name`,
      [groupId, communityId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Mirror group not found'));
    }

    logger.audit('Mirror group deleted', {
      adminId: req.user.id,
      communityId,
      groupId,
      name: result.rows[0].name,
    });

    res.json({ success: true, message: 'Mirror group deleted' });
  } catch (err) {
    next(err);
  }
}

/**
 * Add member to mirror group
 */
export async function addMirrorGroupMember(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const groupId = parseInt(req.params.groupId, 10);
    const { communityServerId, communityServerChannelId, direction } = req.body;

    if (!communityServerId) {
      return next(errors.badRequest('Server ID is required'));
    }

    // Validate direction
    const validDirections = ['send_only', 'receive_only', 'bidirectional'];
    const memberDirection = direction || 'bidirectional';
    if (!validDirections.includes(memberDirection)) {
      return next(errors.badRequest(`Invalid direction. Must be one of: ${validDirections.join(', ')}`));
    }

    // Verify the group belongs to this community
    const groupCheck = await query(
      `SELECT id FROM mirror_groups WHERE id = $1 AND community_id = $2`,
      [groupId, communityId]
    );

    if (groupCheck.rows.length === 0) {
      return next(errors.notFound('Mirror group not found'));
    }

    // Verify the server belongs to this community and is approved
    const serverCheck = await query(
      `SELECT id FROM community_servers WHERE id = $1 AND community_id = $2 AND status = 'approved'`,
      [communityServerId, communityId]
    );

    if (serverCheck.rows.length === 0) {
      return next(errors.badRequest('Server not found or not approved'));
    }

    // Check for existing member
    const existingCheck = await query(
      `SELECT id FROM mirror_group_members
       WHERE mirror_group_id = $1 AND community_server_id = $2
       AND (community_server_channel_id = $3 OR ($3 IS NULL AND community_server_channel_id IS NULL))`,
      [groupId, communityServerId, communityServerChannelId || null]
    );

    if (existingCheck.rows.length > 0) {
      return next(errors.conflict('This server/channel is already in the mirror group'));
    }

    const result = await query(
      `INSERT INTO mirror_group_members
       (mirror_group_id, community_server_id, community_server_channel_id, direction)
       VALUES ($1, $2, $3, $4)
       RETURNING id`,
      [groupId, communityServerId, communityServerChannelId || null, memberDirection]
    );

    logger.audit('Mirror group member added', {
      adminId: req.user.id,
      communityId,
      groupId,
      memberId: result.rows[0].id,
      serverId: communityServerId,
      channelId: communityServerChannelId,
    });

    res.status(201).json({ success: true, memberId: result.rows[0].id });
  } catch (err) {
    next(err);
  }
}

/**
 * Update mirror group member (direction)
 */
export async function updateMirrorGroupMember(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const groupId = parseInt(req.params.groupId, 10);
    const memberId = parseInt(req.params.memberId, 10);
    const { direction, isActive } = req.body;

    const updates = [];
    const params = [];
    let paramIndex = 1;

    if (direction !== undefined) {
      const validDirections = ['send_only', 'receive_only', 'bidirectional'];
      if (!validDirections.includes(direction)) {
        return next(errors.badRequest(`Invalid direction. Must be one of: ${validDirections.join(', ')}`));
      }
      updates.push(`direction = $${paramIndex}`);
      params.push(direction);
      paramIndex++;
    }

    if (isActive !== undefined) {
      updates.push(`is_active = $${paramIndex}`);
      params.push(isActive);
      paramIndex++;
    }

    if (updates.length === 0) {
      return next(errors.badRequest('No updates provided'));
    }

    params.push(memberId, groupId);

    // Verify group belongs to community and update member
    const result = await query(
      `UPDATE mirror_group_members mgm
       SET ${updates.join(', ')}
       FROM mirror_groups mg
       WHERE mgm.id = $${paramIndex} AND mgm.mirror_group_id = $${paramIndex + 1}
       AND mg.id = mgm.mirror_group_id AND mg.community_id = $${paramIndex + 2}
       RETURNING mgm.id`,
      [...params, communityId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Mirror group member not found'));
    }

    logger.audit('Mirror group member updated', {
      adminId: req.user.id,
      communityId,
      groupId,
      memberId,
      updates: Object.keys(req.body),
    });

    res.json({ success: true, message: 'Member updated' });
  } catch (err) {
    next(err);
  }
}

/**
 * Remove member from mirror group
 */
export async function removeMirrorGroupMember(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const groupId = parseInt(req.params.groupId, 10);
    const memberId = parseInt(req.params.memberId, 10);

    // Verify group belongs to community and delete member
    const result = await query(
      `DELETE FROM mirror_group_members mgm
       USING mirror_groups mg
       WHERE mgm.id = $1 AND mgm.mirror_group_id = $2
       AND mg.id = mgm.mirror_group_id AND mg.community_id = $3
       RETURNING mgm.id`,
      [memberId, groupId, communityId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Mirror group member not found'));
    }

    logger.audit('Mirror group member removed', {
      adminId: req.user.id,
      communityId,
      groupId,
      memberId,
    });

    res.json({ success: true, message: 'Member removed' });
  } catch (err) {
    next(err);
  }
}

// ===== Reputation Configuration Endpoints =====

/**
 * Get reputation configuration for community
 */
export async function getReputationConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const result = await query(
      `SELECT is_premium, chat_message, command_usage, giveaway_entry, follow,
              subscription, subscription_tier2, subscription_tier3, gift_subscription,
              donation_per_dollar, cheer_per_100bits, raid, boost,
              warn, timeout, kick, ban,
              auto_ban_enabled, auto_ban_threshold, starting_score,
              min_score, max_score, created_at, updated_at
       FROM community_reputation_config
       WHERE community_id = $1`,
      [communityId]
    );

    if (result.rows.length === 0) {
      // Return defaults if no config exists
      return res.json({
        success: true,
        config: {
          isPremium: false,
          weights: {
            chatMessage: 0.01,
            commandUsage: -0.1,
            giveawayEntry: -1.0,
            follow: 1.0,
            subscription: 5.0,
            subscriptionTier2: 10.0,
            subscriptionTier3: 20.0,
            giftSubscription: 3.0,
            donationPerDollar: 1.0,
            cheerPer100Bits: 1.0,
            raid: 2.0,
            boost: 5.0,
            warn: -25.0,
            timeout: -50.0,
            kick: -75.0,
            ban: -200.0,
          },
          policy: {
            autoBanEnabled: false,
            autoBanThreshold: 450,
            startingScore: 600,
            minScore: 300,
            maxScore: 850,
          },
          canCustomize: false,
        },
      });
    }

    const row = result.rows[0];
    res.json({
      success: true,
      config: {
        isPremium: row.is_premium,
        weights: {
          chatMessage: parseFloat(row.chat_message),
          commandUsage: parseFloat(row.command_usage),
          giveawayEntry: parseFloat(row.giveaway_entry),
          follow: parseFloat(row.follow),
          subscription: parseFloat(row.subscription),
          subscriptionTier2: parseFloat(row.subscription_tier2),
          subscriptionTier3: parseFloat(row.subscription_tier3),
          giftSubscription: parseFloat(row.gift_subscription),
          donationPerDollar: parseFloat(row.donation_per_dollar),
          cheerPer100Bits: parseFloat(row.cheer_per_100bits),
          raid: parseFloat(row.raid),
          boost: parseFloat(row.boost),
          warn: parseFloat(row.warn),
          timeout: parseFloat(row.timeout),
          kick: parseFloat(row.kick),
          ban: parseFloat(row.ban),
        },
        policy: {
          autoBanEnabled: row.auto_ban_enabled,
          autoBanThreshold: row.auto_ban_threshold,
          startingScore: row.starting_score,
          minScore: row.min_score,
          maxScore: row.max_score,
        },
        canCustomize: row.is_premium,
        updatedAt: row.updated_at?.toISOString(),
      },
    });
  } catch (err) {
    // If table doesn't exist yet (migration not run), return defaults
    if (err.code === '42P01') {
      return res.json({
        success: true,
        config: {
          isPremium: false,
          weights: {
            chatMessage: 0.01, commandUsage: -0.1, giveawayEntry: -1.0,
            follow: 1.0, subscription: 5.0, subscriptionTier2: 10.0,
            subscriptionTier3: 20.0, giftSubscription: 3.0,
            donationPerDollar: 1.0, cheerPer100Bits: 1.0,
            raid: 2.0, boost: 5.0, warn: -25.0, timeout: -50.0,
            kick: -75.0, ban: -200.0,
          },
          policy: {
            autoBanEnabled: false, autoBanThreshold: 450,
            startingScore: 600, minScore: 300, maxScore: 850,
          },
          canCustomize: false,
        },
      });
    }
    next(err);
  }
}

/**
 * Update reputation configuration
 * Weight customization requires premium subscription
 */
export async function updateReputationConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const { weights, policy } = req.body;

    // Check if config exists
    const existingResult = await query(
      `SELECT is_premium FROM community_reputation_config WHERE community_id = $1`,
      [communityId]
    );

    const isPremium = existingResult.rows.length > 0 ? existingResult.rows[0].is_premium : false;

    // If trying to update weights without premium, reject
    if (weights && Object.keys(weights).length > 0 && !isPremium) {
      return res.status(403).json({
        success: false,
        error: 'Weight customization requires premium subscription',
        upgradeRequired: true,
      });
    }

    // Build update query
    const updates = [];
    const params = [];
    let paramIndex = 1;

    // Weight fields (premium only)
    if (weights && isPremium) {
      const weightFields = {
        chatMessage: 'chat_message',
        commandUsage: 'command_usage',
        giveawayEntry: 'giveaway_entry',
        follow: 'follow',
        subscription: 'subscription',
        subscriptionTier2: 'subscription_tier2',
        subscriptionTier3: 'subscription_tier3',
        giftSubscription: 'gift_subscription',
        donationPerDollar: 'donation_per_dollar',
        cheerPer100Bits: 'cheer_per_100bits',
        raid: 'raid',
        boost: 'boost',
        warn: 'warn',
        timeout: 'timeout',
        kick: 'kick',
        ban: 'ban',
      };

      for (const [jsName, dbName] of Object.entries(weightFields)) {
        if (weights[jsName] !== undefined) {
          updates.push(`${dbName} = $${paramIndex}`);
          params.push(weights[jsName]);
          paramIndex++;
        }
      }
    }

    // Policy fields (available to all)
    if (policy) {
      if (policy.autoBanEnabled !== undefined) {
        updates.push(`auto_ban_enabled = $${paramIndex}`);
        params.push(policy.autoBanEnabled);
        paramIndex++;
      }
      if (policy.autoBanThreshold !== undefined) {
        const threshold = Math.max(REPUTATION_MIN, Math.min(REPUTATION_MAX, policy.autoBanThreshold));
        updates.push(`auto_ban_threshold = $${paramIndex}`);
        params.push(threshold);
        paramIndex++;
      }
      if (policy.startingScore !== undefined) {
        const score = Math.max(REPUTATION_MIN, Math.min(REPUTATION_MAX, policy.startingScore));
        updates.push(`starting_score = $${paramIndex}`);
        params.push(score);
        paramIndex++;
      }
    }

    if (updates.length === 0) {
      return res.json({ success: true, message: 'No changes to apply' });
    }

    updates.push('updated_at = NOW()');

    if (existingResult.rows.length === 0) {
      // Insert new config
      const insertFields = ['community_id', ...updates.map(u => u.split(' = ')[0])];
      const insertParams = [communityId, ...params];
      const placeholders = insertParams.map((_, i) => `$${i + 1}`).join(', ');

      await query(
        `INSERT INTO community_reputation_config (${insertFields.join(', ')})
         VALUES (${placeholders})`,
        insertParams
      );
    } else {
      // Update existing
      params.push(communityId);
      await query(
        `UPDATE community_reputation_config
         SET ${updates.join(', ')}
         WHERE community_id = $${paramIndex}`,
        params
      );
    }

    logger.audit('Reputation config updated', {
      adminId: req.user.id,
      communityId,
      updatedWeights: weights ? Object.keys(weights) : [],
      updatedPolicy: policy ? Object.keys(policy) : [],
    });

    res.json({ success: true, message: 'Configuration updated' });
  } catch (err) {
    next(err);
  }
}

/**
 * Get users at risk of auto-ban (near threshold)
 */
export async function getAtRiskUsers(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const buffer = Math.min(100, Math.max(10, parseInt(req.query.buffer || '50', 10)));

    // Get auto-ban threshold
    const configResult = await query(
      `SELECT auto_ban_threshold, auto_ban_enabled FROM community_reputation_config
       WHERE community_id = $1`,
      [communityId]
    );

    const threshold = configResult.rows.length > 0 ? configResult.rows[0].auto_ban_threshold : 450;
    const autoBanEnabled = configResult.rows.length > 0 ? configResult.rows[0].auto_ban_enabled : false;
    const warningThreshold = threshold + buffer;

    const result = await query(
      `SELECT cm.user_id, u.username, u.email, u.avatar_url, cm.reputation,
              $1 - cm.reputation as points_until_ban
       FROM community_members cm
       JOIN hub_users u ON u.id = cm.user_id::integer
       WHERE cm.community_id = $2 AND cm.is_active = true
       AND cm.reputation <= $3
       ORDER BY cm.reputation ASC
       LIMIT 50`,
      [threshold, communityId, warningThreshold]
    );

    const users = result.rows.map(row => ({
      userId: row.user_id,
      username: row.username,
      email: row.email,
      avatarUrl: row.avatar_url,
      reputation: formatReputation(row.reputation),
      pointsUntilBan: row.points_until_ban,
    }));

    res.json({
      success: true,
      autoBanEnabled,
      threshold,
      users,
      count: users.length,
    });
  } catch (err) {
    if (err.code === '42P01') {
      return res.json({ success: true, autoBanEnabled: false, threshold: 450, users: [], count: 0 });
    }
    next(err);
  }
}

/**
 * Get reputation leaderboard for community
 */
export async function getReputationLeaderboard(req, res, next) {
  const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '25', 10)));
  const offset = Math.max(0, parseInt(req.query.offset || '0', 10));

  try {
    const communityId = parseInt(req.params.communityId, 10);

    const result = await query(
      `SELECT cm.user_id, u.username, u.avatar_url, cm.reputation,
              RANK() OVER (ORDER BY cm.reputation DESC) as rank
       FROM community_members cm
       JOIN hub_users u ON u.id = cm.user_id::integer
       WHERE cm.community_id = $1 AND cm.is_active = true
       ORDER BY cm.reputation DESC
       LIMIT $2 OFFSET $3`,
      [communityId, limit, offset]
    );

    const users = result.rows.map(row => ({
      userId: row.user_id,
      username: row.username,
      avatarUrl: row.avatar_url,
      reputation: formatReputation(row.reputation),
      rank: parseInt(row.rank, 10),
    }));

    res.json({
      success: true,
      users,
      limit,
      offset,
      count: users.length,
    });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, users: [], limit, offset, count: 0 });
    }
    next(err);
  }
}

// ===== AI Researcher Admin Endpoints =====

/**
 * Get AI insights with pagination and type filter
 */
export async function getAIInsights(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '25', 10)));
    const offset = (page - 1) * limit;
    const insightType = req.query.type; // optional: stream_summary, weekly_rollup, bot_detection

    let whereClause = 'WHERE community_id = $1';
    const params = [communityId];
    let paramIndex = 2;

    if (insightType) {
      whereClause += ` AND insight_type = $${paramIndex}`;
      params.push(insightType);
      paramIndex++;
    }

    // Get total count
    const countResult = await query(
      `SELECT COUNT(*) as count FROM ai_insights ${whereClause}`,
      params
    );
    const total = parseInt(countResult.rows[0]?.count || 0, 10);

    // Get insights
    const result = await query(
      `SELECT id, insight_type, title, summary, metadata, created_at
       FROM ai_insights
       ${whereClause}
       ORDER BY created_at DESC
       LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`,
      [...params, limit, offset]
    );

    const insights = result.rows.map(row => ({
      id: row.id,
      insightType: row.insight_type,
      title: row.title,
      summary: row.summary,
      metadata: row.metadata || {},
      createdAt: row.created_at?.toISOString(),
    }));

    res.json({
      success: true,
      insights,
      pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
    });
  } catch (err) {
    if (err.code === '42P01') {
      return res.json({ success: true, insights: [], pagination: { page: 1, limit: 25, total: 0, totalPages: 0 } });
    }
    next(err);
  }
}

/**
 * Get single AI insight with full content
 */
export async function getAIInsight(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const insightId = parseInt(req.params.insightId, 10);

    const result = await query(
      `SELECT id, insight_type, title, summary, content, metadata, created_at
       FROM ai_insights
       WHERE id = $1 AND community_id = $2`,
      [insightId, communityId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('AI insight not found'));
    }

    const row = result.rows[0];
    res.json({
      success: true,
      insight: {
        id: row.id,
        insightType: row.insight_type,
        title: row.title,
        summary: row.summary,
        content: row.content,
        metadata: row.metadata || {},
        createdAt: row.created_at?.toISOString(),
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get AI researcher configuration for community
 */
export async function getAIResearcherConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const result = await query(
      `SELECT is_enabled, ai_provider, ai_model, custom_ai_endpoint,
              use_custom_endpoint, stream_summary_enabled,
              stream_summary_interval_hours, weekly_rollup_enabled, weekly_rollup_day,
              bot_detection_enabled, bot_detection_sensitivity, context_window_days,
              max_context_tokens, is_premium, created_at, updated_at
       FROM ai_researcher_config
       WHERE community_id = $1`,
      [communityId]
    );

    if (result.rows.length === 0) {
      // Return defaults if no config exists
      return res.json({
        success: true,
        config: {
          isEnabled: false,
          aiProvider: 'ollama',
          aiModel: 'tinyllama',
          streamSummary: {
            enabled: false,
            intervalHours: 6,
          },
          weeklyRollup: {
            enabled: false,
            day: 'sunday',
          },
          botDetection: {
            enabled: false,
            sensitivity: 'medium',
          },
          context: {
            windowDays: 7,
            maxTokens: 4000,
          },
          isPremium: false,
        },
      });
    }

    const row = result.rows[0];
    res.json({
      success: true,
      config: {
        isEnabled: row.is_enabled,
        aiProvider: row.ai_provider || 'ollama',
        aiModel: row.ai_model || 'tinyllama',
        customEndpoint: row.is_premium ? {
          url: row.custom_ai_endpoint || '',
          enabled: row.use_custom_endpoint || false,
          hasApiKey: !!row.custom_api_key_encrypted
        } : null,
        streamSummary: {
          enabled: row.stream_summary_enabled,
          intervalHours: row.stream_summary_interval_hours,
        },
        weeklyRollup: {
          enabled: row.weekly_rollup_enabled,
          day: row.weekly_rollup_day,
        },
        botDetection: {
          enabled: row.bot_detection_enabled,
          sensitivity: row.bot_detection_sensitivity,
        },
        context: {
          windowDays: row.context_window_days,
          maxTokens: row.max_context_tokens,
        },
        isPremium: row.is_premium,
        updatedAt: row.updated_at?.toISOString(),
      },
    });
  } catch (err) {
    // If table doesn't exist yet (migration not run), return defaults
    if (err.code === '42P01') {
      return res.json({
        success: true,
        config: {
          isEnabled: false, aiProvider: 'ollama', aiModel: 'tinyllama',
          streamSummary: { enabled: false, intervalHours: 6 },
          weeklyRollup: { enabled: false, day: 'sunday' },
          botDetection: { enabled: false, sensitivity: 'medium' },
          context: { windowDays: 7, maxTokens: 4000 },
          isPremium: false,
        },
      });
    }
    next(err);
  }
}

/**
 * Update AI researcher configuration
 * Advanced features require premium subscription
 */
export async function updateAIResearcherConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const { isEnabled, aiProvider, aiModel, customEndpoint, streamSummary, weeklyRollup, botDetection, context } = req.body;

    // Check if config exists and get premium status
    const existingResult = await query(
      `SELECT is_premium FROM ai_researcher_config WHERE community_id = $1`,
      [communityId]
    );

    const isPremium = existingResult.rows.length > 0 ? existingResult.rows[0].is_premium : false;

    // Premium-only features
    const premiumFeatures = ['weeklyRollup', 'botDetection'];
    for (const feature of premiumFeatures) {
      if (req.body[feature] && !isPremium) {
        return res.status(403).json({
          success: false,
          error: `${feature} requires premium subscription`,
          upgradeRequired: true,
        });
      }
    }

    // Build update query
    const updates = [];
    const params = [];
    let paramIndex = 1;

    if (isEnabled !== undefined) {
      updates.push(`is_enabled = $${paramIndex}`);
      params.push(isEnabled);
      paramIndex++;
    }

    if (aiProvider !== undefined) {
      const validProviders = ['ollama', 'openai', 'anthropic', 'gemini'];
      if (!validProviders.includes(aiProvider)) {
        return next(errors.badRequest('Invalid AI provider'));
      }
      updates.push(`ai_provider = $${paramIndex}`);
      params.push(aiProvider);
      paramIndex++;
    }

    if (aiModel !== undefined) {
      updates.push(`ai_model = $${paramIndex}`);
      params.push(aiModel);
      paramIndex++;
    }

    // Custom endpoint (premium only)
    if (customEndpoint && isPremium) {
      if (customEndpoint.url !== undefined) {
        updates.push(`custom_ai_endpoint = $${paramIndex}`);
        params.push(customEndpoint.url || null);
        paramIndex++;
      }
      if (customEndpoint.enabled !== undefined) {
        updates.push(`use_custom_endpoint = $${paramIndex}`);
        params.push(customEndpoint.enabled);
        paramIndex++;
      }
      if (customEndpoint.apiKey !== undefined) {
        if (customEndpoint.apiKey) {
          // Encrypt and store API key
          const encrypted = encryptData(customEndpoint.apiKey);
          updates.push(`custom_api_key_encrypted = $${paramIndex}`);
          params.push(encrypted);
          paramIndex++;
        } else {
          // Clear API key
          updates.push(`custom_api_key_encrypted = NULL`);
        }
      }
    } else if (customEndpoint && !isPremium) {
      return res.status(403).json({
        success: false,
        error: 'Custom AI endpoints require premium subscription',
        upgradeRequired: true,
      });
    }

    if (streamSummary) {
      if (streamSummary.enabled !== undefined) {
        updates.push(`stream_summary_enabled = $${paramIndex}`);
        params.push(streamSummary.enabled);
        paramIndex++;
      }
      if (streamSummary.intervalHours !== undefined) {
        const hours = Math.max(1, Math.min(24, streamSummary.intervalHours));
        updates.push(`stream_summary_interval_hours = $${paramIndex}`);
        params.push(hours);
        paramIndex++;
      }
    }

    if (weeklyRollup && isPremium) {
      if (weeklyRollup.enabled !== undefined) {
        updates.push(`weekly_rollup_enabled = $${paramIndex}`);
        params.push(weeklyRollup.enabled);
        paramIndex++;
      }
      if (weeklyRollup.day !== undefined) {
        const validDays = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
        if (!validDays.includes(weeklyRollup.day)) {
          return next(errors.badRequest('Invalid day of week'));
        }
        updates.push(`weekly_rollup_day = $${paramIndex}`);
        params.push(weeklyRollup.day);
        paramIndex++;
      }
    }

    if (botDetection && isPremium) {
      if (botDetection.enabled !== undefined) {
        updates.push(`bot_detection_enabled = $${paramIndex}`);
        params.push(botDetection.enabled);
        paramIndex++;
      }
      if (botDetection.sensitivity !== undefined) {
        const validLevels = ['low', 'medium', 'high'];
        if (!validLevels.includes(botDetection.sensitivity)) {
          return next(errors.badRequest('Invalid sensitivity level'));
        }
        updates.push(`bot_detection_sensitivity = $${paramIndex}`);
        params.push(botDetection.sensitivity);
        paramIndex++;
      }
    }

    if (context) {
      if (context.windowDays !== undefined) {
        const days = Math.max(1, Math.min(30, context.windowDays));
        updates.push(`context_window_days = $${paramIndex}`);
        params.push(days);
        paramIndex++;
      }
      if (context.maxTokens !== undefined && isPremium) {
        const tokens = Math.max(1000, Math.min(16000, context.maxTokens));
        updates.push(`max_context_tokens = $${paramIndex}`);
        params.push(tokens);
        paramIndex++;
      }
    }

    if (updates.length === 0) {
      return res.json({ success: true, message: 'No changes to apply' });
    }

    updates.push('updated_at = NOW()');

    if (existingResult.rows.length === 0) {
      // Insert new config with defaults
      const insertFields = ['community_id', ...updates.map(u => u.split(' = ')[0])];
      const insertParams = [communityId, ...params];
      const placeholders = insertParams.map((_, i) => `$${i + 1}`).join(', ');

      await query(
        `INSERT INTO ai_researcher_config (${insertFields.join(', ')})
         VALUES (${placeholders})`,
        insertParams
      );
    } else {
      // Update existing
      params.push(communityId);
      await query(
        `UPDATE ai_researcher_config
         SET ${updates.join(', ')}
         WHERE community_id = $${paramIndex}`,
        params
      );
    }

    logger.audit('AI researcher config updated', {
      adminId: req.user.id,
      communityId,
      updatedFields: Object.keys(req.body),
    });

    res.json({ success: true, message: 'Configuration updated' });
  } catch (err) {
    next(err);
  }
}

/**
 * Get available AI models and providers
 */
export async function getAvailableAIModels(req, res, next) {
  try {
    const models = {
      ollama: [],
      openai: [
        { id: 'gpt-4o', name: 'GPT-4o', description: 'Most capable model' },
        { id: 'gpt-4o-mini', name: 'GPT-4o Mini', description: 'Fast and affordable' },
        { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', description: 'Previous generation' },
        { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', description: 'Fast and economical' }
      ],
      anthropic: [
        { id: 'claude-opus-4-5-20251101', name: 'Claude Opus 4.5', description: 'Most capable model' },
        { id: 'claude-sonnet-4-5-20250929', name: 'Claude Sonnet 4.5', description: 'Balanced performance' },
        { id: 'claude-haiku-4-20250924', name: 'Claude Haiku 4', description: 'Fast and efficient' }
      ],
      gemini: [
        { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', description: 'Fast and multimodal' },
        { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', description: 'Most capable' },
        { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash', description: 'Fast and efficient' }
      ]
    };

    // Fetch Ollama models if Ollama is available
    try {
      const ollamaUrl = process.env.OLLAMA_URL || 'http://ollama:11434';
      const response = await fetch(`${ollamaUrl}/api/tags`);
      if (response.ok) {
        const data = await response.json();
        models.ollama = data.models.map(m => ({
          id: m.name,
          name: m.name,
          description: `Size: ${(m.size / 1e9).toFixed(1)}GB`,
          modified: m.modified_at
        }));
      }
    } catch (err) {
      logger.warn('Failed to fetch Ollama models', { error: err.message });
      // Default Ollama models if service is unavailable
      models.ollama = [
        { id: 'tinyllama', name: 'TinyLlama', description: 'Lightweight 1.1B model' },
        { id: 'llama3.2', name: 'Llama 3.2', description: '3B parameter model' },
        { id: 'llama3.1', name: 'Llama 3.1', description: '8B parameter model' },
        { id: 'mistral', name: 'Mistral', description: '7B parameter model' }
      ];
    }

    res.json({
      success: true,
      data: models
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get bot detection results with filters
 */
export async function getBotDetectionResults(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '25', 10)));
    const offset = (page - 1) * limit;
    const status = req.query.status; // optional: pending, reviewed, dismissed
    const minConfidence = parseFloat(req.query.minConfidence || '0');

    let whereClause = 'WHERE community_id = $1';
    const params = [communityId];
    let paramIndex = 2;

    if (status) {
      whereClause += ` AND review_status = $${paramIndex}`;
      params.push(status);
      paramIndex++;
    }

    if (minConfidence > 0) {
      whereClause += ` AND confidence >= $${paramIndex}`;
      params.push(minConfidence);
      paramIndex++;
    }

    // Get total count
    const countResult = await query(
      `SELECT COUNT(*) as count FROM bot_detection_results ${whereClause}`,
      params
    );
    const total = parseInt(countResult.rows[0]?.count || 0, 10);

    // Get results
    const result = await query(
      `SELECT bdr.id, bdr.user_id, bdr.username, bdr.confidence, bdr.reasons,
              bdr.review_status, bdr.review_action, bdr.review_notes,
              bdr.detected_at, bdr.reviewed_at, bdr.reviewed_by,
              u.username as reviewed_by_username
       FROM bot_detection_results bdr
       LEFT JOIN hub_users u ON u.id = bdr.reviewed_by
       ${whereClause}
       ORDER BY bdr.confidence DESC, bdr.detected_at DESC
       LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`,
      [...params, limit, offset]
    );

    const results = result.rows.map(row => ({
      id: row.id,
      userId: row.user_id,
      username: row.username,
      confidence: parseFloat(row.confidence),
      reasons: row.reasons || [],
      reviewStatus: row.review_status,
      reviewAction: row.review_action,
      reviewNotes: row.review_notes,
      detectedAt: row.detected_at?.toISOString(),
      reviewedAt: row.reviewed_at?.toISOString(),
      reviewedBy: row.reviewed_by_username,
    }));

    res.json({
      success: true,
      results,
      pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
    });
  } catch (err) {
    // If table doesn't exist yet (migration not run), return empty results
    if (err.code === '42P01') {
      return res.json({
        success: true,
        results: [],
        pagination: { page: 1, limit: 25, total: 0, totalPages: 0 },
      });
    }
    next(err);
  }
}

/**
 * Admin review of bot detection result
 */
export async function reviewBotDetection(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const resultId = parseInt(req.params.resultId, 10);
    const { action, notes } = req.body;

    // Validate action
    const validActions = ['ban', 'monitor', 'dismiss', 'false_positive'];
    if (!action || !validActions.includes(action)) {
      return next(errors.badRequest(`Invalid action. Must be one of: ${validActions.join(', ')}`));
    }

    // Verify the result belongs to this community
    const checkResult = await query(
      `SELECT id, user_id FROM bot_detection_results
       WHERE id = $1 AND community_id = $2`,
      [resultId, communityId]
    );

    if (checkResult.rows.length === 0) {
      return next(errors.notFound('Bot detection result not found'));
    }

    // Update the result
    await query(
      `UPDATE bot_detection_results
       SET review_status = 'reviewed', review_action = $1, review_notes = $2,
           reviewed_at = NOW(), reviewed_by = $3
       WHERE id = $4`,
      [action, notes || null, req.user.id, resultId]
    );

    logger.audit('Bot detection reviewed', {
      adminId: req.user.id,
      communityId,
      resultId,
      action,
      userId: checkResult.rows[0].user_id,
    });

    res.json({ success: true, message: 'Review recorded' });
  } catch (err) {
    next(err);
  }
}

/**
 * Get current AI context visualization data
 */
export async function getAIContext(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    // Get config to determine context window
    const configResult = await query(
      `SELECT context_window_days FROM ai_researcher_config WHERE community_id = $1`,
      [communityId]
    );
    const windowDays = configResult.rows.length > 0 ? configResult.rows[0].context_window_days : 7;

    // Get context stats
    const statsResult = await query(
      `SELECT
         COUNT(DISTINCT user_id) as active_users,
         COUNT(*) as total_messages,
         COUNT(DISTINCT DATE(created_at)) as active_days
       FROM chat_messages
       WHERE community_id = $1
       AND created_at >= NOW() - INTERVAL '${windowDays} days'`,
      [communityId]
    );

    // Get top users
    const topUsersResult = await query(
      `SELECT user_id, username, COUNT(*) as message_count
       FROM chat_messages
       WHERE community_id = $1
       AND created_at >= NOW() - INTERVAL '${windowDays} days'
       GROUP BY user_id, username
       ORDER BY message_count DESC
       LIMIT 10`,
      [communityId]
    );

    // Get activity by hour
    const activityResult = await query(
      `SELECT EXTRACT(HOUR FROM created_at) as hour, COUNT(*) as count
       FROM chat_messages
       WHERE community_id = $1
       AND created_at >= NOW() - INTERVAL '${windowDays} days'
       GROUP BY hour
       ORDER BY hour`,
      [communityId]
    );

    const stats = statsResult.rows[0] || { active_users: 0, total_messages: 0, active_days: 0 };
    const topUsers = topUsersResult.rows.map(row => ({
      userId: row.user_id,
      username: row.username,
      messageCount: parseInt(row.message_count, 10),
    }));
    const activityByHour = activityResult.rows.map(row => ({
      hour: parseInt(row.hour, 10),
      count: parseInt(row.count, 10),
    }));

    res.json({
      success: true,
      context: {
        windowDays,
        stats: {
          activeUsers: parseInt(stats.active_users, 10),
          totalMessages: parseInt(stats.total_messages, 10),
          activeDays: parseInt(stats.active_days, 10),
        },
        topUsers,
        activityByHour,
      },
    });
  } catch (err) {
    // If table doesn't exist yet (migration not run), return empty context
    if (err.code === '42P01') {
      return res.json({
        success: true,
        context: {
          windowDays: 7,
          stats: { activeUsers: 0, totalMessages: 0, activeDays: 0 },
          topUsers: [],
          activityByHour: [],
        },
      });
    }
    next(err);
  }
}

// ===== Bot Detection Score Endpoints =====

/**
 * Get bot detection score for community
 * Returns cached score from analytics_bot_scores table
 */
export async function getBotScore(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const result = await query(
      `SELECT score, grade, bad_actor_score, reputation_score, security_score,
              ai_behavioral_score, suspected_bot_count, high_confidence_bot_count,
              total_users_analyzed, community_size_category, calculation_metadata,
              calculated_at
       FROM analytics_bot_scores
       WHERE community_id = $1`,
      [communityId]
    );

    if (result.rows.length === 0) {
      // Return default/uncalculated state
      return res.json({
        success: true,
        botScore: {
          score: null,
          grade: null,
          message: 'Bot score not yet calculated',
          isCalculated: false,
        },
      });
    }

    const row = result.rows[0];
    res.json({
      success: true,
      botScore: {
        score: row.score,
        grade: row.grade,
        isCalculated: true,
        factors: {
          badActor: row.bad_actor_score,
          reputation: row.reputation_score,
          security: row.security_score,
          aiBehavioral: row.ai_behavioral_score,
        },
        stats: {
          suspectedBotCount: row.suspected_bot_count,
          highConfidenceBotCount: row.high_confidence_bot_count,
          totalUsersAnalyzed: row.total_users_analyzed,
          communitySizeCategory: row.community_size_category,
        },
        metadata: row.calculation_metadata || {},
        calculatedAt: row.calculated_at?.toISOString(),
      },
    });
  } catch (err) {
    if (err.code === '42P01') {
      return res.json({
        success: true,
        botScore: { score: null, grade: null, message: 'Bot score not yet calculated', isCalculated: false },
      });
    }
    next(err);
  }
}

/**
 * Get suspected bots for community (Premium feature)
 * Returns list of users flagged as potential bots with confidence scores
 */
export async function getSuspectedBots(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '50', 10)));
    const minConfidence = Math.max(0, Math.min(100, parseInt(req.query.minConfidence || '50', 10)));

    const result = await query(
      `SELECT id, platform, platform_user_id, username, confidence_score,
              detection_reasons, ai_analysis, behavioral_flags,
              is_false_positive, reviewed_by, reviewed_at,
              first_detected_at, last_detected_at
       FROM analytics_suspected_bots
       WHERE community_id = $1
       AND confidence_score >= $2
       AND (is_false_positive IS NULL OR is_false_positive = false)
       ORDER BY confidence_score DESC
       LIMIT $3`,
      [communityId, minConfidence, limit]
    );

    const suspectedBots = result.rows.map(row => ({
      id: row.id,
      platform: row.platform,
      platformUserId: row.platform_user_id,
      username: row.username,
      confidenceScore: row.confidence_score,
      detectionReasons: row.detection_reasons || [],
      aiAnalysis: row.ai_analysis,
      behavioralFlags: row.behavioral_flags || [],
      isFalsePositive: row.is_false_positive,
      reviewedBy: row.reviewed_by,
      reviewedAt: row.reviewed_at?.toISOString(),
      firstDetectedAt: row.first_detected_at?.toISOString(),
      lastDetectedAt: row.last_detected_at?.toISOString(),
    }));

    res.json({
      success: true,
      suspectedBots,
      count: suspectedBots.length,
      filters: { minConfidence, limit },
    });
  } catch (err) {
    if (err.code === '42P01') {
      return res.json({ success: true, suspectedBots: [], count: 0, filters: { minConfidence: 50, limit: 50 } });
    }
    next(err);
  }
}

/**
 * Review suspected bot (mark as false positive or confirmed)
 */
export async function reviewSuspectedBot(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const botId = parseInt(req.params.botId, 10);
    const { isFalsePositive } = req.body;

    if (typeof isFalsePositive !== 'boolean') {
      return res.status(400).json({
        success: false,
        error: 'isFalsePositive must be a boolean',
      });
    }

    const result = await query(
      `UPDATE analytics_suspected_bots
       SET is_false_positive = $1, reviewed_by = $2, reviewed_at = NOW()
       WHERE id = $3 AND community_id = $4
       RETURNING id, username`,
      [isFalsePositive, req.user.id, botId, communityId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'Suspected bot not found',
      });
    }

    logger.audit('Suspected bot reviewed', {
      adminId: req.user.id,
      communityId,
      botId,
      username: result.rows[0].username,
      isFalsePositive,
    });

    res.json({
      success: true,
      message: isFalsePositive ? 'Marked as false positive' : 'Confirmed as bot',
    });
  } catch (err) {
    next(err);
  }
}

// ===== Connected Platforms =====

/**
 * Get connected platforms summary for community.
 * Aggregates data from community_servers grouped by platform.
 */
export async function getConnectedPlatforms(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const result = await query(
      `SELECT platform, COUNT(*) as server_count,
              BOOL_OR(status = 'approved') as is_active
       FROM community_servers
       WHERE community_id = $1
       GROUP BY platform
       ORDER BY platform ASC`,
      [communityId]
    );

    const connectedPlatforms = result.rows.map(row => ({
      platform: row.platform,
      serverCount: parseInt(row.server_count, 10),
      isActive: row.is_active,
    }));

    res.json({ success: true, connectedPlatforms });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, connectedPlatforms: [] });
    }
    next(err);
  }
}

// ===== Shoutout Configuration =====

/**
 * Get shoutout configuration for a community
 */
export async function getShoutoutConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    let result = await query(
      `SELECT * FROM shoutout_config WHERE community_id = $1`,
      [communityId]
    );

    let config;
    if (result.rows.length === 0) {
      // Create default config
      const insertResult = await query(
        `INSERT INTO shoutout_config (community_id) VALUES ($1)
         RETURNING *`,
        [communityId]
      );
      config = formatShoutoutConfig(insertResult.rows[0]);
    } else {
      config = formatShoutoutConfig(result.rows[0]);
    }

    res.json({ success: true, config });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({
        success: true,
        config: {
          soEnabled: true, soPermission: 'mod', vsoEnabled: true, vsoPermission: 'mod',
          autoShoutoutMode: 'disabled', triggerFirstMessage: false, triggerRaidHost: true,
          widgetPosition: 'bottom-right', widgetDurationSeconds: 30, cooldownMinutes: 60,
        },
      });
    }
    next(err);
  }
}

function formatShoutoutConfig(row) {
  return {
    soEnabled: row.so_enabled,
    soPermission: row.so_permission,
    vsoEnabled: row.vso_enabled,
    vsoPermission: row.vso_permission,
    autoShoutoutMode: row.auto_shoutout_mode,
    triggerFirstMessage: row.trigger_first_message,
    triggerRaidHost: row.trigger_raid_host,
    widgetPosition: row.widget_position,
    widgetDurationSeconds: row.widget_duration_seconds,
    cooldownMinutes: row.cooldown_minutes,
  };
}

/**
 * Update shoutout configuration for a community
 */
export async function updateShoutoutConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const {
      soEnabled, soPermission, vsoEnabled, vsoPermission,
      autoShoutoutMode, triggerFirstMessage, triggerRaidHost,
      widgetPosition, widgetDurationSeconds, cooldownMinutes,
    } = req.body;

    const result = await query(
      `INSERT INTO shoutout_config
         (community_id, so_enabled, so_permission, vso_enabled, vso_permission,
          auto_shoutout_mode, trigger_first_message, trigger_raid_host,
          widget_position, widget_duration_seconds, cooldown_minutes)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
       ON CONFLICT (community_id)
       DO UPDATE SET
         so_enabled = EXCLUDED.so_enabled,
         so_permission = EXCLUDED.so_permission,
         vso_enabled = EXCLUDED.vso_enabled,
         vso_permission = EXCLUDED.vso_permission,
         auto_shoutout_mode = EXCLUDED.auto_shoutout_mode,
         trigger_first_message = EXCLUDED.trigger_first_message,
         trigger_raid_host = EXCLUDED.trigger_raid_host,
         widget_position = EXCLUDED.widget_position,
         widget_duration_seconds = EXCLUDED.widget_duration_seconds,
         cooldown_minutes = EXCLUDED.cooldown_minutes,
         updated_at = NOW()
       RETURNING *`,
      [communityId, soEnabled, soPermission, vsoEnabled, vsoPermission,
       autoShoutoutMode, triggerFirstMessage, triggerRaidHost,
       widgetPosition, widgetDurationSeconds, cooldownMinutes]
    );

    logger.audit('Shoutout config updated', {
      adminId: req.user.id,
      communityId,
    });

    res.json({ success: true, config: formatShoutoutConfig(result.rows[0]) });
  } catch (err) {
    next(err);
  }
}

/**
 * Get shoutout creators list for a community
 */
export async function getShoutoutCreators(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const result = await query(
      `SELECT id, platform, platform_username, added_by, created_at
       FROM shoutout_creators
       WHERE community_id = $1
       ORDER BY created_at DESC`,
      [communityId]
    );

    const creators = result.rows.map(row => ({
      id: row.id,
      platform: row.platform,
      platformUsername: row.platform_username,
      addedBy: row.added_by,
      createdAt: row.created_at?.toISOString(),
    }));

    res.json({ success: true, creators });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, creators: [] });
    }
    next(err);
  }
}

/**
 * Add a creator to the shoutout list
 */
export async function addShoutoutCreator(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const { platform, username } = req.body;

    if (!platform || !username) {
      return next(errors.badRequest('Platform and username are required'));
    }

    const result = await query(
      `INSERT INTO shoutout_creators (community_id, platform, platform_username, added_by)
       VALUES ($1, $2, $3, $4)
       ON CONFLICT (community_id, platform, platform_username) DO NOTHING
       RETURNING id, platform, platform_username, created_at`,
      [communityId, platform, username.trim(), req.user.id]
    );

    if (result.rows.length === 0) {
      return next(errors.conflict('Creator already in list'));
    }

    logger.audit('Shoutout creator added', {
      adminId: req.user.id,
      communityId,
      platform,
      username,
    });

    res.json({
      success: true,
      creator: {
        id: result.rows[0].id,
        platform: result.rows[0].platform,
        platformUsername: result.rows[0].platform_username,
        createdAt: result.rows[0].created_at?.toISOString(),
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Remove a creator from the shoutout list
 */
export async function removeShoutoutCreator(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const creatorId = parseInt(req.params.creatorId, 10);

    const result = await query(
      `DELETE FROM shoutout_creators WHERE id = $1 AND community_id = $2
       RETURNING platform, platform_username`,
      [creatorId, communityId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Creator not found'));
    }

    logger.audit('Shoutout creator removed', {
      adminId: req.user.id,
      communityId,
      creatorId,
      platform: result.rows[0].platform,
      username: result.rows[0].platform_username,
    });

    res.json({ success: true, message: 'Creator removed' });
  } catch (err) {
    next(err);
  }
}

/**
 * Get shoutout history for a community
 */
export async function getShoutoutHistory(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '25', 10)));
    const offset = (page - 1) * limit;

    const countResult = await query(
      'SELECT COUNT(*) as count FROM shoutout_history WHERE community_id = $1',
      [communityId]
    );
    const total = parseInt(countResult.rows[0]?.count || 0, 10);

    const result = await query(
      `SELECT id, platform, target_username, shoutout_type, triggered_by_username,
              trigger_type, created_at
       FROM shoutout_history
       WHERE community_id = $1
       ORDER BY created_at DESC
       LIMIT $2 OFFSET $3`,
      [communityId, limit, offset]
    );

    const history = result.rows.map(row => ({
      id: row.id,
      platform: row.platform,
      targetUsername: row.target_username,
      shoutoutType: row.shoutout_type,
      triggeredBy: row.triggered_by_username,
      triggerType: row.trigger_type,
      createdAt: row.created_at?.toISOString(),
    }));

    res.json({
      success: true,
      history,
      pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
    });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, history: [], pagination: { page: 1, limit: 25, total: 0, totalPages: 0 } });
    }
    next(err);
  }
}

/**
 * Get translation configuration for a community
 */
export async function getTranslationConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    // Get or create default config
    let result = await query(
      `SELECT id, enabled, target_language, confidence_threshold, min_words,
              detection_method, google_api_key, preprocessing, captions, ai_decision
       FROM community_translation_settings
       WHERE community_id = $1`,
      [communityId]
    );

    let config;

    if (result.rows.length === 0) {
      // Create default configuration
      const defaultConfig = {
        enabled: false,
        target_language: 'en',
        confidence_threshold: 0.7,
        min_words: 5,
        detection_method: 'ensemble',
        preprocessing: {
          enabled: true,
          preserve_mentions: true,
          preserve_commands: true,
          preserve_emails: true,
          preserve_urls: true,
          preserve_emotes: true,
          emote_sources: ['global', 'bttv', 'ffz', '7tv'],
        },
        captions: {
          enabled: false,
          display_duration: 5000,
          max_captions: 3,
          show_original: false,
        },
        ai_decision: {
          mode: 'never',
          confidence_threshold: 0.7,
        },
      };

      const insertResult = await query(
        `INSERT INTO community_translation_settings
         (community_id, enabled, target_language, confidence_threshold, min_words,
          detection_method, preprocessing, captions, ai_decision, created_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
         RETURNING id, enabled, target_language, confidence_threshold, min_words,
                   detection_method, preprocessing, captions, ai_decision`,
        [
          communityId,
          defaultConfig.enabled,
          defaultConfig.target_language,
          defaultConfig.confidence_threshold,
          defaultConfig.min_words,
          defaultConfig.detection_method,
          JSON.stringify(defaultConfig.preprocessing),
          JSON.stringify(defaultConfig.captions),
          JSON.stringify(defaultConfig.ai_decision),
        ]
      );

      config = {
        id: insertResult.rows[0].id,
        enabled: insertResult.rows[0].enabled,
        target_language: insertResult.rows[0].target_language,
        confidence_threshold: parseFloat(insertResult.rows[0].confidence_threshold) || 0.7,
        min_words: parseInt(insertResult.rows[0].min_words, 10) || 5,
        detection_method: insertResult.rows[0].detection_method,
        preprocessing: safeJsonParse(insertResult.rows[0].preprocessing),
        captions: safeJsonParse(insertResult.rows[0].captions),
        ai_decision: safeJsonParse(insertResult.rows[0].ai_decision),
      };
    } else {
      const row = result.rows[0];
      config = {
        id: row.id,
        enabled: row.enabled,
        target_language: row.target_language,
        confidence_threshold: parseFloat(row.confidence_threshold) || 0.7,
        min_words: parseInt(row.min_words, 10) || 5,
        detection_method: row.detection_method,
        preprocessing: safeJsonParse(row.preprocessing),
        captions: safeJsonParse(row.captions),
        ai_decision: safeJsonParse(row.ai_decision),
      };
    }

    res.json({
      success: true,
      config,
    });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({
        success: true,
        config: {
          enabled: false,
          target_language: 'en',
          confidence_threshold: 0.7,
          min_words: 5,
          detection_method: 'ensemble',
          preprocessing: {},
          captions: {},
          ai_decision: { mode: 'never' },
        },
      });
    }
    next(err);
  }
}

/**
 * Update translation configuration for a community
 */
export async function updateTranslationConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const {
      enabled,
      target_language,
      confidence_threshold,
      min_words,
      detection_method,
      preprocessing,
      captions,
      ai_decision,
    } = req.body;

    // Validate inputs
    if (typeof enabled !== 'boolean') {
      return res.status(400).json({
        success: false,
        error: 'enabled must be a boolean',
      });
    }

    if (!target_language || typeof target_language !== 'string') {
      return res.status(400).json({
        success: false,
        error: 'target_language is required and must be a string',
      });
    }

    if (typeof confidence_threshold !== 'number' || confidence_threshold < 0.5 || confidence_threshold > 1.0) {
      return res.status(400).json({
        success: false,
        error: 'confidence_threshold must be between 0.5 and 1.0',
      });
    }

    if (typeof min_words !== 'number' || min_words < 1 || min_words > 20) {
      return res.status(400).json({
        success: false,
        error: 'min_words must be between 1 and 20',
      });
    }

    if (!['ensemble', 'fasttext_only', 'provider'].includes(detection_method)) {
      return res.status(400).json({
        success: false,
        error: 'detection_method must be one of: ensemble, fasttext_only, provider',
      });
    }

    // Update or insert
    const result = await query(
      `INSERT INTO community_translation_settings
       (community_id, enabled, target_language, confidence_threshold, min_words,
        detection_method, preprocessing, captions, ai_decision, updated_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
       ON CONFLICT (community_id)
       DO UPDATE SET
         enabled = $2,
         target_language = $3,
         confidence_threshold = $4,
         min_words = $5,
         detection_method = $6,
         preprocessing = $7,
         captions = $8,
         ai_decision = $9,
         updated_at = NOW()
       RETURNING id, enabled, target_language, confidence_threshold, min_words,
                 detection_method, preprocessing, captions, ai_decision`,
      [
        communityId,
        enabled,
        target_language,
        confidence_threshold,
        min_words,
        detection_method,
        JSON.stringify(preprocessing),
        JSON.stringify(captions),
        JSON.stringify(ai_decision),
      ]
    );

    const row = result.rows[0];
    const config = {
      id: row.id,
      enabled: row.enabled,
      target_language: row.target_language,
      confidence_threshold: row.confidence_threshold,
      min_words: row.min_words,
      detection_method: row.detection_method,
      preprocessing: safeJsonParse(row.preprocessing),
      captions: safeJsonParse(row.captions),
      ai_decision: safeJsonParse(row.ai_decision),
    };

    logger.audit('Translation settings updated', {
      adminId: req.user.id,
      communityId,
      detection_method,
    });

    res.json({
      success: true,
      config,
    });
  } catch (err) {
    next(err);
  }
}
