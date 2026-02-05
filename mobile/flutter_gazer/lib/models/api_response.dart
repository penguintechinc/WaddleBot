/// API response wrapper models for Flutter Gazer application.
/// Provides generic response handling with success/error states and pagination support.

import 'package:equatable/equatable.dart';

import 'community.dart';
import 'member.dart';
import 'waddlebot_models.dart';

/// Generic API response wrapper supporting both success and error states.
///
/// This wrapper handles the standard response format from Waddles API endpoints.
/// It supports generic type parameter [T] for type-safe response data handling.
///
/// Example usage:
/// ```dart
/// final response = ApiResponse<Community>.fromJson(jsonData);
/// if (response.success) {
///   print(response.data?.name);
/// } else {
///   print(response.error?.message);
/// }
/// ```
class ApiResponse<T> extends Equatable {
  /// Whether the API request was successful.
  final bool success;

  /// The response data of type [T]. Null if request failed or no data returned.
  final T? data;

  /// Structured error information. Null if request succeeded.
  final ApiError? error;

  /// Human-readable message (success or error description).
  final String? message;

  /// HTTP status code from the API response.
  final int? statusCode;

  /// Request timestamp for tracking purposes.
  final DateTime? timestamp;

  const ApiResponse({
    required this.success,
    this.data,
    this.error,
    this.message,
    this.statusCode,
    this.timestamp,
  });

  /// Create a successful response with data.
  factory ApiResponse.success({
    required T data,
    String? message,
    int? statusCode,
  }) {
    return ApiResponse<T>(
      success: true,
      data: data,
      message: message ?? 'Request successful',
      statusCode: statusCode ?? 200,
      timestamp: DateTime.now(),
    );
  }

  /// Create a failed response with error details.
  factory ApiResponse.error({
    required ApiError error,
    String? message,
    int? statusCode,
  }) {
    return ApiResponse<T>(
      success: false,
      error: error,
      message: message ?? error.message,
      statusCode: statusCode ?? 500,
      timestamp: DateTime.now(),
    );
  }

  /// Parse API response from JSON, handling both success and error cases.
  ///
  /// Requires a [dataFactory] function to parse the data field into type [T].
  /// If [dataFactory] is not provided, [T] must be a primitive type.
  factory ApiResponse.fromJson(
    Map<String, dynamic> json, {
    T Function(dynamic)? dataFactory,
  }) {
    final isSuccess = json['success'] as bool? ?? false;
    final statusCode = json['status_code'] as int? ?? json['code'] as int?;
    final message = json['message'] as String?;
    final timestamp = json['timestamp'] as String?;

    T? data;
    ApiError? error;

    if (isSuccess && json['data'] != null) {
      if (dataFactory != null) {
        try {
          data = dataFactory(json['data']);
        } catch (e) {
          // Fallback if factory fails
          data = null;
        }
      }
    } else if (!isSuccess && json['error'] != null) {
      error = ApiError.fromJson(json['error'] as Map<String, dynamic>);
    }

    return ApiResponse<T>(
      success: isSuccess,
      data: data,
      error: error,
      message: message,
      statusCode: statusCode,
      timestamp: timestamp != null ? DateTime.tryParse(timestamp) : null,
    );
  }

  /// Convert response to JSON.
  Map<String, dynamic> toJson() => {
        'success': success,
        if (data != null) 'data': _toJsonValue(data),
        if (error != null) 'error': error!.toJson(),
        if (message != null) 'message': message,
        if (statusCode != null) 'status_code': statusCode,
        if (timestamp != null) 'timestamp': timestamp!.toIso8601String(),
      };

  /// Helper method to convert data to JSON-serializable value.
  dynamic _toJsonValue(dynamic value) {
    if (value == null) {
      return null;
    } else if (value is Map<String, dynamic>) {
      return value;
    } else if (value is List) {
      return value.map((item) => _toJsonValue(item)).toList();
    } else if (value is Enum) {
      return value.toString().split('.').last;
    }
    return value;
  }

  @override
  List<Object?> get props => [success, data, error, message, statusCode, timestamp];
}

/// Structured error information for API responses.
///
/// Contains error code, message, and optional detailed information.
class ApiError extends Equatable {
  /// Error code (e.g., 'VALIDATION_ERROR', 'UNAUTHORIZED', 'NOT_FOUND').
  final String code;

