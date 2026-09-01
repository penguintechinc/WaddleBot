import { query } from '../config/database.js';
import { logger } from '../utils/logger.js';

export const ALL_TENANT_SCOPES = [
  // Community scopes
  'community:read',
  'community:write',
  'community:delete',
  'community:manage_members',
  'community:manage_roles',
  'community:manage_settings',
  'community:manage_integrations',
  'community:view_analytics',
  'community:manage_modules',
  'community:manage_forms',
  'community:manage_announcements',
  'community:manage_shoutouts',
  'community:manage_reputation',
  'community:manage_inventory',
  'community:manage_tokens',
  'community:manage_calendar',
  'community:manage_join_requests',
  'community:manage_support',
  'community:manage_commands',
  'community:manage_clips',
  'community:manage_lfg',
  'community:manage_servers',
  'community:view_members',
  // Channel scopes
  'channels:read',
  'channels:write',
  'channels:delete',
  'channels:manage',
  'channels:send_messages',
  'channels:delete_messages',
  'channels:pin_messages',
  'channels:manage_permissions',
  'channels:start_call',
  'channels:join_call',
  'channels:end_call',
  'channels:screenshare',
  'channels:override_screenshare',
  'channels:mute_members',
  'channels:deafen_members',
  'channels:kick_members',
  'channels:move_members',
  // Resource scopes
  'resources:upload',
  'resources:delete',
  'resources:manage',
  'members:read',
  'members:write',
  'members:ban',
  'members:kick',
  'members:timeout',
  'members:manage_roles',
  'roles:read',
  'roles:write',
  'roles:delete',
  'audit:read',
  'webhooks:read',
  'webhooks:write',
  'webhooks:delete',
  'integrations:read',
  'integrations:write',
  'bots:read',
  'bots:write',
  'bots:delete',
];

export const SYSTEM_ROLE_SCOPES = {
  owner: [...ALL_TENANT_SCOPES],
  admin: [
    'community:read',
    'community:write',
    'community:manage_members',
    'community:manage_roles',
    'community:manage_settings',
    'community:manage_integrations',
    'community:view_analytics',
    'community:manage_modules',
    'community:manage_forms',
    'community:manage_announcements',
    'community:manage_shoutouts',
    'community:manage_reputation',
    'community:manage_inventory',
    'community:manage_tokens',
    'community:manage_calendar',
    'community:manage_join_requests',
    'community:manage_support',
    'community:manage_commands',
    'community:manage_clips',
    'community:manage_lfg',
    'community:manage_servers',
    'community:view_members',
    'channels:read',
    'channels:write',
    'channels:delete',
    'channels:manage',
    'channels:send_messages',
    'channels:delete_messages',
    'channels:pin_messages',
    'channels:manage_permissions',
    'channels:start_call',
    'channels:join_call',
    'channels:end_call',
    'channels:screenshare',
    'channels:override_screenshare',
    'channels:mute_members',
    'channels:deafen_members',
    'channels:kick_members',
    'channels:move_members',
    'resources:upload',
    'resources:delete',
    'resources:manage',
    'members:read',
    'members:write',
    'members:ban',
    'members:kick',
    'members:timeout',
    'members:manage_roles',
    'roles:read',
    'roles:write',
    'audit:read',
    'webhooks:read',
    'webhooks:write',
    'integrations:read',
    'integrations:write',
    'bots:read',
    'bots:write',
  ],
  moderator: [
    'community:read',
    'community:view_members',
    'channels:read',
    'channels:send_messages',
    'channels:delete_messages',
    'channels:pin_messages',
    'channels:start_call',
    'channels:join_call',
    'channels:screenshare',
    'channels:mute_members',
    'channels:deafen_members',
    'channels:kick_members',
    'channels:move_members',
    'resources:upload',
    'members:read',
    'members:kick',
    'members:timeout',
    'roles:read',
    'audit:read',
  ],
  member: [
    'community:read',
    'community:view_members',
    'channels:read',
    'channels:send_messages',
    'channels:join_call',
    'channels:screenshare',
    'resources:upload',
    'members:read',
    'roles:read',
  ],
  guest: [
    'community:read',
    'channels:read',
    'channels:send_messages',
    'members:read',
  ],
};

/**
 * Resolve scopes for a user in a community, optionally for a specific channel.
 *
 * @param {number} userId
 * @param {number} communityId
 * @param {number|null} [channelId]
 * @param {boolean} [isTemporary]
 * @returns {Promise<{
 *   tenantId: number,
 *   communityId: number,
 *   channelId: number|null,
 *   role: string,
 *   rolePriority: number,
 *   scopes: string[],
 *   isTenantAdmin: boolean,
 * }>}
 */
