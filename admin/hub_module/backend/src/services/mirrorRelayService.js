/**
 * Mirror Relay Service
 * Unified entry point for bridging messages across mirror group members.
 * All platforms (hub, discord, slack) are treated equally — the relay
 * fans out to every other active member in the same mirror group(s).
 */
import { query } from '../config/database.js';
import { logger } from '../utils/logger.js';
import axios from 'axios';

const DISCORD_BOT_RELAY_URL = process.env.DISCORD_BOT_RELAY_URL || 'http://discord-bot-service:8080/internal/relay';
const SLACK_BOT_RELAY_URL = process.env.SLACK_BOT_RELAY_URL || 'http://slack-bot-service:8081/internal/relay';
const TEAMS_BOT_RELAY_URL = process.env.TEAMS_BOT_RELAY_URL || 'http://waddlebot-teams-collector:8008/internal/relay';
const MATTERMOST_BOT_RELAY_URL = process.env.MATTERMOST_BOT_RELAY_URL || 'http://waddlebot-mattermost-collector:8009/internal/relay';
const GOOGLECHAT_BOT_RELAY_URL = process.env.GOOGLECHAT_BOT_RELAY_URL || 'http://waddlebot-googlechat-collector:8012/internal/relay';

// Relay timeout — don't let slow bots block the sender
const RELAY_TIMEOUT_MS = 5000;

/**
 * Relay a message from one mirror group member to all others.
 *
 * @param {object} opts
 * @param {number} opts.sourceMemberChannelId - community_server_channels.id of the source
 * @param {string} opts.platform              - source platform ('hub', 'discord', 'slack', etc.)
 * @param {string} opts.channelType           - 'chat' or 'forum'
 * @param {object} opts.content               - message payload (shape depends on channelType)
 * @param {object} opts.author                - { username, avatarUrl, platform }
 * @param {string} opts.messageType           - 'message', 'forum_post', 'forum_reply'
 * @param {number} [opts.excludeTargetId]     - community_server_channel_id to skip (echo prevention)
 * @param {object} [opts.io]                  - Socket.IO server instance (for hub targets)
 */
export async function relayMessage({
  sourceMemberChannelId,
  platform,
  channelType = 'chat',
  content,
  author,
  messageType = 'message',
  excludeTargetId,
  io,
}) {
  try {
    // Find all mirror groups this source channel belongs to
    const groupsResult = await query(
      `SELECT DISTINCT mg.id AS group_id, mg.channel_type
       FROM mirror_group_members mgm
       JOIN mirror_groups mg ON mg.id = mgm.mirror_group_id
       WHERE mgm.community_server_channel_id = $1
         AND mgm.is_active = true
         AND mg.channel_type = $2`,
      [sourceMemberChannelId, channelType]
    );

    if (!groupsResult.rows.length) return;

    const groupIds = groupsResult.rows.map(r => r.group_id);

    // Find all other active members in those groups
    const targetsResult = await query(
      `SELECT mgm.community_server_channel_id AS target_channel_id,
              cs.platform AS target_platform,
              csc.platform_channel_id,
              csc.platform_channel_name,
              mgm.direction,
              hc.id AS hub_channel_id,
              hc.community_id
       FROM mirror_group_members mgm
       JOIN community_server_channels csc ON csc.id = mgm.community_server_channel_id
       JOIN community_servers cs ON cs.id = csc.community_server_id
       LEFT JOIN hub_channels hc ON hc.community_server_channel_id = csc.id
       WHERE mgm.mirror_group_id = ANY($1)
         AND mgm.is_active = true
         AND mgm.community_server_channel_id != $2`,
      [groupIds, sourceMemberChannelId]
    );

    // Determine valid directions based on source platform
    const isFromHub = platform === 'hub';

    const dispatches = targetsResult.rows
      .filter(t => {
        if (excludeTargetId && t.target_channel_id === excludeTargetId) return false;
        // Direction filtering
        if (isFromHub && t.direction === 'to_hub') return false;  // target only receives from platform
        if (!isFromHub && t.direction === 'from_hub') return false; // target only sends to platform
        return true;
      })
      .map(t => dispatchToTarget(t, content, author, messageType, io));

    await Promise.allSettled(dispatches);
  } catch (err) {
    logger.error('Mirror relay failed', {
      error: err.message,
      sourceMemberChannelId,
      platform,
      channelType,
    });
  }
}

