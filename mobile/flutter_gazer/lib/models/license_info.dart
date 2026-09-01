/// License tier enumeration.
enum LicenseTier { free, premium, pro, enterprise }

/// License data model.
class LicenseInfo {
  final String licenseKey;
  final bool isValid;
  final int expirationDate;
  final Set<String> features;
  final int maxStreams;
  final String licenseName;
  final String? error;
  final LicenseTier tier;

  const LicenseInfo({
    required this.licenseKey,
    required this.isValid,
    required this.expirationDate,
    required this.features,
    this.maxStreams = 1,
    this.licenseName = '',
    this.error,
    this.tier = LicenseTier.free,
  });

  bool get isExpired => DateTime.now().millisecondsSinceEpoch > expirationDate;

  bool hasFeature(String feature) => features.contains(feature);

  /// Check if license tier supports external RTMP streaming.
  bool canStreamExternal() {
    return tier == LicenseTier.pro || tier == LicenseTier.enterprise;
  }

  /// Get maximum bitrate for current license tier (in bps).
  int getMaxBitrate() {
    switch (tier) {
      case LicenseTier.free:
        return 1500000; // 1.5 Mbps
      case LicenseTier.premium:
        return 5000000; // 5 Mbps
      case LicenseTier.pro:
        return 25000000; // 25 Mbps
      case LicenseTier.enterprise:
        return 100000000; // 100 Mbps (unlimited practically)
    }
  }

  /// Get maximum concurrent workflows for current license tier.
  int getMaxWorkflows() {
    switch (tier) {
      case LicenseTier.free:
        return 1;
      case LicenseTier.premium:
        return 3;
      case LicenseTier.pro:
        return 10;
      case LicenseTier.enterprise:
        return 100;
    }
  }

  factory LicenseInfo.fromJson(Map<String, dynamic> json) {
    final tierStr = json['tier'] as String? ?? 'free';
    final tier = _parseLicenseTier(tierStr);

    return LicenseInfo(
      licenseKey: json['license_key'] as String? ?? '',
      isValid: json['is_valid'] as bool? ?? false,
      expirationDate: json['expiration_date'] as int? ?? 0,
      features: Set<String>.from(
        (json['features'] as List<dynamic>?)?.map((f) => f.toString()) ?? [],
      ),
      maxStreams: json['max_streams'] as int? ?? 1,
      licenseName: json['license_name'] as String? ?? '',
      error: json['error'] as String?,
      tier: tier,
    );
  }
}

/// Parse LicenseTier from string representation.
LicenseTier _parseLicenseTier(String tierStr) {
  try {
    return LicenseTier.values.firstWhere(
      (e) => e.name == tierStr.toLowerCase(),
      orElse: () => LicenseTier.free,
    );
  } catch (_) {
    return LicenseTier.free;
  }
}
