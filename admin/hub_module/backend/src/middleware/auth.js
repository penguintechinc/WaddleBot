/**
 * Authentication Middleware
 * JWT verification, multi-tenancy, and scope-based access control
 */
import crypto from 'crypto';
import jwt from 'jsonwebtoken';
import { config } from '../config/index.js';
import { errors } from './errorHandler.js';
import { query } from '../config/database.js';
import { logger } from '../utils/logger.js';
import { resolveScopes, hasScope } from '../services/claimsService.js';

/**
 * Extract raw token string from request headers or cookie
 */
function extractToken(req) {
  const authHeader = req.headers.authorization;
  if (authHeader && authHeader.startsWith('Bearer ')) {
    return authHeader.substring(7);
  }
  return req.cookies?.token || null;
}

/**
 * Resolve a PAT (wdl_u_*) — sets req.user to the token owner, req.tokenScopeCeiling
 * Returns true if resolved, false if token not found / revoked / expired.
 */
async function resolvePAT(req, rawToken) {
  const hash = crypto.createHash('sha256').update(rawToken).digest('hex');
  const result = await query(
    `SELECT uat.*, hu.id as user_id, hu.display_name, hu.email,
            hu.is_super_admin as "isSuperAdmin"
     FROM user_access_tokens uat
     JOIN hub_users hu ON uat.user_id = hu.id
     WHERE uat.token_hash = $1
       AND uat.is_revoked = FALSE
       AND (uat.expires_at IS NULL OR uat.expires_at > NOW())`,
    [hash]
  );
  if (result.rows.length === 0) return false;

  const row = result.rows[0];
  req.user = {
    id: row.user_id,
    userId: row.user_id,
    email: row.email,
    display_name: row.display_name,
    isSuperAdmin: row.isSuperAdmin,
    roles: [],
    communityRoles: {},
  };
  req.tokenScopeCeiling = row.scope_ceiling || null;
  req.tokenType = 'pat';

  // Update last_used_at asynchronously (fire and forget)
  query('UPDATE user_access_tokens SET last_used_at = NOW() WHERE token_hash = $1', [hash])
    .catch(err => logger.warn('Failed to update PAT last_used_at', { error: err.message }));

  return true;
}

/**
 * Resolve a CAT (wdl_c_*) — sets req.community, req.tokenScopes; req.user is null.
 * Returns true if resolved, false if token not found / revoked / expired.
 */
async function resolveCAT(req, rawToken) {
  const hash = crypto.createHash('sha256').update(rawToken).digest('hex');
  const result = await query(
    `SELECT * FROM community_access_tokens
     WHERE token_hash = $1
       AND is_revoked = FALSE
       AND (expires_at IS NULL OR expires_at > NOW())`,
    [hash]
  );
  if (result.rows.length === 0) return false;

  const row = result.rows[0];
  req.user = null;
  req.community = { id: row.community_id };
  req.tokenScopes = row.scopes || [];
  req.tokenType = 'cat';

  query('UPDATE community_access_tokens SET last_used_at = NOW() WHERE token_hash = $1', [hash])
    .catch(err => logger.warn('Failed to update CAT last_used_at', { error: err.message }));

  return true;
}

/**
 * Verify JWT token and attach user to request
 */
async function verifyToken(req) {
  const token = extractToken(req);
  if (!token) return null;

  try {
    const decoded = jwt.verify(token, config.jwt.secret);

    // Check if session is still active
    const result = await query(
      'SELECT * FROM hub_sessions WHERE session_token = $1 AND is_active = true AND expires_at > NOW()',
      [token]
    );

    if (result.rows.length === 0) {
      return null;
    }

    return {
      id: decoded.userId,
      userId: decoded.userId, // For backwards compatibility
      platform: decoded.platform,
      platformUserId: decoded.platformUserId,
      username: decoded.username,
      email: decoded.email,
      avatarUrl: decoded.avatarUrl,
      isSuperAdmin: decoded.isSuperAdmin,
      isAnalyticsConsumer: decoded.isAnalyticsConsumer || false,
      roles: decoded.roles || [],
      communityRoles: decoded.communityRoles || {},
    };
  } catch (err) {
    logger.debug('Token verification failed', { error: err.message });
    return null;
  }
}

/**
 * Resolve tenant context from route params or community lookup.
 * Sets req.tenant if a tenant is found. Safe to use on global routes (no-op).
 */
