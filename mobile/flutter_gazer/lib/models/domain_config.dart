/// Domain configuration for Waddles environments
enum WaddleBotDomain {
  penguintech,
  waddles,
  production,
}

extension WaddleBotDomainExtension on WaddleBotDomain {
  /// Returns the API host for this domain
  String get host {
    switch (this) {
      case WaddleBotDomain.penguintech:
        return 'waddlebot.penguintech.io';
      case WaddleBotDomain.waddles:
        return 'waddles.penguintech.io';
      case WaddleBotDomain.production:
        return 'app.waddlebot.io';
    }
  }

  /// Returns the display name for this domain
  String get displayName {
    switch (this) {
      case WaddleBotDomain.penguintech:
        return 'PenguinTech Dev';
      case WaddleBotDomain.waddles:
        return 'Waddles Dev';
      case WaddleBotDomain.production:
        return 'Waddles';
    }
  }

  /// Returns the API URL for this domain
  String get apiUrl {
    return 'https://$host/api/v2';
  }

  /// Returns the WebSocket URL for this domain
  String get wsUrl {
    return 'wss://$host/api/v1/ws';
  }

  /// Factory method to create domain from host string
  /// Returns production domain if host does not match any known domain
  static WaddleBotDomain fromHost(String host) {
    switch (host) {
      case 'waddlebot.penguintech.io':
        return WaddleBotDomain.penguintech;
      case 'waddles.penguintech.io':
        return WaddleBotDomain.waddles;
      case 'app.waddlebot.io':
        return WaddleBotDomain.production;
      default:
        return WaddleBotDomain.production;
    }
  }
}

extension WaddleBotDomainFactory on WaddleBotDomain {
  /// Factory method to create domain from index
  /// 0 = penguintech, 1 = waddles, 2 = production (default)
  /// Invalid indices default to production
  static WaddleBotDomain fromIndex(int index) {
    switch (index) {
      case 0:
        return WaddleBotDomain.penguintech;
      case 1:
        return WaddleBotDomain.waddles;
      case 2:
      default:
        return WaddleBotDomain.production;
    }
  }
}
