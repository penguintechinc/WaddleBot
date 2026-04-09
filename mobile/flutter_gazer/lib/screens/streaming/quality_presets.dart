import 'package:flutter/material.dart';
import 'package:flutter_libs/flutter_libs.dart';
import '../../models/license_info.dart';
import '../../models/stream_config.dart';
import '../../services/license_service.dart';

/// Quality preset cards with premium gating and custom quality option.
class QualityPresetsCard extends StatefulWidget {
  final StreamConfig currentConfig;
  final LicenseService licenseService;
  final Function(int, int, int, int, bool) onPresetSelect;
  final Function() onCustom;

  const QualityPresetsCard({
    super.key,
    required this.currentConfig,
    required this.licenseService,
    required this.onPresetSelect,
    required this.onCustom,
  });

  @override
  State<QualityPresetsCard> createState() => _QualityPresetsCardState();
}

class _QualityPresetsCardState extends State<QualityPresetsCard> {
  late int _selectedPresetIndex;

  @override
  void initState() {
    super.initState();
    _selectedPresetIndex = _getSelectedPresetIndex();
  }

  int _getSelectedPresetIndex() {
    final config = widget.currentConfig;
    if (config.width == 854 && config.height == 480) return 0; // Low
    if (config.width == 1280 && config.height == 720 && config.fps == 30) {
      return 1; // Medium
    }
    if (config.width == 1920 && config.height == 1080 && config.fps == 30) {
      return 2; // High
    }
    if (config.width == 1920 && config.height == 1080 && config.fps == 60) {
      return 3; // Ultra
    }
    return -1;
  }

  @override
  Widget build(BuildContext context) {
    final license = widget.licenseService.currentLicense;
    final presets = _buildPresets(license);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Preset Grid
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            childAspectRatio: 1.0,
          ),
          itemCount: presets.length,
          itemBuilder: (context, index) {
            final preset = presets[index];
            return _PresetCard(
              preset: preset,
              isSelected: _selectedPresetIndex == index,
              onTap: () {
                setState(() => _selectedPresetIndex = index);
                widget.onPresetSelect(
                  preset.width,
                  preset.height,
                  preset.fps,
                  preset.bitrate,
                  preset.isPremium,
                );
              },
            );
          },
        ),
        const SizedBox(height: 16),

        // Custom Quality Button
        SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: () => _showCustomQualityDialog(context, license),
            icon: const Icon(Icons.tune),
            label: const Text('Custom Quality'),
            style: ElevatedButton.styleFrom(
              backgroundColor: ElderColors.slate700,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 12),
            ),
          ),
        ),
      ],
    );
  }

  List<_QualityPreset> _buildPresets(LicenseInfo? license) {
    return [
      const _QualityPreset(
        name: 'Low',
        resolution: '480p',
        fps: 30,
        bitrate: 1500000,
        width: 854,
        height: 480,
        isPremium: false,
        description: '1.5 Mbps',
      ),
      const _QualityPreset(
        name: 'Medium',
        resolution: '720p',
        fps: 30,
        bitrate: 3000000,
        width: 1280,
        height: 720,
        isPremium: false,
        description: '3 Mbps',
      ),
      const _QualityPreset(
        name: 'High',
        resolution: '1080p',
        fps: 30,
        bitrate: 5000000,
        width: 1920,
        height: 1080,
        isPremium: true,
        description: '5 Mbps',
      ),
      const _QualityPreset(
        name: 'Ultra',
        resolution: '1080p',
        fps: 60,
        bitrate: 8000000,
        width: 1920,
        height: 1080,
        isPremium: true,
        description: '8 Mbps @ 60fps',
      ),
    ];
  }

  void _showCustomQualityDialog(BuildContext context, LicenseInfo? license) {
    final widthController = TextEditingController(
      text: widget.currentConfig.width.toString(),
    );
    final heightController = TextEditingController(
      text: widget.currentConfig.height.toString(),
    );
    final fpsController = TextEditingController(
      text: widget.currentConfig.fps.toString(),
    );
    final bitrateController = TextEditingController(
      text: (widget.currentConfig.videoBitrate / 1000000).toStringAsFixed(1),
    );

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Custom Quality Settings'),
        backgroundColor: ElderColors.slate800,
        surfaceTintColor: Colors.transparent,
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: widthController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Width (px)',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: heightController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Height (px)',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: fpsController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Frame Rate (fps)',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: bitrateController,
                keyboardType: TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                  labelText: 'Bitrate (Mbps)',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              if (license != null)
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: ElderColors.slate700,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    'Max: ${(license.getMaxBitrate() / 1000000).toStringAsFixed(1)} Mbps',
                    style: const TextStyle(
                        fontSize: 12, color: ElderColors.amber500),
                  ),
                ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              try {
                final width = int.parse(widthController.text);
                final height = int.parse(heightController.text);
                final fps = int.parse(fpsController.text);
                final bitrate =
                    (double.parse(bitrateController.text) * 1000000).toInt();

                widget.onPresetSelect(width, height, fps, bitrate, false);
                if (!mounted) return;
                setState(() => _selectedPresetIndex = -1);
                Navigator.pop(context);
              } catch (e) {
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Invalid values'),
                    backgroundColor: ElderColors.red500,
                  ),
                );
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: ElderColors.amber500,
              foregroundColor: ElderColors.slate950,
            ),
            child: const Text('Apply'),
          ),
        ],
      ),
    );

    widthController.dispose();
    heightController.dispose();
    fpsController.dispose();
    bitrateController.dispose();
  }
}

