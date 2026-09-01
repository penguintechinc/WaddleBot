import 'dart:async';
import '../models/overlay_settings.dart';

/// Manages stream composition state. Actual pixel-level composition is
/// handled by native platform code; this service tracks overlay and
/// fallback state for the Flutter UI layer.
class StreamCompositorService {
  int outputWidth;
  int outputHeight;
  bool _isCompositing = false;
  bool _isInFallbackMode = false;
  String _fallbackMessage = 'Capture Card Disconnected';

  OverlaySettings _overlaySettings;

  final _fallbackController = StreamController<bool>.broadcast();
  Stream<bool> get fallbackStream => _fallbackController.stream;

  bool get isCompositing => _isCompositing;
  bool get isInFallbackMode => _isInFallbackMode;
  String get fallbackMessage => _fallbackMessage;
  OverlaySettings get overlaySettings => _overlaySettings;

  StreamCompositorService({
    this.outputWidth = 1280,
    this.outputHeight = 720,
    OverlaySettings? overlaySettings,
  }) : _overlaySettings = overlaySettings ?? const OverlaySettings();

  void initialize(int width, int height) {
    outputWidth = width;
    outputHeight = height;
  }

  void startCompositing() {
    _isCompositing = true;
    _isInFallbackMode = false;
  }

  void stopCompositing() {
    _isCompositing = false;
  }

  void enableFallbackMode([String message = 'Capture Card Disconnected']) {
    _isInFallbackMode = true;
    _fallbackMessage = message;
    _fallbackController.add(true);
  }

  void disableFallbackMode() {
    _isInFallbackMode = false;
    _fallbackController.add(false);
  }

  void updateOverlaySettings(OverlaySettings settings) {
    _overlaySettings = settings;
  }

  void dispose() {
    _fallbackController.close();
  }
}