  /// Human-readable error message.
  final String message;

  /// Detailed error information (field-specific errors, stack traces, etc.).
  final Map<String, dynamic>? details;

  /// Error timestamp for tracking.
  final DateTime? timestamp;

  const ApiError({
    required this.code,
    required this.message,
    this.details,
    this.timestamp,
  });

  /// Create error from JSON.
  factory ApiError.fromJson(Map<String, dynamic> json) {
    return ApiError(
      code: json['code'] as String? ?? 'UNKNOWN_ERROR',
      message: json['message'] as String? ?? 'An unknown error occurred',
      details: json['details'] as Map<String, dynamic>?,
      timestamp: json['timestamp'] != null
          ? DateTime.tryParse(json['timestamp'] as String)
          : null,
    );
  }

  /// Convert error to JSON.
  Map<String, dynamic> toJson() => {
        'code': code,
        'message': message,
        if (details != null) 'details': details,
        if (timestamp != null) 'timestamp': timestamp!.toIso8601String(),
      };

  @override
  List<Object?> get props => [code, message, details, timestamp];
}

/// Paginated API response wrapper for list responses.
///
/// Handles pagination metadata along with paginated items of type [T].
///
/// Example usage:
/// ```dart
/// final response = PaginatedResponse<Community>.fromJson(jsonData);
/// print('Items: ${response.items.length}');
/// print('Total: ${response.total}');
/// print('Has more: ${response.hasMore}');
/// ```
class PaginatedResponse<T> extends Equatable {
  /// List of items in the current page.
  final List<T> items;

  /// Total number of items across all pages.
  final int total;

  /// Current page number (1-indexed).
  final int page;

  /// Number of items per page.
  final int limit;

  /// Whether there are more pages available.
  final bool hasMore;

  /// Total number of pages available.
  final int? totalPages;

  /// Pagination cursor for cursor-based pagination (alternative to page-based).
  final String? nextCursor;

  /// HTTP status code from the API response.
  final int? statusCode;

  /// Response message.
  final String? message;

  /// Request timestamp.
  final DateTime? timestamp;

  const PaginatedResponse({
    required this.items,
    required this.total,
    required this.page,
    required this.limit,
    this.hasMore = false,
    this.totalPages,
    this.nextCursor,
    this.statusCode,
    this.message,
    this.timestamp,
  });

  /// Create successful paginated response.
  factory PaginatedResponse.success({
    required List<T> items,
    required int total,
    required int page,
    required int limit,
    String? nextCursor,
    int? statusCode,
    String? message,
  }) {
    final totalPages = (total / limit).ceil();
    final hasMore = page < totalPages;

    return PaginatedResponse<T>(
      items: items,
      total: total,
      page: page,
      limit: limit,
      hasMore: hasMore,
      totalPages: totalPages,
      nextCursor: nextCursor,
      statusCode: statusCode ?? 200,
      message: message,
      timestamp: DateTime.now(),
    );
  }

  /// Parse paginated response from JSON.
  ///
  /// Requires a [itemFactory] function to parse items of type [T].
  factory PaginatedResponse.fromJson(
    Map<String, dynamic> json, {
    required T Function(dynamic) itemFactory,
  }) {
    final itemsList = (json['items'] as List<dynamic>?)
            ?.map((item) => itemFactory(item))
            .toList() ??
        (json['data'] as List<dynamic>?)
            ?.map((item) => itemFactory(item))
            .toList() ??
        <T>[];

    final total = json['total'] as int? ?? itemsList.length;
    final page = json['page'] as int? ?? json['current_page'] as int? ?? 1;
    final limit = json['limit'] as int? ?? json['per_page'] as int? ?? 10;
    final statusCode = json['status_code'] as int? ?? json['code'] as int?;
    final message = json['message'] as String?;
    final timestamp = json['timestamp'] as String?;
    final nextCursor = json['next_cursor'] as String?;

    final totalPages = (total / limit).ceil();
    final hasMore = page < totalPages;

    return PaginatedResponse<T>(
      items: itemsList,
      total: total,
      page: page,
      limit: limit,
      hasMore: hasMore,
      totalPages: totalPages,
      nextCursor: nextCursor,
      statusCode: statusCode,
      message: message,
      timestamp: timestamp != null ? DateTime.tryParse(timestamp) : null,
    );
  }