export async function resolveTenant(req, res, next) {
  try {
    // Try tenantSlug from route params
    const tenantSlug = req.params.tenantSlug;
    if (tenantSlug) {
      const result = await query(
        'SELECT id, slug, display_name, is_global, is_active FROM tenants WHERE slug = $1',
        [tenantSlug]
      );
      if (!result.rows.length) return next(errors.notFound('Tenant not found'));
      const t = result.rows[0];
      if (!t.is_active) return next(errors.forbidden('Tenant is inactive'));
      req.tenant = { id: t.id, slug: t.slug, displayName: t.display_name, isGlobal: t.is_global };
      return next();
    }

    // Try from communityId
    const communityId = parseInt(req.params.communityId || req.params.id, 10);
    if (communityId && !isNaN(communityId)) {
      const result = await query(
        `SELECT t.id, t.slug, t.display_name, t.is_global, t.is_active
         FROM tenants t JOIN communities c ON c.tenant_id = t.id
         WHERE c.id = $1`,
        [communityId]
      );
      if (result.rows.length) {
        const t = result.rows[0];
        if (!t.is_active) return next(errors.forbidden('Tenant is inactive'));
        req.tenant = { id: t.id, slug: t.slug, displayName: t.display_name, isGlobal: t.is_global };
      }
    }

    // Default: no tenant context (global routes)
    next();
  } catch (err) {
    next(err);
  }
}

/**
 * Optional authentication - sets req.user if valid token present
 */
export async function optionalAuth(req, res, next) {
  req.user = await verifyToken(req);
  next();
}

/**
 * Required authentication - rejects if no valid token.
 * Also resolves tenant admin status when req.tenant is present.
 */
export async function requireAuth(req, res, next) {
  req.user = await verifyToken(req);

  if (!req.user) {
    logger.authz('Access denied - no valid token', { path: req.path });
    return next(errors.unauthorized('Authentication required'));
  }

  // Resolve tenant admin role if tenant context is available
  if (req.user && req.tenant) {
    const taResult = await query(
      'SELECT role FROM tenant_admins WHERE tenant_id = $1 AND user_id = $2',
      [req.tenant.id, req.user.id]
    );
    if (taResult.rows.length > 0) {
      req.isTenantAdmin = true;
      req.tenantAdminRole = taResult.rows[0].role;
    }
  }

  next();
}

/**
 * Require super admin (isSuperAdmin flag on user)
 */
export function requireSuperAdmin(req, res, next) {
  if (!req.user?.isSuperAdmin) {
    logger.authz('Access denied - not super admin', { userId: req.user?.id, path: req.path });
    return next(errors.forbidden('Super admin access required'));
  }
  next();
}

/**
 * Require analytics consumer role OR super admin.
 * GDPR-safe: analytics consumers see aggregates only (hub enforces this at route level).
 */
export function requireAnalyticsConsumer(req, res, next) {
  if (!req.user) return next(errors.unauthorized('Authentication required'));
  if (req.user.isSuperAdmin || req.user.isAnalyticsConsumer) return next();
  return next(errors.forbidden('Analytics consumer access required'));
}

/**
 * Require platform admin role
 */
export function requirePlatformAdmin(req, res, next) {
  if (!req.user?.roles?.includes('platform-admin')) {
    logger.authz('Access denied - not platform admin', {
      userId: req.user?.id,
      path: req.path,
    });
    return next(errors.forbidden('Platform admin access required'));
  }
  next();
}

/**
 * Require community membership.
 * Loads role, priority, and scope claims; sets req.communityRole, req.communityScopes,
 * req.communityRolePriority. Super admins and tenant admins bypass the DB check.
 */
