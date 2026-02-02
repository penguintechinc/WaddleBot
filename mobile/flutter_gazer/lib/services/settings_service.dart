import 'package:shared_preferences/shared_preferences.dart';
import '../models/stream_config.dart';
import '../models/overlay_settings.dart';
import '../models/domain_config.dart';

/// Persists user settings to SharedPreferences.
class SettingsService {
  static const _keyRtmpUrl = 'rtmp_url';
  static const _keyStreamKey = 'stream_key';
  static const _keyResolutionIndex = 'resolution_index';
  static const _keyBitrateIndex = 'bitrate_index';
  static const _keyFpsIndex = 'fps_index';
  static const _keyOverlayEnabled = 'overlay_enabled';
  static const _keyOverlaySize = 'overlay_size';
  static const _keyOverlayPosition = 'overlay_position';
  static const _keyEulaAccepted = 'eula_accepted';
  static const _keyApiDomain = 'api_domain';

  static const List<MapEntry<String, List<int>>> resolutions = [
    MapEntry('360p (640x360)', [640, 360]),
    MapEntry('480p (854x480)', [854, 480]),
    MapEntry('540p (960x540)', [960, 540]),
    MapEntry('720p (1280x720)', [1280, 720]),
    MapEntry('1080p (1920x1080)', [1920, 1080]),
  ];

  static const List<MapEntry<String, int>> bitrates = [
    MapEntry('1000 kbps', 1000000),
    MapEntry('3000 kbps', 3000000),
    MapEntry('5000 kbps', 5000000),
  ];

  static const List<MapEntry<String, int>> fpsOptions = [
    MapEntry('15 FPS', 15),
    MapEntry('24 FPS', 24),
    MapEntry('30 FPS', 30),
    MapEntry('60 FPS', 60),
  ];

  Future<StreamConfig> loadStreamConfig() async {
    final prefs = await SharedPreferences.getInstance();
    final resIdx = prefs.getInt(_keyResolutionIndex) ?? 3; // 720p
    final brIdx = prefs.getInt(_keyBitrateIndex) ?? 1; // 3000 kbps
    final fpsIdx = prefs.getInt(_keyFpsIndex) ?? 2; // 30 FPS

    final res = resolutions[resIdx.clamp(0, resolutions.length - 1)].value;
    final br = bitrates[brIdx.clamp(0, bitrates.length - 1)].value;
    final fps = fpsOptions[fpsIdx.clamp(0, fpsOptions.length - 1)].value;

    return StreamConfig(
      width: res[0],
      height: res[1],
      fps: fps,
      videoBitrate: br,
      rtmpUrl: prefs.getString(_keyRtmpUrl) ?? '',
      streamKey: prefs.getString(_keyStreamKey) ?? '',
    );
  }

  Future<void> saveStreamConfig({
    String? rtmpUrl,
    String? streamKey,
    int? resolutionIndex,
    int? bitrateIndex,
    int? fpsIndex,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    if (rtmpUrl != null) await prefs.setString(_keyRtmpUrl, rtmpUrl);
    if (streamKey != null) await prefs.setString(_keyStreamKey, streamKey);
    if (resolutionIndex != null) {
      await prefs.setInt(_keyResolutionIndex, resolutionIndex);
    }
    if (bitrateIndex != null) {
      await prefs.setInt(_keyBitrateIndex, bitrateIndex);
    }
    if (fpsIndex != null) await prefs.setInt(_keyFpsIndex, fpsIndex);
  }

  Future<OverlaySettings> loadOverlaySettings() async {
    final prefs = await SharedPreferences.getInstance();
    return OverlaySettings(
      enabled: prefs.getBool(_keyOverlayEnabled) ?? false,
      size: OverlaySize
          .values[prefs.getInt(_keyOverlaySize) ?? OverlaySize.medium.index],
      position: OverlayCorner.values[
          prefs.getInt(_keyOverlayPosition) ?? OverlayCorner.topLeft.index],
    );
  }

  Future<void> saveOverlaySettings(OverlaySettings settings) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyOverlayEnabled, settings.enabled);
    await prefs.setInt(_keyOverlaySize, settings.size.index);
    await prefs.setInt(_keyOverlayPosition, settings.position.index);
  }

  Future<bool> isEulaAccepted() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_keyEulaAccepted) ?? false;
  }

  Future<void> acceptEula() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyEulaAccepted, true);
  }

  Future<WaddleBotDomain> loadApiDomain() async {
    final prefs = await SharedPreferences.getInstance();
    final domainIndex = prefs.getInt(_keyApiDomain) ?? 2; // production is index 2
    switch (domainIndex) {
      case 0:
        return WaddleBotDomain.penguintech;
      case 1:
        return WaddleBotDomain.waddles;
      case 2:
      default:
        return WaddleBotDomain.production;
    }
  }

  Future<void> saveApiDomain(WaddleBotDomain domain) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_keyApiDomain, domain.index);
  }
}