  /// Convert paginated response to JSON.
  Map<String, dynamic> toJson() => {
        'items': items.map((item) => _toJsonValue(item)).toList(),
        'total': total,
        'page': page,
        'limit': limit,
        'has_more': hasMore,
        if (totalPages != null) 'total_pages': totalPages,
        if (nextCursor != null) 'next_cursor': nextCursor,
        if (statusCode != null) 'status_code': statusCode,
        if (message != null) 'message': message,
        if (timestamp != null) 'timestamp': timestamp!.toIso8601String(),
      };

  /// Helper method to convert items to JSON-serializable value.
  dynamic _toJsonValue(dynamic value) {
    if (value == null) {
      return null;
    } else if (value is Map<String, dynamic>) {
      return value;
    } else if (value is List) {
      return value.map((item) => _toJsonValue(item)).toList();
    } else if (value is Enum) {
      return value.toString().split('.').last;
    }
    return value;
  }

  @override
  List<Object?> get props => [
        items,
        total,
        page,
        limit,
        hasMore,
        totalPages,
        nextCursor,
        statusCode,
        message,
        timestamp,
      ];
}

/// Communities list API response wrapper.
///
/// Convenient wrapper for API responses containing a list of communities.
class CommunitiesResponse extends Equatable {
  /// List of communities in the response.
  final List<Community> communities;

  /// Total count of communities (useful for pagination).
  final int? total;

  /// Whether the request was successful.
  final bool success;

  /// Error information if request failed.
  final ApiError? error;

  /// Response message.
  final String? message;

  /// HTTP status code.
  final int? statusCode;

  const CommunitiesResponse({
    required this.communities,
    this.total,
    this.success = true,
    this.error,
    this.message,
    this.statusCode,
  });

  /// Create successful communities response.
  factory CommunitiesResponse.success({
    required List<Community> communities,
    int? total,
    String? message,
    int? statusCode,
  }) {
    return CommunitiesResponse(
      communities: communities,
      total: total,
      success: true,
      message: message,
      statusCode: statusCode ?? 200,
    );
  }

  /// Create failed communities response.
  factory CommunitiesResponse.error({
    required ApiError error,
    String? message,
    int? statusCode,
  }) {
    return CommunitiesResponse(
      communities: [],
      success: false,
      error: error,
      message: message,
      statusCode: statusCode ?? 500,
    );
  }

  /// Parse from JSON with error handling.
  factory CommunitiesResponse.fromJson(Map<String, dynamic> json) {
    final isSuccess = json['success'] as bool? ?? true;

    if (!isSuccess && json['error'] != null) {
      return CommunitiesResponse.error(
        error: ApiError.fromJson(json['error'] as Map<String, dynamic>),
        message: json['message'] as String?,
        statusCode: json['status_code'] as int?,
      );
    }

    final communitiesList = (json['communities'] as List<dynamic>?)
            ?.map((c) => Community.fromJson(c as Map<String, dynamic>))
            .toList() ??
        (json['data'] as List<dynamic>?)
            ?.map((c) => Community.fromJson(c as Map<String, dynamic>))
            .toList() ??
        <Community>[];

    return CommunitiesResponse.success(
      communities: communitiesList,
      total: json['total'] as int?,
      message: json['message'] as String?,
      statusCode: json['status_code'] as int?,
    );
  }

  /// Convert to JSON.
  Map<String, dynamic> toJson() => {
        'success': success,
        'communities': communities.map((c) => c.toJson()).toList(),
        if (total != null) 'total': total,
        if (error != null) 'error': error!.toJson(),
        if (message != null) 'message': message,
        if (statusCode != null) 'status_code': statusCode,
      };

  @override
  List<Object?> get props => [communities, total, success, error, message, statusCode];
}

/// Members list API response wrapper.
///
/// Convenient wrapper for API responses containing a list of members.
class MembersResponse extends Equatable {
  /// List of members in the response.
  final List<Member> members;

  /// Total count of members (useful for pagination).
  final int? total;

  /// Whether the request was successful.
  final bool success;

  /// Error information if request failed.
  final ApiError? error;

  /// Response message.
  final String? message;

  /// HTTP status code.
  final int? statusCode;

  const MembersResponse({
    required this.members,
    this.total,
    this.success = true,
    this.error,
    this.message,
    this.statusCode,
  });

