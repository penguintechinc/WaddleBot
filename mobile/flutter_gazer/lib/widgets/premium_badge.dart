import 'package:flutter/material.dart';

/// Premium feature badge widget.
///
/// Small "PRO" or "PREMIUM" badge that can be overlaid on buttons/cards.
/// Uses gold/amber styling with Elder theme.
/// Supports different sizes and optional tooltip with upgrade message.
class PremiumBadge extends StatelessWidget {
  /// Badge size: 'small' (16px), 'medium' (20px), 'large' (24px).
  final String size;

  /// Label to display (default: "PRO").
  final String label;

  /// Tooltip message when user hovers/long-presses.
  final String? tooltip;

  /// Custom background color (overrides theme).
  final Color? backgroundColor;

  /// Custom text color (overrides theme).
  final Color? textColor;

  /// Callback when badge is tapped.
  final VoidCallback? onTap;

  /// Show icon (star) next to label.
  final bool showIcon;

  /// Make badge interactive (with ripple effect).
  final bool interactive;

  const PremiumBadge({
    super.key,
    this.size = 'medium',
    this.label = 'PRO',
    this.tooltip,
    this.backgroundColor,
    this.textColor,
    this.onTap,
    this.showIcon = true,
    this.interactive = false,
  });

  double _getSizeValue() {
    switch (size) {
      case 'small':
        return 14;
      case 'medium':
        return 18;
      case 'large':
        return 22;
      default:
        return 18;
    }
  }

  double _getPaddingHorizontal() {
    switch (size) {
      case 'small':
        return 5;
      case 'medium':
        return 7;
      case 'large':
        return 9;
      default:
        return 7;
    }
  }

  double _getPaddingVertical() {
    switch (size) {
      case 'small':
        return 2;
      case 'medium':
        return 3;
      case 'large':
        return 4;
      default:
        return 3;
    }
  }

  double _getFontSize() {
    switch (size) {
      case 'small':
        return 10;
      case 'medium':
        return 12;
      case 'large':
        return 13;
      default:
        return 12;
    }
  }

  double _getIconSize() {
    switch (size) {
      case 'small':
        return 8;
      case 'medium':
        return 10;
      case 'large':
        return 12;
      default:
        return 10;
    }
  }

  @override
  Widget build(BuildContext context) {
    final badge = _buildBadge();

    if (tooltip != null) {
      return Tooltip(
        message: tooltip!,
        textStyle: const TextStyle(
          color: Colors.white,
          fontSize: 12,
        ),
        decoration: BoxDecoration(
          color: Colors.grey[900],
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: const Color(0xFFD4AF37),
            width: 0.5,
          ),
        ),
        child: badge,
      );
    }

    return badge;
  }

  Widget _buildBadge() {
    Widget child = Padding(
      padding: EdgeInsets.symmetric(
        horizontal: _getPaddingHorizontal(),
        vertical: _getPaddingVertical(),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showIcon) ...[
            Icon(
              Icons.star,
              size: _getIconSize(),
              color: textColor ?? Colors.black87,
            ),
            SizedBox(width: size == 'small' ? 3 : 4),
          ],
          Text(
            label,
            style: TextStyle(
              fontSize: _getFontSize(),
              fontWeight: FontWeight.w700,
              color: textColor ?? Colors.black87,
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );

    final decoration = BoxDecoration(
      gradient: LinearGradient(
        colors: [
          backgroundColor ?? const Color(0xFFD4AF37),
          backgroundColor ?? const Color(0xFFF0D88B),
        ],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      ),
      borderRadius: BorderRadius.circular(_getSizeValue() * 0.5),
      boxShadow: [
        BoxShadow(
          color: (backgroundColor ?? const Color(0xFFD4AF37)).withOpacity( 0.4),
          blurRadius: 6,
          offset: const Offset(0, 2),
        ),
      ],
    );

    if (interactive && onTap != null) {
      return Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(_getSizeValue() * 0.5),
          child: Container(
            decoration: decoration,
            child: child,
          ),
        ),
      );
    }

    return Container(
      decoration: decoration,
      child: child,
    );
  }

  /// Create a small badge (compact display).
  static PremiumBadge small({
    String label = 'PRO',
    String? tooltip,
    VoidCallback? onTap,
  }) {
    return PremiumBadge(
      size: 'small',
      label: label,
      tooltip: tooltip,
      onTap: onTap,
    );
  }

  /// Create a medium badge (default size).
  static PremiumBadge medium({
    String label = 'PRO',
    String? tooltip,
    VoidCallback? onTap,
  }) {
    return PremiumBadge(
      size: 'medium',
      label: label,
      tooltip: tooltip,
      onTap: onTap,
    );
  }

  /// Create a large badge (prominent display).
  static PremiumBadge large({
    String label = 'PRO',
    String? tooltip,
    VoidCallback? onTap,
  }) {
    return PremiumBadge(
      size: 'large',
      label: label,
      tooltip: tooltip,
      onTap: onTap,
    );
  }

  /// Create a custom badge with specific color.
  static PremiumBadge custom({
    required String size,
    String label = 'PRO',
    required Color backgroundColor,
    required Color textColor,
    String? tooltip,
    VoidCallback? onTap,
  }) {
    return PremiumBadge(
      size: size,
      label: label,
      backgroundColor: backgroundColor,
      textColor: textColor,
      tooltip: tooltip,
      onTap: onTap,
    );
  }
}

/// Overlay extension for placing badges on widgets.
class _PremiumBadgeOverlay extends StatelessWidget {
  final Widget child;
  final PremiumBadge badge;
  final Alignment alignment;

  const _PremiumBadgeOverlay({
    required this.child,
    required this.badge,
    this.alignment = Alignment.topRight,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        child,
        Positioned(
          top: alignment == Alignment.topRight || alignment == Alignment.topLeft
              ? -6
              : null,
          bottom: alignment == Alignment.bottomRight ||
                  alignment == Alignment.bottomLeft
              ? -6
              : null,
          right: alignment == Alignment.topRight ||
                  alignment == Alignment.bottomRight
              ? -6
              : null,
          left: alignment == Alignment.topLeft ||
                  alignment == Alignment.bottomLeft
              ? -6
              : null,
          child: badge,
        ),
      ],
    );
  }
}

/// Extension on Widget to easily add premium badge overlay.
extension PremiumBadgeOverlay on Widget {
  /// Overlay a premium badge on this widget.
  ///
  /// Example:
  /// ```dart
  /// FloatingActionButton(
  ///   onPressed: () {},
  ///   child: Icon(Icons.videocam),
  /// ).withPremiumBadge()
  /// ```
  Widget withPremiumBadge({
    String label = 'PRO',
    String? tooltip,
    Alignment alignment = Alignment.topRight,
    String size = 'medium',
  }) {
    return _PremiumBadgeOverlay(
      badge: PremiumBadge(
        size: size,
        label: label,
        tooltip: tooltip,
      ),
      alignment: alignment,
      child: this,
    );
  }

  /// Overlay a premium badge with custom styling.
  Widget withCustomPremiumBadge({
    required String label,
    required Color backgroundColor,
    required Color textColor,
    String? tooltip,
    Alignment alignment = Alignment.topRight,
    String size = 'medium',
  }) {
    return _PremiumBadgeOverlay(
      badge: PremiumBadge(
        size: size,
        label: label,
        backgroundColor: backgroundColor,
        textColor: textColor,
        tooltip: tooltip,
      ),
      alignment: alignment,
      child: this,
    );
  }
}
