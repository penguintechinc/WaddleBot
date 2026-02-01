/// Member Service for REST API operations
/// Handles all member-related API interactions with role-based access control
/// Uses ApiClient singleton for HTTP calls and supports pagination and search

import 'api_client.dart';
import '../models/member.dart';
import '../models/api_response.dart' hide ApiError;

/// Member REST API Service
///
/// Manages all member operations including retrieval, role management,
/// member search, and membership changes within communities.
///
/// Uses the WaddleBot API at: /api/v1/communities/{communityId}/members
class MemberService {
  static final MemberService _instance = MemberService._internal();
  late final ApiClient _apiClient;

  static const String _basePath = '/communities';

  MemberService._internal() {
    _apiClient = ApiClient.getInstance();
  }

  /// Get singleton instance of MemberService
  static MemberService getInstance() => _instance;

  /// Get all members of a community with pagination support
  ///
  /// Returns paginated list of community members
  ///
  /// Parameters:
  /// - [communityId] Community ID (required)
  /// - [page] Current page number (default: 1)
  /// - [pageSize] Number of items per page (default: 20)
  /// - [sortBy] Field to sort by - 'role', 'reputation', 'joined_at' (optional)
  /// - [sortOrder] Sort order 'asc' or 'desc' (optional)
  /// - [role] Filter by role (optional) - e.g., 'admin', 'member'
  ///
  /// Returns: [PaginatedResponse<Member>] with paginated member list
  ///
  /// Throws: [ApiError] if request fails
  ///
  /// Example:
  /// ```dart
  /// final response = await MemberService.getInstance()
  ///   .getMembers('community-123', page: 1, pageSize: 50);
  /// print('Loaded ${response.items.length} members');
  /// ```
  Future<PaginatedResponse<Member>> getMembers(
    String communityId, {
    int page = 1,
    int pageSize = 20,
    String? sortBy,
    String? sortOrder,
    String? role,
  }) async {
    try {
      final params = {
        'page': page,
        'page_size': pageSize,
        if (sortBy != null) 'sort_by': sortBy,
        if (sortOrder != null) 'sort_order': sortOrder,
        if (role != null) 'role': role,
      };

      final response = await _apiClient.get<PaginatedResponse<Member>>(
        '$_basePath/$communityId/members',
        queryParameters: params,
        fromJson: (data) => PaginatedResponse.fromJson(
          data as Map<String, dynamic>,
          itemFactory: (item) => Member.fromJson(item as Map<String, dynamic>),
        ),
      );

      return response;
    } on ApiError {
      rethrow;
    }
  }

  /// Get detailed information about a specific community member
  ///
  /// Returns member details including permissions and badges
  ///
  /// Parameters:
  /// - [communityId] Community ID
  /// - [memberId] Member ID to retrieve
  ///
  /// Returns: [ApiResponse<MemberDetail>] with full member details
  ///
  /// Throws: [ApiError] if member not found or request fails
  ///
  /// Example:
  /// ```dart
  /// final response = await MemberService.getInstance()
  ///   .getMemberDetail('community-123', 'member-456');
  /// print('Role: ${response.data?.getRoleDisplayName()}');
  /// print('Permissions: ${response.data?.permissions}');
  /// ```
  Future<ApiResponse<MemberDetail>> getMemberDetail(
    String communityId,
    String memberId,
  ) async {
    try {
      final response = await _apiClient.get<ApiResponse<MemberDetail>>(
        '$_basePath/$communityId/members/$memberId',
        fromJson: (data) => ApiResponse.fromJson(
          data as Map<String, dynamic>,
          dataFactory: (item) =>
              MemberDetail.fromJson(item as Map<String, dynamic>),
        ),
      );

      return response;
    } on ApiError {
      rethrow;
    }
  }

