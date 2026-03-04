import 'package:flutter/material.dart';
import '../models/overlay_settings.dart';

/// Dialog for configuring camera overlay size and position.
class OverlaySettingsDialog extends StatefulWidget {
  final OverlaySettings current;

  const OverlaySettingsDialog({super.key, required this.current});

  static Future<OverlaySettings?> show(
      BuildContext context, OverlaySettings current) {
    return showDialog<OverlaySettings>(
      context: context,
      builder: (_) => OverlaySettingsDialog(current: current),
    );
  }

  @override
  State<OverlaySettingsDialog> createState() => _OverlaySettingsDialogState();
}

class _OverlaySettingsDialogState extends State<OverlaySettingsDialog> {
  late bool _enabled;
  late OverlaySize _size;
  late OverlayCorner _position;

  @override
  void initState() {
    super.initState();
    _enabled = widget.current.enabled;
    _size = widget.current.size;
    _position = widget.current.position;
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Overlay Settings'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SwitchListTile(
            title: const Text('Camera Overlay'),
            value: _enabled,
            onChanged: (v) => setState(() => _enabled = v),
            contentPadding: EdgeInsets.zero,
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<OverlaySize>(
            initialValue: _size,
            decoration: const InputDecoration(
              labelText: 'Size',
              border: OutlineInputBorder(),
            ),
            items: const [
              DropdownMenuItem(value: OverlaySize.small, child: Text('Small')),
              DropdownMenuItem(
                  value: OverlaySize.medium, child: Text('Medium')),
              DropdownMenuItem(value: OverlaySize.large, child: Text('Large')),
            ],
            onChanged: (v) => setState(() => _size = v ?? OverlaySize.medium),
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<OverlayCorner>(
            initialValue: _position,
            decoration: const InputDecoration(
              labelText: 'Position',
              border: OutlineInputBorder(),
            ),
            items: const [
              DropdownMenuItem(
                  value: OverlayCorner.topLeft, child: Text('Top Left')),
              DropdownMenuItem(
                  value: OverlayCorner.topRight, child: Text('Top Right')),
              DropdownMenuItem(
                  value: OverlayCorner.bottomLeft, child: Text('Bottom Left')),
              DropdownMenuItem(
                  value: OverlayCorner.bottomRight,
                  child: Text('Bottom Right')),
            ],
            onChanged: (v) =>
                setState(() => _position = v ?? OverlayCorner.topLeft),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(
            context,
            OverlaySettings(
                enabled: _enabled, size: _size, position: _position),
          ),
          child: const Text('Apply'),
        ),
      ],
    );
  }
}
