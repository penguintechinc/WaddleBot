import 'package:flutter/material.dart';
import '../config/constants.dart';
import '../models/stream_config.dart';
import '../services/license_service.dart';
import '../services/settings_service.dart';

/// Settings screen for RTMP URL, stream key, resolution, bitrate, FPS.
class SettingsScreen extends StatefulWidget {
  final StreamConfig currentConfig;
  final LicenseService licenseService;
  final SettingsService settingsService;

  const SettingsScreen({
    super.key,
    required this.currentConfig,
    required this.licenseService,
    required this.settingsService,
  });

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _rtmpUrlController;
  late final TextEditingController _streamKeyController;
  int _resolutionIndex = 3;
  int _bitrateIndex = 1;
  int _fpsIndex = 2;

  @override
  void initState() {
    super.initState();
    _rtmpUrlController =
        TextEditingController(text: widget.currentConfig.rtmpUrl);
    _streamKeyController =
        TextEditingController(text: widget.currentConfig.streamKey);
    _loadIndices();
  }

  Future<void> _loadIndices() async {
    // Find matching indices from the config values
    for (int i = 0; i < SettingsService.resolutions.length; i++) {
      final res = SettingsService.resolutions[i].value;
      if (res[0] == widget.currentConfig.width &&
          res[1] == widget.currentConfig.height) {
        _resolutionIndex = i;
        break;
      }
    }
    for (int i = 0; i < SettingsService.bitrates.length; i++) {
      if (SettingsService.bitrates[i].value ==
          widget.currentConfig.videoBitrate) {
        _bitrateIndex = i;
        break;
      }
    }
    for (int i = 0; i < SettingsService.fpsOptions.length; i++) {
      if (SettingsService.fpsOptions[i].value == widget.currentConfig.fps) {
        _fpsIndex = i;
        break;
      }
    }
    if (!mounted) return;
    setState(() {});
  }

  Future<void> _save() async {
    await widget.settingsService.saveStreamConfig(
      rtmpUrl: _rtmpUrlController.text.trim(),
      streamKey: _streamKeyController.text.trim(),
      resolutionIndex: _resolutionIndex,
      bitrateIndex: _bitrateIndex,
      fpsIndex: _fpsIndex,
    );

    final res = SettingsService.resolutions[_resolutionIndex].value;
    final br = SettingsService.bitrates[_bitrateIndex].value;
    final fps = SettingsService.fpsOptions[_fpsIndex].value;

    // Check 1080p license gating
    if (_resolutionIndex == 4 &&
        !widget.licenseService
            .isFeatureAvailable(AppConstants.featureHdStreaming)) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('1080p requires Professional license. Using 720p.')));
      final fallback = SettingsService.resolutions[3].value;
      if (!mounted) return;
      Navigator.pop(
        context,
        StreamConfig(
          width: fallback[0],
          height: fallback[1],
          fps: fps,
          videoBitrate: br,
          rtmpUrl: _rtmpUrlController.text.trim(),
          streamKey: _streamKeyController.text.trim(),
        ),
      );
      return;
    }

    if (!mounted) return;
    Navigator.pop(
      context,
      StreamConfig(
        width: res[0],
        height: res[1],
        fps: fps,
        videoBitrate: br,
        rtmpUrl: _rtmpUrlController.text.trim(),
        streamKey: _streamKeyController.text.trim(),
      ),
    );
  }

  @override
  void dispose() {
    _rtmpUrlController.dispose();
    _streamKeyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Stream Settings'),
        actions: [
          TextButton(onPressed: _save, child: const Text('Save')),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // RTMP URL
          TextField(
            controller: _rtmpUrlController,
            decoration: const InputDecoration(
              labelText: 'RTMP URL',
              hintText: 'rtmp://live.example.com/app',
              border: OutlineInputBorder(),
            ),
            keyboardType: TextInputType.url,
          ),
          const SizedBox(height: 16),

          // Stream Key
          TextField(
            controller: _streamKeyController,
            decoration: const InputDecoration(
              labelText: 'Stream Key',
              border: OutlineInputBorder(),
            ),
            obscureText: true,
          ),
          const SizedBox(height: 24),

          // Resolution
          _buildDropdown(
            label: 'Resolution',
            value: _resolutionIndex,
            items: SettingsService.resolutions
                .asMap()
                .entries
                .map((e) => DropdownMenuItem(
                      value: e.key,
                      child: Text(e.value.key),
                    ))
                .toList(),
            onChanged: (v) => setState(() => _resolutionIndex = v ?? 3),
          ),
          const SizedBox(height: 16),

          // Bitrate
          _buildDropdown(
            label: 'Bitrate',
            value: _bitrateIndex,
            items: SettingsService.bitrates
                .asMap()
                .entries
                .map((e) => DropdownMenuItem(
                      value: e.key,
                      child: Text(e.value.key),
                    ))
                .toList(),
            onChanged: (v) => setState(() => _bitrateIndex = v ?? 1),
          ),
          const SizedBox(height: 16),

          // FPS
          _buildDropdown(
            label: 'Frame Rate',
            value: _fpsIndex,
            items: SettingsService.fpsOptions
                .asMap()
                .entries
                .map((e) => DropdownMenuItem(
                      value: e.key,
                      child: Text(e.value.key),
                    ))
                .toList(),
            onChanged: (v) => setState(() => _fpsIndex = v ?? 2),
          ),
          const SizedBox(height: 24),

          // Waddles section (license-gated)
          _buildWaddleBotSection(),

          const SizedBox(height: 24),

          // License info
          Card(
            child: ListTile(
              leading: Icon(
                widget.licenseService.isValid
                    ? Icons.verified
                    : Icons.warning,
                color: widget.licenseService.isValid
                    ? Colors.green
                    : Colors.orange,
              ),
              title: Text(widget.licenseService.currentLicense?.licenseName ??
                  'No License'),
              subtitle: Text(widget.licenseService.isValid
                  ? 'All features available'
                  : 'Some features may be restricted'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDropdown({
    required String label,
    required int value,
    required List<DropdownMenuItem<int>> items,
    required ValueChanged<int?> onChanged,
  }) {
    return InputDecorator(
      decoration: InputDecoration(
        labelText: label,
        border: const OutlineInputBorder(),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<int>(
          value: value,
          isExpanded: true,
          items: items,
          onChanged: onChanged,
        ),
      ),
    );
  }

  Widget _buildWaddleBotSection() {
    final licensed = widget.licenseService
        .isFeatureAvailable(AppConstants.featureWaddleBotAi);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.smart_toy),
                const SizedBox(width: 8),
                const Text('Waddles Integration',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                const Spacer(),
                if (!licensed)
                  const Chip(label: Text('Pro', style: TextStyle(fontSize: 11))),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              licensed
                  ? 'Chat overlay and stream events are available.'
                  : 'Professional license required for Waddles features.',
              style: TextStyle(
                color: licensed ? null : Theme.of(context).disabledColor,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
