# Flutter Gazer Migration Guide

Guide for migrating from native Android/iOS implementations to Waddles Gazer, with feature comparison and data migration strategies.

## Overview

Waddles Gazer is a cross-platform mobile streaming application built with Flutter that consolidates functionality from both Android and iOS native implementations into a single, maintainable codebase.

**Benefits of Migration:**
- Single codebase for both platforms
- Faster feature development and deployment
- Consistent UX across iOS and Android
- Easier maintenance and bug fixes
- Shared dependencies and libraries
- Centralized license management

---

## Android Migration

### Prerequisites

- Android native app source code
- Firebase projects configured (if applicable)
- Keystore files for signing
- API documentation for backend services
- User data export (if applicable)

### Feature Comparison

| Feature | Android Native | Flutter Gazer | Status |
|---------|----------------|---------------|--------|
| USB Capture | ✅ | ✅ | Complete |
| RTMP Streaming | ✅ | ✅ | Complete |
| Real-time Chat | ✅ | ✅ | Complete |
| Community Management | ✅ | ✅ | Complete |
| Member Directory | ✅ | ✅ | Complete |
| User Profiles | ✅ | ✅ | Complete |
| Settings/Preferences | ✅ | ✅ | Complete |
| Push Notifications | ✅ | ⚙️ | Planned |
| Offline Mode | ⚠️ | ⚙️ | Planned |
| Analytics | ✅ | ⚙️ | Planned |

✅ = Complete | ⚠️ = Partial | ⚙️ = Planned | ❌ = Not applicable

### Migration Checklist

#### 1. Code Review & Extraction

- [ ] Identify all Android service classes
- [ ] Extract business logic from Activities
- [ ] Document all platform-specific implementations
- [ ] List all third-party dependencies
- [ ] Create mapping of Android features to Dart services

#### 2. Architecture Migration

**Android Architecture:**
```
Activities/Fragments
    ↓
ViewModels
    ↓
Repository Layer
    ↓
Network & Database
```

**Flutter Architecture:**
```
Screens/Widgets
    ↓
Controllers (Provider)
    ↓
Services (Business Logic)
    ↓
Platform Channels & REST APIs
```

**Migration Pattern:**
```dart
// Old Android Activity
class StreamingActivity : AppCompatActivity {
  private val viewModel: StreamingViewModel by viewModels()

  override fun onCreate(savedInstanceState: Bundle?) {
    viewModel.startStream(settings)
  }
}

// New Flutter Screen
class StreamingScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Consumer<StreamingController>(
      builder: (context, controller, _) {
        if (controller.state == StreamState.streaming) {
          return StreamingPreview();
        }
        return StreamSetup();
      },
    );
  }
}
```

#### 3. Service Layer Migration

**Extract USB Capture Logic:**

```dart
// Old Android implementation (Java/Kotlin)
class UsbCaptureManager {
  fun getDevices(): List<UsbDevice> { ... }
  fun selectDevice(device: UsbDevice) { ... }
  fun startCapture(settings: CaptureSettings) { ... }
}

// New Flutter service
class USBCaptureService {
  Future<List<USBDevice>> getAvailableDevices() async {
    const platform = MethodChannel('com.penguintech.gazer/usb_capture');
    return await platform.invokeMethod('getDevices');
  }
}
```

**Extract RTMP Streaming Logic:**

```dart
// Old Android implementation
class RtmpBroadcaster {
  fun connect(url: String, key: String) { ... }
  fun startBroadcast(settings: StreamSettings) { ... }
  fun updateBitrate(bitrate: Int) { ... }
}

// New Flutter service
class RTMPService {
  Future<void> connect(String rtmpUrl, String key) async {
    // FFmpeg or native library binding
  }

  Future<void> startBroadcast(StreamSettings settings) async {
    // RTMP protocol implementation
  }
}
```

#### 4. Data Migration

**Step 1: Export Data from Android App**

```kotlin
// Create export function in Android app
fun exportUserData(): String {
  val user = getUserFromPreferences()
  val communities = getCommunities()
  val settings = getSettings()

  val json = JSONObject().apply {
    put("user", user.toJson())
    put("communities", JSONArray(communities.map { it.toJson() }))
    put("settings", settings.toJson())
  }

  return json.toString()
}
```

