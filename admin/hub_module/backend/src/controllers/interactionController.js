/**
 * Interaction Controller
 * Hub channel CRUD (chat, forum, voice) + forum post/reply management.
 */
import { query } from '../config/database.js';
import { logger } from '../utils/logger.js';
import { errors } from '../middleware/errorHandler.js';
import { relayMessage } from '../services/mirrorRelayService.js';

function safeJsonParse(val, fallback = []) {
  if (val === null || val === undefined) return fallback;
  if (typeof val === 'object') return val;
  try { return JSON.parse(val); } catch { return fallback; }
}

// ── Hub Server Auto-Provision ──────────────────────────────────────────

async function ensureHubServer(communityId) {
  const existing = await query(
    `SELECT id FROM community_servers
     WHERE community_id = $1 AND platform = 'hub' LIMIT 1`,
    [communityId]
  );
  if (existing.rows.length) return existing.rows[0].id;

  const result = await query(
    `INSERT INTO community_servers (community_id, platform, platform_server_id, name, status)
     VALUES ($1, 'hub', $2, 'Hub', 'approved')
     RETURNING id`,
    [communityId, `hub-${communityId}`]
  );
  return result.rows[0].id;
}

async function createServerChannel(hubServerId, hubChannelId, channelName, channelType) {
  const result = await query(
    `INSERT INTO community_server_channels
     (community_server_id, platform_channel_id, platform_channel_name, channel_type)
     VALUES ($1, $2, $3, $4)
     RETURNING id`,
    [hubServerId, `hub-ch-${hubChannelId}`, channelName, channelType]
  );
  return result.rows[0].id;
}

// ── Hub Channel CRUD ───────────────────────────────────────────────────

export async function getHubChannels(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId || req.params.id, 10);
    const result = await query(
      `SELECT id, community_id, name, description, channel_type,
              sort_order, is_active, allow_ad_hoc_voice,
              has_chat, has_voice, has_video, is_temporary, temp_duration_minutes, is_broadcast,
              community_server_channel_id, created_at
       FROM hub_channels
       WHERE community_id = $1 AND is_active = true
       ORDER BY channel_type, sort_order, name`,
      [communityId]
    );

    const channels = result.rows.map(r => ({
      id: r.id,
      communityId: r.community_id,
      name: r.name,
      description: r.description,
      channelType: r.channel_type,
      sortOrder: r.sort_order,
      isActive: r.is_active,
      allowAdHocVoice: r.allow_ad_hoc_voice,
      hasChat: r.has_chat,
      hasVoice: r.has_voice,
      hasVideo: r.has_video,
      isTemporary: r.is_temporary,
      tempDurationMinutes: r.temp_duration_minutes,
      isBroadcast: r.is_broadcast,
      communityServerChannelId: r.community_server_channel_id,
      createdAt: r.created_at,
    }));

    // Compute canCreateChannel for member routes (req.params.id present)
    let canCreateChannel = false;
    if (req.params.id && req.user) {
      // Admin-level users always can
      if (req.user.isSuperAdmin || req.isTenantAdmin || req.user.roles?.includes('platform-admin')) {
        canCreateChannel = true;
      } else {
        const policyResult = await query(
          `SELECT c.config,
                  cr.base_claims, cm.claims_cache
           FROM communities c
           LEFT JOIN community_members cm ON cm.community_id = c.id
             AND cm.user_id = $2 AND cm.is_active = true
           LEFT JOIN community_roles cr ON cr.id = cm.community_role_id
           WHERE c.id = $1`,
          [communityId, req.user.id]
        );
        if (policyResult.rows.length && (policyResult.rows[0].base_claims || policyResult.rows[0].claims_cache)) {
          const pRow = policyResult.rows[0];
          let scopes;
          if (pRow.claims_cache) {
            scopes = Array.isArray(pRow.claims_cache)
              ? pRow.claims_cache : (pRow.claims_cache.scopes || []);
          } else {
            const claims = typeof pRow.base_claims === 'string'
              ? JSON.parse(pRow.base_claims) : pRow.base_claims;
            scopes = (claims || {}).scopes || [];
          }
          const policy = (pRow.config || {}).channel_creation_policy || 'admin_only';
          if (policy === 'all_members') {
            canCreateChannel = true;
          } else if (policy === 'communicator') {
            canCreateChannel = scopes.includes('channels:create') || scopes.includes('community:manage_channels');
          } else {
            canCreateChannel = scopes.includes('community:manage_channels') || scopes.includes('community:manage_members');
          }
        }
      }
    }

    res.json({ success: true, channels, canCreateChannel });
  } catch (err) {
    logger.error('Failed to get hub channels', { error: err.message });
    return next(errors.internal('Failed to get hub channels'));
  }
}

