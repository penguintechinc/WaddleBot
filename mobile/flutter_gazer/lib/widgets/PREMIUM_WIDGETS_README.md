# Premium Feature Gating Widgets - Quick Reference

Three reusable Flutter widgets for premium feature licensing UI in the Elder theme.

## Quick Start

### 1. Show Upgrade Dialog
```dart
import 'package:flutter_gazer/widgets/premium_gate_dialog.dart';

PremiumGateDialog.show(
  context,
  featureName: 'External RTMP Streaming',
  currentTier: LicenseTier.free,
  requiredTier: LicenseTier.pro,
  upgradeBenefits: [
    'Stream to external RTMP endpoints',
    'Multiple simultaneous streams',
  ],
  pricingUrl: 'https://www.penguintech.io/pricing',
);
```

### 2. Display License Status
```dart
import 'package:flutter_gazer/widgets/license_status_widget.dart';

LicenseStatusWidget(
  licenseInfo: licenseService.currentLicense!,
  currentWorkflows: activeCount,
  showExpiration: true,
)
```

### 3. Add Premium Badge
```dart
import 'package:flutter_gazer/widgets/premium_badge.dart';

// Simple overlay
ElevatedButton(
  onPressed: () {},
  child: Text('Stream'),
).withPremiumBadge()

// Or standalone
PremiumBadge.large(label: 'PRO')
```

## Widgets Overview

| Widget | Purpose | Mode |
|--------|---------|------|
| **PremiumGateDialog** | Modal upgrade prompt | Modal/Sheet |
| **LicenseStatusWidget** | License tier display | Inline/Expandable |
| **PremiumBadge** | "PRO" indicator | Inline/Overlay |

## Properties Cheat Sheet

### PremiumGateDialog
- `featureName` (required)
- `featureDescription` (optional)
- `currentTier` (required)
- `requiredTier` (required)
- `upgradeBenefits` (optional, List<String>)
- `pricingUrl` (optional)
- `onUpgradePressed` (optional, VoidCallback)
- `onDismissed` (optional, VoidCallback)

### LicenseStatusWidget
- `licenseInfo` (required)
- `currentWorkflows` (optional)
- `compact` (bool, default: false)
- `showExpiration` (bool, default: true)
- `backgroundColor` (Color?, optional)
- `tierTextColor` (Color?, optional)

### PremiumBadge
- `size` ('small'|'medium'|'large', default: 'medium')
- `label` (default: 'PRO')
- `tooltip` (optional)
- `showIcon` (bool, default: true)
- `backgroundColor` (Color?, default: gold)
- `textColor` (Color?, default: black87)

## Common Patterns

### Protect Premium Feature
```dart
bool hasAccess = await licenseService.checkFeatureAccess('streaming');
if (!hasAccess) {
  PremiumGateDialog.show(context, ...);
  return;
}
// Allow access
```

### Settings License Display
```dart
Widget build(context) {
  return LicenseStatusWidget(
    licenseInfo: licenseService.currentLicense!,
    currentWorkflows: _getActiveCount(),
  );
}
```

### Feature Badge Overlay
```dart
Widget buildFeatureButton() {
  return ElevatedButton(
    onPressed: () {},
    child: Text('Advanced'),
  ).withPremiumBadge(
    label: 'PRO',
    tooltip: 'Requires Pro tier',
  );
}
```

## Tier Colors
- **Free**: Gray
- **Premium**: Blue
- **Pro**: Gold (#D4AF37)
- **Enterprise**: Purple

## Elder Theme
- Primary gold: `#D4AF37`
- Background: `#121212`
- Text: `Colors.grey[300]`

## File Locations
- `lib/widgets/premium_gate_dialog.dart` (455 lines)
- `lib/widgets/license_status_widget.dart` (399 lines)
- `lib/widgets/premium_badge.dart` (356 lines)

## Dependencies
- `flutter/material.dart`
- `flutter_gazer/models/license_info.dart`
- `url_launcher/url_launcher.dart` (for dialogs)
- `intl/intl.dart` (for date formatting)

---

See **PREMIUM_WIDGETS_SUMMARY.md** for detailed documentation.
