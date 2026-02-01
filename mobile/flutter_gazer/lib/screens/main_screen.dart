import 'dart:async';
import 'dart:io' show Platform;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/constants.dart';
import '../config/theme.dart';
import '../models/auth.dart';
import '../models/stream_config.dart';
import '../models/stream_state.dart';
import '../models/overlay_settings.dart';
import '../services/license_service.dart';
import '../services/rtmp_service.dart';
import '../services/usb_capture_service.dart';
import '../services/stream_compositor_service.dart';
import '../services/settings_service.dart';
import '../services/waddlebot_service.dart';
import '../widgets/stream_preview_widget.dart';
import '../widgets/stream_controls.dart';
import '../widgets/usb_status_card.dart';
import '../widgets/camera_overlay_widget.dart';
import '../widgets/eula_dialog.dart';
import '../widgets/chat_overlay_widget.dart';
import '../widgets/app_sidebar.dart';
import '../services/waddlebot_chat_service.dart';
import 'communities/community_list.dart';
import 'chat/channel_list.dart';
import 'members/member_list.dart';
import 'settings_screen.dart';

/// Enum for app navigation routes
enum AppRoute {
  communities('/communities', 'Communities'),
  chat('/chat', 'Chat'),
  members('/members', 'Members'),
  streaming('/streaming', 'Streaming'),
  settings('/settings', 'Settings');

  const AppRoute(this.path, this.label);
  final String path;
  final String label;
}

