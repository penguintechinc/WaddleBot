/**
 * Chat Event Handler
 * Handles real-time chat events via WebSocket
 */
import { query } from '../config/database.js';
import { logger } from '../utils/logger.js';
import { relayMessage } from '../services/mirrorRelayService.js';

// Track active channels per socket
const activeChannels = new Map();

/**
 * Record hub chat message activity for leaderboards
 * This is a fire-and-forget operation that shouldn't block chat
 */
async function recordHubChatActivity(communityId, userId, username) {
  try {
    // Insert message event
    await query(
      `INSERT INTO activity_message_events
       (community_id, hub_user_id, platform, platform_user_id, platform_username, channel_id)
       VALUES ($1, $2, 'hub', $3, $4, 'hub-chat')`,
      [communityId, userId, String(userId), username]
    );

    // Update daily stats (upsert)
    await query(
      `INSERT INTO activity_stats_daily
       (community_id, hub_user_id, platform_user_id, platform_username, stat_date, message_count)
       VALUES ($1, $2, $3, $4, CURRENT_DATE, 1)
       ON CONFLICT (community_id, hub_user_id, platform_user_id, stat_date)
       DO UPDATE SET message_count = activity_stats_daily.message_count + 1, updated_at = NOW()`,
      [communityId, userId, String(userId), username]
    );
  } catch (err) {
    // Don't let activity tracking failures affect chat
    logger.error('Failed to record hub chat activity', {
      error: err.message,
      communityId,
      userId,
    });
  }
}

/**
 * Handle chat-related socket events
 */
