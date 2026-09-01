import 'package:flutter/material.dart';
import 'package:flutter_libs/flutter_libs.dart';
import '../../services/community_service.dart';
import '../../models/community.dart';
import '../../models/api_response.dart';

/// Community list screen displaying all communities with search, filter, and create functionality.
///
/// Features:
/// - ListView of community cards with name, avatar, member count
/// - Pull-to-refresh functionality
/// - Search/filter bar for community discovery
/// - FloatingActionButton to create new community (admin only)
/// - Tap to navigate to community detail
/// - Elder theme styling with slate backgrounds and gold accents
/// - Loading and error states with proper handling
class CommunityListScreen extends StatefulWidget {
  final bool isAdmin;

  const CommunityListScreen({
    super.key,
    this.isAdmin = false,
  });

  @override
  State<CommunityListScreen> createState() => _CommunityListScreenState();
}

class _CommunityListScreenState extends State<CommunityListScreen> {
  late final CommunityService _communityService;
  late final TextEditingController _searchController;
  List<Community> _communities = [];
  List<Community> _filteredCommunities = [];
  bool _isLoading = false;
  bool _hasError = false;
  String? _errorMessage;
  int _currentPage = 1;
  bool _hasMorePages = false;

  @override
  void initState() {
    super.initState();
    _communityService = CommunityService.getInstance();
    _searchController = TextEditingController();
    _searchController.addListener(_filterCommunities);
    _loadCommunities();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  /// Load communities from API
  Future<void> _loadCommunities({bool refresh = false}) async {
    if (refresh) {
      _currentPage = 1;
      _communities = [];
    }

    if (!mounted) return;
    setState(() {
      _isLoading = true;
      _hasError = false;
      _errorMessage = null;
    });

    try {
      final response = await _communityService.getCommunities(
        page: _currentPage,
        pageSize: 20,
      );

      if (!mounted) return;

      setState(() {
        if (refresh) {
          _communities = response.items;
        } else {
          _communities.addAll(response.items);
        }
        _hasMorePages = response.hasMore;
        _isLoading = false;
      });

      _filterCommunities();
    } on ApiError catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _hasError = true;
        _errorMessage = e.message;
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

  /// Filter communities based on search input
  void _filterCommunities() {
    final query = _searchController.text.toLowerCase().trim();

    if (query.isEmpty) {
      if (!mounted) return;
      setState(() {
        _filteredCommunities = List.from(_communities);
      });
    } else {
      if (!mounted) return;
      setState(() {
        _filteredCommunities = _communities
            .where((community) =>
                community.name.toLowerCase().contains(query) ||
                community.description.toLowerCase().contains(query))
            .toList();
      });
    }
  }

  /// Load more communities for pagination
  Future<void> _loadMore() async {
    if (_hasMorePages && !_isLoading) {
      _currentPage++;
      await _loadCommunities();
    }
  }

  /// Navigate to community detail screen
  void _navigateToCommunityDetail(Community community) {
    Navigator.of(context).pushNamed(
      '/community-detail',
      arguments: community.id,
    );
  }

  /// Navigate to create community screen
  void _navigateToCreateCommunity() {
    Navigator.of(context).pushNamed('/create-community').then((_) {
      // Refresh the list after creating a community
      _loadCommunities(refresh: true);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Communities'),
        backgroundColor: ElderColors.slate800,
        elevation: 0,
      ),
      backgroundColor: ElderColors.slate950,
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search communities...',
                hintStyle: const TextStyle(color: ElderColors.slate500),
                prefixIcon: const Icon(
                  Icons.search,
                  color: ElderColors.amber500,
                ),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          _filterCommunities();
                        },
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(
                    color: ElderColors.slate700,
                  ),
                ),
                filled: true,
                fillColor: ElderColors.slate800,
              ),
              style: const TextStyle(color: ElderColors.slate100),
            ),
          ),
          // Content
          Expanded(
            child: _buildContent(),
          ),
        ],
      ),
      floatingActionButton: widget.isAdmin
          ? FloatingActionButton(
              onPressed: _navigateToCreateCommunity,
              backgroundColor: ElderColors.amber500,
              foregroundColor: ElderColors.slate950,
              tooltip: 'Create Community',
              child: const Icon(Icons.add),
            )
          : null,
    );
  }

  /// Build main content based on state
  Widget _buildContent() {
    if (_hasError) {
      return _buildErrorState();
    }

    if (_isLoading && _communities.isEmpty) {
      return _buildLoadingState();
    }

    if (_filteredCommunities.isEmpty) {
      return _buildEmptyState();
    }

    return _buildCommunityList();
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
            'Loading communities...',
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
  Widget _buildErrorState() {
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
            _errorMessage ?? 'Failed to load communities',
            style: const TextStyle(
              color: ElderColors.slate200,
              fontSize: 16,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: () => _loadCommunities(refresh: true),
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
            style: ElevatedButton.styleFrom(
              backgroundColor: ElderColors.amber500,
              foregroundColor: ElderColors.slate950,
            ),
          ),
        ],
      ),
    );
  }

  /// Build empty state
  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            _searchController.text.isEmpty ? Icons.groups_2 : Icons.search_off,
            color: ElderColors.slate600,
            size: 48,
          ),
          const SizedBox(height: 16),
          Text(
            _searchController.text.isEmpty
                ? 'No communities yet'
                : 'No communities found',
            style: const TextStyle(
              color: ElderColors.slate400,
              fontSize: 16,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _searchController.text.isEmpty
                ? 'Create or join communities to get started'
                : 'Try adjusting your search',
            style: const TextStyle(
              color: ElderColors.slate500,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }

  /// Build community list with pagination
  Widget _buildCommunityList() {
    return RefreshIndicator(
      onRefresh: () => _loadCommunities(refresh: true),
      color: ElderColors.amber500,
      backgroundColor: ElderColors.slate800,
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        itemCount: _filteredCommunities.length + (_hasMorePages ? 1 : 0),
        itemBuilder: (context, index) {
          if (index == _filteredCommunities.length) {
            // Load more indicator
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 16),
              child: Center(
                child: GestureDetector(
                  onTap: _loadMore,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 24,
                      vertical: 12,
                    ),
                    decoration: BoxDecoration(
                      border: Border.all(
                        color: ElderColors.amber500,
                      ),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Text(
                      'Load More',
                      style: TextStyle(
                        color: ElderColors.amber500,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
              ),
            );
          }

          final community = _filteredCommunities[index];
          return _buildCommunityCard(community);
        },
      ),
    );
  }

  /// Build individual community card
  Widget _buildCommunityCard(Community community) {
    return GestureDetector(
      onTap: () => _navigateToCommunityDetail(community),
      child: Card(
        margin: const EdgeInsets.symmetric(vertical: 8),
        color: ElderColors.slate800,
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(
            color: ElderColors.slate700,
            width: 1,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // Avatar
              _buildAvatar(community),
              const SizedBox(width: 16),
              // Community info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Name
                    Text(
                      community.name,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: ElderColors.amber500,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    // Description
                    Text(
                      community.description,
                      style: const TextStyle(
                        fontSize: 13,
                        color: ElderColors.slate400,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 8),
                    // Member count
                    Row(
                      children: [
                        const Icon(
                          Icons.people,
                          size: 14,
                          color: ElderColors.slate500,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          '${community.memberCount} member${community.memberCount != 1 ? 's' : ''}',
                          style: const TextStyle(
                            fontSize: 12,
                            color: ElderColors.slate500,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              // Chevron
              const Icon(
                Icons.chevron_right,
                color: ElderColors.slate600,
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Build community avatar
  Widget _buildAvatar(Community community) {
    if (community.avatarUrl != null && community.avatarUrl!.isNotEmpty) {
      return Container(
        width: 56,
        height: 56,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: ElderColors.amber500,
            width: 2,
          ),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(6),
          child: Image.network(
            community.avatarUrl!,
            fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) {
              return _buildAvatarPlaceholder(community);
            },
          ),
        ),
      );
    }

    return _buildAvatarPlaceholder(community);
  }

  /// Build avatar placeholder
  Widget _buildAvatarPlaceholder(Community community) {
    return Container(
      width: 56,
      height: 56,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: ElderColors.slate700,
        border: Border.all(
          color: ElderColors.amber500,
          width: 2,
        ),
      ),
      child: Center(
        child: Text(
          community.name.isNotEmpty ? community.name[0].toUpperCase() : '?',
          style: const TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: ElderColors.amber500,
          ),
        ),
      ),
    );
  }
}