export async function createHubChannel(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId || req.params.id, 10);
    const { name, description, channel_type = 'chat', sort_order = 0, allow_ad_hoc_voice = false,
            has_chat, has_voice, has_video, is_temporary, temp_duration_minutes, is_broadcast } = req.body;

    if (!name || !name.trim()) {
      return next(errors.validation('Channel name is required'));
    }

    const validTypes = ['chat', 'forum', 'voice'];
    if (!validTypes.includes(channel_type)) {
      return next(errors.validation('Invalid channel type'));
    }

    // Derive capability defaults from channel_type
    const resolvedHasChat = has_chat !== undefined ? has_chat : (channel_type === 'chat' || channel_type === 'forum');
    const resolvedHasVoice = has_voice !== undefined ? has_voice : (channel_type === 'voice');
    const resolvedHasVideo = has_video !== undefined ? has_video : false;
    const resolvedIsTemporary = is_temporary !== undefined ? is_temporary : false;
    const resolvedIsBroadcast = is_broadcast !== undefined ? is_broadcast : false;

    // Create the hub channel first (without server channel link)
    const chResult = await query(
      `INSERT INTO hub_channels
       (community_id, name, description, channel_type, sort_order, allow_ad_hoc_voice, has_chat, has_voice, has_video, is_temporary, temp_duration_minutes, is_broadcast, created_by)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
       RETURNING id, name, description, channel_type, sort_order, allow_ad_hoc_voice, has_chat, has_voice, has_video, is_temporary, temp_duration_minutes, is_broadcast, created_at`,
      [communityId, name.trim(), description || '', channel_type, sort_order, allow_ad_hoc_voice,
       resolvedHasChat, resolvedHasVoice, resolvedHasVideo, resolvedIsTemporary,
       temp_duration_minutes || null, resolvedIsBroadcast, req.user?.id]
    );

    const hubChannel = chResult.rows[0];

    // Auto-provision hub server + server channel entry
    const hubServerId = await ensureHubServer(communityId);
    const cscId = await createServerChannel(hubServerId, hubChannel.id, name.trim(), channel_type);

    // Link the hub channel to the server channel
    await query(
      `UPDATE hub_channels SET community_server_channel_id = $1 WHERE id = $2`,
      [cscId, hubChannel.id]
    );

    // Auto-insert deny overrides for 'member' role on broadcast channels
    if (resolvedIsBroadcast) {
      const memberRole = await query('SELECT id FROM community_roles WHERE community_id = $1 AND name = $2', [communityId, 'member']);
      if (memberRole.rows.length) {
        await query(
          `INSERT INTO hub_channel_permission_overrides (hub_channel_id, community_role_id, deny_scopes)
           VALUES ($1, $2, $3::jsonb)`,
          [hubChannel.id, memberRole.rows[0].id, JSON.stringify(['channels:send_chat', 'channels:speak'])]
        );
      }
    }

    logger.audit('Hub channel created', {
      channelId: hubChannel.id,
      channelName: name,
      channelType: channel_type,
      communityId,
      userId: req.user?.id,
    });

    res.status(201).json({
      success: true,
      channel: {
        id: hubChannel.id,
        communityId,
        name: hubChannel.name,
        description: hubChannel.description,
        channelType: hubChannel.channel_type,
        sortOrder: hubChannel.sort_order,
        allowAdHocVoice: hubChannel.allow_ad_hoc_voice,
        hasChat: hubChannel.has_chat,
        hasVoice: hubChannel.has_voice,
        hasVideo: hubChannel.has_video,
        isTemporary: hubChannel.is_temporary,
        tempDurationMinutes: hubChannel.temp_duration_minutes,
        isBroadcast: hubChannel.is_broadcast,
        communityServerChannelId: cscId,
        createdAt: hubChannel.created_at,
      },
    });
  } catch (err) {
    if (err.code === '23505') {
      return next(errors.conflict('A channel with that name already exists'));
    }
    logger.error('Failed to create hub channel', { error: err.message });
    return next(errors.internal('Failed to create hub channel'));
  }
}