  /// Create successful members response.
  factory MembersResponse.success({
    required List<Member> members,
    int? total,
    String? message,
    int? statusCode,
  }) {
    return MembersResponse(
      members: members,
      total: total,
      success: true,
      message: message,
      statusCode: statusCode ?? 200,
    );
  }

  /// Create failed members response.
  factory MembersResponse.error({
    required ApiError error,
    String? message,
    int? statusCode,
  }) {
    return MembersResponse(
      members: [],
      success: false,
      error: error,
      message: message,
      statusCode: statusCode ?? 500,
    );
  }

  /// Parse from JSON with error handling.
  factory MembersResponse.fromJson(Map<String, dynamic> json) {
    final isSuccess = json['success'] as bool? ?? true;

    if (!isSuccess && json['error'] != null) {
      return MembersResponse.error(
        error: ApiError.fromJson(json['error'] as Map<String, dynamic>),
        message: json['message'] as String?,
        statusCode: json['status_code'] as int?,
      );
    }

    final membersList = (json['members'] as List<dynamic>?)
            ?.map((m) => Member.fromJson(m as Map<String, dynamic>))
            .toList() ??
        (json['data'] as List<dynamic>?)
            ?.map((m) => Member.fromJson(m as Map<String, dynamic>))
            .toList() ??
        <Member>[];

    return MembersResponse.success(
      members: membersList,
      total: json['total'] as int?,
      message: json['message'] as String?,
      statusCode: json['status_code'] as int?,
    );
  }

  /// Convert to JSON.
  Map<String, dynamic> toJson() => {
        'success': success,
        'members': members.map((m) => m.toJson()).toList(),
        if (total != null) 'total': total,
        if (error != null) 'error': error!.toJson(),
        if (message != null) 'message': message,
        if (statusCode != null) 'status_code': statusCode,
      };

  @override
  List<Object?> get props => [members, total, success, error, message, statusCode];
}

/// Messages/Chat history API response wrapper.
///
/// Convenient wrapper for API responses containing message history.
class MessagesResponse extends Equatable {
  /// Message history including chat messages and pagination.
  final MessageHistory messageHistory;

  /// Whether the request was successful.
  final bool success;

  /// Error information if request failed.
  final ApiError? error;

  /// Response message.
  final String? message;

  /// HTTP status code.
  final int? statusCode;

  const MessagesResponse({
    required this.messageHistory,
    this.success = true,
    this.error,
    this.message,
    this.statusCode,
  });

  /// Create successful messages response.
  factory MessagesResponse.success({
    required MessageHistory messageHistory,
    String? message,
    int? statusCode,
  }) {
    return MessagesResponse(
      messageHistory: messageHistory,
      success: true,
      message: message,
      statusCode: statusCode ?? 200,
    );
  }

  /// Create failed messages response.
  factory MessagesResponse.error({
    required ApiError error,
    String? message,
    int? statusCode,
  }) {
    return MessagesResponse(
      messageHistory: const MessageHistory(messages: []),
      success: false,
      error: error,
      message: message,
      statusCode: statusCode ?? 500,
    );
  }

  /// Parse from JSON with error handling.
  factory MessagesResponse.fromJson(Map<String, dynamic> json) {
    final isSuccess = json['success'] as bool? ?? true;

    if (!isSuccess && json['error'] != null) {
      return MessagesResponse.error(
        error: ApiError.fromJson(json['error'] as Map<String, dynamic>),
        message: json['message'] as String?,
        statusCode: json['status_code'] as int?,
      );
    }

    // Extract message history from either 'message_history' or 'data' field
    final historyData = json['message_history'] as Map<String, dynamic>? ??
        json['data'] as Map<String, dynamic>?;

    final messageHistory = historyData != null
        ? MessageHistory.fromJson(historyData)
        : const MessageHistory(messages: []);

    return MessagesResponse.success(
      messageHistory: messageHistory,
      message: json['message'] as String?,
      statusCode: json['status_code'] as int?,
    );
  }

  /// Convert to JSON.
  Map<String, dynamic> toJson() => {
        'success': success,
        'message_history': messageHistory.toJson(),
        if (error != null) 'error': error!.toJson(),
        if (message != null) 'message': message,
        if (statusCode != null) 'status_code': statusCode,
      };

  @override
  List<Object?> get props => [messageHistory, success, error, message, statusCode];
}
