import Foundation

// MARK: - Authentication Models
struct User: Codable, Identifiable {
    let id: String
    let username: String
    let email: String
    let displayName: String
    let avatar: String?
    let isActive: Bool
    let isPremium: Bool
    let createdAt: Date
    let updatedAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, username, email, avatar, createdAt, updatedAt
        case displayName = "display_name"
        case isActive = "is_active"
        case isPremium = "is_premium"
    }
}

struct AuthResponse: Codable {
    let token: String
    let refreshToken: String
    let user: User
    let expiresAt: Date
    
    enum CodingKeys: String, CodingKey {
        case token, user
        case refreshToken = "refresh_token"
        case expiresAt = "expires_at"
    }
}

struct LoginRequest: Codable {
    let email: String
    let password: String
}

struct RefreshTokenRequest: Codable {
    let refreshToken: String
    
    enum CodingKeys: String, CodingKey {
        case refreshToken = "refresh_token"
    }
}

// MARK: - Community Models
struct Community: Codable, Identifiable {
    let id: String
    let name: String
    let description: String
    let platform: String
    let serverId: String
    let channelId: String?
    let owner: String
    let isActive: Bool
    let isPublic: Bool
    let memberCount: Int
    let createdAt: Date
    let updatedAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, name, description, platform, owner, createdAt, updatedAt
        case serverId = "server_id"
        case channelId = "channel_id"
        case isActive = "is_active"
        case isPublic = "is_public"
        case memberCount = "member_count"
    }
}

struct CommunitySettings: Codable {
    let communityId: String
    let autoBanThreshold: Int
    let autoBanEnabled: Bool
    let name: String
    let description: String
    let isPublic: Bool
    let currencyEnabled: Bool
    let currencyName: String
    let chatMessageReward: Int
    let eventReward: Int
    
    enum CodingKeys: String, CodingKey {
        case name, description
        case communityId = "community_id"
        case autoBanThreshold = "auto_ban_threshold"
        case autoBanEnabled = "auto_ban_enabled"
        case isPublic = "is_public"
        case currencyEnabled = "currency_enabled"
        case currencyName = "currency_name"
        case chatMessageReward = "chat_message_reward"
        case eventReward = "event_reward"
    }
}

// MARK: - Member Models
struct Member: Codable, Identifiable {
    let id: String
    let userId: String
    let communityId: String
    let username: String
    let displayName: String
    let avatar: String?
    let role: String
    let status: String
    let reputationScore: Int
    let currencyBalance: Int
    let joinDate: Date
    let lastActivity: Date?
    
    enum CodingKeys: String, CodingKey {
        case id, username, avatar, role, status
        case userId = "user_id"
        case communityId = "community_id"
        case displayName = "display_name"
        case reputationScore = "reputation_score"
        case currencyBalance = "currency_balance"
        case joinDate = "join_date"
        case lastActivity = "last_activity"
    }
}

struct MemberUpdate: Codable {
    let role: String?
    let status: String?
    let reputationScore: Int?
    let currencyBalance: Int?
    let reason: String?
    
    enum CodingKeys: String, CodingKey {
        case role, status, reason
        case reputationScore = "reputation_score"
        case currencyBalance = "currency_balance"
    }
}

// MARK: - Currency Models
struct CurrencySettings: Codable {
    let communityId: String
    let enabled: Bool
    let name: String
    let chatMessageReward: Int
    let eventReward: Int
    
    enum CodingKeys: String, CodingKey {
        case enabled, name
        case communityId = "community_id"
        case chatMessageReward = "chat_message_reward"
        case eventReward = "event_reward"
    }
}

struct CurrencyTransaction: Codable, Identifiable {
    let id: String
    let memberId: String
    let memberName: String
    let amount: Int
    let type: String
    let source: String
    let reason: String
    let timestamp: Date
    let metadata: [String: String]?
    
    enum CodingKeys: String, CodingKey {
        case id, amount, type, source, reason, timestamp, metadata
        case memberId = "member_id"
        case memberName = "member_name"
    }
}

struct CurrencyBalance: Codable {
    let memberId: String
    let communityId: String
    let balance: Int
    let lastUpdated: Date
    
    enum CodingKeys: String, CodingKey {
        case balance
        case memberId = "member_id"
        case communityId = "community_id"
        case lastUpdated = "last_updated"
    }
}

