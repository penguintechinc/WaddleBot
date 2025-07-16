package com.waddlebot.premium.data.network

import com.waddlebot.premium.data.models.*
import retrofit2.Response
import retrofit2.http.*

interface WaddleBotApi {
    
    // MARK: - Authentication Endpoints
    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): Response<AuthResponse>
    
    @POST("auth/refresh")
    suspend fun refreshToken(@Body request: RefreshTokenRequest): Response<AuthResponse>
    
    @POST("auth/logout")
    suspend fun logout(): Response<ApiResponse<String>>
    
    // MARK: - Community Endpoints
    @GET("communities")
    suspend fun getCommunities(@Query("page") page: Int = 1, @Query("limit") limit: Int = 20): Response<PaginatedResponse<Community>>
    
    @GET("communities/{id}")
    suspend fun getCommunity(@Path("id") id: String): Response<ApiResponse<Community>>
    
    @PUT("communities/{id}/settings")
    suspend fun updateCommunitySettings(@Path("id") id: String, @Body settings: CommunitySettings): Response<ApiResponse<String>>
    
    // MARK: - Member Endpoints
    @GET("communities/{id}/members")
    suspend fun getMembers(@Path("id") communityId: String, @Query("page") page: Int = 1, @Query("limit") limit: Int = 20): Response<PaginatedResponse<Member>>
    
    @GET("communities/{communityId}/members/{memberId}")
    suspend fun getMember(@Path("communityId") communityId: String, @Path("memberId") memberId: String): Response<ApiResponse<Member>>
    
    @PUT("communities/{communityId}/members/{memberId}")
    suspend fun updateMember(@Path("communityId") communityId: String, @Path("memberId") memberId: String, @Body update: MemberUpdate): Response<ApiResponse<String>>
    
    @DELETE("communities/{communityId}/members/{memberId}")
    suspend fun removeMember(@Path("communityId") communityId: String, @Path("memberId") memberId: String): Response<ApiResponse<String>>
    
    // MARK: - Currency Endpoints
    @GET("communities/{id}/currency/settings")
    suspend fun getCurrencySettings(@Path("id") communityId: String): Response<ApiResponse<CurrencySettings>>
    
    @PUT("communities/{id}/currency/settings")
    suspend fun updateCurrencySettings(@Path("id") communityId: String, @Body settings: CurrencySettings): Response<ApiResponse<String>>
    
    @GET("communities/{id}/currency/balances")
    suspend fun getCurrencyBalances(@Path("id") communityId: String, @Query("page") page: Int = 1, @Query("limit") limit: Int = 20): Response<PaginatedResponse<CurrencyBalance>>
    
    @GET("communities/{id}/currency/transactions")
    suspend fun getCurrencyTransactions(@Path("id") communityId: String, @Query("page") page: Int = 1, @Query("limit") limit: Int = 20): Response<PaginatedResponse<CurrencyTransaction>>
    
    @GET("communities/{id}/currency/statistics")
    suspend fun getCurrencyStatistics(@Path("id") communityId: String): Response<ApiResponse<CurrencyStatistics>>
    
    @POST("communities/{communityId}/currency/adjust")
    suspend fun adjustCurrencyBalance(@Path("communityId") communityId: String, @Body adjustment: Map<String, Any>): Response<ApiResponse<String>>
    
    // MARK: - Payment Endpoints
    @GET("communities/{id}/payments")
    suspend fun getPaymentMethods(@Path("id") communityId: String): Response<ApiResponse<List<PaymentMethod>>>
    
    @POST("communities/{id}/payments")
    suspend fun createPayment(@Path("id") communityId: String, @Body request: PaymentRequest): Response<ApiResponse<PaymentTransaction>>
    
    @GET("communities/{id}/payments/history")
    suspend fun getPaymentTransactions(@Path("id") communityId: String, @Query("page") page: Int = 1, @Query("limit") limit: Int = 20): Response<PaginatedResponse<PaymentTransaction>>
    
    // MARK: - Raffle Endpoints
    @GET("communities/{id}/raffles")
    suspend fun getRaffles(@Path("id") communityId: String, @Query("page") page: Int = 1, @Query("limit") limit: Int = 20): Response<PaginatedResponse<Raffle>>
    
    @POST("communities/{id}/raffles")
    suspend fun createRaffle(@Path("id") communityId: String, @Body raffle: RaffleCreate): Response<ApiResponse<Raffle>>
    
    @GET("communities/{communityId}/raffles/{raffleId}")
    suspend fun getRaffle(@Path("communityId") communityId: String, @Path("raffleId") raffleId: String): Response<ApiResponse<Raffle>>
    
    @POST("communities/{communityId}/raffles/{raffleId}/draw")
    suspend fun drawRaffleWinners(@Path("communityId") communityId: String, @Path("raffleId") raffleId: String): Response<ApiResponse<List<RaffleWinner>>>
    
    @GET("communities/{communityId}/raffles/{raffleId}/entries")
    suspend fun getRaffleEntries(@Path("communityId") communityId: String, @Path("raffleId") raffleId: String): Response<ApiResponse<List<RaffleEntry>>>
    
    // MARK: - Giveaway Endpoints
    @GET("communities/{id}/giveaways")
    suspend fun getGiveaways(@Path("id") communityId: String, @Query("page") page: Int = 1, @Query("limit") limit: Int = 20): Response<PaginatedResponse<Giveaway>>
    
    @POST("communities/{id}/giveaways")
    suspend fun createGiveaway(@Path("id") communityId: String, @Body giveaway: GiveawayCreate): Response<ApiResponse<Giveaway>>
    
    @GET("communities/{communityId}/giveaways/{giveawayId}")
    suspend fun getGiveaway(@Path("communityId") communityId: String, @Path("giveawayId") giveawayId: String): Response<ApiResponse<Giveaway>>
    
    @POST("communities/{communityId}/giveaways/{giveawayId}/draw")
    suspend fun drawGiveawayWinners(@Path("communityId") communityId: String, @Path("giveawayId") giveawayId: String): Response<ApiResponse<List<GiveawayWinner>>>
    
    @GET("communities/{communityId}/giveaways/{giveawayId}/entries")
    suspend fun getGiveawayEntries(@Path("communityId") communityId: String, @Path("giveawayId") giveawayId: String): Response<ApiResponse<List<GiveawayEntry>>>
    
    // MARK: - Module Endpoints
    @GET("marketplace/browse")
    suspend fun getModules(@Query("category") category: String? = null, 
                          @Query("search") search: String? = null,
                          @Query("sort") sort: String = "popular",
                          @Query("page") page: Int = 1,
                          @Query("per_page") perPage: Int = 20): Response<PaginatedResponse<Module>>
    
    @GET("marketplace/module/{id}")
    suspend fun getModule(@Path("id") id: String): Response<ApiResponse<Module>>
    
    @POST("marketplace/install")
    suspend fun installModule(@Body request: Map<String, Any>): Response<ApiResponse<String>>
    
    @POST("marketplace/uninstall")
    suspend fun uninstallModule(@Body request: Map<String, Any>): Response<ApiResponse<String>>
    
    @GET("marketplace/entity/{entityId}/modules")
    suspend fun getInstalledModules(@Path("entityId") entityId: String): Response<ApiResponse<List<ModuleInstallation>>>
    
    @POST("marketplace/entity/{entityId}/toggle")
    suspend fun toggleModuleStatus(@Path("entityId") entityId: String, @Body request: Map<String, Any>): Response<ApiResponse<String>>
    
    // MARK: - Subscription Endpoints
    @GET("marketplace/subscription/{entityId}")
    suspend fun getSubscriptionStatus(@Path("entityId") entityId: String): Response<ApiResponse<SubscriptionStatus>>
    
    @POST("marketplace/subscription/create")
    suspend fun createSubscription(@Body request: SubscriptionCreateRequest): Response<ApiResponse<String>>
    
    @POST("marketplace/subscription/renew")
    suspend fun renewSubscription(@Body request: SubscriptionRenewRequest): Response<ApiResponse<String>>
    
    @POST("marketplace/subscription/cancel")
    suspend fun cancelSubscription(@Body request: SubscriptionCancelRequest): Response<ApiResponse<String>>
    
    @GET("marketplace/subscription/{entityId}/payments")
    suspend fun getPaymentHistory(@Path("entityId") entityId: String, @Query("limit") limit: Int = 50): Response<ApiResponse<List<PaymentHistory>>>
    
    @POST("marketplace/subscription/payment")
    suspend fun recordPayment(@Body request: PaymentRecordRequest): Response<ApiResponse<String>>
    
    @POST("marketplace/subscription/check-paid-access")
    suspend fun checkPaidModuleAccess(@Query("entityId") entityId: String, @Query("modulePrice") modulePrice: Double): Response<ApiResponse<PaidModuleAccessCheck>>
    
    @GET("marketplace/browse")
    suspend fun getModulesWithSubscription(@Query("entity_id") entityId: String,
                                         @Query("category") category: String? = null,
                                         @Query("search") search: String? = null,
                                         @Query("sort") sort: String = "popular",
                                         @Query("page") page: Int = 1,
                                         @Query("per_page") perPage: Int = 20): Response<ApiResponse<ModuleWithSubscription>>
    
    // MARK: - Log Endpoints
    @GET("communities/{id}/logs")
    suspend fun getLogs(@Path("id") communityId: String, @Query("page") page: Int = 1, @Query("limit") limit: Int = 20): Response<PaginatedResponse<LogEntry>>
    
    @POST("communities/{id}/logs")
    suspend fun createLog(@Path("id") communityId: String, @Body log: LogEntry): Response<ApiResponse<String>>
}