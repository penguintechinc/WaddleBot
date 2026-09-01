/// Member models for Flutter Gazer application.
/// Includes role-based access control (RBAC) and member hierarchy.
library;

import 'package:equatable/equatable.dart';

/// Enum defining member roles with hierarchical permissions.
enum MemberRole {
  owner,
  admin,
  maintainer,
  member,
  viewer,
}

/// Helper class for permission constants and RBAC operations.
class Permission {
  // Read permissions
  static const String readCommunity = 'read:community';
  static const String readMembers = 'read:members';
  static const String readContent = 'read:content';
  static const String readAnalytics = 'read:analytics';

  // Write permissions
  static const String writeCommunity = 'write:community';
  static const String writeMembers = 'write:members';
  static const String writeContent = 'write:content';

  // Admin permissions
  static const String deleteMembers = 'delete:members';
  static const String manageCommunity = 'manage:community';
  static const String manageRoles = 'manage:roles';
  static const String viewAuditLog = 'view:audit_log';

  // Owner permissions
  static const String deleteContent = 'delete:content';
  static const String deleteCommunity = 'delete:community';
  static const String transferOwnership = 'transfer:ownership';

  /// Get all permissions for a given role.
  static List<String> getPermissionsForRole(MemberRole role) {
    switch (role) {
      case MemberRole.owner:
        return [
          readCommunity,
          readMembers,
          readContent,
          readAnalytics,
          writeCommunity,
          writeMembers,
          writeContent,
          deleteMembers,
          manageCommunity,
          manageRoles,
          viewAuditLog,
          deleteContent,
          deleteCommunity,
          transferOwnership,
        ];
      case MemberRole.admin:
        return [
          readCommunity,
          readMembers,
          readContent,
          readAnalytics,
          writeCommunity,
          writeMembers,
          writeContent,
          deleteMembers,
          manageCommunity,
          manageRoles,
          viewAuditLog,
        ];
      case MemberRole.maintainer:
        return [
          readCommunity,
          readMembers,
          readContent,
          readAnalytics,
          writeMembers,
          writeContent,
        ];
      case MemberRole.member:
        return [
          readCommunity,
          readMembers,
          readContent,
          writeContent,
        ];
      case MemberRole.viewer:
        return [
          readCommunity,
          readMembers,
          readContent,
        ];
    }
  }

  /// Check if a role has a specific permission.
  static bool hasPermission(MemberRole role, String permission) {
    return getPermissionsForRole(role).contains(permission);
  }

  /// Get role display name.
  static String getRoleDisplayName(MemberRole role) {
    switch (role) {
      case MemberRole.owner:
        return 'Owner';
      case MemberRole.admin:
        return 'Admin';
      case MemberRole.maintainer:
        return 'Maintainer';
      case MemberRole.member:
        return 'Member';
      case MemberRole.viewer:
        return 'Viewer';
    }
  }
}

/// Base member model representing a community member.
class Member extends Equatable {
  final String id;
  final String userId;
  final String communityId;
  final String username;
  final String displayName;
  final String? avatarUrl;
  final MemberRole role;
  final DateTime joinedAt;
  final int reputationScore;
  final bool? isOnline;

  const Member({
    required this.id,
    required this.userId,
    required this.communityId,
    required this.username,
    required this.displayName,
    this.avatarUrl,
    required this.role,
    required this.joinedAt,
    required this.reputationScore,
    this.isOnline,
  });

  /// Create a Member from JSON.
  factory Member.fromJson(Map<String, dynamic> json) {
    return Member(
      id: json['id'] as String? ?? '',
      userId: json['userId'] as String? ?? '',
      communityId: json['communityId'] as String? ?? '',
      username: json['username'] as String? ?? '',
      displayName: json['displayName'] as String? ?? '',
      avatarUrl: json['avatarUrl'] as String?,
      role: _parseRole(json['role']),
      joinedAt: _parseDateTime(json['joinedAt']),
      reputationScore: json['reputationScore'] as int? ?? 0,
      isOnline: json['isOnline'] as bool?,
    );
  }

  /// Convert Member to JSON.
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'userId': userId,
      'communityId': communityId,
      'username': username,
      'displayName': displayName,
      'avatarUrl': avatarUrl,
      'role': role.toString().split('.').last,
      'joinedAt': joinedAt.toIso8601String(),
      'reputationScore': reputationScore,
      'isOnline': isOnline,
    };
  }

  /// Create a copy of this member with modified fields.
  Member copyWith({
    String? id,
    String? userId,
    String? communityId,
    String? username,
    String? displayName,
    String? avatarUrl,
    MemberRole? role,
    DateTime? joinedAt,
    int? reputationScore,
    bool? isOnline,
  }) {
    return Member(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      communityId: communityId ?? this.communityId,
      username: username ?? this.username,
      displayName: displayName ?? this.displayName,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      role: role ?? this.role,
      joinedAt: joinedAt ?? this.joinedAt,
      reputationScore: reputationScore ?? this.reputationScore,
      isOnline: isOnline ?? this.isOnline,
    );
  }

  /// Check if this member has a specific permission.
  bool hasPermission(String permission) {
    return Permission.hasPermission(role, permission);
  }

  /// Get all permissions for this member's role.
  List<String> getPermissions() {
    return Permission.getPermissionsForRole(role);
  }

  /// Get role display name.
  String getRoleDisplayName() {
    return Permission.getRoleDisplayName(role);
  }

  /// Check if member can manage other members.
  bool canManageMembers() {
    return hasPermission(Permission.manageRoles);
  }

  /// Check if member can manage community settings.
  bool canManageCommunity() {
    return hasPermission(Permission.manageCommunity);
  }

  /// Check if member is an owner or admin.
  bool isAdmin() {
    return role == MemberRole.owner || role == MemberRole.admin;
  }

  @override
  List<Object?> get props => [
        id,
        userId,
        communityId,
        username,
        displayName,
        avatarUrl,
        role,
        joinedAt,
        reputationScore,
        isOnline,
      ];
}

