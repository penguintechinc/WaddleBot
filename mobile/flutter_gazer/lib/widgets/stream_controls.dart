import 'package:flutter/material.dart';
import '../config/theme.dart';

/// Bottom bar with stream start/stop, overlay toggle, and status.
class StreamControls extends StatelessWidget {
  final bool isStreaming;
  final String streamStatus;
  final VoidCallback onStartStop;
  final VoidCallback onToggleOverlay;
  final VoidCallback? onToggleChat;

  const StreamControls({
    super.key,
    required this.isStreaming,
    required this.streamStatus,
    required this.onStartStop,
    required this.onToggleOverlay,
    this.onToggleChat,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          top: BorderSide(
            color: Theme.of(context).dividerColor,
          ),
        ),
      ),
      child: Row(
        children: [
          // Stream status
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  streamStatus,
                  style: TextStyle(
                    color: isStreaming
                        ? GazerTheme.streamingRed
                        : Theme.of(context).textTheme.bodyMedium?.color,
                    fontWeight:
                        isStreaming ? FontWeight.bold : FontWeight.normal,
                  ),
                ),
                if (isStreaming)
                  Row(
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(
                          color: Colors.red,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        'LIVE',
                        style: TextStyle(
                          color: GazerTheme.streamingRed,
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
              ],
            ),
          ),
          // Chat toggle (Waddles)
          if (onToggleChat != null)
            IconButton(
              icon: const Icon(Icons.chat_bubble_outline),
              onPressed: onToggleChat,
              tooltip: 'Toggle Chat Overlay',
            ),
          // Overlay toggle
          IconButton(
            icon: const Icon(Icons.picture_in_picture),
            onPressed: onToggleOverlay,
            tooltip: 'Toggle Camera Overlay',
          ),
          const SizedBox(width: 8),
          // Start/Stop button
          FilledButton.icon(
            onPressed: onStartStop,
            icon: Icon(isStreaming ? Icons.stop : Icons.play_arrow),
            label: Text(isStreaming ? 'Stop' : 'Start'),
            style: FilledButton.styleFrom(
              backgroundColor:
                  isStreaming ? GazerTheme.streamingRed : null,
            ),
          ),
        ],
      ),
    );
  }
}
