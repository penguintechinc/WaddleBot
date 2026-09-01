import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'dart:developer' as developer;
import 'app.dart';
import 'models/domain_config.dart';
import 'services/settings_service.dart';
import 'services/api_client.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Get package info for version display
  final packageInfo = await PackageInfo.fromPlatform();

  // Log app version to console for debugging
  debugPrint(
      'Flutter Gazer v${packageInfo.version}+${packageInfo.buildNumber}');

  // Initialize domain configuration from persistent storage
  try {
    final settingsService = SettingsService();

    // Load saved API domain from SharedPreferences
    final savedDomain = await settingsService.loadApiDomain();

    // Set the domain in ApiClient singleton
    // This ensures all API requests use the persisted domain across app restarts
    ApiClient.getInstance().setDomain(savedDomain);

    developer.log(
      'Domain initialized: ${savedDomain.displayName} (${savedDomain.host})',
      name: 'main.initializeDomain',
      level: 1000,
    );
  } catch (e, stackTrace) {
    // Fallback to production domain if initialization fails
    developer.log(
      'Error initializing domain configuration, using production domain: $e',
      name: 'main.initializeDomain',
      error: e,
      stackTrace: stackTrace,
      level: 900, // Warning level
    );

    try {
      ApiClient.getInstance().setDomain(WaddleBotDomain.production);
    } catch (fallbackError) {
      developer.log(
        'Critical error: Failed to set fallback production domain: $fallbackError',
        name: 'main.initializeDomain',
        error: fallbackError,
        level: 1200, // Error level
      );
    }
  }

  runApp(const GazerApp());
}
