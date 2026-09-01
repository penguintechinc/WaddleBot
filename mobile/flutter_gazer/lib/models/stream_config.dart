/// Stream configuration model.
class StreamConfig {
  final int width;
  final int height;
  final int fps;
  final int videoBitrate;
  final int audioBitrate;
  final int sampleRate;
  final int iFrameInterval;
  final String rtmpUrl;
  final String streamKey;
  final bool requiresPremium;
  final bool isExternalRtmp;
  final int? maxBitrate;

  const StreamConfig({
    this.width = 1280,
    this.height = 720,
    this.fps = 30,
    this.videoBitrate = 3000000,
    this.audioBitrate = 128000,
    this.sampleRate = 44100,
    this.iFrameInterval = 5,
    this.rtmpUrl = '',
    this.streamKey = '',
    this.requiresPremium = false,
    this.isExternalRtmp = false,
    this.maxBitrate,
  });

  String get fullUrl {
    if (streamKey.isEmpty) return rtmpUrl;
    return rtmpUrl.endsWith('/') ? '$rtmpUrl$streamKey' : '$rtmpUrl/$streamKey';
  }

  StreamConfig copyWith({
    int? width,
    int? height,
    int? fps,
    int? videoBitrate,
    int? audioBitrate,
    int? sampleRate,
    int? iFrameInterval,
    String? rtmpUrl,
    String? streamKey,
    bool? requiresPremium,
    bool? isExternalRtmp,
    int? maxBitrate,
  }) {
    return StreamConfig(
      width: width ?? this.width,
      height: height ?? this.height,
      fps: fps ?? this.fps,
      videoBitrate: videoBitrate ?? this.videoBitrate,
      audioBitrate: audioBitrate ?? this.audioBitrate,
      sampleRate: sampleRate ?? this.sampleRate,
      iFrameInterval: iFrameInterval ?? this.iFrameInterval,
      rtmpUrl: rtmpUrl ?? this.rtmpUrl,
      streamKey: streamKey ?? this.streamKey,
      requiresPremium: requiresPremium ?? this.requiresPremium,
      isExternalRtmp: isExternalRtmp ?? this.isExternalRtmp,
      maxBitrate: maxBitrate ?? this.maxBitrate,
    );
  }
}
