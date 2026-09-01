import 'package:flutter/material.dart';
import '../models/license_info.dart';
import 'package:intl/intl.dart';

/// License status display widget.
///
/// Compact widget showing current license tier with color coding,
/// expiration date, feature count, and usage counters.
/// Expandable to show full license details.
/// Uses Elder theme styling with gold accents.
class LicenseStatusWidget extends StatefulWidget {
  /// Current license information.
  final LicenseInfo licenseInfo;

  /// Current active workflows (for usage counter).
  final int? currentWorkflows;

  /// Callback when widget is tapped to expand.
  final VoidCallback? onExpand;

  /// Whether to show expiration date.
  final bool showExpiration;

  /// Compact display mode (no expand button).
  final bool compact;

  /// Custom background color.
  final Color? backgroundColor;

  /// Custom text color for tier name.
  final Color? tierTextColor;

  const LicenseStatusWidget({
    super.key,
    required this.licenseInfo,
    this.currentWorkflows,
    this.onExpand,
    this.showExpiration = true,
    this.compact = false,
    this.backgroundColor,
    this.tierTextColor,
  });

  @override
  State<LicenseStatusWidget> createState() => _LicenseStatusWidgetState();
}

class _LicenseStatusWidgetState extends State<LicenseStatusWidget> {
  bool _isExpanded = false;

  String _getTierDisplayName(LicenseTier tier) {
    switch (tier) {
      case LicenseTier.free:
        return 'Free';
      case LicenseTier.premium:
        return 'Premium';
      case LicenseTier.pro:
        return 'Pro';
      case LicenseTier.enterprise:
        return 'Enterprise';
    }
  }

  Color _getTierColor(LicenseTier tier) {
    switch (tier) {
      case LicenseTier.free:
        return Colors.grey;
      case LicenseTier.premium:
        return Colors.blue;
      case LicenseTier.pro:
        return const Color(0xFFD4AF37);
      case LicenseTier.enterprise:
        return Colors.purple;
    }
  }

  String _formatExpirationDate(int milliseconds) {
    try {
      final date = DateTime.fromMillisecondsSinceEpoch(milliseconds);
      return DateFormat('MMM d, yyyy').format(date);
    } catch (e) {
      return 'N/A';
    }
  }