export async function requireMember(req, res, next) {
  const communityId = parseInt(req.params.id || req.params.communityId, 10);
  if (isNaN(communityId)) return next(errors.badRequest('Invalid community ID'));

  // Super admins and tenant admins bypass
  if (req.user?.isSuperAdmin || req.isTenantAdmin) {
    req.communityRole = req.user?.isSuperAdmin ? 'super-admin' : 'tenant-admin';
    req.communityScopes = null; // null = all scopes (bypass)
    req.communityRolePriority = 999;
    return next();
  }

  // Platform admins bypass
  if (req.user?.roles?.includes('platform-admin')) {
    req.communityRole = 'platform-admin';
    req.communityScopes = null;
    req.communityRolePriority = 999;
    return next();
  }

  try {
    const result = await query(
      `SELECT cm.role, cm.community_role_id, cr.name as role_name, cr.priority,
              cr.base_claims, cm.claims_cache
       FROM community_members cm
       LEFT JOIN community_roles cr ON cr.id = cm.community_role_id
       WHERE cm.community_id = $1 AND cm.user_id = $2 AND cm.is_active = true`,
      [communityId, req.user.id]
    );

    if (!result.rows.length) {
      logger.authz('Access denied - not a member', { userId: req.user.id, communityId });
      return next(errors.forbidden('Community membership required'));
    }

    const row = result.rows[0];
    req.communityRole = row.role_name || row.role;
    req.communityRolePriority = row.priority || 0;

    // Use claims_cache if available, otherwise parse base_claims
    if (row.claims_cache) {
      req.communityScopes = Array.isArray(row.claims_cache)
        ? row.claims_cache
        : (row.claims_cache.scopes || []);
    } else if (row.base_claims) {
      const claims = typeof row.base_claims === 'string'
        ? JSON.parse(row.base_claims)
        : row.base_claims;
      req.communityScopes = claims.scopes || [];
    } else {
      req.communityScopes = [];
    }

    next();
  } catch (err) {
    next(err);
  }
}

/**
 * Require community admin access.
 * Uses scope-based authorization: checks for community:manage_members or
 * community:manage_channels scopes rather than hardcoded role names.
 * Super admins, tenant admins, and platform admins bypass the check.
 */
export async function requireCommunityAdmin(req, res, next) {
  const communityId = parseInt(req.params.communityId, 10);
  if (isNaN(communityId)) return next(errors.badRequest('Invalid community ID'));

  // Super admins bypass
  if (req.user?.isSuperAdmin) {
    req.communityRole = 'super-admin';
    return next();
  }

  // Tenant admins bypass
  if (req.isTenantAdmin) {
    req.communityRole = 'tenant-admin';
    return next();
  }

  // Platform admins bypass
  if (req.user?.roles?.includes('platform-admin')) {
    req.communityRole = 'platform-admin';
    return next();
  }

  try {
    const result = await query(
      `SELECT cm.role, cr.name as role_name, cr.priority, cr.base_claims
       FROM community_members cm
       LEFT JOIN community_roles cr ON cr.id = cm.community_role_id
       WHERE cm.community_id = $1 AND cm.user_id = $2 AND cm.is_active = true`,
      [communityId, req.user.id]
    );

    if (!result.rows.length) {
      logger.authz('Access denied - not a member', { userId: req.user.id, communityId });
      return next(errors.forbidden('Community admin access required'));
    }

    const row = result.rows[0];
    const claims = typeof row.base_claims === 'string'
      ? JSON.parse(row.base_claims || '{}')
      : (row.base_claims || {});
    const scopes = claims.scopes || [];

    // Check for admin-level scope
    if (!scopes.includes('community:manage_members') && !scopes.includes('community:manage_channels')) {
      logger.authz('Access denied - insufficient scope', {
        userId: req.user.id,
        communityId,
        role: row.role_name,
      });
      return next(errors.forbidden('Community admin access required'));
    }

    req.communityRole = row.role_name || row.role;
    req.communityScopes = scopes;
    req.communityRolePriority = row.priority || 0;
    next();
  } catch (err) {
    next(err);
  }
}

/**
 * Require a specific scope on the resolved community role.
 * Returns a middleware function (factory pattern).
 * Super admins, tenant admins, and routes with null communityScopes (platform-admin bypass) pass through.
 */
export function requireScope(scope) {
  return (req, res, next) => {
    // Bypass for superadmins and tenant admins
    if (req.user?.isSuperAdmin || req.isTenantAdmin) return next();
    // null communityScopes means bypass (platform admin, etc.)
    if (req.communityScopes === null) return next();
    if (req.communityScopes?.includes(scope)) return next();
    logger.authz('Access denied - missing scope', { userId: req.user?.id, scope, path: req.path });
    return res.status(403).json({ error: `Missing scope: ${scope}` });
  };
}

/**
 * Require tenant admin role (or super admin).
 * Must be used after resolveTenant and requireAuth.
 */
