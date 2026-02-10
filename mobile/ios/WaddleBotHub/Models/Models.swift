import Foundation

// MARK: - User Model

struct User: Codable, Identifiable, Equatable {
    let id: String
    let email: String
    let username: String
    let avatarUrl: String?
    let isSuperAdmin: Bool
    let linkedPlatforms: [String]

    enum CodingKeys: String, CodingKey {
        case id
        case email
        case username
        case avatarUrl = "avatar_url"
        case isSuperAdmin = "is_super_admin"
        case linkedPlatforms = "linked_platforms"
    }
}

// MARK: - Community Model

struct Community: Codable, Identifiable, Equatable {
    let id: String
    let name: String
    let description: String?
    let iconUrl: String?
    let memberCount: Int
    let isOwner: Bool
    let role: String
    let createdAt: Date?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case description
        case iconUrl = "icon_url"
        case memberCount = "member_count"
        case isOwner = "is_owner"
        case role
        case createdAt = "created_at"
    }
}

// MARK: - Member Model

struct Member: Codable, Identifiable, Equatable {
    let id: String
    let userId: String
    let username: String
    let displayName: String?
    let avatarUrl: String?
    let role: String
    let joinedAt: Date?
    let isOnline: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case username
        case displayName = "display_name"
        case avatarUrl = "avatar_url"
        case role
        case joinedAt = "joined_at"
        case isOnline = "is_online"
    }
}

// MARK: - Dashboard Model

struct CommunityDashboard: Codable, Equatable {
    let communityId: String
    let totalMembers: Int
    let activeMembers: Int
    let totalCommands: Int
    let commandsToday: Int
    let connectedPlatforms: [String]
    let recentActivity: [ActivityItem]

    enum CodingKeys: String, CodingKey {
        case communityId = "community_id"
        case totalMembers = "total_members"
        case activeMembers = "active_members"
        case totalCommands = "total_commands"
        case commandsToday = "commands_today"
        case connectedPlatforms = "connected_platforms"
        case recentActivity = "recent_activity"
    }
}

struct ActivityItem: Codable, Identifiable, Equatable {
    let id: String
    let type: String
    let message: String
    let timestamp: Date?
    let userId: String?

    enum CodingKeys: String, CodingKey {
        case id
        case type
        case message
        case timestamp
        case userId = "user_id"
    }
}

// MARK: - Auth Request/Response Models

struct LoginRequest: Codable {
    let email: String
    let password: String
}

struct LoginResponse: Codable {
    let success: Bool
    let token: String?
    let user: User?
    let message: String?
}

struct RefreshResponse: Codable {
    let success: Bool
    let token: String?
    let message: String?
}

struct LogoutResponse: Codable {
    let success: Bool
    let message: String?
}

// MARK: - User Response (includes communities)

struct UserResponse: Codable {
    let success: Bool
    let user: User?
    let communities: [Community]?
    let message: String?
}

// MARK: - Generic API Response Wrapper

struct ApiResponse<T: Codable>: Codable {
    let success: Bool
    let data: T?
    let message: String?
    let error: String?
}

// MARK: - Community List Response

struct CommunitiesResponse: Codable {
    let success: Bool
    let communities: [Community]?
    let message: String?
}

// MARK: - Members List Response

struct MembersResponse: Codable {
    let success: Bool
    let members: [Member]?
    let total: Int?
    let page: Int?
    let pageSize: Int?
    let message: String?

    enum CodingKeys: String, CodingKey {
        case success
        case members
        case total
        case page
        case pageSize = "page_size"
        case message
    }
}

// MARK: - Dashboard Response

struct DashboardResponse: Codable {
    let success: Bool
    let dashboard: CommunityDashboard?
    let message: String?
}
