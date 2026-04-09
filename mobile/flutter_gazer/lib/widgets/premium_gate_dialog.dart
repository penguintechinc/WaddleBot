import 'package:flutter/material.dart';
import '../models/license_info.dart';
import 'package:url_launcher/url_launcher.dart';

/// Premium feature gate dialog.
///
/// Shows an upgrade prompt when user attempts to access a premium feature.
/// Displays current tier, required tier, feature benefits, and upgrade button.
/// Uses Elder theme styling with gold accents.
class PremiumGateDialog extends StatefulWidget {
  /// Name of the feature requiring premium access.
  final String featureName;

  /// Description of what the feature does.
  final String? featureDescription;

  /// Current license tier.
  final LicenseTier currentTier;

  /// Required tier for this feature.
  final LicenseTier requiredTier;

  /// Benefits of upgrading (3-5 bullet points).
  final List<String>? upgradeBenefits;

  /// URL to pricing/upgrade page.
  final String? pricingUrl;

  /// Callback when upgrade button is tapped.
  final VoidCallback? onUpgradePressed;

  /// Callback when dialog is dismissed.
  final VoidCallback? onDismissed;

  const PremiumGateDialog({
    super.key,
    required this.featureName,
    this.featureDescription,
    required this.currentTier,
    required this.requiredTier,
    this.upgradeBenefits,
    this.pricingUrl,
    this.onUpgradePressed,
    this.onDismissed,
  });

  @override
  State<PremiumGateDialog> createState() => _PremiumGateDialogState();

  /// Show premium gate dialog.
  static Future<void> show(
    BuildContext context, {
    required String featureName,
    String? featureDescription,
    required LicenseTier currentTier,
    required LicenseTier requiredTier,
    List<String>? upgradeBenefits,
    String? pricingUrl,
    VoidCallback? onUpgradePressed,
    VoidCallback? onDismissed,
  }) {
    return showDialog<void>(
      context: context,
      builder: (context) => PremiumGateDialog(
        featureName: featureName,
        featureDescription: featureDescription,
        currentTier: currentTier,
        requiredTier: requiredTier,
        upgradeBenefits: upgradeBenefits,
        pricingUrl: pricingUrl,
        onUpgradePressed: onUpgradePressed,
        onDismissed: onDismissed,
      ),
      barrierDismissible: true,
    );
  }
}

class _PremiumGateDialogState extends State<PremiumGateDialog> {
  bool _isLoading = false;

  @override
  void dispose() {
    widget.onDismissed?.call();
    super.dispose();
  }

  Future<void> _handleUpgradePressed() async {
    widget.onUpgradePressed?.call();

    if (widget.pricingUrl == null || widget.pricingUrl!.isEmpty) {
      return;
    }

    setState(() => _isLoading = true);

    try {
      final uri = Uri.parse(widget.pricingUrl!);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Could not open pricing page'),
            backgroundColor: Colors.red.shade700,
            duration: const Duration(seconds: 2),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

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

  @override
  Widget build(BuildContext context) {
    final currentTierName = _getTierDisplayName(widget.currentTier);
    final requiredTierName = _getTierDisplayName(widget.requiredTier);

    return AlertDialog(
      backgroundColor: const Color(0xFF1a1a1a),
      contentPadding: EdgeInsets.zero,
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header with icon
            Container(
              padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 20),
              decoration: BoxDecoration(
                color: Colors.grey[900],
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(12),
                  topRight: Radius.circular(12),
                ),
                border: Border(
                  bottom: BorderSide(
                    color: const Color(0xFFD4AF37).withOpacity( 0.3),
                    width: 1,
                  ),
                ),
              ),
              child: Column(
                children: [
                  Container(
                    width: 56,
                    height: 56,
                    decoration: BoxDecoration(
                      color: const Color(0xFFD4AF37).withOpacity( 0.15),
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: const Color(0xFFD4AF37),
                        width: 1.5,
                      ),
                    ),
                    child: const Icon(
                      Icons.lock_outline,
                      color: Color(0xFFD4AF37),
                      size: 28,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Unlock ${widget.featureName}',
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFFD4AF37),
                      letterSpacing: 0.5,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),

            // Content
            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Feature description
                  if (widget.featureDescription != null) ...[
                    Text(
                      widget.featureDescription!,
                      style: TextStyle(
                        fontSize: 13,
                        color: Colors.grey[300],
                        height: 1.5,
                      ),
                    ),
                    const SizedBox(height: 20),
                  ],

                  // Tier comparison
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.grey[900],
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: Colors.grey[800]!,
                        width: 0.5,
                      ),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Your Tier',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.grey[500],
                                  fontWeight: FontWeight.w600,
                                  letterSpacing: 0.3,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 8,
                                  vertical: 6,
                                ),
                                decoration: BoxDecoration(
                                  color: _getTierColor(widget.currentTier)
                                      .withOpacity( 0.15),
                                  borderRadius: BorderRadius.circular(4),
                                  border: Border.all(
                                    color: _getTierColor(widget.currentTier)
                                        .withOpacity( 0.5),
                                    width: 0.5,
                                  ),
                                ),
                                child: Text(
                                  currentTierName,
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                    color: _getTierColor(widget.currentTier),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        Icon(
                          Icons.arrow_forward,
                          size: 18,
                          color: Colors.grey[600],
                        ),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Text(
                                'Required',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.grey[500],
                                  fontWeight: FontWeight.w600,
                                  letterSpacing: 0.3,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 8,
                                  vertical: 6,
                                ),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFD4AF37)
                                      .withOpacity( 0.15),
                                  borderRadius: BorderRadius.circular(4),
                                  border: Border.all(
                                    color: const Color(0xFFD4AF37)
                                        .withOpacity( 0.5),
                                    width: 0.5,
                                  ),
                                ),
                                child: Text(
                                  requiredTierName,
                                  style: const TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                    color: Color(0xFFD4AF37),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 20),

                  // Benefits
                  if (widget.upgradeBenefits != null &&
                      widget.upgradeBenefits!.isNotEmpty) ...[
                    Text(
                      'Upgrade Benefits',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: Colors.grey[400],
                        letterSpacing: 0.3,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Column(
                      children: widget.upgradeBenefits!
                          .map((benefit) => Padding(
                                padding: const EdgeInsets.only(bottom: 8),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Container(
                                      margin: const EdgeInsets.only(top: 4),
                                      width: 6,
                                      height: 6,
                                      decoration: BoxDecoration(
                                        color: const Color(0xFFD4AF37),
                                        borderRadius: BorderRadius.circular(3),
                                      ),
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Text(
                                        benefit,
                                        style: TextStyle(
                                          fontSize: 12,
                                          color: Colors.grey[300],
                                          height: 1.4,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ))
                          .toList(),
                    ),
                  ],
                ],
              ),
            ),

            // Buttons
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Row(
                children: [
                  Expanded(
                    child: TextButton(
                      onPressed: _isLoading ? null : () => Navigator.pop(context),
                      style: TextButton.styleFrom(
                        foregroundColor: Colors.grey[400],
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      child: const Text(
                        'Maybe Later',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFFD4AF37), Color(0xFFF0D88B)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          onTap: _isLoading ? null : _handleUpgradePressed,
                          borderRadius: BorderRadius.circular(6),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            child: _isLoading
                                ? const SizedBox(
                                    height: 20,
                                    width: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor:
                                          AlwaysStoppedAnimation<Color>(
                                        Colors.black,
                                      ),
                                    ),
                                  )
                                : const Text(
                                    'Upgrade Now',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.black,
                                      letterSpacing: 0.5,
                                    ),
                                  ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
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
}
