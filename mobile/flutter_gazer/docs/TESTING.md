# Flutter Gazer Testing Guide

Comprehensive testing documentation for the Waddles Gazer mobile streaming application. This guide covers unit tests, widget tests, integration tests, and end-to-end test strategies for ensuring code quality and stability.

---

## Table of Contents

1. [Testing Strategy](#testing-strategy)
2. [Test Structure](#test-structure)
3. [Unit Tests](#unit-tests)
4. [Widget Tests](#widget-tests)
5. [Integration Tests](#integration-tests)
6. [End-to-End Tests](#end-to-end-tests)
7. [Running Tests](#running-tests)
8. [Coverage Analysis](#coverage-analysis)
9. [Mocking & Dependencies](#mocking--dependencies)
10. [Test Examples](#test-examples)

---

## Testing Strategy

### Test Pyramid

Flutter Gazer follows the standard test pyramid approach:

```
        /\
       /  \     E2E Tests (5-10%)
      /____\    - Full user flows
     /      \   - Critical paths only
    /________\

    /        \
   /  Widget  \  Widget Tests (30-40%)
  /   Tests    \ - Screen rendering
 /______________\- User interactions

 /            \
/  Unit Tests  \ Unit Tests (50-65%)
/______________\- Models & services
               - Business logic
               - API interactions
```

### Test Coverage Goals

- **Unit Tests**: 70-80% code coverage for services, models, and utilities
- **Widget Tests**: Cover 3-5 critical user flows per screen
- **Integration Tests**: Test service + API integration for core features
- **E2E Tests**: Test critical user journeys (login, stream setup, streaming)

### Test Priorities

1. **Critical Path**: Authentication, streaming setup, stream start/stop
2. **Data Models**: StreamConfig, Community, Member models
3. **Services**: WaddleBotService, AuthService, RTMP service
4. **UI Flows**: Login screen, streaming preview, settings
5. **Edge Cases**: Network errors, permission handling, cleanup

---

## Test Structure

### Directory Organization

```
test/
├── unit/                           # Unit tests for services & models
│   ├── models/
│   │   ├── stream_config_test.dart
│   │   ├── auth_test.dart
│   │   └── community_test.dart
│   ├── services/
│   │   ├── waddlebot_service_test.dart
│   │   ├── waddlebot_auth_service_test.dart
│   │   ├── rtmp_service_test.dart
│   │   └── settings_service_test.dart
│   └── utils/
│       └── helpers_test.dart
│
├── widget/                         # Widget & screen tests
│   ├── screens/
│   │   ├── login_screen_test.dart
│   │   ├── stream_setup_test.dart
│   │   ├── streaming_preview_test.dart
│   │   └── settings_screen_test.dart
│   └── widgets/
│       └── custom_widget_test.dart
│
├── integration/                    # Integration tests
│   ├── auth_flow_test.dart
│   ├── streaming_setup_test.dart
│   └── service_integration_test.dart
│
├── e2e/                            # End-to-end tests
│   ├── login_to_stream_test.dart
│   ├── community_browsing_test.dart
│   └── critical_paths_test.dart
│
└── mocks/                          # Shared mock implementations
    ├── mock_waddlebot_service.dart
    ├── mock_auth_service.dart
    └── mock_dio_client.dart
```

### Test File Naming

- Unit tests: `<feature>_test.dart` (e.g., `waddlebot_service_test.dart`)
- Widget tests: `<screen>_test.dart` (e.g., `login_screen_test.dart`)
- Integration tests: `<flow>_test.dart` (e.g., `auth_flow_test.dart`)
- E2E tests: `<scenario>_test.dart` (e.g., `login_to_stream_test.dart`)

---

## Unit Tests

Unit tests verify business logic in isolation with mocked dependencies.

### Testing Models

Models should be immutable and testable. Focus on copyWith methods and computed properties.

**Example: StreamConfig Model Tests**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:gazer_waddlebot/models/stream_config.dart';

void main() {
  group('StreamConfig', () {
    test('fullUrl constructs correct RTMP URL', () {
      final config = StreamConfig(
        rtmpUrl: 'rtmp://server.com/app',
        streamKey: 'mykey123',
      );
      expect(config.fullUrl, 'rtmp://server.com/app/mykey123');
    });

    test('fullUrl handles trailing slash', () {
      final config = StreamConfig(
        rtmpUrl: 'rtmp://server.com/app/',
        streamKey: 'mykey123',
      );
      expect(config.fullUrl, 'rtmp://server.com/app/mykey123');
    });

    test('fullUrl returns rtmpUrl when streamKey is empty', () {
      final config = StreamConfig(
        rtmpUrl: 'rtmp://server.com/app',
        streamKey: '',
      );
      expect(config.fullUrl, 'rtmp://server.com/app');
    });

    test('copyWith updates fields correctly', () {
      final original = StreamConfig(
        width: 1280,
        height: 720,
        fps: 30,
      );

      final updated = original.copyWith(
        fps: 60,
        videoBitrate: 5000000,
      );

      expect(updated.width, 1280);
      expect(updated.fps, 60);
      expect(updated.videoBitrate, 5000000);
    });

    test('copyWith maintains original when no parameters provided', () {
      final original = StreamConfig(
        width: 1920,
        height: 1080,
      );

      final copied = original.copyWith();

      expect(copied.width, 1920);
      expect(copied.height, 1080);
    });

    test('default values are set correctly', () {
      final config = StreamConfig();

      expect(config.width, 1280);
      expect(config.height, 720);
      expect(config.fps, 30);
      expect(config.videoBitrate, 3000000);
    });
  });
}
```

### Testing Services

Services often depend on external APIs or other services. Use mockito to mock dependencies.

**Example: WaddlesService Tests**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:dio/dio.dart';
import 'package:gazer_waddlebot/services/waddlebot_service.dart';
import 'package:gazer_waddlebot/services/waddlebot_auth_service.dart';
import 'package:gazer_waddlebot/models/stream_config.dart';

@GenerateMocks([WaddleBotAuthService, Dio])
void main() {
  late WaddleBotService waddleBotService;
  late MockWaddleBotAuthService mockAuthService;
  late MockDio mockDio;

  setUp(() {
    mockAuthService = MockWaddleBotAuthService();
    mockDio = MockDio();
    waddleBotService = WaddleBotService(
      authService: mockAuthService,
      dio: mockDio,
    );
  });

  tearDown(() {
    waddleBotService.dispose();
  });

  group('WaddleBotService', () {
    test('reportStreamStarted creates active stream ID', () async {
      when(mockDio.post(
        any,
        data: anyNamed('data'),
        options: anyNamed('options'),
      )).thenAnswer((_) async => Response(
        requestOptions: RequestOptions(path: ''),
        statusCode: 200,
      ));

      final config = StreamConfig(width: 1280, height: 720);
      await waddleBotService.reportStreamStarted(config);

      verify(mockDio.post(
        '/router/events',
        data: anyNamed('data'),
        options: anyNamed('options'),
      )).called(1);
    });

    test('reportStreamStopped cancels metrics timer', () async {
      when(mockDio.post(
        any,
        data: anyNamed('data'),
        options: anyNamed('options'),
      )).thenAnswer((_) async => Response(
        requestOptions: RequestOptions(path: ''),
        statusCode: 200,
      ));

      final config = StreamConfig();
      await waddleBotService.reportStreamStarted(config);
      await waddleBotService.reportStreamStopped();

      verify(mockDio.post(
        '/router/events',
        data: anyNamed('data'),
        options: anyNamed('options'),
      )).called(2); // Start + Stop events
    });

    test('reportStreamError includes error message', () async {
      when(mockDio.post(
        any,
        data: anyNamed('data'),
        options: anyNamed('options'),
      )).thenAnswer((_) async => Response(
        requestOptions: RequestOptions(path: ''),
        statusCode: 200,
      ));

      final config = StreamConfig();
      await waddleBotService.reportStreamStarted(config);
      await waddleBotService.reportStreamError('Connection timeout');

      final calls = verify(mockDio.post(any, data: captureAnyNamed('data'), options: anyNamed('options')))
          .captured;
      expect(calls.length, 2);
    });

    test('handle network errors gracefully', () async {
      when(mockDio.post(
        any,
        data: anyNamed('data'),
        options: anyNamed('options'),
      )).thenThrow(DioException(
        requestOptions: RequestOptions(path: ''),
        error: 'Connection failed',
      ));

      final config = StreamConfig();
      // Should not throw despite network error
      expect(
        () => waddleBotService.reportStreamStarted(config),
        returnsNormally,
      );
    });

    test('includes auth token in request headers when available', () async {
      when(mockAuthService.accessToken).thenReturn('test-token-123');
      when(mockDio.post(
        any,
        data: anyNamed('data'),
        options: anyNamed('options'),
      )).thenAnswer((_) async => Response(
        requestOptions: RequestOptions(path: ''),
        statusCode: 200,
      ));

      final config = StreamConfig();
      await waddleBotService.reportStreamStarted(config);

      final capturedOptions = verify(mockDio.post(
        any,
        data: anyNamed('data'),
        options: captureAnyNamed('options'),
      )).captured.last as Options;

      expect(
        capturedOptions.headers?['Authorization'],
        'Bearer test-token-123',
      );
    });
  });
}
```

**Example: Waddles Authentication Service Tests**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:dio/dio.dart';
import 'package:gazer_waddlebot/services/waddlebot_auth_service.dart';

@GenerateMocks([Dio])
void main() {
  late WaddleBotAuthService authService;
  late MockDio mockDio;

  setUp(() {
    mockDio = MockDio();
    authService = WaddleBotAuthService(dio: mockDio);
  });

  group('WaddleBotAuthService', () {
    test('login stores access token', () async {
      when(mockDio.post(
        any,
        data: anyNamed('data'),
        options: anyNamed('options'),
      )).thenAnswer((_) async => Response(
        requestOptions: RequestOptions(path: ''),
        statusCode: 200,
        data: {
          'token': 'access-token-123',
          'refreshToken': 'refresh-token-456',
        },
      ));

      await authService.login('user@example.com', 'password123');

      expect(authService.accessToken, 'access-token-123');
      expect(authService.refreshToken, 'refresh-token-456');
    });

    test('logout clears tokens', () async {
      authService.setTokens('token', 'refresh');
      expect(authService.accessToken, 'token');

      await authService.logout();

      expect(authService.accessToken, isNull);
      expect(authService.refreshToken, isNull);
    });

    test('isAuthenticated returns true when token exists', () {
      authService.setTokens('token', 'refresh');
      expect(authService.isAuthenticated, true);
    });

    test('isAuthenticated returns false when token is null', () {
      expect(authService.isAuthenticated, false);
    });

    test('login throws on invalid credentials', () async {
      when(mockDio.post(
        any,
        data: anyNamed('data'),
        options: anyNamed('options'),
      )).thenThrow(DioException(
        requestOptions: RequestOptions(path: ''),
        response: Response(
          requestOptions: RequestOptions(path: ''),
          statusCode: 401,
          data: {'error': 'Invalid credentials'},
        ),
      ));

      expect(
        () => authService.login('user@example.com', 'wrong'),
        throwsA(isA<DioException>()),
      );
    });
  });
}
```

---

## Widget Tests

Widget tests verify UI behavior and user interactions in a Flutter-specific testing environment.

### Testing Screens

**Example: Login Screen Widget Test**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:gazer_waddlebot/screens/auth/login_screen.dart';
import 'package:gazer_waddlebot/services/waddlebot_auth_service.dart';

@GenerateMocks([WaddleBotAuthService])
void main() {
  late MockWaddleBotAuthService mockAuthService;

  setUp(() {
    mockAuthService = MockWaddleBotAuthService();
  });

  group('LoginScreen Widget Tests', () {
    testWidgets('displays login form elements', (WidgetTester tester) async {
      await tester.pumpWidget(MaterialApp(
        home: LoginScreen(authService: mockAuthService),
      ));

      expect(find.byType(TextField), findsWidgets);
      expect(find.byType(ElevatedButton), findsWidgets);
    });

    testWidgets('email field accepts input', (WidgetTester tester) async {
      await tester.pumpWidget(MaterialApp(
        home: LoginScreen(authService: mockAuthService),
      ));

      final emailField = find.byKey(const Key('emailField'));
      await tester.enterText(emailField, 'user@example.com');
      await tester.pumpAndSettle();

      expect(find.text('user@example.com'), findsOneWidget);
    });

    testWidgets('login button submits form', (WidgetTester tester) async {
      when(mockAuthService.login(any, any))
          .thenAnswer((_) async => {});

      await tester.pumpWidget(MaterialApp(
        home: LoginScreen(authService: mockAuthService),
        routes: {
          '/main': (context) => const Scaffold(),
        },
      ));

      await tester.enterText(
        find.byKey(const Key('emailField')),
        'user@example.com',
      );
      await tester.enterText(
        find.byKey(const Key('passwordField')),
        'password123',
      );

      await tester.tap(find.byType(ElevatedButton));
      await tester.pumpAndSettle();

      verify(mockAuthService.login('user@example.com', 'password123'))
          .called(1);
    });

    testWidgets('displays error message on login failure',
        (WidgetTester tester) async {
      when(mockAuthService.login(any, any))
          .thenThrow(Exception('Login failed'));

      await tester.pumpWidget(MaterialApp(
        home: LoginScreen(authService: mockAuthService),
      ));

      await tester.enterText(
        find.byKey(const Key('emailField')),
        'user@example.com',
      );
      await tester.enterText(
        find.byKey(const Key('passwordField')),
        'wrong',
      );

      await tester.tap(find.byType(ElevatedButton));
      await tester.pumpAndSettle();

      expect(find.byType(SnackBar), findsOneWidget);
    });

    testWidgets('requires email and password before submitting',
        (WidgetTester tester) async {
      await tester.pumpWidget(MaterialApp(
        home: LoginScreen(authService: mockAuthService),
      ));

      final submitButton = find.byType(ElevatedButton);
      expect(tester.widget<ElevatedButton>(submitButton).enabled, false);

      await tester.enterText(
        find.byKey(const Key('emailField')),
        'user@example.com',
      );
      await tester.pumpAndSettle();

      expect(tester.widget<ElevatedButton>(submitButton).enabled, false);

      await tester.enterText(
        find.byKey(const Key('passwordField')),
        'password123',
      );
      await tester.pumpAndSettle();

      expect(tester.widget<ElevatedButton>(submitButton).enabled, true);
    });
  });
}
```

### Testing Custom Widgets

**Example: Stream Quality Selector Widget Test**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gazer_waddlebot/models/stream_config.dart';
import 'package:gazer_waddlebot/screens/streaming/quality_presets.dart';

void main() {
  group('QualityPresetsWidget', () {
    testWidgets('displays all quality presets', (WidgetTester tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: QualityPresetsWidget(
            onPresetSelected: (_) {},
          ),
        ),
      ));

      expect(find.text('1080p 60fps'), findsOneWidget);
      expect(find.text('720p 60fps'), findsOneWidget);
      expect(find.text('720p 30fps'), findsOneWidget);
      expect(find.text('480p 30fps'), findsOneWidget);
    });

    testWidgets('calls callback when preset selected',
        (WidgetTester tester) async {
      StreamConfig? selectedConfig;

      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: QualityPresetsWidget(
            onPresetSelected: (config) {
              selectedConfig = config;
            },
          ),
        ),
      ));

      await tester.tap(find.text('1080p 60fps'));
      await tester.pumpAndSettle();

      expect(selectedConfig, isNotNull);
      expect(selectedConfig!.width, 1920);
      expect(selectedConfig!.height, 1080);
      expect(selectedConfig!.fps, 60);
    });

    testWidgets('highlights selected preset', (WidgetTester tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: QualityPresetsWidget(
            onPresetSelected: (_) {},
          ),
        ),
      ));

      await tester.tap(find.text('720p 60fps'));
      await tester.pumpAndSettle();

      final tile = find.byKey(const Key('preset_720p_60fps'));
      expect(
        tester.widget<Container>(tile).decoration,
        isA<BoxDecoration>(),
      );
    });
  });
}
```

---

## Integration Tests

Integration tests verify how multiple services work together.

**Example: Authentication Flow Integration Test**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:dio/dio.dart';
import 'package:gazer_waddlebot/services/waddlebot_auth_service.dart';
import 'package:gazer_waddlebot/services/settings_service.dart';

@GenerateMocks([Dio])
void main() {
  late WaddleBotAuthService authService;
  late SettingsService settingsService;
  late MockDio mockDio;

  setUp(() {
    mockDio = MockDio();
    authService = WaddleBotAuthService(dio: mockDio);
    settingsService = SettingsService();
  });

  group('Auth Flow Integration', () {
    test('login updates auth state and saves preferences', () async {
      when(mockDio.post(
        any,
        data: anyNamed('data'),
        options: anyNamed('options'),
      )).thenAnswer((_) async => Response(
        requestOptions: RequestOptions(path: ''),
        statusCode: 200,
        data: {
          'token': 'token123',
          'refreshToken': 'refresh123',
          'user': {
            'id': 'user123',
            'email': 'user@example.com',
            'premium': true,
          },
        },
      ));

      expect(authService.isAuthenticated, false);

      await authService.login('user@example.com', 'password');

      expect(authService.isAuthenticated, true);
      expect(authService.accessToken, 'token123');
      expect(authService.refreshToken, 'refresh123');

      // Verify settings were updated
      final email = await settingsService.getUserEmail();
      expect(email, 'user@example.com');
    });

    test('logout clears both auth state and preferences', () async {
      authService.setTokens('token', 'refresh');
      await settingsService.setUserEmail('user@example.com');

      expect(authService.isAuthenticated, true);

      await authService.logout();

      expect(authService.isAuthenticated, false);
      final email = await settingsService.getUserEmail();
      expect(email, isNull);
    });

    test('token refresh preserves auth state', () async {
      authService.setTokens('old-token', 'refresh-token');

      when(mockDio.post(
        any,
        data: anyNamed('data'),
        options: anyNamed('options'),
      )).thenAnswer((_) async => Response(
        requestOptions: RequestOptions(path: ''),
        statusCode: 200,
        data: {
          'token': 'new-token',
          'refreshToken': 'new-refresh-token',
        },
      ));

      await authService.refreshToken();

      expect(authService.accessToken, 'new-token');
      expect(authService.refreshToken, 'new-refresh-token');
    });
  });
}
```

**Example: Streaming Setup Integration Test**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:gazer_waddlebot/services/waddlebot_service.dart';
import 'package:gazer_waddlebot/services/settings_service.dart';
import 'package:gazer_waddlebot/models/stream_config.dart';

@GenerateMocks([WaddleBotService])
void main() {
  late MockWaddleBotService mockWaddleBotService;
  late SettingsService settingsService;

  setUp(() {
    mockWaddleBotService = MockWaddleBotService();
    settingsService = SettingsService();
  });

  group('Streaming Setup Integration', () {
    test('save and load stream configuration', () async {
      final config = StreamConfig(
        width: 1920,
        height: 1080,
        fps: 60,
        rtmpUrl: 'rtmp://server.com/app',
        streamKey: 'key123',
      );

      await settingsService.saveStreamConfig(config);
      final loaded = await settingsService.loadStreamConfig();

      expect(loaded.width, 1920);
      expect(loaded.height, 1080);
      expect(loaded.fps, 60);
      expect(loaded.rtmpUrl, 'rtmp://server.com/app');
    });

    test('stream start triggers service reporting', () async {
      when(mockWaddleBotService.reportStreamStarted(any))
          .thenAnswer((_) async => {});

      final config = StreamConfig();
      await mockWaddleBotService.reportStreamStarted(config);

      verify(mockWaddleBotService.reportStreamStarted(config)).called(1);
    });

    test('stream stop is properly reported', () async {
      when(mockWaddleBotService.reportStreamStopped())
          .thenAnswer((_) async => {});

      await mockWaddleBotService.reportStreamStopped();

      verify(mockWaddleBotService.reportStreamStopped()).called(1);
    });
  });
}
```

---

## End-to-End Tests

E2E tests verify complete user workflows. These typically use the Flutter Driver or Integration Test packages.

**Example: E2E Login to Streaming Test**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:gazer_waddlebot/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Login to Streaming E2E', () {
    testWidgets('Complete user flow: login -> stream setup -> stream',
        (WidgetTester tester) async {
      app.main();
      await tester.pumpAndSettle();

      // Verify login screen appears
      expect(find.byType(TextField), findsWidgets);

      // Enter credentials
      await tester.enterText(
        find.byKey(const Key('emailField')),
        'testuser@example.com',
      );
      await tester.enterText(
        find.byKey(const Key('passwordField')),
        'testpass123',
      );

      // Tap login button
      await tester.tap(find.byType(ElevatedButton));
      await tester.pumpAndSettle(const Duration(seconds: 2));

      // Should navigate to main screen
      expect(find.byType(BottomNavigationBar), findsOneWidget);

      // Navigate to streaming setup
      await tester.tap(find.byIcon(Icons.videocam));
      await tester.pumpAndSettle();

      // Verify stream setup screen
      expect(find.text('Stream Setup'), findsOneWidget);

      // Select quality preset
      await tester.tap(find.text('1080p 60fps'));
      await tester.pumpAndSettle();

      // Enter RTMP details
      await tester.enterText(
        find.byKey(const Key('rtmpUrlField')),
        'rtmp://live.example.com/app',
      );
      await tester.enterText(
        find.byKey(const Key('streamKeyField')),
        'stream_key_123',
      );

      // Start streaming
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle(const Duration(seconds: 2));

      // Verify streaming preview appears
      expect(find.byType(CameraPreview), findsOneWidget);
      expect(find.text('Live'), findsOneWidget);
    });

    testWidgets('Settings navigation and preferences persistence',
        (WidgetTester tester) async {
      app.main();
      await tester.pumpAndSettle();

      // Login first
      await tester.enterText(
        find.byKey(const Key('emailField')),
        'user@example.com',
      );
      await tester.enterText(
        find.byKey(const Key('passwordField')),
        'password',
      );
      await tester.tap(find.byType(ElevatedButton));
      await tester.pumpAndSettle(const Duration(seconds: 1));

      // Navigate to settings
      await tester.tap(find.byIcon(Icons.settings));
      await tester.pumpAndSettle();

      // Toggle a setting
      await tester.tap(find.byKey(const Key('darkModeToggle')));
      await tester.pumpAndSettle();

      // Verify setting is toggled
      expect(
        tester.widget<Switch>(find.byKey(const Key('darkModeToggle'))).value,
        true,
      );

      // Pop back and verify setting persists
      await tester.pageBack();
      await tester.pumpAndSettle();
      await tester.tap(find.byIcon(Icons.settings));
      await tester.pumpAndSettle();

      expect(
        tester.widget<Switch>(find.byKey(const Key('darkModeToggle'))).value,
        true,
      );
    });
  });
}
```

---

## Running Tests

### Run All Tests

```bash
# Run all unit, widget, and integration tests
flutter test

# Run tests with coverage
flutter test --coverage

# Run tests with verbose output
flutter test -v

# Run tests with specific pattern
flutter test test/unit/models/
```

### Run Specific Test Types

```bash
# Run only unit tests
flutter test test/unit/

# Run only widget tests
flutter test test/widget/

# Run only integration tests
flutter test test/integration/

# Run a specific test file
flutter test test/unit/services/waddlebot_service_test.dart

# Run tests matching a pattern
flutter test --name "StreamConfig"
```

### Run E2E Tests

```bash
# On physical device or emulator
flutter drive --target=test_driver/app.dart

# Or using integration_test
flutter test integration_test/
```

### Test Execution During Development

```bash
# Watch mode - re-run tests on file changes
flutter test --watch

# Run tests on save for specific files
flutter test test/unit/models/ --watch
```

---

## Coverage Analysis

### Generate Coverage Report

```bash
# Generate coverage data
flutter test --coverage

# View coverage report (requires lcov)
# On macOS/Linux
genhtml coverage/lcov.info -o coverage/html
open coverage/html/index.html

# On Windows
genhtml coverage/lcov.info -o coverage\html
start coverage\html\index.html
```

### Coverage Configuration

Create `analysis_options.yaml`:

```yaml
analyzer:
  exclude:
    - test/**
    - lib/generated/**

  errors:
    missing_required_param: warning
    missing_return: warning
    todo: ignore

linter:
  rules:
    - avoid_empty_else
    - avoid_null_chars_in_string_literals
    - avoid_relative_lib_imports
    - avoid_returning_null_for_future
    - avoid_slow_async_io
    - cancel_subscriptions
    - close_sinks
    - comment_references
    - control_flow_in_finally
    - empty_statements
    - hash_and_equals
    - invariant_booleans
    - iterable_contains_unrelated_type
    - list_remove_unrelated_type
    - literal_only_boolean_expressions
    - no_adjacent_strings_in_list
    - no_duplicate_case_values
    - prefer_void_to_null
    - test_types_in_equals
    - throw_in_finally
    - unnecessary_statements
    - unrelated_type_equality_checks
```

### Coverage Targets

- **Services**: 80% minimum coverage
- **Models**: 90% minimum coverage (mostly getters/setters)
- **Screens**: 60% minimum coverage (focus on logic, not rendering)
- **Utilities**: 85% minimum coverage

---

## Mocking & Dependencies

### Using Mockito

Generate mocks using build_runner:

```bash
flutter pub run build_runner build
# Or watch mode
flutter pub run build_runner watch
```

### Mock Examples

**Mock WaddleBotService**

```dart
import 'package:mockito/mockito.dart';
import 'package:gazer_waddlebot/services/waddlebot_service.dart';

class MockWaddleBotService extends Mock implements WaddleBotService {}

// Usage
final mockService = MockWaddleBotService();
when(mockService.reportStreamStarted(any)).thenAnswer((_) async => {});
```

**Mock Dio Client**

```dart
import 'package:mockito/mockito.dart';
import 'package:dio/dio.dart';

class MockDio extends Mock implements Dio {
  @override
  Future<Response<T>> post<T>(
    String path, {
    data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: {'success': true} as T,
    );
  }
}
```

**Mock SharedPreferences**

```dart
import 'package:mockito/mockito.dart';
import 'package:shared_preferences/shared_preferences.dart';

class MockSharedPreferences extends Mock implements SharedPreferences {
  final Map<String, dynamic> _store = {};

  @override
  Future<bool> setString(String key, String value) async {
    _store[key] = value;
    return true;
  }

  @override
  String? getString(String key) => _store[key] as String?;

  @override
  Future<bool> remove(String key) async {
    _store.remove(key);
    return true;
  }
}
```

### Testing with Dependencies

```dart
void main() {
  group('Service with Dependencies', () {
    late MyService service;
    late MockDependency mockDep;

    setUp(() {
      mockDep = MockDependency();
      service = MyService(mockDep);
    });

    test('handles dependency response', () async {
      when(mockDep.fetchData()).thenAnswer((_) async => {'id': 1});

      final result = await service.processData();

      expect(result.id, 1);
      verify(mockDep.fetchData()).called(1);
    });
  });
}
```

---

## Test Examples

### Complete Unit Test Example: Settings Service

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:gazer_waddlebot/services/settings_service.dart';

@GenerateMocks([SharedPreferences])
void main() {
  late SettingsService settingsService;
  late MockSharedPreferences mockPrefs;

  setUp(() {
    mockPrefs = MockSharedPreferences();
    settingsService = SettingsService(prefs: mockPrefs);
  });

  group('SettingsService', () {
    const testEmail = 'user@example.com';
    const testKey = 'settings_email';

    test('saves user email to preferences', () async {
      when(mockPrefs.setString(testKey, testEmail))
          .thenAnswer((_) async => true);

      await settingsService.setUserEmail(testEmail);

      verify(mockPrefs.setString(testKey, testEmail)).called(1);
    });

    test('retrieves user email from preferences', () async {
      when(mockPrefs.getString(testKey)).thenReturn(testEmail);

      final result = await settingsService.getUserEmail();

      expect(result, testEmail);
      verify(mockPrefs.getString(testKey)).called(1);
    });

    test('returns null when email not set', () async {
      when(mockPrefs.getString(testKey)).thenReturn(null);

      final result = await settingsService.getUserEmail();

      expect(result, null);
    });

    test('clears all settings', () async {
      when(mockPrefs.clear()).thenAnswer((_) async => true);

      await settingsService.clearAll();

      verify(mockPrefs.clear()).called(1);
    });

    test('handles save failure gracefully', () async {
      when(mockPrefs.setString(testKey, any))
          .thenThrow(Exception('Storage error'));

      expect(
        () => settingsService.setUserEmail(testEmail),
        throwsException,
      );
    });
  });
}
```

### Complete Widget Test Example: Stream Preview

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:gazer_waddlebot/screens/streaming/streaming_preview.dart';
import 'package:gazer_waddlebot/services/rtmp_service.dart';

@GenerateMocks([RtmpService])
void main() {
  late MockRtmpService mockRtmpService;

  setUp(() {
    mockRtmpService = MockRtmpService();
  });

  group('StreamingPreview Widget Tests', () {
    testWidgets('displays camera preview while streaming',
        (WidgetTester tester) async {
      when(mockRtmpService.isStreaming).thenReturn(true);

      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: StreamingPreviewScreen(
            rtmpService: mockRtmpService,
          ),
        ),
      ));

      expect(find.byType(CameraPreview), findsOneWidget);
      expect(find.text('Live'), findsOneWidget);
    });

    testWidgets('shows stream stats overlay', (WidgetTester tester) async {
      when(mockRtmpService.isStreaming).thenReturn(true);
      when(mockRtmpService.bitrate).thenReturn('2.5 Mbps');
      when(mockRtmpService.frameRate).thenReturn(60);

      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: StreamingPreviewScreen(
            rtmpService: mockRtmpService,
          ),
        ),
      ));

      expect(find.text('2.5 Mbps'), findsOneWidget);
      expect(find.text('60 fps'), findsOneWidget);
    });

    testWidgets('stop button triggers stream stop', (WidgetTester tester) async {
      when(mockRtmpService.isStreaming).thenReturn(true);
      when(mockRtmpService.stopStream()).thenAnswer((_) async => {});

      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: StreamingPreviewScreen(
            rtmpService: mockRtmpService,
          ),
        ),
      ));

      await tester.tap(find.byKey(const Key('stopStreamButton')));
      await tester.pumpAndSettle();

      verify(mockRtmpService.stopStream()).called(1);
    });
  });
}
```

---

## Best Practices

### Testing Guidelines

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Clarity**: Test names should clearly describe what is being tested
3. **Arrange-Act-Assert**: Follow AAA pattern in test structure
4. **Mocking**: Mock external dependencies; test single units in isolation
5. **Cleanup**: Use tearDown to clean up resources and state
6. **Coverage**: Aim for high coverage on critical paths and business logic
7. **Performance**: Keep tests fast; mock network calls and slow operations
8. **Readability**: Use meaningful variable names and comments
9. **No Sleeps**: Avoid `sleep()` or hard timeouts; use `pumpAndSettle()`
10. **Realistic Data**: Use realistic mock data that reflects production scenarios

### Common Pitfalls to Avoid

- ❌ Writing tests that depend on test execution order
- ❌ Using `sleep()` instead of `pumpAndSettle()`
- ❌ Testing UI rendering instead of logic
- ❌ Not mocking external dependencies
- ❌ Writing overly complex tests that are hard to understand
- ❌ Ignoring error cases and edge cases
- ❌ Not cleaning up resources (timers, subscriptions)
- ❌ Testing private implementation details instead of public APIs

---

## Pre-Commit Testing Checklist

Before committing code:

- [ ] Run `flutter test` - all tests pass
- [ ] Run `flutter test --coverage` - coverage meets targets
- [ ] Run `flutter analyze` - no analysis errors
- [ ] Run `flutter format .` - code is formatted
- [ ] Test new features manually
- [ ] Verify error handling works
- [ ] Test on both iOS and Android (if changed native code)

---

## Resources

- [Flutter Testing Documentation](https://flutter.dev/docs/testing)
- [Unit Testing with Mockito](https://pub.dev/packages/mockito)
- [Widget Testing](https://flutter.dev/docs/testing/widget-test-introduction)
- [Integration Testing](https://flutter.dev/docs/testing/integration-tests)
- [Coverage Analysis](https://github.com/google/coverage.dart)

---

**Last Updated**: January 30, 2026

**Testing Framework Versions**:
- flutter_test: latest (included with Flutter SDK)
- mockito: ^5.4.0
- build_runner: ^2.4.0
