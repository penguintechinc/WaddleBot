import 'dart:async';
import 'package:socket_io_client/socket_io_client.dart' as io;
import '../config/constants.dart';
import '../models/domain_config.dart';
import '../models/waddlebot_models.dart';
import 'waddlebot_auth_service.dart';

/// Waddles chat via Socket.io — real-time messages and typing events.
class WaddleBotChatService {
  final WaddleBotAuthService _authService;
  WaddleBotDomain _domain;
  io.Socket? _socket;
  int _reconnectAttempts = 0;
  Timer? _reconnectTimer;
  Timer? _typingDebounceTimer;
  Timer? _pingTimer;
  bool _isDisposed = false;
  bool _isProcessingMessage = false;

  final _messageController = StreamController<ChatMessage>.broadcast();
  final _typingController = StreamController<TypingEvent>.broadcast();
  final _connectionController = StreamController<WBConnectionState>.broadcast();
  final _channelsController = StreamController<List<ChatChannel>>.broadcast();
  final _messageHistoryController =
      StreamController<MessageHistory>.broadcast();

  WBConnectionState _connectionState = WBConnectionState.disconnected;
  String? _currentChannelId;
  final Map<String, MessageHistory> _messageHistoryCache = {};

  Stream<ChatMessage> get incomingMessages => _messageController.stream;
  Stream<TypingEvent> get typingEvents => _typingController.stream;
  Stream<WBConnectionState> get connectionState => _connectionController.stream;
  Stream<List<ChatChannel>> get channels => _channelsController.stream;
  Stream<MessageHistory> get messageHistory => _messageHistoryController.stream;
  WBConnectionState get currentConnectionState => _connectionState;
  String? get currentChannelId => _currentChannelId;

  WaddleBotChatService({
    WaddleBotAuthService? authService,
    WaddleBotDomain domain = WaddleBotDomain.production,
  })  : _authService = authService ?? WaddleBotAuthService(),
        _domain = domain;

  /// Connect to the Waddles chat socket with auth token in query.
  void connect() {
    if (_authService.accessToken == null) return;
    if (_isDisposed) return;

    _updateState(WBConnectionState.connecting);

    _socket = io.io(
      _domain.wsUrl,
      io.OptionBuilder()
          .setTransports(['websocket'])
          .setQuery({'token': _authService.accessToken})
          .setExtraHeaders({
            'Authorization': 'Bearer ${_authService.accessToken}',
          })
          .enableAutoConnect()
          .enableReconnection()
          .setReconnectionDelay(1000)
          .setReconnectionDelayMax(5000)
          .setReconnectionAttempts(10)
          .build(),
    );

    _socket!
      ..onConnect((_) {
        _reconnectAttempts = 0;
        _reconnectTimer?.cancel();
        _updateState(WBConnectionState.connected);
      })
      ..onDisconnect((_) {
        _updateState(WBConnectionState.disconnected);
      })
      ..onConnectError((error) {
        _updateState(WBConnectionState.error);
        _handleReconnectWithBackoff();
      })
      ..on('chat:message', (data) {
        if (_isProcessingMessage) return;
        _isProcessingMessage = true;
        try {
          if (data is Map<String, dynamic>) {
            _messageController.add(ChatMessage.fromJson(data));
          }
        } finally {
          _isProcessingMessage = false;
        }
      })
      ..on('chat:typing', (data) {
        if (_isProcessingMessage) return;
        _isProcessingMessage = true;
        try {
          if (data is Map<String, dynamic>) {
            _typingController.add(TypingEvent.fromJson(data));
          }
        } finally {
          _isProcessingMessage = false;
        }
      })
      ..on('chat:history', (data) {
        if (_isProcessingMessage) return;
        _isProcessingMessage = true;
        try {
          if (data is Map<String, dynamic>) {
            final history = MessageHistory.fromJson(data);
            final channelId = data['channel_id'] as String?;
            if (channelId != null) {
              _messageHistoryCache[channelId] = history;
              _messageHistoryController.add(history);
            }
          }
        } finally {
          _isProcessingMessage = false;
        }
      })
      ..on('chat:channels', (data) {
        if (_isProcessingMessage) return;
        _isProcessingMessage = true;
        try {
          if (data is List<dynamic>) {
            final channels = data
                .cast<Map<String, dynamic>>()
                .map((c) => ChatChannel.fromJson(c))
                .toList();
            _channelsController.add(channels);
          }
        } finally {
          _isProcessingMessage = false;
        }
      });

    // Keepalive ping
    _pingTimer = Timer.periodic(
      const Duration(seconds: AppConstants.waddleBotPingIntervalSec),
      (timer) {
        if (_isDisposed) {
          timer.cancel();
          return;
        }
        if (_socket?.connected == true) {
          _socket?.emit('ping');
        }
      },
    );
  }

  /// Get list of channels for a community.
  Future<List<ChatChannel>> getChannels(String communityId) async {
    final completer = Completer<List<ChatChannel>>();
    _socket?.emitWithAck('chat:list_channels', {'community_id': communityId},
        ack: (response) {
      if (response is List<dynamic>) {
        final channels = response
            .cast<Map<String, dynamic>>()
            .map((c) => ChatChannel.fromJson(c))
            .toList();
        completer.complete(channels);
      } else {
        completer.complete([]);
      }
    });
    return completer.future;
  }

