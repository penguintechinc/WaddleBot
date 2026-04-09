import 'dart:async';
import 'package:flutter/services.dart';
import '../models/stream_config.dart';
import '../models/stream_state.dart';

/// RTMP streaming service — delegates to native platform channels.
class RtmpService {
  static const _channel = MethodChannel('io.waddlebot.gazer/rtmp');
  static const _stateChannel = EventChannel('io.waddlebot.gazer/rtmp_state');

  final _stateController = StreamController<StreamState>.broadcast();
  StreamSubscription? _nativeStateSub;
  StreamState _currentState = const StreamDisconnected();

  Stream<StreamState> get stateStream => _stateController.stream;
  StreamState get currentState => _currentState;
  bool get isStreaming => _currentState is StreamStreaming;

  RtmpService() {
    _listenNativeState();
  }

  void _listenNativeState() {
    _nativeStateSub =
        _stateChannel.receiveBroadcastStream().map<StreamState>((event) {
      final map = event as Map;
      switch (map['state'] as String) {
        case 'disconnected':
          return const StreamDisconnected();
        case 'connecting':
          return const StreamConnecting();
        case 'connected':
          return StreamConnected(map['url'] as String? ?? '');
        case 'streaming':
          return const StreamStreaming();
        case 'error':
          return StreamError(map['message'] as String? ?? 'Unknown error');
        default:
          return const StreamDisconnected();
      }
    }).listen(
      (state) {
        _currentState = state;
        _stateController.add(state);
      },
      onError: (e) {
        _currentState = StreamError(e.toString());
        _stateController.add(_currentState);
      },
    );
  }

  /// Start RTMP streaming with the given configuration.
  Future<bool> startStreaming(StreamConfig config) async {
    try {
      _currentState = const StreamConnecting();
      _stateController.add(_currentState);

      final result = await _channel.invokeMethod<bool>('startStreaming', {
        'url': config.fullUrl,
        'width': config.width,
        'height': config.height,
        'fps': config.fps,
        'videoBitrate': config.videoBitrate,
        'audioBitrate': config.audioBitrate,
        'sampleRate': config.sampleRate,
      });
      return result ?? false;
    } on PlatformException catch (e) {
      _currentState = StreamError(e.message ?? 'Platform error');
      _stateController.add(_currentState);
      return false;
    }
  }

  /// Stop RTMP streaming.
  Future<void> stopStreaming() async {
    try {
      await _channel.invokeMethod('stopStreaming');
    } on PlatformException catch (_) {
      // Ignore — stopping is best-effort
    }
    _currentState = const StreamDisconnected();
    _stateController.add(_currentState);
  }

  /// Update bitrate during an active stream.
  Future<void> updateBitrate(int bitrate) async {
    try {
      await _channel.invokeMethod('updateBitrate', {'bitrate': bitrate});
    } on PlatformException catch (_) {}
  }

  /// Get current stream statistics from native layer.
  Future<Map<String, dynamic>> getStreamStats() async {
    try {
      final result = await _channel.invokeMethod<Map>('getStreamStats');
      return Map<String, dynamic>.from(result ?? {});
    } on PlatformException catch (_) {
      return {};
    }
  }

  void dispose() {
    _nativeStateSub?.cancel();
    _stateController.close();
  }
}
