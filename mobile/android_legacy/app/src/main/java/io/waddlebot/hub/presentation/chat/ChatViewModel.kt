package io.waddlebot.hub.presentation.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import io.waddlebot.hub.data.network.ChatMessage
import io.waddlebot.hub.data.network.ConnectionState
import io.waddlebot.hub.data.network.WebSocketError
import io.waddlebot.hub.data.network.WebSocketService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ViewModel for managing chat state and WebSocket communication.
 * Handles message sending/receiving, typing indicators, and connection management.
 */
class ChatViewModel(
    private val webSocketService: WebSocketService
) : ViewModel() {

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    val connectionState: StateFlow<ConnectionState> = webSocketService.connectionState

    private var currentCommunityId: String? = null
    private var currentChannelName: String? = null
    private var authToken: String? = null

    init {
        observeWebSocketEvents()
    }

    /**
     * Set the authentication token and connect to WebSocket.
     * @param token JWT authentication token
     */
    fun setAuthToken(token: String) {
        authToken = token
        webSocketService.connect(token)
    }

    /**
     * Join a chat channel.
     * @param communityId The community ID
     * @param channelName The channel name to join
     */
    fun joinChannel(communityId: String, channelName: String) {
        currentCommunityId = communityId
        currentChannelName = channelName

        // Clear previous messages when joining a new channel
        _uiState.update { it.copy(messages = emptyList(), typingUsers = emptySet()) }

        webSocketService.joinChannel(communityId, channelName)

        // Request chat history
        _uiState.update { it.copy(isLoadingHistory = true) }
        webSocketService.requestHistory(communityId, channelName)
    }

    /**
     * Update the message input field.
     * @param input The new input value
     */
    fun updateMessageInput(input: String) {
        _uiState.update { it.copy(messageInput = input) }
    }

    /**
     * Send a chat message to the current channel.
     * @param communityId The community ID
     * @param channelName The channel name
     */
    fun sendMessage(communityId: String, channelName: String) {
        val content = _uiState.value.messageInput.trim()
        if (content.isEmpty()) return

        webSocketService.sendMessage(
            communityId = communityId,
            channelName = channelName,
            content = content,
            type = "text"
        )

        // Clear input after sending
        _uiState.update { it.copy(messageInput = "") }
    }

    /**
     * Send typing indicator to the channel.
     * @param communityId The community ID
     * @param channelName The channel name
     * @param isTyping Whether the user is typing
     */
    fun sendTypingIndicator(communityId: String, channelName: String, isTyping: Boolean) {
        webSocketService.sendTypingIndicator(communityId, channelName, isTyping)
    }

    /**
     * Attempt to reconnect to WebSocket.
     */
    fun reconnect() {
        authToken?.let { token ->
            webSocketService.connect(token)

            // Rejoin the current channel after reconnection
            viewModelScope.launch {
                webSocketService.connectionState.collect { state ->
                    if (state == ConnectionState.CONNECTED) {
                        currentCommunityId?.let { communityId ->
                            currentChannelName?.let { channelName ->
                                joinChannel(communityId, channelName)
                            }
                        }
                    }
                }
            }
        }
    }

    /**
     * Clear the current error message.
     */
    fun clearError() {
        _uiState.update { it.copy(errorMessage = null) }
    }

    /**
     * Load more message history for pagination.
     */
    fun loadMoreHistory() {
        val communityId = currentCommunityId ?: return
        val channelName = currentChannelName ?: return
        val oldestMessage = _uiState.value.messages.firstOrNull() ?: return

        _uiState.update { it.copy(isLoadingHistory = true) }
        webSocketService.requestHistory(
            communityId = communityId,
            channelName = channelName,
            before = oldestMessage.createdAt
        )
    }

    private fun observeWebSocketEvents() {
        // Observe incoming messages
        viewModelScope.launch {
            webSocketService.incomingMessages.collect { message ->
                _uiState.update { state ->
                    state.copy(
                        messages = state.messages + message
                    )
                }
            }
        }

        // Observe typing events
        viewModelScope.launch {
            webSocketService.typingUsers.collect { event ->
                _uiState.update { state ->
                    val updatedTypingUsers = if (event.isTyping) {
                        state.typingUsers + event.username
                    } else {
                        state.typingUsers - event.username
                    }
                    state.copy(typingUsers = updatedTypingUsers)
                }
            }
        }

        // Observe chat history
        viewModelScope.launch {
            webSocketService.chatHistory.collect { historyMessages ->
                _uiState.update { state ->
                    // Prepend history messages to existing messages
                    val existingIds = state.messages.map { it.id }.toSet()
                    val newMessages = historyMessages.filter { it.id !in existingIds }

                    state.copy(
                        messages = newMessages + state.messages,
                        isLoadingHistory = false
                    )
                }
            }
        }

        // Observe errors
        viewModelScope.launch {
            webSocketService.errors.collect { error ->
                val errorMessage = when (error) {
                    is WebSocketError.ConnectionFailed -> "Connection failed: ${error.message}"
                    is WebSocketError.NotConnected -> "Not connected to server"
                    is WebSocketError.MaxReconnectionAttemptsReached -> "Unable to connect after multiple attempts"
                }
                _uiState.update { it.copy(errorMessage = errorMessage) }
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        // Stop typing indicator when leaving
        currentCommunityId?.let { communityId ->
            currentChannelName?.let { channelName ->
                webSocketService.sendTypingIndicator(communityId, channelName, false)
            }
        }
    }
}

/**
 * UI state for the chat screen.
 */
data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val messageInput: String = "",
    val typingUsers: Set<String> = emptySet(),
    val isLoadingHistory: Boolean = false,
    val errorMessage: String? = null
)
