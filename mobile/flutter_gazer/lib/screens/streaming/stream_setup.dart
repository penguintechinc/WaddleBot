import 'package:flutter/material.dart';
import 'package:flutter_libs/flutter_libs.dart';
import '../../config/theme.dart';
import '../../models/license_info.dart';
import '../../models/stream_config.dart';
import '../../services/license_service.dart';
import 'quality_presets.dart';

/// RTMP configuration screen for stream setup.
/// Supports Waddles hosted RTMP and premium external RTMP option.
class StreamSetupScreen extends StatefulWidget {
  final StreamConfig initialConfig;
  final LicenseService licenseService;
  final Function(StreamConfig) onConfigUpdate;

  const StreamSetupScreen({
    super.key,
    required this.initialConfig,
    required this.licenseService,
    required this.onConfigUpdate,
  });

  @override
  State<StreamSetupScreen> createState() => _StreamSetupScreenState();
}

class _StreamSetupScreenState extends State<StreamSetupScreen> {
  late final TextEditingController _rtmpUrlController;
  late final TextEditingController _streamKeyController;
  late final TextEditingController _bitrateController;

  late StreamConfig _config;
  bool _showExternalRtmp = false;
  bool _isExternalRtmpUrl = false;

  @override
  void initState() {
    super.initState();
    _config = widget.initialConfig;
    _rtmpUrlController = TextEditingController(text: _config.rtmpUrl);
    _streamKeyController = TextEditingController(text: _config.streamKey);
    _bitrateController = TextEditingController(
      text: (_config.videoBitrate / 1000000).toString(),
    );
  }

  @override
  void dispose() {
    _rtmpUrlController.dispose();
    _streamKeyController.dispose();
    _bitrateController.dispose();
    super.dispose();
  }

  void _updateConfig(StreamConfig newConfig) {
    if (!mounted) return;
    setState(() => _config = newConfig);
    widget.onConfigUpdate(_config);
  }

  /// Validates if the given RTMP URL is a Waddles platform URL.
  /// Waddles URLs: rtmp://rtmp.waddlebot.io/* or rtmps://rtmp.waddlebot.io/*
  /// All other URLs are considered external.
  bool _isWaddleBotRtmpUrl(String url) {
    if (url.isEmpty) return true; // Default to Waddles for empty input
    try {
      final uri = Uri.parse(url);
      final host = uri.host.toLowerCase();
      return host == 'rtmp.waddlebot.io';
    } catch (e) {
      return false; // Invalid URL format
    }
  }

  Future<void> _toggleExternalRtmp() async {
    if (_showExternalRtmp) {
      if (!mounted) return;
      setState(() => _showExternalRtmp = false);
      return;
    }

    // Check premium entitlement for external RTMP
    final license = widget.licenseService.currentLicense;
    final canUseExternal = license?.canStreamExternal() ?? false;

    if (!canUseExternal) {
      if (!mounted) return;
      _showUpgradeDialog(
        'External RTMP Streaming',
        'Upgrade to Pro or Enterprise tier to stream to external RTMP servers.',
      );
      return;
    }

    if (!mounted) return;
    setState(() {
      _showExternalRtmp = true;
      _validateAndUpdateExternalRtmpStatus();
    });
  }

  /// Updates the external RTMP URL validation status.
  void _validateAndUpdateExternalRtmpStatus() {
    final isExternal = !_isWaddleBotRtmpUrl(_rtmpUrlController.text);
    if (!mounted) return;
    setState(() => _isExternalRtmpUrl = isExternal);
  }

