/// Camera overlay size presets.
enum OverlaySize { small, medium, large, custom }

/// Camera overlay corner positions.
enum OverlayCorner { topLeft, topRight, bottomLeft, bottomRight }

/// Camera overlay settings.
class OverlaySettings {
  final bool enabled;
  final OverlaySize size;
  final OverlayCorner position;

  const OverlaySettings({
    this.enabled = false,
    this.size = OverlaySize.medium,
    this.position = OverlayCorner.topLeft,
  });

  OverlaySettings copyWith({
    bool? enabled,
    OverlaySize? size,
    OverlayCorner? position,
  }) {
    return OverlaySettings(
      enabled: enabled ?? this.enabled,
      size: size ?? this.size,
      position: position ?? this.position,
    );
  }

  double get sizeFraction {
    switch (size) {
      case OverlaySize.small:
        return 0.15;
      case OverlaySize.medium:
        return 0.25;
      case OverlaySize.large:
        return 0.35;
      case OverlaySize.custom:
        return 0.25;
    }
  }
}