/**
 * Dispatch a relayed message to a single target member.
 */
async function dispatchToTarget(target, content, author, messageType, io) {
  try {
    switch (target.target_platform) {
      case 'hub':
        return dispatchToHub(target, content, author, messageType, io);
      case 'discord':
        return dispatchToPlatformBot(DISCORD_BOT_RELAY_URL, target, content, author, messageType);
      case 'slack':
        return dispatchToPlatformBot(SLACK_BOT_RELAY_URL, target, content, author, messageType);
      case 'teams':
        return dispatchToPlatformBot(TEAMS_BOT_RELAY_URL, target, content, author, messageType);
      case 'mattermost':
        return dispatchToPlatformBot(MATTERMOST_BOT_RELAY_URL, target, content, author, messageType);
      case 'googlechat':
        return dispatchToPlatformBot(GOOGLECHAT_BOT_RELAY_URL, target, content, author, messageType);
      default:
        logger.warn('Unknown target platform for relay', { platform: target.target_platform });
    }
  } catch (err) {
    logger.error('Dispatch to target failed', {
      error: err.message,
      targetChannelId: target.target_channel_id,
      targetPlatform: target.target_platform,
    });
  }
}

/**
 * Dispatch to a hub channel via Socket.IO or DB insert (for forums).
 */
async function dispatchToHub(target, content, author, messageType, io) {
  if (messageType === 'message' && io && target.hub_channel_id) {
    // Emit to the Socket.IO room for this hub channel
    const roomName = `community:${target.community_id}:hub-channel-${target.hub_channel_id}`;
    io.to(roomName).emit('chat:bridged-message', {
      communityId: target.community_id,
      hubChannelId: target.hub_channel_id,
      content: content.text || content.content,
      author,
      createdAt: new Date().toISOString(),
    });

    // Also persist the bridged message
    await query(
      `INSERT INTO hub_chat_messages
       (community_id, channel_name, hub_channel_id, sender_platform,
        sender_username, sender_avatar_url, message_content, message_type)
       VALUES ($1, $2, $3, $4, $5, $6, $7, 'text')`,
      [
        target.community_id,
        `hub-channel-${target.hub_channel_id}`,
        target.hub_channel_id,
        author.platform,
        author.username,
        author.avatarUrl || null,
        content.text || content.content,
      ]
    );
  } else if (messageType === 'forum_post' && target.hub_channel_id) {
    await query(
      `INSERT INTO hub_forum_posts
       (hub_channel_id, community_id, title, body, tags,
        author_platform, author_username, author_avatar_url, platform_thread_id)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
      [
        target.hub_channel_id,
        target.community_id,
        content.title,
        content.body || '',
        JSON.stringify(content.tags || []),
        author.platform,
        author.username,
        author.avatarUrl || null,
        content.platformThreadId || null,
      ]
    );
  } else if (messageType === 'forum_reply' && target.hub_channel_id) {
    // Find matching post by platform_thread_id
    const postResult = await query(
      `SELECT id FROM hub_forum_posts
       WHERE hub_channel_id = $1 AND platform_thread_id = $2
       LIMIT 1`,
      [target.hub_channel_id, content.platformThreadId]
    );
    if (postResult.rows.length) {
      const postId = postResult.rows[0].id;
      await query(
        `INSERT INTO hub_forum_replies
         (post_id, author_platform, author_username, author_avatar_url, content, platform_message_id)
         VALUES ($1, $2, $3, $4, $5, $6)`,
        [postId, author.platform, author.username, author.avatarUrl || null, content.text, content.platformMessageId || null]
      );
      await query(
        `UPDATE hub_forum_posts SET reply_count = reply_count + 1, last_reply_at = NOW() WHERE id = $1`,
        [postId]
      );
    }
  }
}

/**
 * Dispatch to a platform bot via its internal relay HTTP endpoint.
 */
async function dispatchToPlatformBot(relayUrl, target, content, author, messageType) {
  await axios.post(relayUrl, {
    platformChannelId: target.platform_channel_id,
    channelName: target.platform_channel_name,
    content,
    author,
    messageType,
  }, {
    timeout: RELAY_TIMEOUT_MS,
  });
}