export async function updateHubChannel(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const channelId = parseInt(req.params.id, 10);
    const { name, description, sort_order, allow_ad_hoc_voice,
            has_chat, has_voice, has_video, is_temporary, temp_duration_minutes, is_broadcast } = req.body;

    const updates = [];
    const params = [channelId, communityId];
    let idx = 3;

    if (name !== undefined) { updates.push(`name = $${idx}`); params.push(name.trim()); idx++; }
    if (description !== undefined) { updates.push(`description = $${idx}`); params.push(description); idx++; }
    if (sort_order !== undefined) { updates.push(`sort_order = $${idx}`); params.push(sort_order); idx++; }
    if (allow_ad_hoc_voice !== undefined) { updates.push(`allow_ad_hoc_voice = $${idx}`); params.push(allow_ad_hoc_voice); idx++; }
    if (has_chat !== undefined) { updates.push(`has_chat = $${idx}`); params.push(has_chat); idx++; }
    if (has_voice !== undefined) { updates.push(`has_voice = $${idx}`); params.push(has_voice); idx++; }
    if (has_video !== undefined) { updates.push(`has_video = $${idx}`); params.push(has_video); idx++; }
    if (is_temporary !== undefined) { updates.push(`is_temporary = $${idx}`); params.push(is_temporary); idx++; }
    if (temp_duration_minutes !== undefined) { updates.push(`temp_duration_minutes = $${idx}`); params.push(temp_duration_minutes); idx++; }
    if (is_broadcast !== undefined) { updates.push(`is_broadcast = $${idx}`); params.push(is_broadcast); idx++; }

    if (!updates.length) return next(errors.validation('No fields to update'));
    updates.push('updated_at = NOW()');

    const result = await query(
      `UPDATE hub_channels SET ${updates.join(', ')}
       WHERE id = $1 AND community_id = $2
       RETURNING id, name, description, channel_type, sort_order, allow_ad_hoc_voice, updated_at`,
      params
    );

    if (!result.rows.length) return next(errors.notFound('Channel not found'));

    res.json({ success: true, channel: result.rows[0] });
  } catch (err) {
    logger.error('Failed to update hub channel', { error: err.message });
    return next(errors.internal('Failed to update hub channel'));
  }
}

export async function deleteHubChannel(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const channelId = parseInt(req.params.id, 10);

    const result = await query(
      `UPDATE hub_channels SET is_active = false, updated_at = NOW()
       WHERE id = $1 AND community_id = $2
       RETURNING name`,
      [channelId, communityId]
    );

    if (!result.rows.length) return next(errors.notFound('Channel not found'));

    logger.audit('Hub channel deleted', { channelId, communityId, userId: req.user?.id });
    res.json({ success: true, message: 'Channel deleted' });
  } catch (err) {
    logger.error('Failed to delete hub channel', { error: err.message });
    return next(errors.internal('Failed to delete hub channel'));
  }
}

