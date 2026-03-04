import 'package:flutter_libs/flutter_libs.dart';

/// Form configuration helpers for Flutter Gazer application.
/// Provides pre-configured form definitions for common operations using FormModalBuilder.
class FormConfigs {
  /// User profile editing form configuration.
  /// Allows users to update their profile information: name, email, avatar, and bio.
  ///
  /// Fields:
  /// - name: Text field (required, 2-50 chars)
  /// - email: Email field (required, valid email format)
  /// - avatar: URL field (optional, custom avatar URL)
  /// - bio: Text area (optional, max 500 chars, for personal bio)
  static FormModalBuilder getUserProfileFormConfig({
    required Future<void> Function(Map<String, dynamic>) onSubmit,
  }) {
    return FormModalBuilder(
      title: 'Edit Profile',
      onSubmit: onSubmit,
      fields: const [
        FormFieldConfig(
          name: 'name',
          label: 'Display Name',
          type: FormFieldType.text,
          required: true,
          min: 2,
          max: 50,
          placeholder: 'Enter your display name',
          helpText: 'Used in stream chat and user mentions',
        ),
        FormFieldConfig(
          name: 'email',
          label: 'Email Address',
          type: FormFieldType.email,
          required: true,
          pattern: r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
          placeholder: 'your.email@example.com',
          helpText: 'Used for account recovery and notifications',
        ),
        FormFieldConfig(
          name: 'avatar',
          label: 'Avatar URL',
          type: FormFieldType.url,
          required: false,
          pattern: r'^https?://',
          placeholder: 'https://example.com/avatar.jpg',
          helpText: 'Custom avatar image URL (JPG, PNG, max 5MB)',
        ),
        FormFieldConfig(
          name: 'bio',
          label: 'Bio',
          type: FormFieldType.textarea,
          required: false,
          max: 500,
          placeholder: 'Tell your viewers about yourself...',
          helpText:
              'Personal description displayed on your profile (max 500 chars)',
        ),
      ],
      submitLabel: 'Save Profile',
      cancelLabel: 'Cancel',
    );
  }

  /// Stream configuration form for video quality and performance settings.
  /// Allows users to configure streaming parameters: resolution quality, bitrate, and frames per second.
  /// Premium feature: Access to advanced streaming profiles (4K, 60fps, adaptive bitrate).
  ///
  /// Fields:
  /// - quality: Select field (720p, 1080p, 1440p, 4K - with premium gate)
  /// - bitrate: Number field (1000-50000 kbps, with premium limits)
  /// - fps: Select field (24, 30, 60 fps - with premium gate for 60fps)
  /// - adaptiveBitrate: Checkbox (premium feature for dynamic bitrate adjustment)
  static FormModalBuilder getStreamConfigFormConfig({
    required bool isPremium,
    required Future<void> Function(Map<String, dynamic>) onSubmit,
  }) {
    return FormModalBuilder(
      title: 'Stream Configuration',
      onSubmit: onSubmit,
      fields: [
        FormFieldConfig(
          name: 'quality',
          label: 'Video Quality',
          type: FormFieldType.select,
          required: true,
          options: [
            const FormFieldOption(label: '720p (HD)', value: '720p'),
            const FormFieldOption(label: '1080p (Full HD)', value: '1080p'),
            if (isPremium)
              const FormFieldOption(
                  label: '1440p (2K) - Premium', value: '1440p'),
            if (isPremium)
              const FormFieldOption(
                  label: '4K (Ultra HD) - Premium', value: '4k'),
          ],
          defaultValue: '720p',
          helpText: 'Higher quality requires more bandwidth',
        ),
        FormFieldConfig(
          name: 'bitrate',
          label: 'Bitrate (kbps)',
          type: FormFieldType.number,
          required: true,
          min: 1000,
          max: isPremium ? 50000 : 8000,
          defaultValue: '2500',
          placeholder: '2500',
          helpText: isPremium
              ? 'Recommended: 2500-5000 kbps for 1080p30fps'
              : 'Recommended: 2500-5000 kbps for 1080p30fps (Premium: up to 50000 kbps)',
        ),
        FormFieldConfig(
          name: 'fps',
          label: 'Frames Per Second',
          type: FormFieldType.select,
          required: true,
          options: [
            const FormFieldOption(label: '24 FPS', value: '24'),
            const FormFieldOption(label: '30 FPS', value: '30'),
            if (isPremium)
              const FormFieldOption(label: '60 FPS - Premium', value: '60'),
          ],
          defaultValue: '30',
          helpText: 'Higher FPS provides smoother motion but increases bitrate',
        ),
        if (isPremium)
          const FormFieldConfig(
            name: 'adaptiveBitrate',
            label: 'Adaptive Bitrate',
            type: FormFieldType.checkbox,
            required: false,
            defaultValue: 'true',
            helpText:
                'Automatically adjust bitrate based on network conditions (Premium feature)',
          ),
      ],
      submitLabel: 'Apply Settings',
      cancelLabel: 'Cancel',
    );
  }