**Step 2: Generate Migration File**

```json
{
  "version": "1.0",
  "export_date": "2026-01-30T10:30:00Z",
  "user": {
    "id": "user-123",
    "username": "john_doe",
    "email": "john@example.com",
    "license_tier": "pro"
  },
  "communities": [
    {
      "id": "community-1",
      "name": "My Community",
      "joined_at": "2025-06-15T09:00:00Z"
    }
  ],
  "settings": {
    "theme": "dark",
    "notifications_enabled": true
  }
}
```

**Step 3: Import to Flutter App**

```dart
class DataMigrationService {
  Future<void> importAndroidData(String jsonData) async {
    final json = jsonDecode(jsonData);

    // Migrate user data
    final user = User.fromJson(json['user']);
    await settingsService.storeUser(user);

    // Migrate communities
    final communities = (json['communities'] as List)
      .map((c) => Community.fromJson(c))
      .toList();
    await communityService.saveCommunities(communities);

    // Migrate settings
    final settings = UserSettings.fromJson(json['settings']);
    await settingsService.saveSettings(settings);
  }
}
```

#### 5. Authentication Migration

```dart
// Step 1: Obtain Android JWT token
final androidToken = await _getTokenFromAndroidApp();

// Step 2: Validate token with Flutter app
final isValid = await waddleBotService.validateToken(androidToken);

// Step 3: Store in Flutter Secure Storage
if (isValid) {
  await secureStorage.write(key: 'jwt_token', value: androidToken);
} else {
  // Require re-authentication
  await navigateToLogin();
}
```

#### 6. API Endpoint Migration

**Android Endpoints → Flutter Endpoints (Same Backend)**

```
POST /api/v1/auth/login              (same)
POST /api/v1/streams/start            (same)
POST /api/v1/streams/stop             (same)
GET  /api/v1/communities              (same)
GET  /api/v1/communities/{id}         (same)
POST /api/v1/communities/{id}/join    (same)
```

**Configure in Flutter:**

```dart
// lib/config/api_config.dart
const String API_BASE_URL = 'https://api.example.com/api/v1';
const String SOCKET_IO_URL = 'https://chat.example.com';

class WaddleBotService {
  final Dio _dio = Dio(
    BaseOptions(
      baseUrl: API_BASE_URL,
      connectTimeout: Duration(seconds: 30),
    ),
  );
}
```

### Gradual Migration Strategy

#### Phase 1: Setup (Week 1)
- [ ] Clone Flutter Gazer repository
- [ ] Set up development environment
- [ ] Configure API endpoints
- [ ] Test basic connectivity

#### Phase 2: Core Features (Weeks 2-3)
- [ ] Migrate authentication
- [ ] Migrate USB capture integration
- [ ] Migrate RTMP streaming
- [ ] Verify feature parity

#### Phase 3: User Features (Weeks 4-5)
- [ ] Migrate community management
- [ ] Migrate chat functionality
- [ ] Migrate member directory
- [ ] Migrate user settings

#### Phase 4: Testing & Deployment (Weeks 6-7)
- [ ] User acceptance testing
- [ ] Performance testing
- [ ] Security audit
- [ ] Beta release
- [ ] Full rollout

### Platform Channel Implementation

**Migrate Android USB Capture:**

```kotlin
// Android USB Capture Migration
// File: android/app/src/main/kotlin/com/penguintech/gazer/UsbCaptureChannel.kt

class UsbCaptureChannel(private val activity: Activity) {
    companion object {
        private const val CHANNEL = "com.penguintech.gazer/usb_capture"
    }

    fun setup(binaryMessenger: BinaryMessenger) {
        val channel = MethodChannel(binaryMessenger, CHANNEL)
        channel.setMethodCallHandler { call, result ->
            when (call.method) {
                "getDevices" -> handleGetDevices(result)
                "selectDevice" -> handleSelectDevice(call.argument("device_id"), result)
                "startCapture" -> handleStartCapture(call.arguments, result)
                else -> result.notImplemented()
            }
        }
    }

    private fun handleGetDevices(result: MethodChannel.Result) {
        val manager = activity.getSystemService(Context.USB_SERVICE) as UsbManager
        val devices = manager.deviceList.values.map {
            mapOf(
                "id" to it.deviceId.toString(),
                "name" to it.productName,
                "vendor_id" to it.vendorId,
                "product_id" to it.productId
            )
        }
        result.success(devices)
    }

    private fun handleSelectDevice(deviceId: String?, result: MethodChannel.Result) {
        // Implement device selection logic
        result.success(null)
    }

    private fun handleStartCapture(arguments: Any?, result: MethodChannel.Result) {
        val args = arguments as Map<String, Any>
        val resolution = args["resolution"] as String
        val frameRate = args["frame_rate"] as Int
        val bitrate = args["bitrate"] as Int

        // Start capture with parameters
        result.success(null)
    }
}
```

