# Flutter Gazer Architecture Guide

## Overview

Waddles Gazer follows a layered architecture pattern with clear separation of concerns:

```
┌─────────────────────────────────────────────────┐
│           UI Layer (Screens & Widgets)          │
│                                                 │
│  ├─ Auth Screens    ├─ Streaming Screens       │
│  ├─ Chat Screens    ├─ Community Screens       │
│  └─ Settings        └─ Member Management       │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│      State Management Layer (Provider)          │
│                                                 │
│  ├─ AuthController         ├─ StreamingCtrl     │
│  ├─ CommunityController    ├─ ChatController    │
│  └─ SettingsController     └─ MemberController  │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│         Service Layer (Business Logic)          │
│                                                 │
│  ├─ WaddleBotService       ├─ RTMPService       │
│  ├─ USBCaptureService      ├─ CommunityService  │
│  ├─ MemberService          └─ SettingsService   │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│       Data Layer (Models & Storage)             │
│                                                 │
│  ├─ REST API (Dio)         ├─ LocalStorage      │
│  ├─ Socket.io Events       └─ SecureStorage     │
│  └─ Platform Channels                          │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│         Platform Layer (Native Code)            │
│                                                 │
│  ├─ Kotlin (Android)       ├─ Swift (iOS)       │
│  └─ USB Capture            └─ Camera Access     │
└─────────────────────────────────────────────────┘
```

## Architecture Layers

### 1. Presentation Layer (UI)

#### Screens (`lib/screens/`)

**Authentication Screens** (`lib/screens/auth/`)
- `LoginScreen` - User authentication interface
- Handles login flow and token management

**Streaming Screens** (`lib/screens/streaming/`)
- `StreamingPreview` - Live preview during streaming
- `StreamSetup` - Configure RTMP/streaming parameters
- `QualityPresets` - Select video quality (480p, 720p, 1080p)

**Community Screens** (`lib/screens/communities/`)
- `CommunityList` - Browse available communities
- `CommunityDetail` - View community information and chat

**Chat Screens** (`lib/screens/chat/`)
- `ChatScreen` - Real-time chat interface
- `ChannelList` - Available channels in community

**Member Screens** (`lib/screens/members/`)
- `MemberList` - Directory of community members
- `MemberDetail` - Individual member profiles

**Settings Screens** (`lib/screens/settings/`)
- `SettingsScreen` - User preferences and app configuration
- License tier display and upgrade prompts

**Main Shell** (`lib/screens/main_screen.dart`)
- Root navigation container
- Bottom navigation for major sections

#### Widgets (`lib/widgets/`)

**Premium Feature Widgets**
- `PremiumGateDialog` - Upgrade prompt for restricted features
- `LicenseStatusWidget` - Display current license tier and usage
- `PremiumBadge` - Visual indicator for premium features

**Feature-Specific Widgets**
- `StreamQualitySelector` - Quality selection dropdown
- `RTMPConfigForm` - RTMP server configuration form
- `USBCaptureSelector` - USB device selection
- `StreamStats` - Real-time streaming statistics

### 2. State Management Layer

Uses **Provider** package for reactive state management.

#### Controllers (`*_controller.dart`)

**AuthController**
```dart
class AuthController extends ChangeNotifier {
  String? _token;
  User? _currentUser;
  bool _isLoading = false;

  // Public getters
  bool get isAuthenticated => _token != null;
  User? get currentUser => _currentUser;
  bool get isLoading => _isLoading;

  // Methods
  Future<void> login(String username, String password);
  Future<void> logout();
  Future<void> refreshToken();
}
```

**StreamingController**
```dart
class StreamingController extends ChangeNotifier {
  StreamSettings? _streamSettings;
  StreamState _state = StreamState.idle;
  RTMPConnection? _connection;

  // Public getters
  StreamSettings? get settings => _streamSettings;
  StreamState get state => _state;

  // Methods
  Future<void> startStream(StreamSettings settings);
  Future<void> stopStream();
  Future<void> updateBitrate(int bitrate);
}
```

**CommunityController**
```dart
class CommunityController extends ChangeNotifier {
  List<Community> _communities = [];
  Community? _selectedCommunity;
  bool _isLoading = false;

  // Public getters
  List<Community> get communities => _communities;
  Community? get selectedCommunity => _selectedCommunity;

  // Methods
  Future<void> loadCommunities();
  Future<void> selectCommunity(String id);
  Future<void> joinCommunity(String id);
}
```