  /// RTMP endpoint configuration form for custom streaming setup.
  /// Allows users to configure custom RTMP streaming endpoints with authentication.
  /// Premium feature: Multiple endpoints, redundancy, and advanced analytics.
  ///
  /// Fields:
  /// - rtmpUrl: URL field (required, must be valid RTMP endpoint)
  /// - streamKey: Password field (required, secret stream key)
  /// - endpointName: Text field (optional, friendly name for the endpoint)
  /// - backup: Checkbox (optional, premium feature for backup endpoint)
  /// - analytics: Checkbox (optional, premium feature for detailed streaming analytics)
  static FormModalBuilder getRtmpEndpointFormConfig({
    required bool isPremium,
    required Future<void> Function(Map<String, dynamic>) onSubmit,
  }) {
    return FormModalBuilder(
      title: 'RTMP Endpoint Setup',
      onSubmit: onSubmit,
      fields: [
        const FormFieldConfig(
          name: 'rtmpUrl',
          label: 'RTMP Server URL',
          type: FormFieldType.url,
          required: true,
          pattern: r'^rtmps?://',
          placeholder: 'rtmp://live.example.com/app',
          helpText: 'Server address provided by your streaming service',
        ),
        const FormFieldConfig(
          name: 'streamKey',
          label: 'Stream Key',
          type: FormFieldType.password,
          required: true,
          min: 10,
          placeholder: '••••••••••••••••',
          helpText: 'Keep this secret! Do not share publicly',
        ),
        const FormFieldConfig(
          name: 'endpointName',
          label: 'Endpoint Name',
          type: FormFieldType.text,
          required: false,
          max: 100,
          placeholder: 'e.g., "Primary Twitch", "YouTube Backup"',
          helpText: 'Friendly name to identify this endpoint',
        ),
        if (isPremium)
          const FormFieldConfig(
            name: 'backup',
            label: 'Use as Backup Endpoint',
            type: FormFieldType.checkbox,
            required: false,
            defaultValue: 'false',
            helpText:
                'Enable redundancy: stream to primary and backup simultaneously (Premium)',
          ),
        if (isPremium)
          const FormFieldConfig(
            name: 'analytics',
            label: 'Enable Advanced Analytics',
            type: FormFieldType.checkbox,
            required: false,
            defaultValue: 'true',
            helpText:
                'Track detailed metrics: bitrate, dropped frames, viewer bandwidth (Premium)',
          ),
      ],
      submitLabel: 'Save Endpoint',
      cancelLabel: 'Cancel',
    );
  }

