import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import '../config/constants.dart';
import '../models/license_info.dart';

/// Manages license validation against PenguinTech license server.
class LicenseService {
  static const _keyLicenseKey = 'license_key';
  static const _keyLastValidation = 'last_validation';
  static const _keyLicenseData = 'license_data';
  static const _keyDeviceId = 'device_id';

  final Dio _dio;
  LicenseInfo? _currentLicense;

  LicenseService({Dio? dio}) : _dio = dio ?? Dio();

  LicenseInfo? get currentLicense => _currentLicense;
  bool get isValid => _currentLicense?.isValid == true && !(_currentLicense?.isExpired ?? true);

  bool isFeatureAvailable(String feature) {
    return _currentLicense?.hasFeature(feature) ?? false;
  }

  int get maxStreams => _currentLicense?.maxStreams ?? 1;

  /// Check tier-based feature entitlement (validates against server).
  Future<bool> checkFeatureEntitlement(String feature) async {
    if (_currentLicense == null) return false;

    try {
      final deviceId = await _getOrCreateDeviceId();
      final response = await _dio.post(
        AppConstants.licenseServerFeaturesUrl,
        data: {
          'license_key': _currentLicense!.licenseKey,
          'device_id': deviceId,
          'feature': feature,
          'product': AppConstants.productName,
          'version': AppConstants.appVersion,
          'platform': 'flutter',
        },
        options: Options(
          headers: {
            'Content-Type': 'application/json',
            'User-Agent': 'Gazer-Mobile/${AppConstants.appVersion}',
          },
          sendTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 15),
        ),
      );

      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        return data['entitlements']?['available'] == true;
      }
    } catch (_) {
      // Fallback to cached feature check on error
      return _currentLicense?.hasFeature(feature) ?? false;
    }
    return false;
  }

  /// Send usage metrics and keepalive to license server.
  Future<bool> sendKeepAlive({
    int? streamsActive,
    int? cpuUsagePercent,
    int? memoryUsageMb,
  }) async {
    if (_currentLicense == null) return false;

    try {
      final deviceId = await _getOrCreateDeviceId();
      final response = await _dio.post(
        AppConstants.licenseServerKeepaliveUrl,
        data: {
          'license_key': _currentLicense!.licenseKey,
          'device_id': deviceId,
          'product': AppConstants.productName,
          'version': AppConstants.appVersion,
          'platform': 'flutter',
          'timestamp': DateTime.now().millisecondsSinceEpoch,
          if (streamsActive != null) 'streams_active': streamsActive,
          if (cpuUsagePercent != null) 'cpu_usage_percent': cpuUsagePercent,
          if (memoryUsageMb != null) 'memory_usage_mb': memoryUsageMb,
        },
        options: Options(
          headers: {
            'Content-Type': 'application/json',
            'User-Agent': 'Gazer-Mobile/${AppConstants.appVersion}',
          },
          sendTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 15),
        ),
      );

      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// Initialize license — validates stored key or grants Play Store license.
  Future<bool> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    final storedKey = prefs.getString(_keyLicenseKey);
    final lastValidation = prefs.getInt(_keyLastValidation) ?? 0;
    final now = DateTime.now().millisecondsSinceEpoch;

    if (storedKey == null || storedKey.isEmpty) {
      // Play Store purchase — grant full access
      _currentLicense = const LicenseInfo(
        licenseKey: 'PLAYSTORE_LICENSE',
        isValid: true,
        expirationDate: 9999999999999,
        features: {
          AppConstants.featureUsbCapture,
          AppConstants.featureCameraOverlay,
          AppConstants.featureHdStreaming,
          AppConstants.featureAdvancedSettings,
        },
        maxStreams: 1,
        licenseName: 'Play Store License',
      );
      await _saveLicenseData(prefs);
      return true;
    }

    if (now - lastValidation > AppConstants.licenseValidationIntervalMs) {
      return validateLicense(storedKey);
    }

    final cached = prefs.getString(_keyLicenseData);
    if (cached != null) {
      _currentLicense = _parseCachedData(cached);
      if (_currentLicense?.isValid ?? false) {
        // Check offline grace period
        if (_isWithinOfflineGracePeriod(lastValidation, now)) {
          return true;
        }
      }
      return _currentLicense?.isValid ?? false;
    }
    return false;
  }

  /// Validate license key with remote server.
  Future<bool> validateLicense(String licenseKey) async {
    try {
      final deviceId = await _getOrCreateDeviceId();
      final response = await _dio.post(
        AppConstants.licenseServerUrl,
        data: {
          'license_key': licenseKey,
          'device_id': deviceId,
          'product': AppConstants.productName,
          'version': AppConstants.appVersion,
          'platform': 'flutter',
        },
        options: Options(
          headers: {
            'Content-Type': 'application/json',
            'User-Agent': 'Gazer-Mobile/${AppConstants.appVersion}',
          },
          sendTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 15),
        ),
      );

      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        if (data['valid'] == true) {
          final license = data['license'] as Map<String, dynamic>;
          final features = (license['features'] as List<dynamic>?)
                  ?.map((e) => e.toString())
                  .toSet() ??
              {};

          final tierStr = license['tier'] as String? ?? 'free';
          _currentLicense = LicenseInfo(
            licenseKey: licenseKey,
            isValid: true,
            expirationDate: license['expiration'] as int? ?? 9999999999999,
            features: features,
            maxStreams: license['max_streams'] as int? ?? 1,
            licenseName: license['name'] as String? ?? 'Professional License',
            tier: _parseLicenseTierFromString(tierStr),
          );

          final prefs = await SharedPreferences.getInstance();
          await prefs.setString(_keyLicenseKey, licenseKey);
          await prefs.setInt(
              _keyLastValidation, DateTime.now().millisecondsSinceEpoch);
          await _saveLicenseData(prefs);
          return true;
        } else {
          _currentLicense = LicenseInfo(
            licenseKey: licenseKey,
            isValid: false,
            expirationDate: 0,
            features: const {},
            licenseName: 'Invalid License',
            error: data['error'] as String? ?? 'Invalid license',
          );
        }
      } else {
        _currentLicense = LicenseInfo(
          licenseKey: licenseKey,
          isValid: false,
          expirationDate: 0,
          features: const {},
          licenseName: 'Server Error',
          error: 'Server error: ${response.statusCode}',
        );
      }
    } catch (e) {
      _currentLicense = LicenseInfo(
        licenseKey: licenseKey,
        isValid: false,
        expirationDate: 0,
        features: const {},
        licenseName: 'Validation Error',
        error: e.toString(),
      );
    }
    return false;
  }

  /// Clear stored license data.
  Future<void> clearLicense() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keyLicenseKey);
    await prefs.remove(_keyLastValidation);
    await prefs.remove(_keyLicenseData);
    _currentLicense = null;
  }

  Future<String> _getOrCreateDeviceId() async {
    final prefs = await SharedPreferences.getInstance();
    var deviceId = prefs.getString(_keyDeviceId);
    if (deviceId == null) {
      final raw = '${const Uuid().v4()}-gazer-mobile';
      deviceId = sha256.convert(utf8.encode(raw)).toString().substring(0, 16);
      await prefs.setString(_keyDeviceId, deviceId);
    }
    return deviceId;
  }

  Future<void> _saveLicenseData(SharedPreferences prefs) async {
    if (_currentLicense == null) return;
    final l = _currentLicense!;
    final json = jsonEncode({
      'license_key': l.licenseKey,
      'is_valid': l.isValid,
      'expiration': l.expirationDate,
      'features': l.features.toList(),
      'max_streams': l.maxStreams,
      'license_name': l.licenseName,
      'tier': l.tier.name,
      if (l.error != null) 'error': l.error,
    });
    await prefs.setString(_keyLicenseData, json);
  }

  LicenseInfo? _parseCachedData(String cached) {
    try {
      final json = jsonDecode(cached) as Map<String, dynamic>;
      final tierStr = json['tier'] as String? ?? 'free';
      return LicenseInfo(
        licenseKey: json['license_key'] as String,
        isValid: json['is_valid'] as bool,
        expirationDate: json['expiration'] as int,
        features:
            (json['features'] as List<dynamic>).map((e) => e.toString()).toSet(),
        maxStreams: json['max_streams'] as int? ?? 1,
        licenseName: json['license_name'] as String? ?? '',
        error: json['error'] as String?,
        tier: _parseLicenseTierFromString(tierStr),
      );
    } catch (_) {
      return null;
    }
  }

  /// Check if license is within offline grace period.
  bool _isWithinOfflineGracePeriod(int lastValidation, int now) {
    return (now - lastValidation) <= AppConstants.licenseOfflineGracePeriodMs;
  }

  /// Parse LicenseTier from string.
  LicenseTier _parseLicenseTierFromString(String tierStr) {
    try {
      return LicenseTier.values.firstWhere(
        (e) => e.name == tierStr.toLowerCase(),
        orElse: () => LicenseTier.free,
      );
    } catch (_) {
      return LicenseTier.free;
    }
  }
}