**Provider Registration** (`lib/config/providers.dart`)
```dart
final providers = [
  ChangeNotifierProvider(create: (_) => AuthController()),
  ChangeNotifierProvider(create: (_) => StreamingController()),
  ChangeNotifierProvider(create: (_) => CommunityController()),
  ChangeNotifierProvider(create: (_) => ChatController()),
  ChangeNotifierProvider(create: (_) => MemberController()),
];
```

### 3. Service Layer

Services implement business logic and interface with external systems.

#### WaddleBotService (`lib/services/waddlebot_service.dart`)

Main API client for all backend communication:

```dart
class WaddleBotService {
  final Dio _dio;
  final String _baseUrl;
  late String _token;

  // Authentication
  Future<LoginResponse> login(String username, String password);
  Future<void> logout();
  Future<String> refreshToken();

  // Streaming
  Future<StreamResponse> startStream(StreamSettings settings);
  Future<void> stopStream(String streamId);
  Future<StreamStatus> getStreamStatus(String streamId);

  // Communities
  Future<List<Community>> getCommunities();
  Future<Community> getCommunityDetail(String id);
  Future<void> joinCommunity(String id);
  Future<void> leaveCommunity(String id);

  // Members
  Future<List<Member>> getMembers(String communityId);
  Future<Member> getMemberDetail(String id);

  // Settings
  Future<UserSettings> getUserSettings();
  Future<void> updateSettings(UserSettings settings);
}
```

#### RTMPService (`lib/services/rtmp_service.dart`)

Manages RTMP streaming connections:

```dart
class RTMPService {
  late RTMPConnection _connection;
  StreamController<RTMPStatus> statusStream = StreamController();

  // Connection management
  Future<void> connect(String rtmpUrl, String key);
  Future<void> disconnect();
  bool get isConnected => _connection?.isConnected ?? false;

  // Streaming control
  Future<void> startBroadcast(StreamSettings settings);
  Future<void> stopBroadcast();
  Future<void> updateBitrate(int bitrate);

  // Status monitoring
  Stream<RTMPStatus> get statusUpdates => statusStream.stream;
}
```

#### USBCaptureService (`lib/services/usb_capture_service.dart`)

Platform channel interface for USB capture devices:

```dart
class USBCaptureService {
  static const platform = MethodChannel('com.penguintech.gazer/usb_capture');

  // Device discovery
  Future<List<USBDevice>> getAvailableDevices();
  Future<USBDeviceInfo> getDeviceInfo(String deviceId);

  // Device control
  Future<void> selectDevice(String deviceId);
  Future<void> startCapture(CaptureSettings settings);
  Future<void> stopCapture();

  // Configuration
  Future<void> setResolution(Resolution resolution);
  Future<void> setFrameRate(int fps);
  Future<void> setBitrate(int bitrate);

  // Events
  Stream<CaptureEvent> get captureEvents;
}
```

#### CommunityService (`lib/services/community_service.dart`)

Community-specific API operations:

```dart
class CommunityService {
  final WaddleBotService _apiService;

  Future<List<Community>> listCommunities({int page = 1, int limit = 20});
  Future<Community> getCommunity(String id);
  Future<void> joinCommunity(String id);
  Future<void> leaveCommunity(String id);
  Future<List<Channel>> getChannels(String communityId);
  Future<void> selectChannel(String communityId, String channelId);
}
```

#### MemberService (`lib/services/member_service.dart`)

Member management and profile operations:

```dart
class MemberService {
  final WaddleBotService _apiService;

  Future<List<Member>> getMembers(String communityId, {int page = 1});
  Future<Member> getMemberProfile(String memberId);
  Future<void> updateProfile(Member member);
  Future<List<Member>> searchMembers(String query, String communityId);
  Future<void> blockMember(String memberId);
}
```

#### SettingsService (`lib/services/settings_service.dart`)

Local and cloud settings management:

```dart
class SettingsService {
  final SharedPreferences _prefs;
  final FlutterSecureStorage _secureStorage;

  // Local settings
  void setSetting(String key, dynamic value);
  dynamic getSetting(String key, {dynamic defaultValue});

  // Secure storage
  Future<void> storeSecureData(String key, String value);
  Future<String?> retrieveSecureData(String key);

  // Cloud sync
  Future<void> syncSettings();
  Future<UserSettings> getUserSettings();
}
```

