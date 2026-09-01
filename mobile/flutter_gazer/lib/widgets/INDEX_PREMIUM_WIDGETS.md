# Premium Feature Gating Widgets - Index

Quick navigation for the three premium feature gating widgets.

## Files

### 1. **premium_gate_dialog.dart** (455 lines)
Modal dialog for showing upgrade prompts when users access premium-only features.

**Quick Features:**
- Feature name, description, and upgrade benefits display
- Tier comparison (current → required)
- Gold gradient upgrade button with URL launcher
- Loading state during link open
- Callback support for tracking

**Quick Usage:**
```dart
PremiumGateDialog.show(context,
  featureName: 'External RTMP Streaming',
  currentTier: LicenseTier.free,
  requiredTier: LicenseTier.pro,
  upgradeBenefits: [...],
  pricingUrl: 'https://...',
)
```

**See:** PREMIUM_WIDGETS_SUMMARY.md § 1. premium_gate_dialog.dart

---

### 2. **license_status_widget.dart** (399 lines)
Compact/expandable widget displaying license tier, features, and usage.

**Quick Features:**
- Status indicator with color-coded tier
- Expandable details panel
- Usage counters (workflows, streams, bitrate)
- Expiration date with warning
- Two modes: compact | expandable

**Quick Usage:**
```dart
LicenseStatusWidget(
  licenseInfo: licenseService.currentLicense!,
  currentWorkflows: activeCount,
)
```

**See:** PREMIUM_WIDGETS_SUMMARY.md § 2. license_status_widget.dart

---

### 3. **premium_badge.dart** (356 lines)
Small "PRO" badge with star icon, gold styling, and overlay support.

**Quick Features:**
- Three sizes: small | medium | large
- Star icon + customizable label
- Gold gradient background
- Tooltip support
- Widget extension for easy overlay (`.withPremiumBadge()`)

**Quick Usage:**
```dart
ElevatedButton(...).withPremiumBadge()
// or
PremiumBadge.large(label: 'PRO')
```

**See:** PREMIUM_WIDGETS_SUMMARY.md § 3. premium_badge.dart

---

## Documentation

| Document | Purpose |
|----------|---------|
| **PREMIUM_WIDGETS_SUMMARY.md** | Complete reference with patterns, styling, and examples |
| **PREMIUM_WIDGETS_README.md** | Quick start guide with code snippets |
| **INDEX_PREMIUM_WIDGETS.md** | This navigation index |

---

## Quick Integration Patterns

### Pattern 1: Block Premium Access
```dart
bool hasAccess = await licenseService.checkFeatureAccess('streaming');
if (!hasAccess) {
  PremiumGateDialog.show(context, 
    featureName: 'Feature Name',
    currentTier: license.tier,
    requiredTier: LicenseTier.pro,
  );
  return;
}
// Allow access
```

### Pattern 2: Show License in Settings
```dart
LicenseStatusWidget(
  licenseInfo: licenseService.currentLicense!,
  currentWorkflows: getActiveWorkflowCount(),
)
```

### Pattern 3: Badge on Button
```dart
ElevatedButton(onPressed: () {}, child: Text('Stream'))
  .withPremiumBadge(label: 'PRO', size: 'small')
```

---

## Files Structure
```
lib/widgets/
├── premium_gate_dialog.dart       ← Upgrade dialog
├── license_status_widget.dart     ← License display
├── premium_badge.dart             ← Pro badge
├── INDEX_PREMIUM_WIDGETS.md       ← This file
└── PREMIUM_WIDGETS_README.md      ← Quick reference

root/
└── PREMIUM_WIDGETS_SUMMARY.md     ← Complete docs
```

---

## Quick Feature Matrix

| Feature | Dialog | Status | Badge |
|---------|--------|--------|-------|
| Elder theme | ✓ | ✓ | ✓ |
| Null safe | ✓ | ✓ | ✓ |
| Callbacks | ✓ | ✓ | ✓ |
| All tiers | ✓ | ✓ | ✓ |
| Expandable | - | ✓ | - |
| Overlay | - | - | ✓ |
| URL launch | ✓ | - | - |

---

## Getting Started

1. **Import a widget:**
   ```dart
   import 'package:flutter_gazer/widgets/premium_gate_dialog.dart';
   ```

2. **Use the widget:**
   ```dart
   PremiumGateDialog.show(context, ...);
   ```

3. **Reference docs:**
   - Quick start: `PREMIUM_WIDGETS_README.md`
   - Full docs: `PREMIUM_WIDGETS_SUMMARY.md`
   - This file: Quick navigation

---

## Dependencies

All widgets use existing project dependencies:
- `flutter/material.dart`
- `flutter_gazer/models/license_info.dart`
- `url_launcher/url_launcher.dart` (premium_gate_dialog)
- `intl/intl.dart` (license_status_widget)

No new pubspec.yaml entries required.

---

## Elder Theme Colors

- Primary Gold: `#D4AF37`
- Secondary Gold: `#F0D88B`
- Dark Background: `#121212` - `#1a1a1a`
- Text Primary: `Colors.grey[300]`
- Text Secondary: `Colors.grey[500]`

---

Last updated: 2026-01-30