// ── Forum CRUD ─────────────────────────────────────────────────────────

export async function getForumPosts(req, res, next) {
  try {
    const communityId = parseInt(req.params.id || req.params.communityId, 10);
    const channelId = parseInt(req.params.channelId, 10);
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(50, Math.max(1, parseInt(req.query.limit || '20', 10)));
    const offset = (page - 1) * limit;

    const result = await query(
      `SELECT id, hub_channel_id, title, body, tags,
              author_hub_user_id, author_platform, author_username, author_avatar_url,
              is_pinned, is_locked, reply_count, last_reply_at,
              created_at, updated_at
       FROM hub_forum_posts
       WHERE hub_channel_id = $1 AND community_id = $2
       ORDER BY is_pinned DESC, last_reply_at DESC NULLS LAST, created_at DESC
       LIMIT $3 OFFSET $4`,
      [channelId, communityId, limit, offset]
    );

    const countResult = await query(
      `SELECT COUNT(*) FROM hub_forum_posts WHERE hub_channel_id = $1 AND community_id = $2`,
      [channelId, communityId]
    );

    const posts = result.rows.map(r => ({
      id: r.id,
      hubChannelId: r.hub_channel_id,
      title: r.title,
      body: r.body,
      tags: safeJsonParse(r.tags, []),
      authorHubUserId: r.author_hub_user_id,
      authorPlatform: r.author_platform,
      authorUsername: r.author_username,
      authorAvatarUrl: r.author_avatar_url,
      isPinned: r.is_pinned,
      isLocked: r.is_locked,
      replyCount: r.reply_count,
      lastReplyAt: r.last_reply_at,
      createdAt: r.created_at,
    }));

    res.json({
      success: true,
      posts,
      pagination: { page, limit, total: parseInt(countResult.rows[0].count, 10) },
    });
  } catch (err) {
    logger.error('Failed to get forum posts', { error: err.message });
    return next(errors.internal('Failed to get forum posts'));
  }
}

export async function getForumPost(req, res, next) {
  try {
    const communityId = parseInt(req.params.id || req.params.communityId, 10);
    const postId = parseInt(req.params.postId, 10);

    const postResult = await query(
      `SELECT id, hub_channel_id, title, body, tags,
              author_hub_user_id, author_platform, author_username, author_avatar_url,
              is_pinned, is_locked, reply_count, last_reply_at,
              created_at, updated_at
       FROM hub_forum_posts
       WHERE id = $1 AND community_id = $2`,
      [postId, communityId]
    );

    if (!postResult.rows.length) return next(errors.notFound('Post not found'));

    const repliesResult = await query(
      `SELECT id, post_id, author_hub_user_id, author_platform,
              author_username, author_avatar_url, content,
              platform_message_id, created_at
       FROM hub_forum_replies
       WHERE post_id = $1
       ORDER BY created_at ASC`,
      [postId]
    );

    const r = postResult.rows[0];
    const post = {
      id: r.id,
      hubChannelId: r.hub_channel_id,
      title: r.title,
      body: r.body,
      tags: safeJsonParse(r.tags, []),
      authorHubUserId: r.author_hub_user_id,
      authorPlatform: r.author_platform,
      authorUsername: r.author_username,
      authorAvatarUrl: r.author_avatar_url,
      isPinned: r.is_pinned,
      isLocked: r.is_locked,
      replyCount: r.reply_count,
      lastReplyAt: r.last_reply_at,
      createdAt: r.created_at,
      replies: repliesResult.rows.map(rep => ({
        id: rep.id,
        authorHubUserId: rep.author_hub_user_id,
        authorPlatform: rep.author_platform,
        authorUsername: rep.author_username,
        authorAvatarUrl: rep.author_avatar_url,
        content: rep.content,
        createdAt: rep.created_at,
      })),
    };

    res.json({ success: true, post });
  } catch (err) {
    logger.error('Failed to get forum post', { error: err.message });
    return next(errors.internal('Failed to get forum post'));
  }
}

