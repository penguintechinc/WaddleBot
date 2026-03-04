import 'package:flutter/material.dart';
import 'package:flutter_libs/flutter_libs.dart';
import 'package:intl/intl.dart';
import '../../services/member_service.dart';
import '../../services/waddlebot_auth_service.dart';
import '../../models/member.dart';
import '../../models/api_response.dart';
import 'member_detail.dart';

/// Member list screen displaying all community members with search, filter, and role-based controls.
///
/// Features:
/// - ListView of member cards with avatar, name, role, online status
/// - Search bar with real-time filtering (minimum 2 characters)
/// - Role filter dropdown (All, Owner, Admin, Maintainer, Member, Viewer)
/// - Pull-to-refresh functionality
/// - Tap to navigate to member detail screen
/// - Elder theme styling with slate backgrounds and gold accents
/// - Loading and pagination support
/// - Role-based visibility (edit role button for admins only)
class MemberListScreen extends StatefulWidget {
  final String communityId;
  final bool isAdmin;

  const MemberListScreen({
    super.key,
    required this.communityId,
    this.isAdmin = false,
  });

  @override
  State<MemberListScreen> createState() => _MemberListScreenState();
}

class _MemberListScreenState extends State<MemberListScreen> {
  late final MemberService _memberService;
  late final WaddleBotAuthService _authService;
  late final TextEditingController _searchController;

  List<Member> _members = [];
  List<Member> _filteredMembers = [];
  bool _isLoading = false;
  bool _hasError = false;
  String? _errorMessage;
  int _currentPage = 1;
  bool _hasMorePages = false;
  String? _selectedRoleFilter;
  bool _isSearching = false;
  late final ScrollController _scrollController;

  static const List<String> _roleFilters = [
    'All',
    'Owner',
    'Admin',
    'Maintainer',
    'Member',
    'Viewer',
  ];

  static const Map<String, String> _roleToApiValue = {
    'Owner': 'owner',
    'Admin': 'admin',
    'Maintainer': 'maintainer',
    'Member': 'member',
    'Viewer': 'viewer',
  };

