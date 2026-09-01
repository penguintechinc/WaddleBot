import 'package:flutter/material.dart';

/// Displays the video preview from the USB capture texture.
class StreamPreviewWidget extends StatelessWidget {
  final int? textureId;

  const StreamPreviewWidget({super.key, this.textureId});

  @override
  Widget build(BuildContext context) {
    if (textureId != null && textureId! >= 0) {
      return AspectRatio(
        aspectRatio: 16 / 9,
        child: Texture(textureId: textureId!),
      );
    }
    return Container(
      color: Colors.black,
      child: const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.videocam_off, size: 64, color: Colors.white38),
            SizedBox(height: 16),
            Text(
              'Video Preview',
              style: TextStyle(color: Colors.white54, fontSize: 18),
            ),
            SizedBox(height: 4),
            Text(
              '(Connect USB Device)',
              style: TextStyle(color: Colors.white38, fontSize: 14),
            ),
          ],
        ),
      ),
    );
  }
}
