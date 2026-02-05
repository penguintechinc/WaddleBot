# Waddles Mobile Applications

This documentation covers the Waddles mobile applications for Android and iOS platforms. The mobile apps provide community management, real-time chat, and member administration capabilities.

## Overview

Waddles mobile apps are native applications built with modern frameworks:

- **Android**: Kotlin with Jetpack Compose
- **iOS**: Swift with SwiftUI

Both platforms share the same feature set and connect to the Waddles Hub API for backend services.

## Features

### Core Features

| Feature | Description |
|---------|-------------|
| **Authentication** | Secure login with JWT tokens and session management |
| **Community Management** | View and manage communities you belong to |
| **Real-time Chat** | WebSocket-based chat with typing indicators |
| **Member Directory** | Browse and search community members |
| **Settings** | User preferences and account management |

### Chat Features

- Real-time message sending and receiving
- Typing indicators
- Message history with pagination
- Connection state management
- Automatic reconnection handling

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](getting-started.md) | Setup instructions for Android and iOS development |
| [Architecture](architecture.md) | Application structure and design patterns |
| [API Integration](api-integration.md) | Hub API endpoints and WebSocket events |

## Quick Links

### Android Development

- **Language**: Kotlin 1.9+
- **UI Framework**: Jetpack Compose
- **Minimum SDK**: 26 (Android 8.0)
- **Target SDK**: 34 (Android 14)
- **Socket.io Client**: `io.socket:socket.io-client:2.1.0`

### iOS Development

- **Language**: Swift 5.9+
- **UI Framework**: SwiftUI
- **Minimum iOS**: 16.0
- **WebSocket**: Native URLSessionWebSocketTask

## Project Structure

```
mobile/
+-- android/
|   +-- app/
|       +-- src/main/java/io/waddlebot/hub/
|           +-- data/
|           |   +-- models/          # Data models
|           |   +-- network/         # Network services (WebSocket, API)
|           |   +-- repository/      # Data repositories
|           +-- presentation/
|           |   +-- auth/            # Authentication screens
|           |   +-- chat/            # Chat screens
|           |   +-- communities/     # Community screens
|           |   +-- members/         # Member screens
|           |   +-- navigation/      # Navigation components
|           |   +-- settings/        # Settings screens
|           +-- ui/
|               +-- theme/           # App theming
+-- ios/
    +-- WaddlesHub/
        +-- Services/                # WebSocket and API services
        +-- Views/
            +-- Chat/                # Chat views
```

## Technology Stack

### Android

| Technology | Purpose |
|------------|---------|
| Kotlin | Primary language |
| Jetpack Compose | Declarative UI |
| Kotlin Coroutines | Asynchronous programming |
| Kotlin Flow | Reactive data streams |
| Socket.io Client | WebSocket communication |
| Coil | Image loading |
| Hilt | Dependency injection |

### iOS

| Technology | Purpose |
|------------|---------|
| Swift | Primary language |
| SwiftUI | Declarative UI |
| Combine | Reactive programming |
| URLSession | HTTP and WebSocket communication |
| async/await | Asynchronous programming |

## Getting Help

For issues or questions:

1. Check the [Getting Started](getting-started.md) guide for setup problems
2. Review the [Architecture](architecture.md) for design questions
3. See [API Integration](api-integration.md) for backend connectivity issues
4. Contact the engineering team at support@penguintech.io

## Version Information

| Platform | Current Version | Last Updated |
|----------|-----------------|--------------|
| Android | 1.0.0 | 2026-01 |
| iOS | 1.0.0 | 2026-01 |

---

*Maintained by Penguin Tech Inc Engineering Team*