/// Main application shell with sidebar navigation and multi-screen support
class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  late final LicenseService _licenseService;
  late final RtmpService _rtmpService;
  late final UsbCaptureService _usbService;
  late final StreamCompositorService _compositorService;
  late final SettingsService _settingsService;
  late final WaddleBotService _waddleBotService;
  late final WaddleBotChatService _chatService;

  // Navigation state
  AppRoute _currentRoute = AppRoute.streaming;
  final PageController _pageController = PageController(initialPage: 3);

  StreamConfig _streamConfig = const StreamConfig();
  OverlaySettings _overlaySettings = const OverlaySettings();
  bool _isStreaming = false;
  bool _isChatOverlayVisible = false;
  String _usbStatusText = 'Not Connected';
  Color _usbStatusColor = GazerTheme.streamingRed;
  String _streamStatusText = 'Ready';
  bool _initialized = false;

  StreamSubscription? _rtmpSub;
  StreamSubscription? _usbSub;
  StreamSubscription? _fallbackSub;

  @override
  void initState() {
    super.initState();
    _licenseService = LicenseService();
    _rtmpService = RtmpService();
    _usbService = UsbCaptureService();
    _compositorService = StreamCompositorService();
    _settingsService = SettingsService();
    _waddleBotService = WaddleBotService();
    _chatService = WaddleBotChatService();
    _initializeApp();
  }

  Future<void> _initializeApp() async {
    // Check EULA
    final eulaAccepted = await _settingsService.isEulaAccepted();
    if (!eulaAccepted && mounted) {
      final accepted = await EulaDialog.show(context);
      if (accepted != true) {
        // EULA declined — cannot continue
        return;
      }
      await _settingsService.acceptEula();
    }

    // Initialize license
    await _licenseService.initialize();

    // Connect chat service
    _chatService.connect();

    // Load settings
    _streamConfig = await _settingsService.loadStreamConfig();
    _overlaySettings = await _settingsService.loadOverlaySettings();

    // Listen to state changes
    _rtmpSub = _rtmpService.stateStream.listen(_onStreamStateChanged);
    _usbSub = _usbService.stateStream.listen(_onUsbStateChanged);
    _fallbackSub = _compositorService.fallbackStream.listen((_) {
      if (mounted) setState(() {});
    });

    // Auto-scan for USB devices
    _usbService.scanForDevices();

    if (mounted) setState(() => _initialized = true);
  }

  void _onStreamStateChanged(StreamState state) {
    if (!mounted) return;
    setState(() {
      switch (state) {
        case StreamDisconnected():
          _streamStatusText = 'Ready';
          _isStreaming = false;
        case StreamConnecting():
          _streamStatusText = 'Connecting...';
        case StreamConnected():
          _streamStatusText = 'Connected';
        case StreamStreaming():
          _streamStatusText = 'Streaming';
          _isStreaming = true;
        case StreamError(message: final msg):
          _streamStatusText = 'Error: $msg';
          _isStreaming = false;
      }
    });
  }

  void _onUsbStateChanged(UsbDeviceState state) {
    if (!mounted) return;
    setState(() {
      switch (state) {
        case UsbDisconnected():
          _usbStatusText = 'Not Connected';
          _usbStatusColor = GazerTheme.streamingRed;
          if (_isStreaming) {
            _compositorService.enableFallbackMode('Capture Card Disconnected');
          }
        case UsbDeviceFound(deviceName: final name):
          _usbStatusText = 'Found: $name';
          _usbStatusColor = GazerTheme.warningAmber;
        case UsbConnecting():
          _usbStatusText = 'Connecting...';
          _usbStatusColor = GazerTheme.warningAmber;
        case UsbConnected(deviceName: final name):
          _usbStatusText = 'Connected: $name';
          _usbStatusColor = GazerTheme.connectedGreen;
          _compositorService.disableFallbackMode();
        case UsbError(message: final msg):
          _usbStatusText = 'Error: $msg';
          _usbStatusColor = GazerTheme.streamingRed;
      }
    });
  }

  Future<void> _startStreaming() async {
    if (_streamConfig.rtmpUrl.isEmpty) {
      _showSnack('Please configure RTMP URL in settings');
      return;
    }
    if (_usbService.currentState is! UsbConnected) {
      _showSnack('Please connect USB device first');
      return;
    }
    _compositorService.initialize(_streamConfig.width, _streamConfig.height);
    _compositorService.startCompositing();
    await _rtmpService.startStreaming(_streamConfig);

    // Report to WaddleBot if licensed
    if (_licenseService.isFeatureAvailable(AppConstants.featureWaddleBotAi)) {
      _waddleBotService.reportStreamStarted(_streamConfig);
    }
  }

  Future<void> _stopStreaming() async {
    await _rtmpService.stopStreaming();
    _compositorService.stopCompositing();

    if (_licenseService.isFeatureAvailable(AppConstants.featureWaddleBotAi)) {
      _waddleBotService.reportStreamStopped();
    }
  }

  void _openSettings() async {
    final result = await Navigator.push<StreamConfig>(
      context,
      MaterialPageRoute(
        builder: (_) => SettingsScreen(
          currentConfig: _streamConfig,
          licenseService: _licenseService,
          settingsService: _settingsService,
        ),
      ),
    );
    if (result != null && mounted) {
      setState(() => _streamConfig = result);
    }
  }

  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  void dispose() {
    _rtmpSub?.cancel();
    _usbSub?.cancel();
    _fallbackSub?.cancel();
    _pageController.dispose();
    _rtmpService.dispose();
    _usbService.dispose();
    _compositorService.dispose();
    _waddleBotService.dispose();
    _chatService.dispose();
    super.dispose();
  }

  void _navigateToRoute(AppRoute route) {
    setState(() => _currentRoute = route);
    _pageController.animateToPage(
      route.index,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!_initialized) {
      return Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    // On mobile (small screens), use bottom navigation
    // On tablets/desktop (large screens), use sidebar navigation
    final isSmallScreen = MediaQuery.of(context).size.width < 600;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Gazer Stream Studio'),
        elevation: 0,
      ),
      drawer: !isSmallScreen
          ? null
          : Drawer(
              child: _buildSidebarContent(),
            ),
      body: isSmallScreen
          ? _buildMobileLayout()
          : _buildTabletLayout(),
    );
  }

  Widget _buildTabletLayout() {
    return Row(
      children: [
        // Sidebar (fixed width)
        SizedBox(
          width: 280,
          child: _buildSidebarContent(),
        ),
        // Main content area
        Expanded(
          child: _buildScreenContent(),
        ),
      ],
    );
  }

  Widget _buildMobileLayout() {
    return _buildScreenContent();
  }

  Widget _buildSidebarContent() {
    // Mock user for sidebar (would come from auth provider in real app)
    final mockUser = User(
      id: 'mock-user-1',
      email: 'streamer@example.com',
      username: 'Streamer User',
      isSuperAdmin: true,
      createdAt: DateTime.now(),
      avatarUrl: null,
    );

    return AppSidebar(
      currentUser: mockUser,
      selectedRoute: _currentRoute.path,
      onNavigate: () {
        // Close drawer on mobile
        if (Navigator.of(context).canPop()) {
          Navigator.of(context).pop();
        }
      },
      onRouteSelected: (routePath) {
        // Find matching AppRoute and navigate to it
        final route = AppRoute.values.firstWhere(
          (r) => r.path == routePath,
          orElse: () => AppRoute.streaming,
        );
        _navigateToRoute(route);
      },
    );
  }

  Widget _buildScreenContent() {
    return PageView(
      controller: _pageController,
      onPageChanged: (index) {
        if (index >= 0 && index < AppRoute.values.length) {
          setState(() => _currentRoute = AppRoute.values[index]);
        }
      },
      children: [
        _buildCommunitiesScreen(),
        _buildChatScreen(),
        _buildMembersScreen(),
        _buildStreamingScreen(),
        _buildSettingsScreen(),
      ],
    );
  }

  /// Communities screen showing community list and management
  Widget _buildCommunitiesScreen() {
    return const CommunityListScreen(isAdmin: true);
  }

  /// Chat screen showing community chat channels
  Widget _buildChatScreen() {
    return ChannelListScreen(
      communityId: 'general',
      chatService: _chatService,
    );
  }

  /// Members screen showing community members
  Widget _buildMembersScreen() {
    return const MemberListScreen(
      communityId: 'general',
      isAdmin: true,
    );
  }

  /// Streaming screen with video preview and controls
  Widget _buildStreamingScreen() {
    return Column(
      children: [
        // Video preview area
        Expanded(
          child: Stack(
            children: [
              StreamPreviewWidget(textureId: _usbService.textureId),
              if (_compositorService.isInFallbackMode)
                Center(
                  child: Container(
                    padding: const EdgeInsets.all(32),
                    decoration: BoxDecoration(
                      color: Colors.black87,
                      border: Border.all(color: Colors.red, width: 4),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          _compositorService.fallbackMessage,
                          style: const TextStyle(
                              color: Colors.white,
                              fontSize: 20,
                              fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Please reconnect your USB capture device',
                          style: TextStyle(color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                ),
              if (_overlaySettings.enabled)
                CameraOverlayWidget(settings: _overlaySettings),
              if (_isChatOverlayVisible &&
                  _licenseService
                      .isFeatureAvailable(AppConstants.featureWaddleBotAi))
                const Positioned(
                  bottom: 16,
                  left: 16,
                  child: ChatOverlayWidget(),
                ),
            ],
          ),
        ),
        // USB status
        if (Platform.isAndroid || _isIpad())
          UsbStatusCard(
            statusText: _usbStatusText,
            statusColor: _usbStatusColor,
            onScanPressed: () => _usbService.scanForDevices(),
          ),
        // Stream controls
        StreamControls(
          isStreaming: _isStreaming,
          streamStatus: _streamStatusText,
          onStartStop: _isStreaming ? _stopStreaming : _startStreaming,
          onToggleOverlay: () {
            setState(() {
              _overlaySettings = _overlaySettings.copyWith(
                enabled: !_overlaySettings.enabled,
              );
            });
          },
          onToggleChat: _licenseService
                  .isFeatureAvailable(AppConstants.featureWaddleBotAi)
              ? () => setState(() => _isChatOverlayVisible = !_isChatOverlayVisible)
              : null,
        ),
      ],
    );
  }

  /// Settings screen for stream configuration
  Widget _buildSettingsScreen() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Settings',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.grey[900],
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.grey[800]!),
            ),
            child: Column(
              children: [
                const Icon(Icons.settings, size: 48, color: Color(0xFFD4AF37)),
                const SizedBox(height: 16),
                const Text(
                  'Stream configuration',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
                ),
                const SizedBox(height: 8),
                Text(
                  'Configure RTMP, resolution, and overlay settings',
                  style: TextStyle(color: Colors.grey[400]),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: _openSettings,
                  child: const Text('Open Settings'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  bool _isIpad() {
    // On iOS, check for tablet form factor
    if (!Platform.isIOS) return false;
    return MediaQuery.of(context).size.shortestSide >= 600;
  }
}

/// Mock user model for sidebar (would be replaced with real auth provider)