  void _showUpgradeDialog(String title, String message) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        backgroundColor: ElderColors.slate800,
        surfaceTintColor: Colors.transparent,
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Later'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              // TODO: Navigate to upgrade flow
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: ElderColors.amber500,
              foregroundColor: ElderColors.slate950,
            ),
            child: const Text('Upgrade'),
          ),
        ],
      ),
    );
  }

  void _applyPreset(
      int width, int height, int fps, int bitrate, bool isPremium) {
    final license = widget.licenseService.currentLicense;
    if (isPremium && license?.tier == LicenseTier.free) {
      _showUpgradeDialog(
        'Premium Quality',
        'This preset requires a Premium or higher tier license.',
      );
      return;
    }

    final maxBitrate = license?.getMaxBitrate() ?? 1500000;
    final actualBitrate = bitrate > maxBitrate ? maxBitrate : bitrate;

    final newConfig = _config.copyWith(
      width: width,
      height: height,
      fps: fps,
      videoBitrate: actualBitrate,
      requiresPremium: isPremium,
    );

    _updateConfig(newConfig);

    if (actualBitrate < bitrate) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Bitrate limited to your tier maximum'),
          backgroundColor: ElderColors.amber600,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final license = widget.licenseService.currentLicense;
    final maxBitrate = license?.getMaxBitrate() ?? 1500000;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Stream Setup'),
        backgroundColor: ElderColors.slate800,
      ),
      backgroundColor: ElderColors.slate950,
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Waddles RTMP Section
              const _SectionTitle(title: 'RTMP Configuration'),
              const SizedBox(height: 12),

              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: ElderColors.slate900,
                  border: Border.all(color: ElderColors.slate700),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Expanded(
                          child: Text(
                            'Waddles RTMP',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                              color: ElderColors.slate100,
                            ),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: GazerTheme.connectedGreen.withOpacity(0.2),
                            border:
                                Border.all(color: GazerTheme.connectedGreen),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            'FREE',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: GazerTheme.connectedGreen,
                            ),
                          ),
                        ),
                        if (_showExternalRtmp && _isExternalRtmpUrl)
                          Padding(
                            padding: const EdgeInsets.only(left: 8),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 4,
                              ),
                              decoration: BoxDecoration(
                                color: ElderColors.amber500.withOpacity(0.2),
                                border: Border.all(color: ElderColors.amber500),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: const Text(
                                'PREMIUM',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.bold,
                                  color: ElderColors.amber500,
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _rtmpUrlController,
                      readOnly: !_showExternalRtmp,
                      decoration: InputDecoration(
                        labelText: 'RTMP URL',
                        hintText: 'rtmp://waddlebot.io/live',
                        border: const OutlineInputBorder(),
                        enabled: _showExternalRtmp,
                        errorText: _showExternalRtmp &&
                                _isExternalRtmpUrl &&
                                !(widget.licenseService.currentLicense
                                        ?.canStreamExternal() ??
                                    false)
                            ? 'External RTMP requires Premium license'
                            : null,
                      ),
                      style: const TextStyle(color: ElderColors.slate100),
                      onChanged: (value) {
                        _updateConfig(_config.copyWith(rtmpUrl: value));
                        _validateAndUpdateExternalRtmpStatus();
                      },
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _streamKeyController,
                      obscureText: true,
                      readOnly: !_showExternalRtmp,
                      decoration: InputDecoration(
                        labelText: 'Stream Key',
                        hintText: 'Your stream key (hidden)',
                        border: const OutlineInputBorder(),
                        suffixIcon: const Icon(Icons.lock_outline),
                        enabled: _showExternalRtmp,
                      ),
                      style: const TextStyle(color: ElderColors.slate100),
                      onChanged: (value) {
                        _updateConfig(_config.copyWith(streamKey: value));
                      },
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // External RTMP Toggle
              ElevatedButton.icon(
                onPressed: _toggleExternalRtmp,
                icon: Icon(
                  _showExternalRtmp
                      ? Icons.keyboard_arrow_up
                      : Icons.keyboard_arrow_down,
                ),
                label: Text(
                  _showExternalRtmp
                      ? 'Hide External RTMP'
                      : 'Use External RTMP',
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: ElderColors.slate700,
                  foregroundColor: Colors.white,
                ),
              ),
              const SizedBox(height: 24),

              // Quality Settings Section
              const _SectionTitle(title: 'Quality Settings'),
              const SizedBox(height: 12),

              QualityPresetsCard(
                currentConfig: _config,
                licenseService: widget.licenseService,
                onPresetSelect: _applyPreset,
                onCustom: () {},
              ),
              const SizedBox(height: 24),

              // Current Configuration Display
              const _SectionTitle(title: 'Current Configuration'),
              const SizedBox(height: 12),

              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: ElderColors.slate900,
                  border: Border.all(color: ElderColors.slate700),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  children: [
                    _ConfigRow(
                      label: 'Resolution',
                      value: '${_config.width}x${_config.height}',
                    ),
                    const Divider(color: ElderColors.slate700, height: 12),
                    _ConfigRow(
                        label: 'Frame Rate', value: '${_config.fps} fps'),
                    const Divider(color: ElderColors.slate700, height: 12),
                    _ConfigRow(
                      label: 'Video Bitrate',
                      value:
                          '${(_config.videoBitrate / 1000000).toStringAsFixed(1)} Mbps',
                      valueColor: _config.videoBitrate > maxBitrate
                          ? ElderColors.red500
                          : null,
                    ),
                    const Divider(color: ElderColors.slate700, height: 12),
                    _ConfigRow(
                      label: 'Audio Bitrate',
                      value:
                          '${(_config.audioBitrate / 1000).toStringAsFixed(0)} Kbps',
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // License Tier Info
              if (license != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: ElderColors.slate900,
                    border: Border.all(color: ElderColors.amber500, width: 1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(
                            Icons.verified,
                            color: ElderColors.amber500,
                            size: 18,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            license.licenseName,
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                              color: ElderColors.amber500,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Max bitrate: ${(maxBitrate / 1000000).toStringAsFixed(1)} Mbps',
                        style: const TextStyle(
                          fontSize: 12,
                          color: ElderColors.slate300,
                        ),
                      ),
                      if (license.canStreamExternal())
                        Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Row(
                            children: [
                              Icon(
                                Icons.check_circle,
                                size: 14,
                                color: GazerTheme.connectedGreen,
                              ),
                              const SizedBox(width: 6),
                              Text(
                                'External RTMP unlocked',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: GazerTheme.connectedGreen,
                                ),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Section title widget.
class _SectionTitle extends StatelessWidget {
  final String title;

  const _SectionTitle({required this.title});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 4,
          height: 20,
          decoration: BoxDecoration(
            color: ElderColors.amber500,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          title,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            color: ElderColors.slate100,
          ),
        ),
      ],
    );
  }
}

/// Configuration row widget.
class _ConfigRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;

  const _ConfigRow({required this.label, required this.value, this.valueColor});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label,
            style: const TextStyle(color: ElderColors.slate400, fontSize: 13)),
        Text(
          value,
          style: TextStyle(
            color: valueColor ?? ElderColors.amber500,
            fontSize: 14,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}