  /// Join a specific channel by ID.
  void joinChannel(String channelId) {
    _currentChannelId = channelId;
    _socket?.emit('chat:join', {'channel_id': channelId});
  }

  /// Leave a specific channel by ID.
  void leaveChannel(String channelId) {
    _socket?.emit('chat:leave', {'channel_id': channelId});
    if (_currentChannelId == channelId) {
      _currentChannelId = null;
    }
  }

  /// Get paginated message history for a channel.
  /// [limit] - number of messages to fetch (default 20)
  /// [cursor] - pagination cursor for next batch (null for first page)
  Future<MessageHistory> getMessageHistory(String channelId,
      {int limit = 20, String? cursor}) async {
    final completer = Completer<MessageHistory>();
    _socket?.emitWithAck('chat:history', {
      'channel_id': channelId,
      'limit': limit,
      if (cursor != null) 'cursor': cursor,
    }, ack: (response) {
      if (response is Map<String, dynamic>) {
        final history = MessageHistory.fromJson(response);
        _messageHistoryCache[channelId] = history;
        completer.complete(history);
      } else {
        completer.complete(const MessageHistory(
            messages: [], hasMore: false, nextCursor: null));
      }
    });
    return completer.future;
  }

  /// Send a message to the current channel.
  void sendMessage(String content,
      {MessageType messageType = MessageType.text,
      String? attachmentUrl,
      String? replyToId}) {
    if (_currentChannelId == null) return;
    _socket?.emit('chat:send', {
      'channel_id': _currentChannelId,
      'content': content,
      'message_type': messageType.name,
      if (attachmentUrl != null) 'attachment_url': attachmentUrl,
      if (replyToId != null) 'reply_to_id': replyToId,
    });
  }

  /// Edit an existing message.
  void editMessage(String messageId, String newContent) {
    _socket?.emit('chat:edit', {
      'message_id': messageId,
      'content': newContent,
    });
  }

  /// Delete a message.
  void deleteMessage(String messageId) {
    _socket?.emit('chat:delete', {'message_id': messageId});
  }

  /// Add a reaction emoji to a message.
  void addReaction(String messageId, String emoji) {
    _socket?.emit('chat:add_reaction', {
      'message_id': messageId,
      'emoji': emoji,
    });
  }

  /// Remove a reaction emoji from a message.
  void removeReaction(String messageId, String emoji) {
    _socket?.emit('chat:remove_reaction', {
      'message_id': messageId,
      'emoji': emoji,
    });
  }

  /// Emit typing indicator with debouncing (300ms).
  void sendTypingIndicator(bool isTyping) {
    _typingDebounceTimer?.cancel();
    if (isTyping) {
      _typingDebounceTimer = Timer(const Duration(milliseconds: 300), () {
        if (_currentChannelId != null) {
          _socket?.emit('chat:typing', {
            'channel_id': _currentChannelId,
            'is_typing': true,
          });
        }
      });
    } else {
      if (_currentChannelId != null) {
        _socket?.emit('chat:typing', {
          'channel_id': _currentChannelId,
          'is_typing': false,
        });
      }
    }
  }

  /// Disconnect from the socket.
  void disconnect() {
    _reconnectTimer?.cancel();
    _typingDebounceTimer?.cancel();
    _pingTimer?.cancel();
    _pingTimer = null;
    _socket?.disconnect();
    _socket?.dispose();
    _socket = null;
    _updateState(WBConnectionState.disconnected);
  }

  /// Update the domain and reconnect if previously connected.
  /// Disconnects if currently connected, updates the domain, then reconnects.
  void updateDomain(WaddleBotDomain domain) {
    final wasConnected = _socket?.connected ?? false;

    // Disconnect if currently connected
    if (wasConnected) {
      disconnect();
    }

    // Update domain
    _domain = domain;

    // Reconnect if was previously connected
    if (wasConnected && !_isDisposed) {
      connect();
    }
  }

  /// Handle reconnection with exponential backoff.
  void _handleReconnectWithBackoff() {
    if (_isDisposed ||
        _reconnectAttempts >= AppConstants.waddleBotMaxReconnectAttempts) {
      return;
    }
    _reconnectAttempts++;

    final delayMs = AppConstants.waddleBotReconnectDelayMs *
        (1 << (_reconnectAttempts - 1).clamp(0, 5));
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(milliseconds: delayMs), () {
      if (_connectionState != WBConnectionState.connected && !_isDisposed) {
        _socket?.connect();
      }
    });
  }

  void _updateState(WBConnectionState state) {
    if (_isDisposed) return;
    _connectionState = state;
    _connectionController.add(state);
  }

  void dispose() {
    _isDisposed = true;
    _pingTimer?.cancel();
    _pingTimer = null;
    disconnect();
    _messageController.close();
    _typingController.close();
    _connectionController.close();
    _channelsController.close();
    _messageHistoryController.close();
  }
}
