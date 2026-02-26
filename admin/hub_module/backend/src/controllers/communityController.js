/**
 * Community Controller - Authenticated member features
 */
import { query, transaction } from '../config/database.js';
import { errors } from '../middleware/errorHandler.js';
import { logger } from '../utils/logger.js';
import { formatReputation, clampReputation } from '../utils/reputation.js';
import {
  verifyPlatformAdmin,
  isUserCommunityAdmin,
} from '../services/platformPermissionService.js';

const VALID_COMMUNITY_TYPES = ['shared_interest_group', 'gaming', 'creator', 'corporate', 'other'];

/**
 * Get user's communities
 */
export async function getMyCommunities(req, res, next) {
  try {
    const result = await query(
      `SELECT c.id, c.name, c.display_name, c.description, c.config,
              c.platform, c.member_count, cm.role, cm.joined_at
       FROM community_members cm
       JOIN communities c ON c.id = cm.community_id
       WHERE cm.user_id = $1 AND cm.is_active = true AND c.is_active = true
       ORDER BY cm.joined_at DESC`,
      [req.user.id]
    );

    const communities = result.rows.map(row => ({
      id: row.id,
      name: row.name,
      displayName: row.display_name || row.name,
      description: row.description,
      logoUrl: row.config?.logo_url || null,
      platform: row.platform,
      memberCount: row.member_count || 0,
      role: row.role,
      joinedAt: row.joined_at?.toISOString(),
    }));

    res.json({ success: true, communities });
  } catch (err) {
    next(err);
  }
}

/**
 * Get community dashboard data
 */
