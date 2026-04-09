import 'package:flutter/material.dart';
import 'package:flutter_libs/flutter_libs.dart';
import '../../config/constants.dart';
import '../../config/theme.dart';
import '../../models/overlay_settings.dart';
import '../../models/stream_config.dart';
import '../../models/stream_state.dart';
import '../../services/license_service.dart';
import '../../services/rtmp_service.dart';
import '../../services/stream_compositor_service.dart';
import '../../services/usb_capture_service.dart';
import '../../widgets/overlay_settings_dialog.dart';

/// Main streaming preview screen with USB capture device preview,
/// camera overlay control, go live/stop button, and stream metrics.
class StreamingPreviewScreen extends StatefulWidget {
  final RtmpService rtmpService;
  final UsbCaptureService usbCaptureService;
  final StreamCompositorService compositorService;
  final LicenseService licenseService;
  final StreamConfig initialConfig;

  const StreamingPreviewScreen({
    super.key,
    required this.rtmpService,
    required this.usbCaptureService,
    required this.compositorService,
    required this.licenseService,
    required this.initialConfig,
  });

  @override
  State<StreamingPreviewScreen> createState() => _StreamingPreviewScreenState();
}

class _StreamingPreviewScreenState extends State<StreamingPreviewScreen> {
  late StreamConfig _config;
  StreamState _state = const StreamDisconnected();
  OverlaySettings _overlaySettings = const OverlaySettings(enabled: false);

  Map<String, dynamic> _streamStats = {
    'bitrate': 0,
    'fps': 0,
    'viewerCount': 0,
    'droppedFrames': 0,
  };

  @override
  void initState() {
    super.initState();
    _config = widget.initialConfig;

    // Listen to stream state changes
    widget.rtmpService.stateStream.listen((state) {
      if (mounted) {
        setState(() => _state = state);
      }
    });

    // Periodically update stream stats
    _startStatsPolling();
  }

  void _startStatsPolling() {
    Future.delayed(const Duration(seconds: 1), () async {
      if (!mounted) return;

      if (widget.rtmpService.isStreaming) {
        final stats = await widget.rtmpService.getStreamStats();
        if (mounted) {
          setState(() {
            _streamStats = {
              'bitrate': stats['bitrate'] ?? 0,
              'fps': stats['fps'] ?? 0,
              'viewerCount': stats['viewer_count'] ?? 0,
              'droppedFrames': stats['dropped_frames'] ?? 0,
            };
          });
        }
      }
      _startStatsPolling();
    });
  }

