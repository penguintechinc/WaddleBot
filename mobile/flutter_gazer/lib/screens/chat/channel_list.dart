import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:flutter_libs/flutter_libs.dart';
import '../../config/theme.dart';
import '../../models/waddlebot_models.dart';
import '../../services/waddlebot_chat_service.dart';
import 'chat_screen.dart';

/// Channel list screen - displays available chat channels with unread badges,
/// last message previews, and real-time updates via Socket.io.
class ChannelListScreen extends StatefulWidget {
  final String communityId;
  final WaddleBotChatService chatService;

  const ChannelListScreen({
    super.key,
    required this.communityId,
    required this.chatService,
  });

  @override
  State<ChannelListScreen> createState() => _ChannelListScreenState();
}

class _ChannelListScreenState extends State<ChannelListScreen> {
  late Future<List<ChatChannel>> _channelsFuture;
  final Map<String, int> _unreadCounts = {};
  final Map<String, ChatMessage?> _lastMessages = {};

  @override
  void initState() {
    super.initState();
    _channelsFuture = widget.chatService.getChannels(widget.communityId);

    // Listen for new messages to update unread counts
    widget.chatService.incomingMessages.listen((message) {
      if (mounted) {
        setState(() {
          _lastMessages[message.communityId] = message;
          // Increment unread count for channels where user isn't currently chatting
          if (widget.chatService.currentChannelId != message.communityId) {
            _unreadCounts[message.communityId] =
                (_unreadCounts[message.communityId] ?? 0) + 1;
          }
        });
      }
    });
  }

  Future<void> _onRefresh() async {
    if (!mounted) return;
    setState(() {
      _channelsFuture = widget.chatService.getChannels(widget.communityId);
    });
  }

  void _clearUnreadCount(String channelId) {
    if (!mounted) return;
    setState(() {
      _unreadCounts[channelId] = 0;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Channels'),
        elevation: 0,
        backgroundColor: ElderColors.slate800,
        foregroundColor: ElderColors.white,
      ),
      backgroundColor: ElderColors.slate950,
      body: RefreshIndicator(
        onRefresh: _onRefresh,
        color: ElderColors.amber500,
        backgroundColor: ElderColors.slate800,
        child: FutureBuilder<List<ChatChannel>>(
          future: _channelsFuture,
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
                      'Error loading channels',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: ElderColors.white,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      snapshot.error.toString(),
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: ElderColors.slate400,
                          ),
                    ),
                  ],
                ),
              );
            }

            final channels = snapshot.data ?? [];

            if (channels.isEmpty) {
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
                      'No channels available',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: ElderColors.white,
                          ),
                    ),
                  ],
                ),
              );
            }

            return ListView.builder(
              itemCount: channels.length,
              itemBuilder: (context, index) {
                final channel = channels[index];
                final unreadCount = _unreadCounts[channel.id] ?? 0;
                final lastMessage = _lastMessages[channel.id];

                return _ChannelListTile(
                  channel: channel,
                  unreadCount: unreadCount,
                  lastMessage: lastMessage,
                  onTap: () {
                    _clearUnreadCount(channel.id);
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (context) => ChatScreen(
                          channel: channel,
                          chatService: widget.chatService,
                        ),
                      ),
                    );
                  },
                );
              },
            );
          },
        ),
      ),
    );
  }

  @override
  void dispose() {
    super.dispose();
  }
}

/// Individual channel list tile with unread badge and last message preview.
class _ChannelListTile extends StatelessWidget {
  final ChatChannel channel;
  final int unreadCount;
  final ChatMessage? lastMessage;
  final VoidCallback onTap;

  const _ChannelListTile({
    required this.channel,
    required this.unreadCount,
    required this.lastMessage,
    required this.onTap,
  });

  String _formatLastMessageTime(DateTime? dateTime) {
    if (dateTime == null) return '';

    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inMinutes < 1) {
      return 'now';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      return DateFormat('MMM d').format(dateTime);
    }
  }

  String _getLastMessagePreview() {
    if (lastMessage == null) return 'No messages yet';

    const maxLength = 40;
    final content = lastMessage!.content;

    if (content.length > maxLength) {
      return '${content.substring(0, maxLength)}...';
    }
    return content;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: ElderColors.slate800,
            width: 1,
          ),
        ),
      ),
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: ElderColors.slate800,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: ElderColors.slate700,
            ),
          ),
          child: Center(
            child: Text(
              channel.name.isNotEmpty ? channel.name[0].toUpperCase() : '#',
              style: const TextStyle(
                color: ElderColors.amber500,
                fontWeight: FontWeight.bold,
                fontSize: 20,
              ),
            ),
          ),
        ),
        title: Row(
          children: [
            Expanded(
              child: Text(
                '#${channel.name}',
                style: const TextStyle(
                  color: ElderColors.white,
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (unreadCount > 0)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: GazerTheme.streamingRed,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  unreadCount.toString(),
                  style: const TextStyle(
                    color: ElderColors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
          ],
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            Text(
              _getLastMessagePreview(),
              style: const TextStyle(
                color: ElderColors.slate400,
                fontSize: 12,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '${channel.memberCount} members',
                  style: const TextStyle(
                    color: ElderColors.slate500,
                    fontSize: 11,
                  ),
                ),
                Text(
                  _formatLastMessageTime(lastMessage?.createdAt),
                  style: const TextStyle(
                    color: ElderColors.slate500,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ],
        ),
        trailing: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: ElderColors.slate800,
            borderRadius: BorderRadius.circular(6),
          ),
          child: const Icon(
            Icons.chevron_right,
            color: ElderColors.slate500,
            size: 20,
          ),
        ),
      ),
    );
  }
}
