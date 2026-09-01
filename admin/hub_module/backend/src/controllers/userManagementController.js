/**
 * User Management Controller - Platform-level user CRUD operations for super admins
 */
import bcrypt from 'bcrypt';
import { query, transaction } from '../config/database.js';
import { errors } from '../middleware/errorHandler.js';
import crypto from 'crypto';
import { logger } from '../utils/logger.js';

const SALT_ROUNDS = 10;

/**
 * List all hub users with pagination, search, and filtering
 */
export async function listUsers(req, res, next) {
  try {
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '25', 10)));
    const offset = (page - 1) * limit;
    const search = req.query.search || '';
    const role = req.query.role; // 'super_admin', 'vendor', 'user'
    const isActive = req.query.isActive;

    let whereClause = 'WHERE 1=1';
    const params = [];
    let paramIndex = 1;

    if (search) {
      whereClause += ` AND (email ILIKE $${paramIndex} OR username ILIKE $${paramIndex})`;
      params.push(`%${search}%`);
      paramIndex++;
    }

    if (role === 'super_admin') {
      whereClause += ` AND is_super_admin = true`;
    } else if (role === 'vendor') {
      whereClause += ` AND is_vendor = true`;
    }

    if (isActive !== undefined) {
      whereClause += ` AND is_active = $${paramIndex}`;
      params.push(isActive === 'true');
      paramIndex++;
    }

    const countResult = await query(
      `SELECT COUNT(*) as count FROM hub_users ${whereClause}`,
      params
    );
    const total = parseInt(countResult.rows[0]?.count || 0, 10);

    const result = await query(
      `SELECT id, email, username, avatar_url, is_active, is_super_admin, is_vendor,
              email_verified, created_at, updated_at
       FROM hub_users
       ${whereClause}
       ORDER BY created_at DESC
       LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`,
      [...params, limit, offset]
    );

    const users = result.rows.map(row => ({
      id: row.id,
      email: row.email,
      username: row.username,
      avatarUrl: row.avatar_url,
      isActive: row.is_active,
      isSuperAdmin: row.is_super_admin,
      isVendor: row.is_vendor,
      emailVerified: row.email_verified,
      createdAt: row.created_at?.toISOString(),
      updatedAt: row.updated_at?.toISOString(),
    }));

    logger.audit('List users', {
      community: 'platform',
      user: req.user.id,
      action: 'list_users',
      result: 'success',
      count: users.length,
    });

    res.json({
      success: true,
      users,
      pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get single user details
 */
export async function getUser(req, res, next) {
  try {
    const userId = parseInt(req.params.userId, 10);

    const result = await query(
      `SELECT id, email, username, avatar_url, is_active, is_super_admin, is_vendor,
              email_verified, created_at, updated_at
       FROM hub_users WHERE id = $1`,
      [userId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('User not found'));
    }

    const row = result.rows[0];
    const user = {
      id: row.id,
      email: row.email,
      username: row.username,
      avatarUrl: row.avatar_url,
      isActive: row.is_active,
      isSuperAdmin: row.is_super_admin,
      isVendor: row.is_vendor,
      emailVerified: row.email_verified,
      createdAt: row.created_at?.toISOString(),
      updatedAt: row.updated_at?.toISOString(),
    };

    logger.audit('Get user', {
      community: 'platform',
      user: req.user.id,
      action: 'get_user',
      targetUser: userId,
      result: 'success',
    });

    res.json({ success: true, user });
  } catch (err) {
    next(err);
  }
}

/**
 * Create new local user
 * Username is automatically set to email for unified identity
 */
export async function createUser(req, res, next) {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return next(errors.badRequest('Email and password required'));
    }

    if (password.length < 8) {
      return next(errors.badRequest('Password must be at least 8 characters'));
    }

    // Check for duplicate email
    const existingResult = await query(
      'SELECT id FROM hub_users WHERE email = $1',
      [email]
    );

    if (existingResult.rows.length > 0) {
      return next(errors.conflict('Email already exists'));
    }

    // Hash password
    const passwordHash = await bcrypt.hash(password, SALT_ROUNDS);

    // Create user with transaction - username = email
    await transaction(async (client) => {
      await client.query(
        `INSERT INTO hub_users
         (email, username, password_hash, is_active, email_verified, created_at, updated_at)
         VALUES ($1, $1, $2, $3, $4, NOW(), NOW())`,
        [email, passwordHash, true, false]
      );
    });

    // Fetch created user
    const result = await query(
      `SELECT id, email, username, is_active, is_super_admin, is_vendor, email_verified, created_at
       FROM hub_users WHERE email = $1`,
      [email]
    );

    const row = result.rows[0];
    const user = {
      id: row.id,
      email: row.email,
      username: row.username,
      isActive: row.is_active,
      isSuperAdmin: row.is_super_admin,
      isVendor: row.is_vendor,
      emailVerified: row.email_verified,
      createdAt: row.created_at?.toISOString(),
    };

    logger.audit('Create user', {
      community: 'platform',
      user: req.user.id,
      action: 'create_user',
      newUser: email,
      result: 'success',
    });

    res.status(201).json({ success: true, user });
  } catch (err) {
    next(err);
  }
}

