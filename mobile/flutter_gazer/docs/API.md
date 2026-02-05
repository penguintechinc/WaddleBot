# Flutter Gazer API Reference

Complete API documentation for Waddles Gazer services, models, widgets, and platform channels.

## Table of Contents

1. [Service APIs](#service-apis)
2. [Model Classes](#model-classes)
3. [Widget APIs](#widget-apis)
4. [Platform Channels](#platform-channels)
5. [Error Handling](#error-handling)
6. [Code Examples](#code-examples)

---

## Service APIs

### WaddleBotService

Main API client for all backend communication.

**Import**: `package:gazer_waddlebot/services/waddlebot_service.dart`

#### Constructor

```dart
WaddleBotService({
  required String baseUrl,
  required String licenseServerUrl,
  Duration timeout = const Duration(seconds: 30),
})
```

#### Authentication Methods

##### `login(String username, String password)`

Authenticate user with credentials.

```dart
Future<LoginResponse> login(String username, String password)
```

**Parameters:**
- `username` (String): User's email or username
- `password` (String): User's password

**Returns:** `LoginResponse` containing JWT token and user info

**Throws:** `DioException` on network error

**Example:**
```dart
try {
  final response = await waddleBotService.login('user@example.com', 'password123');
  final token = response.token;
  final user = response.user;
} on DioException catch (e) {
  print('Login failed: ${e.message}');
}
```

##### `logout()`

Sign out user and invalidate token.

```dart
Future<void> logout()
```

**Returns:** Future that completes when logout is complete

**Example:**
```dart
await waddleBotService.logout();
```

##### `refreshToken()`

Refresh JWT token before expiry.

```dart
Future<String> refreshToken()
```

**Returns:** New JWT token

**Throws:** `DioException` if refresh fails

**Example:**
```dart
final newToken = await waddleBotService.refreshToken();
```

#### Streaming Methods

##### `startStream(StreamSettings settings)`

Start a new stream.

```dart
Future<StreamResponse> startStream(StreamSettings settings)
```

**Parameters:**
- `settings` (StreamSettings): Stream configuration

**Returns:** `StreamResponse` with stream ID and connection details

**Throws:** `DioException`, `ValidationException`

**Example:**
```dart
final response = await waddleBotService.startStream(
  StreamSettings(
    url: 'rtmp://example.com/live',
    key: 'stream-key',
    bitrate: 5000,
    resolution: Resolution.r720p,
    frameRate: 30,
  ),
);
print('Stream ID: ${response.streamId}');
```

##### `stopStream(String streamId)`

Stop active stream.

```dart
Future<void> stopStream(String streamId)
```

**Parameters:**
- `streamId` (String): ID of stream to stop

**Returns:** Future that completes when stream is stopped

**Example:**
```dart
await waddleBotService.stopStream('stream-123');
```

##### `getStreamStatus(String streamId)`

Get current stream status.

```dart
Future<StreamStatus> getStreamStatus(String streamId)
```

**Parameters:**
- `streamId` (String): ID of stream

**Returns:** `StreamStatus` with current state and metrics

**Example:**
```dart
final status = await waddleBotService.getStreamStatus('stream-123');
print('Bitrate: ${status.bitrate} kbps');
print('Viewers: ${status.viewerCount}');
```

#### Community Methods

##### `getCommunities({int page = 1, int limit = 20})`

Fetch list of available communities.

```dart
Future<List<Community>> getCommunities({int page = 1, int limit = 20})
```

**Parameters:**
- `page` (int): Page number for pagination
- `limit` (int): Results per page

**Returns:** List of `Community` objects

**Example:**
```dart
final communities = await waddleBotService.getCommunities(page: 1, limit: 10);
for (var community in communities) {
  print('${community.name} - ${community.memberCount} members');
}
```

##### `getCommunityDetail(String id)`

Get detailed community information.

```dart
Future<Community> getCommunityDetail(String id)
```

**Parameters:**
- `id` (String): Community ID

**Returns:** `Community` object with full details

**Example:**
```dart
final community = await waddleBotService.getCommunityDetail('community-123');
print('Description: ${community.description}');
print('Owner: ${community.owner.username}');
```

##### `joinCommunity(String id)`

Join a community.

```dart
Future<void> joinCommunity(String id)
```

**Parameters:**
- `id` (String): Community ID

**Returns:** Future that completes when joined

**Example:**
```dart
await waddleBotService.joinCommunity('community-123');
print('Successfully joined community');
```

##### `leaveCommunity(String id)`

Leave a community.

```dart
Future<void> leaveCommunity(String id)
```

**Parameters:**
- `id` (String): Community ID

**Returns:** Future that completes when left

**Example:**
```dart
await waddleBotService.leaveCommunity('community-123');
```

#### Member Methods

##### `getMembers(String communityId, {int page = 1, int limit = 50})`

Fetch community members.

```dart
Future<List<Member>> getMembers(
  String communityId, {
  int page = 1,
  int limit = 50,
})
```

**Parameters:**
- `communityId` (String): Community ID
- `page` (int): Page number
- `limit` (int): Results per page

**Returns:** List of `Member` objects

**Example:**
```dart
final members = await waddleBotService.getMembers('community-123');
for (var member in members) {
  print('${member.username} (${member.role})');
}
```

##### `getMemberDetail(String memberId)`

Get detailed member profile.

```dart
Future<Member> getMemberDetail(String memberId)
```

**Parameters:**
- `memberId` (String): Member ID

**Returns:** `Member` object with full profile

**Example:**
```dart
final member = await waddleBotService.getMemberDetail('member-456');
print('Joined: ${member.joinedAt}');
print('Role: ${member.role}');
```

#### Settings Methods

##### `getUserSettings()`

Get user settings and preferences.

```dart
Future<UserSettings> getUserSettings()
```

**Returns:** `UserSettings` object

**Example:**
```dart
final settings = await waddleBotService.getUserSettings();
print('Theme: ${settings.theme}');
print('Notifications: ${settings.notificationsEnabled}');
```

##### `updateSettings(UserSettings settings)`

Update user settings.

```dart
Future<void> updateSettings(UserSettings settings)
```

**Parameters:**
- `settings` (UserSettings): Updated settings

**Returns:** Future that completes when updated

**Example:**
```dart
await waddleBotService.updateSettings(
  UserSettings(
    theme: 'dark',
    notificationsEnabled: true,
    volumeLevel: 80,
  ),
);
```

### RTMPService

Manages RTMP streaming connections and broadcast control.

**Import**: `package:gazer_waddlebot/services/rtmp_service.dart`

#### Constructor

```dart
RTMPService({
  required String serverUrl,
  Duration connectionTimeout = const Duration(seconds: 10),
})
```

#### Connection Methods

##### `connect(String rtmpUrl, String key)`

Establish RTMP connection.

```dart
Future<void> connect(String rtmpUrl, String key)
```

**Parameters:**
- `rtmpUrl` (String): RTMP server URL (e.g., 'rtmp://live.example.com/live')
- `key` (String): Stream key

**Returns:** Future that completes when connected

**Throws:** `RTMPException`

**Example:**
```dart
try {
  await rtmpService.connect(
    'rtmp://live.youtube.com/rtmp',
    'your-stream-key',
  );
  print('Connected to RTMP server');
} on RTMPException catch (e) {
  print('Connection failed: ${e.message}');
}
```

##### `disconnect()`

Close RTMP connection.

```dart
Future<void> disconnect()
```

**Returns:** Future that completes when disconnected

**Example:**
```dart
await rtmpService.disconnect();
```

##### `isConnected`

Check connection status.

```dart
bool get isConnected
```

**Returns:** `true` if connected, `false` otherwise

**Example:**
```dart
if (rtmpService.isConnected) {
  print('RTMP connection is active');
}
```

#### Broadcast Methods

##### `startBroadcast(StreamSettings settings)`

Start broadcasting.

```dart
Future<void> startBroadcast(StreamSettings settings)
```

**Parameters:**
- `settings` (StreamSettings): Broadcast settings

**Returns:** Future that completes when broadcast starts

**Example:**
```dart
await rtmpService.startBroadcast(
  StreamSettings(
    bitrate: 5000,
    resolution: Resolution.r720p,
    frameRate: 30,
  ),
);
```

##### `stopBroadcast()`

Stop broadcasting.

```dart
Future<void> stopBroadcast()
```

**Returns:** Future that completes when stopped

**Example:**
```dart
await rtmpService.stopBroadcast();
```

##### `updateBitrate(int bitrate)`

Dynamically update bitrate during broadcast.

```dart
Future<void> updateBitrate(int bitrate)
```

**Parameters:**
- `bitrate` (int): New bitrate in kbps

**Returns:** Future that completes when updated

**Example:**
```dart
await rtmpService.updateBitrate(8000); // 8 Mbps
```

#### Status Monitoring

##### `statusUpdates`

Stream of RTMP status updates.

```dart
Stream<RTMPStatus> get statusUpdates
```

**Returns:** Stream of `RTMPStatus` events

**Example:**
```dart
rtmpService.statusUpdates.listen((status) {
  print('Bitrate: ${status.bitrate} kbps');
  print('Viewers: ${status.viewerCount}');
});
```

### USBCaptureService

Platform channel interface for USB capture devices.

**Import**: `package:gazer_waddlebot/services/usb_capture_service.dart`

#### Device Discovery

##### `getAvailableDevices()`

Get list of connected USB capture devices.

```dart
Future<List<USBDevice>> getAvailableDevices()
```

**Returns:** List of `USBDevice` objects

**Example:**
```dart
final devices = await usbCaptureService.getAvailableDevices();
for (var device in devices) {
  print('${device.name} - ${device.vendorId}:${device.productId}');
}
```

##### `getDeviceInfo(String deviceId)`

Get detailed device information.

```dart
Future<USBDeviceInfo> getDeviceInfo(String deviceId)
```

**Parameters:**
- `deviceId` (String): USB device ID

**Returns:** `USBDeviceInfo` with detailed specs

**Example:**
```dart
final info = await usbCaptureService.getDeviceInfo('device-123');
print('Resolution: ${info.maxResolution}');
print('Frame rate: ${info.maxFrameRate} fps');
```

#### Device Control

##### `selectDevice(String deviceId)`

Select USB device for capture.

```dart
Future<void> selectDevice(String deviceId)
```

**Parameters:**
- `deviceId` (String): Device ID to select

**Returns:** Future that completes when selected

**Example:**
```dart
await usbCaptureService.selectDevice('device-123');
```

##### `startCapture(CaptureSettings settings)`

Start capturing from selected device.

```dart
Future<void> startCapture(CaptureSettings settings)
```

**Parameters:**
- `settings` (CaptureSettings): Capture configuration

**Returns:** Future that completes when capture starts

**Example:**
```dart
await usbCaptureService.startCapture(
  CaptureSettings(
    resolution: Resolution.r1080p,
    frameRate: 60,
    bitrate: 10000,
  ),
);
```

##### `stopCapture()`

Stop capturing.

```dart
Future<void> stopCapture()
```

**Returns:** Future that completes when capture stops

**Example:**
```dart
await usbCaptureService.stopCapture();
```

#### Configuration

##### `setResolution(Resolution resolution)`

Set capture resolution.

```dart
Future<void> setResolution(Resolution resolution)
```

**Parameters:**
- `resolution` (Resolution): Target resolution

**Returns:** Future that completes when set

**Example:**
```dart
await usbCaptureService.setResolution(Resolution.r1080p);
```

##### `setFrameRate(int fps)`

Set capture frame rate.

```dart
Future<void> setFrameRate(int fps)
```

**Parameters:**
- `fps` (int): Frames per second

**Returns:** Future that completes when set

**Example:**
```dart
await usbCaptureService.setFrameRate(60);
```

##### `setBitrate(int bitrate)`

Set capture bitrate.

```dart
Future<void> setBitrate(int bitrate)
```

**Parameters:**
- `bitrate` (int): Bitrate in kbps

**Returns:** Future that completes when set

**Example:**
```dart
await usbCaptureService.setBitrate(15000); // 15 Mbps
```

#### Event Streaming

##### `captureEvents`

Stream of capture events.

```dart
Stream<CaptureEvent> get captureEvents
```

**Returns:** Stream of `CaptureEvent` notifications

**Example:**
```dart
usbCaptureService.captureEvents.listen((event) {
  if (event.type == CaptureEventType.frameDropped) {
    print('Frame dropped: ${event.message}');
  }
});
```

---

## Model Classes

### User

User profile and authentication data.

```dart
class User {
  final String id;
  final String username;
  final String email;
  final String? avatarUrl;
  final LicenseTier licenseTier;
  final DateTime createdAt;
  final DateTime? lastLogin;

  User({
    required this.id,
    required this.username,
    required this.email,
    this.avatarUrl,
    required this.licenseTier,
    required this.createdAt,
    this.lastLogin,
  });

  factory User.fromJson(Map<String, dynamic> json) => User(...);
  Map<String, dynamic> toJson() => {...};
}
```

### Community

Community information and metadata.

```dart
class Community {
  final String id;
  final String name;
  final String? description;
  final String? thumbnailUrl;
  final User owner;
  final int memberCount;
  final DateTime createdAt;
  final List<String> tags;

  Community({
    required this.id,
    required this.name,
    this.description,
    this.thumbnailUrl,
    required this.owner,
    required this.memberCount,
    required this.createdAt,
    required this.tags,
  });

  factory Community.fromJson(Map<String, dynamic> json) => Community(...);
}
```

### Member

Community member information.

```dart
class Member {
  final String id;
  final String username;
  final String? avatarUrl;
  final MemberRole role;
  final DateTime joinedAt;
  final int postCount;
  final bool isOnline;

  Member({
    required this.id,
    required this.username,
    this.avatarUrl,
    required this.role,
    required this.joinedAt,
    required this.postCount,
    required this.isOnline,
  });

  factory Member.fromJson(Map<String, dynamic> json) => Member(...);
}

enum MemberRole { owner, admin, moderator, member, viewer }
```

### StreamSettings

Streaming configuration parameters.

```dart
class StreamSettings {
  final String url;
  final String key;
  final int bitrate;
  final Resolution resolution;
  final int frameRate;
  final String? title;
  final String? description;

  StreamSettings({
    required this.url,
    required this.key,
    required this.bitrate,
    required this.resolution,
    required this.frameRate,
    this.title,
    this.description,
  });

  factory StreamSettings.fromJson(Map<String, dynamic> json) => StreamSettings(...);
  Map<String, dynamic> toJson() => {...};
}

enum Resolution { r480p, r720p, r1080p, r2k, r4k }
```

### LicenseInfo

License tier and feature information.

```dart
class LicenseInfo {
  final LicenseTier tier;
  final DateTime expiresAt;
  final int maxStreams;
  final int maxBitrate;
  final int maxWorkflows;
  final List<String> enabledFeatures;

  LicenseInfo({
    required this.tier,
    required this.expiresAt,
    required this.maxStreams,
    required this.maxBitrate,
    required this.maxWorkflows,
    required this.enabledFeatures,
  });

  bool get isExpired => DateTime.now().isAfter(expiresAt);
  bool hasFeature(String feature) => enabledFeatures.contains(feature);

  factory LicenseInfo.fromJson(Map<String, dynamic> json) => LicenseInfo(...);
}

enum LicenseTier { free, premium, pro, enterprise }
```

### StreamStatus

Real-time streaming metrics.

```dart
class StreamStatus {
  final String streamId;
  final StreamState state;
  final int bitrate; // current bitrate in kbps
  final int viewerCount;
  final Duration uptime;
  final double cpuUsage;
  final int droppedFrames;
  final DateTime lastUpdate;

  StreamStatus({
    required this.streamId,
    required this.state,
    required this.bitrate,
    required this.viewerCount,
    required this.uptime,
    required this.cpuUsage,
    required this.droppedFrames,
    required this.lastUpdate,
  });

  factory StreamStatus.fromJson(Map<String, dynamic> json) => StreamStatus(...);
}

enum StreamState { idle, connecting, streaming, paused, error, stopped }
```

### RTMPStatus

RTMP connection status and metrics.

```dart
class RTMPStatus {
  final bool isConnected;
  final int bitrate; // kbps
  final int fps;
  final Duration connectionDuration;
  final String? error;
  final DateTime lastUpdate;

  RTMPStatus({
    required this.isConnected,
    required this.bitrate,
    required this.fps,
    required this.connectionDuration,
    this.error,
    required this.lastUpdate,
  });
}
```

### USBDevice

USB capture device information.

```dart
class USBDevice {
  final String id;
  final String name;
  final int vendorId;
  final int productId;
  final String? serialNumber;
  final String? manufacturer;

  USBDevice({
    required this.id,
    required this.name,
    required this.vendorId,
    required this.productId,
    this.serialNumber,
    this.manufacturer,
  });

  factory USBDevice.fromJson(Map<String, dynamic> json) => USBDevice(...);
}

class USBDeviceInfo extends USBDevice {
  final Resolution maxResolution;
  final int maxFrameRate;
  final int maxBitrate;
  final List<String> supportedResolutions;

  USBDeviceInfo({
    required String id,
    required String name,
    required int vendorId,
    required int productId,
    String? serialNumber,
    String? manufacturer,
    required this.maxResolution,
    required this.maxFrameRate,
    required this.maxBitrate,
    required this.supportedResolutions,
  }) : super(
    id: id,
    name: name,
    vendorId: vendorId,
    productId: productId,
    serialNumber: serialNumber,
    manufacturer: manufacturer,
  );

  factory USBDeviceInfo.fromJson(Map<String, dynamic> json) => USBDeviceInfo(...);
}
```

---

## Widget APIs

### PremiumGateDialog

Upgrade prompt dialog for premium features.

**Import**: `package:gazer_waddlebot/widgets/premium_gate_dialog.dart`

#### Properties

```dart
class PremiumGateDialog extends StatefulWidget {
  final String featureName;
  final String? featureDescription;
  final LicenseTier currentTier;
  final LicenseTier requiredTier;
  final List<String>? upgradeBenefits;
  final String? pricingUrl;
  final VoidCallback? onUpgradePressed;
  final VoidCallback? onDismissed;

  const PremiumGateDialog({
    required this.featureName,
    this.featureDescription,
    required this.currentTier,
    required this.requiredTier,
    this.upgradeBenefits,
    this.pricingUrl,
    this.onUpgradePressed,
    this.onDismissed,
  });
}
```

#### Static Methods

##### `show()`

Display the dialog.

```dart
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
})
```

**Example:**
```dart
await PremiumGateDialog.show(
  context,
  featureName: 'External RTMP Streaming',
  featureDescription: 'Stream to external RTMP servers',
  currentTier: LicenseTier.free,
  requiredTier: LicenseTier.pro,
  upgradeBenefits: [
    'Stream to external RTMP endpoints',
    'Multiple simultaneous streams',
    'Advanced bitrate control',
  ],
  pricingUrl: 'https://www.penguintech.io/pricing',
  onUpgradePressed: () => _handleUpgrade(),
);
```

### LicenseStatusWidget

Display current license tier and usage.

**Import**: `package:gazer_waddlebot/widgets/license_status_widget.dart`

#### Properties

```dart
class LicenseStatusWidget extends StatefulWidget {
  final LicenseInfo licenseInfo;
  final int? currentWorkflows;
  final VoidCallback? onExpand;
  final bool showExpiration;
  final bool compact;
  final Color? backgroundColor;
  final Color? tierTextColor;

  const LicenseStatusWidget({
    required this.licenseInfo,
    this.currentWorkflows,
    this.onExpand,
    this.showExpiration = true,
    this.compact = false,
    this.backgroundColor,
    this.tierTextColor,
  });
}
```

#### Usage

```dart
// Expandable widget
LicenseStatusWidget(
  licenseInfo: licenseService.currentLicense!,
  currentWorkflows: activeWorkflows,
  showExpiration: true,
  onExpand: () => print('Expanded'),
)

// Compact inline display
LicenseStatusWidget(
  licenseInfo: licenseService.currentLicense!,
  compact: true,
  backgroundColor: Colors.grey[900],
)
```

### PremiumBadge

Visual indicator for premium features.

**Import**: `package:gazer_waddlebot/widgets/premium_badge.dart`

#### Properties

```dart
class PremiumBadge extends StatelessWidget {
  final String size; // 'small', 'medium', 'large'
  final String label;
  final String? tooltip;
  final Color? backgroundColor;
  final Color? textColor;
  final VoidCallback? onTap;
  final bool showIcon;
  final bool interactive;

  const PremiumBadge({
    this.size = 'medium',
    this.label = 'PRO',
    this.tooltip,
    this.backgroundColor,
    this.textColor,
    this.onTap,
    this.showIcon = true,
    this.interactive = false,
  });
}
```

#### Static Methods

```dart
PremiumBadge.small()     // Small badge (10px font)
PremiumBadge.medium()    // Medium badge (12px font)
PremiumBadge.large()     // Large badge (13px font)
PremiumBadge.custom()    // Custom colors
```

#### Widget Extension

```dart
// Add premium badge to any widget
FloatingActionButton(
  onPressed: () {},
  child: Icon(Icons.videocam),
).withPremiumBadge(
  label: 'PRO',
  tooltip: 'Pro tier feature',
  size: 'medium',
)
```

---

## Platform Channels

### Android (Kotlin)

**Channel ID**: `com.penguintech.gazer/usb_capture`

#### Available Methods

##### `getDevices`

Get list of connected USB devices.

**Parameters:** None

**Returns:**
```dart
List<Map<String, dynamic>> [
  {
    'id': 'device-123',
    'name': 'USB Video Capture Device',
    'vendor_id': 1234,
    'product_id': 5678,
    'serial_number': 'ABC123',
    'manufacturer': 'Acme Corp',
  },
]
```

**Example:**
```dart
const platform = MethodChannel('com.penguintech.gazer/usb_capture');
final List<dynamic> devices = await platform.invokeMethod('getDevices');
```

##### `selectDevice`

Select USB device for capture.

**Parameters:**
```dart
{
  'device_id': 'device-123',
}
```

**Returns:** null

**Example:**
```dart
await platform.invokeMethod('selectDevice', {'device_id': 'device-123'});
```

##### `startCapture`

Start capturing from device.

**Parameters:**
```dart
{
  'resolution': '1080p',
  'frame_rate': 30,
  'bitrate': 5000,
}
```

**Returns:** null

##### `stopCapture`

Stop capturing.

**Parameters:** None

**Returns:** null

### iOS (Swift)

**Channel ID**: Same as Android

Platform channel implementation similar to Android with native Swift code.

---

## Error Handling

### Exception Types

```dart
// Network errors
class NetworkException implements Exception {
  final String message;
  final int? statusCode;

  NetworkException(this.message, [this.statusCode]);
}

// RTMP connection errors
class RTMPException implements Exception {
  final String message;
  final RTMPErrorCode code;

  RTMPException(this.message, this.code);
}

// USB capture errors
class USBCaptureException implements Exception {
  final String message;
  final USBErrorCode code;

  USBCaptureException(this.message, this.code);
}

// License validation errors
class LicenseException implements Exception {
  final String message;

  LicenseException(this.message);
}
```

### Error Codes

```dart
enum RTMPErrorCode {
  connectionFailed,
  invalidUrl,
  authenticationFailed,
  networkTimeout,
  unknownError,
}

enum USBErrorCode {
  deviceNotFound,
  permissionDenied,
  deviceBusy,
  invalidSettings,
  captureFailure,
}
```

---

## Code Examples

### Complete Streaming Workflow

```dart
class StreamingExample {
  late WaddlesService apiService;
  late RTMPService rtmpService;
  late USBCaptureService captureService;
  late StreamingController streamingController;

  Future<void> setupAndStream() async {
    // 1. Start USB capture
    final devices = await captureService.getAvailableDevices();
    if (devices.isEmpty) {
      print('No USB devices found');
      return;
    }

    await captureService.selectDevice(devices[0].id);
    await captureService.startCapture(
      CaptureSettings(
        resolution: Resolution.r1080p,
        frameRate: 60,
        bitrate: 10000,
      ),
    );

    // 2. Create stream on backend
    final streamResponse = await apiService.startStream(
      StreamSettings(
        url: 'rtmp://live.example.com/live',
        key: 'my-stream-key',
        bitrate: 5000,
        resolution: Resolution.r1080p,
        frameRate: 30,
      ),
    );

    // 3. Connect RTMP and start broadcasting
    await rtmpService.connect(streamResponse.rtmpUrl, streamResponse.key);
    await rtmpService.startBroadcast(
      StreamSettings(
        bitrate: 5000,
        resolution: Resolution.r1080p,
        frameRate: 30,
      ),
    );

    // 4. Monitor status
    rtmpService.statusUpdates.listen((status) {
      print('Bitrate: ${status.bitrate} kbps');
      print('Viewers: ${status.viewerCount}');
    });

    // 5. Stop when done
    await Future.delayed(Duration(minutes: 30));
    await rtmpService.stopBroadcast();
    await captureService.stopCapture();
    await apiService.stopStream(streamResponse.streamId);
  }
}
```

### Premium Feature Gating

```dart
Future<void> startExternalStreaming(BuildContext context) async {
  final hasAccess = await licenseService.checkFeatureAccess('externalStreaming');

  if (!hasAccess) {
    await PremiumGateDialog.show(
      context,
      featureName: 'External RTMP Streaming',
      featureDescription: 'Stream to external platforms like YouTube Live',
      currentTier: licenseService.currentLicense!.tier,
      requiredTier: LicenseTier.pro,
      upgradeBenefits: [
        'Stream to multiple RTMP endpoints',
        'Advanced bitrate control',
        'Priority streaming support',
        '99.9% uptime SLA',
      ],
      pricingUrl: 'https://www.penguintech.io/pricing',
      onUpgradePressed: () => launchUrl(Uri.parse('https://www.penguintech.io/pricing')),
    );
    return;
  }

  // Proceed with streaming
  await streamingController.startStream(settings);
}
```

### License Status Display in Settings

```dart
class SettingsPage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Settings')),
      body: ListView(
        children: [
          Padding(
            padding: EdgeInsets.all(16),
            child: Consumer<LicenseController>(
              builder: (context, licenseCtrl, _) {
                if (licenseCtrl.license == null) {
                  return Center(child: CircularProgressIndicator());
                }

                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'License Information',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    SizedBox(height: 16),
                    LicenseStatusWidget(
                      licenseInfo: licenseCtrl.license!,
                      currentWorkflows: licenseCtrl.activeWorkflows,
                      showExpiration: true,
                      onExpand: () => print('Expanded'),
                    ),
                    SizedBox(height: 24),
                    ElevatedButton.icon(
                      onPressed: () => launchUrl(
                        Uri.parse('https://www.penguintech.io/pricing'),
                      ),
                      icon: Icon(Icons.upgrade),
                      label: Text('Upgrade License'),
                    ).withPremiumBadge(
                      label: 'UPGRADE',
                      size: 'medium',
                    ),
                  ],
                );
              },
            ),
          ),
          // More settings...
        ],
      ),
    );
  }
}
```

---

**API Version**: 2.1.0
**Last Updated**: 2026-01-30
**Product**: Waddles Gazer
