import 'package:flutter/material.dart';

/// Compact card showing USB device status with a scan button.
class UsbStatusCard extends StatelessWidget {
  final String statusText;
  final Color statusColor;
  final VoidCallback onScanPressed;

  const UsbStatusCard({
    super.key,
    required this.statusText,
    required this.statusColor,
    required this.onScanPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        children: [
          Icon(Icons.usb, color: statusColor, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              statusText,
              style: TextStyle(color: statusColor, fontSize: 13),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          TextButton.icon(
            onPressed: onScanPressed,
            icon: const Icon(Icons.search, size: 18),
            label: const Text('Scan'),
            style: TextButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
          ),
        ],
      ),
    );
  }
}
