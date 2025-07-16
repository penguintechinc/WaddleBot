package com.waddlebot.premium.data.repository

import com.waddlebot.premium.data.models.*
import com.waddlebot.premium.data.network.WaddleBotApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SubscriptionRepository @Inject constructor(
    private val api: WaddleBotApi
) {
    
    /**
     * Get subscription status for a community
     */
    fun getSubscriptionStatus(entityId: String): Flow<SubscriptionStatus> = flow {
        try {
            val response = api.getSubscriptionStatus(entityId)
            if (response.isSuccessful && response.body() != null) {
                val subscription = response.body()!!.subscription
                emit(subscription)
            } else {
                throw ApiError("subscription_error", "Failed to get subscription status")
            }
        } catch (e: Exception) {
            throw NetworkError.NetworkError(e)
        }
    }
    
    /**
     * Create a new subscription
     */
    fun createSubscription(request: SubscriptionCreateRequest): Flow<ApiResponse<String>> = flow {
        try {
            val response = api.createSubscription(request)
            if (response.isSuccessful && response.body() != null) {
                emit(response.body()!!)
            } else {
                throw ApiError("subscription_create_error", "Failed to create subscription")
            }
        } catch (e: Exception) {
            throw NetworkError.NetworkError(e)
        }
    }
    
    /**
     * Renew an existing subscription
     */
    fun renewSubscription(request: SubscriptionRenewRequest): Flow<ApiResponse<String>> = flow {
        try {
            val response = api.renewSubscription(request)
            if (response.isSuccessful && response.body() != null) {
                emit(response.body()!!)
            } else {
                throw ApiError("subscription_renew_error", "Failed to renew subscription")
            }
        } catch (e: Exception) {
            throw NetworkError.NetworkError(e)
        }
    }
    
    /**
     * Cancel a subscription
     */
    fun cancelSubscription(request: SubscriptionCancelRequest): Flow<ApiResponse<String>> = flow {
        try {
            val response = api.cancelSubscription(request)
            if (response.isSuccessful && response.body() != null) {
                emit(response.body()!!)
            } else {
                throw ApiError("subscription_cancel_error", "Failed to cancel subscription")
            }
        } catch (e: Exception) {
            throw NetworkError.NetworkError(e)
        }
    }
    
    /**
     * Get payment history for a community
     */
    fun getPaymentHistory(entityId: String, limit: Int = 50): Flow<List<PaymentHistory>> = flow {
        try {
            val response = api.getPaymentHistory(entityId, limit)
            if (response.isSuccessful && response.body() != null) {
                emit(response.body()!!.payments)
            } else {
                throw ApiError("payment_history_error", "Failed to get payment history")
            }
        } catch (e: Exception) {
            throw NetworkError.NetworkError(e)
        }
    }
    
    /**
     * Record a payment
     */
    fun recordPayment(request: PaymentRecordRequest): Flow<ApiResponse<String>> = flow {
        try {
            val response = api.recordPayment(request)
            if (response.isSuccessful && response.body() != null) {
                emit(response.body()!!)
            } else {
                throw ApiError("payment_record_error", "Failed to record payment")
            }
        } catch (e: Exception) {
            throw NetworkError.NetworkError(e)
        }
    }
    
    /**
     * Check if entity can access paid modules
     */
    fun checkPaidModuleAccess(entityId: String, modulePrice: Double): Flow<PaidModuleAccessCheck> = flow {
        try {
            val response = api.checkPaidModuleAccess(entityId, modulePrice)
            if (response.isSuccessful && response.body() != null) {
                val result = response.body()!!
                emit(PaidModuleAccessCheck(
                    entityId = result.entityId,
                    modulePrice = result.modulePrice,
                    canInstall = result.accessCheck.canInstall,
                    reason = result.accessCheck.reason,
                    message = result.accessCheck.message,
                    warning = result.accessCheck.warning
                ))
            } else {
                throw ApiError("access_check_error", "Failed to check paid module access")
            }
        } catch (e: Exception) {
            throw NetworkError.NetworkError(e)
        }
    }
    
    /**
     * Get modules with subscription information
     */
    fun getModulesWithSubscription(entityId: String, category: String? = null, 
                                 search: String? = null, sort: String = "popular",
                                 page: Int = 1, perPage: Int = 20): Flow<PaginatedResponse<ModuleWithSubscription>> = flow {
        try {
            val response = api.getModulesWithSubscription(
                entityId = entityId,
                category = category,
                search = search,
                sort = sort,
                page = page,
                perPage = perPage
            )
            if (response.isSuccessful && response.body() != null) {
                val result = response.body()!!
                val modulesWithSubscription = result.modules.map { module ->
                    ModuleWithSubscription(
                        id = module.id,
                        name = module.name,
                        description = module.description,
                        version = module.version,
                        author = module.author,
                        price = module.price ?: 0.0,
                        currency = module.currency ?: "USD",
                        category = module.category,
                        platform = module.platform,
                        isActive = module.isActive,
                        downloadCount = module.downloadCount,
                        rating = module.rating,
                        reviewCount = module.reviewCount,
                        subscriptionRequired = module.subscriptionRequired,
                        canInstall = module.canInstall,
                        accessReason = module.accessReason,
                        accessMessage = module.accessMessage,
                        createdAt = module.createdAt,
                        updatedAt = module.updatedAt
                    )
                }
                
                emit(PaginatedResponse(
                    data = modulesWithSubscription,
                    pagination = PaginationInfo(
                        page = result.pagination.page,
                        limit = result.pagination.perPage,
                        total = result.pagination.totalCount,
                        totalPages = result.pagination.totalPages,
                        hasNext = result.pagination.hasNext,
                        hasPrevious = result.pagination.hasPrev
                    ),
                    success = true
                ))
            } else {
                throw ApiError("modules_error", "Failed to get modules with subscription info")
            }
        } catch (e: Exception) {
            throw NetworkError.NetworkError(e)
        }
    }
}