---

## iOS Migration

### Prerequisites

- iOS native app source code
- Xcode project configuration
- Certificate and provisioning profiles
- API documentation for backend services
- User data export (if applicable)

### Feature Comparison

| Feature | iOS Native | Flutter Gazer | Status |
|---------|-----------|---------------|--------|
| Camera Input | ✅ | ✅ | Complete |
| RTMP Streaming | ✅ | ✅ | Complete |
| Real-time Chat | ✅ | ✅ | Complete |
| Community Management | ✅ | ✅ | Complete |
| Settings/Preferences | ✅ | ✅ | Complete |
| Push Notifications | ✅ | ⚙️ | Planned |
| Keychain Storage | ✅ | ✅ | Complete |

### Migration Checklist

#### 1. Code Review & Extraction

- [ ] Identify all iOS ViewControllers
- [ ] Extract business logic from UI
- [ ] Document all Core Foundation usage
- [ ] List all CocoaPods dependencies
- [ ] Create mapping of iOS features to Dart services

#### 2. Architecture Migration

**iOS Architecture:**
```
ViewControllers
    ↓
ViewModels
    ↓
Services
    ↓
Network & Storage
```

**Flutter Equivalent:**
```
Screens
    ↓
Controllers
    ↓
Services
    ↓
Platform Channels & REST APIs
```

#### 3. Service Layer Migration

**Extract Camera Stream Logic:**

```swift
// Old iOS implementation (Swift)
class CameraManager: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    func startCapture(settings: CaptureSettings) {
        // Setup AVCaptureSession
        // Configure device and output
    }
}

// Migrate to Flutter service
class USBCaptureService {
  Future<void> startCapture(CaptureSettings settings) async {
    // Use platform channels to native camera code
  }
}
```

**Extract RTMP Streaming Logic:**

```swift
// Old iOS implementation
class RtmpBroadcaster {
    func connect(url: String, key: String) async throws {
        // RTMP connection logic
    }
}

// Flutter service
class RTMPService {
  Future<void> connect(String rtmpUrl, String key) async {
    // Platform channel to native RTMP library
  }
}
```

#### 4. Keychain Migration

**Export iOS Keychain Data:**

```swift
// Create export function in iOS app
func exportKeychainData() -> String {
  let token = KeychainManager.retrieveToken()
  let credentials = KeychainManager.retrieveCredentials()

  let data = [
    "token": token,
    "username": credentials.username,
    "email": credentials.email
  ]

  return try JSONSerialization.data(withJSONObject: data).string
}
```

**Import to Flutter:**

```dart
Future<void> importIOSKeychainData(String jsonData) async {
  final data = jsonDecode(jsonData);

  // Store token in Flutter Secure Storage
  await secureStorage.write(
    key: 'jwt_token',
    value: data['token'],
  );
}
```

#### 5. UserDefaults Migration

**Export iOS UserDefaults:**

```swift
func exportUserDefaults() -> String {
  let prefs = UserDefaults.standard
  let data = [
    "theme": prefs.string(forKey: "theme") ?? "light",
    "language": prefs.string(forKey: "language") ?? "en",
    "notifications_enabled": prefs.bool(forKey: "notifications_enabled")
  ]

  return try JSONSerialization.data(withJSONObject: data).string
}
```

**Import to Flutter:**

```dart
Future<void> importIOSUserDefaults(String jsonData) async {
  final data = jsonDecode(jsonData);
  final prefs = await SharedPreferences.getInstance();

  await prefs.setString('theme', data['theme']);
  await prefs.setString('language', data['language']);
  await prefs.setBool('notifications_enabled', data['notifications_enabled']);
}
```

