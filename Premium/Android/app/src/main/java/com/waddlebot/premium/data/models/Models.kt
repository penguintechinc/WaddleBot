package com.waddlebot.premium.data.models

import android.os.Parcelable
import kotlinx.parcelize.Parcelize
import kotlinx.datetime.Instant

// MARK: - Authentication Models
@Parcelize
data class User(
    val id: String,
    val username: String,
    val email: String,
    val displayName: String,
    val avatar: String? = null,
    val isActive: Boolean,
    val isPremium: Boolean,
    val createdAt: Instant,
    val updatedAt: Instant
) : Parcelable

@Parcelize
data class AuthResponse(
    val token: String,
    val refreshToken: String,
    val user: User,
    val expiresAt: Instant
) : Parcelable

data class LoginRequest(
    val email: String,
    val password: String
)

data class RefreshTokenRequest(
    val refreshToken: String
)

// MARK: - Community Models
@Parcelize
data class Community(
    val id: String,
    val name: String,
    val description: String,
    val platform: String,
    val serverId: String,
    val channelId: String? = null,
    val owner: String,
    val isActive: Boolean,
    val isPublic: Boolean,
    val memberCount: Int,
    val createdAt: Instant,
    val updatedAt: Instant
) : Parcelable

@Parcelize
data class CommunitySettings(
    val communityId: String,
    val autoBanThreshold: Int,
    val autoBanEnabled: Boolean,
    val name: String,
    val description: String,
    val isPublic: Boolean,
    val currencyEnabled: Boolean,
    val currencyName: String,
    val chatMessageReward: Int,
    val eventReward: Int
) : Parcelable

// MARK: - Member Models
@Parcelize
data class Member(
    val id: String,
    val userId: String,
    val communityId: String,
    val username: String,
    val displayName: String,
    val avatar: String? = null,
    val role: String,
    val status: String,
    val reputationScore: Int,
    val currencyBalance: Int,
    val joinDate: Instant,
    val lastActivity: Instant? = null
) : Parcelable

data class MemberUpdate(
    val role: String? = null,
    val status: String? = null,
    val reputationScore: Int? = null,
    val currencyBalance: Int? = null,
    val reason: String? = null
)

// MARK: - Currency Models
@Parcelize
data class CurrencySettings(
    val communityId: String,
    val enabled: Boolean,
    val name: String,
    val chatMessageReward: Int,
    val eventReward: Int
) : Parcelable

@Parcelize
data class CurrencyTransaction(
    val id: String,
    val memberId: String,
    val memberName: String,
    val amount: Int,
    val type: String,
    val source: String,
    val reason: String,
    val timestamp: Instant,
    val metadata: Map<String, String>? = null
) : Parcelable

@Parcelize
data class CurrencyBalance(
    val memberId: String,
    val communityId: String,
    val balance: Int,
    val lastUpdated: Instant
) : Parcelable

@Parcelize
data class CurrencyStatistics(
    val totalCurrency: Int,
    val activeMembers: Int,
    val totalTransactions: Int,
    val averageBalance: Double,
    val topEarners: List<Member>
) : Parcelable

// MARK: - Payment Models
@Parcelize
data class PaymentMethod(
    val id: String,
    val communityId: String,
    val type: String,
    val provider: String,
    val isActive: Boolean,
    val configuration: Map<String, String>,
    val createdAt: Instant
) : Parcelable

@Parcelize
data class PaymentTransaction(
    val id: String,
    val communityId: String,
    val moduleId: String? = null,
    val amount: Double,
    val currency: String,
    val status: String,
    val provider: String,
    val providerTransactionId: String? = null,
    val createdAt: Instant,
    val completedAt: Instant? = null
) : Parcelable

data class PaymentRequest(
    val communityId: String,
    val moduleId: String? = null,
    val amount: Double,
    val currency: String,
    val provider: String,
    val returnUrl: String? = null,
    val cancelUrl: String? = null
)

