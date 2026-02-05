/// Waddles chat message.
class ChatMessage {
  final String id;
  final String communityId;
  final String senderId;
  final String senderUsername;
  final String content;
  final String type;
  final DateTime createdAt;
  final MessageType messageType;
  final String? attachmentUrl;
  final String? replyToId;
  final Map<String, int> reactions;

  const ChatMessage({
    required this.id,
    required this.communityId,
    required this.senderId,
    required this.senderUsername,
    required this.content,
    this.type = 'text',
    required this.createdAt,
    this.messageType = MessageType.text,
    this.attachmentUrl,
    this.replyToId,
    this.reactions = const {},
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    final reactionsMap = <String, int>{};
    if (json['reactions'] is Map<String, dynamic>) {
      (json['reactions'] as Map<String, dynamic>).forEach((key, value) {
        reactionsMap[key] = value as int? ?? 0;
      });
    }

    return ChatMessage(
      id: json['id'] as String? ?? '',
      communityId: json['community_id'] as String? ?? '',
      senderId: json['sender_id'] as String? ?? '',
      senderUsername: json['sender_username'] as String? ?? '',
      content: json['content'] as String? ?? '',
      type: json['type'] as String? ?? 'text',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ??
          DateTime.now(),
      messageType: _parseMessageType(json['message_type'] as String?),
      attachmentUrl: json['attachment_url'] as String?,
      replyToId: json['reply_to_id'] as String?,
      reactions: reactionsMap,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'community_id': communityId,
        'sender_id': senderId,
        'sender_username': senderUsername,
        'content': content,
        'type': type,
        'created_at': createdAt.toIso8601String(),
        'message_type': messageType.name,
        if (attachmentUrl != null) 'attachment_url': attachmentUrl,
        if (replyToId != null) 'reply_to_id': replyToId,
        if (reactions.isNotEmpty) 'reactions': reactions,
      };
}

/// Parse MessageType from string representation.
MessageType _parseMessageType(String? typeStr) {
  if (typeStr == null) return MessageType.text;
  try {
    return MessageType.values.firstWhere(
      (e) => e.name == typeStr,
      orElse: () => MessageType.text,
    );
  } catch (_) {
    return MessageType.text;
  }
}

/// Waddles typing event.
class TypingEvent {
  final String communityId;
  final String channelName;
  final String userId;
  final String username;
  final bool isTyping;

  const TypingEvent({
    required this.communityId,
    required this.channelName,
    required this.userId,
    required this.username,
    required this.isTyping,
  });

  factory TypingEvent.fromJson(Map<String, dynamic> json) {
    return TypingEvent(
      communityId: json['community_id'] as String? ?? '',
      channelName: json['channel_name'] as String? ?? '',
      userId: json['user_id'] as String? ?? '',
      username: json['username'] as String? ?? '',
      isTyping: json['is_typing'] as bool? ?? false,
    );
  }
}

/// Message type enumeration.
enum MessageType { text, image, video, audio, system, announcement }

/// Waddles chat channel.
class ChatChannel {
  final String id;
  final String name;
  final String communityId;
  final String description;
  final int memberCount;
  final DateTime? lastMessageAt;

  const ChatChannel({
    required this.id,
    required this.name,
    required this.communityId,
    this.description = '',
    this.memberCount = 0,
    this.lastMessageAt,
  });

  factory ChatChannel.fromJson(Map<String, dynamic> json) {
    return ChatChannel(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      communityId: json['community_id'] as String? ?? '',
      description: json['description'] as String? ?? '',
      memberCount: json['member_count'] as int? ?? 0,
      lastMessageAt: json['last_message_at'] == null
          ? null
          : DateTime.tryParse(json['last_message_at'] as String),
    );
  }
}

/// Waddles message history with pagination support.
class MessageHistory {
  final List<ChatMessage> messages;
  final bool hasMore;
  final String? nextCursor;

  const MessageHistory({
    required this.messages,
    this.hasMore = false,
    this.nextCursor,
  });

  factory MessageHistory.fromJson(Map<String, dynamic> json) {
    final messageList = (json['messages'] as List<dynamic>?)
            ?.map((m) => ChatMessage.fromJson(m as Map<String, dynamic>))
            .toList() ??
        [];
    return MessageHistory(
      messages: messageList,
      hasMore: json['has_more'] as bool? ?? false,
      nextCursor: json['next_cursor'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'messages': messages.map((m) => m.toJson()).toList(),
        'has_more': hasMore,
        if (nextCursor != null) 'next_cursor': nextCursor,
      };
}

/// Waddles stream lifecycle event.
class StreamEvent {
  final StreamEventType type;
  final String streamId;
  final DateTime timestamp;
  final Map<String, dynamic>? metadata;
  final bool requiresPremium;

  const StreamEvent({
    required this.type,
    required this.streamId,
    required this.timestamp,
    this.metadata,
    this.requiresPremium = false,
  });

  Map<String, dynamic> toJson() => {
        'type': type.name,
        'stream_id': streamId,
        'timestamp': timestamp.toIso8601String(),
        'requires_premium': requiresPremium,
        if (metadata != null) 'metadata': metadata,
      };
}

enum StreamEventType { started, stopped, error }

/// Waddles stream metrics.
class StreamMetrics {
  final String streamId;
  final int bitrate;
  final int fps;
  final int droppedFrames;
  final int viewerCount;
  final Duration uptime;

  const StreamMetrics({
    required this.streamId,
    this.bitrate = 0,
    this.fps = 0,
    this.droppedFrames = 0,
    this.viewerCount = 0,
    this.uptime = Duration.zero,
  });

  Map<String, dynamic> toJson() => {
        'stream_id': streamId,
        'bitrate': bitrate,
        'fps': fps,
        'dropped_frames': droppedFrames,
        'viewer_count': viewerCount,
        'uptime_seconds': uptime.inSeconds,
      };
}

/// Waddles connection state.
enum WBConnectionState { disconnected, connecting, connected, error }
