import 'dart:async';
import 'package:dio/dio.dart';
import '../config/constants.dart';
import '../models/stream_config.dart';
import '../models/waddlebot_models.dart';
import 'waddlebot_auth_service.dart';

/// Waddles event and metrics reporting service.
class WaddleBotService {
  final WaddleBotAuthService _authService;
  final Dio _dio;
  Timer? _metricsTimer;
  String? _activeStreamId;
  DateTime? _streamStartTime;

  WaddleBotService({WaddleBotAuthService? authService, Dio? dio})
      : _authService = authService ?? WaddleBotAuthService(),
        _dio = dio ??
            Dio(BaseOptions(
              baseUrl: AppConstants.waddleBotApiUrl,
              connectTimeout: const Duration(seconds: 10),
              receiveTimeout: const Duration(seconds: 15),
            ));

  /// Report that a stream has started.
  Future<void> reportStreamStarted(StreamConfig config) async {
    _activeStreamId =
        'gazer-${DateTime.now().millisecondsSinceEpoch}';
    _streamStartTime = DateTime.now();

    final event = StreamEvent(
      type: StreamEventType.started,
      streamId: _activeStreamId!,
      timestamp: DateTime.now(),
      metadata: {
        'width': config.width,
        'height': config.height,
        'fps': config.fps,
        'bitrate': config.videoBitrate,
      },
    );
    await _postEvent(event);
    _startMetricsReporting();
  }

  /// Report that a stream has stopped.
  Future<void> reportStreamStopped() async {
    _metricsTimer?.cancel();
    if (_activeStreamId == null) return;

    final event = StreamEvent(
      type: StreamEventType.stopped,
      streamId: _activeStreamId!,
      timestamp: DateTime.now(),
    );
    await _postEvent(event);
    _activeStreamId = null;
    _streamStartTime = null;
  }

  /// Report a stream error.
  Future<void> reportStreamError(String message) async {
    if (_activeStreamId == null) return;

    final event = StreamEvent(
      type: StreamEventType.error,
      streamId: _activeStreamId!,
      timestamp: DateTime.now(),
      metadata: {'error': message},
    );
    await _postEvent(event);
  }

  void _startMetricsReporting() {
    _metricsTimer?.cancel();
    _metricsTimer = Timer.periodic(
      const Duration(seconds: AppConstants.waddleBotMetricsIntervalSec),
      (_) => _reportMetrics(),
    );
  }

  Future<void> _reportMetrics() async {
    if (_activeStreamId == null) return;

    final metrics = StreamMetrics(
      streamId: _activeStreamId!,
      uptime: _streamStartTime != null
          ? DateTime.now().difference(_streamStartTime!)
          : Duration.zero,
    );

    try {
      await _dio.post(
        '/router/responses',
        data: metrics.toJson(),
        options: _authOptions(),
      );
    } catch (_) {}
  }

  Future<void> _postEvent(StreamEvent event) async {
    try {
      await _dio.post(
        '/router/events',
        data: event.toJson(),
        options: _authOptions(),
      );
    } catch (_) {
      // Best-effort — don't block streaming on Waddles errors
    }
  }

  Options _authOptions() {
    final headers = <String, dynamic>{
      'Content-Type': 'application/json',
    };
    if (_authService.accessToken != null) {
      headers['Authorization'] = 'Bearer ${_authService.accessToken}';
    }
    return Options(headers: headers);
  }

  void dispose() {
    _metricsTimer?.cancel();
  }
}
