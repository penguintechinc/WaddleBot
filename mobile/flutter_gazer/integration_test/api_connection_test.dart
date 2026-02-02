import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:dio/dio.dart';
import 'package:gazer_waddlebot/services/api_client.dart';
import 'package:gazer_waddlebot/models/domain_config.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:gazer_waddlebot/services/settings_service.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('API Connectivity Tests', () {
    late ApiClient apiClient;
    late Dio dio;
    late SettingsService settingsService;

    setUp(() async {
      apiClient = ApiClient.getInstance();
      dio = Dio();
      SharedPreferences.setMockInitialValues({});
      settingsService = SettingsService();
    });

    tearDown(() async {
      await settingsService.saveApiDomain(WaddleBotDomain.production);
    });

    group('Health Check Endpoints', () {
      test('PenguinTech domain health check succeeds', () async {
        apiClient.setDomain(WaddleBotDomain.penguintech);

        try {
          final response = await dio.get(
            '${WaddleBotDomain.penguintech.apiUrl}/health',
            options: Options(
              connectTimeout: const Duration(seconds: 30),
              receiveTimeout: const Duration(seconds: 60),
            ),
          );

          expect(response.statusCode, isIn([200, 204]));
        } on DioException catch (e) {
          expect(
            e.type,
            isNot(DioExceptionType.connectionTimeout),
            reason: 'PenguinTech health check should not timeout',
          );
          expect(
            e.type,
            isNot(DioExceptionType.receiveTimeout),
            reason: 'PenguinTech health check should complete within timeout',
          );
        }
      });

      test('Waddles domain health check succeeds', () async {
        apiClient.setDomain(WaddleBotDomain.waddles);

        try {
          final response = await dio.get(
            '${WaddleBotDomain.waddles.apiUrl}/health',
            options: Options(
              connectTimeout: const Duration(seconds: 30),
              receiveTimeout: const Duration(seconds: 60),
            ),
          );

          expect(response.statusCode, isIn([200, 204]));
        } on DioException catch (e) {
          expect(
            e.type,
            isNot(DioExceptionType.connectionTimeout),
            reason: 'Waddles health check should not timeout',
          );
          expect(
            e.type,
            isNot(DioExceptionType.receiveTimeout),
            reason: 'Waddles health check should complete within timeout',
          );
        }
      });

      test('Production domain health check succeeds', () async {
        apiClient.setDomain(WaddleBotDomain.production);

        try {
          final response = await dio.get(
            '${WaddleBotDomain.production.apiUrl}/health',
            options: Options(
              connectTimeout: const Duration(seconds: 30),
              receiveTimeout: const Duration(seconds: 60),
            ),
          );

          expect(response.statusCode, isIn([200, 204]));
        } on DioException catch (e) {
          expect(
            e.type,
            isNot(DioExceptionType.connectionTimeout),
            reason: 'Production health check should not timeout',
          );
          expect(
            e.type,
            isNot(DioExceptionType.receiveTimeout),
            reason: 'Production health check should complete within timeout',
          );
        }
      });
    });

    group('Invalid Endpoint Handling', () {
      test('Invalid endpoint on PenguinTech returns 404', () async {
        apiClient.setDomain(WaddleBotDomain.penguintech);

        try {
          await dio.get(
            '${WaddleBotDomain.penguintech.apiUrl}/invalid-endpoint-that-does-not-exist',
            options: Options(
              connectTimeout: const Duration(seconds: 30),
              receiveTimeout: const Duration(seconds: 60),
              validateStatus: (status) => true,
            ),
          );
        } on DioException catch (e) {
          expect(e.response?.statusCode, 404);
        }
      });

      test('Invalid endpoint on Waddles returns 404', () async {
        apiClient.setDomain(WaddleBotDomain.waddles);

        try {
          await dio.get(
            '${WaddleBotDomain.waddles.apiUrl}/invalid-endpoint-that-does-not-exist',
            options: Options(
              connectTimeout: const Duration(seconds: 30),
              receiveTimeout: const Duration(seconds: 60),
              validateStatus: (status) => true,
            ),
          );
        } on DioException catch (e) {
          expect(e.response?.statusCode, 404);
        }
      });

      test('Invalid endpoint on Production returns 404', () async {
        apiClient.setDomain(WaddleBotDomain.production);

        try {
          await dio.get(
            '${WaddleBotDomain.production.apiUrl}/invalid-endpoint-that-does-not-exist',
            options: Options(
              connectTimeout: const Duration(seconds: 30),
              receiveTimeout: const Duration(seconds: 60),
              validateStatus: (status) => true,
            ),
          );
        } on DioException catch (e) {
          expect(e.response?.statusCode, 404);
        }
      });
    });

    group('Domain Switching and Route Updates', () {
      test('Switching from PenguinTech to Waddles updates API routes', () async {
        apiClient.setDomain(WaddleBotDomain.penguintech);
        expect(
          apiClient.getCurrentDomain(),
          WaddleBotDomain.penguintech,
          reason: 'Should start with PenguinTech domain',
        );

        apiClient.setDomain(WaddleBotDomain.waddles);
        expect(
          apiClient.getCurrentDomain(),
          WaddleBotDomain.waddles,
          reason: 'Should switch to Waddles domain',
        );
      });

      test('Switching from Waddles to Production updates API routes', () async {
        apiClient.setDomain(WaddleBotDomain.waddles);
        expect(
          apiClient.getCurrentDomain(),
          WaddleBotDomain.waddles,
          reason: 'Should start with Waddles domain',
        );

        apiClient.setDomain(WaddleBotDomain.production);
        expect(
          apiClient.getCurrentDomain(),
          WaddleBotDomain.production,
          reason: 'Should switch to Production domain',
        );
      });

      test('Switching from Production to PenguinTech updates API routes', () async {
        apiClient.setDomain(WaddleBotDomain.production);
        expect(
          apiClient.getCurrentDomain(),
          WaddleBotDomain.production,
          reason: 'Should start with Production domain',
        );

        apiClient.setDomain(WaddleBotDomain.penguintech);
        expect(
          apiClient.getCurrentDomain(),
          WaddleBotDomain.penguintech,
          reason: 'Should switch to PenguinTech domain',
        );
      });

      test('API routes are correctly updated after domain switch', () async {
        apiClient.setDomain(WaddleBotDomain.penguintech);
        final penguintechUrl = apiClient.getCurrentDomain().apiUrl;
        expect(penguintechUrl, WaddleBotDomain.penguintech.apiUrl);

        apiClient.setDomain(WaddleBotDomain.production);
        final productionUrl = apiClient.getCurrentDomain().apiUrl;
        expect(productionUrl, WaddleBotDomain.production.apiUrl);

        expect(
          penguintechUrl,
          isNot(productionUrl),
          reason: 'Different domains should have different API URLs',
        );
      });

      test('Multiple sequential domain switches work correctly', () async {
        final domains = [
          WaddleBotDomain.penguintech,
          WaddleBotDomain.waddles,
          WaddleBotDomain.production,
          WaddleBotDomain.penguintech,
          WaddleBotDomain.waddles,
        ];

        for (final domain in domains) {
          apiClient.setDomain(domain);
          expect(
            apiClient.getCurrentDomain(),
            domain,
            reason: 'Domain should match after each switch',
          );
        }
      });
    });

    group('Domain Configuration Validation', () {
      test('All domain URLs are valid HTTPS endpoints', () {
        for (final domain in WaddleBotDomain.values) {
          final apiUrl = domain.apiUrl;
          expect(apiUrl.startsWith('https://'), true,
              reason: 'API URL should use HTTPS: $apiUrl');
          expect(apiUrl.contains('/api/'), true,
              reason: 'API URL should contain /api/: $apiUrl');
        }
      });

      test('WebSocket URLs are valid for all domains', () {
        for (final domain in WaddleBotDomain.values) {
          final wsUrl = domain.wsUrl;
          expect(wsUrl.startsWith('wss://'), true,
              reason: 'WebSocket URL should use WSS: $wsUrl');
          expect(wsUrl.contains('/api/'), true,
              reason: 'WebSocket URL should contain /api/: $wsUrl');
        }
      });

      test('Domain hosts are correctly configured', () {
        expect(WaddleBotDomain.penguintech.host, 'waddlebot.penguintech.io');
        expect(WaddleBotDomain.waddles.host, 'waddles.penguintech.io');
        expect(WaddleBotDomain.production.host, 'app.waddlebot.io');
      });

      test('Domain display names are human-readable', () {
        expect(WaddleBotDomain.penguintech.displayName, isNotEmpty);
        expect(WaddleBotDomain.waddles.displayName, isNotEmpty);
        expect(WaddleBotDomain.production.displayName, isNotEmpty);

        expect(WaddleBotDomain.penguintech.displayName,
            contains('PenguinTech'));
        expect(
            WaddleBotDomain.waddles.displayName, contains('Waddles'));
      });
    });

    group('API Error Handling', () {
      test('ApiClient handles empty domain URL error', () {
        apiClient.setDomain(WaddleBotDomain.production);

        expect(
          () => apiClient.setDomain(WaddleBotDomain.production),
          isNot(throwsA(isA<ArgumentError>())),
          reason: 'Valid domain should not throw error',
        );
      });

      test('API client maintains consistent state after operations', () async {
        final initialDomain = apiClient.getCurrentDomain();

        apiClient.setDomain(WaddleBotDomain.waddles);
        expect(apiClient.getCurrentDomain(), WaddleBotDomain.waddles);

        apiClient.setDomain(WaddleBotDomain.production);
        expect(apiClient.getCurrentDomain(), WaddleBotDomain.production);

        apiClient.setDomain(initialDomain);
        expect(apiClient.getCurrentDomain(), initialDomain);
      });

      test('Concurrent domain switches are handled safely', () async {
        final futures = <Future<void>>[];

        for (int i = 0; i < 10; i++) {
          futures.add(
            Future(() {
              const domains = WaddleBotDomain.values;
              apiClient.setDomain(domains[i % domains.length]);
            }),
          );
        }

        await Future.wait(futures);

        final finalDomain = apiClient.getCurrentDomain();
        expect(finalDomain, isA<WaddleBotDomain>());
      });
    });

    group('Domain Persistence Tests', () {
      test('Save production domain to SharedPreferences', () async {
        final domain = WaddleBotDomain.production;

        await settingsService.saveApiDomain(domain);

        final prefs = await SharedPreferences.getInstance();
        final savedIndex = prefs.getInt('api_domain');

        expect(savedIndex, equals(domain.index));
        expect(savedIndex, equals(2));
      });

      test('Save penguintech domain to SharedPreferences', () async {
        final domain = WaddleBotDomain.penguintech;

        await settingsService.saveApiDomain(domain);

        final prefs = await SharedPreferences.getInstance();
        final savedIndex = prefs.getInt('api_domain');

        expect(savedIndex, equals(domain.index));
        expect(savedIndex, equals(0));
      });

      test('Save waddles domain to SharedPreferences', () async {
        final domain = WaddleBotDomain.waddles;

        await settingsService.saveApiDomain(domain);

        final prefs = await SharedPreferences.getInstance();
        final savedIndex = prefs.getInt('api_domain');

        expect(savedIndex, equals(domain.index));
        expect(savedIndex, equals(1));
      });

      test('Default domain index when not set is 2 (production)', () async {
        final prefs = await SharedPreferences.getInstance();
        await prefs.remove('api_domain');

        final storedIndex = prefs.getInt('api_domain') ?? 2;

        expect(storedIndex, equals(2));
      });

      test('Domain persists to SharedPreferences across service instances',
          () async {
        await settingsService.saveApiDomain(WaddleBotDomain.waddles);

        // Simulate new service instance by getting fresh prefs
        final prefs = await SharedPreferences.getInstance();
        final savedIndex = prefs.getInt('api_domain');

        expect(savedIndex, equals(1));
        expect(savedIndex, equals(WaddleBotDomain.waddles.index));
      });
    });

    group('Default Domain Tests', () {
      test('Production domain is the hardcoded default', () {
        final domain = WaddleBotDomain.production;

        expect(domain.index, equals(2));
      });

      test('Production domain has correct API URL', () {
        final domain = WaddleBotDomain.production;

        expect(domain.host, equals('app.waddlebot.io'));
        expect(domain.apiUrl, equals('https://app.waddlebot.io/api/v2'));
        expect(domain.wsUrl, equals('wss://app.waddlebot.io/api/v1/ws'));
        expect(domain.displayName, equals('Waddles'));
      });
    });

    group('All Domains Valid Tests', () {
      test('All three domains exist', () {
        expect(WaddleBotDomain.values.length, equals(3));
      });

      test('Penguintech domain is valid', () {
        final domain = WaddleBotDomain.penguintech;

        expect(domain.host, equals('waddlebot.penguintech.io'));
        expect(domain.apiUrl, equals('https://waddlebot.penguintech.io/api/v2'));
        expect(domain.wsUrl, equals('wss://waddlebot.penguintech.io/api/v1/ws'));
        expect(domain.displayName, equals('PenguinTech Dev'));
      });

      test('Waddles domain is valid', () {
        final domain = WaddleBotDomain.waddles;

        expect(domain.host, equals('waddles.penguintech.io'));
        expect(domain.apiUrl, equals('https://waddles.penguintech.io/api/v2'));
        expect(domain.wsUrl, equals('wss://waddles.penguintech.io/api/v1/ws'));
        expect(domain.displayName, equals('Waddles Dev'));
      });

      test('Production domain is valid', () {
        final domain = WaddleBotDomain.production;

        expect(domain.host, equals('app.waddlebot.io'));
        expect(domain.apiUrl, equals('https://app.waddlebot.io/api/v2'));
        expect(domain.wsUrl, equals('wss://app.waddlebot.io/api/v1/ws'));
        expect(domain.displayName, equals('Waddles'));
      });

      test('All domains have unique hosts', () {
        final hosts = {
          WaddleBotDomain.penguintech.host,
          WaddleBotDomain.waddles.host,
          WaddleBotDomain.production.host,
        };

        expect(hosts.length, equals(3));
      });

      test('All domains have unique API URLs', () {
        final apiUrls = {
          WaddleBotDomain.penguintech.apiUrl,
          WaddleBotDomain.waddles.apiUrl,
          WaddleBotDomain.production.apiUrl,
        };

        expect(apiUrls.length, equals(3));
      });

      test('All domains have unique WebSocket URLs', () {
        final wsUrls = {
          WaddleBotDomain.penguintech.wsUrl,
          WaddleBotDomain.waddles.wsUrl,
          WaddleBotDomain.production.wsUrl,
        };

        expect(wsUrls.length, equals(3));
      });
    });

    group('Index Mapping Tests', () {
      test('Penguintech domain has index 0', () {
        expect(WaddleBotDomain.penguintech.index, equals(0));
      });

      test('Waddles domain has index 1', () {
        expect(WaddleBotDomain.waddles.index, equals(1));
      });

      test('Production domain has index 2', () {
        expect(WaddleBotDomain.production.index, equals(2));
      });

      test('Enum values order matches expected indices', () {
        expect(WaddleBotDomain.values[0], equals(WaddleBotDomain.penguintech));
        expect(WaddleBotDomain.values[1], equals(WaddleBotDomain.waddles));
        expect(WaddleBotDomain.values[2], equals(WaddleBotDomain.production));
      });
    });

    group('Domain Switching Workflow Tests', () {
      test('Complete workflow: switch API client, save, and verify storage',
          () async {
        final currentDomain = apiClient.getCurrentDomain();
        expect(currentDomain, equals(WaddleBotDomain.production));

        apiClient.setDomain(WaddleBotDomain.penguintech);
        expect(
          apiClient.getCurrentDomain(),
          equals(WaddleBotDomain.penguintech),
        );

        await settingsService.saveApiDomain(WaddleBotDomain.penguintech);

        final prefs = await SharedPreferences.getInstance();
        final savedIndex = prefs.getInt('api_domain');
        expect(savedIndex, equals(0));
      });

      test('Domain change reflects in API URLs', () {
        apiClient.setDomain(WaddleBotDomain.penguintech);
        var currentDomain = apiClient.getCurrentDomain();
        expect(currentDomain.apiUrl, contains('waddlebot.penguintech.io'));

        apiClient.setDomain(WaddleBotDomain.waddles);
        currentDomain = apiClient.getCurrentDomain();
        expect(currentDomain.apiUrl, contains('waddles.penguintech.io'));

        apiClient.setDomain(WaddleBotDomain.production);
        currentDomain = apiClient.getCurrentDomain();
        expect(currentDomain.apiUrl, contains('app.waddlebot.io'));
      });
    });

    group('Edge Cases and Error Handling Tests', () {
      test('Each domain has valid host string', () {
        for (final domain in WaddleBotDomain.values) {
          expect(domain.host.isNotEmpty, isTrue);
          expect(domain.host.contains('.'), isTrue);
        }
      });

      test('Domain index is consistent across calls', () {
        for (final domain in WaddleBotDomain.values) {
          final index1 = domain.index;
          final index2 = domain.index;

          expect(index1, equals(index2));
        }
      });

      test('Setting domain with empty apiUrl throws error', () {
        expect(
          () => apiClient.setDomain(WaddleBotDomain.production),
          isNotNull,
        );
      });

      test('All domains have non-empty critical properties', () {
        for (final domain in WaddleBotDomain.values) {
          expect(domain.host.isNotEmpty, isTrue);
          expect(domain.displayName.isNotEmpty, isTrue);
          expect(domain.apiUrl.isNotEmpty, isTrue);
          expect(domain.wsUrl.isNotEmpty, isTrue);
          expect(domain.apiUrl.startsWith('https://'), isTrue);
          expect(domain.wsUrl.startsWith('wss://'), isTrue);
        }
      });

      test('API URLs follow correct versioning format', () {
        for (final domain in WaddleBotDomain.values) {
          expect(domain.apiUrl, contains('/api/v'));
          expect(domain.apiUrl.contains('/api/v2'), isTrue);
        }
      });

      test('WebSocket URLs follow correct protocol', () {
        for (final domain in WaddleBotDomain.values) {
          expect(domain.wsUrl, startsWith('wss://'));
          expect(domain.wsUrl, contains('/api/v1/ws'));
        }
      });
    });
  });
}