  void _toggleExpand() {
    setState(() => _isExpanded = !_isExpanded);
    widget.onExpand?.call();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.compact) {
      return _buildCompactDisplay();
    }
    return _buildExpandableDisplay();
  }

  /// Build compact display (single row).
  Widget _buildCompactDisplay() {
    final tierName = _getTierDisplayName(widget.licenseInfo.tier);
    final tierColor = _getTierColor(widget.licenseInfo.tier);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: widget.backgroundColor ?? Colors.grey[900],
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: Colors.grey[800]!,
          width: 0.5,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: widget.licenseInfo.isValid ? tierColor : Colors.red,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          const SizedBox(width: 8),
          Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'License',
                style: TextStyle(
                  fontSize: 10,
                  color: Colors.grey[500],
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.2,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                tierName,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: widget.tierTextColor ?? tierColor,
                ),
              ),
            ],
          ),
          if (widget.licenseInfo.isExpired)
            Padding(
              padding: const EdgeInsets.only(left: 8),
              child: Icon(
                Icons.warning_rounded,
                size: 14,
                color: Colors.orange[600],
              ),
            ),
        ],
      ),
    );
  }

  /// Build expandable display with details.
  Widget _buildExpandableDisplay() {
    final tierName = _getTierDisplayName(widget.licenseInfo.tier);
    final tierColor = _getTierColor(widget.licenseInfo.tier);
    final isExpired = widget.licenseInfo.isExpired;
    final maxWorkflows = widget.licenseInfo.getMaxWorkflows();
    final currentWorkflows = widget.currentWorkflows ?? 0;

    return Container(
      decoration: BoxDecoration(
        color: widget.backgroundColor ?? const Color(0xFF121212),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isExpired
              ? Colors.red.withOpacity(0.5)
              : const Color(0xFFD4AF37).withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Column(
        children: [
          // Compact header (always visible)
          InkWell(
            onTap: _toggleExpand,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  // Status indicator
                  Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(
                      color: isExpired ? Colors.red : tierColor,
                      borderRadius: BorderRadius.circular(5),
                    ),
                  ),
                  const SizedBox(width: 12),

                  // Tier and status
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'License Status',
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.grey[500],
                            fontWeight: FontWeight.w600,
                            letterSpacing: 0.2,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 4,
                              ),
                              decoration: BoxDecoration(
                                color: tierColor.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(
                                  color: tierColor.withOpacity(0.5),
                                  width: 0.5,
                                ),
                              ),
                              child: Text(
                                tierName,
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                  color: tierColor,
                                  letterSpacing: 0.3,
                                ),
                              ),
                            ),
                            if (isExpired) ...[
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 8,
                                  vertical: 4,
                                ),
                                decoration: BoxDecoration(
                                  color: Colors.red.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(4),
                                  border: Border.all(
                                    color: Colors.red.withOpacity(0.5),
                                    width: 0.5,
                                  ),
                                ),
                                child: const Text(
                                  'Expired',
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.w700,
                                    color: Colors.red,
                                  ),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ],
                    ),
                  ),

                  // Expand button
                  Icon(
                    _isExpanded ? Icons.expand_less : Icons.expand_more,
                    color: Colors.grey[600],
                    size: 20,
                  ),
                ],
              ),
            ),
          ),

          // Expanded details
          if (_isExpanded) ...[
            Divider(
              height: 1,
              color: Colors.grey[800],
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Features count
                  _buildDetailRow(
                    'Features',
                    '${widget.licenseInfo.features.length} enabled',
                  ),
                  const SizedBox(height: 10),

                  // Max streams
                  _buildDetailRow(
                    'Max Streams',
                    '${widget.licenseInfo.maxStreams}',
                  ),
                  const SizedBox(height: 10),

                  // Max bitrate
                  _buildDetailRow(
                    'Max Bitrate',
                    _formatBitrate(
                      widget.licenseInfo.getMaxBitrate(),
                    ),
                  ),
                  const SizedBox(height: 10),

                  // Workflows
                  if (maxWorkflows > 0) ...[
                    _buildDetailRow(
                      'Workflows',
                      '$currentWorkflows/$maxWorkflows used',
                      valueColor: currentWorkflows >= maxWorkflows
                          ? Colors.orange[600]
                          : null,
                    ),
                    const SizedBox(height: 10),
                  ],

                  // Expiration
                  if (widget.showExpiration) ...[
                    _buildDetailRow(
                      'Expires',
                      _formatExpirationDate(
                        widget.licenseInfo.expirationDate,
                      ),
                      valueColor: isExpired ? Colors.red : null,
                    ),
                    const SizedBox(height: 10),
                  ],

                  // External streaming capability
                  if (widget.licenseInfo.canStreamExternal()) ...[
                    _buildDetailRow(
                      'External Streaming',
                      'Enabled',
                      valueColor: Colors.green[400],
                    ),
                  ],
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDetailRow(
    String label,
    String value, {
    Color? valueColor,
  }) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[400],
            fontWeight: FontWeight.w500,
          ),
        ),
        Text(
          value,
          style: TextStyle(
            fontSize: 12,
            color: valueColor ?? Colors.grey[200],
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  String _formatBitrate(int bps) {
    if (bps >= 1000000000) {
      return '${(bps / 1000000000).toStringAsFixed(0)} Gbps';
    } else if (bps >= 1000000) {
      return '${(bps / 1000000).toStringAsFixed(1)} Mbps';
    } else if (bps >= 1000) {
      return '${(bps / 1000).toStringAsFixed(1)} Kbps';
    }
    return '$bps bps';
  }
}