/// Individual preset card widget.
class _PresetCard extends StatelessWidget {
  final _QualityPreset preset;
  final bool isSelected;
  final VoidCallback onTap;

  const _PresetCard({
    required this.preset,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: isSelected ? ElderColors.slate800 : ElderColors.slate900,
          border: Border.all(
            color: isSelected ? ElderColors.amber500 : ElderColors.slate700,
            width: isSelected ? 2 : 1,
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Stack(
          fit: StackFit.expand,
          children: [
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              preset.name,
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                                color: isSelected
                                    ? ElderColors.amber500
                                    : ElderColors.slate100,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              preset.resolution,
                              style: TextStyle(
                                fontSize: 12,
                                color: isSelected
                                    ? ElderColors.amber400
                                    : ElderColors.slate400,
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (preset.isPremium)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: ElderColors.amber500.withOpacity(0.2),
                            border: Border.all(color: ElderColors.amber500),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.star,
                                  size: 10, color: ElderColors.amber500),
                              SizedBox(width: 2),
                              Text(
                                'PRO',
                                style: TextStyle(
                                  fontSize: 9,
                                  fontWeight: FontWeight.bold,
                                  color: ElderColors.amber500,
                                ),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),

                  // Details
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _DetailRow(
                        icon: Icons.videocam,
                        label: '${preset.fps}fps',
                        isSelected: isSelected,
                      ),
                      const SizedBox(height: 4),
                      _DetailRow(
                        icon: Icons.speed,
                        label: preset.description,
                        isSelected: isSelected,
                      ),
                    ],
                  ),

                  // Selection indicator
                  if (isSelected)
                    Row(
                      children: [
                        Container(
                          width: 6,
                          height: 6,
                          decoration: const BoxDecoration(
                            color: ElderColors.amber500,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 4),
                        const Text(
                          'Selected',
                          style: TextStyle(
                            fontSize: 10,
                            color: ElderColors.amber500,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Detail row widget for preset card.
class _DetailRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isSelected;

  const _DetailRow(
      {required this.icon, required this.label, required this.isSelected});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          icon,
          size: 12,
          color: isSelected ? ElderColors.amber400 : ElderColors.slate500,
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 11,
            color: isSelected ? ElderColors.amber400 : ElderColors.slate400,
          ),
        ),
      ],
    );
  }
}

/// Quality preset data model.
class _QualityPreset {
  final String name;
  final String resolution;
  final int fps;
  final int bitrate;
  final int width;
  final int height;
  final bool isPremium;
  final String description;

  const _QualityPreset({
    required this.name,
    required this.resolution,
    required this.fps,
    required this.bitrate,
    required this.width,
    required this.height,
    required this.isPremium,
    required this.description,
  });
}
