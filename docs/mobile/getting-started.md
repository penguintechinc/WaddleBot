# Getting Started with Waddles Mobile

This guide covers setup instructions for both Android and iOS development environments.

## Prerequisites

### Common Requirements

- Git for version control
- Access to the Waddles repository
- Hub API server running (local or remote)

## Android Setup

### Requirements

| Requirement | Version |
|-------------|---------|
| Android Studio | Hedgehog (2023.1.1) or later |
| JDK | 17 or later |
| Kotlin | 1.9.0 or later |
| Gradle | 8.0 or later |
| Android SDK | API 34 (Android 14) |

### Installation Steps

1. **Install Android Studio**

   Download from [developer.android.com](https://developer.android.com/studio) and follow the installation wizard.

2. **Clone the Repository**

   ```bash
   git clone <repository-url>
   cd waddlebot/mobile/android
   ```

3. **Open in Android Studio**

   - Launch Android Studio
   - Select "Open an existing project"
   - Navigate to `mobile/android` directory
   - Wait for Gradle sync to complete

4. **Configure SDK**

   In Android Studio:
   - Go to File > Project Structure > SDK Location
   - Ensure Android SDK path is set correctly
   - Install SDK 34 if not present via SDK Manager

5. **Add Dependencies**

   Ensure `app/build.gradle.kts` includes:

   ```kotlin
   dependencies {
       // Socket.io client
       implementation("io.socket:socket.io-client:2.1.0")

       // Jetpack Compose
       implementation(platform("androidx.compose:compose-bom:2024.01.00"))
       implementation("androidx.compose.ui:ui")
       implementation("androidx.compose.ui:ui-graphics")
       implementation("androidx.compose.ui:ui-tooling-preview")
       implementation("androidx.compose.material3:material3")

       // Lifecycle and ViewModel
       implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.7.0")
       implementation("androidx.lifecycle:lifecycle-runtime-compose:2.7.0")

       // Coil for image loading
       implementation("io.coil-kt:coil-compose:2.5.0")

       // Coroutines
       implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
   }
   ```

6. **Configure Environment**

   Create or update `local.properties`:

   ```properties
   sdk.dir=/path/to/Android/sdk
   HUB_API_URL=https://hub-api.waddlebot.io
   ```

7. **Build and Run**

   - Connect an Android device or start an emulator
   - Click Run (green play button) or use `./gradlew assembleDebug`

### Android Project Structure

```
app/src/main/
+-- java/io/waddlebot/hub/
|   +-- data/
|   |   +-- models/           # Data classes
|   |   +-- network/          # WebSocketService, API clients
|   |   +-- repository/       # Data repositories
|   +-- presentation/
|   |   +-- auth/             # Login/register screens
|   |   +-- chat/             # ChatScreen, ChatViewModel
|   |   +-- communities/      # Community list/detail
|   |   +-- members/          # Member directory
|   |   +-- navigation/       # NavHost, routes
|   |   +-- settings/         # User settings
|   +-- ui/theme/             # Theme, colors, typography
+-- res/
    +-- drawable/             # Icons and images
    +-- values/               # Strings, colors, themes
```

### Android Troubleshooting

| Issue | Solution |
|-------|----------|
| Gradle sync fails | Invalidate caches: File > Invalidate Caches |
| Socket.io connection fails | Check network permissions in AndroidManifest.xml |
| Emulator slow | Enable hardware acceleration in BIOS |

---

## iOS Setup

### Requirements

| Requirement | Version |
|-------------|---------|
| macOS | Ventura (13.0) or later |
| Xcode | 15.0 or later |
| Swift | 5.9 or later |
| iOS Deployment Target | 16.0 |

### Installation Steps

1. **Install Xcode**

   Download from the Mac App Store or [developer.apple.com](https://developer.apple.com/xcode/).

2. **Install Command Line Tools**

   ```bash
   xcode-select --install
   ```

3. **Clone the Repository**

   ```bash
   git clone <repository-url>
   cd waddlebot/mobile/ios
   ```

4. **Open in Xcode**

   ```bash
   open WaddlesHub.xcodeproj
   ```

   Or double-click the `.xcodeproj` file in Finder.

5. **Configure Signing**

   - Select the project in the navigator
   - Go to Signing & Capabilities tab
   - Select your development team
   - Enable "Automatically manage signing"

6. **Add Socket.io (Optional)**

   If using socket.io-client-swift instead of native WebSocket:

   Via Swift Package Manager:
   - File > Add Package Dependencies
   - Enter: `https://github.com/socketio/socket.io-client-swift`
   - Select version 16.0.0 or later

   The current implementation uses native URLSessionWebSocketTask.

7. **Configure Environment**

   Create `Configuration.swift`:

   ```swift
   struct Configuration {
       static let hubAPIURL = URL(string: "https://hub-api.waddlebot.io")!
       static let webSocketURL = URL(string: "wss://hub-api.waddlebot.io")!
   }
   ```

8. **Build and Run**

   - Select a simulator or connected device
   - Press Cmd+R or click the Run button

### iOS Project Structure

```
WaddlesHub/
+-- Services/
|   +-- WebSocketManager.swift    # WebSocket handling
|   +-- APIClient.swift           # REST API client
|   +-- AuthService.swift         # Authentication
+-- Views/
|   +-- Chat/
|   |   +-- ChatView.swift        # Main chat UI
|   +-- Auth/
|   |   +-- LoginView.swift
|   +-- Communities/
|   |   +-- CommunityListView.swift
|   +-- Members/
|   |   +-- MemberListView.swift
|   +-- Settings/
|       +-- SettingsView.swift
+-- Models/
|   +-- User.swift
|   +-- Community.swift
|   +-- Message.swift
+-- Utilities/
    +-- Extensions.swift
```

### iOS Troubleshooting

| Issue | Solution |
|-------|----------|
| Build fails with signing error | Configure development team in project settings |
| Simulator not available | Download iOS runtime via Xcode > Settings > Platforms |
| WebSocket connection fails | Ensure App Transport Security allows your domain |

### App Transport Security

If connecting to a non-HTTPS server during development, add to `Info.plist`:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

Remove this for production builds.

---

## Running the Hub API Locally

For local development, start the Hub API:

```bash
cd waddlebot
make dev
```

The API will be available at `http://localhost:8080`.

Update the mobile app configuration to point to your local server:

**Android** (`local.properties`):
```properties
HUB_API_URL=http://10.0.2.2:8080  # Android emulator localhost
```

**iOS** (`Configuration.swift`):
```swift
static let hubAPIURL = URL(string: "http://localhost:8080")!
```

## Next Steps

- Read the [Architecture](architecture.md) guide to understand the app structure
- Review [API Integration](api-integration.md) for backend connectivity details
- Start implementing features following the existing patterns

---

*For additional help, contact the engineering team at support@penguintech.io*
