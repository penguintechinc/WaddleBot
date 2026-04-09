/// Community Service for REST API operations
/// Handles all community-related API interactions with type-safe responses
/// Uses ApiClient singleton for HTTP calls and supports pagination
library;

import 'api_client.dart';
import '../models/community.dart';
import '../models/api_response.dart' hide ApiError;

/// Community REST API Service
///
/// Manages all community operations including retrieval, creation,
/// updates, deletion, statistics, and activity tracking.
///
/// Uses the Waddles API at: /api/v1/communities
class CommunityService {
  static final CommunityService _instance = CommunityService._internal();
  late final ApiClient _apiClient;

  static const String _basePath = '/communities';

  CommunityService._internal() {
    _apiClient = ApiClient.getInstance();
  }

  /// Get singleton instance of CommunityService
  static CommunityService getInstance() => _instance;

  /// Get all communities with pagination support
  ///
  /// Returns paginated list of communities
  ///
  /// Parameters:
  /// - [page] Current page number (default: 1)
  /// - [pageSize] Number of items per page (default: 20)
  /// - [sortBy] Field to sort by (optional)
  /// - [sortOrder] Sort order 'asc' or 'desc' (optional)
  ///
  /// Returns: [PaginatedResponse<Community>] with paginated community list
  ///
  /// Throws: [ApiError] if request fails
  ///
  /// Example:
  /// ```dart
  /// final response = await CommunityService.getInstance()
  ///   .getCommunities(page: 1, pageSize: 20);
  /// if (response.hasMore) {
  ///   print('${response.items.length} communities loaded');
  /// }
  /// ```
  Future<PaginatedResponse<Community>> getCommunities({
    int page = 1,
    int pageSize = 20,
    String? sortBy,
    String? sortOrder,
  }) async {
    try {
      final params = {
        'page': page,
        'page_size': pageSize,
        if (sortBy != null) 'sort_by': sortBy,
        if (sortOrder != null) 'sort_order': sortOrder,
      };

      final response = await _apiClient.get<PaginatedResponse<Community>>(
        _basePath,
        queryParameters: params,
        fromJson: (data) => PaginatedResponse.fromJson(
          data as Map<String, dynamic>,
          itemFactory: (item) =>
              Community.fromJson(item as Map<String, dynamic>),
        ),
      );

      return response;
    } on ApiError {
      rethrow;
    }
  }

  /// Get detailed information about a specific community
  ///
  /// Returns community details including stats and recent activity
  ///
  /// Parameters:
  /// - [id] Community ID
  ///
  /// Returns: [ApiResponse<CommunityDetail>] with full community details
  ///
  /// Throws: [ApiError] if community not found or request fails
  ///
  /// Example:
  /// ```dart
  /// final response = await CommunityService.getInstance()
  ///   .getCommunityDetail('community-123');
  /// print('Member count: ${response.data?.stats.memberCount}');
  /// ```
  Future<ApiResponse<CommunityDetail>> getCommunityDetail(String id) async {
    try {
      final response = await _apiClient.get<ApiResponse<CommunityDetail>>(
        '$_basePath/$id',
        fromJson: (data) => ApiResponse.fromJson(
          data as Map<String, dynamic>,
          dataFactory: (item) =>
              CommunityDetail.fromJson(item as Map<String, dynamic>),
        ),
      );

      return response;
    } on ApiError {
      rethrow;
    }
  }

  /// Create a new community
  ///
  /// Creates a new community with the provided details
  ///
  /// Parameters:
  /// - [name] Community name (required)
  /// - [description] Community description (required)
  /// - [avatarUrl] Avatar image URL (optional)
  ///
  /// Returns: [ApiResponse<Community>] with newly created community
  ///
  /// Throws: [ApiError] if validation fails or request fails
  ///
  /// Example:
  /// ```dart
  /// final response = await CommunityService.getInstance()
  ///   .createCommunity(
  ///     name: 'Gaming Hub',
  ///     description: 'Community for gamers',
  ///     avatarUrl: 'https://example.com/avatar.png'
  ///   );
  /// print('Created: ${response.data?.id}');
  /// ```
  Future<ApiResponse<Community>> createCommunity({
    required String name,
    required String description,
    String? avatarUrl,
  }) async {
    try {
      final data = {
        'name': name,
        'description': description,
        if (avatarUrl != null) 'avatar_url': avatarUrl,
      };

      final response = await _apiClient.post<ApiResponse<Community>>(
        _basePath,
        data: data,
        fromJson: (responseData) => ApiResponse.fromJson(
          responseData as Map<String, dynamic>,
          dataFactory: (item) =>
              Community.fromJson(item as Map<String, dynamic>),
        ),
      );

      return response;
    } on ApiError {
      rethrow;
    }
  }

