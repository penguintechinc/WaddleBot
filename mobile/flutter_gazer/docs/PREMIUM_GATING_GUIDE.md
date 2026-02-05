# Premium Gating Integration Guide

## Table of Contents

1. [Overview](#overview)
2. [Available Widgets](#available-widgets)
3. [LicenseService API](#licenseservice-api)
4. [Client-Side Gating](#client-side-gating)
5. [Server-Side Gating](#server-side-gating)
6. [Integration Patterns](#integration-patterns)
7. [Future Features](#future-features)

---

## Overview

Premium gating in Waddles Gazer implements a hybrid approach to restrict features based on user license status:

### Strategy

- **Client-Side Gating**: Immediate UI feedback, prevents unnecessary API calls for free users
- **Server-Side Gating**: Enforces business logic server-side, prevents client-side cheating
- **License Synchronization**: License status synced from Hub API on app launch and periodically

### Feature Tier Structure

```
FREE TIER (Basic Features)
├── Single Gazer instance
├── 1x USB camera input
├── Standard 360p streaming
└── Basic settings

PREMIUM TIER (Advanced Features)
├── Multiple simultaneous streamers
├── 4x USB camera inputs
├── HD 1080p streaming
├── Overlay mode
├── External RTMP destinations
├── Advanced settings
└── Priority support
```

### License Status States

```
UNKNOWN       → License status not yet loaded
UNLICENSED    → No valid license
BASIC         → Free tier
PREMIUM       → Premium tier (all features)
EXPIRED       → License expired
ERROR         → License validation failed
```

---

## Available Widgets

### PremiumGateDialog

Interactive dialog for managing premium feature access requests.

```dart
class PremiumGateDialog extends StatelessWidget {
  final String featureName;
  final String? description;
  final VoidCallback onUpgradePressed;
  final VoidCallback? onDismissPressed;

  const PremiumGateDialog({
    required this.featureName,
    this.description,
    required this.onUpgradePressed,
    this.onDismissPressed,
  });

  @override
  Widget build(BuildContext context) {
    // Shows feature name, tier requirements, upgrade button
  }
}
```

**Usage:**

```dart
showDialog(
  context: context,
  builder: (context) => PremiumGateDialog(
    featureName: 'HD Streaming',
    description: 'Upgrade to premium to stream in 1080p',
    onUpgradePressed: () {
      Navigator.pop(context);
      _navigateToLicensing();
    },
  ),
);
```

### LicenseStatusWidget

Compact widget displaying current license status with color coding.

```dart
class LicenseStatusWidget extends StatelessWidget {
  final LicenseStatus status;
  final bool showLabel;
  final double size;

  const LicenseStatusWidget({
    required this.status,
    this.showLabel = true,
    this.size = 20.0,
  });

  @override
  Widget build(BuildContext context) {
    // Displays status badge with color:
    // GREEN for PREMIUM
    // GRAY for BASIC
    // RED for EXPIRED/ERROR
    // BLUE for UNKNOWN
  }
}
```

**Usage:**

```dart
AppBar(
  title: Text('Gazer'),
  actions: [
    Padding(
      padding: EdgeInsets.all(16),
      child: LicenseStatusWidget(
        status: licenseService.currentStatus,
      ),
    ),
  ],
)
```

### PremiumBadge

Badge overlay for features requiring premium tier.

```dart
class PremiumBadge extends StatelessWidget {
  final Widget child;
  final bool isPremium;
  final String? label;

  const PremiumBadge({
    required this.child,
    this.isPremium = false,
    this.label = 'PREMIUM',
  });

  @override
  Widget build(BuildContext context) {
    // Renders child with gold premium badge overlay
  }
}
```

**Usage:**

```dart
PremiumBadge(
  isPremium: !licenseService.canUseFeature('hd_streaming'),
  child: ListTile(
    title: Text('HD Streaming (1080p)'),
    subtitle: Text('Enable 1080p video quality'),
  ),
)
```

---

## LicenseService API

Core service for checking feature availability and managing license status.

### Methods

#### `canUseFeature(String featureName) -> Future<bool>`

Check if current license allows feature usage.

```dart
final canStream = await licenseService.canUseFeature('hd_streaming');
if (canStream) {
  startHDStream();
} else {
  showPremiumGate('HD Streaming');
}
```

**Supported Features:**

```dart
// Camera inputs
'multi_camera'          // Multiple simultaneous camera sources
'usb_camera_4x'         // 4x USB camera inputs (premium limit)
'usb_camera_unlimited'  // Unlimited USB inputs (future)

// Streaming quality
'hd_streaming'          // 1080p video quality
'streaming_quality_adaptive'  // Adaptive bitrate

// Streaming modes
'overlay_mode'          // Picture-in-picture overlay
'external_rtmp'         // Send to external RTMP destinations

// Advanced features
'workflow_creation'     // Create custom workflows
'module_marketplace'    // Access module marketplace
'video_proxy'           // Proxy video to multiple destinations
```

#### `getLicenseStatus() -> Future<LicenseStatus>`

Fetch current license status from Hub API.

```dart
try {
  final status = await licenseService.getLicenseStatus();
  print('License: ${status.tier}');
  print('Expires: ${status.expiresAt}');
} catch (e) {
  print('Error fetching license: $e');
}
```

#### `getFeatureLimit(String featureName) -> Future<FeatureLimit?>`

Get numeric limit for a feature (e.g., max cameras, max workflows).

```dart
final cameraLimit = await licenseService.getFeatureLimit('usb_camera_max');
print('Maximum USB cameras: ${cameraLimit?.limit}');
// Output: Maximum USB cameras: 1 (FREE) or 4 (PREMIUM)

final workflowLimit = await licenseService.getFeatureLimit('workflow_max');
print('Maximum workflows: ${workflowLimit?.limit}');
// Output: Maximum workflows: 1 (FREE) or unlimited (PREMIUM)
```

#### `onLicenseStatusChanged -> Stream<LicenseStatus>`

Stream for reactive license status updates.

```dart
licenseService.onLicenseStatusChanged.listen((status) {
  setState(() {
    _licenseStatus = status;
  });
});
```

#### `syncLicenseStatus() -> Future<void>`

Force synchronization with Hub API.

```dart
// Called on app launch and periodically (every 24 hours)
await licenseService.syncLicenseStatus();
```

---

## Client-Side Gating

Prevent premium features from being accessible in the UI for unlicensed users.

### USB Camera Input Limiting

```dart
class CameraInputSelector extends StatefulWidget {
  @override
  State<CameraInputSelector> createState() => _CameraInputSelectorState();
}

class _CameraInputSelectorState extends State<CameraInputSelector> {
  final licenseService = LicenseService();
  List<String> availableCameras = [];
  int selectedCameraCount = 0;

  @override
  void initState() {
    super.initState();
    _loadAvailableCameras();
  }

  Future<void> _loadAvailableCameras() async {
    final cameras = await CameraManager.getAvailableCameras();

    // Get max camera limit based on license
    final limit = await licenseService.getFeatureLimit('usb_camera_max');
    final maxCameras = limit?.limit ?? 1;

    setState(() {
      availableCameras = cameras
          .take(maxCameras)
          .map((c) => c.name)
          .toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Camera selection with locked state for premium-only slots
        for (int i = 0; i < 4; i++)
          CameraSlot(
            index: i,
            isAvailable: i < availableCameras.length,
            camera: i < availableCameras.length
                ? availableCameras[i]
                : null,
            onLocked: () => _showUpgradeDialog(context),
          ),
      ],
    );
  }

  void _showUpgradeDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => PremiumGateDialog(
        featureName: 'Multiple USB Cameras',
        description: 'Upgrade to premium to use 4 USB camera inputs simultaneously',
        onUpgradePressed: () {
          Navigator.pop(context);
          // Navigate to license purchase/upgrade flow
        },
      ),
    );
  }
}
```

### Overlay Mode Gating

```dart
class StreamingModeSelector extends StatefulWidget {
  @override
  State<StreamingModeSelector> createState() => _StreamingModeSelectorState();
}

class _StreamingModeSelectorState extends State<StreamingModeSelector> {
  final licenseService = LicenseService();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Standard streaming mode (always available)
        ListTile(
          title: Text('Standard Mode'),
          subtitle: Text('Stream from single source'),
          trailing: Radio<String>(
            value: 'standard',
            groupValue: _selectedMode,
            onChanged: (value) {
              setState(() => _selectedMode = value!);
            },
          ),
        ),

        // Overlay mode (premium only)
        FutureBuilder<bool>(
          future: licenseService.canUseFeature('overlay_mode'),
          builder: (context, snapshot) {
            final canUseOverlay = snapshot.data ?? false;

            return PremiumBadge(
              isPremium: !canUseOverlay,
              child: ListTile(
                title: Text('Overlay Mode'),
                subtitle: Text('Picture-in-picture with multiple streams'),
                enabled: canUseOverlay,
                trailing: Radio<String>(
                  value: 'overlay',
                  groupValue: canUseOverlay ? _selectedMode : '',
                  onChanged: canUseOverlay
                      ? (value) => setState(() => _selectedMode = value!)
                      : null,
                ),
                onTap: !canUseOverlay
                    ? () => _showPremiumGate(context)
                    : null,
              ),
            );
          },
        ),
      ],
    );
  }

  void _showPremiumGate(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => PremiumGateDialog(
        featureName: 'Overlay Mode',
        description: 'Upgrade to premium for picture-in-picture streaming',
        onUpgradePressed: () {
          Navigator.pop(context);
          // Navigate to licensing
        },
      ),
    );
  }
}
```

### HD Streaming Quality Gating

```dart
class StreamingQualitySettings extends StatefulWidget {
  @override
  State<StreamingQualitySettings> createState() =>
    _StreamingQualitySettingsState();
}

class _StreamingQualitySettingsState extends State<StreamingQualitySettings> {
  final licenseService = LicenseService();
  String selectedQuality = '360p'; // Default

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text('Streaming Quality', style: Theme.of(context).textTheme.titleMedium),
        SizedBox(height: 16),

        // 360p (always available)
        ListTile(
          title: Text('360p (Standard)'),
          subtitle: Text('Recommended for mobile networks'),
          trailing: Radio<String>(
            value: '360p',
            groupValue: selectedQuality,
            onChanged: (value) {
              setState(() => selectedQuality = value!);
            },
          ),
        ),

        // 720p (premium)
        FutureBuilder<bool>(
          future: licenseService.canUseFeature('hd_streaming'),
          builder: (context, snapshot) {
            final canUseHD = snapshot.data ?? false;

            return PremiumBadge(
              isPremium: !canUseHD,
              child: ListTile(
                title: Text('720p (HD)'),
                subtitle: Text('Higher quality for good networks'),
                enabled: canUseHD,
                trailing: Radio<String>(
                  value: '720p',
                  groupValue: canUseHD ? selectedQuality : '',
                  onChanged: canUseHD
                      ? (value) => setState(() => selectedQuality = value!)
                      : null,
                ),
                onTap: !canUseHD
                    ? () => _showPremiumGate(context, '720p')
                    : null,
              ),
            );
          },
        ),

        // 1080p (premium)
        FutureBuilder<bool>(
          future: licenseService.canUseFeature('hd_streaming'),
          builder: (context, snapshot) {
            final canUseHD = snapshot.data ?? false;

            return PremiumBadge(
              isPremium: !canUseHD,
              child: ListTile(
                title: Text('1080p (Full HD)'),
                subtitle: Text('Maximum quality (requires fast network)'),
                enabled: canUseHD,
                trailing: Radio<String>(
                  value: '1080p',
                  groupValue: canUseHD ? selectedQuality : '',
                  onChanged: canUseHD
                      ? (value) => setState(() => selectedQuality = value!)
                      : null,
                ),
                onTap: !canUseHD
                    ? () => _showPremiumGate(context, '1080p')
                    : null,
              ),
            );
          },
        ),
      ],
    );
  }

  void _showPremiumGate(BuildContext context, String quality) {
    showDialog(
      context: context,
      builder: (context) => PremiumGateDialog(
        featureName: '$quality Streaming',
        description: 'Upgrade to premium for high-definition streaming',
        onUpgradePressed: () {
          Navigator.pop(context);
          // Navigate to licensing
        },
      ),
    );
  }
}
```

### External RTMP Destinations Gating

```dart
class RTMPDestinationManager extends StatefulWidget {
  @override
  State<RTMPDestinationManager> createState() => _RTMPDestinationManagerState();
}

class _RTMPDestinationManagerState extends State<RTMPDestinationManager> {
  final licenseService = LicenseService();
  List<String> rtmpDestinations = [];

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text('External RTMP Destinations',
          style: Theme.of(context).textTheme.titleMedium),
        SizedBox(height: 16),

        // List existing destinations
        ListView.builder(
          itemCount: rtmpDestinations.length,
          itemBuilder: (context, index) {
            return RTMPDestinationTile(
              destination: rtmpDestinations[index],
              onDelete: () => _removeDestination(index),
            );
          },
        ),

        SizedBox(height: 16),

        // Add destination button (premium only)
        FutureBuilder<bool>(
          future: licenseService.canUseFeature('external_rtmp'),
          builder: (context, snapshot) {
            final canUseRTMP = snapshot.data ?? false;

            return ElevatedButton.icon(
              onPressed: canUseRTMP
                  ? () => _showAddDestinationDialog(context)
                  : () => _showPremiumGate(context),
              icon: Icon(Icons.add),
              label: Text('Add RTMP Destination'),
            );
          },
        ),
      ],
    );
  }

  void _showPremiumGate(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => PremiumGateDialog(
        featureName: 'External RTMP Streaming',
        description: 'Upgrade to premium to stream to external RTMP servers',
        onUpgradePressed: () {
          Navigator.pop(context);
          // Navigate to licensing
        },
      ),
    );
  }

  void _showAddDestinationDialog(BuildContext context) {
    // Implementation for adding RTMP destination
  }

  void _removeDestination(int index) {
    setState(() => rtmpDestinations.removeAt(index));
  }
}
```

---

## Server-Side Gating

Hub API enforces premium gating server-side and returns HTTP 402 (Payment Required) for unauthorized features.

### Hub API Integration

The Hub API returns 402 Payment Required when free users attempt premium operations:

```dart
class HubApiClient {
  Future<StreamResponse> startStream(StreamRequest request) async {
    try {
      final response = await _httpClient.post(
        '/api/v1/streams/start',
        headers: {
          'Authorization': 'Bearer $_authToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode(request.toJson()),
      );

      // Handle 402 Payment Required
      if (response.statusCode == 402) {
        throw PremiumFeatureRequiredException(
          featureName: response.headers['X-Required-Feature'] ?? 'Unknown',
          tier: response.headers['X-Required-Tier'] ?? 'premium',
        );
      }

      if (response.statusCode == 401) {
        throw UnauthorizedException();
      }

      if (!response.statusCodeSuccess) {
        throw ApiException(
          statusCode: response.statusCode,
          message: response.body,
        );
      }

      return StreamResponse.fromJson(jsonDecode(response.body));
    } catch (e) {
      rethrow;
    }
  }
}
```

### 402 Response Handler

```dart
class Stream402Handler {
  static void handle(
    BuildContext context,
    PremiumFeatureRequiredException exception,
  ) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Premium Feature Required'),
        content: Text(
          'The feature "${exception.featureName}" requires a ${exception.tier} license. '
          'Please upgrade your account to continue.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              // Navigate to licensing/upgrade flow
              _navigateToUpgrade(context);
            },
            child: Text('Upgrade Now'),
          ),
        ],
      ),
    );
  }
}
```

### Handling 402 in Stream Start

```dart
class StreamController {
  Future<void> startStreaming(StreamConfig config) async {
    try {
      final response = await _hubApi.startStream(
        StreamRequest(
          quality: config.quality,
          mode: config.mode,
          destinations: config.destinations,
        ),
      );

      setState(() => _streamActive = true);
    } on PremiumFeatureRequiredException catch (e) {
      if (!mounted) return;

      // User attempted premium feature without license
      Stream402Handler.handle(context, e);
    } on UnauthorizedException catch (e) {
      // Re-authenticate required
      _navigateToLogin();
    } on ApiException catch (e) {
      _showErrorSnackbar('Stream failed: ${e.message}');
    }
  }
}
```

### Graceful Fallback

When 402 occurs, fall back to free-tier feature set:

```dart
class StreamConfigManager {
  Future<StreamConfig> ensureValidConfig(StreamConfig requested) async {
    try {
      // Attempt requested config
      return await _validate(requested);
    } on PremiumFeatureRequiredException catch (e) {
      // Fall back to free-tier equivalent
      return _getFreeAlternative(requested);
    }
  }

  StreamConfig _getFreeAlternative(StreamConfig config) {
    return StreamConfig(
      quality: '360p', // Downgrade from HD
      mode: 'standard', // Remove overlay
      destinations: [], // Remove external RTMP
      cameras: config.cameras.take(1).toList(), // Single camera
    );
  }
}
```

---

## Integration Patterns

### Pattern 1: Check Features Before Showing UI

```dart
class SettingsScreen extends StatefulWidget {
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final licenseService = LicenseService();
  Map<String, bool> featureAvailability = {};

  @override
  void initState() {
    super.initState();
    _loadFeatureAvailability();
  }

  Future<void> _loadFeatureAvailability() async {
    final features = [
      'hd_streaming',
      'overlay_mode',
      'external_rtmp',
      'multi_camera',
    ];

    final availability = <String, bool>{};
    for (final feature in features) {
      availability[feature] =
        await licenseService.canUseFeature(feature);
    }

    setState(() => featureAvailability = availability);
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        if (featureAvailability['hd_streaming'] ?? false)
          SettingTile(
            title: 'Streaming Quality',
            onTap: () => _showQualitySettings(context),
          ),

        if (featureAvailability['overlay_mode'] ?? false)
          SettingTile(
            title: 'Overlay Settings',
            onTap: () => _showOverlaySettings(context),
          ),

        if (featureAvailability['external_rtmp'] ?? false)
          SettingTile(
            title: 'External Destinations',
            onTap: () => _showDestinationSettings(context),
          ),
      ],
    );
  }
}
```

### Pattern 2: Show Premium Badges on Restricted Features

```dart
class FeatureCard extends StatefulWidget {
  final String title;
  final String featureKey;
  final VoidCallback? onTap;

  const FeatureCard({
    required this.title,
    required this.featureKey,
    this.onTap,
  });

  @override
  State<FeatureCard> createState() => _FeatureCardState();
}

class _FeatureCardState extends State<FeatureCard> {
  final licenseService = LicenseService();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<bool>(
      future: licenseService.canUseFeature(widget.featureKey),
      builder: (context, snapshot) {
        final isAvailable = snapshot.data ?? false;

        return PremiumBadge(
          isPremium: !isAvailable,
          child: GestureDetector(
            onTap: widget.onTap,
            child: Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.title,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    if (!isAvailable)
                      Padding(
                        padding: EdgeInsets.only(top: 8),
                        child: Text(
                          'Premium Feature',
                          style: TextStyle(color: Colors.grey),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
```

### Pattern 3: Handle 402 Responses from API

```dart
class ApiErrorHandler {
  static void handleError(
    BuildContext context,
    dynamic error,
  ) {
    if (error is PremiumFeatureRequiredException) {
      // Premium feature gate
      showDialog(
        context: context,
        builder: (context) => PremiumGateDialog(
          featureName: error.featureName,
          description: 'This feature requires a ${error.tier} license',
          onUpgradePressed: () {
            Navigator.pop(context);
            _navigateToUpgrade(context);
          },
        ),
      );
    } else if (error is ApiException && error.statusCode == 402) {
      // Generic 402 handling
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: Text('Premium Feature'),
          content: Text('Upgrade your account to access this feature'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () => _navigateToUpgrade(context),
              child: Text('Upgrade'),
            ),
          ],
        ),
      );
    } else if (error is UnauthorizedException) {
      // Handle auth error
      _navigateToLogin(context);
    } else {
      // Generic error
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: ${error.toString()}')),
      );
    }
  }
}
```

### Pattern 4: Display License Status in Settings

```dart
class LicenseSettingsScreen extends StatefulWidget {
  @override
  State<LicenseSettingsScreen> createState() => _LicenseSettingsScreenState();
}

class _LicenseSettingsScreenState extends State<LicenseSettingsScreen> {
  final licenseService = LicenseService();
  late StreamSubscription<LicenseStatus> _licenseSubscription;

  @override
  void initState() {
    super.initState();
    _licenseSubscription = licenseService.onLicenseStatusChanged
        .listen((status) {
          setState(() {}); // Rebuild on license change
        });
  }

  @override
  void dispose() {
    _licenseSubscription.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<LicenseStatus>(
      future: licenseService.getLicenseStatus(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return Center(child: CircularProgressIndicator());
        }

        if (snapshot.hasError) {
          return ErrorWidget(
            message: 'Failed to load license status',
            onRetry: () => setState(() {}),
          );
        }

        final status = snapshot.data!;

        return Column(
          children: [
            // License status header
            Container(
              padding: EdgeInsets.all(16),
              color: Colors.grey[100],
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'License Status',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      SizedBox(height: 8),
                      Text(
                        _statusText(status),
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: _statusColor(status),
                        ),
                      ),
                    ],
                  ),
                  LicenseStatusWidget(status: status.tier),
                ],
              ),
            ),
            SizedBox(height: 24),

            // License details
            ListTile(
              title: Text('License Tier'),
              trailing: Text(_tierText(status.tier)),
            ),

            if (status.expiresAt != null)
              ListTile(
                title: Text('Expires'),
                trailing: Text(_formatDate(status.expiresAt!)),
              ),

            if (status.tier == LicenseTier.premium)
              ListTile(
                title: Text('Features'),
                trailing: Text('All Premium Features'),
              ),

            SizedBox(height: 24),

            // Action buttons
            Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (status.tier != LicenseTier.premium)
                    ElevatedButton(
                      onPressed: () => _navigateToUpgrade(context),
                      child: Text('Upgrade to Premium'),
                    ),

                  SizedBox(height: 12),

                  OutlinedButton(
                    onPressed: () => _refreshLicense(),
                    child: Text('Refresh License'),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  String _statusText(LicenseStatus status) {
    switch (status.tier) {
      case LicenseTier.premium:
        return 'Premium';
      case LicenseTier.basic:
        return 'Basic (Free)';
      case LicenseTier.expired:
        return 'Expired';
      default:
        return 'Unknown';
    }
  }

  Color _statusColor(LicenseStatus status) {
    switch (status.tier) {
      case LicenseTier.premium:
        return Colors.green;
      case LicenseTier.basic:
        return Colors.blue;
      case LicenseTier.expired:
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  Future<void> _refreshLicense() async {
    try {
      await licenseService.syncLicenseStatus();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('License updated')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to refresh license')),
      );
    }
  }

  void _navigateToUpgrade(BuildContext context) {
    // Navigate to upgrade flow
  }
}
```

---

## Future Features

Placeholder sections for upcoming premium features and monetization integration.

### Workflow Creation

**Status**: Future implementation

**Free Tier**:
- 1 custom workflow allowed
- Basic triggers and actions
- Limited to single streaming scenario

**Premium Tier**:
- Unlimited custom workflows
- Advanced triggers and conditions
- Scheduled workflows
- Workflow templates marketplace
- Multi-scenario automation

**Implementation Notes**:
```dart
// Future: Check workflow creation limit
final workflowLimit = await licenseService
    .getFeatureLimit('workflow_max');

// Future: Premium workflow features
final canUseScheduling = await licenseService
    .canUseFeature('workflow_scheduling');

final canUseAdvancedTriggers = await licenseService
    .canUseFeature('workflow_advanced_triggers');
```

### Video Proxy Destinations

**Status**: Future implementation

**Free Tier**:
- 3 proxy destinations maximum
- Basic HTTP/RTMP proxy
- Standard bitrate limits

**Premium Tier**:
- 10+ proxy destinations
- Advanced proxy types (HLS, DASH, WebRTC)
- Priority bandwidth allocation
- Geo-redundancy options

**Implementation Notes**:
```dart
// Future: Check proxy destination limit
final proxyLimit = await licenseService
    .getFeatureLimit('proxy_destination_max');

// Future: Premium proxy features
final canUseAdvancedProxy = await licenseService
    .canUseFeature('proxy_advanced_types');

final canUseGeoRedundancy = await licenseService
    .canUseFeature('proxy_geo_redundancy');
```

### Module Marketplace

**Status**: Future implementation

**Description**:
- Community-created modules and filters
- Premium module packages
- Installation and management system

**Premium Features**:
- Access to premium modules
- Priority module availability
- Custom module development support

**Implementation Notes**:
```dart
// Future: Module marketplace access
final canAccessMarketplace = await licenseService
    .canUseFeature('module_marketplace');

final canInstallPremiumModules = await licenseService
    .canUseFeature('module_marketplace_premium');

// Feature gate module installation
if (await licenseService.canUseFeature('module_marketplace')) {
  // Show marketplace UI
}
```

### Payment Processing

**Status**: Future implementation

**Integration Points**:
- Stripe integration for credit card payments
- In-app subscription management
- Receipt and invoice generation
- Payment history and billing portal

**Implementation Notes**:
```dart
// Future: Payment processing service
class PaymentService {
  Future<PaymentResult> createCheckoutSession(
    String productId,
  ) async {
    // Stripe payment session creation
  }

  Future<Subscription> getSubscription() async {
    // Fetch user's active subscription
  }

  Future<void> updatePaymentMethod() async {
    // Update payment method on file
  }
}
```

### Currency System

**Status**: Future implementation

**Features**:
- Multi-currency pricing
- Automatic currency detection
- Localized pricing display
- Currency conversion caching

**Supported Currencies**: USD, EUR, GBP, JPY, AUD, CAD, more

**Implementation Notes**:
```dart
// Future: Currency configuration
class CurrencyService {
  Future<String> getLocalizedPrice(
    String productId,
  ) async {
    // Get price in user's local currency
  }

  Future<List<String>> getSupportedCurrencies() async {
    // Get list of supported currencies
  }

  String formatPrice(double amount, String currency) {
    // Format amount with currency symbol
  }
}
```

### Raffles & Giveaways

**Status**: Future implementation

**Features**:
- Periodic premium license giveaways
- Community participation raffles
- Referral rewards program
- Free trial period codes

**Implementation Notes**:
```dart
// Future: Raffle and giveaway system
class RaffleService {
  Future<List<Raffle>> getActiveRaffles() async {
    // Fetch active raffles and giveaways
  }

  Future<void> enterRaffle(String raffleId) async {
    // Enter user into raffle
  }

  Future<RaffleEntry?> checkWinnerStatus() async {
    // Check if user won any active raffles
  }

  Future<void> redeemPrizeCode(String code) async {
    // Redeem premium license code
  }
}
```

### Referral Program

**Status**: Future implementation

**Structure**:
- Earn free premium months by referring friends
- Referral tracking and statistics
- Bonus rewards for milestones

**Implementation Notes**:
```dart
// Future: Referral program service
class ReferralService {
  Future<String> generateReferralCode() async {
    // Generate unique referral code
  }

  Future<ReferralStats> getReferralStats() async {
    // Get referral performance metrics
  }

  Future<void> shareReferralLink() async {
    // Share referral link via social/messaging
  }
}
```

---

## Summary

This guide provides a comprehensive framework for implementing premium gating in Flutter Gazer:

1. **Client-Side**: Immediate UI feedback and feature availability checking
2. **Server-Side**: Business logic enforcement and 402 payment-required responses
3. **Widgets**: Reusable UI components for premium gates and status display
4. **Patterns**: Common integration scenarios with code examples
5. **Future**: Placeholder sections for upcoming monetization features

For questions or integration support, refer to the main Waddles project documentation or contact the development team.
