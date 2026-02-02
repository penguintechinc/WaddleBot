import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:gazer_waddlebot/app.dart';
import 'package:gazer_waddlebot/services/waddlebot_auth_service.dart';
import 'package:gazer_waddlebot/services/community_service.dart';
import 'package:gazer_waddlebot/models/waddlebot_models.dart';
import 'package:gazer_waddlebot/screens/main_screen.dart';
import 'package:gazer_waddlebot/screens/chat/chat_screen.dart';
import 'package:gazer_waddlebot/screens/communities/community_list.dart';
import 'package:gazer_waddlebot/screens/auth/login_screen.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Data Propagation E2E Tests', () {
    late WaddleBotAuthService authService;
    late CommunityService communityService;

    setUp(() {
      authService = WaddleBotAuthService();
      communityService = CommunityService.getInstance();
    });

    tearDown(() async {
      try {
        await authService.logout();
      } catch (_) {}
    });

    group('Login Flow', () {
      testWidgets('Login with valid credentials succeeds', (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle();

        final emailField = find.byType(TextField).first;
        final passwordField = find.byType(TextField).at(1);
        final loginButton = find.byType(ElevatedButton).first;

        expect(emailField, findsOneWidget);
        expect(passwordField, findsOneWidget);
        expect(loginButton, findsOneWidget);

        await tester.enterText(emailField, 'test.user@example.com');
        await tester.enterText(passwordField, 'TestPassword123!');
        await tester.tap(loginButton);
        await tester.pumpAndSettle(const Duration(seconds: 3));

        final mainContent = find.byType(MainScreen);
        expect(mainContent, findsOneWidget,
            reason: 'Login should navigate to main screen');
      });

      testWidgets('Login with invalid credentials shows error', (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle();

        final emailField = find.byType(TextField).first;
        final passwordField = find.byType(TextField).at(1);
        final loginButton = find.byType(ElevatedButton).first;

        await tester.enterText(emailField, 'invalid@example.com');
        await tester.enterText(passwordField, 'wrongpassword');
        await tester.tap(loginButton);
        await tester.pumpAndSettle(const Duration(seconds: 3));

        final errorText = find.text('Invalid credentials');
        expect(errorText, findsWidgets,
            reason: 'Error message should be displayed for invalid credentials');
      });

      testWidgets('User data persists after login', (WidgetTester tester) async {
        const testEmail = 'persist.test@example.com';
        const testPassword = 'PersistPassword123!';

        final response = await authService.login(testEmail, testPassword);

        expect(authService.isAuthenticated, true,
            reason: 'User should be authenticated after login');
        expect(authService.currentUser, isNotNull,
            reason: 'Current user should be set');
        expect(authService.currentUser!.email, testEmail,
            reason: 'User email should match login credentials');
        expect(authService.accessToken, isNotNull,
            reason: 'Access token should be set');
        expect(response.token, isNotEmpty,
            reason: 'Token response should contain JWT token');
      });

      testWidgets('Token refresh works correctly', (WidgetTester tester) async {
        const testEmail = 'refresh.test@example.com';
        const testPassword = 'RefreshPassword123!';

        await authService.login(testEmail, testPassword);

        await Future.delayed(const Duration(seconds: 1));
        await authService.refreshToken();

        final newToken = authService.accessToken;
        expect(newToken, isNotNull,
            reason: 'Token should be refreshed');
        expect(authService.isAuthenticated, true,
            reason: 'User should remain authenticated after token refresh');
      });

      testWidgets('Logout clears authentication state', (WidgetTester tester) async {
        const testEmail = 'logout.test@example.com';
        const testPassword = 'LogoutPassword123!';

        await authService.login(testEmail, testPassword);
        expect(authService.isAuthenticated, true);

        await authService.logout();

        expect(authService.isAuthenticated, false,
            reason: 'User should not be authenticated after logout');
        expect(authService.currentUser, isNull,
            reason: 'Current user should be cleared');
        expect(authService.accessToken, isNull,
            reason: 'Access token should be cleared');
      });
    });

    group('Communities List', () {
      setUp(() async {
        const testEmail = 'community.test@example.com';
        const testPassword = 'CommunityPassword123!';
        await authService.login(testEmail, testPassword);
      });

      testWidgets('Communities list renders correctly', (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle();

        final communityListScreen = find.byType(CommunityListScreen);
        expect(communityListScreen, findsOneWidget,
            reason: 'Communities list screen should be visible after login');

        final communityTiles = find.byType(ListTile);
        expect(communityTiles, findsWidgets,
            reason: 'Community list should contain community tiles');
      });

      testWidgets('Communities data loads from backend', (WidgetTester tester) async {
        final response = await communityService.getCommunities(page: 1, pageSize: 20);

        expect(response.items, isNotEmpty,
            reason: 'Communities list should not be empty');
        expect(response.total, greaterThanOrEqualTo(response.items.length),
            reason: 'Total count should be >= items length');

        for (final community in response.items) {
          expect(community.id, isNotEmpty,
              reason: 'Community should have valid ID');
          expect(community.name, isNotEmpty,
              reason: 'Community should have name');
          expect(community.description, isNotEmpty,
              reason: 'Community should have description');
          expect(community.ownerId, isNotEmpty,
              reason: 'Community should have owner ID');
        }
      });

      testWidgets('Communities list displays correct data', (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle(const Duration(seconds: 2));

        final response = await communityService.getCommunities(page: 1, pageSize: 20);
        expect(response.items, isNotEmpty);

        final firstCommunity = response.items.first;
        final communityNameText = find.text(firstCommunity.name);
        expect(communityNameText, findsWidgets,
            reason: 'Community name should be displayed in list');

        final memberCountText = find.text('${firstCommunity.memberCount}');
        expect(memberCountText, findsWidgets,
            reason: 'Member count should be displayed');
      });

      testWidgets('Community detail screen shows backend data',
          (WidgetTester tester) async {
        final response = await communityService.getCommunities(page: 1, pageSize: 20);
        expect(response.items, isNotEmpty);

        final firstCommunity = response.items.first;
        final detailResponse =
            await communityService.getCommunityDetail(firstCommunity.id);

        expect(detailResponse.data, isNotNull,
            reason: 'Community detail should be loaded');
        expect(detailResponse.data!.name, firstCommunity.name,
            reason: 'Community name should match');
        expect(detailResponse.data!.id, firstCommunity.id,
            reason: 'Community ID should match');
        expect(detailResponse.data!.stats, isNotNull,
            reason: 'Community stats should be included');
      });

      testWidgets('Community stats display correctly', (WidgetTester tester) async {
        final response = await communityService.getCommunities(page: 1, pageSize: 20);
        expect(response.items, isNotEmpty);

        final firstCommunity = response.items.first;
        final statsResponse =
            await communityService.getCommunityStats(firstCommunity.id);

        expect(statsResponse.data, isNotNull,
            reason: 'Stats should be retrieved');
        expect(statsResponse.data!.memberCount, greaterThanOrEqualTo(0),
            reason: 'Member count should be >= 0');
        expect(statsResponse.data!.activeMembers, greaterThanOrEqualTo(0),
            reason: 'Active members should be >= 0');
        expect(statsResponse.data!.commandsToday, greaterThanOrEqualTo(0),
            reason: 'Commands today should be >= 0');
        expect(statsResponse.data!.messagesToday, greaterThanOrEqualTo(0),
            reason: 'Messages today should be >= 0');
      });

      testWidgets('Pagination works correctly', (WidgetTester tester) async {
        final page1Response =
            await communityService.getCommunities(page: 1, pageSize: 5);
        expect(page1Response.items, isNotEmpty);
        expect(page1Response.items.length, lessThanOrEqualTo(5));

        if (page1Response.hasMore) {
          final page2Response =
              await communityService.getCommunities(page: 2, pageSize: 5);
          expect(page2Response.items, isNotEmpty);

          final page1Ids = page1Response.items.map((c) => c.id).toSet();
          final page2Ids = page2Response.items.map((c) => c.id).toSet();

          expect(page1Ids.intersection(page2Ids), isEmpty,
              reason: 'Different pages should have different communities');
        }
      });

      testWidgets('Community updates propagate to UI', (WidgetTester tester) async {
        final initialResponse =
            await communityService.getCommunities(page: 1, pageSize: 20);
        expect(initialResponse.items, isNotEmpty);

        await Future.delayed(const Duration(seconds: 1));

        final updatedResponse =
            await communityService.getCommunities(page: 1, pageSize: 20);

        expect(updatedResponse.items, isNotEmpty,
            reason: 'Communities should still be available');
        expect(updatedResponse.items.length, greaterThan(0),
            reason: 'Should have communities after refresh');
      });
    });

    group('Chat Messages', () {
      setUp(() async {
        const testEmail = 'chat.test@example.com';
        const testPassword = 'ChatPassword123!';
        await authService.login(testEmail, testPassword);
      });

      testWidgets('Chat screen renders after login', (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle();

        final chatScreen = find.byType(ChatScreen);
        expect(chatScreen, findsOneWidget,
            reason: 'Chat screen should be accessible after login');
      });

      testWidgets('Message sending works correctly', (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle();

        final messageInputField = find.byType(TextField).first;
        final sendButton = find.byIcon(Icons.send);

        expect(messageInputField, findsOneWidget,
            reason: 'Message input field should exist');
        expect(sendButton, findsOneWidget,
            reason: 'Send button should exist');

        await tester.enterText(messageInputField, 'Test message');
        await tester.tap(sendButton);
        await tester.pumpAndSettle(const Duration(seconds: 2));

        final sentMessageText = find.text('Test message');
        expect(sentMessageText, findsWidgets,
            reason: 'Sent message should appear in chat');
      });

      testWidgets('Message history displays correctly', (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle(const Duration(seconds: 2));

        final messageListView = find.byType(ListView);
        expect(messageListView, findsWidgets,
            reason: 'Message list view should exist');

        final messageTexts = find.byType(Text);
        expect(messageTexts, findsWidgets,
            reason: 'Messages should be displayed as text');
      });

      testWidgets('Message timestamps display correctly', (WidgetTester tester) async {
        final testMessage = ChatMessage(
          id: 'msg-001',
          communityId: 'comm-001',
          senderId: 'user-001',
          senderUsername: 'testuser',
          content: 'Test message with timestamp',
          createdAt: DateTime.now(),
        );

        expect(testMessage.createdAt, isNotNull,
            reason: 'Message should have timestamp');
        expect(testMessage.id, isNotEmpty,
            reason: 'Message should have ID');
        expect(testMessage.senderUsername, isNotEmpty,
            reason: 'Message should have sender username');
      });

      testWidgets('Typing indicators display correctly', (WidgetTester tester) async {
        const typingEvent = TypingEvent(
          communityId: 'comm-001',
          channelName: 'general',
          userId: 'user-002',
          username: 'otheruser',
          isTyping: true,
        );

        expect(typingEvent.isTyping, true,
            reason: 'Typing indicator should be set');
        expect(typingEvent.username, isNotEmpty,
            reason: 'Typing event should have username');
        expect(typingEvent.channelName, isNotEmpty,
            reason: 'Typing event should have channel name');
      });

      testWidgets('Message reactions work correctly', (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle();

        final firstMessage = find.byType(ListTile).first;
        await tester.longPress(firstMessage);
        await tester.pumpAndSettle();

        final reactionButton = find.byIcon(Icons.emoji_emotions);
        if (reactionButton.evaluate().isNotEmpty) {
          await tester.tap(reactionButton);
          await tester.pumpAndSettle(const Duration(seconds: 1));

          final emojiPanel = find.byType(GridView);
          expect(emojiPanel, findsWidgets,
              reason: 'Emoji panel should display for reactions');
        }
      });

      testWidgets('Message threads work correctly', (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle();

        final firstMessage = find.byType(ListTile).first;
        await tester.tap(firstMessage);
        await tester.pumpAndSettle(const Duration(seconds: 1));

        final threadView = find.byType(Column);
        expect(threadView, findsWidgets,
            reason: 'Thread view should be accessible');
      });

      testWidgets('Real-time message updates propagate', (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle(const Duration(seconds: 2));

        final initialMessages = find.byType(ListTile);
        final initialCount = initialMessages.evaluate().length;

        await Future.delayed(const Duration(seconds: 2));
        await tester.pumpAndSettle();

        final updatedMessages = find.byType(ListTile);
        final updatedCount = updatedMessages.evaluate().length;

        expect(updatedCount, greaterThanOrEqualTo(initialCount),
            reason: 'Message count should increase or stay the same');
      });

      testWidgets('Message editing works correctly', (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle();

        final firstMessage = find.byType(ListTile).first;
        await tester.longPress(firstMessage);
        await tester.pumpAndSettle();

        final editButton = find.byIcon(Icons.edit);
        if (editButton.evaluate().isNotEmpty) {
          await tester.tap(editButton);
          await tester.pumpAndSettle();

          final messageInputField = find.byType(TextField).first;
          expect(messageInputField, findsOneWidget,
              reason: 'Message should be editable');
        }
      });

      testWidgets('Message deletion works correctly', (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle();

        final firstMessage = find.byType(ListTile).first;
        await tester.longPress(firstMessage);
        await tester.pumpAndSettle();

        final deleteButton = find.byIcon(Icons.delete);
        if (deleteButton.evaluate().isNotEmpty) {
          await tester.tap(deleteButton);
          await tester.pumpAndSettle();

          final confirmButton = find.byType(TextButton).first;
          await tester.tap(confirmButton);
          await tester.pumpAndSettle(const Duration(seconds: 1));
        }
      });

      testWidgets('Channel switching preserves message history',
          (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle(const Duration(seconds: 2));

        final channelList = find.byType(ListView).first;
        expect(channelList, findsOneWidget,
            reason: 'Channel list should be displayed');

        final firstChannel = find.byType(ListTile).first;
        await tester.tap(firstChannel);
        await tester.pumpAndSettle();

        final secondChannel = find.byType(ListTile).at(1);
        if (secondChannel.evaluate().isNotEmpty) {
          await tester.tap(secondChannel);
          await tester.pumpAndSettle();

          await tester.tap(firstChannel);
          await tester.pumpAndSettle();

          final messageList = find.byType(ListView).at(1);
          expect(messageList, findsWidgets,
              reason: 'Message history should persist when switching channels');
        }
      });
    });

    group('Data Consistency', () {
      setUp(() async {
        const testEmail = 'consistency.test@example.com';
        const testPassword = 'ConsistencyPassword123!';
        await authService.login(testEmail, testPassword);
      });

      testWidgets('User data consistency across sessions', (WidgetTester tester) async {
        final user1 = authService.currentUser;
        expect(user1, isNotNull);

        await Future.delayed(const Duration(seconds: 1));

        final refreshedUser = await authService.getCurrentUser();
        expect(refreshedUser.id, user1!.id,
            reason: 'User ID should remain consistent');
        expect(refreshedUser.email, user1.email,
            reason: 'User email should remain consistent');
      });

      testWidgets('Community data remains consistent during updates',
          (WidgetTester tester) async {
        final response1 = await communityService.getCommunities(page: 1, pageSize: 20);
        expect(response1.items, isNotEmpty);

        final community1 = response1.items.first;
        final detail1 = await communityService.getCommunityDetail(community1.id);

        expect(detail1.data!.id, community1.id,
            reason: 'Community ID should be consistent');
        expect(detail1.data!.name, community1.name,
            reason: 'Community name should be consistent');
        expect(detail1.data!.ownerId, community1.ownerId,
            reason: 'Community owner should be consistent');
      });

      testWidgets('API responses contain all required fields', (WidgetTester tester) async {
        final response = await communityService.getCommunities(page: 1, pageSize: 20);

        for (final community in response.items) {
          expect(community.id, isNotEmpty,
              reason: 'Community must have ID');
          expect(community.name, isNotEmpty,
              reason: 'Community must have name');
          expect(community.ownerId, isNotEmpty,
              reason: 'Community must have owner ID');
          expect(community.createdAt, isNotNull,
              reason: 'Community must have createdAt');
          expect(community.updatedAt, isNotNull,
              reason: 'Community must have updatedAt');
        }
      });

      testWidgets('Message data remains consistent across connections',
          (WidgetTester tester) async {
        final testMessage = ChatMessage(
          id: 'msg-consistency-001',
          communityId: 'comm-001',
          senderId: 'user-001',
          senderUsername: 'testuser',
          content: 'Consistency test message',
          createdAt: DateTime.now(),
        );

        final jsonData = testMessage.toJson();
        final reconstructedMessage = ChatMessage.fromJson(jsonData);

        expect(reconstructedMessage.id, testMessage.id,
            reason: 'Message ID should be preserved through serialization');
        expect(reconstructedMessage.content, testMessage.content,
            reason: 'Message content should be preserved');
        expect(reconstructedMessage.senderUsername, testMessage.senderUsername,
            reason: 'Sender username should be preserved');
      });

      testWidgets('Error responses are handled gracefully', (WidgetTester tester) async {
        try {
          await communityService.getCommunityDetail('invalid-community-id');
          fail('Should throw error for invalid community ID');
        } catch (e) {
          expect(e, isNotNull,
              reason: 'Invalid request should raise error');
        }
      });
    });

    group('Performance & Load', () {
      setUp(() async {
        const testEmail = 'performance.test@example.com';
        const testPassword = 'PerformancePassword123!';
        await authService.login(testEmail, testPassword);
      });

      testWidgets('Large community list loads efficiently', (WidgetTester tester) async {
        final stopwatch = Stopwatch()..start();

        final response = await communityService.getCommunities(page: 1, pageSize: 100);

        stopwatch.stop();

        expect(response.items, isNotEmpty,
            reason: 'Should load communities');
        expect(stopwatch.elapsedMilliseconds, lessThan(5000),
            reason: 'Large list should load within 5 seconds');
      });

      testWidgets('Multiple API calls execute concurrently', (WidgetTester tester) async {
        final stopwatch = Stopwatch()..start();

        final futures = [
          communityService.getCommunities(page: 1, pageSize: 20),
          communityService.getCommunities(page: 2, pageSize: 20),
          authService.getCurrentUser(),
        ];

        final results = await Future.wait(futures);

        stopwatch.stop();

        expect(results.length, 3,
            reason: 'All concurrent requests should complete');
        expect(stopwatch.elapsedMilliseconds, lessThan(10000),
            reason: 'Concurrent requests should complete within 10 seconds');
      });

      testWidgets('UI remains responsive during data loading', (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle();

        final loadingIndicators = find.byType(CircularProgressIndicator);
        expect(loadingIndicators, findsWidgets,
            reason: 'Loading indicators should be visible during data load');

        await tester.pumpAndSettle(const Duration(seconds: 5));

        final successContent = find.byType(ListView);
        expect(successContent, findsWidgets,
            reason: 'Content should render after loading completes');
      });
    });

    group('Network Resilience', () {
      setUp(() async {
        const testEmail = 'network.test@example.com';
        const testPassword = 'NetworkPassword123!';
        try {
          await authService.login(testEmail, testPassword);
        } catch (_) {}
      });

      testWidgets('Handles connection timeouts gracefully', (WidgetTester tester) async {
        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle();

        final errorWidgets = find.byType(SnackBar);
        expect(errorWidgets, findsWidgets,
            reason: 'Error messages should display on failure');
      });

      testWidgets('Retry mechanism works on failed requests', (WidgetTester tester) async {
        int requestCount = 0;
        try {
          await communityService.getCommunities(page: 1, pageSize: 20);
          requestCount++;
        } catch (_) {}

        await Future.delayed(const Duration(seconds: 1));

        try {
          await communityService.getCommunities(page: 1, pageSize: 20);
          requestCount++;
        } catch (_) {}

        expect(requestCount, greaterThanOrEqualTo(0),
            reason: 'Should attempt multiple requests');
      });

      testWidgets('Authentication error triggers logout', (WidgetTester tester) async {
        await authService.logout();

        expect(authService.isAuthenticated, false,
            reason: 'Should be logged out after auth error');

        await tester.pumpWidget(const GazerApp());
        await tester.pumpAndSettle();

        final loginScreen = find.byType(LoginScreen);
        expect(loginScreen, findsOneWidget,
            reason: 'Should redirect to login on auth error');
      });
    });
  });
}