  @override
  void initState() {
    super.initState();
    _memberService = MemberService.getInstance();
    _authService = WaddleBotAuthService();
    _searchController = TextEditingController();
    _scrollController = ScrollController();
    _searchController.addListener(_onSearchChanged);
    _scrollController.addListener(_onScroll);
    _selectedRoleFilter = 'All';
    _loadMembers();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  /// Handle search input changes with debouncing
  void _onSearchChanged() {
    if (_isSearching) return;

    final query = _searchController.text.trim();

    if (query.isEmpty) {
      _currentPage = 1;
      _loadMembers();
      return;
    }

    if (query.length < 2) {
      if (!mounted) return;
      setState(() {
        _filteredMembers = [];
      });
      return;
    }

    _performSearch(query);
  }

  /// Perform member search via API
  Future<void> _performSearch(String query) async {
    if (!mounted) return;
    setState(() {
      _isSearching = true;
      _isLoading = true;
      _hasError = false;
      _errorMessage = null;
    });

    try {
      final roleFilter = _selectedRoleFilter != 'All'
          ? _roleToApiValue[_selectedRoleFilter]
          : null;

      final response = await _memberService.searchMembers(
        widget.communityId,
        query: query,
        page: 1,
        pageSize: 50,
        role: roleFilter,
      );

      if (!mounted) return;

      setState(() {
        _filteredMembers = response.items;
        _isLoading = false;
        _isSearching = false;
      });
    } on ApiError catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _isSearching = false;
        _hasError = true;
        _errorMessage = e.message ?? 'Search failed';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _isSearching = false;
        _hasError = true;
        _errorMessage = 'An unexpected error occurred';
      });
    }
  }

  /// Handle pagination with scroll
  void _onScroll() {
    if (_scrollController.position.pixels >=
            _scrollController.position.maxScrollExtent - 500 &&
        !_isLoading &&
        _hasMorePages) {
      _loadMoreMembers();
    }
  }

  /// Load members from API
  Future<void> _loadMembers({bool refresh = false}) async {
    if (refresh) {
      _currentPage = 1;
      _members = [];
      _searchController.clear();
    }

    if (!mounted) return;
    setState(() {
      _isLoading = true;
      _hasError = false;
      _errorMessage = null;
    });

    try {
      final roleFilter = _selectedRoleFilter != 'All'
          ? _roleToApiValue[_selectedRoleFilter]
          : null;

      final response = await _memberService.getMembers(
        widget.communityId,
        page: _currentPage,
        pageSize: 20,
        sortBy: 'reputation',
        sortOrder: 'desc',
        role: roleFilter,
      );

      if (!mounted) return;

      setState(() {
        if (refresh) {
          _members = response.items;
          _filteredMembers = response.items;
        } else {
          _members.addAll(response.items);
          _filteredMembers = _members;
        }
        _hasMorePages = response.hasMore;
        _isLoading = false;
      });
    } on ApiError catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _hasError = true;
        _errorMessage = e.message ?? 'Failed to load members';
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

  /// Load more members for pagination
  Future<void> _loadMoreMembers() async {
    if (_isLoading || !_hasMorePages) return;

    _currentPage++;
    await _loadMembers();
  }

  /// Handle role filter changes
  void _onRoleFilterChanged(String? newRole) {
    if (newRole == null) return;

    setState(() {
      _selectedRoleFilter = newRole;
    });

    _currentPage = 1;
    _loadMembers(refresh: true);
  }

  /// Navigate to member detail screen
  void _navigateToMemberDetail(Member member) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => MemberDetailScreen(
          communityId: widget.communityId,
          memberId: member.id,
          isAdmin: widget.isAdmin,
        ),
      ),
    );
  }

  /// Build member card widget
  Widget _buildMemberCard(Member member) {
    final initials = (member.displayName.isNotEmpty
            ? member.displayName[0]
            : member.username[0])
        .toUpperCase();

    return Card(
      color: ElderColors.slate800,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        onTap: () => _navigateToMemberDetail(member),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              // Avatar
              Stack(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: ElderColors.amber600,
                      shape: BoxShape.circle,
                      image: member.avatarUrl != null
                          ? DecorationImage(
                              image: NetworkImage(member.avatarUrl!),
                              fit: BoxFit.cover,
                            )
                          : null,
                    ),
                    child: member.avatarUrl == null
                        ? Center(
                            child: Text(
                              initials,
                              style: const TextStyle(
                                color: ElderColors.slate950,
                                fontWeight: FontWeight.bold,
                                fontSize: 18,
                              ),
                            ),
                          )
                        : null,
                  ),
                  // Online status indicator
                  if (member.isOnline == true)
                    Positioned(
                      bottom: 0,
                      right: 0,
                      child: Container(
                        width: 14,
                        height: 14,
                        decoration: BoxDecoration(
                          color: ElderColors.green500,
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: ElderColors.slate800,
                            width: 2,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(width: 12),
              // Member info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            member.displayName,
                            style: const TextStyle(
                              color: ElderColors.slate100,
                              fontWeight: FontWeight.w600,
                              fontSize: 15,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 8),
                        // Role badge
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: _getRoleColor(member.role),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            member.getRoleDisplayName(),
                            style: const TextStyle(
                              color: ElderColors.slate950,
                              fontWeight: FontWeight.bold,
                              fontSize: 11,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Text(
                          '@${member.username}',
                          style: const TextStyle(
                            color: ElderColors.slate400,
                            fontSize: 13,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '★ ${member.reputationScore}',
                          style: const TextStyle(
                            color: ElderColors.amber400,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              // Status text
              Text(
                member.isOnline == true ? 'Online' : 'Offline',
                style: TextStyle(
                  color: member.isOnline == true
                      ? ElderColors.green500
                      : ElderColors.slate400,
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ElderColors.slate950,
      appBar: AppBar(
        title: const Text(
          'Members',
          style: TextStyle(
            color: ElderColors.amber500,
            fontWeight: FontWeight.bold,
          ),
        ),
        backgroundColor: ElderColors.slate800,
        elevation: 0,
        centerTitle: true,
      ),
      body: Column(
        children: [
          // Search and filter section
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                // Search bar
                TextField(
                  controller: _searchController,
                  style: const TextStyle(color: ElderColors.slate100),
                  decoration: InputDecoration(
                    hintText: 'Search members... (min 2 chars)',
                    hintStyle: const TextStyle(color: ElderColors.slate500),
                    prefixIcon: const Icon(
                      Icons.search,
                      color: ElderColors.slate500,
                    ),
                    suffixIcon: _searchController.text.isNotEmpty
                        ? IconButton(
                            icon: const Icon(
                              Icons.clear,
                              color: ElderColors.slate500,
                            ),
                            onPressed: () {
                              _searchController.clear();
                            },
                          )
                        : null,
                    filled: true,
                    fillColor: ElderColors.slate800,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(
                        color: ElderColors.slate700,
                      ),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(
                        color: ElderColors.slate700,
                      ),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(
                        color: ElderColors.amber500,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                // Role filter dropdown
                DropdownButton<String>(
                  value: _selectedRoleFilter,
                  isExpanded: true,
                  dropdownColor: ElderColors.slate800,
                  style: const TextStyle(color: ElderColors.amber500),
                  items: _roleFilters.map((role) {
                    return DropdownMenuItem<String>(
                      value: role,
                      child: Text(
                        'Role: $role',
                        style: const TextStyle(color: ElderColors.slate100),
                      ),
                    );
                  }).toList(),
                  onChanged: _onRoleFilterChanged,
                  underline: Container(
                    height: 1,
                    color: ElderColors.slate700,
                  ),
                ),
              ],
            ),
          ),
          // Members list
          Expanded(
            child: _buildMembersList(),
          ),
        ],
      ),
    );
  }

  /// Build members list widget
  Widget _buildMembersList() {
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
              _errorMessage ?? 'Failed to load members',
              style: const TextStyle(
                color: ElderColors.slate300,
                fontSize: 16,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => _loadMembers(refresh: true),
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

    if (_isLoading && _members.isEmpty) {
      return const Center(
        child: CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation<Color>(ElderColors.amber500),
        ),
      );
    }

    final displayMembers =
        _searchController.text.isNotEmpty ? _filteredMembers : _members;

    if (displayMembers.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              _searchController.text.isNotEmpty
                  ? Icons.person_search
                  : Icons.people_outline,
              size: 64,
              color: ElderColors.slate500,
            ),
            const SizedBox(height: 16),
            Text(
              _searchController.text.isNotEmpty
                  ? 'No members found'
                  : 'No members yet',
              style: const TextStyle(
                color: ElderColors.slate300,
                fontSize: 16,
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => _loadMembers(refresh: true),
      color: ElderColors.amber500,
      backgroundColor: ElderColors.slate800,
      child: ListView.builder(
        controller: _scrollController,
        itemCount: displayMembers.length + (_isLoading ? 1 : 0),
        itemBuilder: (context, index) {
          if (index == displayMembers.length) {
            return const Padding(
              padding: EdgeInsets.all(16),
              child: Center(
                child: SizedBox(
                  width: 30,
                  height: 30,
                  child: CircularProgressIndicator(
                    valueColor: AlwaysStoppedAnimation<Color>(
                      ElderColors.amber500,
                    ),
                    strokeWidth: 2,
                  ),
                ),
              ),
            );
          }

          return _buildMemberCard(displayMembers[index]);
        },
      ),
    );
  }
}