export async function createForumPost(req, res, next) {
  try {
    const communityId = parseInt(req.params.id || req.params.communityId, 10);
    const channelId = parseInt(req.params.channelId, 10);
    const { title, body, tags } = req.body;

    if (!title || !title.trim()) return next(errors.validation('Title is required'));

    const result = await query(
      `INSERT INTO hub_forum_posts
       (hub_channel_id, community_id, title, body, tags,
        author_hub_user_id, author_platform, author_username, author_avatar_url)
       VALUES ($1, $2, $3, $4, $5, $6, 'hub', $7, $8)
       RETURNING id, title, body, tags, created_at`,
      [
        channelId, communityId, title.trim(), body || '', JSON.stringify(tags || []),
        req.user?.id, req.user?.username, req.user?.avatarUrl || null,
      ]
    );

    const post = result.rows[0];

    // Relay to bridged channels
    const channelResult = await query(
      `SELECT community_server_channel_id FROM hub_channels WHERE id = $1`,
      [channelId]
    );
    if (channelResult.rows[0]?.community_server_channel_id) {
      relayMessage({
        sourceMemberChannelId: channelResult.rows[0].community_server_channel_id,
        platform: 'hub',
        channelType: 'forum',
        content: { title: title.trim(), body: body || '', tags: tags || [] },
        author: { username: req.user?.username, avatarUrl: req.user?.avatarUrl, platform: 'hub' },
        messageType: 'forum_post',
      }).catch(err => logger.error('Forum post relay failed', { error: err.message }));
    }

    logger.audit('Forum post created', { postId: post.id, channelId, communityId, userId: req.user?.id });
    res.status(201).json({ success: true, post: { id: post.id, title: post.title, createdAt: post.created_at } });
  } catch (err) {
    logger.error('Failed to create forum post', { error: err.message });
    return next(errors.internal('Failed to create forum post'));
  }
}

export async function createForumReply(req, res, next) {
  try {
    const communityId = parseInt(req.params.id || req.params.communityId, 10);
    const postId = parseInt(req.params.postId, 10);
    const { content } = req.body;

    if (!content || !content.trim()) return next(errors.validation('Reply content is required'));

    // Verify post exists and not locked
    const postResult = await query(
      `SELECT p.id, p.is_locked, p.hub_channel_id, p.platform_thread_id,
              hc.community_server_channel_id
       FROM hub_forum_posts p
       JOIN hub_channels hc ON hc.id = p.hub_channel_id
       WHERE p.id = $1 AND p.community_id = $2`,
      [postId, communityId]
    );

    if (!postResult.rows.length) return next(errors.notFound('Post not found'));
    if (postResult.rows[0].is_locked) return next(errors.validation('This post is locked'));

    const result = await query(
      `INSERT INTO hub_forum_replies
       (post_id, author_hub_user_id, author_platform, author_username, author_avatar_url, content)
       VALUES ($1, $2, 'hub', $3, $4, $5)
       RETURNING id, content, created_at`,
      [postId, req.user?.id, req.user?.username, req.user?.avatarUrl || null, content.trim()]
    );

    await query(
      `UPDATE hub_forum_posts SET reply_count = reply_count + 1, last_reply_at = NOW() WHERE id = $1`,
      [postId]
    );

    // Relay reply to bridged channels
    const postRow = postResult.rows[0];
    if (postRow.community_server_channel_id) {
      relayMessage({
        sourceMemberChannelId: postRow.community_server_channel_id,
        platform: 'hub',
        channelType: 'forum',
        content: { text: content.trim(), platformThreadId: postRow.platform_thread_id },
        author: { username: req.user?.username, avatarUrl: req.user?.avatarUrl, platform: 'hub' },
        messageType: 'forum_reply',
      }).catch(err => logger.error('Forum reply relay failed', { error: err.message }));
    }

    res.status(201).json({ success: true, reply: result.rows[0] });
  } catch (err) {
    logger.error('Failed to create forum reply', { error: err.message });
    return next(errors.internal('Failed to create forum reply'));
  }
}

