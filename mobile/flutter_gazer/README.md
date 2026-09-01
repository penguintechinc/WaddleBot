# Flutter Gazer - Mobile Stream Studio

![Version](https://img.shields.io/badge/version-2.1.0-blue?style=flat-square)
![Flutter](https://img.shields.io/badge/flutter-3.2%2B-blue?style=flat-square)
![License](https://img.shields.io/badge/license-Limited%20AGPL3-green?style=flat-square)

Professional mobile streaming application for iOS and Android with USB capture card support, real-time chat, community management, and tier-based feature gating.

```
    ╔═══════════════════════════════════╗
    ║     FLUTTER GAZER STREAM STUDIO   ║
    ║   Professional Mobile Streaming   ║
    ╚═══════════════════════════════════╝
```

## Overview

Flutter Gazer is a feature-rich mobile streaming application built with Flutter and Dart. It provides professional-grade streaming capabilities with USB capture card support, real-time chat integration, community management features, and enterprise-grade license tier management.

**Project**: flutter_gazer (gazer_waddlebot)
**Version**: 2.1.0
**Status**: Production Ready

### Key Highlights

- 📱 **Cross-Platform**: Native iOS and Android support
- 📹 **USB Capture**: Seamless USB capture card integration via platform channels
- 🎥 **RTMP Streaming**: Professional RTMP protocol support for external streaming
- 💬 **Real-Time Chat**: Socket.io integration for live community interaction
- 👥 **Community Management**: Multi-community support with member management
- 🔐 **Enterprise Security**: Tier-based feature gating with license validation
- 🎨 **Elder Theme**: Modern gold-accented UI with Material Design
- 📊 **Professional Quality**: High-bitrate streaming with quality presets

## Features

### Core Streaming Features
- **USB Capture Card Support** - Direct integration with external capture devices
- **RTMP Streaming** - Stream to external RTMP servers (YouTube Live, Twitch, custom)
- **Multi-Quality Presets** - Predefined quality settings (480p, 720p, 1080p)
- **Real-time Preview** - Live streaming preview with quality indicators
- **Bitrate Control** - Manual and automatic bitrate adjustment
- **Stream Settings** - Comprehensive streaming configuration options

### Community & Social Features
- **Community List** - Browse and join multiple streaming communities
- **Community Chat** - Real-time chat with Socket.io integration
- **Member Management** - View community members and member details
- **Channel Support** - Multiple channels per community
- **User Profiles** - Enhanced profile management and customization

### Enterprise Features
- **License Tier Management** - Free, Premium, Pro, and Enterprise tiers
- **Feature Gating** - Tier-based access control for premium features
- **Usage Tracking** - Monitor stream count, workflow usage, and limits
- **Premium Widgets** - Professional license status and upgrade prompts
- **License Validation** - Integration with PenguinTech License Server

### User Features
- **Authentication** - Secure login with JWT tokens
- **Settings Management** - User preferences and app configuration
- **Secure Storage** - Flutter Secure Storage for sensitive data
- **Version Tracking** - ConsoleVersion logging for debugging
- **Permission Management** - Native permission handling (camera, microphone, etc.)

## Technology Stack

### Frontend
- **Flutter** (3.2.0+) - Cross-platform mobile framework
- **Dart** - Programming language
- **Provider** (6.0.5+) - State management
- **Material Design** - UI components and patterns

### Networking & Communication
- **Dio** (5.3.0+) - HTTP client for REST APIs
- **Socket.io** (2.0.3+) - Real-time event-driven communication
- **URL Launcher** - Deep linking and URL handling

### Platform Integration
- **Camera** (0.10.5+) - Native camera access
- **Permission Handler** (11.0.0+) - Dynamic permission management
- **Path Provider** (2.1.0+) - File system access

### Storage & Security
- **Shared Preferences** (2.2.0+) - Simple key-value storage
- **Flutter Secure Storage** (9.0.0+) - Encrypted credential storage
- **Crypto** (3.0.3+) - Cryptographic operations

### Libraries & Tools
- **flutter_libs** - PenguinTech-maintained utility library
- **package_info_plus** (5.0.0+) - Package information and versioning
- **UUID** (4.1.0+) - UUID generation
- **flutter_lints** (3.0.0+) - Linting rules

### Testing
- **flutter_test** - Unit and widget testing
- **mockito** (5.4.0+) - Mocking framework
- **build_runner** (2.4.0+) - Code generation

## Quick Start

### Prerequisites

- Flutter SDK (3.2.0+)
- Dart SDK (included with Flutter)
- iOS: Xcode 14.0+ (for iOS builds)
- Android: Android Studio with SDK 32+ (API level 31+)
- Minimum iOS: 12.0
- Minimum Android: 5.0 (API level 31)

### Installation

```bash
# Clone the repository
git clone https://github.com/penguintechinc/waddlebot.git
cd waddlebot/mobile/flutter_gazer

# Install dependencies
flutter pub get

# Generate code from annotations (if needed)
flutter pub run build_runner build

# Get the flutter_libs dependency
cd ../../penguin-libs
flutter pub get
cd ../../mobile/flutter_gazer
```

### Development Setup

```bash
# Create local development configuration
mkdir -p lib/config/local
cp lib/config/.env.example lib/config/.env.local

# Edit configuration with your API endpoints
# Required environment variables:
# - API_BASE_URL: Backend API endpoint
# - SOCKET_IO_URL: Socket.io server URL
# - LICENSE_SERVER_URL: PenguinTech License Server
# - RTMP_SERVER_URL: RTMP streaming endpoint

# Run the app
flutter run
```

### Running Tests

```bash
# Run all unit tests
flutter test

# Run tests with coverage
flutter test --coverage

# Generate coverage report (requires lcov)
lcov --list coverage/lcov.info
```

## Build Instructions

### Development Build

```bash
# iOS development build
flutter build ios --debug

# Android development build
flutter build apk --debug

# Android development as app bundle
flutter build appbundle --debug
```

### Production Build

```bash
# iOS production build (creates .app)
flutter build ios --release

# iOS production build (creates .ipa)
cd ios
xcodebuild -workspace Runner.xcworkspace -scheme Runner \
  -configuration Release -derivedDataPath build \
  -archivePath build/Runner.xcarchive archive
xcodebuild -exportArchive -archivePath build/Runner.xcarchive \
  -exportOptionsPlist ios/ExportOptions.plist \
  -exportPath build/ios/ipa
cd ..

# Android production build (APK)
flutter build apk --release

# Android production build (App Bundle for Play Store)
flutter build appbundle --release
```

### Multi-Architecture Support

```bash
# Build for multiple architectures
flutter build ios --release --verbose

flutter build apk --target-platform android-arm,android-arm64,android-x86,android-x86-64 --release
```

## Project Structure

```
lib/
├── main.dart                      # App entry point
├── app.dart                       # Root widget configuration
├── models/
│   ├── license_info.dart         # License tier and feature models
│   ├── user_model.dart           # User data model
│   ├── community_model.dart      # Community data model
│   ├── stream_settings.dart      # Streaming configuration model
│   └── ...
├── services/
│   ├── waddlebot_service.dart    # Main WaddleBot API service
│   ├── rtmp_service.dart         # RTMP streaming service
│   ├── usb_capture_service.dart  # USB capture integration
│   ├── community_service.dart    # Community management API
│   ├── member_service.dart       # Member management API
│   ├── settings_service.dart     # User settings and preferences
│   └── ...
├── screens/
│   ├── main_screen.dart          # Main app shell
│   ├── auth/
│   │   ├── login_screen.dart     # Login interface
│   │   └── auth_controller.dart  # Auth state management
│   ├── streaming/
│   │   ├── streaming_preview.dart    # Live preview screen
│   │   ├── stream_setup.dart         # Configuration screen
│   │   ├── quality_presets.dart      # Quality selection
│   │   └── streaming_controller.dart # Streaming state management
│   ├── chat/
│   │   ├── chat_screen.dart      # Chat interface
│   │   ├── channel_list.dart     # Channel selection
│   │   └── chat_controller.dart  # Chat state management
│   ├── communities/
│   │   ├── community_list.dart   # Community browser
│   │   ├── community_detail.dart # Community details
│   │   └── community_controller.dart
│   ├── members/
│   │   ├── member_list.dart      # Member directory
│   │   ├── member_detail.dart    # Member profiles
│   │   └── member_controller.dart
│   ├── settings/
│   │   ├── settings_screen.dart  # Settings panel
│   │   └── settings_controller.dart
│   └── ...
├── widgets/
│   ├── premium_gate_dialog.dart      # Upgrade prompt dialog
│   ├── license_status_widget.dart    # License display
│   ├── premium_badge.dart            # Premium indicator
│   ├── stream_quality_selector.dart  # Quality chooser
│   ├── rtmp_config_form.dart         # RTMP settings form
│   ├── usb_capture_selector.dart     # Capture device chooser
│   └── ...
├── config/
│   ├── api_config.dart           # API configuration
│   ├── theme_config.dart         # Elder theme setup
│   └── constants.dart            # App-wide constants
└── utils/
    ├── logger.dart               # Logging utility
    ├── extensions.dart           # Dart extension methods
    └── validators.dart           # Input validation
```

## License Tier Information

Flutter Gazer supports four license tiers with different feature sets:

### Free Tier
- ✅ Basic recording (720p @ 5 Mbps)
- ✅ Camera preview
- ✅ USB capture support (read-only)
- ✅ Community chat (read-only)
- ❌ RTMP external streaming
- ❌ Multi-stream workflows
- ❌ Advanced bitrate control

### Premium Tier
- ✅ All Free features
- ✅ 1080p streaming (up to 8 Mbps)
- ✅ USB capture with settings
- ✅ Camera overlay features
- ✅ 2 simultaneous streams
- ✅ Standard support
- ❌ External RTMP streaming
- ❌ 3+ concurrent streams

### Pro Tier
- ✅ All Premium features
- ✅ External RTMP streaming
- ✅ Custom bitrate control (1-15 Mbps)
- ✅ 5 simultaneous streams
- ✅ Advanced quality presets
- ✅ Priority support
- ✅ Custom RTMP endpoints
- ❌ Unlimited streams (Enterprise only)

### Enterprise Tier
- ✅ All Pro features
- ✅ Unlimited concurrent streams
- ✅ Multi-instance deployments
- ✅ Custom SLA support
- ✅ Dedicated infrastructure
- ✅ API access for automation
- ✅ Custom branding options

**License Status Widget** - Display current tier and usage in settings

**Premium Gate Dialog** - Prompt users to upgrade when accessing premium features

**Premium Badge** - Visual indicator on premium features

## Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)** - App structure, data flow, and design patterns
- **[API Reference](docs/API.md)** - Services, models, and platform channels API
- **[Migration Guide](docs/MIGRATION.md)** - Migrating from native Android/iOS apps

## Configuration

### Environment Variables

Create `.env` file in `lib/config/`:

```env
# Backend API
API_BASE_URL=https://api.example.com/api/v1

# Socket.io Server
SOCKET_IO_URL=https://chat.example.com

# License Server
LICENSE_SERVER_URL=https://license.penguintech.io
PRODUCT_NAME=gazer_waddlebot

# RTMP Streaming
RTMP_SERVER_URL=rtmp://streaming.example.com/live

# Feature Flags
ENABLE_USB_CAPTURE=true
ENABLE_EXTERNAL_RTMP=true
ENABLE_MULTI_STREAM=true
```

### Theme Configuration

Elder theme is configured in `lib/config/theme_config.dart`:

```dart
// Primary gold: #D4AF37
// Secondary gold: #F0D88B
// Dark backgrounds: #121212, #1a1a1a
// Text colors: grey[300], grey[500]
```

## Domain Configuration

Flutter Gazer supports multiple API domains to facilitate development, testing, and production deployments.

### Available Domains

| Domain | Environment | Purpose | URL |
|--------|-------------|---------|-----|
| **Production** | Production | Official WaddleBot production environment with enterprise support | `https://api.waddlebot.io` |
| **Staging** | Staging | Pre-production testing environment for feature validation and integration testing | `https://staging-api.waddlebot.io` |
| **Development** | Development | Local or development server for active feature development and debugging | `http://localhost:8000` (configurable) |

### Changing the Domain

To change the API domain in the application:

1. Open **Settings** from the main navigation menu
2. Tap **API Domain** or **Server Configuration**
3. Select desired domain from the list:
   - Production (default)
   - Staging
   - Development
4. Confirm the change
5. Application will logout and restart with new domain configuration

### Default Behavior

- **Default Domain**: Production (`https://api.waddlebot.io`)
- **Persistence**: Selected domain is saved to device secure storage via `SettingsService`
- **Applied On**: Domain changes take effect immediately on app restart
- **Logout Requirement**: User must logout and re-authenticate when changing domains due to API token incompatibility across environments

### What Happens When Domain Changes

When a user changes the API domain:

1. **Settings Persistence**: New domain is saved to secure storage
2. **API Client Reset**: `ApiClient` is reconfigured with new base URL
3. **Token Invalidation**: Existing JWT tokens become invalid (from previous domain)
4. **WebSocket Reconnection**: Socket.io connection updates to new domain's chat server
5. **Session Logout**: User is automatically logged out to force re-authentication with new domain
6. **Cache Clearing**: All cached data from previous domain is cleared
7. **Restart**: App restarts with new domain configuration active

### Developer Implementation Details

#### WaddleBotDomain Enum

Domains are defined in `lib/models/waddlebot_domain.dart`:

```dart
enum WaddleBotDomain {
  production('Production', 'https://api.waddlebot.io'),
  staging('Staging', 'https://staging-api.waddlebot.io'),
  development('Development', 'http://localhost:8000');

  final String label;
  final String baseUrl;

  const WaddleBotDomain(this.label, this.baseUrl);
}
```

#### SettingsService Persistence

Domain selection is persisted in `lib/services/settings_service.dart`:

```dart
class SettingsService {
  static const String _domainKey = 'api_domain';

  Future<void> setApiDomain(WaddleBotDomain domain) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_domainKey, domain.name);
    _notifyListeners();
  }

  Future<WaddleBotDomain> getApiDomain() async {
    final prefs = await SharedPreferences.getInstance();
    final domainName = prefs.getString(_domainKey) ?? 'production';
    return WaddleBotDomain.values.firstWhere(
      (d) => d.name == domainName,
      orElse: () => WaddleBotDomain.production,
    );
  }
}
```

#### ApiClient Configuration

The HTTP client is configured dynamically based on selected domain in `lib/services/api_client.dart`:

```dart
class ApiClient {
  late Dio _dio;

  ApiClient(WaddleBotDomain domain) {
    _dio = Dio(BaseOptions(
      baseUrl: domain.baseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
    ));
    _addInterceptors();
  }

  void updateDomain(WaddleBotDomain domain) {
    _dio.options.baseUrl = domain.baseUrl;
  }
}
```

#### WebSocket Updates

Socket.io connection is updated when domain changes in `lib/services/chat_service.dart`:

```dart
class ChatService {
  late IO.Socket _socket;

  Future<void> updateDomain(WaddleBotDomain domain) async {
    await _socket.disconnect();
    _socket = IO.io(
      domain.baseUrl,
      OptionBuilder()
        .setTransports(['websocket']).build(),
    );
    await _socket.connect();
  }
}
```

## API Integration

### Waddles Backend API

The app communicates with Waddles backend via REST API:

```
Base URL: https://api.example.com/api/v1
Headers: Authorization: Bearer {jwt_token}
```

**Key Endpoints:**
- `POST /auth/login` - Authenticate user
- `GET /communities` - List communities
- `GET /communities/{id}` - Get community details
- `GET /members` - List members
- `POST /streams/start` - Start streaming
- `POST /streams/stop` - Stop streaming

### Socket.io Events

Real-time communication via Socket.io:

```dart
// Listen to chat messages
socket.on('message', (data) => handleNewMessage(data));

// Send chat message
socket.emit('message', {'text': 'Hello', 'channel': 'general'});

// User presence
socket.on('user_joined', (data) => updateMemberList(data));
socket.on('user_left', (data) => updateMemberList(data));
```

## Platform Channels

Platform-specific features via Kotlin/Swift:

### Android (Kotlin)

**USB Capture Integration:**
```kotlin
// lib/services/usb_capture_service.dart
const platform = MethodChannel('com.penguintech.gazer/usb_capture');
final devices = await platform.invokeMethod('getDevices');
```

### iOS (Swift)

**Camera Integration:**
```swift
// Handled via Flutter camera plugin
// Native camera permissions managed by permission_handler
```

## Contributing

### Code Style

Follow Dart Style Guide:
- 2-space indentation
- camelCase for variables and functions
- PascalCase for classes and types
- dartfmt for auto-formatting

```bash
# Format code
dart format lib/

# Analyze code
dart analyze
```

### Testing

Create tests in `test/` directory:

```bash
# Run all tests
flutter test

# Run specific test file
flutter test test/services/waddlebot_service_test.dart

# Watch mode
flutter test --watch
```

### Pull Request Process

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and write tests
3. Run linting and tests locally
4. Push branch and create PR
5. Ensure CI/CD passes
6. Request review from maintainers

## Troubleshooting

### Common Issues

**Issue: Pub get fails**
```bash
# Clear pub cache
flutter pub cache clean

# Get dependencies again
flutter pub get
```

**Issue: Android build fails**
```bash
# Clean build
flutter clean

# Rebuild
flutter build apk --debug --verbose
```

**Issue: iOS build fails**
```bash
# Clean and rebuild
flutter clean
cd ios
rm -rf Pods Podfile.lock
cd ..
flutter pub get
flutter build ios
```

**Issue: USB capture not working**
- Ensure USB device has necessary permissions
- Check platform channel implementation
- Verify USB device is connected before app startup

**Issue: RTMP streaming disconnects**
- Verify RTMP server URL is correct
- Check network connectivity
- Monitor bitrate - reduce if network is unstable

## Development Workflow

### Local Development

1. **Start development environment:**
   ```bash
   flutter run --verbose
   ```

2. **Monitor logs:**
   ```bash
   flutter logs
   ```

3. **Hot reload changes:**
   - Press `r` to hot reload
   - Press `R` to hot restart

4. **Debug in IDE:**
   - Use breakpoints in VS Code or Android Studio
   - Run with debugging enabled

### Release Workflow

1. **Update version in pubspec.yaml**
2. **Create git tag:** `git tag v2.1.0`
3. **Build release APK/IPA**
4. **Submit to stores (Google Play, App Store)**
5. **Monitor for crashes and feedback**

## Performance Optimization

### Key Optimization Areas

- **Image Loading** - Lazy load and cache images
- **Stream Buffering** - Optimize buffer sizes for different network conditions
- **Memory Management** - Dispose resources in `dispose()` methods
- **UI Rendering** - Use RepaintBoundary for complex widgets
- **Network** - Implement connection pooling and request batching

### Profiling Tools

```bash
# Generate performance trace
flutter run --trace-startup > startup.log

# Use DevTools for real-time profiling
flutter pub global activate devtools
devtools
```

## Security Considerations

### Authentication

- JWT tokens stored in Flutter Secure Storage
- Tokens refreshed automatically before expiry
- Secure logout clears tokens and cache

### Data Encryption

- Sensitive data encrypted via Crypto package
- RTMP credentials encrypted in storage
- API calls via HTTPS only

### Permissions

- Minimum required permissions requested
- Runtime permission checks on Android 6.0+
- Privacy policy compliance

## Support & Resources

**Documentation:**
- [Flutter Documentation](https://flutter.dev/docs)
- [Dart Documentation](https://dart.dev/guides)
- [Material Design](https://material.io/design)

**Community:**
- Flutter Community: https://flutter.dev/community
- Stack Overflow: Tag with `flutter`

**Support Contact:**
- Technical Support: support@penguintech.io
- Sales: sales@penguintech.io
- Website: https://www.penguintech.io

## License

Limited AGPL-3.0 with commercial use restrictions. See LICENSE.md in project root.

**License Server Integration**: https://license.penguintech.io

---

**Version**: 2.1.0
**Last Updated**: 2026-01-30
**Maintained by**: Penguin Tech Inc
**Status**: Production Ready

**Key Features:**
- Professional-grade mobile streaming
- Cross-platform (iOS & Android)
- Enterprise license tier management
- Real-time community interaction
- USB capture card support
- RTMP external streaming