/**
 * Update user (email, active status)
 * Username is always synced to email for unified identity
 */
export async function updateUser(req, res, next) {
  try {
    const userId = parseInt(req.params.userId, 10);
    const { email, isActive } = req.body;

    if (!email && isActive === undefined) {
      return next(errors.badRequest('At least one field to update is required'));
    }

    // Get current user
    const currentResult = await query(
      'SELECT email FROM hub_users WHERE id = $1',
      [userId]
    );

    if (currentResult.rows.length === 0) {
      return next(errors.notFound('User not found'));
    }

    const current = currentResult.rows[0];
    let updateFields = [];
    let values = [];
    let paramIndex = 1;

    if (email && email !== current.email) {
      // Check if email already exists
      const checkEmail = await query(
        'SELECT id FROM hub_users WHERE email = $1 AND id != $2',
        [email, userId]
      );
      if (checkEmail.rows.length > 0) {
        return next(errors.conflict('Email already in use'));
      }
      // Update both email and username together
      updateFields.push(`email = $${paramIndex}`);
      updateFields.push(`username = $${paramIndex}`);
      values.push(email);
      paramIndex++;
    }

    if (isActive !== undefined) {
      updateFields.push(`is_active = $${paramIndex}`);
      values.push(isActive);
      paramIndex++;
    }

    if (updateFields.length === 0) {
      return res.json({ success: true, message: 'No changes' });
    }

    updateFields.push(`updated_at = NOW()`);
    values.push(userId);

    await query(
      `UPDATE hub_users SET ${updateFields.join(', ')} WHERE id = $${paramIndex}`,
      values
    );

    // Fetch updated user
    const result = await query(
      `SELECT id, email, username, is_active, is_super_admin, is_vendor, created_at, updated_at
       FROM hub_users WHERE id = $1`,
      [userId]
    );

    const row = result.rows[0];
    const user = {
      id: row.id,
      email: row.email,
      username: row.username,
      isActive: row.is_active,
      isSuperAdmin: row.is_super_admin,
      isVendor: row.is_vendor,
      createdAt: row.created_at?.toISOString(),
      updatedAt: row.updated_at?.toISOString(),
    };

    logger.audit('Update user', {
      community: 'platform',
      user: req.user.id,
      action: 'update_user',
      targetUser: userId,
      result: 'success',
    });

    res.json({ success: true, user });
  } catch (err) {
    next(err);
  }
}

/**
 * Delete user (soft delete - set is_active to false)
 */
export async function deleteUser(req, res, next) {
  try {
    const userId = parseInt(req.params.userId, 10);

    // Prevent self-deletion
    if (userId === req.user.id) {
      return next(errors.forbidden('Cannot delete your own account'));
    }

    const result = await query(
      'SELECT id FROM hub_users WHERE id = $1',
      [userId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('User not found'));
    }

    await query(
      'UPDATE hub_users SET is_active = false, updated_at = NOW() WHERE id = $1',
      [userId]
    );

    logger.audit('Delete user', {
      community: 'platform',
      user: req.user.id,
      action: 'delete_user',
      targetUser: userId,
      result: 'success',
    });

    res.json({ success: true, message: 'User deleted' });
  } catch (err) {
    next(err);
  }
}

/**
 * Assign or revoke super admin role
 */