// MARK: - Raffle Models
@Parcelize
data class Raffle(
    val id: String,
    val communityId: String,
    val title: String,
    val description: String,
    val entryCost: Int,
    val maxEntries: Int,
    val maxWinners: Int,
    val startTime: Instant,
    val endTime: Instant,
    val status: String,
    val createdBy: String,
    val createdAt: Instant,
    val winnersDrawn: Boolean,
    val totalEntries: Int
) : Parcelable

@Parcelize
data class RaffleEntry(
    val id: String,
    val raffleId: String,
    val memberId: String,
    val memberName: String,
    val entryCount: Int,
    val enteredAt: Instant
) : Parcelable

@Parcelize
data class RaffleWinner(
    val id: String,
    val raffleId: String,
    val memberId: String,
    val memberName: String,
    val position: Int,
    val drawnAt: Instant
) : Parcelable

// MARK: - Giveaway Models
@Parcelize
data class Giveaway(
    val id: String,
    val communityId: String,
    val title: String,
    val description: String,
    val entryCost: Int,
    val maxWinners: Int,
    val startTime: Instant,
    val endTime: Instant,
    val status: String,
    val createdBy: String,
    val createdAt: Instant,
    val winnersDrawn: Boolean,
    val totalEntries: Int
) : Parcelable

@Parcelize
data class GiveawayEntry(
    val id: String,
    val giveawayId: String,
    val memberId: String,
    val memberName: String,
    val enteredAt: Instant
) : Parcelable

@Parcelize
data class GiveawayWinner(
    val id: String,
    val giveawayId: String,
    val memberId: String,
    val memberName: String,
    val position: Int,
    val drawnAt: Instant
) : Parcelable

// MARK: - Module Models
@Parcelize
data class Module(
    val id: String,
    val name: String,
    val description: String,
    val version: String,
    val author: String,
    val price: Double? = null,
    val currency: String? = null,
    val category: String,
    val platform: String,
    val isActive: Boolean,
    val downloadCount: Int,
    val rating: Double,
    val reviewCount: Int,
    val createdAt: Instant,
    val updatedAt: Instant
) : Parcelable

@Parcelize
data class ModuleInstallation(
    val id: String,
    val communityId: String,
    val moduleId: String,
    val version: String,
    val isEnabled: Boolean,
    val configuration: Map<String, String>? = null,
    val installedAt: Instant,
    val lastUpdated: Instant
) : Parcelable

// MARK: - Log Models
@Parcelize
data class LogEntry(
    val id: String,
    val communityId: String,
    val action: String,
    val performedBy: String,
    val targetId: String? = null,
    val targetType: String? = null,
    val details: Map<String, String>? = null,
    val timestamp: Instant
) : Parcelable

// MARK: - API Response Models
data class ApiResponse<T>(
    val data: T? = null,
    val message: String? = null,
    val success: Boolean,
    val errors: List<String>? = null
)

data class PaginatedResponse<T>(
    val data: List<T>,
    val pagination: PaginationInfo,
    val message: String? = null,
    val success: Boolean
)

data class PaginationInfo(
    val page: Int,
    val limit: Int,
    val total: Int,
    val totalPages: Int,
    val hasNext: Boolean,
    val hasPrevious: Boolean
)

// MARK: - Error Models
data class ApiError(
    val code: String,
    val message: String,
    val details: Map<String, String>? = null
) : Exception(message)

sealed class NetworkError : Exception() {
    object InvalidUrl : NetworkError()
    object NoData : NetworkError()
    object DecodingError : NetworkError()
    data class NetworkError(val error: Throwable) : com.waddlebot.premium.data.models.NetworkError()
    data class HttpError(val code: Int, val message: String) : com.waddlebot.premium.data.models.NetworkError()
    object Unauthorized : NetworkError()
    object Forbidden : NetworkError()
    object NotFound : NetworkError()
    object ServerError : NetworkError()
    object Timeout : NetworkError()
    object Unknown : NetworkError()
}

// MARK: - Utility Enums
enum class UserRole(val displayName: String, val color: String) {
    OWNER("Owner", "#F44336"),
    ADMIN("Admin", "#FF9800"),
    MODERATOR("Moderator", "#2196F3"),
    MEMBER("Member", "#757575")
}