export function handleChatEvents(io, socket) {
  /**
   * Join a community channel
   * Event: 'chat:join'
   * Payload: { communityId, channelName }
   */
  socket.on('chat:join', async (data) => {
    try {
      const { communityId, channelName } = data;

      if (!communityId) {
        socket.emit('chat:error', { error: 'Community ID required' });
        return;
      }

      // Create room name
      const roomName = channelName
        ? `community:${communityId}:${channelName}`
        : `community:${communityId}`;

      // Join the room
      await socket.join(roomName);

      // Track active channel for this socket
      if (!activeChannels.has(socket.id)) {
        activeChannels.set(socket.id, new Set());
      }
      activeChannels.get(socket.id).add(roomName);

      logger.audit('User joined chat channel', {
        userId: socket.userId,
        username: socket.username,
        communityId,
        channelName,
        roomName,
      });

      // Notify user of successful join
      socket.emit('chat:joined', {
        communityId,
        channelName,
        roomName,
      });

      // Notify others in the room
      socket.to(roomName).emit('chat:user-joined', {
        userId: socket.userId,
        username: socket.username,
        avatarUrl: socket.avatarUrl,
        platform: socket.platform,
      });
    } catch (err) {
      logger.error('Error joining chat channel', {
        error: err.message,
        userId: socket.userId,
      });
      socket.emit('chat:error', { error: 'Failed to join channel' });
    }
  });

  /**
   * Leave a channel
   * Event: 'chat:leave'
   * Payload: { communityId, channelName }
   */
  socket.on('chat:leave', async (data) => {
    try {
      const { communityId, channelName } = data;

      const roomName = channelName
        ? `community:${communityId}:${channelName}`
        : `community:${communityId}`;

      // Leave the room
      await socket.leave(roomName);

      // Remove from active channels
      if (activeChannels.has(socket.id)) {
        activeChannels.get(socket.id).delete(roomName);
      }

      logger.audit('User left chat channel', {
        userId: socket.userId,
        username: socket.username,
        communityId,
        channelName,
      });

      // Notify others in the room
      socket.to(roomName).emit('chat:user-left', {
        userId: socket.userId,
        username: socket.username,
      });

      socket.emit('chat:left', { communityId, channelName });
    } catch (err) {
      logger.error('Error leaving chat channel', {
        error: err.message,
        userId: socket.userId,
      });
      socket.emit('chat:error', { error: 'Failed to leave channel' });
    }
  });

  /**
   * Send a chat message
   * Event: 'chat:message'
   * Payload: { communityId, channelName, content, type }
   */
  socket.on('chat:message', async (data) => {
    try {
      const { communityId, channelName, content, type = 'text' } = data;

      if (!communityId || !content) {
        socket.emit('chat:error', { error: 'Community ID and content required' });
        return;
      }

      // Validate content length
      if (content.length > 2000) {
        socket.emit('chat:error', { error: 'Message too long (max 2000 characters)' });
        return;
      }

      // Store message in database
      const result = await query(
        `INSERT INTO hub_chat_messages
         (community_id, channel_name, sender_hub_user_id, sender_platform,
          sender_username, sender_avatar_url, message_content, message_type)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
         RETURNING id, created_at`,
        [
          communityId,
          channelName,
          socket.userId,
          socket.platform,
          socket.username,
          socket.avatarUrl,
          content,
          type,
        ]
      );

      const message = {
        id: result.rows[0].id,
        communityId,
        channelName,
        senderId: socket.userId,
        senderPlatform: socket.platform,
        senderUsername: socket.username,
        senderAvatarUrl: socket.avatarUrl,
        content,
        type,
        createdAt: result.rows[0].created_at,
      };

      // Determine room name
      const roomName = channelName
        ? `community:${communityId}:${channelName}`
        : `community:${communityId}`;

      // Broadcast to all users in the room (including sender)
      io.to(roomName).emit('chat:message', message);

      // Record activity for leaderboards (fire-and-forget)
      recordHubChatActivity(communityId, socket.userId, socket.username);

      // Relay to mirror group members (fire-and-forget)
      if (channelName && channelName.startsWith('hub-channel-')) {
        const hubChannelId = parseInt(channelName.replace('hub-channel-', ''), 10);
        if (hubChannelId) {
          query(
            `SELECT community_server_channel_id FROM hub_channels WHERE id = $1 AND community_id = $2`,
            [hubChannelId, communityId]
          ).then(result => {
            if (result.rows[0]?.community_server_channel_id) {
              relayMessage({
                sourceMemberChannelId: result.rows[0].community_server_channel_id,
                platform: 'hub',
                channelType: 'chat',
                content: { text: content },
                author: {
                  username: socket.username,
                  avatarUrl: socket.avatarUrl,
                  platform: 'hub',
                },
                messageType: 'message',
                io,
              }).catch(err => logger.error('Chat relay failed', { error: err.message }));
            }
          }).catch(err => logger.error('Hub channel lookup failed', { error: err.message }));
        }
      }

      logger.audit('Chat message sent', {
        messageId: message.id,
        userId: socket.userId,
        username: socket.username,
        communityId,
        channelName,
        contentLength: content.length,
      });
    } catch (err) {
      logger.error('Error sending chat message', {
        error: err.message,
        userId: socket.userId,
        data,
      });
      socket.emit('chat:error', { error: 'Failed to send message' });
    }
  });

  /**
   * Send typing indicator
   * Event: 'chat:typing'
   * Payload: { communityId, channelName, isTyping }
   */
  socket.on('chat:typing', (data) => {
    try {
      const { communityId, channelName, isTyping } = data;

      if (!communityId) return;

      const roomName = channelName
        ? `community:${communityId}:${channelName}`
        : `community:${communityId}`;

      // Broadcast typing indicator to others in room (not sender)
      socket.to(roomName).emit('chat:typing', {
        userId: socket.userId,
        username: socket.username,
        isTyping,
      });
    } catch (err) {
      logger.error('Error sending typing indicator', {
        error: err.message,
        userId: socket.userId,
      });
    }
  });

  /**
   * Request chat history
   * Event: 'chat:history'
   * Payload: { communityId, channelName, limit, before }
   */
  socket.on('chat:history', async (data) => {
    try {
      const { communityId, channelName, limit = 50, before } = data;

      if (!communityId) {
        socket.emit('chat:error', { error: 'Community ID required' });
        return;
      }

      let queryText = `
        SELECT id, community_id, channel_name, sender_hub_user_id,
               sender_platform, sender_username, sender_avatar_url,
               message_content, message_type, created_at
        FROM hub_chat_messages
        WHERE community_id = $1
      `;
      const params = [communityId];

      // Filter by channel if provided
      if (channelName) {
        queryText += ' AND channel_name = $2';
        params.push(channelName);
      }

      // Pagination with before timestamp
      if (before) {
        queryText += ` AND created_at < $${params.length + 1}`;
        params.push(before);
      }

      queryText += ` ORDER BY created_at DESC LIMIT $${params.length + 1}`;
      params.push(Math.min(limit, 100)); // Max 100 messages

      const result = await query(queryText, params);

      // Format messages
      const messages = result.rows.map((row) => ({
        id: row.id,
        communityId: row.community_id,
        channelName: row.channel_name,
        senderId: row.sender_hub_user_id,
        senderPlatform: row.sender_platform,
        senderUsername: row.sender_username,
        senderAvatarUrl: row.sender_avatar_url,
        content: row.message_content,
        type: row.message_type,
        createdAt: row.created_at,
      })).reverse(); // Reverse to show oldest first

      socket.emit('chat:history', {
        communityId,
        channelName,
        messages,
        hasMore: result.rows.length === Math.min(limit, 100),
      });

      logger.audit('Chat history requested', {
        userId: socket.userId,
        communityId,
        channelName,
        messageCount: messages.length,
      });
    } catch (err) {
      logger.error('Error fetching chat history', {
        error: err.message,
        userId: socket.userId,
        data,
      });
      socket.emit('chat:error', { error: 'Failed to fetch history' });
    }
  });

  /**
   * Handle socket disconnection
   */
  socket.on('disconnect', () => {
    // Leave all active channels
    if (activeChannels.has(socket.id)) {
      const channels = activeChannels.get(socket.id);
      channels.forEach((roomName) => {
        socket.to(roomName).emit('chat:user-left', {
          userId: socket.userId,
          username: socket.username,
        });
      });
      activeChannels.delete(socket.id);
    }
  });
}