#### 6. Platform Channel Implementation

**Migrate iOS Camera Access:**

```swift
// File: ios/Runner/CameraChannel.swift

import Foundation
import AVFoundation

class CameraChannel {
    static let methodChannelName = "com.penguintech.gazer/camera"

    static func setup(with controller: FlutterViewController) {
        let channel = FlutterMethodChannel(
            name: methodChannelName,
            binaryMessenger: controller.binaryMessenger
        )

        channel.setMethodCallHandler { call, result in
            switch call.method {
            case "requestPermission":
                requestCameraPermission(result: result)
            case "getCameraInfo":
                getCameraInfo(result: result)
            case "startPreview":
                startCameraPreview(result: result)
            default:
                result(FlutterMethodNotImplemented)
            }
        }
    }

    private static func requestCameraPermission(result: @escaping FlutterResult) {
        AVCaptureDevice.requestAccess(for: .video) { granted in
            result(granted)
        }
    }

    private static func getCameraInfo(result: FlutterResult) {
        let devices = AVCaptureDevice.DiscoverySession(
            deviceTypes: [.builtInWideAngleCamera],
            mediaType: .video,
            position: .front
        ).devices

        let cameraInfo = devices.map { device in
            [
                "name": device.localizedName,
                "position": device.position.rawValue,
                "formats": device.formats.count
            ]
        }

        result(cameraInfo)
    }

    private static func startCameraPreview(result: FlutterResult) {
        // Start camera preview implementation
        result(nil)
    }
}
```

### Gradual Migration Strategy

#### Phase 1: Setup (Week 1)
- [ ] Clone Flutter Gazer repository
- [ ] Configure iOS build settings
- [ ] Test on iOS simulator
- [ ] Verify API connectivity

#### Phase 2: Core Features (Weeks 2-3)
- [ ] Migrate authentication
- [ ] Migrate camera/capture integration
- [ ] Migrate RTMP streaming
- [ ] Test on physical device

#### Phase 3: User Features (Weeks 4-5)
- [ ] Migrate community features
- [ ] Migrate chat functionality
- [ ] Migrate settings management
- [ ] Performance testing

#### Phase 4: Testing & Deployment (Weeks 6-7)
- [ ] QA testing
- [ ] Beta TestFlight build
- [ ] App Store submission
- [ ] Full release

---

## Shared Data Format

### User Profile Export

```json
{
  "version": "1.0",
  "export_platform": "android|ios",
  "export_date": "2026-01-30T10:30:00Z",
  "user": {
    "id": "user-123",
    "username": "john_doe",
    "email": "john@example.com",
    "avatar_url": "https://...",
    "license_tier": "pro",
    "created_at": "2025-06-15T09:00:00Z"
  },
  "authentication": {
    "token": "jwt-token-here",
    "token_expires_at": "2026-02-15T10:30:00Z"
  },
  "communities": [
    {
      "id": "community-1",
      "name": "My Community",
      "role": "owner",
      "joined_at": "2025-06-15T09:00:00Z"
    }
  ],
  "settings": {
    "theme": "dark",
    "language": "en",
    "notifications_enabled": true,
    "notification_sound": true,
    "notification_vibrate": true,
    "auto_quality_adjust": true,
    "preferred_resolution": "1080p",
    "preferred_bitrate": 5000
  },
  "cache": {
    "last_community_viewed": "community-1",
    "last_login": "2026-01-30T10:00:00Z"
  }
}
```

### Import Flow in Flutter