/// Extended member model with detailed information.
class MemberDetail extends Member {
  final List<String> permissions;
  final List<String> badges;
  final DateTime? lastActive;

  const MemberDetail({
    required super.id,
    required super.userId,
    required super.communityId,
    required super.username,
    required super.displayName,
    super.avatarUrl,
    required super.role,
    required super.joinedAt,
    required super.reputationScore,
    super.isOnline,
    required this.permissions,
    required this.badges,
    this.lastActive,
  });

  /// Create a MemberDetail from JSON.
  factory MemberDetail.fromJson(Map<String, dynamic> json) {
    final baseMember = Member.fromJson(json);
    return MemberDetail(
      id: baseMember.id,
      userId: baseMember.userId,
      communityId: baseMember.communityId,
      username: baseMember.username,
      displayName: baseMember.displayName,
      avatarUrl: baseMember.avatarUrl,
      role: baseMember.role,
      joinedAt: baseMember.joinedAt,
      reputationScore: baseMember.reputationScore,
      isOnline: baseMember.isOnline,
      permissions: _parseStringList(json['permissions']),
      badges: _parseStringList(json['badges']),
      lastActive: json['lastActive'] != null
          ? _parseDateTime(json['lastActive'])
          : null,
    );
  }

  /// Convert MemberDetail to JSON.
  @override
  Map<String, dynamic> toJson() {
    final baseJson = super.toJson();
    return {
      ...baseJson,
      'permissions': permissions,
      'badges': badges,
      'lastActive': lastActive?.toIso8601String(),
    };
  }

  /// Create a copy of this member detail with modified fields.
  @override
  MemberDetail copyWith({
    String? id,
    String? userId,
    String? communityId,
    String? username,
    String? displayName,
    String? avatarUrl,
    MemberRole? role,
    DateTime? joinedAt,
    int? reputationScore,
    bool? isOnline,
    List<String>? permissions,
    List<String>? badges,
    DateTime? lastActive,
  }) {
    return MemberDetail(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      communityId: communityId ?? this.communityId,
      username: username ?? this.username,
      displayName: displayName ?? this.displayName,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      role: role ?? this.role,
      joinedAt: joinedAt ?? this.joinedAt,
      reputationScore: reputationScore ?? this.reputationScore,
      isOnline: isOnline ?? this.isOnline,
      permissions: permissions ?? this.permissions,
      badges: badges ?? this.badges,
      lastActive: lastActive ?? this.lastActive,
    );
  }

  /// Check if member has a specific badge.
  bool hasBadge(String badge) {
    return badges.contains(badge);
  }

  /// Get member status based on online state and last activity.
  String getStatus() {
    if (isOnline == true) {
      return 'Online';
    }
    if (lastActive != null) {
      final now = DateTime.now();
      final diff = now.difference(lastActive!);
      if (diff.inMinutes < 5) {
        return 'Recently active';
      } else if (diff.inHours < 1) {
        return 'Active ${diff.inMinutes}m ago';
      } else if (diff.inDays < 1) {
        return 'Active ${diff.inHours}h ago';
      } else {
        return 'Active ${diff.inDays}d ago';
      }
    }
    return 'Offline';
  }

  @override
  List<Object?> get props => [
        ...super.props,
        permissions,
        badges,
        lastActive,
      ];
}

/// Helper function to parse MemberRole from string or int.
MemberRole _parseRole(dynamic value) {
  if (value == null) return MemberRole.viewer;
  if (value is String) {
    return MemberRole.values.firstWhere(
      (role) => role.toString().split('.').last == value.toLowerCase(),
      orElse: () => MemberRole.viewer,
    );
  }
  if (value is int) {
    return MemberRole.values.asMap()[value] ?? MemberRole.viewer;
  }
  return MemberRole.viewer;
}

/// Helper function to parse DateTime safely.
DateTime _parseDateTime(dynamic value) {
  if (value == null) return DateTime.now();
  if (value is DateTime) return value;
  if (value is String) {
    try {
      return DateTime.parse(value);
    } catch (e) {
      return DateTime.now();
    }
  }
  return DateTime.now();
}

/// Helper function to parse List<String> from dynamic value.
List<String> _parseStringList(dynamic value) {
  if (value == null) return [];
  if (value is List) {
    return value.map((e) => e.toString()).toList();
  }
  return [];
}
