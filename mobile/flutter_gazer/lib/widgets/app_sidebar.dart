import 'package:flutter/material.dart';
import '../models/auth.dart';
import '../services/license_service.dart';

/// AppSidebar widget implementing SidebarMenu from penguin-libs
/// with role-based menu filtering and Elder theme styling
class AppSidebar extends StatefulWidget {
  final User currentUser;
  final VoidCallback onNavigate;
  final String selectedRoute;
  final Function(String)? onRouteSelected;

  const AppSidebar({
    super.key,
    required this.currentUser,
    required this.onNavigate,
    required this.selectedRoute,
    this.onRouteSelected,
  });

  @override
  State<AppSidebar> createState() => _AppSidebarState();
}

class _AppSidebarState extends State<AppSidebar> {
  late LicenseService _licenseService;
  bool _hasPremiumFeatures = false;

  @override
  void initState() {
    super.initState();
    _licenseService = LicenseService();
    _initializeLicenseStatus();
  }

  Future<void> _initializeLicenseStatus() async {
    final hasPremium =
        await _licenseService.checkFeatureEntitlement('streaming');
    setState(() {
      _hasPremiumFeatures = hasPremium;
    });
  }

  List<SidebarMenuItem> _buildMenuItems() {
    final items = <SidebarMenuItem>[
      // Communities
      SidebarMenuItem(
        id: 'communities',
        label: 'Communities',
        icon: Icons.group,
        route: '/communities',
        badge: null,
        isActive: widget.selectedRoute == '/communities',
        onTap: () => _handleNavigation('/communities'),
      ),

      // Chat
      SidebarMenuItem(
        id: 'chat',
        label: 'Chat',
        icon: Icons.chat_bubble,
        route: '/chat',
        badge: null,
        isActive: widget.selectedRoute == '/chat',
        onTap: () => _handleNavigation('/chat'),
      ),

      // Members
      SidebarMenuItem(
        id: 'members',
        label: 'Members',
        icon: Icons.people,
        route: '/members',
        badge: null,
        isActive: widget.selectedRoute == '/members',
        onTap: () => _handleNavigation('/members'),
      ),
    ];

    // Conditionally add Streaming (premium feature)
    if (_hasPremiumFeatures) {
      items.add(
        SidebarMenuItem(
          id: 'streaming',
          label: 'Streaming',
          icon: Icons.videocam,
          route: '/streaming',
          badge: SidebarMenuBadge(
            label: 'Premium',
            backgroundColor: const Color(0xFFD4AF37), // Gold
            textColor: Colors.black,
          ),
          isActive: widget.selectedRoute == '/streaming',
          onTap: () => _handleNavigation('/streaming'),
        ),
      );
    }

    // Settings
    items.add(
      SidebarMenuItem(
        id: 'settings',
        label: 'Settings',
        icon: Icons.settings,
        route: '/settings',
        badge: null,
        isActive: widget.selectedRoute == '/settings',
        onTap: () => _handleNavigation('/settings'),
      ),
    );

    return items;
  }

  void _handleNavigation(String route) {
    widget.onNavigate();
    // Navigate based on role-based permissions
    if (_canAccessRoute(route)) {
      // Use custom route callback if provided, otherwise fall back to named routes
      if (widget.onRouteSelected != null) {
        widget.onRouteSelected!(route);
      } else {
        Navigator.of(context).pushNamed(route);
      }
    } else {
      _showAccessDenied(route);
    }
  }

  bool _canAccessRoute(String route) {
    // Role-based access control
    switch (route) {
      case '/streaming':
        return _hasPremiumFeatures &&
            (widget.currentUser.role == 'admin' ||
                widget.currentUser.role == 'moderator');
      case '/settings':
        return widget.currentUser.role == 'admin';
      case '/communities':
      case '/chat':
      case '/members':
        return true; // Available to all authenticated users
      default:
        return false;
    }
  }

