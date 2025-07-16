import Foundation

struct APIConfig {
    static let baseURL = "https://api.waddlebot.io"
    static let portalAPIURL = "https://api.waddlebot.io/community"
    static let routerAPIURL = "https://api.waddlebot.io/router"
    static let marketplaceAPIURL = "https://api.waddlebot.io/marketplace"
    static let timeout: TimeInterval = 30.0
    static let retryAttempts = 3
    static let retryDelay: TimeInterval = 1.0
}

struct AppConfig {
    static let appName = "WaddleBot Premium"
    static let appVersion = "1.0.0"
    static let companyName = "WaddleBot"
    static let premiumRequired = true
    static let subscriptionCheckInterval: TimeInterval = 300 // 5 minutes
    static let sessionTimeout: TimeInterval = 3600 // 1 hour
    static let refreshTokenThreshold: TimeInterval = 300 // 5 minutes
}

struct StorageKeys {
    static let userToken = "waddlebot_user_token"
    static let refreshToken = "waddlebot_refresh_token"
    static let userData = "waddlebot_user_data"
    static let premiumStatus = "waddlebot_premium_status"
    static let settings = "waddlebot_settings"
    static let communities = "waddlebot_communities"
    static let lastSync = "waddlebot_last_sync"
}

struct Endpoints {
    // Authentication
    static let login = "/auth/login"
    static let logout = "/auth/logout"
    static let refresh = "/auth/refresh"
    static let verifyPremium = "/auth/verify-premium"
    
    // User Management
    static let userProfile = "/user/profile"
    static let userCommunities = "/user/communities"
    static let userPermissions = "/user/permissions"
    
    // Community Management
    static let communities = "/communities"
    static let communityMembers = "/communities/{id}/members"
    static let communityModules = "/communities/{id}/modules"
    static let communityStats = "/communities/{id}/stats"
    static let communitySettings = "/communities/{id}/settings"
    
    // Currency Management
    static let currencySettings = "/communities/{id}/currency"
    static let currencyBalance = "/communities/{id}/members/{memberId}/currency"
    static let currencyTransactions = "/communities/{id}/currency/transactions"
    static let currencyEarn = "/communities/{id}/currency/earn"
    static let currencySpend = "/communities/{id}/currency/spend"
    
    // Payment Integration
    static let paymentMethods = "/payment/methods"
    static let paymentProcess = "/payment/process"
    static let paymentVerify = "/payment/verify"
    static let paymentHistory = "/payment/history"
    
    // Raffle & Giveaway System
    static let raffles = "/communities/{id}/raffles"
    static let raffleEntries = "/communities/{id}/raffles/{raffleId}/entries"
    static let raffleWinners = "/communities/{id}/raffles/{raffleId}/winners"
    static let giveaways = "/communities/{id}/giveaways"
    static let giveawayEntries = "/communities/{id}/giveaways/{giveawayId}/entries"
    static let giveawayWinners = "/communities/{id}/giveaways/{giveawayId}/winners"
    
    // Health Check
    static let health = "/health"
    static let status = "/status"
}

struct RolePermissions {
    static let owner = ["read", "write", "admin", "manage_members", "manage_modules", "ban_members", "unban_members", "edit_reputation", "view_logs", "manage_currency", "manage_payments", "create_raffles", "create_giveaways"]
    static let admin = ["read", "write", "manage_members", "manage_modules", "ban_members", "unban_members", "edit_reputation", "view_logs", "manage_currency", "manage_payments", "create_raffles", "create_giveaways"]
    static let moderator = ["read", "write", "manage_members", "ban_members", "create_raffles", "create_giveaways"]
    static let member = ["read", "participate_raffles", "participate_giveaways"]
}

struct ReputationConfig {
    static let minScore = 450
    static let maxScore = 850
    static let defaultScore = 650
    static let banScore = 450
    static let minAutoBanThreshold = 451
    static let maxAutoBanThreshold = 850
    static let defaultAutoBanThreshold = 500
}

struct CurrencyConfig {
    static let defaultName = "Credits"
    static let minPrice = 0.01
    static let maxPrice = 999.99
    static let defaultChatReward = 1
    static let defaultEventReward = 5
    static let minChatReward = 0
    static let maxChatReward = 100
    static let minEventReward = 0
    static let maxEventReward = 1000
    static let initialBalance = 0
    static let maxBalance = 1000000
}

struct PaymentConfig {
    static let supportedCurrencies = ["USD", "EUR", "GBP", "CAD", "AUD"]
    static let defaultCurrency = "USD"
    static let minTransaction = 0.50
    static let maxTransaction = 10000.00
}

struct RaffleConfig {
    static let minCost = 1
    static let maxCost = 10000
    static let minDuration = 300 // 5 minutes
    static let maxDuration = 604800 // 7 days
    static let defaultDuration = 3600 // 1 hour
    static let maxEntriesPerUser = 100
    static let minEntriesPerUser = 1
}

struct GiveawayConfig {
    static let minCost = 1
    static let maxCost = 10000
    static let minDuration = 300 // 5 minutes
    static let maxDuration = 604800 // 7 days
    static let defaultDuration = 3600 // 1 hour
    static let maxEntriesPerUser = 1
    static let minEntriesPerUser = 1
}