  /// Update an existing community
  ///
  /// Updates community name, description, or avatar
  ///
  /// Parameters:
  /// - [id] Community ID to update
  /// - [name] New community name (optional)
  /// - [description] New description (optional)
  /// - [avatarUrl] New avatar URL (optional)
  ///
  /// Returns: [ApiResponse<Community>] with updated community
  ///
  /// Throws: [ApiError] if not authorized or request fails
  ///
  /// Example:
  /// ```dart
  /// final response = await CommunityService.getInstance()
  ///   .updateCommunity(
  ///     id: 'community-123',
  ///     name: 'New Gaming Hub',
  ///     description: 'Updated description'
  ///   );
  /// ```
  Future<ApiResponse<Community>> updateCommunity(
    String id, {
    String? name,
    String? description,
    String? avatarUrl,
  }) async {
    try {
      final data = {
        if (name != null) 'name': name,
        if (description != null) 'description': description,
        if (avatarUrl != null) 'avatar_url': avatarUrl,
      };

      final response = await _apiClient.put<ApiResponse<Community>>(
        '$_basePath/$id',
        data: data,
        fromJson: (responseData) => ApiResponse.fromJson(
          responseData as Map<String, dynamic>,
          dataFactory: (item) =>
              Community.fromJson(item as Map<String, dynamic>),
        ),
      );

      return response;
    } on ApiError {
      rethrow;
    }
  }

  /// Delete a community
  ///
  /// Permanently deletes a community and all associated data
  /// Only community owner can delete
  ///
  /// Parameters:
  /// - [id] Community ID to delete
  ///
  /// Returns: [ApiResponse<void>] indicating success/failure
  ///
  /// Throws: [ApiError] if not authorized or request fails
  ///
  /// Example:
  /// ```dart
  /// final response = await CommunityService.getInstance()
  ///   .deleteCommunity('community-123');
  /// if (response.success) {
  ///   print('Community deleted');
  /// }
  /// ```
  Future<ApiResponse<void>> deleteCommunity(String id) async {
    try {
      await _apiClient.delete<Map<String, dynamic>>(
        '$_basePath/$id',
        fromJson: (responseData) => responseData as Map<String, dynamic>,
      );

      return ApiResponse<void>(
        success: true,
        statusCode: 200,
        message: 'Community deleted successfully',
        timestamp: DateTime.now(),
      );
    } on ApiError {
      rethrow;
    }
  }

  /// Get community statistics
  ///
  /// Retrieves statistics including member count, active members,
  /// commands and messages posted today
  ///
  /// Parameters:
  /// - [id] Community ID
  ///
  /// Returns: [ApiResponse<CommunityStats>] with stats data
  ///
  /// Throws: [ApiError] if community not found or request fails
  ///
  /// Example:
  /// ```dart
  /// final response = await CommunityService.getInstance()
  ///   .getCommunityStats('community-123');
  /// print('Active members: ${response.data?.activeMembers}');
  /// ```
  Future<ApiResponse<CommunityStats>> getCommunityStats(String id) async {
    try {
      final response = await _apiClient.get<ApiResponse<CommunityStats>>(
        '$_basePath/$id/stats',
        fromJson: (data) => ApiResponse.fromJson(
          data as Map<String, dynamic>,
          dataFactory: (item) =>
              CommunityStats.fromJson(item as Map<String, dynamic>),
        ),
      );

      return response;
    } on ApiError {
      rethrow;
    }
  }

  /// Get recent activity in a community
  ///
  /// Retrieves recent activity including member joins, messages,
  /// commands, and workflows
  ///
  /// Parameters:
  /// - [id] Community ID
  /// - [limit] Number of activity items to retrieve (default: 10, max: 50)
  /// - [offset] Pagination offset (default: 0)
  ///
  /// Returns: [PaginatedResponse<ActivityItem>] with activity list
  ///
  /// Throws: [ApiError] if community not found or request fails
  ///
  /// Example:
  /// ```dart
  /// final response = await CommunityService.getInstance()
  ///   .getRecentActivity('community-123', limit: 20);
  /// for (var activity in response.items) {
  ///   print('${activity.type}: ${activity.description}');
  /// }
  /// ```
  Future<PaginatedResponse<ActivityItem>> getRecentActivity(
    String id, {
    int limit = 10,
    int offset = 0,
  }) async {
    try {
      final params = {
        'limit': limit.clamp(1, 50),
        'offset': offset,
      };

      final response = await _apiClient.get<PaginatedResponse<ActivityItem>>(
        '$_basePath/$id/activity',
        queryParameters: params,
        fromJson: (data) => PaginatedResponse.fromJson(
          data as Map<String, dynamic>,
          itemFactory: (item) =>
              ActivityItem.fromJson(item as Map<String, dynamic>),
        ),
      );

      return response;
    } on ApiError {
      rethrow;
    }
  }
}
