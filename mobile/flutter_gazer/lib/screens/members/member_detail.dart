import 'package:flutter/material.dart';
import 'package:flutter_libs/flutter_libs.dart';
import 'package:intl/intl.dart';
import '../../services/member_service.dart';
import '../../services/waddlebot_auth_service.dart';
import '../../models/member.dart';
import '../../models/api_response.dart';

/// Member detail screen displaying comprehensive member profile information.
///
/// Features:
/// - Shows member info: avatar, display name, username, role badge
/// - Stats: reputation score, join date, last active time
/// - Badges list if available
/// - Permissions list with descriptions
/// - Online status indicator
/// - Elder theme styled profile cards with slate and gold colors
/// - Edit role button (admin only)
/// - Loading and error handling with proper state management
class MemberDetailScreen extends StatefulWidget {
  final String communityId;
  final String memberId;
  final bool isAdmin;

  const MemberDetailScreen({
    super.key,
    required this.communityId,
    required this.memberId,
    this.isAdmin = false,
  });

  @override
  State<MemberDetailScreen> createState() => _MemberDetailScreenState();
}

class _MemberDetailScreenState extends State<MemberDetailScreen> {
  late final MemberService _memberService;
  late final WaddleBotAuthService _authService;

  MemberDetail? _memberDetail;
  bool _isLoading = true;
  bool _hasError = false;
  String? _errorMessage;
  String? _selectedRole;

  static const Map<String, String> _roleValues = {
    'Owner': 'owner',
    'Admin': 'admin',
    'Maintainer': 'maintainer',
    'Member': 'member',
    'Viewer': 'viewer',
  };

  static const Map<String, String> _permissionDescriptions = {
    'read:community': 'View community details and information',
    'read:members': 'View member list and profiles',
    'read:content': 'View community content and posts',
    'read:analytics': 'View analytics and statistics',
    'write:community': 'Edit community settings',
    'write:members': 'Manage member information',
    'write:content': 'Create and edit content',
    'delete:members': 'Remove members from community',
    'manage:community': 'Full community management',
    'manage:roles': 'Change member roles and permissions',
    'view:audit_log': 'View audit logs and activity',
    'delete:content': 'Delete content and posts',
    'delete:community': 'Delete community',
    'transfer:ownership': 'Transfer ownership to another member',
  };

  @override
  void initState() {
    super.initState();
    _memberService = MemberService.getInstance();
    _authService = WaddleBotAuthService();
    _loadMemberDetail();
  }