```dart
class DataMigrationController {
  Future<void> importMigrationFile(File file) async {
    // 1. Parse JSON
    final jsonString = await file.readAsString();
    final data = jsonDecode(jsonString);

    // 2. Validate version
    if (data['version'] != '1.0') {
      throw Exception('Unsupported migration format version');
    }

    // 3. Import user data
    await _importUser(data['user']);

    // 4. Import authentication
    await _importAuthentication(data['authentication']);

    // 5. Import communities
    await _importCommunities(data['communities']);

    // 6. Import settings
    await _importSettings(data['settings']);

    // 7. Notify completion
    notifyListeners();
  }

  Future<void> _importUser(Map<String, dynamic> userData) async {
    final user = User.fromJson(userData);
    await settingsService.storeUser(user);
  }

  Future<void> _importAuthentication(Map<String, dynamic> authData) async {
    final token = authData['token'] as String;
    final expiresAt = DateTime.parse(authData['token_expires_at']);

    await secureStorage.write(key: 'jwt_token', value: token);
    await secureStorage.write(
      key: 'token_expires_at',
      value: expiresAt.toIso8601String(),
    );
  }

  Future<void> _importCommunities(List<dynamic> communities) async {
    final communityList = communities
      .map((c) => Community.fromJson(c))
      .toList();

    await communityService.saveCommunities(communityList);
  }

  Future<void> _importSettings(Map<String, dynamic> settings) async {
    final userSettings = UserSettings.fromJson(settings);
    await settingsService.saveSettings(userSettings);
  }
}
```

---

## Troubleshooting

### Common Migration Issues

#### 1. Token Expiration After Migration

**Problem:** JWT token from Android/iOS app expires immediately after import.

**Solution:**
```dart
Future<void> validateAndRefreshToken() async {
  final token = await secureStorage.read(key: 'jwt_token');
  final expiresAt = await secureStorage.read(key: 'token_expires_at');

  if (expiresAt == null) {
    // Token expiry time not stored - require re-authentication
    await navigateToLogin();
    return;
  }

  final expiryDateTime = DateTime.parse(expiresAt);
  if (DateTime.now().isAfter(expiryDateTime.subtract(Duration(minutes: 5)))) {
    // Token expiring soon - refresh
    try {
      final newToken = await waddleBotService.refreshToken();
      await secureStorage.write(key: 'jwt_token', value: newToken);
    } catch (e) {
      // Refresh failed - require re-authentication
      await navigateToLogin();
    }
  }
}
```

#### 2. API Endpoint Mismatch

**Problem:** Flutter app can't connect to same backend as native app.

**Solution:**
- Verify API base URL configuration
- Check CORS settings if different domains
- Verify Bearer token format in Authorization header
- Test with same HTTP client (Dio)

#### 3. USB Device Not Recognized

**Problem:** USB capture device not recognized after migration.

**Solution:**
```dart
Future<void> debugUSBDevices() async {
  final devices = await usbCaptureService.getAvailableDevices();

  if (devices.isEmpty) {
    print('No USB devices found');
    // Check permissions
    final hasPermission = await requestUSBPermission();
    if (!hasPermission) {
      print('USB permission denied');
    }
    return;
  }

  for (var device in devices) {
    print('Device: ${device.name}');
    print('Vendor ID: ${device.vendorId}');
    print('Product ID: ${device.productId}');
  }
}
```

#### 4. License Tier Not Recognized

**Problem:** User's license tier shows as 'free' after migration.

**Solution:**
```dart
Future<void> syncLicenseInfo() async {
  try {
    final licenseInfo = await licenseService.fetchLicenseInfo();

    if (licenseInfo == null) {
      print('License info not available');
      await licenseService.requestNewLicense();
      return;
    }

    print('License tier: ${licenseInfo.tier}');
    print('Expires: ${licenseInfo.expiresAt}');

    // Validate with server
    final isValid = await licenseService.validateLicense();
    if (!isValid) {
      print('License validation failed');
    }
  } catch (e) {
    print('Error syncing license: $e');
  }
}
```

---

## Post-Migration Checklist

- [ ] All data successfully migrated
- [ ] User can log in with same credentials
- [ ] All saved communities accessible
- [ ] Settings and preferences preserved
- [ ] USB devices recognized
- [ ] RTMP streaming works
- [ ] Chat functionality operational
- [ ] License tier correctly displayed
- [ ] Performance meets requirements
- [ ] All tests passing
- [ ] User acceptance testing complete
- [ ] Documentation updated
- [ ] Native apps archived/deprecated

---

## Support

For migration issues or questions:

- **Technical Support**: support@penguintech.io
- **Documentation**: See ARCHITECTURE.md and API.md
- **Issue Tracking**: GitHub Issues
- **Community**: Flutter Community forums

---

**Migration Guide Version**: 1.0
**Last Updated**: 2026-01-30
**Applies To**: Waddles Gazer v2.1.0+
