package io.waddlebot.hub.data.repository

import io.waddlebot.hub.data.models.ApiResult
import io.waddlebot.hub.data.models.Community
import io.waddlebot.hub.data.models.CommunityDashboard
import io.waddlebot.hub.data.models.Member
import io.waddlebot.hub.data.network.HubApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class CommunityRepository @Inject constructor(
    private val api: HubApi
) {
    suspend fun getMyCommunities(): ApiResult<List<Community>> {
        return withContext(Dispatchers.IO) {
            try {
                val response = api.getMyCommunities()
                if (response.isSuccessful) {
                    val body = response.body()
                    if (body != null && body.success) {
                        ApiResult.Success(body.communities)
                    } else {
                        ApiResult.Error(body?.error ?: "Failed to get communities")
                    }
                } else {
                    ApiResult.Error("Failed to get communities: ${response.code()}", response.code())
                }
            } catch (e: Exception) {
                ApiResult.Error(e.message ?: "Unknown error occurred")
            }
        }
    }

    suspend fun getCommunityDashboard(id: String): ApiResult<CommunityDashboard> {
        return withContext(Dispatchers.IO) {
            try {
                val response = api.getCommunityDashboard(id)
                if (response.isSuccessful) {
                    val body = response.body()
                    if (body != null && body.success && body.dashboard != null) {
                        ApiResult.Success(body.dashboard)
                    } else {
                        ApiResult.Error(body?.error ?: "Failed to get dashboard")
                    }
                } else {
                    ApiResult.Error("Failed to get dashboard: ${response.code()}", response.code())
                }
            } catch (e: Exception) {
                ApiResult.Error(e.message ?: "Unknown error occurred")
            }
        }
    }

    suspend fun getCommunityMembers(id: String): ApiResult<List<Member>> {
        return withContext(Dispatchers.IO) {
            try {
                val response = api.getCommunityMembers(id)
                if (response.isSuccessful) {
                    val body = response.body()
                    if (body != null && body.success) {
                        ApiResult.Success(body.members)
                    } else {
                        ApiResult.Error(body?.error ?: "Failed to get members")
                    }
                } else {
                    ApiResult.Error("Failed to get members: ${response.code()}", response.code())
                }
            } catch (e: Exception) {
                ApiResult.Error(e.message ?: "Unknown error occurred")
            }
        }
    }
}
