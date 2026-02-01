package io.waddlebot.hub.data.models

import com.google.gson.annotations.SerializedName

data class User(
    val id: String,
    val email: String,
    val username: String,
    @SerializedName("avatar_url")
    val avatarUrl: String? = null,
    @SerializedName("is_super_admin")
    val isSuperAdmin: Boolean = false,
    @SerializedName("linked_platforms")
    val linkedPlatforms: List<String> = emptyList(),
    val communities: List<Community>? = null
)

data class Community(
    val id: String,
    val name: String,
    val description: String? = null,
    @SerializedName("avatar_url")
    val avatarUrl: String? = null,
    @SerializedName("member_count")
    val memberCount: Int = 0,
    @SerializedName("owner_id")
    val ownerId: String? = null,
    @SerializedName("created_at")
    val createdAt: String? = null
)

data class CommunityDashboard(
    val community: Community,
    val stats: CommunityStats,
    @SerializedName("recent_activity")
    val recentActivity: List<ActivityItem> = emptyList()
)

data class CommunityStats(
    @SerializedName("member_count")
    val memberCount: Int = 0,
    @SerializedName("active_members")
    val activeMembers: Int = 0,
    @SerializedName("commands_today")
    val commandsToday: Int = 0,
    @SerializedName("messages_today")
    val messagesToday: Int = 0
)

data class ActivityItem(
    val id: String,
    val type: String,
    val description: String,
    val timestamp: String,
    @SerializedName("user_name")
    val userName: String? = null
)

data class Member(
    val id: String,
    @SerializedName("user_id")
    val userId: String,
    @SerializedName("community_id")
    val communityId: String,
    val username: String,
    @SerializedName("display_name")
    val displayName: String? = null,
    @SerializedName("avatar_url")
    val avatarUrl: String? = null,
    val role: String = "viewer",
    @SerializedName("joined_at")
    val joinedAt: String? = null,
    @SerializedName("reputation_score")
    val reputationScore: Int = 0
)

data class LoginRequest(
    val email: String,
    val password: String
)

data class LoginResponse(
    val success: Boolean,
    val token: String? = null,
    val user: User? = null,
    val error: String? = null
)

data class RefreshResponse(
    val success: Boolean,
    val token: String? = null,
    val error: String? = null
)

data class UserResponse(
    val success: Boolean,
    val user: User? = null,
    val error: String? = null
)

data class CommunitiesResponse(
    val success: Boolean,
    val communities: List<Community> = emptyList(),
    val error: String? = null
)

data class DashboardResponse(
    val success: Boolean,
    val dashboard: CommunityDashboard? = null,
    val error: String? = null
)

data class MembersResponse(
    val success: Boolean,
    val members: List<Member> = emptyList(),
    val total: Int = 0,
    val error: String? = null
)

sealed class ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>()
    data class Error(val message: String, val code: Int? = null) : ApiResult<Nothing>()
}
