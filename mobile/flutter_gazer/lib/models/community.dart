/// Activity type enum for community activity tracking.
enum ActivityType {
  memberJoined,
  memberLeft,
  messagePosted,
  commandExecuted,
  workflowTriggered;

  /// Convert enum to string representation.
  String toJson() => toString().split('.').last;

  /// Create enum from string representation.
  static ActivityType fromJson(String value) {
    return ActivityType.values.firstWhere(
      (e) => e.toJson() == value,
      orElse: () => ActivityType.messagePosted,
    );
  }
}

/// Represents a single activity item in a community.
class ActivityItem {
  final String id;
  final ActivityType type;
  final String description;
  final DateTime timestamp;
  final String userName;
  final String? userId;

  const ActivityItem({
    required this.id,
    required this.type,
    required this.description,
    required this.timestamp,
    required this.userName,
    this.userId,
  });

  factory ActivityItem.fromJson(Map<String, dynamic> json) {
    return ActivityItem(
      id: json['id'] as String? ?? '',
      type: ActivityType.fromJson(json['type'] as String? ?? 'messagePosted'),
      description: json['description'] as String? ?? '',
      timestamp: DateTime.tryParse(json['timestamp'] as String? ?? '') ??
          DateTime.now(),
      userName: json['user_name'] as String? ?? 'Unknown',
      userId: json['user_id'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'type': type.toJson(),
        'description': description,
        'timestamp': timestamp.toIso8601String(),
        'user_name': userName,
        if (userId != null) 'user_id': userId,
      };

  ActivityItem copyWith({
    String? id,
    ActivityType? type,
    String? description,
    DateTime? timestamp,
    String? userName,
    String? userId,
  }) {
    return ActivityItem(
      id: id ?? this.id,
      type: type ?? this.type,
      description: description ?? this.description,
      timestamp: timestamp ?? this.timestamp,
      userName: userName ?? this.userName,
      userId: userId ?? this.userId,
    );
  }
}

/// Community statistics.
class CommunityStats {
  final int memberCount;
  final int activeMembers;
  final int commandsToday;
  final int messagesToday;

  const CommunityStats({
    required this.memberCount,
    required this.activeMembers,
    required this.commandsToday,
    required this.messagesToday,
  });

  factory CommunityStats.fromJson(Map<String, dynamic> json) {
    return CommunityStats(
      memberCount: json['member_count'] as int? ?? 0,
      activeMembers: json['active_members'] as int? ?? 0,
      commandsToday: json['commands_today'] as int? ?? 0,
      messagesToday: json['messages_today'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'member_count': memberCount,
        'active_members': activeMembers,
        'commands_today': commandsToday,
        'messages_today': messagesToday,
      };

  CommunityStats copyWith({
    int? memberCount,
    int? activeMembers,
    int? commandsToday,
    int? messagesToday,
  }) {
    return CommunityStats(
      memberCount: memberCount ?? this.memberCount,
      activeMembers: activeMembers ?? this.activeMembers,
      commandsToday: commandsToday ?? this.commandsToday,
      messagesToday: messagesToday ?? this.messagesToday,
    );
  }
}

/// Basic community model.
class Community {
  final String id;
  final String name;
  final String description;
  final String? avatarUrl;
  final int memberCount;
  final String ownerId;
  final DateTime createdAt;
  final DateTime updatedAt;

  const Community({
    required this.id,
    required this.name,
    required this.description,
    this.avatarUrl,
    required this.memberCount,
    required this.ownerId,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Community.fromJson(Map<String, dynamic> json) {
    return Community(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      avatarUrl: json['avatar_url'] as String?,
      memberCount: json['member_count'] as int? ?? 0,
      ownerId: json['owner_id'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ??
          DateTime.now(),
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? '') ??
          DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'description': description,
        if (avatarUrl != null) 'avatar_url': avatarUrl,
        'member_count': memberCount,
        'owner_id': ownerId,
        'created_at': createdAt.toIso8601String(),
        'updated_at': updatedAt.toIso8601String(),
      };

  Community copyWith({
    String? id,
    String? name,
    String? description,
    String? avatarUrl,
    int? memberCount,
    String? ownerId,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Community(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      memberCount: memberCount ?? this.memberCount,
      ownerId: ownerId ?? this.ownerId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}

/// Detailed community model with stats and recent activity.
class CommunityDetail extends Community {
  final CommunityStats stats;
  final List<ActivityItem> recentActivity;

  const CommunityDetail({
    required super.id,
    required super.name,
    required super.description,
    super.avatarUrl,
    required super.memberCount,
    required super.ownerId,
    required super.createdAt,
    required super.updatedAt,
    required this.stats,
    required this.recentActivity,
  });

  factory CommunityDetail.fromJson(Map<String, dynamic> json) {
    return CommunityDetail(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      avatarUrl: json['avatar_url'] as String?,
      memberCount: json['member_count'] as int? ?? 0,
      ownerId: json['owner_id'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ??
          DateTime.now(),
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? '') ??
          DateTime.now(),
      stats: CommunityStats.fromJson(
          json['stats'] as Map<String, dynamic>? ?? {}),
      recentActivity: (json['recent_activity'] as List<dynamic>?)
              ?.map((e) =>
                  ActivityItem.fromJson(e as Map<String, dynamic>? ?? {}))
              .toList() ??
          [],
    );
  }

  @override
  Map<String, dynamic> toJson() => {
        ...super.toJson(),
        'stats': stats.toJson(),
        'recent_activity': recentActivity.map((e) => e.toJson()).toList(),
      };

  @override
  CommunityDetail copyWith({
    String? id,
    String? name,
    String? description,
    String? avatarUrl,
    int? memberCount,
    String? ownerId,
    DateTime? createdAt,
    DateTime? updatedAt,
    CommunityStats? stats,
    List<ActivityItem>? recentActivity,
  }) {
    return CommunityDetail(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      memberCount: memberCount ?? this.memberCount,
      ownerId: ownerId ?? this.ownerId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      stats: stats ?? this.stats,
      recentActivity: recentActivity ?? this.recentActivity,
    );
  }
}