### 4. Data Layer

#### Models (`lib/models/`)

Data structures with null safety:

```dart
class User {
  final String id;
  final String username;
  final String email;
  final String? avatarUrl;
  final LicenseTier licenseTier;

  User({
    required this.id,
    required this.username,
    required this.email,
    this.avatarUrl,
    required this.licenseTier,
  });

  factory User.fromJson(Map<String, dynamic> json) => User(
    id: json['id'],
    username: json['username'],
    email: json['email'],
    avatarUrl: json['avatar_url'],
    licenseTier: LicenseTier.fromString(json['license_tier']),
  );
}

class StreamSettings {
  final String url;
  final String key;
  final int bitrate;
  final Resolution resolution;
  final int frameRate;

  StreamSettings({
    required this.url,
    required this.key,
    required this.bitrate,
    required this.resolution,
    required this.frameRate,
  });
}

class LicenseInfo {
  final LicenseTier tier;
  final DateTime expiresAt;
  final int maxStreams;
  final int maxBitrate;
  final List<String> enabledFeatures;

  LicenseInfo({
    required this.tier,
    required this.expiresAt,
    required this.maxStreams,
    required this.maxBitrate,
    required this.enabledFeatures,
  });

  bool get isExpired => DateTime.now().isAfter(expiresAt);
  bool hasFeature(String feature) => enabledFeatures.contains(feature);
}

enum LicenseTier { free, premium, pro, enterprise }

enum StreamState { idle, connecting, streaming, error, stopped }

enum Resolution { r480p, r720p, r1080p, r2k, r4k }
```

#### Storage

**Shared Preferences** - Non-sensitive app preferences
```dart
SharedPreferences prefs = await SharedPreferences.getInstance();
prefs.setString('theme', 'elder');
prefs.setBool('notifications_enabled', true);
```

**Flutter Secure Storage** - Encrypted sensitive data
```dart
FlutterSecureStorage secureStorage = FlutterSecureStorage();
await secureStorage.write(key: 'jwt_token', value: token);
String? token = await secureStorage.read(key: 'jwt_token');
```

### 5. Platform Layer

#### Android (Kotlin)

**USB Capture Plugin** (`android/app/src/main/kotlin/com/penguintech/gazer/UsbCapturePlugin.kt`)

```kotlin
class UsbCapturePlugin : MethodCallHandler {
    override fun onMethodCall(@NonNull call: MethodCall, @NonNull result: Result) {
        when (call.method) {
            "getDevices" -> {
                val devices = getAvailableUsbDevices()
                result.success(devices)
            }
            "selectDevice" -> {
                val deviceId = call.argument<String>("device_id")
                selectDevice(deviceId)
                result.success(null)
            }
            else -> result.notImplemented()
        }
    }
}
```

#### iOS (Swift)

**Camera Integration** (`ios/Runner/CameraPlugin.swift`)

```swift
class CameraPlugin: NSObject, FlutterPlugin {
    static func dummyMethodToEnforceBundling(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        // Method implementation
    }

    static func register(with registrar: FlutterPluginRegistrar) {
        // Plugin registration
    }
}
```

## Data Flow Diagrams

### Authentication Flow

```
User Input (LoginScreen)
    ↓
AuthController.login()
    ↓
WaddleBotService.login()
    ↓
POST /api/v1/auth/login
    ↓
JWT Token (response)
    ↓
FlutterSecureStorage.write(token)
    ↓
AuthController.notifyListeners()
    ↓
UI Updates (MainScreen navigates)
```

### Streaming Flow

```
User Config (StreamSetup)
    ↓
StreamingController.startStream()
    ↓
WaddleBotService.startStream()
    ↓
POST /api/v1/streams/start → Stream ID
    ↓
RTMPService.connect()
    ↓
Platform Channel → USB Capture Service
    ↓
onMethodCall('startCapture')
    ↓
Kotlin/Swift native code
    ↓
Stream established
    ↓
StreamingController updates status
    ↓
StreamingPreview renders live feed
```

### Chat Message Flow

