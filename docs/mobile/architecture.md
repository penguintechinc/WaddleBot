# Mobile Application Architecture

This document describes the architecture and design patterns used in the Waddles mobile applications.

## Overview

Both Android and iOS apps follow the **MVVM (Model-View-ViewModel)** architecture pattern with reactive data binding. This ensures:

- Separation of concerns
- Testability
- Maintainable codebase
- Consistent patterns across platforms

## Architecture Pattern: MVVM

```
+------------------+
|      View        |  UI Layer (Compose/SwiftUI)
|  (Declarative)   |  - Renders UI based on state
+--------+---------+  - Sends user actions to ViewModel
         |
         | observes state / sends actions
         v
+------------------+
|   ViewModel      |  Presentation Layer
|                  |  - Holds UI state
|                  |  - Processes user actions
+--------+---------+  - Calls services/repositories
         |
         | calls
         v
+------------------+
|    Services/     |  Data Layer
|   Repositories   |  - WebSocket communication
|                  |  - REST API calls
+--------+---------+  - Data transformation
         |
         | network requests
         v
+------------------+
|    Hub API       |  Backend
+------------------+
```

## Android Architecture

### Layer Structure

```
+-------------------------------------------------------+
|                    Presentation Layer                  |
|  +--------------------------------------------------+ |
|  |  Composables (ChatScreen, MessageInput, etc.)    | |
|  +--------------------------------------------------+ |
|  |  ViewModels (ChatViewModel)                      | |
|  |  - StateFlow for UI state                        | |
|  |  - Coroutines for async operations               | |
|  +--------------------------------------------------+ |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|                      Data Layer                        |
|  +--------------------------------------------------+ |
|  |  Services (WebSocketService)                     | |
|  |  - Socket.io client management                   | |
|  |  - Event emission and reception                  | |
|  +--------------------------------------------------+ |
|  |  Repositories (Optional)                         | |
|  |  - Data aggregation                              | |
|  |  - Caching logic                                 | |
|  +--------------------------------------------------+ |
+-------------------------------------------------------+
```

### Key Components

**WebSocketService**
- Manages Socket.io client connection
- Emits events: `chat:join`, `chat:message`, `chat:typing`, `chat:history`
- Receives events and publishes via SharedFlow
- Handles reconnection logic

**ChatViewModel**
- Manages ChatUiState (messages, input, typing users, etc.)
- Observes WebSocketService flows
- Exposes state via StateFlow for Compose

**ChatScreen**
- Declarative UI using Jetpack Compose
- Observes ViewModel state
- Triggers ViewModel actions on user interaction

### Data Flow (Android)

```
User Action (tap send)
        |
        v
ChatScreen calls viewModel.sendMessage()
        |
        v
ChatViewModel calls webSocketService.sendMessage()
        |
        v
WebSocketService emits "chat:message" via Socket.io
        |
        v
Server broadcasts message to channel
        |
        v
WebSocketService receives "chat:message" event
        |
        v
WebSocketService emits to incomingMessages SharedFlow
        |
        v
ChatViewModel collects flow, updates _uiState
        |
        v
ChatScreen recomposes with new message
```

### State Management (Android)

```kotlin
// UI State data class
data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val messageInput: String = "",
    val typingUsers: Set<String> = emptySet(),
    val isLoadingHistory: Boolean = false,
    val errorMessage: String? = null
)

// ViewModel exposes StateFlow
private val _uiState = MutableStateFlow(ChatUiState())
val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

// Compose observes state
val uiState by viewModel.uiState.collectAsState()
```

---

## iOS Architecture

### Layer Structure

```
+-------------------------------------------------------+
|                    Presentation Layer                  |
|  +--------------------------------------------------+ |
|  |  Views (ChatView, MessageInputView, etc.)        | |
|  |  - SwiftUI declarative views                     | |
|  +--------------------------------------------------+ |
|  |  ViewModels (ChatViewModel)                      | |
|  |  - @Published properties for state               | |
|  |  - Combine for async operations                  | |
|  +--------------------------------------------------+ |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|                      Data Layer                        |
|  +--------------------------------------------------+ |
|  |  Services (WebSocketManager)                     | |
|  |  - URLSessionWebSocketTask                       | |
|  |  - Socket.io protocol handling                   | |
|  +--------------------------------------------------+ |
+-------------------------------------------------------+
```