export async function resolveScopes(userId, communityId, channelId = null, isTemporary = false) {
  // Step 1: Check tenant_admins
  const tenantAdminResult = await query(
    `SELECT ta.role as tenant_role
     FROM tenant_admins ta
     JOIN communities c ON c.tenant_id = ta.tenant_id
     WHERE ta.user_id = $1 AND c.id = $2`,
    [userId, communityId]
  );

  if (tenantAdminResult.rows.length > 0) {
    // Fetch tenantId for the return object
    const tenantRow = await query(
      `SELECT tenant_id FROM communities WHERE id = $1`,
      [communityId]
    );
    const tenantId = tenantRow.rows[0]?.tenant_id ?? null;

    logger.debug({ userId, communityId, role: tenantAdminResult.rows[0].tenant_role }, 'Resolved tenant admin scopes');

    return {
      tenantId,
      communityId,
      channelId: channelId ?? null,
      role: tenantAdminResult.rows[0].tenant_role,
      rolePriority: 0,
      scopes: [...ALL_TENANT_SCOPES],
      isTenantAdmin: true,
    };
  }

  // Step 2: Load community role and claims
  const memberResult = await query(
    `SELECT cr.name as role_name, cr.priority, cr.base_claims,
            cm.claims_cache, c.tenant_id, cr.id as role_id
     FROM community_members cm
     JOIN community_roles cr ON cr.id = cm.community_role_id
     JOIN communities c ON c.id = cm.community_id
     WHERE cm.user_id = $1 AND cm.community_id = $2 AND cm.is_active = true`,
    [userId, communityId]
  );

  if (memberResult.rows.length === 0) {
    logger.warn({ userId, communityId }, 'No active community membership found during scope resolution');
    return {
      tenantId: null,
      communityId,
      channelId: channelId ?? null,
      role: 'none',
      rolePriority: 9999,
      scopes: [],
      isTenantAdmin: false,
    };
  }

  const member = memberResult.rows[0];
  const tenantId = member.tenant_id;
  const roleName = member.role_name;
  const rolePriority = member.priority;
  const roleId = member.role_id;

  let baseScopes;

  // Step 4: Use claims_cache if channelId is NOT provided and cache is populated
  if (!channelId && member.claims_cache !== null) {
    try {
      baseScopes = Array.isArray(member.claims_cache)
        ? member.claims_cache
        : JSON.parse(member.claims_cache);
      logger.debug({ userId, communityId }, 'Using claims_cache for scope resolution');
    } catch (err) {
      logger.warn({ userId, communityId, err }, 'Failed to parse claims_cache, falling back to base_claims');
      baseScopes = parseBaseClaims(member.base_claims);
    }
  } else {
    baseScopes = parseBaseClaims(member.base_claims);
  }

  // Step 3: Apply channel overrides if channelId provided
  if (channelId) {
    const scopeType = isTemporary ? 'temporary' : 'permanent';

    const overrideResult = await query(
      `SELECT grant_scopes, deny_scopes
       FROM hub_channel_permission_overrides
       WHERE hub_channel_id = $1 AND community_role_id = $2
         AND (scope = 'both' OR scope = $3)`,
      [channelId, roleId, scopeType]
    );

    if (overrideResult.rows.length > 0) {
      const grantSet = new Set(baseScopes);

      for (const row of overrideResult.rows) {
        const grantScopes = parseBaseClaims(row.grant_scopes);
        const denyScopes = parseBaseClaims(row.deny_scopes);

        for (const s of grantScopes) {
          grantSet.add(s);
        }
        for (const s of denyScopes) {
          grantSet.delete(s);
        }
      }

      baseScopes = Array.from(grantSet);
      logger.debug({ userId, communityId, channelId, overrideCount: overrideResult.rows.length }, 'Applied channel permission overrides');
    }
  }

  return {
    tenantId,
    communityId,
    channelId: channelId ?? null,
    role: roleName,
    rolePriority: rolePriority,
    scopes: baseScopes,
    isTenantAdmin: false,
  };
}

/**
 * Parse base_claims from DB — handles array or JSON string.
 * @param {string[]|string|null} claims
 * @returns {string[]}
 */
function parseBaseClaims(claims) {
  if (!claims) return [];
  if (Array.isArray(claims)) return claims;
  try {
    const parsed = JSON.parse(claims);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/**
 * Determine if a user can override another user's screenshare.
 *
 * @param {number} requesterPriority - Lower number = higher authority
 * @param {number} sharerPriority
 * @param {string[]} requesterScopes
 * @returns {boolean}
 */
export function canOverrideScreenshare(requesterPriority, sharerPriority, requesterScopes) {
  return (
    Array.isArray(requesterScopes) &&
    requesterScopes.includes('channels:override_screenshare') &&
    requesterPriority > sharerPriority
  );
}

/**
 * Invalidate the claims_cache for community members.
 * If roleId is provided, only invalidates members with that role.
 *
 * @param {number} communityId
 * @param {number|null} [roleId]
 * @returns {Promise<number>} Number of rows updated
 */
export async function invalidateClaimsCache(communityId, roleId = null) {
  let result;

  if (roleId != null) {
    result = await query(
      `UPDATE community_members
       SET claims_cache = NULL
       WHERE community_id = $1 AND community_role_id = $2`,
      [communityId, roleId]
    );
  } else {
    result = await query(
      `UPDATE community_members
       SET claims_cache = NULL
       WHERE community_id = $1`,
      [communityId]
    );
  }

  const rowCount = result.rowCount ?? 0;
  logger.debug({ communityId, roleId, rowCount }, 'Invalidated claims_cache');
  return rowCount;
}

/**
 * Check if a resolved scope set contains a specific scope.
 *
 * @param {string[]} resolvedScopes
 * @param {string} scope
 * @returns {boolean}
 */
export function hasScope(resolvedScopes, scope) {
  return Array.isArray(resolvedScopes) && resolvedScopes.includes(scope);
}