export async function assignSuperAdminRole(req, res, next) {
  try {
    const userId = parseInt(req.params.userId, 10);
    const { grant } = req.body;

    if (grant === undefined) {
      return next(errors.badRequest('Grant parameter required'));
    }

    const result = await query(
      'SELECT id, is_super_admin FROM hub_users WHERE id = $1',
      [userId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('User not found'));
    }

    const user = result.rows[0];
    if (user.is_super_admin === grant) {
      return res.json({
        success: true,
        message: `User already ${grant ? 'has' : 'does not have'} super admin role`,
      });
    }

    await query(
      'UPDATE hub_users SET is_super_admin = $1, updated_at = NOW() WHERE id = $2',
      [grant, userId]
    );

    logger.audit('Assign super admin role', {
      community: 'platform',
      user: req.user.id,
      action: 'assign_super_admin',
      targetUser: userId,
      grant,
      result: 'success',
    });

    res.json({
      success: true,
      message: `Super admin role ${grant ? 'granted' : 'revoked'}`,
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Assign or revoke vendor role
 */
export async function assignVendorRole(req, res, next) {
  try {
    const userId = parseInt(req.params.userId, 10);
    const { grant } = req.body;

    if (grant === undefined) {
      return next(errors.badRequest('Grant parameter required'));
    }

    const result = await query(
      'SELECT id, is_vendor FROM hub_users WHERE id = $1',
      [userId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('User not found'));
    }

    const user = result.rows[0];
    if (user.is_vendor === grant) {
      return res.json({
        success: true,
        message: `User already ${grant ? 'has' : 'does not have'} vendor role`,
      });
    }

    await query(
      'UPDATE hub_users SET is_vendor = $1, updated_at = NOW() WHERE id = $2',
      [grant, userId]
    );

    logger.audit('Assign vendor role', {
      community: 'platform',
      user: req.user.id,
      action: 'assign_vendor',
      targetUser: userId,
      grant,
      result: 'success',
    });

    res.json({
      success: true,
      message: `Vendor role ${grant ? 'granted' : 'revoked'}`,
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Set email verification status for a user
 */
export async function setEmailVerification(req, res, next) {
  try {
    const userId = parseInt(req.params.userId, 10);
    const { verified } = req.body;

    if (verified === undefined) {
      return next(errors.badRequest('Verified parameter required'));
    }

    const result = await query(
      'SELECT id, email_verified FROM hub_users WHERE id = $1',
      [userId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('User not found'));
    }

    const user = result.rows[0];
    if (user.email_verified === verified) {
      return res.json({
        success: true,
        message: `User email is already ${verified ? 'verified' : 'unverified'}`,
      });
    }

    if (verified) {
      // When verifying, also clear any pending verification token
      await query(
        `UPDATE hub_users
         SET email_verified = true, email_verification_token = NULL, updated_at = NOW()
         WHERE id = $1`,
        [userId]
      );
    } else {
      await query(
        'UPDATE hub_users SET email_verified = false, updated_at = NOW() WHERE id = $1',
        [userId]
      );
    }

    logger.audit('Set email verification', {
      community: 'platform',
      user: req.user.id,
      action: 'set_email_verification',
      targetUser: userId,
      verified,
      result: 'success',
    });

    res.json({
      success: true,
      message: `Email ${verified ? 'verified' : 'unverified'}`,
    });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /api/v1/superadmin/users/:userId/analytics-consumer-role
 * Toggle analytics consumer role for a user.
 */
export async function assignAnalyticsConsumerRole(req, res, next) {
  try {
    const userId = parseInt(req.params.userId, 10);
    const { enabled } = req.body;

    if (typeof enabled !== 'boolean') {
      return next(errors.badRequest('enabled (boolean) is required'));
    }

    const result = await query(
      'UPDATE hub_users SET is_analytics_consumer = $1, updated_at = NOW() WHERE id = $2 RETURNING id, email, username, is_analytics_consumer',
      [enabled, userId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('User not found'));
    }

    logger.audit('Toggle analytics consumer role', {
      community: 'platform',
      user: req.user.id,
      action: 'assign_analytics_consumer_role',
      result: 'success',
      targetUser: userId,
      enabled,
    });

    res.json({
      success: true,
      user: {
        id: result.rows[0].id,
        email: result.rows[0].email,
        username: result.rows[0].username,
        isAnalyticsConsumer: result.rows[0].is_analytics_consumer,
      },
    });
  } catch (err) {
    logger.error('Failed to toggle analytics consumer role', err);
    next(err);
  }
}

/**
 * GET /api/v1/superadmin/users/:userId/deletion-request
 * Read-only view of a user's data deletion status (for support).
 */
export async function getUserDeletionRequest(req, res, next) {
  try {
    const userId = parseInt(req.params.userId, 10);

    const result = await query(
      `SELECT requested_at, completed_at, status
       FROM data_deletion_requests
       WHERE hub_user_id = $1
       ORDER BY requested_at DESC
       LIMIT 1`,
      [userId]
    );

    res.json({
      success: true,
      deletion_request: result.rows[0] || null,
    });
  } catch (err) {
    logger.error('Failed to fetch deletion request', err);
    next(err);
  }
}

/**
 * Generate password reset token
 */
export async function generatePasswordReset(req, res, next) {
  try {
    const userId = parseInt(req.params.userId, 10);

    const result = await query(
      'SELECT id, email FROM hub_users WHERE id = $1',
      [userId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('User not found'));
    }

    const user = result.rows[0];

    // Generate reset token (random 32-char hex)
    const resetToken = crypto.randomBytes(16).toString('hex');
    const resetExpires = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 hours

    await query(
      `UPDATE hub_users
       SET password_reset_token = $1, password_reset_expires = $2, updated_at = NOW()
       WHERE id = $3`,
      [resetToken, resetExpires, userId]
    );

    logger.audit('Generate password reset', {
      community: 'platform',
      user: req.user.id,
      action: 'generate_password_reset',
      targetUser: userId,
      result: 'success',
    });

    res.json({
      success: true,
      message: 'Password reset token generated',
      resetToken, // In production, send this via email instead
      resetExpires: resetExpires.toISOString(),
    });
  } catch (err) {
    next(err);
  }
}
