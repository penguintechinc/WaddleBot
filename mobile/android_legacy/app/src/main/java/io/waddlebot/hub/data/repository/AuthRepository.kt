package io.waddlebot.hub.data.repository

import io.waddlebot.hub.data.models.ApiResult
import io.waddlebot.hub.data.models.LoginRequest
import io.waddlebot.hub.data.models.LoginResponse
import io.waddlebot.hub.data.models.User
import io.waddlebot.hub.data.network.HubApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val api: HubApi,
    private val preferencesRepository: PreferencesRepository
) {
    val isLoggedIn: Flow<Boolean> = preferencesRepository.isLoggedIn

    fun hasToken(): Boolean = preferencesRepository.hasToken()

    suspend fun login(email: String, password: String): ApiResult<LoginResponse> {
        return withContext(Dispatchers.IO) {
            try {
                val response = api.login(LoginRequest(email, password))
                if (response.isSuccessful) {
                    val body = response.body()
                    if (body != null && body.success && body.token != null && body.user != null) {
                        preferencesRepository.saveToken(body.token)
                        preferencesRepository.saveUserInfo(
                            userId = body.user.id,
                            email = body.user.email,
                            username = body.user.username
                        )
                        ApiResult.Success(body)
                    } else {
                        ApiResult.Error(body?.error ?: "Login failed")
                    }
                } else {
                    ApiResult.Error("Login failed: ${response.code()}", response.code())
                }
            } catch (e: Exception) {
                ApiResult.Error(e.message ?: "Unknown error occurred")
            }
        }
    }

    suspend fun refreshToken(): ApiResult<String> {
        return withContext(Dispatchers.IO) {
            try {
                val response = api.refreshToken()
                if (response.isSuccessful) {
                    val body = response.body()
                    if (body != null && body.success && body.token != null) {
                        preferencesRepository.saveToken(body.token)
                        ApiResult.Success(body.token)
                    } else {
                        ApiResult.Error(body?.error ?: "Token refresh failed")
                    }
                } else {
                    ApiResult.Error("Token refresh failed: ${response.code()}", response.code())
                }
            } catch (e: Exception) {
                ApiResult.Error(e.message ?: "Unknown error occurred")
            }
        }
    }

    suspend fun getCurrentUser(): ApiResult<User> {
        return withContext(Dispatchers.IO) {
            try {
                val response = api.getCurrentUser()
                if (response.isSuccessful) {
                    val body = response.body()
                    if (body != null && body.success && body.user != null) {
                        preferencesRepository.saveUserInfo(
                            userId = body.user.id,
                            email = body.user.email,
                            username = body.user.username
                        )
                        ApiResult.Success(body.user)
                    } else {
                        ApiResult.Error(body?.error ?: "Failed to get user")
                    }
                } else {
                    if (response.code() == 401) {
                        preferencesRepository.clearAll()
                    }
                    ApiResult.Error("Failed to get user: ${response.code()}", response.code())
                }
            } catch (e: Exception) {
                ApiResult.Error(e.message ?: "Unknown error occurred")
            }
        }
    }

    suspend fun logout(): ApiResult<Unit> {
        return withContext(Dispatchers.IO) {
            try {
                api.logout()
            } catch (_: Exception) {
                // Ignore logout API errors - clear local data anyway
            }
            preferencesRepository.clearAll()
            ApiResult.Success(Unit)
        }
    }

    fun getStoredUserId(): String? = preferencesRepository.getUserId()

    fun getStoredUserEmail(): String? = preferencesRepository.getUserEmail()

    fun getStoredUserName(): String? = preferencesRepository.getUserName()
}
