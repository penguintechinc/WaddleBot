import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:convert';
import '../models/auth.dart';
import 'api_client.dart';
import 'license_service.dart';

/// Waddles authentication service with JWT refresh, secure storage, and license integration.
///
/// Manages:
/// - User login/logout with TokenResponse containing User data
/// - JWT token refresh with automatic retry on 401
/// - Secure token persistence using flutter_secure_storage
/// - License validation after successful authentication
/// - Authentication state management using AuthState sealed classes
class WaddleBotAuthService {
  static const _keyAccessToken = 'wb_access_token';
  static const _keyRefreshToken = 'wb_refresh_token';
  static const _keyCurrentUser = 'wb_current_user';

  late final ApiClient _apiClient;
  late final FlutterSecureStorage _secureStorage;
  final LicenseService? _licenseService;

  String? _accessToken;
  String? _refreshToken;
  User? _currentUser;
  TokenResponse? _tokenResponse;

  WaddleBotAuthService({
    ApiClient? apiClient,
    FlutterSecureStorage? secureStorage,
    LicenseService? licenseService,
  })  : _apiClient = apiClient ?? ApiClient.getInstance(),
        _secureStorage = secureStorage ?? const FlutterSecureStorage(),
        _licenseService = licenseService {
    // Register this auth service with the API client for token refresh capability
    _apiClient.setAuthService(this);
  }

  /// Current access token
  String? get accessToken => _accessToken;

  /// Current authenticated user
  User? get currentUser => _currentUser;

  /// Current token response (includes expiration info)
  TokenResponse? get tokenResponse => _tokenResponse;

  /// Check if user is authenticated (has valid access token)
  bool get isAuthenticated => _accessToken != null && _accessToken!.isNotEmpty;

  /// Get authentication state
  AuthState get authState {
    if (_currentUser == null) {
      return const Unauthenticated();
    }
    if (_tokenResponse != null) {
      return Authenticated(
        user: _currentUser!,
        tokenResponse: _tokenResponse!,
      );
    }
    return const Unauthenticated();
  }

  /// Load persisted tokens from secure storage on app startup.
  ///
  /// Returns whether tokens were successfully loaded and are still valid.
  Future<bool> loadStoredTokens() async {
    try {
      _accessToken = await _secureStorage.read(key: _keyAccessToken);
      _refreshToken = await _secureStorage.read(key: _keyRefreshToken);
      final userJson = await _secureStorage.read(key: _keyCurrentUser);

      if (userJson != null && _accessToken != null) {
        _currentUser =
            User.fromJson(jsonDecode(userJson) as Map<String, dynamic>);
        await _apiClient.setAuthToken(_accessToken!);
        return true;
      }
    } catch (e) {
      // Error loading stored tokens
    }
    return false;
  }

  /// Login with email and password.
  ///
  /// Returns [TokenResponse] on success containing:
  /// - JWT access token
  /// - Refresh token
  /// - Expiration time
  /// - Authenticated user data
  ///
  /// Throws [ApiError] on authentication failure.
  /// Integrates with LicenseService to validate user license after login.
  Future<TokenResponse> login(String email, String password) async {
    try {
      final response = await _apiClient.post<TokenResponse>(
        '/auth/login',
        data: {
          'email': email,
          'password': password,
        },
        fromJson: (json) =>
            TokenResponse.fromJson(json as Map<String, dynamic>),
      );

      _tokenResponse = response;
      _accessToken = response.token;
      _refreshToken = response.refreshToken;
      _currentUser = response.user;

      // Persist tokens securely
      await _secureStorage.write(key: _keyAccessToken, value: _accessToken!);
      if (_refreshToken != null) {
        await _secureStorage.write(
          key: _keyRefreshToken,
          value: _refreshToken!,
        );
      }
      await _secureStorage.write(
        key: _keyCurrentUser,
        value: jsonEncode(_currentUser!.toJson()),
      );

      // Update API client with new token
      await _apiClient.setAuthToken(_accessToken!);

      // Validate license after successful login (if available)
      if (_licenseService != null && _currentUser != null) {
        try {
          // Extract license key from JWT claims or user data
          // This allows license validation tied to the authenticated user
          unawaited(_licenseService.initialize());
        } catch (e) {
          // Continue despite license check failure — feature gating handles this
        }
      }

      return response;
    } catch (e) {
      rethrow;
    }
  }