struct CurrencyStatistics: Codable {
    let totalCurrency: Int
    let activeMembers: Int
    let totalTransactions: Int
    let averageBalance: Double
    let topEarners: [Member]
    
    enum CodingKeys: String, CodingKey {
        case activeMembers, totalTransactions, averageBalance, topEarners
        case totalCurrency = "total_currency"
    }
}

// MARK: - Payment Models
struct PaymentMethod: Codable, Identifiable {
    let id: String
    let communityId: String
    let type: String
    let provider: String
    let isActive: Bool
    let configuration: [String: String]
    let createdAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, type, provider, configuration, createdAt
        case communityId = "community_id"
        case isActive = "is_active"
    }
}

struct PaymentTransaction: Codable, Identifiable {
    let id: String
    let communityId: String
    let moduleId: String?
    let amount: Double
    let currency: String
    let status: String
    let provider: String
    let providerTransactionId: String?
    let createdAt: Date
    let completedAt: Date?
    
    enum CodingKeys: String, CodingKey {
        case id, amount, currency, status, provider, createdAt, completedAt
        case communityId = "community_id"
        case moduleId = "module_id"
        case providerTransactionId = "provider_transaction_id"
    }
}

struct PaymentRequest: Codable {
    let communityId: String
    let moduleId: String?
    let amount: Double
    let currency: String
    let provider: String
    let returnUrl: String?
    let cancelUrl: String?
    
    enum CodingKeys: String, CodingKey {
        case amount, currency, provider, returnUrl, cancelUrl
        case communityId = "community_id"
        case moduleId = "module_id"
    }
}

// MARK: - Raffle Models
struct Raffle: Codable, Identifiable {
    let id: String
    let communityId: String
    let title: String
    let description: String
    let entryCost: Int
    let maxEntries: Int
    let maxWinners: Int
    let startTime: Date
    let endTime: Date
    let status: String
    let createdBy: String
    let createdAt: Date
    let winnersDrawn: Bool
    let totalEntries: Int
    
    enum CodingKeys: String, CodingKey {
        case id, title, description, status, createdBy, createdAt, winnersDrawn, totalEntries
        case communityId = "community_id"
        case entryCost = "entry_cost"
        case maxEntries = "max_entries"
        case maxWinners = "max_winners"
        case startTime = "start_time"
        case endTime = "end_time"
    }
}

struct RaffleEntry: Codable, Identifiable {
    let id: String
    let raffleId: String
    let memberId: String
    let memberName: String
    let entryCount: Int
    let enteredAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, entryCount, enteredAt
        case raffleId = "raffle_id"
        case memberId = "member_id"
        case memberName = "member_name"
    }
}

struct RaffleWinner: Codable, Identifiable {
    let id: String
    let raffleId: String
    let memberId: String
    let memberName: String
    let position: Int
    let drawnAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, position, drawnAt
        case raffleId = "raffle_id"
        case memberId = "member_id"
        case memberName = "member_name"
    }
}

// MARK: - Giveaway Models
struct Giveaway: Codable, Identifiable {
    let id: String
    let communityId: String
    let title: String
    let description: String
    let entryCost: Int
    let maxWinners: Int
    let startTime: Date
    let endTime: Date
    let status: String
    let createdBy: String
    let createdAt: Date
    let winnersDrawn: Bool
    let totalEntries: Int
    
    enum CodingKeys: String, CodingKey {
        case id, title, description, status, createdBy, createdAt, winnersDrawn, totalEntries
        case communityId = "community_id"
        case entryCost = "entry_cost"
        case maxWinners = "max_winners"
        case startTime = "start_time"
        case endTime = "end_time"
    }
}

struct GiveawayEntry: Codable, Identifiable {
    let id: String
    let giveawayId: String
    let memberId: String
    let memberName: String
    let enteredAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, enteredAt
        case giveawayId = "giveaway_id"
        case memberId = "member_id"
        case memberName = "member_name"
    }
}

struct GiveawayWinner: Codable, Identifiable {
    let id: String
    let giveawayId: String
    let memberId: String
    let memberName: String
    let position: Int
    let drawnAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, position, drawnAt
        case giveawayId = "giveaway_id"
        case memberId = "member_id"
        case memberName = "member_name"
    }
}