### Key Components

**WebSocketManager**
- Uses native URLSessionWebSocketTask
- Implements Socket.io protocol manually
- Publishes events via Combine PassthroughSubject
- Handles connection lifecycle and reconnection

**ChatViewModel**
- ObservableObject with @Published properties
- Subscribes to WebSocketManager publishers
- Manages chat state and user actions

**ChatView**
- SwiftUI view observing ViewModel
- Uses @StateObject for ViewModel ownership
- Bindings for two-way data flow

### Data Flow (iOS)

```
User Action (tap send)
        |
        v
ChatView calls viewModel.sendMessage()
        |
        v
ChatViewModel calls webSocketManager.sendMessage()
        |
        v
WebSocketManager encodes and sends Socket.io message
        |
        v
Server broadcasts message to channel
        |
        v
WebSocketManager receives message via URLSessionWebSocketTask
        |
        v
WebSocketManager parses Socket.io format, sends via incomingMessages
        |
        v
ChatViewModel receives via Combine subscription
        |
        v
ChatViewModel updates @Published messages
        |
        v
ChatView re-renders with new message
```

### State Management (iOS)

```swift
// ViewModel with Published properties
@MainActor
final class ChatViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var messageInput: String = ""
    @Published var typingUsers: Set<String> = []
    @Published var isLoadingHistory: Bool = false
    @Published var errorMessage: String?
}

// View observes ViewModel
struct ChatView: View {
    @StateObject private var viewModel: ChatViewModel

    var body: some View {
        // UI automatically updates when @Published changes
    }
}
```

---

## Common Patterns

### Connection State Management

Both platforms track WebSocket connection state:

```
+---------------+     connect()    +---------------+
|  Disconnected | --------------->  |  Connecting  |
+---------------+                  +---------------+
       ^                                   |
       |                                   | success
       | disconnect()                      v
       |                           +---------------+
       +--------------------------- |   Connected   |
       |                           +---------------+
       |                                   |
       | max retries                       | error
       |                                   v
+---------------+  <---------------  +---------------+
|     Error     |   retry failed   |   Reconnecting |
+---------------+                  +---------------+
```

### Error Handling

Errors are captured and displayed to users:

1. Connection errors trigger reconnection
2. Max retry exceeded shows error state
3. User can manually trigger reconnection
4. All errors are logged for debugging

### Typing Indicators

Typing indicators follow this pattern:

1. User starts typing -> send `isTyping: true`
2. User clears input -> send `isTyping: false`
3. User sends message -> send `isTyping: false`
4. Receive typing events from other users
5. Display typing users in UI

---

## Dependency Injection

### Android (Hilt)

```kotlin
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides
    @Singleton
    fun provideWebSocketService(): WebSocketService {
        return WebSocketService(baseUrl = BuildConfig.HUB_API_URL)
    }
}
```

### iOS (Manual/Environment)

```swift
// App entry point
@main
struct WaddlesHubApp: App {
    let webSocketManager = WebSocketManager(
        baseURL: Configuration.webSocketURL
    )

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(webSocketManager)
        }
    }
}
```

---

## Testing Strategy

### Unit Tests

| Component | Test Focus |
|-----------|------------|
| ViewModel | State transitions, action handling |
| Services | Message encoding/decoding |
| Models | Data parsing, validation |

### Integration Tests

| Scenario | Description |
|----------|-------------|
| Connection | WebSocket connect/disconnect cycles |
| Messaging | Send and receive message flow |
| Reconnection | Recovery from connection loss |

### UI Tests

| Flow | Description |
|------|-------------|
| Chat | Send message, view history |
| Auth | Login, logout, session handling |
| Navigation | Screen transitions |

---

## Best Practices

1. **Keep Views Dumb**: Views should only render state, not contain business logic
2. **Single Source of Truth**: UI state lives in ViewModel
3. **Unidirectional Data Flow**: State flows down, events flow up
4. **Immutable State**: Use data classes/structs for state
5. **Handle All States**: Loading, success, error, empty states
6. **Lifecycle Awareness**: Clean up subscriptions in onCleared/deinit

---

*For API details, see [API Integration](api-integration.md)*