  /// Load member detail from API
  Future<void> _loadMemberDetail() async {
    if (!mounted) return;

    setState(() {
      _isLoading = true;
      _hasError = false;
      _errorMessage = null;
    });

    try {
      final response = await _memberService.getMemberDetail(
        widget.communityId,
        widget.memberId,
      );

      if (!mounted) return;

      if (response.success && response.data != null) {
        setState(() {
          _memberDetail = response.data;
          _selectedRole = _memberDetail!.role.toString().split('.').last;
          _isLoading = false;
        });
      } else {
        setState(() {
          _isLoading = false;
          _hasError = true;
          _errorMessage = response.message ?? 'Failed to load member details';
        });
      }
    } on ApiError catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _hasError = true;
        _errorMessage = e.message ?? 'Failed to load member details';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _hasError = true;
        _errorMessage = 'An unexpected error occurred';
      });
    }
  }

  /// Update member role
  Future<void> _updateMemberRole(String newRole) async {
    if (!widget.isAdmin || _memberDetail == null) return;

    if (!mounted) return;

    setState(() {
      _isLoading = true;
    });

    try {
      final response = await _memberService.updateMemberRole(
        widget.communityId,
        widget.memberId,
        newRole,
      );

      if (!mounted) return;

      if (response.success) {
        // Reload member detail
        await _loadMemberDetail();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Member role updated successfully'),
              backgroundColor: ElderColors.green500,
            ),
          );
        }
      } else {
        setState(() {
          _isLoading = false;
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(response.message ?? 'Failed to update role'),
              backgroundColor: ElderColors.red500,
            ),
          );
        }
      }
    } on ApiError catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.message ?? 'Failed to update role'),
          backgroundColor: ElderColors.red500,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('An unexpected error occurred'),
          backgroundColor: ElderColors.red500,
        ),
      );
    }
  }

  /// Show role selection dialog
  void _showRoleSelectionDialog() {
    if (!widget.isAdmin || _memberDetail == null) return;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: ElderColors.slate800,
        title: const Text(
          'Change Member Role',
          style: TextStyle(color: ElderColors.amber500),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: _roleValues.entries.map((entry) {
            return RadioListTile<String>(
              title: Text(
                entry.key,
                style: const TextStyle(color: ElderColors.slate100),
              ),
              subtitle: Text(
                _getRoleDescription(entry.key),
                style: const TextStyle(
                  color: ElderColors.slate400,
                  fontSize: 12,
                ),
              ),
              value: entry.value,
              groupValue: _selectedRole,
              activeColor: ElderColors.amber500,
              onChanged: (value) {
                Navigator.pop(context);
                if (value != null) {
                  _updateMemberRole(value);
                }
              },
            );
          }).toList(),
        ),
      ),
    );
  }

  /// Get role description
  String _getRoleDescription(String role) {
    switch (role) {
      case 'Owner':
        return 'Full access and community ownership';
      case 'Admin':
        return 'Administrative privileges and management';
      case 'Maintainer':
        return 'Content management and moderation';
      case 'Member':
        return 'Standard member with content creation';
      case 'Viewer':
        return 'Read-only access to community';
      default:
        return '';
    }
  }

  /// Get role color for badge
  Color _getRoleColor(MemberRole role) {
    switch (role) {
      case MemberRole.owner:
        return ElderColors.red500;
      case MemberRole.admin:
        return Colors.orange;
      case MemberRole.maintainer:
        return ElderColors.amber500;
      case MemberRole.member:
        return Colors.blue;
      case MemberRole.viewer:
        return ElderColors.slate600;
    }
  }

  /// Format date for display
  String _formatDate(DateTime date) {
    return DateFormat('MMM d, yyyy').format(date);
  }

  /// Format relative time
  String _getRelativeTime(DateTime date) {
    final now = DateTime.now();
    final diff = now.difference(date);

    if (diff.inMinutes < 1) {
      return 'Now';
    } else if (diff.inMinutes < 60) {
      return '${diff.inMinutes}m ago';
    } else if (diff.inHours < 24) {
      return '${diff.inHours}h ago';
    } else if (diff.inDays < 30) {
      return '${diff.inDays}d ago';
    } else if (diff.inDays < 365) {
      return '${(diff.inDays / 30).floor()}mo ago';
    } else {
      return '${(diff.inDays / 365).floor()}y ago';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ElderColors.slate950,
      appBar: AppBar(
        title: const Text(
          'Member Profile',
          style: TextStyle(
            color: ElderColors.amber500,
            fontWeight: FontWeight.bold,
          ),
        ),
        backgroundColor: ElderColors.slate800,
        elevation: 0,
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: ElderColors.amber500),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: _buildContent(),
    );
  }

  /// Build main content
  Widget _buildContent() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation<Color>(ElderColors.amber500),
        ),
      );
    }

    if (_hasError) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline,
              size: 64,
              color: ElderColors.slate500,
            ),
            const SizedBox(height: 16),
            Text(
              _errorMessage ?? 'Failed to load member details',
              style: const TextStyle(
                color: ElderColors.slate300,
                fontSize: 16,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadMemberDetail,
              style: ElevatedButton.styleFrom(
                backgroundColor: ElderColors.amber500,
                padding: const EdgeInsets.symmetric(
                  horizontal: 32,
                  vertical: 12,
                ),
              ),
              child: const Text(
                'Retry',
                style: TextStyle(
                  color: ElderColors.slate950,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
      );
    }

    if (_memberDetail == null) {
      return const Center(
        child: Text(
          'Member not found',
          style: TextStyle(color: ElderColors.slate300),
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header card with avatar and basic info
          _buildHeaderCard(),
          const SizedBox(height: 20),
          // Stats cards
          _buildStatsCards(),
          const SizedBox(height: 20),
          // Badges section
          if (_memberDetail!.badges.isNotEmpty) ...[
            _buildBadgesSection(),
            const SizedBox(height: 20),
          ],
          // Permissions section
          _buildPermissionsSection(),
          const SizedBox(height: 20),
          // Edit role button (admin only)
          if (widget.isAdmin) _buildEditRoleButton(),
        ],
      ),
    );
  }

  /// Build header card with avatar and basic info
  Widget _buildHeaderCard() {
    final initials = (_memberDetail!.displayName.isNotEmpty
            ? _memberDetail!.displayName[0]
            : _memberDetail!.username[0])
        .toUpperCase();

    return Card(
      color: ElderColors.slate800,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            // Avatar with status
            Stack(
              children: [
                Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(
                    color: ElderColors.amber600,
                    shape: BoxShape.circle,
                    image: _memberDetail!.avatarUrl != null
                        ? DecorationImage(
                            image: NetworkImage(_memberDetail!.avatarUrl!),
                            fit: BoxFit.cover,
                          )
                        : null,
                  ),
                  child: _memberDetail!.avatarUrl == null
                      ? Center(
                          child: Text(
                            initials,
                            style: const TextStyle(
                              color: ElderColors.slate950,
                              fontWeight: FontWeight.bold,
                              fontSize: 40,
                            ),
                          ),
                        )
                      : null,
                ),
                // Online status
                Positioned(
                  bottom: 0,
                  right: 0,
                  child: Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: _memberDetail!.isOnline == true
                          ? ElderColors.green500
                          : ElderColors.slate600,
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: ElderColors.slate800,
                        width: 3,
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            // Display name
            Text(
              _memberDetail!.displayName,
              style: const TextStyle(
                color: ElderColors.slate100,
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 4),
            // Username
            Text(
              '@${_memberDetail!.username}',
              style: const TextStyle(
                color: ElderColors.slate400,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 12),
            // Role badge
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: _getRoleColor(_memberDetail!.role),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                _memberDetail!.getRoleDisplayName(),
                style: const TextStyle(
                  color: ElderColors.slate950,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ),
            const SizedBox(height: 12),
            // Status text
            Text(
              _memberDetail!.getStatus(),
              style: TextStyle(
                color: _memberDetail!.isOnline == true
                    ? ElderColors.green500
                    : ElderColors.slate400,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build stats cards
  Widget _buildStatsCards() {
    return Row(
      children: [
        Expanded(
          child: _buildStatCard(
            icon: Icons.star,
            label: 'Reputation',
            value: '${_memberDetail!.reputationScore}',
            color: ElderColors.amber500,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildStatCard(
            icon: Icons.calendar_today,
            label: 'Joined',
            value: _formatDate(_memberDetail!.joinedAt),
            color: Colors.blue,
          ),
        ),
      ],
    );
  }

  /// Build individual stat card
  Widget _buildStatCard({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Card(
      color: ElderColors.slate800,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 8),
            Text(
              label,
              style: const TextStyle(
                color: ElderColors.slate400,
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              value,
              style: const TextStyle(
                color: ElderColors.slate100,
                fontSize: 14,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  /// Build badges section
  Widget _buildBadgesSection() {
    return Card(
      color: ElderColors.slate800,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Badges',
              style: TextStyle(
                color: ElderColors.amber500,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _memberDetail!.badges.map((badge) {
                return Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: ElderColors.slate700,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: ElderColors.amber400),
                  ),
                  child: Text(
                    badge,
                    style: const TextStyle(
                      color: ElderColors.amber400,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  /// Build permissions section
  Widget _buildPermissionsSection() {
    return Card(
      color: ElderColors.slate800,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Permissions',
              style: TextStyle(
                color: ElderColors.amber500,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            ..._memberDetail!.permissions.map((permission) {
              final description = _permissionDescriptions[permission] ??
                  permission.replaceAll('_', ' ');
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Padding(
                      padding: EdgeInsets.only(top: 4),
                      child: Icon(
                        Icons.check_circle,
                        color: ElderColors.green500,
                        size: 18,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            permission,
                            style: const TextStyle(
                              color: ElderColors.slate100,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            description,
                            style: const TextStyle(
                              color: ElderColors.slate400,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ],
        ),
      ),
    );
  }

  /// Build edit role button
  Widget _buildEditRoleButton() {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: _showRoleSelectionDialog,
        icon: const Icon(Icons.edit),
        label: const Text('Edit Member Role'),
        style: ElevatedButton.styleFrom(
          backgroundColor: ElderColors.amber500,
          foregroundColor: ElderColors.slate950,
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
    );
  }
}