```
User Types Message (ChatScreen)
    ↓
ChatController.sendMessage()
    ↓
Socket.io emit('message')
    ↓
Server receives and broadcasts
    ↓
Socket.io on('message') event
    ↓
ChatController updates messages list
    ↓
ChatController.notifyListeners()
    ↓
ChatScreen rebuilds with new message
```

### Premium Feature Gating

```
User Clicks Premium Feature
    ↓
Feature Handler checks license
    ↓
LicenseService.checkFeatureAccess()
    ↓
Access denied (Free tier)
    ↓
PremiumGateDialog.show()
    ↓
User sees upgrade options
    ↓
User clicks "Upgrade"
    ↓
url_launcher opens pricing page
```

## State Management Pattern

### Controller Pattern

Each screen has a corresponding controller:

```dart
// Listen to state changes in screen
class StreamingPreview extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Consumer<StreamingController>(
      builder: (context, controller, _) {
        if (controller.state == StreamState.streaming) {
          return LiveFeed(stream: controller.stream);
        } else if (controller.state == StreamState.error) {
          return ErrorWidget(error: controller.error);
        }
        return LoadingWidget();
      },
    );
  }
}
```

### Reactive Updates

Controllers use `notifyListeners()` to trigger UI rebuilds:

```dart
class StreamingController extends ChangeNotifier {
  StreamState _state = StreamState.idle;

  Future<void> startStream(StreamSettings settings) async {
    _state = StreamState.connecting;
    notifyListeners(); // UI rebuilds

    try {
      await _rtmpService.connect(settings);
      _state = StreamState.streaming;
      notifyListeners(); // UI rebuilds
    } catch (e) {
      _state = StreamState.error;
      notifyListeners(); // UI rebuilds
    }
  }
}
```

## Premium Feature Architecture

### License Tier Model

```dart
enum LicenseTier {
  free,        // Basic features
  premium,     // Enhanced features
  pro,         // Professional features
  enterprise   // All features + custom support
}

class LicenseInfo {
  final LicenseTier tier;
  final DateTime expiresAt;
  final int maxStreams;
  final int maxBitrate;
  final List<String> enabledFeatures;

  bool canUseFeature(String feature) => enabledFeatures.contains(feature);
}
```

### Feature Gating Strategy

```dart
class LicenseService {
  late LicenseInfo _license;

  Future<bool> checkFeatureAccess(String feature) async {
    // Validate license with server
    final isValid = await _validateLicense();
    if (!isValid) return false;

    // Check feature access
    return _license.canUseFeature(feature);
  }

  Future<void> showUpgradeDialog(BuildContext context, String feature) {
    return PremiumGateDialog.show(
      context,
      featureName: feature,
      currentTier: _license.tier,
      requiredTier: _getRequiredTier(feature),
    );
  }
}
```

### Premium Widgets

**PremiumGateDialog** - Upgrade prompt shown when user tries premium feature

**LicenseStatusWidget** - Display current license tier and usage

**PremiumBadge** - Visual indicator on premium features

### Premium Features by Tier

| Feature | Free | Premium | Pro | Enterprise |
|---------|------|---------|-----|-----------|
| Basic Recording | ✅ | ✅ | ✅ | ✅ |
| USB Capture | ✅ | ✅ | ✅ | ✅ |
| 1080p Streaming | ❌ | ✅ | ✅ | ✅ |
| External RTMP | ❌ | ❌ | ✅ | ✅ |
| Multi-Stream (2) | ❌ | ✅ | ✅ | ✅ |
| Multi-Stream (5) | ❌ | ❌ | ✅ | ✅ |
| Unlimited Streams | ❌ | ❌ | ❌ | ✅ |
| Custom Bitrate | ❌ | ❌ | ✅ | ✅ |
| Priority Support | ❌ | ❌ | ✅ | ✅ |

## Platform Channels

### Android (Kotlin)

**Method Channel** - Synchronous calls to native code

```kotlin
// Android Implementation
val channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "com.penguintech.gazer/usb_capture")
channel.setMethodCallHandler { call, result ->
    when (call.method) {
        "getDevices" -> {
            val devices = UsbManager.getDeviceList()
            result.success(devices.map { it.toMap() })
        }
        "startCapture" -> {
            val settings = call.arguments as Map<String, Any>
            startCapture(settings)
            result.success(null)
        }
        else -> result.notImplemented()
    }
}
```

```dart
// Dart Call
const platform = MethodChannel('com.penguintech.gazer/usb_capture');
final devices = await platform.invokeMethod('getDevices');
```

