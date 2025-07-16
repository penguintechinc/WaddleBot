package com.waddlebot.premium.presentation.subscription

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.waddlebot.premium.data.models.*
import com.waddlebot.premium.data.repository.SubscriptionRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SubscriptionViewModel @Inject constructor(
    private val subscriptionRepository: SubscriptionRepository
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(SubscriptionUiState())
    val uiState = _uiState.asStateFlow()
    
    fun loadSubscriptionData(entityId: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            
            try {
                // Load subscription status
                subscriptionRepository.getSubscriptionStatus(entityId)
                    .catch { error ->
                        _uiState.update { 
                            it.copy(
                                isLoading = false, 
                                error = "Failed to load subscription status: ${error.message}"
                            ) 
                        }
                    }
                    .collect { subscription ->
                        _uiState.update { 
                            it.copy(
                                subscriptionStatus = subscription,
                                isLoading = false
                            ) 
                        }
                    }
                
                // Load payment history
                subscriptionRepository.getPaymentHistory(entityId)
                    .catch { error ->
                        // Don't fail the entire screen if payment history fails
                        _uiState.update { 
                            it.copy(
                                paymentHistory = emptyList(),
                                error = "Failed to load payment history: ${error.message}"
                            ) 
                        }
                    }
                    .collect { payments ->
                        _uiState.update { 
                            it.copy(paymentHistory = payments) 
                        }
                    }
                
            } catch (e: Exception) {
                _uiState.update { 
                    it.copy(
                        isLoading = false, 
                        error = "Failed to load subscription data: ${e.message}"
                    ) 
                }
            }
        }
    }
    
    fun renewSubscription(entityId: String, durationDays: Int = 30) {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            
            try {
                val request = SubscriptionRenewRequest(
                    entityId = entityId,
                    durationDays = durationDays,
                    amountPaid = 29.99 // Default premium price
                )
                
                subscriptionRepository.renewSubscription(request)
                    .catch { error ->
                        _uiState.update { 
                            it.copy(
                                isLoading = false, 
                                error = "Failed to renew subscription: ${error.message}"
                            ) 
                        }
                    }
                    .collect { response ->
                        if (response.success) {
                            // Reload subscription data
                            loadSubscriptionData(entityId)
                            _uiState.update { 
                                it.copy(
                                    isLoading = false,
                                    successMessage = "Subscription renewed successfully!"
                                ) 
                            }
                        } else {
                            _uiState.update { 
                                it.copy(
                                    isLoading = false, 
                                    error = "Failed to renew subscription: ${response.message}"
                                ) 
                            }
                        }
                    }
                
            } catch (e: Exception) {
                _uiState.update { 
                    it.copy(
                        isLoading = false, 
                        error = "Failed to renew subscription: ${e.message}"
                    ) 
                }
            }
        }
    }
    
    fun cancelSubscription(entityId: String, reason: String? = null) {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            
            try {
                val request = SubscriptionCancelRequest(
                    entityId = entityId,
                    reason = reason
                )
                
                subscriptionRepository.cancelSubscription(request)
                    .catch { error ->
                        _uiState.update { 
                            it.copy(
                                isLoading = false, 
                                error = "Failed to cancel subscription: ${error.message}"
                            ) 
                        }
                    }
                    .collect { response ->
                        if (response.success) {
                            // Reload subscription data
                            loadSubscriptionData(entityId)
                            _uiState.update { 
                                it.copy(
                                    isLoading = false,
                                    successMessage = "Subscription cancelled successfully!"
                                ) 
                            }
                        } else {
                            _uiState.update { 
                                it.copy(
                                    isLoading = false, 
                                    error = "Failed to cancel subscription: ${response.message}"
                                ) 
                            }
                        }
                    }
                
            } catch (e: Exception) {
                _uiState.update { 
                    it.copy(
                        isLoading = false, 
                        error = "Failed to cancel subscription: ${e.message}"
                    ) 
                }
            }
        }
    }
    
    fun createSubscription(entityId: String, subscriptionType: String = "premium", 
                          durationDays: Int = 30, paymentMethod: String = "stripe") {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            
            try {
                val request = SubscriptionCreateRequest(
                    entityId = entityId,
                    subscriptionType = subscriptionType,
                    durationDays = durationDays,
                    paymentMethod = paymentMethod,
                    amountPaid = 29.99 // Default premium price
                )
                
                subscriptionRepository.createSubscription(request)
                    .catch { error ->
                        _uiState.update { 
                            it.copy(
                                isLoading = false, 
                                error = "Failed to create subscription: ${error.message}"
                            ) 
                        }
                    }
                    .collect { response ->
                        if (response.success) {
                            // Reload subscription data
                            loadSubscriptionData(entityId)
                            _uiState.update { 
                                it.copy(
                                    isLoading = false,
                                    successMessage = "Subscription created successfully!"
                                ) 
                            }
                        } else {
                            _uiState.update { 
                                it.copy(
                                    isLoading = false, 
                                    error = "Failed to create subscription: ${response.message}"
                                ) 
                            }
                        }
                    }
                
            } catch (e: Exception) {
                _uiState.update { 
                    it.copy(
                        isLoading = false, 
                        error = "Failed to create subscription: ${e.message}"
                    ) 
                }
            }
        }
    }
    
    fun checkPaidModuleAccess(entityId: String, modulePrice: Double) {
        viewModelScope.launch {
            try {
                subscriptionRepository.checkPaidModuleAccess(entityId, modulePrice)
                    .catch { error ->
                        _uiState.update { 
                            it.copy(
                                error = "Failed to check paid module access: ${error.message}"
                            ) 
                        }
                    }
                    .collect { accessCheck ->
                        _uiState.update { 
                            it.copy(paidModuleAccess = accessCheck) 
                        }
                    }
                
            } catch (e: Exception) {
                _uiState.update { 
                    it.copy(
                        error = "Failed to check paid module access: ${e.message}"
                    ) 
                }
            }
        }
    }
    
    fun clearError() {
        _uiState.update { it.copy(error = null) }
    }
    
    fun clearSuccessMessage() {
        _uiState.update { it.copy(successMessage = null) }
    }
}

data class SubscriptionUiState(
    val isLoading: Boolean = false,
    val subscriptionStatus: SubscriptionStatus? = null,
    val paymentHistory: List<PaymentHistory> = emptyList(),
    val paidModuleAccess: PaidModuleAccessCheck? = null,
    val error: String? = null,
    val successMessage: String? = null
)