enum class MemberStatus(val displayName: String, val color: String) {
    ACTIVE("Active", "#4CAF50"),
    INACTIVE("Inactive", "#757575"),
    BANNED("Banned", "#F44336"),
    SUSPENDED("Suspended", "#FF9800")
}

enum class Platform(val displayName: String, val icon: String) {
    TWITCH("Twitch", "📺"),
    DISCORD("Discord", "🎮"),
    SLACK("Slack", "💬")
}

// MARK: - Create Request Models
data class RaffleCreate(
    val title: String,
    val description: String,
    val entryCost: Int,
    val maxEntries: Int,
    val maxWinners: Int,
    val duration: Int
)

data class GiveawayCreate(
    val title: String,
    val description: String,
    val entryCost: Int,
    val maxWinners: Int,
    val duration: Int
)

data class PremiumStatus(
    val isPremium: Boolean,
    val expiresAt: Instant? = null,
    val plan: String? = null
)

// MARK: - Subscription Models
@Parcelize
data class CommunitySubscription(
    val entityId: String,
    val subscriptionType: String,
    val subscriptionStatus: String,
    val subscriptionStart: Instant,
    val subscriptionEnd: Instant,
    val autoRenew: Boolean,
    val paymentMethod: String? = null,
    val amountPaid: Double,
    val currency: String,
    val gracePeriodEnd: Instant? = null,
    val daysRemaining: Int,
    val canInstallPaid: Boolean
) : Parcelable

@Parcelize
data class SubscriptionStatus(
    val hasSubscription: Boolean,
    val subscriptionType: String,
    val subscriptionStatus: String,
    val canInstallPaid: Boolean,
    val expiresAt: Instant? = null,
    val gracePeriodEnd: Instant? = null,
    val daysRemaining: Int,
    val autoRenew: Boolean? = null,
    val paymentMethod: String? = null,
    val amountPaid: Double? = null,
    val currency: String? = null
) : Parcelable

@Parcelize
data class PaymentHistory(
    val id: String,
    val entityId: String,
    val paymentId: String,
    val paymentMethod: String,
    val amount: Double,
    val currency: String,
    val paymentStatus: String,
    val paymentDate: Instant,
    val description: String? = null
) : Parcelable

data class SubscriptionCreateRequest(
    val entityId: String,
    val subscriptionType: String,
    val durationDays: Int,
    val paymentMethod: String? = null,
    val paymentId: String? = null,
    val amountPaid: Double,
    val currency: String = "USD"
)

data class SubscriptionRenewRequest(
    val entityId: String,
    val durationDays: Int,
    val paymentMethod: String? = null,
    val paymentId: String? = null,
    val amountPaid: Double,
    val currency: String = "USD"
)

data class SubscriptionCancelRequest(
    val entityId: String,
    val reason: String? = null
)

data class PaymentRecordRequest(
    val entityId: String,
    val paymentId: String,
    val paymentMethod: String,
    val amount: Double,
    val currency: String = "USD",
    val paymentStatus: String = "completed",
    val description: String? = null,
    val metadata: Map<String, String>? = null
)

data class PaidModuleAccessCheck(
    val entityId: String,
    val modulePrice: Double,
    val canInstall: Boolean,
    val reason: String,
    val message: String? = null,
    val warning: String? = null
)

// MARK: - Enhanced Module Models with Subscription Info
@Parcelize
data class ModuleWithSubscription(
    val id: String,
    val name: String,
    val description: String,
    val version: String,
    val author: String,
    val price: Double,
    val currency: String,
    val category: String,
    val platform: String,
    val isActive: Boolean,
    val downloadCount: Int,
    val rating: Double,
    val reviewCount: Int,
    val subscriptionRequired: Boolean,
    val canInstall: Boolean,
    val accessReason: String,
    val accessMessage: String? = null,
    val createdAt: Instant,
    val updatedAt: Instant
) : Parcelable