  /// Refresh the access token using refresh token.
  ///
  /// Automatically called when 401 Unauthorized is received.
  /// Returns updated [TokenResponse] on success.
  /// Throws [ApiError] if refresh fails (user must log in again).
  Future<TokenResponse> refreshToken() async {
    if (_refreshToken == null || _refreshToken!.isEmpty) {
      throw ApiError(
        message: 'No refresh token available',
        statusCode: 401,
        errorCode: 'NO_REFRESH_TOKEN',
      );
    }

    try {
      // Make POST request to /api/v2/auth/refresh with refresh token
      final response = await _apiClient.post<TokenResponse>(
        '/api/v2/auth/refresh',
        data: {
          'refresh_token': _refreshToken,
        },
        fromJson: (json) =>
            TokenResponse.fromJson(json as Map<String, dynamic>),
      );

      _tokenResponse = response;
      _accessToken = response.token;
      _refreshToken = response.refreshToken ?? _refreshToken;
      _currentUser = response.user;

      // Persist updated tokens to secure storage
      await _secureStorage.write(key: _keyAccessToken, value: _accessToken!);
      if (_refreshToken != null) {
        await _secureStorage.write(
          key: _keyRefreshToken,
          value: _refreshToken!,
        );
      }
      await _secureStorage.write(
        key: _keyCurrentUser,
        value: jsonEncode(_currentUser!.toJson()),
      );

      // Update API client with new token
      await _apiClient.setAuthToken(_accessToken!);

      return response;
    } on ApiError catch (e) {
      // If refresh returns 401, refresh token is expired - clear auth state
      if (e.statusCode == 401) {
        await logout();
      }
      rethrow;
    } catch (e) {
      // For any other error, also clear auth state
      await logout();

      // Convert to ApiError if not already
      if (e is! ApiError) {
        throw ApiError(
          message: 'Token refresh failed: ${e.toString()}',
          statusCode: 401,
          errorCode: 'REFRESH_FAILED',
          originalError: e,
        );
      }
      rethrow;
    }
  }

  /// Get current authenticated user with fresh data from server.
  ///
  /// Returns [User] with latest profile information.
  /// Throws [ApiError] if request fails.
  Future<User> getCurrentUser() async {
    try {
      final user = await _apiClient.get<User>(
        '/auth/me',
        fromJson: (json) => User.fromJson(json as Map<String, dynamic>),
      );
      _currentUser = user;
      // Update cached user data
      await _secureStorage.write(
        key: _keyCurrentUser,
        value: jsonEncode(user.toJson()),
      );
      return user;
    } catch (e) {
      rethrow;
    }
  }

  /// Logout — clears tokens and license data.
  ///
  /// Removes all authentication state from:
  /// - Memory
  /// - Secure storage
  /// - API client
  /// - License service (if available)
  Future<void> logout() async {
    try {
      // Clear memory state
      _accessToken = null;
      _refreshToken = null;
      _currentUser = null;
      _tokenResponse = null;

      // Clear secure storage
      await _secureStorage.delete(key: _keyAccessToken);
      await _secureStorage.delete(key: _keyRefreshToken);
      await _secureStorage.delete(key: _keyCurrentUser);

      // Clear API client token
      await _apiClient.clearAuthToken();

      // Clear license data
      if (_licenseService != null) {
        await _licenseService.clearLicense();
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Check if access token is expired.
  ///
  /// Returns true if token has expired or will expire in next 60 seconds.
  bool isTokenExpired({int bufferSeconds = 60}) {
    if (_tokenResponse == null) return true;
    final expirationTime = _tokenResponse!.expirationDateTime;
    return DateTime.now()
        .add(Duration(seconds: bufferSeconds))
        .isAfter(expirationTime);
  }

  /// Auto-refresh token if expired, then retry failed request.
  ///
  /// Used by interceptors to transparently handle token expiration.
  /// Returns true if refresh successful, false otherwise.
  Future<bool> autoRefreshIfNeeded() async {
    if (isTokenExpired()) {
      try {
        await refreshToken();
        return true;
      } catch (e) {
        // Token refresh failed
        return false;
      }
    }
    return true;
  }
}

// ignore: avoid_returning_null_for_future
void unawaited(Future<void> future) {
  future.catchError((_) {});
}
