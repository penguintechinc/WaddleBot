package io.waddlebot.hub.data.network

import io.waddlebot.hub.data.models.CommunitiesResponse
import io.waddlebot.hub.data.models.DashboardResponse
import io.waddlebot.hub.data.models.LoginRequest
import io.waddlebot.hub.data.models.LoginResponse
import io.waddlebot.hub.data.models.MembersResponse
import io.waddlebot.hub.data.models.RefreshResponse
import io.waddlebot.hub.data.models.UserResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface HubApi {

    @POST("api/v1/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    @POST("api/v1/auth/refresh")
    suspend fun refreshToken(): Response<RefreshResponse>

    @GET("api/v1/auth/me")
    suspend fun getCurrentUser(): Response<UserResponse>

    @POST("api/v1/auth/logout")
    suspend fun logout(): Response<Unit>

    @GET("api/v1/community/my")
    suspend fun getMyCommunities(): Response<CommunitiesResponse>

    @GET("api/v1/community/{id}/dashboard")
    suspend fun getCommunityDashboard(@Path("id") id: String): Response<DashboardResponse>

    @GET("api/v1/community/{id}/members")
    suspend fun getCommunityMembers(@Path("id") id: String): Response<MembersResponse>
}
