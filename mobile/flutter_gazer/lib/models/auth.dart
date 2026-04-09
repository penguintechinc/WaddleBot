/// User model representing an authenticated user.
class User {
  final String id;
  final String email;
  final String username;
  final String? avatarUrl;
  final bool isSuperAdmin;
  final List<String> linkedPlatforms;
  final List<String> communities;
  final DateTime createdAt;

  const User({
    required this.id,
    required this.email,
    required this.username,
    this.avatarUrl,
    this.isSuperAdmin = false,
    this.linkedPlatforms = const [],
    this.communities = const [],
    required this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as String? ?? '',
      email: json['email'] as String? ?? '',
      username: json['username'] as String? ?? '',
      avatarUrl: json['avatar_url'] as String?,
      isSuperAdmin: json['is_super_admin'] as bool? ?? false,
      linkedPlatforms: (json['linked_platforms'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      communities: (json['communities'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ??
          DateTime.now(),
    );
  }

  /// Get user role based on permissions
  String get role => isSuperAdmin ? 'admin' : 'user';

  Map<String, dynamic> toJson() => {
        'id': id,
        'email': email,
        'username': username,
        if (avatarUrl != null) 'avatar_url': avatarUrl,
        'is_super_admin': isSuperAdmin,
        'linked_platforms': linkedPlatforms,
        'communities': communities,
        'created_at': createdAt.toIso8601String(),
      };

  User copyWith({
    String? id,
    String? email,
    String? username,
    String? avatarUrl,
    bool? isSuperAdmin,
    List<String>? linkedPlatforms,
    List<String>? communities,
    DateTime? createdAt,
  }) {
    return User(
      id: id ?? this.id,
      email: email ?? this.email,
      username: username ?? this.username,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      isSuperAdmin: isSuperAdmin ?? this.isSuperAdmin,
      linkedPlatforms: linkedPlatforms ?? this.linkedPlatforms,
      communities: communities ?? this.communities,
      createdAt: createdAt ?? this.createdAt,
    );
  }
}

/// JWT token response from authentication endpoint.
class TokenResponse {
  final String token;
  final int expiresIn;
  final String? refreshToken;
  final User user;

  const TokenResponse({
    required this.token,
    required this.expiresIn,
    this.refreshToken,
    required this.user,
  });

  factory TokenResponse.fromJson(Map<String, dynamic> json) {
    return TokenResponse(
      token: json['token'] as String? ?? '',
      expiresIn: json['expires_in'] as int? ?? 3600,
      refreshToken: json['refresh_token'] as String?,
      user: User.fromJson(json['user'] as Map<String, dynamic>? ?? {}),
    );
  }

  Map<String, dynamic> toJson() => {
        'token': token,
        'expires_in': expiresIn,
        if (refreshToken != null) 'refresh_token': refreshToken,
        'user': user.toJson(),
      };

  /// Check if the token has expired.
  bool get isExpired {
    final expirationTime = DateTime.now().add(Duration(seconds: expiresIn));
    return DateTime.now().isAfter(expirationTime);
  }

  /// Get expiration DateTime.
  DateTime get expirationDateTime =>
      DateTime.now().add(Duration(seconds: expiresIn));

  /// Check if token is valid (not expired).
  bool get isValid => !isExpired;

  /// Copy with new values.
  TokenResponse copyWith({
    String? token,
    int? expiresIn,
    String? refreshToken,
    User? user,
  }) {
    return TokenResponse(
      token: token ?? this.token,
      expiresIn: expiresIn ?? this.expiresIn,
      refreshToken: refreshToken ?? this.refreshToken,
      user: user ?? this.user,
    );
  }
}

/// JWT claims decoded from the access token.
class JwtClaims {
  final String sub; // User ID (subject)
  final int iat; // Issued at timestamp
  final int exp; // Expiration timestamp
  final String? licenseKey;
  final String? tier;
  final Map<String, dynamic> _rawClaims;

  const JwtClaims({
    required this.sub,
    required this.iat,
    required this.exp,
    this.licenseKey,
    this.tier,
    Map<String, dynamic>? rawClaims,
  }) : _rawClaims = rawClaims ?? const {};

  factory JwtClaims.fromJson(Map<String, dynamic> json) {
    return JwtClaims(
      sub: json['sub'] as String? ?? '',
      iat: json['iat'] as int? ?? 0,
      exp: json['exp'] as int? ?? 0,
      licenseKey: json['license_key'] as String?,
      tier: json['tier'] as String?,
      rawClaims: json,
    );
  }

  Map<String, dynamic> toJson() => {
        'sub': sub,
        'iat': iat,
        'exp': exp,
        if (licenseKey != null) 'license_key': licenseKey,
        if (tier != null) 'tier': tier,
      };

  /// Check if the token has expired.
  bool get isExpired {
    final expirationTime =
        DateTime.fromMillisecondsSinceEpoch(exp * 1000, isUtc: true);
    return DateTime.now().toUtc().isAfter(expirationTime);
  }

  /// Get expiration DateTime.
  DateTime get expirationDateTime =>
      DateTime.fromMillisecondsSinceEpoch(exp * 1000, isUtc: true);

  /// Get issue DateTime.
  DateTime get issuedDateTime =>
      DateTime.fromMillisecondsSinceEpoch(iat * 1000, isUtc: true);

  /// Check if token is valid (not expired).
  bool get isValid => !isExpired;

  /// Get a custom claim value.
  T? getCustomClaim<T>(String key) {
    final value = _rawClaims[key];
    return value is T ? value : null;
  }

  /// Copy with new values.
  JwtClaims copyWith({
    String? sub,
    int? iat,
    int? exp,
    String? licenseKey,
    String? tier,
  }) {
    return JwtClaims(
      sub: sub ?? this.sub,
      iat: iat ?? this.iat,
      exp: exp ?? this.exp,
      licenseKey: licenseKey ?? this.licenseKey,
      tier: tier ?? this.tier,
      rawClaims: _rawClaims,
    );
  }
}

/// Login credentials for authentication.
class LoginCredentials {
  final String email;
  final String password;

  const LoginCredentials({
    required this.email,
    required this.password,
  });

  factory LoginCredentials.fromJson(Map<String, dynamic> json) {
    return LoginCredentials(
      email: json['email'] as String? ?? '',
      password: json['password'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        'email': email,
        'password': password,
      };

  /// Check if credentials are valid (both fields non-empty).
  bool get isValid => email.isNotEmpty && password.isNotEmpty;

  /// Copy with new values.
  LoginCredentials copyWith({
    String? email,
    String? password,
  }) {
    return LoginCredentials(
      email: email ?? this.email,
      password: password ?? this.password,
    );
  }
}

/// Sealed class representing the authentication state.
sealed class AuthState {
  const AuthState();
}

/// Initial unauthenticated state.
final class Unauthenticated extends AuthState {
  const Unauthenticated();

  @override
  String toString() => 'AuthState.unauthenticated()';
}

/// Authentication in progress state.
final class Authenticating extends AuthState {
  const Authenticating();

  @override
  String toString() => 'AuthState.authenticating()';
}

/// Successfully authenticated state with user data.
final class Authenticated extends AuthState {
  final User user;
  final TokenResponse tokenResponse;

  const Authenticated({
    required this.user,
    required this.tokenResponse,
  });

  @override
  String toString() => 'AuthState.authenticated(user: ${user.username})';
}

/// Authentication error state.
final class AuthError extends AuthState {
  final String message;
  final String? code;
  final dynamic originalError;

  const AuthError({
    required this.message,
    this.code,
    this.originalError,
  });

  @override
  String toString() =>
      'AuthState.error(message: $message${code != null ? ', code: $code' : ''})';
}
