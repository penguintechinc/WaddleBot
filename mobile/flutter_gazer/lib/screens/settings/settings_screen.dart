import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'dart:developer' as developer;
import 'package:flutter_libs/flutter_libs.dart';
import '../../config/constants.dart';
import '../../config/form_configs.dart';
import '../../models/auth.dart';
import '../../models/license_info.dart';
import '../../models/domain_config.dart';
import '../../services/license_service.dart';
import '../../services/settings_service.dart';
import '../../services/waddlebot_auth_service.dart';
import '../../services/api_client.dart';

/// Main settings screen for Flutter Gazer.
/// Displays comprehensive settings organized in categories with Elder theme styling.
///
/// Settings Categories:
/// 1. Account Settings - Edit user profile
/// 2. License Management - View tier, features, expiration, upgrade
/// 3. Stream Quality - Quality presets
/// 4. Audio Settings - Microphone and audio processing
/// 5. Notification Preferences - Push, chat, follower notifications
/// 6. About - App version, build number, license info
/// 7. Logout - Sign out with confirmation
class SettingsScreen extends StatefulWidget {
  final WaddleBotAuthService authService;
  final LicenseService licenseService;
  final SettingsService settingsService;
  final VoidCallback onLogout;

  const SettingsScreen({
    super.key,
    required this.authService,
    required this.licenseService,
    required this.settingsService,
    required this.onLogout,
  });

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late User _currentUser;
  late LicenseInfo? _licenseInfo;
  WaddleBotDomain? _selectedDomain;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _currentUser = widget.authService.currentUser ??
        User(
          id: '',
          email: '',
          username: '',
          createdAt: DateTime.now(),
        );
    _licenseInfo = widget.licenseService.currentLicense;
    _loadDomain();
  }

  Future<void> _loadDomain() async {
    try {
      final domain = await widget.settingsService.loadApiDomain();
      if (!mounted) return;
      setState(() {
        _selectedDomain = domain;
      });
    } catch (e) {
      if (!mounted) return;
      developer.log(
        'Error loading API domain: $e',
        name: 'SettingsScreen._loadDomain',
        error: e,
      );
      if (!mounted) return;
      setState(() {
        _selectedDomain = WaddleBotDomain.production;
      });
    }
  }

  Future<void> _handleAccountSettingsEdit() async {
    final formBuilder = FormConfigs.getUserProfileFormConfig(
      onSubmit: (_) async {},
    );
    // Pre-populate form with current user data
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Edit profile functionality coming soon')),
      );
    }
  }

  Future<void> _handleAudioSettings() async {
    const availableMicrophones = [
      'Default Microphone',
      'Built-in Mic',
      'External USB Mic'
    ];
    final isPremium = widget.licenseService
        .isFeatureAvailable(AppConstants.featureAdvancedSettings);

    final formBuilder = FormConfigs.getAudioSettingsFormConfig(
      isPremium: isPremium,
      availableMicrophones: availableMicrophones,
      onSubmit: (_) async {},
    );

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Audio settings functionality coming soon')),
      );
    }
  }

  Future<void> _handleNotificationPreferences() async {
    final formBuilder = FormConfigs.getNotificationPreferencesFormConfig(
      onSubmit: (_) async {},
    );

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Notification preferences coming soon')),
      );
    }
  }

  Future<void> _handleStreamQualityNavigation() async {
    if (mounted) {
      Navigator.pushNamed(context, '/settings/quality-presets');
    }
  }

  Future<void> _handleDomainChange(WaddleBotDomain newDomain) async {
    if (newDomain == _selectedDomain) {
      return;
    }

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Change API Domain'),
        content: const Text('Change API domain? This will log you out.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(context);
              setState(() => _isLoading = true);
              try {
                // Save domain preference
                await widget.settingsService.saveApiDomain(newDomain);

                // Update API client domain
                final apiClient = ApiClient.getInstance();
                apiClient.setDomain(newDomain);

                // Update selected domain
                if (!mounted) return;
                setState(() {
                  _selectedDomain = newDomain;
                });

                // Navigate to login screen (replace route)
                if (!mounted) return;
                Navigator.of(context).pushNamedAndRemoveUntil(
                  '/login',
                  (route) => false,
                );
              } catch (e) {
                if (!mounted) return;
                developer.log(
                  'Error changing API domain: $e',
                  name: 'SettingsScreen._handleDomainChange',
                  error: e,
                );
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('Error changing domain: $e'),
                    backgroundColor: ElderColors.red500,
                  ),
                );
                if (!mounted) return;
                setState(() => _isLoading = false);
              }
            },
            child: const Text('Change Domain',
                style: TextStyle(color: Colors.orange)),
          ),
        ],
      ),
    );
  }

  Future<void> _handleLogout() async {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Sign Out'),
        content: const Text('Are you sure you want to sign out?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(context);
              if (!mounted) return;
              setState(() => _isLoading = true);
              try {
                // Perform logout
                widget.onLogout();
              } finally {
                if (!mounted) return;
                setState(() => _isLoading = false);
              }
            },
            child: const Text('Sign Out', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  String _formatExpirationDate(int millisecondsSinceEpoch) {
    final date = DateTime.fromMillisecondsSinceEpoch(millisecondsSinceEpoch);
    return DateFormat('MMM dd, yyyy').format(date);
  }

  String _getLicenseTierDisplayName(LicenseTier tier) {
    switch (tier) {
      case LicenseTier.free:
        return 'Free';
      case LicenseTier.premium:
        return 'Premium';
      case LicenseTier.pro:
        return 'Professional';
      case LicenseTier.enterprise:
        return 'Enterprise';
    }
  }

  Color _getLicenseTierColor(LicenseTier tier) {
    switch (tier) {
      case LicenseTier.free:
        return Colors.grey;
      case LicenseTier.premium:
        return ElderColors.amber500;
      case LicenseTier.pro:
        return ElderColors.green500;
      case LicenseTier.enterprise:
        return ElderColors.blue500;
    }
  }

  bool get _isAdmin => _currentUser.isSuperAdmin;

  Widget _buildDomainSelectionCard() {
    if (_selectedDomain == null) {
      return Card(
        color: ElderColors.slate800,
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: ElderColors.slate700, width: 1),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: ElderColors.amber500.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(
                      Icons.cloud,
                      color: ElderColors.amber500,
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: 16),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'API Domain',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                        Text(
                          'Loading domain configuration...',
                          style: TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
    }

    return Card(
      color: ElderColors.slate800,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: ElderColors.slate700, width: 1),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: ElderColors.amber500.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(
                    Icons.cloud,
                    color: ElderColors.amber500,
                    size: 24,
                  ),
                ),
                const SizedBox(width: 16),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'API Domain',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      Text(
                        'Select Waddles API endpoint',
                        style: TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ...WaddleBotDomain.values.map(
              (domain) => RadioListTile<WaddleBotDomain>(
                value: domain,
                groupValue: _selectedDomain,
                onChanged: (WaddleBotDomain? newValue) {
                  if (newValue != null) {
                    _handleDomainChange(newValue);
                  }
                },
                title: Text(
                  domain.displayName,
                  style: const TextStyle(
                    color: ElderColors.amber500,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                subtitle: Text(
                  domain.host,
                  style: const TextStyle(fontSize: 12),
                ),
                dense: true,
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        elevation: 0,
        backgroundColor: ElderColors.slate800,
      ),
      backgroundColor: ElderColors.slate950,
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Account Settings
                  _buildSettingsCard(
                    icon: Icons.person,
                    title: 'Account Settings',
                    subtitle: 'Manage your profile information',
                    onTap: _handleAccountSettingsEdit,
                    children: [
                      ListTile(
                        leading: const Icon(Icons.email, size: 20),
                        title: const Text('Email'),
                        subtitle: Text(
                          _currentUser.email,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        dense: true,
                      ),
                      ListTile(
                        leading: const Icon(Icons.badge, size: 20),
                        title: const Text('Username'),
                        subtitle: Text(
                          _currentUser.username.isNotEmpty
                              ? _currentUser.username
                              : 'Not set',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        dense: true,
                      ),
                      Padding(
                        padding: const EdgeInsets.only(top: 12),
                        child: SizedBox(
                          height: 40,
                          child: ElevatedButton.icon(
                            onPressed: _handleAccountSettingsEdit,
                            icon: const Icon(Icons.edit, size: 18),
                            label: const Text('Edit Profile'),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // License Management
                  _buildLicenseCard(),
                  const SizedBox(height: 16),

                  // API Domain Selection
                  _buildDomainSelectionCard(),
                  const SizedBox(height: 16),

                  // Stream Quality
                  _buildSettingsCard(
                    icon: Icons.settings_remote,
                    title: 'Stream Quality',
                    subtitle: 'Configure resolution, bitrate, and FPS',
                    onTap: _handleStreamQualityNavigation,
                    children: [
                      ListTile(
                        leading: const Icon(Icons.videocam, size: 20),
                        title: const Text('Quality Presets'),
                        subtitle:
                            const Text('Manage streaming quality settings'),
                        trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                        dense: true,
                        onTap: _handleStreamQualityNavigation,
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Audio Settings
                  _buildSettingsCard(
                    icon: Icons.mic,
                    title: 'Audio Settings',
                    subtitle: 'Microphone and audio processing',
                    onTap: _handleAudioSettings,
                    children: [
                      ListTile(
                        leading: const Icon(Icons.volume_up, size: 20),
                        title: const Text('Microphone Settings'),
                        subtitle: const Text(
                          'Configure microphone device and volume',
                        ),
                        trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                        dense: true,
                        onTap: _handleAudioSettings,
                      ),
                      if (widget.licenseService.isFeatureAvailable(
                          AppConstants.featureAdvancedSettings))
                        const Padding(
                          padding: EdgeInsets.only(top: 8),
                          child: ListTile(
                            leading: Icon(Icons.auto_awesome, size: 20),
                            title: Text('Advanced Audio Processing'),
                            subtitle: Text(
                              'Noise suppression and echo cancellation available',
                            ),
                            dense: true,
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Notification Preferences
                  _buildSettingsCard(
                    icon: Icons.notifications,
                    title: 'Notification Preferences',
                    subtitle: 'Manage notification settings',
                    onTap: _handleNotificationPreferences,
                    children: [
                      ListTile(
                        leading:
                            const Icon(Icons.notifications_active, size: 20),
                        title: const Text('Push Notifications'),
                        subtitle:
                            const Text('Configure when to receive alerts'),
                        trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                        dense: true,
                        onTap: _handleNotificationPreferences,
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Admin-only settings section
                  if (_isAdmin) ...[
                    _buildAdminSettingsSection(),
                    const SizedBox(height: 16),
                  ],

                  // About
                  _buildAboutCard(),
                  const SizedBox(height: 16),

                  // Logout
                  _buildLogoutCard(),
                  const SizedBox(height: 32),
                ],
              ),
            ),
    );
  }

  Widget _buildSettingsCard({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    required List<Widget> children,
  }) {
    return Card(
      color: ElderColors.slate800,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: ElderColors.slate700, width: 1),
      ),
      child: Column(
        children: [
          ListTile(
            leading: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: ElderColors.amber500.withOpacity(0.2),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: ElderColors.amber500, size: 24),
            ),
            title: Text(title,
                style: const TextStyle(fontWeight: FontWeight.bold)),
            subtitle: Text(subtitle, style: const TextStyle(fontSize: 12)),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: children,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLicenseCard() {
    if (_licenseInfo == null) {
      return Card(
        color: ElderColors.slate800,
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: ElderColors.slate700, width: 1),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: ElderColors.amber500.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(
                      Icons.verified,
                      color: ElderColors.amber500,
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: 16),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'License Management',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                        Text(
                          'View and manage your license',
                          style: TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Center(
                child: Text('License information loading...'),
              ),
            ],
          ),
        ),
      );
    }

    final isExpired = _licenseInfo!.isExpired;
    final expirationDate = _formatExpirationDate(_licenseInfo!.expirationDate);
    final tierColor = _getLicenseTierColor(_licenseInfo!.tier);
    final tierName = _getLicenseTierDisplayName(_licenseInfo!.tier);

    return Card(
      color: ElderColors.slate800,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: isExpired ? ElderColors.red500 : ElderColors.slate700,
          width: 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: tierColor.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    isExpired ? Icons.warning : Icons.verified,
                    color: tierColor,
                    size: 24,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'License Management',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      Text(
                        'Current: $tierName License',
                        style: TextStyle(
                          fontSize: 12,
                          color: tierColor,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            // License tier and status
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: ElderColors.slate900,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('License Tier'),
                      Chip(
                        label: Text(tierName),
                        backgroundColor: tierColor.withOpacity(0.2),
                        labelStyle: TextStyle(color: tierColor),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  if (isExpired)
                    const Row(
                      children: [
                        Icon(Icons.error, color: ElderColors.red500, size: 18),
                        SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'License expired',
                            style: TextStyle(color: ElderColors.red500),
                          ),
                        ),
                      ],
                    )
                  else
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Expires'),
                        Text(
                          expirationDate,
                          style: const TextStyle(fontWeight: FontWeight.w500),
                        ),
                      ],
                    ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            // Features list
            if (_licenseInfo!.features.isNotEmpty) ...[
              const Text(
                'Available Features',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _licenseInfo!.features
                    .take(5)
                    .map((feature) => Chip(
                          label: Text(
                            feature
                                .replaceAll('_', ' ')
                                .split(' ')
                                .map((w) => w.isEmpty
                                    ? ''
                                    : w[0].toUpperCase() + w.substring(1))
                                .join(' '),
                            style: const TextStyle(fontSize: 11),
                          ),
                          backgroundColor:
                              ElderColors.amber500.withOpacity(0.2),
                          labelStyle: const TextStyle(
                            color: ElderColors.amber500,
                            fontSize: 11,
                          ),
                        ))
                    .toList(),
              ),
              if (_licenseInfo!.features.length > 5)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    '+${_licenseInfo!.features.length - 5} more features',
                    style: const TextStyle(
                      fontSize: 11,
                      color: ElderColors.slate400,
                    ),
                  ),
                ),
            ],
            const SizedBox(height: 16),
            // Max streams info
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Max Concurrent Streams'),
                Text(
                  '${_licenseInfo!.maxStreams}',
                  style: const TextStyle(fontWeight: FontWeight.w500),
                ),
              ],
            ),
            const SizedBox(height: 16),
            // Upgrade button (if not enterprise)
            if (_licenseInfo!.tier != LicenseTier.enterprise)
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Upgrade coming soon')),
                    );
                  },
                  icon: const Icon(Icons.upgrade, size: 18),
                  label: const Text('Upgrade License'),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildAdminSettingsSection() {
    return Card(
      color: ElderColors.slate800,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(
          color: ElderColors.amber500,
          width: 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: ElderColors.amber500.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(
                    Icons.admin_panel_settings,
                    color: ElderColors.amber500,
                    size: 24,
                  ),
                ),
                const SizedBox(width: 16),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Admin Settings',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      Text(
                        'Administrative functions available',
                        style: TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ListTile(
              leading: const Icon(Icons.people, size: 20),
              title: const Text('Manage Users'),
              subtitle: const Text('View and manage user accounts'),
              trailing: const Icon(Icons.arrow_forward_ios, size: 16),
              dense: true,
              onTap: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('User management coming soon')),
                );
              },
            ),
            const SizedBox(height: 8),
            ListTile(
              leading: const Icon(Icons.security, size: 20),
              title: const Text('Security Settings'),
              subtitle: const Text('Configure security policies'),
              trailing: const Icon(Icons.arrow_forward_ios, size: 16),
              dense: true,
              onTap: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                      content: Text('Security settings coming soon')),
                );
              },
            ),
            const SizedBox(height: 8),
            ListTile(
              leading: const Icon(Icons.analytics, size: 20),
              title: const Text('System Analytics'),
              subtitle: const Text('View system metrics and logs'),
              trailing: const Icon(Icons.arrow_forward_ios, size: 16),
              dense: true,
              onTap: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Analytics coming soon')),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAboutCard() {
    return Card(
      color: ElderColors.slate800,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: ElderColors.slate700, width: 1),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: ElderColors.amber500.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(
                    Icons.info,
                    color: ElderColors.amber500,
                    size: 24,
                  ),
                ),
                const SizedBox(width: 16),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'About',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      Text(
                        'App information and version',
                        style: TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: ElderColors.slate900,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('App Version'),
                      Text(
                        AppConstants.appVersion,
                        style: TextStyle(fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                  SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Build Number'),
                      Text(
                        '2024.1.0',
                        style: TextStyle(fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                  SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Product'),
                      Text(
                        AppConstants.productName,
                        style: TextStyle(
                          fontWeight: FontWeight.w500,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            const Center(
              child: Text(
                '© 2024 Penguin Tech Inc.\nGazer Mobile Stream Studio',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 11,
                  color: ElderColors.slate400,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLogoutCard() {
    return Card(
      color: ElderColors.slate800,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: ElderColors.red500, width: 1),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: ElderColors.red500.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(
                    Icons.logout,
                    color: ElderColors.red500,
                    size: 24,
                  ),
                ),
                const SizedBox(width: 16),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Account',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      Text(
                        'Sign out of your account',
                        style: TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _handleLogout,
              icon: const Icon(Icons.logout, size: 18),
              label: const Text('Sign Out'),
              style: ElevatedButton.styleFrom(
                backgroundColor: ElderColors.red500,
                foregroundColor: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