// MARK: - Module Models
struct Module: Codable, Identifiable {
    let id: String
    let name: String
    let description: String
    let version: String
    let author: String
    let price: Double?
    let currency: String?
    let category: String
    let platform: String
    let isActive: Bool
    let downloadCount: Int
    let rating: Double
    let reviewCount: Int
    let createdAt: Date
    let updatedAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, name, description, version, author, price, currency, category, platform, rating, createdAt, updatedAt
        case isActive = "is_active"
        case downloadCount = "download_count"
        case reviewCount = "review_count"
    }
}

struct ModuleInstallation: Codable, Identifiable {
    let id: String
    let communityId: String
    let moduleId: String
    let version: String
    let isEnabled: Bool
    let configuration: [String: String]?
    let installedAt: Date
    let lastUpdated: Date
    
    enum CodingKeys: String, CodingKey {
        case id, version, configuration, installedAt, lastUpdated
        case communityId = "community_id"
        case moduleId = "module_id"
        case isEnabled = "is_enabled"
    }
}

// MARK: - Log Models
struct LogEntry: Codable, Identifiable {
    let id: String
    let communityId: String
    let action: String
    let performedBy: String
    let targetId: String?
    let targetType: String?
    let details: [String: String]?
    let timestamp: Date
    
    enum CodingKeys: String, CodingKey {
        case id, action, performedBy, details, timestamp
        case communityId = "community_id"
        case targetId = "target_id"
        case targetType = "target_type"
    }
}

// MARK: - API Response Models
struct APIResponse<T: Codable>: Codable {
    let data: T?
    let message: String?
    let success: Bool
    let errors: [String]?
}

struct PaginatedResponse<T: Codable>: Codable {
    let data: [T]
    let pagination: PaginationInfo
    let message: String?
    let success: Bool
}

struct PaginationInfo: Codable {
    let page: Int
    let limit: Int
    let total: Int
    let totalPages: Int
    let hasNext: Bool
    let hasPrevious: Bool
    
    enum CodingKeys: String, CodingKey {
        case page, limit, total, hasNext, hasPrevious
        case totalPages = "total_pages"
    }
}

// MARK: - Error Models
struct APIError: Codable, Error {
    let code: String
    let message: String
    let details: [String: String]?
}

enum NetworkError: Error {
    case invalidURL
    case noData
    case decodingError
    case networkError(Error)
    case httpError(Int, String)
    case unauthorized
    case forbidden
    case notFound
    case serverError
    case timeout
    case unknown
}

// MARK: - Utility Enums
enum UserRole: String, CaseIterable {
    case owner = "owner"
    case admin = "admin"
    case moderator = "moderator"
    case member = "member"
    
    var displayName: String {
        return self.rawValue.capitalized
    }
    
    var color: String {
        switch self {
        case .owner: return "#F44336"
        case .admin: return "#FF9800"
        case .moderator: return "#2196F3"
        case .member: return "#757575"
        }
    }
}

enum MemberStatus: String, CaseIterable {
    case active = "active"
    case inactive = "inactive"
    case banned = "banned"
    case suspended = "suspended"
    
    var displayName: String {
        return self.rawValue.capitalized
    }
    
    var color: String {
        switch self {
        case .active: return "#4CAF50"
        case .inactive: return "#757575"
        case .banned: return "#F44336"
        case .suspended: return "#FF9800"
        }
    }
}

enum Platform: String, CaseIterable {
    case twitch = "twitch"
    case discord = "discord"
    case slack = "slack"
    
    var displayName: String {
        return self.rawValue.capitalized
    }
    
    var icon: String {
        switch self {
        case .twitch: return "📺"
        case .discord: return "🎮"
        case .slack: return "💬"
        }
    }
}

// MARK: - Subscription Models
struct CommunitySubscription: Codable, Identifiable {
    let id: String
    let entityId: String
    let subscriptionType: String
    let subscriptionStatus: String
    let subscriptionStart: Date
    let subscriptionEnd: Date
    let autoRenew: Bool
    let paymentMethod: String?
    let amountPaid: Double
    let currency: String
    let gracePeriodEnd: Date?
    let daysRemaining: Int
    let canInstallPaid: Bool
    
    enum CodingKeys: String, CodingKey {
        case id, currency, daysRemaining
        case entityId = "entity_id"
        case subscriptionType = "subscription_type"
        case subscriptionStatus = "subscription_status"
        case subscriptionStart = "subscription_start"
        case subscriptionEnd = "subscription_end"
        case autoRenew = "auto_renew"
        case paymentMethod = "payment_method"
        case amountPaid = "amount_paid"
        case gracePeriodEnd = "grace_period_end"
        case canInstallPaid = "can_install_paid"
    }
}

