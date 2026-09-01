import 'dart:typed_data';

/// Video frame data from USB capture or camera.
class VideoFrame {
  final Uint8List data;
  final int width;
  final int height;
  final int format;
  final int timestamp;

  const VideoFrame({
    required this.data,
    required this.width,
    required this.height,
    required this.format,
    required this.timestamp,
  });

  bool get isError => format == -1;
}