### iOS (Swift)

**Method Channel** - Similar pattern for iOS

```swift
// iOS Implementation
let channel = FlutterMethodChannel(name: "com.penguintech.gazer/usb_capture",
                                  binaryMessenger: controller.binaryMessenger)
channel.setMethodCallHandler { (call: FlutterMethodCall, result: @escaping FlutterResult) in
    switch call.method {
    case "getDevices":
        // Get devices implementation
        result([])
    default:
        result(FlutterMethodNotImplemented)
    }
}
```

## Error Handling

### Service Layer Error Handling

```dart
Future<void> startStream(StreamSettings settings) async {
  try {
    _state = StreamState.connecting;
    notifyListeners();

    final response = await _waddleBotService.startStream(settings);

    _state = StreamState.streaming;
    notifyListeners();
  } on DioException catch (e) {
    _error = 'Network error: ${e.message}';
    _state = StreamState.error;
    notifyListeners();
  } on RTMPException catch (e) {
    _error = 'RTMP error: ${e.message}';
    _state = StreamState.error;
    notifyListeners();
  } catch (e) {
    _error = 'Unknown error: $e';
    _state = StreamState.error;
    notifyListeners();
  }
}
```

### User-Facing Error UI

```dart
if (controller.state == StreamState.error) {
  return ErrorWidget(
    message: controller.error,
    onRetry: () => controller.startStream(settings),
  );
}
```

## Extension Methods

### Utility Extensions (`lib/utils/extensions.dart`)

```dart
extension DateTimeExt on DateTime {
  String toReadableFormat() {
    return DateFormat('MMM d, yyyy').format(this);
  }

  bool get isExpired => isBefore(DateTime.now());
}

extension StringExt on String {
  String get capitalized => '${this[0].toUpperCase()}${substring(1)}';
}

extension IntExt on int {
  String toFileSize() {
    if (this < 1024) return '$this B';
    if (this < 1024 * 1024) return '${(this / 1024).toStringAsFixed(2)} KB';
    return '${(this / (1024 * 1024)).toStringAsFixed(2)} MB';
  }
}

extension ListExt<T> on List<T> {
  List<T> get shuffled => [...this]..shuffle();
}

// Add premium badge extension
extension WidgetExt on Widget {
  Widget withPremiumBadge({
    String label = 'PRO',
    String? tooltip,
    String size = 'medium',
  }) {
    return Stack(
      children: [
        this,
        Positioned(
          top: 0,
          right: 0,
          child: PremiumBadge(
            label: label,
            tooltip: tooltip,
            size: size,
          ),
        ),
      ],
    );
  }
}
```

## Best Practices

### Service Locator Pattern (Optional)

For dependency injection:

```dart
import 'package:get_it/get_it.dart';

final getIt = GetIt.instance;

void setupServiceLocator() {
  getIt.registerSingleton<WaddleBotService>(
    WaddleBotService(baseUrl: apiBaseUrl),
  );
  getIt.registerSingleton<RTMPService>(RTMPService());
  getIt.registerSingleton<SettingsService>(SettingsService());
}

// Usage in controllers
class StreamingController {
  final _waddleBotService = getIt<WaddleBotService>();
  final _rtmpService = getIt<RTMPService>();
}
```

### Resource Cleanup

```dart
class StreamingController extends ChangeNotifier {
  late StreamSubscription _statusSubscription;

  StreamingController() {
    _statusSubscription = _rtmpService.statusUpdates.listen((status) {
      _updateStatus(status);
      notifyListeners();
    });
  }

  @override
  void dispose() {
    _statusSubscription.cancel();
    super.dispose();
  }
}
```

### Testing Architecture

```dart
// Test setup with mocked services
void main() {
  late MockWaddleBotService mockApiService;
  late StreamingController controller;

  setUp(() {
    mockApiService = MockWaddleBotService();
    controller = StreamingController(apiService: mockApiService);
  });

  test('startStream updates state to streaming', () async {
    when(mockApiService.startStream(any))
      .thenAnswer((_) async => StreamResponse(...));

    await controller.startStream(testSettings);

    expect(controller.state, StreamState.streaming);
  });
}
```

---

**Last Updated**: 2026-01-30
**Version**: 2.1.0
**Product**: Waddles Gazer