export async function moderateForumPost(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const postId = parseInt(req.params.id, 10);
    const { is_pinned, is_locked, delete: doDelete } = req.body;

    if (doDelete) {
      await query(`DELETE FROM hub_forum_posts WHERE id = $1 AND community_id = $2`, [postId, communityId]);
      return res.json({ success: true, message: 'Post deleted' });
    }

    const updates = [];
    const params = [postId, communityId];
    let idx = 3;

    if (is_pinned !== undefined) { updates.push(`is_pinned = $${idx}`); params.push(is_pinned); idx++; }
    if (is_locked !== undefined) { updates.push(`is_locked = $${idx}`); params.push(is_locked); idx++; }

    if (!updates.length) return next(errors.validation('No moderation action specified'));
    updates.push('updated_at = NOW()');

    await query(
      `UPDATE hub_forum_posts SET ${updates.join(', ')} WHERE id = $1 AND community_id = $2`,
      params
    );

    res.json({ success: true, message: 'Post moderated' });
  } catch (err) {
    logger.error('Failed to moderate forum post', { error: err.message });
    return next(errors.internal('Failed to moderate forum post'));
  }
}

export async function deleteForumReply(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const replyId = parseInt(req.params.id, 10);

    const result = await query(
      `DELETE FROM hub_forum_replies r
       USING hub_forum_posts p
       WHERE r.id = $1 AND r.post_id = p.id AND p.community_id = $2
       RETURNING r.post_id`,
      [replyId, communityId]
    );

    if (!result.rows.length) return next(errors.notFound('Reply not found'));

    // Decrement reply count
    await query(
      `UPDATE hub_forum_posts SET reply_count = GREATEST(reply_count - 1, 0) WHERE id = $1`,
      [result.rows[0].post_id]
    );

    res.json({ success: true, message: 'Reply deleted' });
  } catch (err) {
    logger.error('Failed to delete forum reply', { error: err.message });
    return next(errors.internal('Failed to delete forum reply'));
  }
}

// ── Internal Relay Endpoint ────────────────────────────────────────────

export async function internalRelayIncoming(req, res) {
  try {
    const { sourcePlatformChannelId, platform, channelType, content, author, messageType } = req.body;

    // Look up the community_server_channels row for the source
    const cscResult = await query(
      `SELECT id FROM community_server_channels WHERE platform_channel_id = $1 LIMIT 1`,
      [sourcePlatformChannelId]
    );

    if (!cscResult.rows.length) {
      return res.status(404).json({ success: false, error: 'Source channel not found' });
    }

    const io = req.app.get('io');

    await relayMessage({
      sourceMemberChannelId: cscResult.rows[0].id,
      platform: platform || author?.platform,
      channelType: channelType || 'chat',
      content,
      author,
      messageType: messageType || 'message',
      io,
    });

    res.json({ success: true });
  } catch (err) {
    logger.error('Internal relay incoming failed', { error: err.message });
    res.status(500).json({ success: false, error: 'Relay failed' });
  }
}

// ── Community Roles CRUD ─────────────────────────────────────────────

export async function getCommunityRoles(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const result = await query(
      `SELECT id, community_id, name, display_name, description, is_system, priority, base_claims, created_at, updated_at
       FROM community_roles WHERE community_id = $1 ORDER BY priority DESC, name`,
      [communityId]
    );
    const roles = result.rows.map(r => ({
      id: r.id, communityId: r.community_id, name: r.name,
      displayName: r.display_name, description: r.description,
      isSystem: r.is_system, priority: r.priority,
      scopes: safeJsonParse(r.base_claims, { scopes: [] }).scopes || [],
      createdAt: r.created_at, updatedAt: r.updated_at,
    }));
    res.json({ success: true, roles });
  } catch (err) {
    logger.error('Failed to get community roles', { error: err.message });
    return next(errors.internal('Failed to get community roles'));
  }
}