  /// Add a new member to a community
  ///
  /// Invites or adds a user to a community with specified role
  ///
  /// Parameters:
  /// - [communityId] Community ID
  /// - [userId] User ID to add (required)
  /// - [role] Member role - 'owner', 'admin', 'maintainer', 'member', 'viewer'
  ///   (default: 'member')
  ///
  /// Returns: [ApiResponse<Member>] with newly added member
  ///
  /// Throws: [ApiError] if user not found, already member, or not authorized
  ///
  /// Example:
  /// ```dart
  /// final response = await MemberService.getInstance()
  ///   .addMember('community-123', 'user-789', role: 'member');
  /// print('Member added: ${response.data?.displayName}');
  /// ```
  Future<ApiResponse<Member>> addMember(
    String communityId, {
    required String userId,
    String role = 'member',
  }) async {
    try {
      final data = {
        'user_id': userId,
        'role': role,
      };

      final response = await _apiClient.post<ApiResponse<Member>>(
        '$_basePath/$communityId/members',
        data: data,
        fromJson: (responseData) => ApiResponse.fromJson(
          responseData as Map<String, dynamic>,
          dataFactory: (item) =>
              Member.fromJson(item as Map<String, dynamic>),
        ),
      );

      return response;
    } on ApiError {
      rethrow;
    }
  }

  /// Update a member's role in the community
  ///
  /// Changes a member's role with role hierarchy validation
  /// Cannot promote beyond current user's role level
  ///
  /// Parameters:
  /// - [communityId] Community ID
  /// - [memberId] Member ID to update
  /// - [role] New role - 'owner', 'admin', 'maintainer', 'member', 'viewer'
  ///   (required)
  ///
  /// Returns: [ApiResponse<Member>] with updated member
  ///
  /// Throws: [ApiError] if not authorized or invalid role
  ///
  /// Example:
  /// ```dart
  /// final response = await MemberService.getInstance()
  ///   .updateMemberRole('community-123', 'member-456', 'admin');
  /// print('Updated role: ${response.data?.getRoleDisplayName()}');
  /// ```
  Future<ApiResponse<Member>> updateMemberRole(
    String communityId,
    String memberId,
    String role,
  ) async {
    try {
      final data = {
        'role': role,
      };

      final response = await _apiClient.put<ApiResponse<Member>>(
        '$_basePath/$communityId/members/$memberId',
        data: data,
        fromJson: (responseData) => ApiResponse.fromJson(
          responseData as Map<String, dynamic>,
          dataFactory: (item) =>
              Member.fromJson(item as Map<String, dynamic>),
        ),
      );

      return response;
    } on ApiError {
      rethrow;
    }
  }

  /// Remove a member from the community
  ///
  /// Permanently removes a member from the community
  /// Member data and history are retained for audit purposes
  ///
  /// Parameters:
  /// - [communityId] Community ID
  /// - [memberId] Member ID to remove
  ///
  /// Returns: [ApiResponse<void>] indicating success/failure
  ///
  /// Throws: [ApiError] if not authorized or member not found
  ///
  /// Example:
  /// ```dart
  /// final response = await MemberService.getInstance()
  ///   .removeMember('community-123', 'member-456');
  /// if (response.success) {
  ///   print('Member removed from community');
  /// }
  /// ```
  Future<ApiResponse<void>> removeMember(
    String communityId,
    String memberId,
  ) async {
    try {
      await _apiClient.delete<Map<String, dynamic>>(
        '$_basePath/$communityId/members/$memberId',
        fromJson: (responseData) => responseData as Map<String, dynamic>,
      );

      return ApiResponse<void>(
        success: true,
        statusCode: 200,
        message: 'Member removed successfully',
        timestamp: DateTime.now(),
      );
    } on ApiError {
      rethrow;
    }
  }