export async function getCommunityDashboard(req, res, next) {
  try {
    const communityId = parseInt(req.params.id, 10);

    if (isNaN(communityId)) {
      return next(errors.badRequest('Invalid community ID'));
    }

    // Get community details
    const communityResult = await query(
      `SELECT id, name, display_name, description, config,
              platform, member_count, created_at
       FROM communities
       WHERE id = $1 AND is_active = true`,
      [communityId]
    );

    if (communityResult.rows.length === 0) {
      return next(errors.notFound('Community not found'));
    }

    const community = communityResult.rows[0];

    // Get user's membership
    const memberResult = await query(
      `SELECT role, reputation, joined_at
       FROM community_members
       WHERE community_id = $1 AND user_id = $2 AND is_active = true`,
      [communityId, req.user.id]
    );

    if (memberResult.rows.length === 0) {
      return next(errors.forbidden('Not a member of this community'));
    }

    const membership = memberResult.rows[0];

    // Get live streams from linked servers if any
    let liveStreams = [];
    try {
      const streamsResult = await query(
        `SELECT co.entity_id, co.channel_id, co.viewer_count, co.stream_title, co.game_name
         FROM coordination co
         JOIN community_servers cs ON cs.platform = co.platform AND cs.platform_server_id = co.server_id
         WHERE cs.community_id = $1 AND cs.status = 'approved' AND co.is_live = true
         ORDER BY co.viewer_count DESC
         LIMIT 5`,
        [communityId]
      );
      liveStreams = streamsResult.rows.map(row => ({
        entityId: row.entity_id,
        channelName: row.channel_id,
        viewerCount: row.viewer_count || 0,
        title: row.stream_title || '',
        game: row.game_name || '',
      }));
    } catch {
      // coordination table might not have all columns yet
    }

    // Get recent chat messages as activity
    let recentActivity = [];
    try {
      const activityResult = await query(
        `SELECT id, sender_username, message_content, created_at
         FROM hub_chat_messages
         WHERE community_id = $1
         ORDER BY created_at DESC
         LIMIT 10`,
        [communityId]
      );
      recentActivity = activityResult.rows.map(row => ({
        id: row.id,
        type: 'chat',
        description: `${row.sender_username}: ${row.message_content?.substring(0, 100)}`,
        createdAt: row.created_at?.toISOString(),
      }));
    } catch {
      // hub_chat_messages might be empty
    }

    res.json({
      success: true,
      community: {
        id: community.id,
        name: community.name,
        displayName: community.display_name || community.name,
        description: community.description,
        logoUrl: community.config?.logo_url || null,
        bannerUrl: community.config?.banner_url || null,
        platform: community.platform,
        memberCount: community.member_count || 0,
        createdAt: community.created_at?.toISOString(),
      },
      membership: {
        role: membership.role,
        reputation: formatReputation(membership.reputation),
        joinedAt: membership.joined_at?.toISOString(),
      },
      recentActivity,
      liveStreams,
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get community leaderboard
 */
export async function getLeaderboard(req, res, next) {
  try {
    const communityId = parseInt(req.params.id, 10);
    const limit = Math.min(50, Math.max(1, parseInt(req.query.limit || '20', 10)));

    if (isNaN(communityId)) {
      return next(errors.badRequest('Invalid community ID'));
    }

    const result = await query(
      `SELECT cm.user_id, u.username, u.avatar_url, cm.reputation, cm.role
       FROM community_members cm
       LEFT JOIN hub_users u ON u.id = cm.user_id
       WHERE cm.community_id = $1 AND cm.is_active = true
       ORDER BY cm.reputation DESC
       LIMIT $2`,
      [communityId, limit]
    );

    const leaderboard = result.rows.map((row, index) => ({
      rank: index + 1,
      userId: row.user_id,
      username: row.username,
      avatarUrl: row.avatar_url,
      reputation: formatReputation(row.reputation),
      role: row.role,
    }));

    res.json({ success: true, leaderboard });
  } catch (err) {
    next(err);
  }
}

/**
 * Get community members (for member browsing)
 * Allows community members to view other members
 */
export async function getCommunityMembers(req, res, next) {
  try {
    const communityId = parseInt(req.params.id, 10);
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(50, Math.max(1, parseInt(req.query.limit || '25', 10)));
    const offset = (page - 1) * limit;
    const search = req.query.search?.trim();
    const roleFilter = req.query.role;

    if (isNaN(communityId)) {
      return next(errors.badRequest('Invalid community ID'));
    }

    // Build query with optional filters
    let whereClause = 'WHERE cm.community_id = $1 AND cm.is_active = true';
    const params = [communityId];
    let paramIndex = 2;

    if (search) {
      whereClause += ` AND u.username ILIKE $${paramIndex}`;
      params.push(`%${search}%`);
      paramIndex++;
    }

    if (roleFilter) {
      // Support multiple roles separated by comma
      const roles = roleFilter.split(',').map(r => r.trim()).filter(Boolean);
      if (roles.length > 0) {
        whereClause += ` AND cm.role = ANY($${paramIndex}::text[])`;
        params.push(roles);
        paramIndex++;
      }
    }

    // Count total
    const countResult = await query(
      `SELECT COUNT(*) as count
       FROM community_members cm
       LEFT JOIN hub_users u ON u.id = cm.user_id
       ${whereClause}`,
      params
    );
    const total = parseInt(countResult.rows[0]?.count || 0, 10);

    // Get paginated members
    // Sort by role hierarchy (owner > admin > mod > vip > member), then by join date
    const result = await query(
      `SELECT cm.user_id, u.username, u.avatar_url, cm.role, cm.joined_at
       FROM community_members cm
       LEFT JOIN hub_users u ON u.id = cm.user_id
       ${whereClause}
       ORDER BY
         CASE cm.role
           WHEN 'community-owner' THEN 1
           WHEN 'community-admin' THEN 2
           WHEN 'moderator' THEN 3
           WHEN 'vip' THEN 4
           ELSE 5
         END,
         cm.joined_at ASC
       LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`,
      [...params, limit, offset]
    );

    const members = result.rows.map(row => ({
      userId: row.user_id,
      username: row.username,
      avatarUrl: row.avatar_url,
      role: row.role,
      joinedAt: row.joined_at?.toISOString(),
    }));

    res.json({
      success: true,
      members,
      pagination: {
        page,
        limit,
        total,
        pages: Math.ceil(total / limit),
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get community activity feed
 */
export async function getActivityFeed(req, res, next) {
  try {
    const communityId = parseInt(req.params.id, 10);
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(50, Math.max(1, parseInt(req.query.limit || '20', 10)));
    const offset = (page - 1) * limit;

    if (isNaN(communityId)) {
      return next(errors.badRequest('Invalid community ID'));
    }

    const countResult = await query(
      'SELECT COUNT(*) as count FROM community_activity WHERE community_id = $1',
      [communityId]
    );
    const total = parseInt(countResult.rows[0]?.count || 0, 10);

    const result = await query(
      `SELECT id, activity_type, user_id, user_name, description, metadata, created_at
       FROM community_activity
       WHERE community_id = $1
       ORDER BY created_at DESC
       LIMIT $2 OFFSET $3`,
      [communityId, limit, offset]
    );

    const activities = result.rows.map(row => ({
      id: row.id,
      type: row.activity_type,
      userId: row.user_id,
      userName: row.user_name,
      description: row.description,
      metadata: row.metadata,
      createdAt: row.created_at?.toISOString(),
    }));

    res.json({
      success: true,
      activities,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get community events
 */
export async function getEvents(req, res, next) {
  try {
    const communityId = parseInt(req.params.id, 10);
    const status = req.query.status || 'approved';
    const upcoming = req.query.upcoming !== 'false';

    if (isNaN(communityId)) {
      return next(errors.badRequest('Invalid community ID'));
    }

    let whereClause = 'WHERE community_id = $1 AND status = $2';
    const params = [communityId, status];

    if (upcoming) {
      whereClause += ' AND event_date >= NOW()';
    }

    const result = await query(
      `SELECT id, title, description, event_date, end_date, location,
              max_attendees, created_by, created_by_name, status
       FROM events
       ${whereClause}
       ORDER BY event_date ASC
       LIMIT 50`,
      params
    );

    const events = result.rows.map(row => ({
      id: row.id,
      title: row.title,
      description: row.description,
      eventDate: row.event_date?.toISOString(),
      endDate: row.end_date?.toISOString(),
      location: row.location,
      maxAttendees: row.max_attendees,
      createdBy: row.created_by_name,
      status: row.status,
    }));

    res.json({ success: true, events });
  } catch (err) {
    next(err);
  }
}

/**
 * Get community memories (quotes, URLs)
 */
export async function getMemories(req, res, next) {
  try {
    const communityId = parseInt(req.params.id, 10);
    const type = req.query.type; // quote, url, note
    const limit = Math.min(50, Math.max(1, parseInt(req.query.limit || '20', 10)));

    if (isNaN(communityId)) {
      return next(errors.badRequest('Invalid community ID'));
    }

    let whereClause = 'WHERE community_id = $1 AND is_active = true';
    const params = [communityId];

    if (type) {
      whereClause += ' AND memory_type = $2';
      params.push(type);
    }

    const result = await query(
      `SELECT id, memory_type, title, content, url, author, tags, usage_count, created_at
       FROM memories
       ${whereClause}
       ORDER BY usage_count DESC, created_at DESC
       LIMIT $${params.length + 1}`,
      [...params, limit]
    );

    const memories = result.rows.map(row => ({
      id: row.id,
      type: row.memory_type,
      title: row.title,
      content: row.content,
      url: row.url,
      author: row.author,
      tags: row.tags,
      usageCount: row.usage_count || 0,
      createdAt: row.created_at?.toISOString(),
    }));

    res.json({ success: true, memories });
  } catch (err) {
    next(err);
  }
}

/**
 * Get installed modules for community
 */
export async function getInstalledModules(req, res, next) {
  try {
    const communityId = parseInt(req.params.id, 10);

    if (isNaN(communityId)) {
      return next(errors.badRequest('Invalid community ID'));
    }

    const result = await query(
      `SELECT mi.id, mi.module_id, m.name, m.display_name, m.description,
              m.category, m.icon_url, mi.is_enabled, mi.config, mi.installed_at
       FROM module_installations mi
       JOIN modules m ON m.id = mi.module_id
       WHERE mi.community_id = $1
       ORDER BY mi.installed_at DESC`,
      [communityId]
    );

    const modules = result.rows.map(row => ({
      installationId: row.id,
      moduleId: row.module_id,
      name: row.name,
      displayName: row.display_name || row.name,
      description: row.description,
      category: row.category,
      iconUrl: row.icon_url,
      isEnabled: row.is_enabled,
      config: row.config,
      installedAt: row.installed_at?.toISOString(),
    }));

    res.json({ success: true, modules });
  } catch (err) {
    next(err);
  }
}

/**
 * Update user profile in community
 */
export async function updateProfile(req, res, next) {
  try {
    const communityId = parseInt(req.params.id, 10);
    const { displayName, bio, socialLinks } = req.body;

    if (isNaN(communityId)) {
      return next(errors.badRequest('Invalid community ID'));
    }

    // Update community member profile
    await query(
      `UPDATE community_members
       SET display_name = COALESCE($1, display_name),
           bio = COALESCE($2, bio),
           social_links = COALESCE($3, social_links),
           updated_at = NOW()
       WHERE community_id = $4 AND user_id = $5`,
      [displayName, bio, socialLinks ? JSON.stringify(socialLinks) : null, communityId, req.user.id]
    );

    logger.audit('Profile updated', {
      userId: req.user.id,
      communityId,
      fields: Object.keys(req.body),
    });

    res.json({ success: true, message: 'Profile updated' });
  } catch (err) {
    next(err);
  }
}

/**
 * Join community (or request to join)
 */
export async function joinCommunity(req, res, next) {
  try {
    const communityId = parseInt(req.params.id, 10);
    const { message } = req.body;

    if (isNaN(communityId)) {
      return next(errors.badRequest('Invalid community ID'));
    }

    // Get community details including join mode
    const communityResult = await query(
      `SELECT id, name, display_name, join_mode, is_active, is_public
       FROM communities WHERE id = $1`,
      [communityId]
    );

    if (communityResult.rows.length === 0) {
      return next(errors.notFound('Community not found'));
    }

    const community = communityResult.rows[0];

    if (!community.is_active) {
      return next(errors.badRequest('Community is not active'));
    }

    if (!community.is_public && community.join_mode === 'invite') {
      return next(errors.forbidden('This community is invite-only'));
    }

    // Check if already a member
    const memberCheck = await query(
      `SELECT id, is_active FROM community_members
       WHERE community_id = $1 AND user_id = $2`,
      [communityId, req.user.id]
    );

    if (memberCheck.rows.length > 0) {
      if (memberCheck.rows[0].is_active) {
        return next(errors.conflict('Already a member of this community'));
      }
      // Reactivate membership if previously left
      await query(
        `UPDATE community_members SET is_active = true, joined_at = NOW()
         WHERE community_id = $1 AND user_id = $2`,
        [communityId, req.user.id]
      );
      await query(
        `UPDATE communities SET member_count = member_count + 1 WHERE id = $1`,
        [communityId]
      );
      logger.audit('User rejoined community', { userId: req.user.id, communityId });
      return res.json({ success: true, joined: true, message: 'Rejoined community' });
    }

    // Check for pending request
    const requestCheck = await query(
      `SELECT id, status FROM join_requests
       WHERE community_id = $1 AND user_id = $2`,
      [communityId, req.user.id]
    );

    if (requestCheck.rows.length > 0) {
      const existingRequest = requestCheck.rows[0];
      if (existingRequest.status === 'pending') {
        return next(errors.conflict('You already have a pending join request'));
      }
      if (existingRequest.status === 'rejected') {
        return next(errors.forbidden('Your previous join request was rejected'));
      }
    }

    // Handle based on join mode
    if (community.join_mode === 'approval') {
      // Create join request
      await query(
        `INSERT INTO join_requests (community_id, user_id, message)
         VALUES ($1, $2, $3)
         ON CONFLICT (community_id, user_id)
         DO UPDATE SET status = 'pending', message = $3, created_at = NOW()`,
        [communityId, req.user.id, message || null]
      );

      logger.audit('Join request created', {
        userId: req.user.id,
        communityId,
        communityName: community.name,
      });

      return res.json({
        success: true,
        joined: false,
        pending: true,
        message: 'Join request submitted. Waiting for approval.',
      });
    }

    // Open join - add directly as member
    await query(
      `INSERT INTO community_members (community_id, user_id, role, is_active, joined_at)
       VALUES ($1, $2, 'member', true, NOW())`,
      [communityId, req.user.id]
    );

    await query(
      `UPDATE communities SET member_count = member_count + 1 WHERE id = $1`,
      [communityId]
    );

    logger.audit('User joined community', {
      userId: req.user.id,
      communityId,
      communityName: community.name,
    });

    res.json({ success: true, joined: true, message: 'Joined community successfully' });
  } catch (err) {
    next(err);
  }
}

/**
 * Get user's pending join requests
 */
export async function getMyJoinRequests(req, res, next) {
  try {
    const result = await query(
      `SELECT jr.id, jr.community_id, jr.message, jr.status, jr.created_at,
              c.name, c.display_name, c.platform
       FROM join_requests jr
       JOIN communities c ON c.id = jr.community_id
       WHERE jr.user_id = $1
       ORDER BY jr.created_at DESC`,
      [req.user.id]
    );

    const requests = result.rows.map(row => ({
      id: row.id,
      communityId: row.community_id,
      communityName: row.display_name || row.name,
      platform: row.platform,
      message: row.message,
      status: row.status,
      createdAt: row.created_at?.toISOString(),
    }));

    res.json({ success: true, requests });
  } catch (err) {
    next(err);
  }
}

/**
 * Cancel join request
 */
export async function cancelJoinRequest(req, res, next) {
  try {
    const requestId = parseInt(req.params.requestId, 10);

    if (isNaN(requestId)) {
      return next(errors.badRequest('Invalid request ID'));
    }

    const result = await query(
      `DELETE FROM join_requests
       WHERE id = $1 AND user_id = $2 AND status = 'pending'
       RETURNING community_id`,
      [requestId, req.user.id]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Join request not found or already processed'));
    }

    logger.audit('Join request cancelled', {
      userId: req.user.id,
      requestId,
      communityId: result.rows[0].community_id,
    });

    res.json({ success: true, message: 'Join request cancelled' });
  } catch (err) {
    next(err);
  }
}

/**
 * Leave community
 */
export async function leaveCommunity(req, res, next) {
  try {
    const communityId = parseInt(req.params.id, 10);

    if (isNaN(communityId)) {
      return next(errors.badRequest('Invalid community ID'));
    }

    // Check if user is owner
    const memberResult = await query(
      `SELECT role FROM community_members
       WHERE community_id = $1 AND user_id = $2 AND is_active = true`,
      [communityId, req.user.id]
    );

    if (memberResult.rows.length === 0) {
      return next(errors.badRequest('Not a member of this community'));
    }

    if (memberResult.rows[0].role === 'community-owner') {
      return next(errors.badRequest('Owners cannot leave. Transfer ownership first.'));
    }

    // Deactivate membership
    await query(
      `UPDATE community_members
       SET is_active = false, left_at = NOW()
       WHERE community_id = $1 AND user_id = $2`,
      [communityId, req.user.id]
    );

    // Update member count
    await query(
      `UPDATE communities
       SET member_count = member_count - 1
       WHERE id = $1`,
      [communityId]
    );

    logger.audit('User left community', {
      userId: req.user.id,
      communityId,
    });

    res.json({ success: true, message: 'Left community successfully' });
  } catch (err) {
    next(err);
  }
}

/**
 * Add a platform server to a community
 * User must be admin/owner of the platform server (verified via OAuth)
 */
export async function addServerToCommunity(req, res, next) {
  try {
    const communityId = parseInt(req.params.id, 10);
    const { platform, platformServerId, platformServerName, linkType } = req.body;

    if (isNaN(communityId)) {
      return next(errors.badRequest('Invalid community ID'));
    }

    // Validate platform
    const validPlatforms = ['discord', 'twitch', 'slack', 'youtube'];
    if (!validPlatforms.includes(platform)) {
      return next(errors.badRequest(`Invalid platform. Must be one of: ${validPlatforms.join(', ')}`));
    }

    if (!platformServerId) {
      return next(errors.badRequest('Platform server ID is required'));
    }

    // Check community exists
    const communityResult = await query(
      `SELECT id, name FROM communities WHERE id = $1 AND is_active = true`,
      [communityId]
    );

    if (communityResult.rows.length === 0) {
      return next(errors.notFound('Community not found'));
    }

    // Check if server is already linked
    const existingResult = await query(
      `SELECT id, status FROM community_servers
       WHERE community_id = $1 AND platform = $2 AND platform_server_id = $3`,
      [communityId, platform, platformServerId]
    );

    if (existingResult.rows.length > 0) {
      const existing = existingResult.rows[0];
      if (existing.status === 'approved') {
        return next(errors.conflict('This server is already linked to this community'));
      }
      if (existing.status === 'pending') {
        return next(errors.conflict('A link request for this server is already pending'));
      }
    }

    // Verify user is admin/owner on the platform
    const verifyResult = await verifyPlatformAdmin(req.user.id, platform, platformServerId);

    if (!verifyResult.verified) {
      return next(errors.forbidden(verifyResult.error || 'You must be an admin/owner of this server to link it'));
    }

    // Check if user is a community admin
    const isCommunityAdmin = await isUserCommunityAdmin(req.user.id, communityId);

    // Determine initial status
    const status = isCommunityAdmin ? 'approved' : 'pending';
    const serverName = platformServerName || verifyResult.serverName || platformServerId;

    if (status === 'approved') {
      // Direct add to community_servers
      await query(
        `INSERT INTO community_servers
         (community_id, platform, platform_server_id, platform_server_name, link_type, added_by, approved_by, status, verified_at)
         VALUES ($1, $2, $3, $4, $5, $6, $6, 'approved', NOW())
         ON CONFLICT (community_id, platform, platform_server_id)
         DO UPDATE SET status = 'approved', approved_by = $6, verified_at = NOW()`,
        [communityId, platform, platformServerId, serverName, linkType || 'server', req.user.id]
      );

      logger.audit('Server linked to community', {
        userId: req.user.id,
        communityId,
        platform,
        platformServerId,
        serverName,
      });

      return res.status(201).json({
        success: true,
        approved: true,
        message: 'Server linked successfully',
      });
    }

    // Create link request for community admin approval
    await query(
      `INSERT INTO server_link_requests
       (community_id, platform, platform_server_id, platform_server_name, requested_by)
       VALUES ($1, $2, $3, $4, $5)`,
      [communityId, platform, platformServerId, serverName, req.user.id]
    );

    logger.audit('Server link request created', {
      userId: req.user.id,
      communityId,
      platform,
      platformServerId,
      serverName,
    });

    res.status(201).json({
      success: true,
      approved: false,
      pending: true,
      message: 'Link request submitted. Waiting for community admin approval.',
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get servers linked to a community
 */
export async function getCommunityServers(req, res, next) {
  try {
    const communityId = parseInt(req.params.id, 10);

    if (isNaN(communityId)) {
      return next(errors.badRequest('Invalid community ID'));
    }

    const result = await query(
      `SELECT cs.id, cs.platform, cs.platform_server_id, cs.platform_server_name,
              cs.link_type, cs.is_primary, cs.config, cs.created_at,
              u.username as added_by_username
       FROM community_servers cs
       LEFT JOIN hub_users u ON u.id = cs.added_by
       WHERE cs.community_id = $1 AND cs.status = 'approved'
       ORDER BY cs.is_primary DESC, cs.created_at ASC`,
      [communityId]
    );

    const servers = result.rows.map(row => ({
      id: row.id,
      platform: row.platform,
      platformServerId: row.platform_server_id,
      platformServerName: row.platform_server_name,
      linkType: row.link_type,
      isPrimary: row.is_primary,
      config: row.config || {},
      addedBy: row.added_by_username,
      createdAt: row.created_at?.toISOString(),
    }));

    res.json({ success: true, servers });
  } catch (err) {
    next(err);
  }
}

/**
 * Get user's pending server link requests
 */
export async function getMyServerLinkRequests(req, res, next) {
  try {
    const result = await query(
      `SELECT slr.id, slr.community_id, slr.platform, slr.platform_server_id,
              slr.platform_server_name, slr.status, slr.review_note, slr.created_at,
              c.name as community_name, c.display_name as community_display_name
       FROM server_link_requests slr
       JOIN communities c ON c.id = slr.community_id
       WHERE slr.requested_by = $1
       ORDER BY slr.created_at DESC`,
      [req.user.id]
    );

    const requests = result.rows.map(row => ({
      id: row.id,
      communityId: row.community_id,
      communityName: row.community_display_name || row.community_name,
      platform: row.platform,
      platformServerId: row.platform_server_id,
      platformServerName: row.platform_server_name,
      status: row.status,
      reviewNote: row.review_note,
      createdAt: row.created_at?.toISOString(),
    }));

    res.json({ success: true, requests });
  } catch (err) {
    next(err);
  }
}

/**
 * Cancel server link request
 */
export async function cancelServerLinkRequest(req, res, next) {
  try {
    const requestId = parseInt(req.params.requestId, 10);

    if (isNaN(requestId)) {
      return next(errors.badRequest('Invalid request ID'));
    }

    const result = await query(
      `DELETE FROM server_link_requests
       WHERE id = $1 AND requested_by = $2 AND status = 'pending'
       RETURNING community_id, platform, platform_server_id`,
      [requestId, req.user.id]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Server link request not found or already processed'));
    }

    logger.audit('Server link request cancelled', {
      userId: req.user.id,
      requestId,
      communityId: result.rows[0].community_id,
      platform: result.rows[0].platform,
      platformServerId: result.rows[0].platform_server_id,
    });

    res.json({ success: true, message: 'Server link request cancelled' });
  } catch (err) {
    next(err);
  }
}

/**
 * Create a new community (authenticated user becomes owner)
 * POST /api/v1/communities/create
 */
export async function createCommunity(req, res, next) {
  try {
    const { name, displayName, description, platform, platformServerId, isPublic, communityType } = req.body;

    if (!name || !platform) {
      return next(errors.badRequest('Name and platform are required'));
    }

    // Validate community type
    const validatedCommunityType = communityType || 'creator';
    if (!VALID_COMMUNITY_TYPES.includes(validatedCommunityType)) {
      return next(errors.badRequest(
        `Invalid community type. Must be one of: ${VALID_COMMUNITY_TYPES.join(', ')}`
      ));
    }

    // Normalize community name
    const normalizedName = name
      .toLowerCase()
      .replace(/[^a-z0-9\s\-_]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .slice(0, 100);

    if (!normalizedName) {
      return next(errors.badRequest('Community name must contain valid characters'));
    }

    // Check if community name already exists
    const existingResult = await query(
      'SELECT id FROM communities WHERE name = $1',
      [normalizedName]
    );

    if (existingResult.rows.length > 0) {
      return next(errors.conflict('Community name already exists'));
    }

    const result = await transaction(async (client) => {
      // Create the community with the current user as owner
      const communityResult = await client.query(
        `INSERT INTO communities
         (name, display_name, description, platform, platform_server_id,
          owner_id, owner_name, is_public, community_type, member_count, created_by, tenant_id)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 1, $6, $10)
         RETURNING id, name, display_name, platform, community_type, created_at`,
        [
          normalizedName,
          displayName || name,
          description || '',
          platform,
          platformServerId || null,
          req.user.id,
          req.user.username || null,
          isPublic !== false,
          validatedCommunityType,
          req.user.tenantId || 1,
        ]
      );

      const newCommunity = communityResult.rows[0];

      // Seed system roles for the new community
      await client.query('SELECT seed_community_system_roles($1)', [newCommunity.id]);

      // Add creator as community-owner member (reputation starts at 600)
      const ownerRoleResult = await client.query(
        `SELECT id FROM community_roles WHERE community_id = $1 AND name = 'community-owner'`,
        [newCommunity.id]
      );
      const ownerRoleId = ownerRoleResult.rows[0]?.id || null;

      await client.query(
        `INSERT INTO community_members
         (community_id, user_id, role, community_role_id, reputation, is_active, joined_at)
         VALUES ($1, $2, 'community-owner', $3, 600, true, NOW())`,
        [newCommunity.id, req.user.id, ownerRoleId]
      );

      return newCommunity;
    });

    logger.audit('Community created by user', {
      userId: req.user.id,
      communityId: result.id,
      name: result.name,
      communityType: result.community_type,
    });

    res.status(201).json({
      success: true,
      community: {
        id: result.id,
        name: result.name,
        displayName: result.display_name,
        platform: result.platform,
        communityType: result.community_type,
        createdAt: result.created_at?.toISOString(),
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get connected platforms for a community
 * GET /api/v1/admin/:communityId/connected-platforms
 */
export async function getConnectedPlatforms(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const platforms = await query(`
      SELECT DISTINCT
        platform,
        COUNT(*) as server_count,
        BOOL_OR(is_active) as has_active_servers
      FROM community_servers
      WHERE community_id = $1
      GROUP BY platform
      ORDER BY platform
    `, [communityId]);

    res.json({
      success: true,
      connectedPlatforms: platforms.rows.map(p => ({
        platform: p.platform,
        serverCount: parseInt(p.server_count, 10),
        isActive: p.has_active_servers
      }))
    });
  } catch (err) {
    next(err);
  }
}