export async function createCommunityRole(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const { name, displayName, description, priority, scopes } = req.body;
    if (!name || !name.trim()) return next(errors.validation('Role name is required'));
    if (priority !== undefined && (priority < 0 || priority > 49)) {
      return next(errors.validation('Custom role priority must be between 0 and 49'));
    }
    const baseClaims = JSON.stringify({ scopes: scopes || [] });
    const result = await query(
      `INSERT INTO community_roles (community_id, name, display_name, description, is_system, priority, base_claims)
       VALUES ($1, $2, $3, $4, false, $5, $6::jsonb)
       RETURNING id, name, display_name, priority, base_claims, created_at`,
      [communityId, name.trim().toLowerCase(), displayName || name.trim(), description || '', priority || 0, baseClaims]
    );
    const role = result.rows[0];
    logger.audit('Community role created', { roleId: role.id, name: role.name, communityId, userId: req.user?.id });
    res.status(201).json({
      success: true,
      role: { id: role.id, name: role.name, displayName: role.display_name, priority: role.priority,
              scopes: safeJsonParse(role.base_claims, { scopes: [] }).scopes, createdAt: role.created_at },
    });
  } catch (err) {
    if (err.code === '23505') return next(errors.conflict('A role with that name already exists'));
    logger.error('Failed to create community role', { error: err.message });
    return next(errors.internal('Failed to create community role'));
  }
}

export async function updateCommunityRole(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const roleId = parseInt(req.params.roleId, 10);
    const { displayName, description, priority, scopes } = req.body;

    // Cannot edit system role scopes (only display_name/description)
    const existing = await query('SELECT is_system FROM community_roles WHERE id = $1 AND community_id = $2', [roleId, communityId]);
    if (!existing.rows.length) return next(errors.notFound('Role not found'));

    const updates = [];
    const params = [roleId, communityId];
    let idx = 3;
    if (displayName !== undefined) { updates.push(`display_name = $${idx}`); params.push(displayName); idx++; }
    if (description !== undefined) { updates.push(`description = $${idx}`); params.push(description); idx++; }
    if (priority !== undefined && !existing.rows[0].is_system) { updates.push(`priority = $${idx}`); params.push(priority); idx++; }
    if (scopes !== undefined && !existing.rows[0].is_system) {
      updates.push(`base_claims = $${idx}::jsonb`); params.push(JSON.stringify({ scopes })); idx++;
    }
    if (!updates.length) return next(errors.validation('No fields to update'));
    updates.push('updated_at = NOW()');

    await query(`UPDATE community_roles SET ${updates.join(', ')} WHERE id = $1 AND community_id = $2`, params);

    // Invalidate claims cache for affected members
    if (scopes !== undefined) {
      await query('UPDATE community_members SET claims_cache = NULL WHERE community_id = $1 AND community_role_id = $2', [communityId, roleId]);
    }

    logger.audit('Community role updated', { roleId, communityId, userId: req.user?.id });
    res.json({ success: true, message: 'Role updated' });
  } catch (err) {
    logger.error('Failed to update community role', { error: err.message });
    return next(errors.internal('Failed to update community role'));
  }
}