  /// Search for members in a community
  ///
  /// Searches for community members by username, display name, or email
  /// Supports fuzzy matching and partial queries
  ///
  /// Parameters:
  /// - [communityId] Community ID
  /// - [query] Search query string (required, minimum 2 characters)
  /// - [page] Current page number (default: 1)
  /// - [pageSize] Number of items per page (default: 20)
  /// - [role] Filter results by role (optional)
  ///
  /// Returns: [PaginatedResponse<Member>] with search results
  ///
  /// Throws: [ApiError] if request fails or query too short
  ///
  /// Example:
  /// ```dart
  /// final response = await MemberService.getInstance()
  ///   .searchMembers('community-123', 'john', pageSize: 10);
  /// for (var member in response.items) {
  ///   print('${member.displayName} (@${member.username})');
  /// }
  /// ```
  Future<PaginatedResponse<Member>> searchMembers(
    String communityId, {
    required String query,
    int page = 1,
    int pageSize = 20,
    String? role,
  }) async {
    try {
      // Validate query length
      if (query.trim().length < 2) {
        throw ApiError(
          message: 'Search query must be at least 2 characters',
          statusCode: 400,
          errorCode: 'INVALID_QUERY',
        );
      }

      final params = {
        'q': query.trim(),
        'page': page,
        'page_size': pageSize,
        if (role != null) 'role': role,
      };

      final response = await _apiClient.get<PaginatedResponse<Member>>(
        '$_basePath/$communityId/members/search',
        queryParameters: params,
        fromJson: (data) => PaginatedResponse.fromJson(
          data as Map<String, dynamic>,
          itemFactory: (item) => Member.fromJson(item as Map<String, dynamic>),
        ),
      );

      return response;
    } on ApiError {
      rethrow;
    }
  }

  /// Get online status of community members
  ///
  /// Retrieves current online status of specified members
  ///
  /// Parameters:
  /// - [communityId] Community ID
  /// - [memberIds] List of member IDs to check (required)
  ///
  /// Returns: [ApiResponse<Map<String, bool>>] mapping member ID to online status
  ///
  /// Throws: [ApiError] if request fails
  ///
  /// Example:
  /// ```dart
  /// final response = await MemberService.getInstance()
  ///   .getOnlineStatus('community-123',
  ///     memberIds: ['member-1', 'member-2']);
  /// response.data?.forEach((memberId, isOnline) {
  ///   print('$memberId: ${isOnline ? "Online" : "Offline"}');
  /// });
  /// ```
  Future<ApiResponse<Map<String, bool>>> getOnlineStatus(
    String communityId, {
    required List<String> memberIds,
  }) async {
    try {
      final data = {
        'member_ids': memberIds,
      };

      final response =
          await _apiClient.post<ApiResponse<Map<String, bool>>>(
        '$_basePath/$communityId/members/online-status',
        data: data,
        fromJson: (responseData) {
          final apiResp = ApiResponse.fromJson(
            responseData as Map<String, dynamic>,
            dataFactory: (item) {
              if (item is Map) {
                return Map<String, bool>.from(
                  (item as Map<String, dynamic>).map(
                    (key, value) => MapEntry(key, value as bool),
                  ),
                );
              }
              return <String, bool>{};
            },
          );
          return apiResp;
        },
      );

      return response;
    } on ApiError {
      rethrow;
    }
  }

  /// Get member statistics for a community
  ///
  /// Retrieves aggregated member statistics
  ///
  /// Parameters:
  /// - [communityId] Community ID
  ///
  /// Returns: [ApiResponse<Map<String, int>>] with statistics
  ///   - total: Total member count
  ///   - active: Active members (last 7 days)
  ///   - admins: Admin count
  ///   - online: Currently online
  ///
  /// Throws: [ApiError] if request fails
  ///
  /// Example:
  /// ```dart
  /// final response = await MemberService.getInstance()
  ///   .getMemberStats('community-123');
  /// print('Total: ${response.data?["total"]}');
  /// print('Online: ${response.data?["online"]}');
  /// ```
  Future<ApiResponse<Map<String, int>>> getMemberStats(
    String communityId,
  ) async {
    try {
      final response = await _apiClient.get<ApiResponse<Map<String, int>>>(
        '$_basePath/$communityId/members/stats',
        fromJson: (responseData) {
          final apiResp = ApiResponse.fromJson(
            responseData as Map<String, dynamic>,
            dataFactory: (item) {
              if (item is Map) {
                return Map<String, int>.from(
                  (item as Map<String, dynamic>).map(
                    (key, value) => MapEntry(key, value as int),
                  ),
                );
              }
              return <String, int>{};
            },
          );
          return apiResp;
        },
      );

      return response;
    } on ApiError {
      rethrow;
    }
  }
}
