import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:flutter_libs/flutter_libs.dart';
import '../../config/theme.dart';
import '../../models/waddlebot_models.dart';
import '../../services/waddlebot_chat_service.dart';

/// Real-time chat screen with message list, text input, typing indicators,
/// and message pagination via Socket.io.
class ChatScreen extends StatefulWidget {
  final ChatChannel channel;
  final WaddleBotChatService chatService;

  const ChatScreen({
    super.key,
    required this.channel,
    required this.chatService,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  late final TextEditingController _messageController;
  late final ScrollController _scrollController;
  late Future<MessageHistory> _initialMessagesFuture;

  final List<ChatMessage> _messages = [];
  final Map<String, bool> _typingUsers = {};
  String? _nextCursor;
  bool _isLoadingMore = false;
  bool _hasMoreMessages = true;

  @override
  void initState() {
    super.initState();
    _messageController = TextEditingController();
    _scrollController = ScrollController();

    // Join the channel
    widget.chatService.joinChannel(widget.channel.id);

    // Load initial message history
    _initialMessagesFuture =
        widget.chatService.getMessageHistory(widget.channel.id);

    // Listen for real-time incoming messages
    widget.chatService.incomingMessages.listen((message) {
      if (mounted && message.id == widget.channel.id) {
        setState(() {
          _messages.insert(0, message);
        });
        _scrollToBottom();
      }
    });

    // Listen for typing indicators
    widget.chatService.typingEvents.listen((typingEvent) {
      if (mounted) {
        setState(() {
          if (typingEvent.isTyping) {
            _typingUsers[typingEvent.userId] = true;
          } else {
            _typingUsers.remove(typingEvent.userId);
          }
        });
      }
    });

    // Set up scroll listener for pagination
    _scrollController.addListener(_onScroll);
  }

  void _onScroll() {
    if (_scrollController.position.pixels >
        _scrollController.position.maxScrollExtent - 500) {
      if (!_isLoadingMore && _hasMoreMessages) {
        _loadMoreMessages();
      }
    }
  }

  Future<void> _loadMoreMessages() async {
    if (_isLoadingMore || !_hasMoreMessages) return;

    setState(() {
      _isLoadingMore = true;
    });

    try {
      final history = await widget.chatService.getMessageHistory(
        widget.channel.id,
        cursor: _nextCursor,
      );

      if (mounted) {
        setState(() {
          _messages.addAll(history.messages);
          _nextCursor = history.nextCursor;
          _hasMoreMessages = history.hasMore;
          _isLoadingMore = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoadingMore = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Failed to load more messages'),
            backgroundColor: GazerTheme.streamingRed,
          ),
        );
      }
    }
  }

  void _scrollToBottom() {
    Future.microtask(() {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          0,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _sendMessage() {
    final content = _messageController.text.trim();
    if (content.isEmpty) return;

    widget.chatService.sendMessage(content, messageType: MessageType.text);
    _messageController.clear();
    widget.chatService.sendTypingIndicator(false);
  }

  void _onMessageChanged(String value) {
    if (value.isNotEmpty) {
      widget.chatService.sendTypingIndicator(true);
    } else {
      widget.chatService.sendTypingIndicator(false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(widget.channel.name),
            if (_typingUsers.isNotEmpty)
              Text(
                '${_typingUsers.length} typing...',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: ElderColors.amber500,
                    ),
              ),
          ],
        ),
        elevation: 0,
        backgroundColor: ElderColors.slate800,
        foregroundColor: ElderColors.white,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(4),
          child: _ConnectionStatusIndicator(
            connectionState: widget.chatService.currentConnectionState,
          ),
        ),
      ),
      backgroundColor: ElderColors.slate950,
      body: Column(
        children: [
          // Connection status banner
          StreamBuilder<WBConnectionState>(
            stream: widget.chatService.connectionState,
            builder: (context, snapshot) {
              final state = snapshot.data ?? WBConnectionState.disconnected;
              if (state == WBConnectionState.connected) {
                return const SizedBox.shrink();
              }

              return Container(
                padding: const EdgeInsets.symmetric(vertical: 8),
                color: state == WBConnectionState.error
                    ? GazerTheme.streamingRed.withValues(alpha: 0.2)
                    : ElderColors.amber700.withValues(alpha: 0.2),
                child: Center(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      SizedBox(
                        width: 12,
                        height: 12,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            state == WBConnectionState.error
                                ? GazerTheme.streamingRed
                                : ElderColors.amber500,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        state == WBConnectionState.error
                            ? 'Connection error'
                            : 'Connecting...',
                        style: TextStyle(
                          color: state == WBConnectionState.error
                              ? GazerTheme.streamingRed
                              : ElderColors.amber500,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
          // Messages list
          Expanded(
            child: FutureBuilder<MessageHistory>(
              future: _initialMessagesFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(
                    child: CircularProgressIndicator(
                      valueColor:
                          AlwaysStoppedAnimation<Color>(ElderColors.amber500),
                    ),
                  );
                }

                if (snapshot.hasError) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.error_outline,
                          size: 48,
                          color: GazerTheme.streamingRed,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'Failed to load messages',
                          style:
                              Theme.of(context).textTheme.titleMedium?.copyWith(
                                    color: ElderColors.white,
                                  ),
                        ),
                      ],
                    ),
                  );
                }

                final initialMessages = snapshot.data?.messages ?? [];

                if (_messages.isEmpty && initialMessages.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(
                          Icons.chat_bubble_outline,
                          size: 48,
                          color: ElderColors.slate600,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'No messages yet',
                          style:
                              Theme.of(context).textTheme.titleMedium?.copyWith(
                                    color: ElderColors.white,
                                  ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Start the conversation!',
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: ElderColors.slate400,
                                  ),
                        ),
                      ],
                    ),
                  );
                }

                final allMessages = _messages.isEmpty
                    ? initialMessages
                    : [...initialMessages, ..._messages];

                return Stack(
                  children: [
                    ListView.builder(
                      controller: _scrollController,
                      reverse: true,
                      itemCount: allMessages.length +
                          (_isLoadingMore || !_hasMoreMessages ? 0 : 1),
                      itemBuilder: (context, index) {
                        if (index == allMessages.length) {
                          if (!_hasMoreMessages) {
                            return const Padding(
                              padding: EdgeInsets.symmetric(vertical: 16),
                              child: Center(
                                child: Text(
                                  'No more messages',
                                  style: TextStyle(
                                    color: ElderColors.slate500,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                            );
                          }

                          return const Padding(
                            padding: EdgeInsets.symmetric(vertical: 16),
                            child: Center(
                              child: SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  valueColor: AlwaysStoppedAnimation<Color>(
                                    ElderColors.amber500,
                                  ),
                                ),
                              ),
                            ),
                          );
                        }

                        final message =
                            allMessages[allMessages.length - 1 - index];
                        return _MessageBubble(message: message);
                      },
                    ),
                    // Floating typing indicator
                    if (_typingUsers.isNotEmpty)
                      Positioned(
                        bottom: 0,
                        left: 0,
                        right: 0,
                        child: _TypingIndicator(
                          typingUserCount: _typingUsers.length,
                        ),
                      ),
                  ],
                );
              },
            ),
          ),
          // Message input area
          _MessageInputField(
            messageController: _messageController,
            onSendPressed: _sendMessage,
            onChanged: _onMessageChanged,
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    widget.chatService.leaveChannel(widget.channel.id);
    _messageController.dispose();
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }
}

/// Individual message bubble with sender info and timestamp.
class _MessageBubble extends StatelessWidget {
  final ChatMessage message;

  const _MessageBubble({required this.message});

  String _formatTime(DateTime dateTime) {
    return DateFormat('HH:mm').format(dateTime);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                message.senderUsername,
                style: const TextStyle(
                  color: ElderColors.amber500,
                  fontWeight: FontWeight.w600,
                  fontSize: 12,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                _formatTime(message.createdAt),
                style: const TextStyle(
                  color: ElderColors.slate500,
                  fontSize: 11,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: ElderColors.slate800,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: ElderColors.slate700,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  message.content,
                  style: const TextStyle(
                    color: ElderColors.white,
                    fontSize: 13,
                    height: 1.4,
                  ),
                  maxLines: null,
                ),
                if (message.reactions.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 4,
                    children: message.reactions.entries.map((entry) {
                      return Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: ElderColors.slate700,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          '${entry.key} ${entry.value}',
                          style: const TextStyle(
                            fontSize: 11,
                            color: ElderColors.white,
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Message input field with send button and typing indicator support.
class _MessageInputField extends StatefulWidget {
  final TextEditingController messageController;
  final VoidCallback onSendPressed;
  final ValueChanged<String> onChanged;

  const _MessageInputField({
    required this.messageController,
    required this.onSendPressed,
    required this.onChanged,
  });

  @override
  State<_MessageInputField> createState() => _MessageInputFieldState();
}

class _MessageInputFieldState extends State<_MessageInputField> {
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    widget.messageController.addListener(_updateHasText);
  }

  void _updateHasText() {
    if (!mounted) return;
    setState(() {
      _hasText = widget.messageController.text.isNotEmpty;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: ElderColors.slate800,
      padding: const EdgeInsets.all(12),
      child: SafeArea(
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: widget.messageController,
                onChanged: widget.onChanged,
                maxLines: null,
                minLines: 1,
                textCapitalization: TextCapitalization.sentences,
                decoration: InputDecoration(
                  hintText: 'Type a message...',
                  hintStyle: const TextStyle(
                    color: ElderColors.slate500,
                  ),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                    borderSide: const BorderSide(
                      color: ElderColors.slate700,
                    ),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                    borderSide: const BorderSide(
                      color: ElderColors.slate700,
                    ),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                    borderSide: const BorderSide(
                      color: ElderColors.amber500,
                    ),
                  ),
                  filled: true,
                  fillColor: ElderColors.slate900,
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 10,
                  ),
                  isDense: true,
                ),
                style: const TextStyle(
                  color: ElderColors.white,
                ),
                cursorColor: ElderColors.amber500,
              ),
            ),
            const SizedBox(width: 8),
            Container(
              decoration: BoxDecoration(
                color: _hasText ? ElderColors.amber500 : ElderColors.slate700,
                borderRadius: BorderRadius.circular(8),
              ),
              child: IconButton(
                onPressed: _hasText ? widget.onSendPressed : null,
                icon: const Icon(Icons.send),
                color: _hasText ? ElderColors.slate900 : ElderColors.slate500,
                iconSize: 20,
                padding: const EdgeInsets.all(8),
                constraints: const BoxConstraints(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    widget.messageController.removeListener(_updateHasText);
    super.dispose();
  }
}

/// Typing indicator showing users currently typing.
class _TypingIndicator extends StatefulWidget {
  final int typingUserCount;

  const _TypingIndicator({required this.typingUserCount});

  @override
  State<_TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<_TypingIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    )..repeat();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          const Text(
            'Someone is typing',
            style: TextStyle(
              color: ElderColors.slate400,
              fontSize: 12,
              fontStyle: FontStyle.italic,
            ),
          ),
          const SizedBox(width: 8),
          Row(
            children: List.generate(3, (index) {
              return ScaleTransition(
                scale: Tween<double>(begin: 0.6, end: 1.0).animate(
                  CurvedAnimation(
                    parent: _animationController,
                    curve: Interval(
                      index * 0.2,
                      (index + 1) * 0.2 + 0.6,
                      curve: Curves.easeInOut,
                    ),
                  ),
                ),
                child: Container(
                  width: 6,
                  height: 6,
                  margin: const EdgeInsets.symmetric(horizontal: 2),
                  decoration: BoxDecoration(
                    color: ElderColors.amber500,
                    borderRadius: BorderRadius.circular(3),
                  ),
                ),
              );
            }),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }
}

/// Connection status indicator shown in app bar.
class _ConnectionStatusIndicator extends StatelessWidget {
  final WBConnectionState connectionState;

  const _ConnectionStatusIndicator({
    required this.connectionState,
  });

  @override
  Widget build(BuildContext context) {
    Color statusColor;
    switch (connectionState) {
      case WBConnectionState.connected:
        statusColor = GazerTheme.connectedGreen;
      case WBConnectionState.connecting:
        statusColor = ElderColors.amber500;
      case WBConnectionState.error:
        statusColor = GazerTheme.streamingRed;
      default:
        statusColor = ElderColors.slate700;
    }

    return Container(
      height: 4,
      color: statusColor,
    );
  }
}
