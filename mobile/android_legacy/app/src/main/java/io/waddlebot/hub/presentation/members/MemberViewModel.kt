package io.waddlebot.hub.presentation.members

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.waddlebot.hub.data.models.Member
import io.waddlebot.hub.data.repository.CommunityRepository
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class MemberListState(
    val members: List<Member> = emptyList(),
    val filteredMembers: List<Member> = emptyList(),
    val searchQuery: String = "",
    val isLoading: Boolean = false,
    val isSearching: Boolean = false,
    val error: String? = null
)

@OptIn(FlowPreview::class)
@HiltViewModel
class MemberViewModel @Inject constructor(
    private val communityRepository: CommunityRepository,
    savedStateHandle: SavedStateHandle
) : ViewModel() {

    private val communityId: String = savedStateHandle.get<String>("communityId") ?: ""

    private val _state = MutableStateFlow(MemberListState())
    val state: StateFlow<MemberListState> = _state.asStateFlow()

    private val searchQueryFlow = MutableStateFlow("")

    init {
        if (communityId.isNotEmpty()) {
            loadMembers()
            setupSearchDebounce()
        }
    }

    private fun setupSearchDebounce() {
        searchQueryFlow
            .debounce(300)
            .distinctUntilChanged()
            .onEach { query ->
                if (query.isNotEmpty()) {
                    searchMembers(query)
                } else {
                    _state.update {
                        it.copy(
                            filteredMembers = it.members,
                            isSearching = false
                        )
                    }
                }
            }
            .launchIn(viewModelScope)
    }

    fun loadMembers() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }

            communityRepository.getMembers(communityId)
                .onSuccess { members ->
                    _state.update {
                        it.copy(
                            members = members,
                            filteredMembers = if (it.searchQuery.isEmpty()) {
                                members
                            } else {
                                it.filteredMembers
                            },
                            isLoading = false
                        )
                    }
                }
                .onFailure { throwable ->
                    _state.update {
                        it.copy(
                            isLoading = false,
                            error = throwable.message ?: "Failed to load members"
                        )
                    }
                }
        }
    }

    fun onSearchQueryChange(query: String) {
        _state.update {
            it.copy(
                searchQuery = query,
                isSearching = query.isNotEmpty()
            )
        }
        searchQueryFlow.value = query
    }

    private fun searchMembers(query: String) {
        viewModelScope.launch {
            communityRepository.getMembers(communityId, search = query)
                .onSuccess { members ->
                    _state.update {
                        it.copy(
                            filteredMembers = members,
                            isSearching = false
                        )
                    }
                }
                .onFailure {
                    // Fall back to local filtering
                    val filtered = _state.value.members.filter { member ->
                        member.username.contains(query, ignoreCase = true) ||
                            member.displayName?.contains(query, ignoreCase = true) == true
                    }
                    _state.update {
                        it.copy(
                            filteredMembers = filtered,
                            isSearching = false
                        )
                    }
                }
        }
    }

    fun clearSearch() {
        _state.update {
            it.copy(
                searchQuery = "",
                filteredMembers = it.members,
                isSearching = false
            )
        }
        searchQueryFlow.value = ""
    }

    fun clearError() {
        _state.update { it.copy(error = null) }
    }
}
