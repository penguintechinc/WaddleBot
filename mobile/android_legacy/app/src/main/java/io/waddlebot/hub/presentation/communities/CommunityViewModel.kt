package io.waddlebot.hub.presentation.communities

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.waddlebot.hub.data.models.Community
import io.waddlebot.hub.data.models.CommunityDetail
import io.waddlebot.hub.data.repository.CommunityRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class CommunityListState(
    val communities: List<Community> = emptyList(),
    val isLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val error: String? = null
)

data class CommunityDetailState(
    val detail: CommunityDetail? = null,
    val isLoading: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class CommunityViewModel @Inject constructor(
    private val communityRepository: CommunityRepository
) : ViewModel() {

    private val _listState = MutableStateFlow(CommunityListState())
    val listState: StateFlow<CommunityListState> = _listState.asStateFlow()

    private val _detailState = MutableStateFlow(CommunityDetailState())
    val detailState: StateFlow<CommunityDetailState> = _detailState.asStateFlow()

    init {
        loadCommunities()
    }

    fun loadCommunities() {
        viewModelScope.launch {
            _listState.update { it.copy(isLoading = true, error = null) }

            communityRepository.getCommunities()
                .onSuccess { communities ->
                    _listState.update {
                        it.copy(
                            communities = communities,
                            isLoading = false,
                            isRefreshing = false
                        )
                    }
                }
                .onFailure { throwable ->
                    _listState.update {
                        it.copy(
                            isLoading = false,
                            isRefreshing = false,
                            error = throwable.message ?: "Failed to load communities"
                        )
                    }
                }
        }
    }

    fun refreshCommunities() {
        viewModelScope.launch {
            _listState.update { it.copy(isRefreshing = true, error = null) }

            communityRepository.getCommunities()
                .onSuccess { communities ->
                    _listState.update {
                        it.copy(
                            communities = communities,
                            isRefreshing = false
                        )
                    }
                }
                .onFailure { throwable ->
                    _listState.update {
                        it.copy(
                            isRefreshing = false,
                            error = throwable.message ?: "Failed to refresh"
                        )
                    }
                }
        }
    }

    fun loadCommunityDetail(communityId: String) {
        viewModelScope.launch {
            _detailState.update { it.copy(isLoading = true, error = null) }

            communityRepository.getCommunityDetail(communityId)
                .onSuccess { detail ->
                    _detailState.update {
                        it.copy(
                            detail = detail,
                            isLoading = false
                        )
                    }
                }
                .onFailure { throwable ->
                    _detailState.update {
                        it.copy(
                            isLoading = false,
                            error = throwable.message ?: "Failed to load community"
                        )
                    }
                }
        }
    }

    fun clearDetailState() {
        _detailState.update { CommunityDetailState() }
    }

    fun clearListError() {
        _listState.update { it.copy(error = null) }
    }

    fun clearDetailError() {
        _detailState.update { it.copy(error = null) }
    }
}
