import 'package:flutter/material.dart';
import 'package:flutter_libs/flutter_libs.dart';
import '../../services/community_service.dart';
import '../../models/community.dart';
import '../../models/api_response.dart';

/// Community detail screen showing comprehensive community information and activity.
///
/// Features:
/// - Fetches and displays community details using CommunityService
/// - Shows community info, stats, and recent activity
/// - Tabbed navigation: Overview, Members, Activity
/// - Elder theme styled cards with slate backgrounds and gold accents
/// - Loading and error states with proper handling
/// - Edit button visible to admin users (admin-only functionality)
/// - Uses FutureBuilder for async data loading
class CommunityDetailScreen extends StatefulWidget {
  final String communityId;
  final bool isAdmin;

  const CommunityDetailScreen({
    super.key,
    required this.communityId,
    this.isAdmin = false,
  });

  @override
  State<CommunityDetailScreen> createState() => _CommunityDetailScreenState();
}

class _CommunityDetailScreenState extends State<CommunityDetailScreen>
    with SingleTickerProviderStateMixin {
  late final CommunityService _communityService;
  late final TabController _tabController;

  @override
  void initState() {
    super.initState();
    _communityService = CommunityService.getInstance();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  /// Navigate to edit community screen
  void _navigateToEditCommunity(CommunityDetail community) {
    Navigator.of(context).pushNamed(
      '/edit-community',
      arguments: community,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Community Details'),
        backgroundColor: ElderColors.slate800,
        elevation: 0,
        actions: widget.isAdmin
            ? [
                IconButton(
                  icon: const Icon(Icons.edit),
                  onPressed: () {
                    // This will be called with community data from FutureBuilder
                  },
                  tooltip: 'Edit Community',
                ),
              ]
            : null,
      ),
      backgroundColor: ElderColors.slate950,
      body: FutureBuilder<ApiResponse<CommunityDetail>>(
        future: _communityService.getCommunityDetail(widget.communityId),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return _buildLoadingState();
          }

          if (snapshot.hasError || !snapshot.data!.success) {
            return _buildErrorState(
              snapshot.data?.message ?? 'Failed to load community details',
            );
          }

          final community = snapshot.data!.data;
          if (community == null) {
            return _buildErrorState('Community not found');
          }

          // Update AppBar action with community data
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted && widget.isAdmin) {
              // Action already defined in AppBar
            }
          });

          return _buildDetailContent(community);
        },
      ),
    );
  }

  /// Build loading state
  Widget _buildLoadingState() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation<Color>(ElderColors.amber500),
          ),
          SizedBox(height: 16),
          Text(
            'Loading community details...',
            style: TextStyle(
              color: ElderColors.slate400,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }

  /// Build error state
  Widget _buildErrorState(String message) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.error_outline,
            color: ElderColors.red500,
            size: 48,
          ),
          const SizedBox(height: 16),
          Text(
            message,
            style: const TextStyle(
              color: ElderColors.slate200,
              fontSize: 16,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.arrow_back),
            label: const Text('Go Back'),
            style: ElevatedButton.styleFrom(
              backgroundColor: ElderColors.amber500,
              foregroundColor: ElderColors.slate950,
            ),
          ),
        ],
      ),
    );
  }

  /// Build detailed content with tabs
  Widget _buildDetailContent(CommunityDetail community) {
    return Column(
      children: [
        // Header with community info
        _buildCommunityHeader(community),
        // Tab bar
        TabBar(
          controller: _tabController,
          labelColor: ElderColors.amber500,
          unselectedLabelColor: ElderColors.slate500,
          indicatorColor: ElderColors.amber500,
          indicatorSize: TabBarIndicatorSize.tab,
          tabs: const [
            Tab(text: 'Overview'),
            Tab(text: 'Members'),
            Tab(text: 'Activity'),
          ],
        ),
        // Tab content
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildOverviewTab(community),
              _buildMembersTab(community),
              _buildActivityTab(community),
            ],
          ),
        ),
      ],
    );
  }

  /// Build community header with avatar and basic info
  Widget _buildCommunityHeader(CommunityDetail community) {
    return Container(
      color: ElderColors.slate800,
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // Avatar
          _buildLargeAvatar(community),
          const SizedBox(height: 16),
          // Community name
          Text(
            community.name,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: ElderColors.amber500,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          // Community description
          Text(
            community.description,
            style: const TextStyle(
              fontSize: 14,
              color: ElderColors.slate400,
            ),
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 16),
          // Quick stats
          _buildQuickStats(community),
        ],
      ),
    );
  }

  /// Build large avatar for header
  Widget _buildLargeAvatar(CommunityDetail community) {
    if (community.avatarUrl != null && community.avatarUrl!.isNotEmpty) {
      return Container(
        width: 80,
        height: 80,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: ElderColors.amber500,
            width: 3,
          ),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(9),
          child: Image.network(
            community.avatarUrl!,
            fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) {
              return _buildLargeAvatarPlaceholder(community);
            },
          ),
        ),
      );
    }

    return _buildLargeAvatarPlaceholder(community);
  }

  /// Build large avatar placeholder
  Widget _buildLargeAvatarPlaceholder(CommunityDetail community) {
    return Container(
      width: 80,
      height: 80,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: ElderColors.slate700,
        border: Border.all(
          color: ElderColors.amber500,
          width: 3,
        ),
      ),
      child: Center(
        child: Text(
          community.name.isNotEmpty ? community.name[0].toUpperCase() : '?',
          style: const TextStyle(
            fontSize: 36,
            fontWeight: FontWeight.bold,
            color: ElderColors.amber500,
          ),
        ),
      ),
    );
  }

  /// Build quick stats row
  Widget _buildQuickStats(CommunityDetail community) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        _buildStatItem(
          icon: Icons.people,
          label: 'Members',
          value: community.stats.memberCount.toString(),
        ),
        _buildStatItem(
          icon: Icons.check_circle,
          label: 'Active',
          value: community.stats.activeMembers.toString(),
        ),
        _buildStatItem(
          icon: Icons.message,
          label: 'Messages',
          value: community.stats.messagesToday.toString(),
        ),
        _buildStatItem(
          icon: Icons.terminal,
          label: 'Commands',
          value: community.stats.commandsToday.toString(),
        ),
      ],
    );
  }

  /// Build individual stat item
  Widget _buildStatItem({
    required IconData icon,
    required String label,
    required String value,
  }) {
    return Column(
      children: [
        Icon(
          icon,
          color: ElderColors.amber500,
          size: 20,
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            color: ElderColors.amber500,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: const TextStyle(
            fontSize: 11,
            color: ElderColors.slate500,
          ),
        ),
      ],
    );
  }

  /// Build Overview tab content
  Widget _buildOverviewTab(CommunityDetail community) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Description card
          _buildInfoCard(
            title: 'Description',
            content: community.description,
            icon: Icons.description,
          ),
          const SizedBox(height: 12),
          // Created date card
          _buildInfoCard(
            title: 'Created',
            content: _formatDate(community.createdAt),
            icon: Icons.calendar_today,
          ),
          const SizedBox(height: 12),
          // Updated date card
          _buildInfoCard(
            title: 'Last Updated',
            content: _formatDate(community.updatedAt),
            icon: Icons.update,
          ),
          const SizedBox(height: 12),
          // Stats summary
          _buildStatsSummary(community),
        ],
      ),
    );
  }

  /// Build Members tab content
  Widget _buildMembersTab(CommunityDetail community) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Member Overview',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: ElderColors.amber500,
                ),
          ),
          const SizedBox(height: 16),
          // Member stats cards
          _buildMemberStatCard(
            label: 'Total Members',
            value: community.stats.memberCount,
            icon: Icons.people,
          ),
          const SizedBox(height: 12),
          _buildMemberStatCard(
            label: 'Active Members',
            value: community.stats.activeMembers,
            icon: Icons.check_circle,
          ),
          const SizedBox(height: 16),
          Card(
            color: ElderColors.slate800,
            elevation: 2,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: const BorderSide(
                color: ElderColors.slate700,
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Activity Status',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: ElderColors.slate300,
                        ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Member Engagement',
                            style: TextStyle(
                              fontSize: 12,
                              color: ElderColors.slate500,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${((community.stats.activeMembers / (community.stats.memberCount > 0 ? community.stats.memberCount : 1)) * 100).toStringAsFixed(1)}%',
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: ElderColors.amber500,
                            ),
                          ),
                        ],
                      ),
                      LinearProgressIndicator(
                        value: community.stats.activeMembers /
                            (community.stats.memberCount > 0
                                ? community.stats.memberCount
                                : 1),
                        minHeight: 8,
                        backgroundColor: ElderColors.slate700,
                        valueColor: const AlwaysStoppedAnimation<Color>(
                          ElderColors.green500,
                        ),
                      ).expand(),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Center(
            child: Text(
              'Tap members icon to view full member list',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: ElderColors.slate500,
                  ),
            ),
          ),
        ],
      ),
    );
  }

  /// Build Activity tab content
  Widget _buildActivityTab(CommunityDetail community) {
    if (community.recentActivity.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.history,
              color: ElderColors.slate600,
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              'No recent activity',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: ElderColors.slate400,
                  ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: community.recentActivity.length,
      itemBuilder: (context, index) {
        final activity = community.recentActivity[index];
        return _buildActivityItem(activity);
      },
    );
  }

  /// Build individual activity item
  Widget _buildActivityItem(ActivityItem activity) {
    return Card(
      color: ElderColors.slate800,
      elevation: 1,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: const BorderSide(
          color: ElderColors.slate700,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Activity icon
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: ElderColors.slate700,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                _getActivityIcon(activity.type),
                color: ElderColors.amber500,
                size: 20,
              ),
            ),
            const SizedBox(width: 12),
            // Activity details
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    activity.userName,
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: ElderColors.amber500,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    activity.description,
                    style: const TextStyle(
                      fontSize: 12,
                      color: ElderColors.slate300,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            // Timestamp
            Text(
              _formatTime(activity.timestamp),
              style: const TextStyle(
                fontSize: 11,
                color: ElderColors.slate500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Get icon for activity type
  IconData _getActivityIcon(ActivityType type) {
    switch (type) {
      case ActivityType.memberJoined:
        return Icons.person_add;
      case ActivityType.memberLeft:
        return Icons.person_remove;
      case ActivityType.messagePosted:
        return Icons.message;
      case ActivityType.commandExecuted:
        return Icons.terminal;
      case ActivityType.workflowTriggered:
        return Icons.workflow;
    }
  }

  /// Build info card for Overview tab
  Widget _buildInfoCard({
    required String title,
    required String content,
    required IconData icon,
  }) {
    return Card(
      color: ElderColors.slate800,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(
          color: ElderColors.slate700,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: ElderColors.slate700,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                icon,
                color: ElderColors.amber500,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 12,
                      color: ElderColors.slate500,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    content,
                    style: const TextStyle(
                      fontSize: 14,
                      color: ElderColors.slate200,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build stats summary card
  Widget _buildStatsSummary(CommunityDetail community) {
    return Card(
      color: ElderColors.slate800,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(
          color: ElderColors.slate700,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Today\'s Activity',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: ElderColors.amber500,
                  ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildTodayStatColumn(
                  label: 'Messages',
                  value: community.stats.messagesToday,
                  icon: Icons.message,
                ),
                _buildTodayStatColumn(
                  label: 'Commands',
                  value: community.stats.commandsToday,
                  icon: Icons.terminal,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// Build today stat column
  Widget _buildTodayStatColumn({
    required String label,
    required int value,
    required IconData icon,
  }) {
    return Column(
      children: [
        Icon(
          icon,
          color: ElderColors.amber500,
          size: 24,
        ),
        const SizedBox(height: 8),
        Text(
          value.toString(),
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: ElderColors.amber500,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            color: ElderColors.slate500,
          ),
        ),
      ],
    );
  }

  /// Build member stat card
  Widget _buildMemberStatCard({
    required String label,
    required int value,
    required IconData icon,
  }) {
    return Card(
      color: ElderColors.slate800,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(
          color: ElderColors.slate700,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: ElderColors.slate700,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                icon,
                color: ElderColors.amber500,
                size: 24,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: const TextStyle(
                      fontSize: 12,
                      color: ElderColors.slate500,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    value.toString(),
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: ElderColors.amber500,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Format date to readable string
  String _formatDate(DateTime dateTime) {
    return '${dateTime.month}/${dateTime.day}/${dateTime.year}';
  }

  /// Format time to relative string
  String _formatTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inMinutes < 1) {
      return 'just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      return _formatDate(dateTime);
    }
  }
}