struct SubscriptionStatus: Codable {
    let hasSubscription: Bool
    let subscriptionType: String
    let subscriptionStatus: String
    let canInstallPaid: Bool
    let expiresAt: Date?
    let gracePeriodEnd: Date?
    let daysRemaining: Int
    let autoRenew: Bool?
    let paymentMethod: String?
    let amountPaid: Double?
    let currency: String?
    
    enum CodingKeys: String, CodingKey {
        case currency, daysRemaining
        case hasSubscription = "has_subscription"
        case subscriptionType = "subscription_type"
        case subscriptionStatus = "subscription_status"
        case canInstallPaid = "can_install_paid"
        case expiresAt = "expires_at"
        case gracePeriodEnd = "grace_period_end"
        case autoRenew = "auto_renew"
        case paymentMethod = "payment_method"
        case amountPaid = "amount_paid"
    }
}

struct PaymentHistory: Codable, Identifiable {
    let id: String
    let entityId: String
    let paymentId: String
    let paymentMethod: String
    let amount: Double
    let currency: String
    let paymentStatus: String
    let paymentDate: Date
    let description: String?
    
    enum CodingKeys: String, CodingKey {
        case id, amount, currency, description
        case entityId = "entity_id"
        case paymentId = "payment_id"
        case paymentMethod = "payment_method"
        case paymentStatus = "payment_status"
        case paymentDate = "payment_date"
    }
}

struct SubscriptionCreateRequest: Codable {
    let entityId: String
    let subscriptionType: String
    let durationDays: Int
    let paymentMethod: String?
    let paymentId: String?
    let amountPaid: Double
    let currency: String
    
    enum CodingKeys: String, CodingKey {
        case currency
        case entityId = "entity_id"
        case subscriptionType = "subscription_type"
        case durationDays = "duration_days"
        case paymentMethod = "payment_method"
        case paymentId = "payment_id"
        case amountPaid = "amount_paid"
    }
}

struct SubscriptionRenewRequest: Codable {
    let entityId: String
    let durationDays: Int
    let paymentMethod: String?
    let paymentId: String?
    let amountPaid: Double
    let currency: String
    
    enum CodingKeys: String, CodingKey {
        case currency
        case entityId = "entity_id"
        case durationDays = "duration_days"
        case paymentMethod = "payment_method"
        case paymentId = "payment_id"
        case amountPaid = "amount_paid"
    }
}

struct SubscriptionCancelRequest: Codable {
    let entityId: String
    let reason: String?
    
    enum CodingKeys: String, CodingKey {
        case reason
        case entityId = "entity_id"
    }
}

struct PaymentRecordRequest: Codable {
    let entityId: String
    let paymentId: String
    let paymentMethod: String
    let amount: Double
    let currency: String
    let paymentStatus: String
    let description: String?
    let metadata: [String: String]?
    
    enum CodingKeys: String, CodingKey {
        case amount, currency, description, metadata
        case entityId = "entity_id"
        case paymentId = "payment_id"
        case paymentMethod = "payment_method"
        case paymentStatus = "payment_status"
    }
}

struct PaidModuleAccessCheck: Codable {
    let entityId: String
    let modulePrice: Double
    let canInstall: Bool
    let reason: String
    let message: String?
    let warning: String?
    
    enum CodingKeys: String, CodingKey {
        case reason, message, warning
        case entityId = "entity_id"
        case modulePrice = "module_price"
        case canInstall = "can_install"
    }
}

// MARK: - Enhanced Module Models with Subscription Info
struct ModuleWithSubscription: Codable, Identifiable {
    let id: String
    let name: String
    let description: String
    let version: String
    let author: String
    let price: Double
    let currency: String
    let category: String
    let platform: String
    let isActive: Bool
    let downloadCount: Int
    let rating: Double
    let reviewCount: Int
    let subscriptionRequired: Bool
    let canInstall: Bool
    let accessReason: String
    let accessMessage: String?
    let createdAt: Date
    let updatedAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, name, description, version, author, price, currency, category, platform, rating, createdAt, updatedAt
        case isActive = "is_active"
        case downloadCount = "download_count"
        case reviewCount = "review_count"
        case subscriptionRequired = "subscription_required"
        case canInstall = "can_install"
        case accessReason = "access_reason"
        case accessMessage = "access_message"
    }
}