export async function deleteCommunityRole(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const roleId = parseInt(req.params.roleId, 10);

    const existing = await query('SELECT is_system, name FROM community_roles WHERE id = $1 AND community_id = $2', [roleId, communityId]);
    if (!existing.rows.length) return next(errors.notFound('Role not found'));
    if (existing.rows[0].is_system) return next(errors.forbidden('Cannot delete system roles'));

    // Reassign members to 'member' role
    const memberRole = await query('SELECT id FROM community_roles WHERE community_id = $1 AND name = $2', [communityId, 'member']);
    if (memberRole.rows.length) {
      await query('UPDATE community_members SET community_role_id = $1, claims_cache = NULL WHERE community_id = $2 AND community_role_id = $3',
        [memberRole.rows[0].id, communityId, roleId]);
    }

    await query('DELETE FROM community_roles WHERE id = $1 AND community_id = $2', [roleId, communityId]);
    logger.audit('Community role deleted', { roleId, name: existing.rows[0].name, communityId, userId: req.user?.id });
    res.json({ success: true, message: 'Role deleted, members reassigned to member role' });
  } catch (err) {
    logger.error('Failed to delete community role', { error: err.message });
    return next(errors.internal('Failed to delete community role'));
  }
}

// ── Channel Permission Overrides ─────────────────────────────────────

export async function getChannelPermissionOverrides(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const channelId = parseInt(req.params.id, 10);

    // Verify channel belongs to community
    const chCheck = await query('SELECT id FROM hub_channels WHERE id = $1 AND community_id = $2', [channelId, communityId]);
    if (!chCheck.rows.length) return next(errors.notFound('Channel not found'));

    const result = await query(
      `SELECT o.id, o.hub_channel_id, o.community_role_id, cr.name as role_name, cr.display_name as role_display_name,
              o.grant_scopes, o.deny_scopes, o.scope, o.created_at
       FROM hub_channel_permission_overrides o
       JOIN community_roles cr ON cr.id = o.community_role_id
       WHERE o.hub_channel_id = $1
       ORDER BY cr.priority DESC`,
      [channelId]
    );

    const overrides = result.rows.map(r => ({
      id: r.id, hubChannelId: r.hub_channel_id, communityRoleId: r.community_role_id,
      roleName: r.role_name, roleDisplayName: r.role_display_name,
      grantScopes: safeJsonParse(r.grant_scopes, []),
      denyScopes: safeJsonParse(r.deny_scopes, []),
      scope: r.scope, createdAt: r.created_at,
    }));

    res.json({ success: true, overrides });
  } catch (err) {
    logger.error('Failed to get channel permission overrides', { error: err.message });
    return next(errors.internal('Failed to get channel permission overrides'));
  }
}

export async function updateChannelPermissionOverrides(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const channelId = parseInt(req.params.id, 10);
    const { overrides } = req.body; // Array of { communityRoleId, grantScopes, denyScopes, scope }

    if (!Array.isArray(overrides)) return next(errors.validation('overrides must be an array'));

    const chCheck = await query('SELECT id FROM hub_channels WHERE id = $1 AND community_id = $2', [channelId, communityId]);
    if (!chCheck.rows.length) return next(errors.notFound('Channel not found'));

    // Replace all overrides in a transaction-like approach
    await query('DELETE FROM hub_channel_permission_overrides WHERE hub_channel_id = $1', [channelId]);

    for (const o of overrides) {
      if (!o.communityRoleId) continue;
      await query(
        `INSERT INTO hub_channel_permission_overrides (hub_channel_id, community_role_id, grant_scopes, deny_scopes, scope)
         VALUES ($1, $2, $3::jsonb, $4::jsonb, $5)`,
        [channelId, o.communityRoleId, JSON.stringify(o.grantScopes || []), JSON.stringify(o.denyScopes || []), o.scope || 'both']
      );
    }

    // Invalidate claims cache for all community members
    await query('UPDATE community_members SET claims_cache = NULL WHERE community_id = $1', [communityId]);

    logger.audit('Channel permission overrides updated', { channelId, communityId, count: overrides.length, userId: req.user?.id });
    res.json({ success: true, message: 'Permission overrides updated' });
  } catch (err) {
    logger.error('Failed to update channel permission overrides', { error: err.message });
    return next(errors.internal('Failed to update channel permission overrides'));
  }
}
