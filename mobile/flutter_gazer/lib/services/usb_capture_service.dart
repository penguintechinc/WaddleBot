import 'dart:async';
import 'package:flutter/services.dart';

/// USB device connection states.
sealed class UsbDeviceState {
  const UsbDeviceState();
}

class UsbDisconnected extends UsbDeviceState {
  const UsbDisconnected();
}

class UsbDeviceFound extends UsbDeviceState {
  final String deviceName;
  const UsbDeviceFound(this.deviceName);
}

class UsbConnecting extends UsbDeviceState {
  const UsbConnecting();
}

class UsbConnected extends UsbDeviceState {
  final String deviceName;
  const UsbConnected(this.deviceName);
}

class UsbError extends UsbDeviceState {
  final String message;
  const UsbError(this.message);
}

/// Bridge to native USB capture via platform channels.
class UsbCaptureService {
  static const _channel = MethodChannel('io.waddlebot.gazer/usb_capture');
  static const _stateChannel = EventChannel('io.waddlebot.gazer/usb_state');

  final _stateController = StreamController<UsbDeviceState>.broadcast();
  StreamSubscription? _nativeStateSub;
  UsbDeviceState _currentState = const UsbDisconnected();
  int? _textureId;

  Stream<UsbDeviceState> get stateStream => _stateController.stream;
  UsbDeviceState get currentState => _currentState;
  int? get textureId => _textureId;

  UsbCaptureService() {
    _listenNativeState();
  }

  void _listenNativeState() {
    _nativeStateSub =
        _stateChannel.receiveBroadcastStream().map<UsbDeviceState>((event) {
      final map = event as Map;
      switch (map['state'] as String) {
        case 'disconnected':
          return const UsbDisconnected();
        case 'found':
          return UsbDeviceFound(map['deviceName'] as String? ?? 'Unknown');
        case 'connecting':
          return const UsbConnecting();
        case 'connected':
          _textureId = map['textureId'] as int?;
          return UsbConnected(map['deviceName'] as String? ?? 'Unknown');
        case 'error':
          return UsbError(map['message'] as String? ?? 'Unknown error');
        default:
          return const UsbDisconnected();
      }
    }).listen(
      (state) {
        _currentState = state;
        _stateController.add(state);
      },
      onError: (e) {
        _currentState = UsbError(e.toString());
        _stateController.add(_currentState);
      },
    );
  }

  /// Scan for connected USB video devices.
  Future<void> scanForDevices() async {
    try {
      await _channel.invokeMethod('scanForDevices');
    } on PlatformException catch (e) {
      _currentState = UsbError(e.message ?? 'Scan failed');
      _stateController.add(_currentState);
    }
  }

  /// Connect to a USB device by name.
  Future<void> connectDevice(String deviceName) async {
    try {
      _currentState = const UsbConnecting();
      _stateController.add(_currentState);
      await _channel.invokeMethod('connectDevice', {'deviceName': deviceName});
    } on PlatformException catch (e) {
      _currentState = UsbError(e.message ?? 'Connection failed');
      _stateController.add(_currentState);
    }
  }

  /// Disconnect from current USB device.
  Future<void> disconnectDevice() async {
    try {
      await _channel.invokeMethod('disconnectDevice');
    } on PlatformException catch (_) {}
    _textureId = null;
    _currentState = const UsbDisconnected();
    _stateController.add(_currentState);
  }

  /// Start capturing frames at the specified resolution and fps.
  Future<bool> startCapture({
    int width = 1280,
    int height = 720,
    int fps = 30,
  }) async {
    try {
      final result = await _channel.invokeMethod<bool>('startCapture', {
        'width': width,
        'height': height,
        'fps': fps,
      });
      return result ?? false;
    } on PlatformException catch (_) {
      return false;
    }
  }

  /// Stop frame capture.
  Future<void> stopCapture() async {
    try {
      await _channel.invokeMethod('stopCapture');
    } on PlatformException catch (_) {}
  }

  void dispose() {
    _nativeStateSub?.cancel();
    _stateController.close();
  }
}