  Future<void> _startStreaming() async {
    final canStream = await widget.licenseService.checkFeatureEntitlement(
      AppConstants.featureUsbCapture,
    );

    if (!canStream) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('USB capture not available in your tier'),
            backgroundColor: ElderColors.red500,
          ),
        );
      }
      return;
    }

    final success = await widget.rtmpService.startStreaming(_config);
    if (!success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Failed to start streaming'),
          backgroundColor: ElderColors.red500,
        ),
      );
    }
  }

  Future<void> _stopStreaming() async {
    await widget.rtmpService.stopStreaming();
  }

  Future<void> _toggleOverlay() async {
    final result = await OverlaySettingsDialog.show(context, _overlaySettings);
    if (result != null && mounted) {
      setState(() => _overlaySettings = result);
      widget.compositorService.updateOverlaySettings(_overlaySettings);
    }
  }

  String _formatBitrate(int bits) {
    if (bits < 1000000) {
      return '${(bits / 1000).toStringAsFixed(0)} Kbps';
    }
    return '${(bits / 1000000).toStringAsFixed(1)} Mbps';
  }

  String _getStreamStatusText() {
    if (_state is StreamStreaming) return 'LIVE';
    if (_state is StreamConnecting) return 'CONNECTING...';
    if (_state is StreamConnected) return 'CONNECTED';
    if (_state is StreamError) return 'ERROR';
    return 'STOPPED';
  }

  Color _getStreamStatusColor() {
    if (_state is StreamStreaming) return GazerTheme.streamingRed;
    if (_state is StreamConnecting) return GazerTheme.warningAmber;
    if (_state is StreamConnected) return GazerTheme.connectedGreen;
    if (_state is StreamError) return ElderColors.red500;
    return ElderColors.slate500;
  }

  @override
  Widget build(BuildContext context) {
    final isStreaming = _state is StreamStreaming;
    final isConnecting = _state is StreamConnecting;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Stream Preview'),
        backgroundColor: ElderColors.slate800,
      ),
      backgroundColor: ElderColors.slate950,
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Preview Container
              Container(
                decoration: BoxDecoration(
                  border: Border.all(color: ElderColors.slate700, width: 2),
                  borderRadius: BorderRadius.circular(12),
                  color: ElderColors.slate900,
                ),
                child: AspectRatio(
                  aspectRatio: 16 / 9,
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      // USB Capture Preview
                      Container(
                        color: ElderColors.slate950,
                        child: Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(
                                Icons.devices,
                                size: 64,
                                color: ElderColors.slate700,
                              ),
                              const SizedBox(height: 16),
                              Text(
                                'USB Capture Device\n${_config.width}x${_config.height} @ ${_config.fps}fps',
                                textAlign: TextAlign.center,
                                style: const TextStyle(
                                  color: ElderColors.slate400,
                                  fontSize: 14,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),

                      // Overlay Settings Indicator
                      if (_overlaySettings.enabled)
                        Positioned(
                          right: 12,
                          bottom: 12,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: ElderColors.amber500.withValues(alpha: 0.9),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: const Text(
                              'Overlay ON',
                              style: TextStyle(
                                color: ElderColors.slate950,
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ),

                      // Live Badge
                      if (isStreaming)
                        Positioned(
                          top: 12,
                          left: 12,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 6,
                            ),
                            decoration: BoxDecoration(
                              color: GazerTheme.streamingRed,
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: const Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Icons.fiber_manual_record,
                                  size: 12,
                                  color: Colors.white,
                                ),
                                SizedBox(width: 6),
                                Text(
                                  'LIVE',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // Stream Status Display
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: ElderColors.slate900,
                  border: Border.all(color: _getStreamStatusColor(), width: 2),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 12,
                      height: 12,
                      decoration: BoxDecoration(
                        color: _getStreamStatusColor(),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _getStreamStatusText(),
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: _getStreamStatusColor(),
                            ),
                          ),
                          if (_state is StreamError)
                            Text(
                              (_state as StreamError).message,
                              style: const TextStyle(
                                fontSize: 12,
                                color: ElderColors.slate400,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Stream Metrics
              if (isStreaming)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: ElderColors.slate900,
                    border: Border.all(color: ElderColors.slate700),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    children: [
                      _MetricRow(
                        label: 'Bitrate',
                        value: _formatBitrate(_streamStats['bitrate'] as int),
                      ),
                      const Divider(color: ElderColors.slate700, height: 12),
                      _MetricRow(label: 'FPS', value: '${_streamStats['fps']}'),
                      const Divider(color: ElderColors.slate700, height: 12),
                      _MetricRow(
                        label: 'Viewers',
                        value: '${_streamStats['viewerCount']}',
                      ),
                      const Divider(color: ElderColors.slate700, height: 12),
                      _MetricRow(
                        label: 'Dropped Frames',
                        value: '${_streamStats['droppedFrames']}',
                        valueColor: (_streamStats['droppedFrames'] as int) > 0
                            ? ElderColors.red500
                            : ElderColors.green500,
                      ),
                    ],
                  ),
                ),
              const SizedBox(height: 24),

              // Control Buttons
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed:
                          _overlaySettings.enabled ? _toggleOverlay : null,
                      icon: const Icon(Icons.settings),
                      label: const Text('Overlay'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: ElderColors.slate700,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: _toggleOverlay,
                      icon: Icon(
                        _overlaySettings.enabled
                            ? Icons.visibility_off
                            : Icons.visibility,
                      ),
                      label: Text(_overlaySettings.enabled ? 'Hide' : 'Show'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: ElderColors.amber600,
                        foregroundColor: ElderColors.slate950,
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Main Stream Control Button
              ElevatedButton.icon(
                onPressed: isConnecting
                    ? null
                    : (isStreaming ? _stopStreaming : _startStreaming),
                icon: Icon(
                    isStreaming ? Icons.stop_circle : Icons.play_circle_fill),
                label: Text(isStreaming ? 'Stop Streaming' : 'Go Live'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: isStreaming
                      ? GazerTheme.streamingRed
                      : GazerTheme.connectedGreen,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  disabledBackgroundColor: ElderColors.slate700,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Metric row widget for displaying stream statistics.
class _MetricRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;

  const _MetricRow({required this.label, required this.value, this.valueColor});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label,
            style: const TextStyle(color: ElderColors.slate300, fontSize: 14)),
        Text(
          value,
          style: TextStyle(
            color: valueColor ?? ElderColors.amber500,
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}