export function requireTenantAdmin(req, res, next) {
  if (req.user?.isSuperAdmin || req.isTenantAdmin) return next();
  logger.authz('Access denied - not tenant admin', { userId: req.user?.id, path: req.path });
  return next(errors.forbidden('Tenant admin access required'));
}

/**
 * Require channel creation permission based on community config policy.
 * Reads communities.config.channel_creation_policy and checks user scopes.
 * Must be used after requireAuth. Sets req.communityRole, req.communityScopes,
 * req.communityRolePriority on success.
 */
export async function requireChannelCreation(req, res, next) {
  const communityId = parseInt(req.params.id || req.params.communityId, 10);
  if (isNaN(communityId)) return next(errors.badRequest('Invalid community ID'));

  // Super admins, tenant admins, platform admins bypass
  if (req.user?.isSuperAdmin || req.isTenantAdmin) {
    req.communityRole = req.user?.isSuperAdmin ? 'super-admin' : 'tenant-admin';
    req.communityScopes = null;
    req.communityRolePriority = 999;
    return next();
  }
  if (req.user?.roles?.includes('platform-admin')) {
    req.communityRole = 'platform-admin';
    req.communityScopes = null;
    req.communityRolePriority = 999;
    return next();
  }

  try {
    const result = await query(
      `SELECT c.config,
              cm.role, cm.community_role_id, cr.name AS role_name,
              cr.priority, cr.base_claims, cm.claims_cache
       FROM communities c
       LEFT JOIN community_members cm ON cm.community_id = c.id
         AND cm.user_id = $2 AND cm.is_active = true
       LEFT JOIN community_roles cr ON cr.id = cm.community_role_id
       WHERE c.id = $1`,
      [communityId, req.user.id]
    );

    if (!result.rows.length) return next(errors.notFound('Community not found'));

    const row = result.rows[0];
    if (!row.role && !row.community_role_id) {
      return next(errors.forbidden('Community membership required'));
    }

    // Resolve scopes
    let scopes;
    if (row.claims_cache) {
      scopes = Array.isArray(row.claims_cache)
        ? row.claims_cache
        : (row.claims_cache.scopes || []);
    } else if (row.base_claims) {
      const claims = typeof row.base_claims === 'string'
        ? JSON.parse(row.base_claims) : row.base_claims;
      scopes = claims.scopes || [];
    } else {
      scopes = [];
    }

    req.communityRole = row.role_name || row.role;
    req.communityScopes = scopes;
    req.communityRolePriority = row.priority || 0;

    const policy = (row.config || {}).channel_creation_policy || 'admin_only';

    if (policy === 'all_members') {
      return next();
    }

    if (policy === 'communicator') {
      if (scopes.includes('channels:create') || scopes.includes('community:manage_channels')) {
        return next();
      }
      logger.authz('Channel creation denied - missing channels:create scope', {
        userId: req.user.id, communityId, role: row.role_name, policy,
      });
      return next(errors.forbidden('Channel creation requires Communicator role or higher'));
    }

    // admin_only (default)
    if (scopes.includes('community:manage_channels') || scopes.includes('community:manage_members')) {
      return next();
    }
    logger.authz('Channel creation denied - admin only policy', {
      userId: req.user.id, communityId, role: row.role_name, policy,
    });
    return next(errors.forbidden('Only admins can create channels'));
  } catch (err) {
    next(err);
  }
}

/**
 * Require service API key for internal service-to-service calls
 */
export function requireServiceAuth(req, res, next) {
  const apiKey = req.headers['x-api-key'] || req.headers['x-service-key'];

  if (!apiKey) {
    logger.authz('Access denied - no service API key', { path: req.path });
    return next(errors.unauthorized('Service API key required'));
  }

  if (apiKey !== config.serviceApiKey) {
    logger.authz('Access denied - invalid service API key', { path: req.path });
    return next(errors.unauthorized('Invalid service API key'));
  }

  // Mark request as coming from internal service
  req.isServiceRequest = true;
  next();
}

export default {
  resolveTenant,
  optionalAuth,
  requireAuth,
  requireSuperAdmin,
  requireAnalyticsConsumer,
  requirePlatformAdmin,
  requireMember,
  requireCommunityAdmin,
  requireChannelCreation,
  requireScope,
  requireTenantAdmin,
  requireServiceAuth,
};
