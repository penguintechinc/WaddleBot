import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_libs/flutter_libs.dart';

import '../../services/waddlebot_auth_service.dart';

/// Gazer Login Screen using LoginPageBuilder
///
/// Features:
/// - LoginPageBuilder from penguin-libs with Elder theme
/// - Integration with Waddles authentication service
/// - JWT token persistence via flutter_secure_storage
/// - MFA/2FA support enabled
/// - Professional streaming app branding
class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    required this.authService,
  });

  final WaddleBotAuthService authService;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  static const _secureStorage = FlutterSecureStorage();
  static const _keyAccessToken = 'gazer_access_token';
  static const _keyRefreshToken = 'gazer_refresh_token';

  void _handleLoginSuccess(LoginResponse response) async {
    try {
      // Persist tokens securely
      if (response.token != null) {
        await _secureStorage.write(
          key: _keyAccessToken,
          value: response.token!,
        );
      }

      if (response.refreshToken != null) {
        await _secureStorage.write(
          key: _keyRefreshToken,
          value: response.refreshToken!,
        );
      }

      if (mounted) {
        // Navigate to main app
        Navigator.of(context).pushReplacementNamed('/main');
      }
    } catch (e) {
      _showErrorSnackBar('Failed to save authentication tokens: $e');
    }
  }

  void _handleLoginError(String error) {
    _showErrorSnackBar('Login failed: $error');
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red.shade900,
        duration: const Duration(seconds: 4),
      ),
    );
  }

  String _transformErrorMessage(String error) {
    // Transform API error messages to user-friendly text
    switch (error.toLowerCase()) {
      case 'invalid credentials':
        return 'Invalid email or password. Please try again.';
      case 'user not found':
        return 'No account found with this email address.';
      case 'account locked':
        return 'Your account has been locked. Contact support.';
      case 'email not verified':
        return 'Please verify your email address first.';
      case 'mfa required':
        return 'Multi-factor authentication required.';
      default:
        return error;
    }
  }

  void _handleForgotPassword() {
    // Open forgot password flow
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Password reset functionality coming soon'),
        duration: Duration(seconds: 2),
      ),
    );
  }

  void _handleSignUp() {
    // Navigate to sign up screen
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Sign up functionality coming soon'),
        duration: Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: LoginPageBuilder(
        // API Configuration
        apiConfig: const LoginApiConfig(
          loginUrl: 'https://hub-api.waddlebot.io/api/v1/auth/login',
          method: LoginMethod.post,
        ),

        // Branding Configuration
        branding: const BrandingConfig(
          appName: 'Gazer',
          tagline: 'Professional Mobile Streaming Studio',
          logoWidth: 280,
        ),

        // MFA Configuration (enabled)
        mfaConfig: const MFAConfig(
          enabled: true,
          codeLength: 6,
          allowRememberDevice: true,
        ),

        // GDPR/Cookie Consent (optional)
        gdprConfig: const GDPRConfig(
          enabled: false,
          privacyPolicyUrl: 'https://waddlebot.io/privacy',
          cookiePolicyUrl: 'https://waddlebot.io/cookies',
        ),

        // Color Configuration - Elder theme
        colorConfig: LoginColorConfig.elder,

        // Callback handlers
        onLoginSuccess: _handleLoginSuccess,
        onLoginError: _handleLoginError,
        transformErrorMessage: _transformErrorMessage,
        forgotPasswordCallback: _handleForgotPassword,
        signUpCallback: _handleSignUp,

        // UI Configuration
        showRememberMe: true,
      ),
    );
  }
}
