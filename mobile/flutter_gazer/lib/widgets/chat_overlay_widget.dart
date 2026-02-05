import 'dart:async';
import 'package:flutter/material.dart';
import '../models/waddlebot_models.dart';
import '../services/waddlebot_chat_service.dart';

/// Transparent overlay showing the last few Waddles chat messages.
class ChatOverlayWidget extends StatefulWidget {
  final int maxMessages;

  const ChatOverlayWidget({super.key, this.maxMessages = 5});

  @override
  State<ChatOverlayWidget> createState() => _ChatOverlayWidgetState();
}

class _ChatOverlayWidgetState extends State<ChatOverlayWidget> {
  final List<ChatMessage> _messages = [];
  StreamSubscription? _messageSub;

  // In a real app, this would be injected via Provider or similar
  final WaddleBotChatService _chatService = WaddleBotChatService();

  @override
  void initState() {
    super.initState();
    _messageSub = _chatService.incomingMessages.listen((msg) {
      if (!mounted) return;
      setState(() {
        _messages.add(msg);
        if (_messages.length > widget.maxMessages) {
          _messages.removeAt(0);
        }
      });
    });
  }

  @override
  void dispose() {
    _messageSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 280,
      constraints: const BoxConstraints(maxHeight: 200),
      decoration: BoxDecoration(
        color: Colors.black54,
        borderRadius: BorderRadius.circular(8),
      ),
      padding: const EdgeInsets.all(8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: _messages.map((msg) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: RichText(
              text: TextSpan(
                children: [
                  TextSpan(
                    text: '${msg.senderUsername}: ',
                    style: const TextStyle(
                      color: Colors.amber,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                  TextSpan(
                    text: msg.content,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          );
        }).toList(),
      ),
    );
  }
}