  /// Audio settings form configuration.
  /// Allows users to configure microphone, audio processing, and levels.
  /// Premium feature: Advanced audio processing (noise suppression, echo cancellation).
  ///
  /// Fields:
  /// - microphone: Select field (available audio devices)
  /// - volume: Number field (0-100, microphone gain)
  /// - noiseGate: Number field (premium feature, noise suppression threshold)
  /// - echoCancel: Checkbox (premium feature, echo cancellation)
  static FormModalBuilder getAudioSettingsFormConfig({
    required bool isPremium,
    required List<String> availableMicrophones,
    required Future<void> Function(Map<String, dynamic>) onSubmit,
  }) {
    return FormModalBuilder(
      title: 'Audio Settings',
      onSubmit: onSubmit,
      fields: [
        FormFieldConfig(
          name: 'microphone',
          label: 'Microphone Device',
          type: FormFieldType.select,
          required: true,
          options: availableMicrophones
              .map((mic) => FormFieldOption(label: mic, value: mic))
              .toList(),
          helpText: 'Select your microphone input device',
        ),
        const FormFieldConfig(
          name: 'volume',
          label: 'Microphone Volume',
          type: FormFieldType.number,
          required: true,
          min: 0,
          max: 100,
          defaultValue: '80',
          helpText: 'Microphone gain level (0-100%)',
        ),
        if (isPremium)
          const FormFieldConfig(
            name: 'noiseGate',
            label: 'Noise Gate Threshold (dB)',
            type: FormFieldType.number,
            required: false,
            min: -80,
            max: 0,
            defaultValue: '-40',
            helpText:
                'Mute audio below this level to reduce background noise (Premium)',
          ),
        if (isPremium)
          const FormFieldConfig(
            name: 'echoCancel',
            label: 'Echo Cancellation',
            type: FormFieldType.checkbox,
            required: false,
            defaultValue: 'true',
            helpText:
                'Automatically remove echo and reverb from your microphone (Premium)',
          ),
      ],
      submitLabel: 'Save Audio Settings',
      cancelLabel: 'Cancel',
    );
  }

  /// Notification preferences form configuration.
  /// Allows users to customize notification settings for various events.
  ///
  /// Fields:
  /// - pushNotifications: Checkbox (enable/disable all push notifications)
  /// - followerNotifications: Checkbox (notify on new followers)
  /// - chatNotifications: Checkbox (notify on chat messages)
  /// - donationNotifications: Checkbox (notify on donations/tips)
  /// - soundEnabled: Checkbox (enable notification sounds)
  static FormModalBuilder getNotificationPreferencesFormConfig({
    required Future<void> Function(Map<String, dynamic>) onSubmit,
  }) {
    return FormModalBuilder(
      title: 'Notification Preferences',
      onSubmit: onSubmit,
      fields: const [
        FormFieldConfig(
          name: 'pushNotifications',
          label: 'Enable Push Notifications',
          type: FormFieldType.checkbox,
          required: false,
          defaultValue: 'true',
          helpText: 'Receive notifications on your device',
        ),
        FormFieldConfig(
          name: 'followerNotifications',
          label: 'Follower Notifications',
          type: FormFieldType.checkbox,
          required: false,
          defaultValue: 'true',
          helpText: 'Get notified when someone follows your stream',
        ),
        FormFieldConfig(
          name: 'chatNotifications',
          label: 'Chat Message Notifications',
          type: FormFieldType.checkbox,
          required: false,
          defaultValue: 'false',
          helpText: 'Get notified when you receive chat messages',
        ),
        FormFieldConfig(
          name: 'donationNotifications',
          label: 'Donation/Tip Notifications',
          type: FormFieldType.checkbox,
          required: false,
          defaultValue: 'true',
          helpText: 'Get notified when viewers send donations or tips',
        ),
        FormFieldConfig(
          name: 'soundEnabled',
          label: 'Notification Sounds',
          type: FormFieldType.checkbox,
          required: false,
          defaultValue: 'true',
          helpText: 'Play sound when notifications arrive',
        ),
      ],
      submitLabel: 'Save Preferences',
      cancelLabel: 'Cancel',
    );
  }
}
