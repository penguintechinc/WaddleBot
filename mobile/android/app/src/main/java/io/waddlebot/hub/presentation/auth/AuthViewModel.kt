package io.waddlebot.hub.presentation.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.waddlebot.hub.data.models.ApiResult
import io.waddlebot.hub.data.models.User
import io.waddlebot.hub.data.repository.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AuthState(
    val isLoading: Boolean = false,
    val isLoggedIn: Boolean = false,
    val user: User? = null,
    val error: String? = null,
    val isCheckingAuth: Boolean = true
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _state = MutableStateFlow(AuthState())
    val state: StateFlow<AuthState> = _state.asStateFlow()

    init {
        checkAuthStatus()
    }

    fun checkAuthStatus() {
        viewModelScope.launch {
            _state.update { it.copy(isCheckingAuth = true, error = null) }

            if (!authRepository.hasToken()) {
                _state.update { it.copy(isCheckingAuth = false, isLoggedIn = false) }
                return@launch
            }

            when (val result = authRepository.getCurrentUser()) {
                is ApiResult.Success -> {
                    _state.update {
                        it.copy(
                            isCheckingAuth = false,
                            isLoggedIn = true,
                            user = result.data
                        )
                    }
                }
                is ApiResult.Error -> {
                    _state.update {
                        it.copy(
                            isCheckingAuth = false,
                            isLoggedIn = false,
                            user = null
                        )
                    }
                }
            }
        }
    }

    fun login(email: String, password: String) {
        if (email.isBlank() || password.isBlank()) {
            _state.update { it.copy(error = "Email and password are required") }
            return
        }

        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }

            when (val result = authRepository.login(email, password)) {
                is ApiResult.Success -> {
                    val user = result.data.user
                    if (user != null) {
                        _state.update {
                            it.copy(
                                isLoading = false,
                                isLoggedIn = true,
                                user = user,
                                error = null
                            )
                        }
                    } else {
                        _state.update {
                            it.copy(
                                isLoading = false,
                                error = "Login response did not include a user"
                            )
                        }
                    }
                }
                is ApiResult.Error -> {
                    _state.update {
                        it.copy(
                            isLoading = false,
                            error = result.message
                        )
                    }
                }
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true) }

            authRepository.logout()

            _state.update {
                AuthState(
                    isLoading = false,
                    isLoggedIn = false,
                    isCheckingAuth = false
                )
            }
        }
    }

    fun clearError() {
        _state.update { it.copy(error = null) }
    }
}