  void _showAccessDenied(String route) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Access denied to $route'),
        backgroundColor: Colors.red.shade700,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SidebarMenu(
      items: _buildMenuItems(),
      theme: _buildSidebarTheme(),
      onItemSelected: (menuItem) {
        _handleNavigation(menuItem.route);
      },
      header: _buildSidebarHeader(),
      footer: _buildSidebarFooter(),
    );
  }

  Widget _buildSidebarHeader() {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 24,
            backgroundImage: widget.currentUser.avatarUrl != null
                ? NetworkImage(widget.currentUser.avatarUrl!)
                : null,
            child: widget.currentUser.avatarUrl == null
                ? Text(
                    widget.currentUser.username.substring(0, 1).toUpperCase(),
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  )
                : null,
          ),
          const SizedBox(height: 12),
          Text(
            widget.currentUser.username,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Color(0xFFD4AF37), // Elder gold
            ),
          ),
          const SizedBox(height: 4),
          Text(
            widget.currentUser.role.toUpperCase(),
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey[400],
              letterSpacing: 0.5,
            ),
          ),
          if (_hasPremiumFeatures)
            Padding(
              padding: const EdgeInsets.only(top: 8.0),
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 8,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFFD4AF37).withOpacity(0.2),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: const Color(0xFFD4AF37),
                    width: 0.5,
                  ),
                ),
                child: const Text(
                  'Premium',
                  style: TextStyle(
                    fontSize: 10,
                    color: Color(0xFFD4AF37),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSidebarFooter() {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          Divider(
            color: Colors.grey[700],
            height: 24,
          ),
          GestureDetector(
            onTap: () => _handleLogout(),
            child: Row(
              children: [
                const Icon(
                  Icons.logout,
                  size: 20,
                  color: Colors.grey,
                ),
                const SizedBox(width: 12),
                Text(
                  'Logout',
                  style: TextStyle(
                    color: Colors.grey[400],
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _handleLogout() {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          backgroundColor: const Color(0xFF1a1a1a),
          title: const Text(
            'Logout',
            style: TextStyle(color: Color(0xFFD4AF37)),
          ),
          content: const Text(
            'Are you sure you want to logout?',
            style: TextStyle(color: Colors.white70),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text(
                'Cancel',
                style: TextStyle(color: Colors.grey),
              ),
            ),
            TextButton(
              onPressed: () {
                Navigator.pop(context);
                Navigator.of(context).pushNamedAndRemoveUntil(
                  '/login',
                  (route) => false,
                );
              },
              child: const Text(
                'Logout',
                style: TextStyle(color: Color(0xFFD4AF37)),
              ),
            ),
          ],
        );
      },
    );
  }

  SidebarMenuTheme _buildSidebarTheme() {
    return SidebarMenuTheme(
      backgroundColor: const Color(0xFF121212),
      selectedItemColor: const Color(0xFFD4AF37),
      selectedItemBackground: Colors.grey[900]!,
      itemTextColor: Colors.grey[400]!,
      itemIconColor: Colors.grey[600]!,
      dividerColor: Colors.grey[800]!,
      borderRadius: 8.0,
      itemPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      selectedItemBorder: const Border(
        left: BorderSide(
          color: Color(0xFFD4AF37),
          width: 3,
        ),
      ),
    );
  }
}

/// SidebarMenuItem model for type-safe menu item creation
class SidebarMenuItem {
  final String id;
  final String label;
  final IconData icon;
  final String route;
  final SidebarMenuBadge? badge;
  final bool isActive;
  final VoidCallback? onTap;

  SidebarMenuItem({
    required this.id,
    required this.label,
    required this.icon,
    required this.route,
    this.badge,
    this.isActive = false,
    this.onTap,
  });
}

/// Badge model for menu items (e.g., "Premium" indicator)
class SidebarMenuBadge {
  final String label;
  final Color backgroundColor;
  final Color textColor;

  SidebarMenuBadge({
    required this.label,
    required this.backgroundColor,
    required this.textColor,
  });
}

/// SidebarMenuTheme for Elder theme styling
class SidebarMenuTheme {
  final Color backgroundColor;
  final Color selectedItemColor;
  final Color? selectedItemBackground;
  final Color itemTextColor;
  final Color itemIconColor;
  final Color dividerColor;
  final double borderRadius;
  final EdgeInsets itemPadding;
  final Border? selectedItemBorder;

  SidebarMenuTheme({
    required this.backgroundColor,
    required this.selectedItemColor,
    this.selectedItemBackground,
    required this.itemTextColor,
    required this.itemIconColor,
    required this.dividerColor,
    required this.borderRadius,
    required this.itemPadding,
    this.selectedItemBorder,
  });
}

/// Main SidebarMenu widget orchestrating all components
class SidebarMenu extends StatelessWidget {
  final List<SidebarMenuItem> items;
  final SidebarMenuTheme theme;
  final Function(SidebarMenuItem)? onItemSelected;
  final Widget? header;
  final Widget? footer;

  const SidebarMenu({
    super.key,
    required this.items,
    required this.theme,
    this.onItemSelected,
    this.header,
    this.footer,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      color: theme.backgroundColor,
      child: Column(
        children: [
          if (header != null) ...[
            header!,
            Divider(color: theme.dividerColor, height: 1),
          ],
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: items.length,
              itemBuilder: (context, index) {
                final item = items[index];
                return _buildMenuItem(context, item);
              },
            ),
          ),
          if (footer != null) ...[
            Divider(color: theme.dividerColor, height: 1),
            footer!,
          ],
        ],
      ),
    );
  }

  Widget _buildMenuItem(BuildContext context, SidebarMenuItem item) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () {
            item.onTap?.call();
            onItemSelected?.call(item);
          },
          borderRadius: BorderRadius.circular(theme.borderRadius),
          child: Container(
            padding: theme.itemPadding,
            decoration: BoxDecoration(
              color: item.isActive ? theme.selectedItemBackground : null,
              border: item.isActive ? theme.selectedItemBorder : null,
              borderRadius: BorderRadius.circular(theme.borderRadius),
            ),
            child: Row(
              children: [
                Icon(
                  item.icon,
                  size: 24,
                  color: item.isActive
                      ? theme.selectedItemColor
                      : theme.itemIconColor,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    item.label,
                    style: TextStyle(
                      fontSize: 14,
                      color: item.isActive
                          ? theme.selectedItemColor
                          : theme.itemTextColor,
                      fontWeight:
                          item.isActive ? FontWeight.w600 : FontWeight.normal,
                    ),
                  ),
                ),
                if (item.badge != null) ...[
                  const SizedBox(width: 8),
                  _buildBadge(item.badge!),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildBadge(SidebarMenuBadge badge) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: badge.backgroundColor,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        badge.label,
        style: TextStyle(
          fontSize: 10,
          color: badge.textColor,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
