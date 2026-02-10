package io.waddlebot.hub.data.network

import android.util.Log
import io.socket.client.IO
import io.socket.client.Socket
import io.socket.emitter.Emitter
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.net.URI

/**
 * WebSocket service for real-time chat communication using Socket.io.
 * Handles connection management, event emission, and message reception.
 */
class WebSocketService(
    private val baseUrl: String
) {
    companion object {
        private const val TAG = "WebSocketService"
        private const val RECONNECTION_DELAY_MS = 1000L
        private const val MAX_RECONNECTION_ATTEMPTS = 5

        // Socket.io events
        const val EVENT_CHAT_JOIN = "chat:join"
        const val EVENT_CHAT_MESSAGE = "chat:message"
        const val EVENT_CHAT_TYPING = "chat:typing"
        const val EVENT_CHAT_HISTORY = "chat:history"
    }

    private var socket: Socket? = null
    private var authToken: String? = null
    private var reconnectionAttempts = 0

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _incomingMessages = MutableSharedFlow<ChatMessage>()
    val incomingMessages: SharedFlow<ChatMessage> = _incomingMessages.asSharedFlow()

    private val _typingUsers = MutableSharedFlow<TypingEvent>()
    val typingUsers: SharedFlow<TypingEvent> = _typingUsers.asSharedFlow()

    private val _chatHistory = MutableSharedFlow<List<ChatMessage>>()
    val chatHistory: SharedFlow<List<ChatMessage>> = _chatHistory.asSharedFlow()

    private val _errors = MutableSharedFlow<WebSocketError>()
    val errors: SharedFlow<WebSocketError> = _errors.asSharedFlow()

    /**
     * Initialize and connect to the WebSocket server.
     * @param token JWT authentication token
     */
    fun connect(token: String) {
        if (_connectionState.value == ConnectionState.CONNECTED) {
            Log.d(TAG, "Already connected")
            return
        }

        authToken = token
        _connectionState.value = ConnectionState.CONNECTING

        try {
            val options = IO.Options().apply {
                auth = mapOf("token" to token)
                reconnection = true
                reconnectionDelay = RECONNECTION_DELAY_MS
                reconnectionAttempts = MAX_RECONNECTION_ATTEMPTS
                transports = arrayOf("websocket")
            }

            socket = IO.socket(URI.create(baseUrl), options).apply {
                on(Socket.EVENT_CONNECT, onConnect)
                on(Socket.EVENT_DISCONNECT, onDisconnect)
                on(Socket.EVENT_CONNECT_ERROR, onConnectError)
                on(EVENT_CHAT_MESSAGE, onMessageReceived)
                on(EVENT_CHAT_TYPING, onTypingReceived)
                on(EVENT_CHAT_HISTORY, onHistoryReceived)
                connect()
            }

            Log.d(TAG, "Connecting to $baseUrl")
        } catch (e: Exception) {
            Log.e(TAG, "Connection error", e)
            _connectionState.value = ConnectionState.ERROR
            scope.launch {
                _errors.emit(WebSocketError.ConnectionFailed(e.message ?: "Unknown error"))
            }
        }
    }

    /**
     * Disconnect from the WebSocket server.
     */
    fun disconnect() {
        socket?.apply {
            off()
            disconnect()
        }
        socket = null
        _connectionState.value = ConnectionState.DISCONNECTED
        reconnectionAttempts = 0
        Log.d(TAG, "Disconnected")
    }

    /**
     * Join a chat channel.
     * @param communityId The community ID
     * @param channelName The channel name to join
     */
    fun joinChannel(communityId: String, channelName: String) {
        if (_connectionState.value != ConnectionState.CONNECTED) {
            Log.w(TAG, "Cannot join channel: not connected")
            scope.launch {
                _errors.emit(WebSocketError.NotConnected)
            }
            return
        }

        val payload = JSONObject().apply {
            put("communityId", communityId)
            put("channelName", channelName)
        }

        socket?.emit(EVENT_CHAT_JOIN, payload)
        Log.d(TAG, "Joining channel: $channelName in community: $communityId")
    }

    /**
     * Send a chat message.
     * @param communityId The community ID
     * @param channelName The channel name
     * @param content The message content
     * @param type The message type (default: "text")
     */
    fun sendMessage(
        communityId: String,
        channelName: String,
        content: String,
        type: String = "text"
    ) {
        if (_connectionState.value != ConnectionState.CONNECTED) {
            Log.w(TAG, "Cannot send message: not connected")
            scope.launch {
                _errors.emit(WebSocketError.NotConnected)
            }
            return
        }

        val payload = JSONObject().apply {
            put("communityId", communityId)
            put("channelName", channelName)
            put("content", content)
            put("type", type)
        }

        socket?.emit(EVENT_CHAT_MESSAGE, payload)
        Log.d(TAG, "Message sent to $channelName")
    }

    /**
     * Send typing indicator.
     * @param communityId The community ID
     * @param channelName The channel name
     * @param isTyping Whether the user is typing
     */
    fun sendTypingIndicator(
        communityId: String,
        channelName: String,
        isTyping: Boolean
    ) {
        if (_connectionState.value != ConnectionState.CONNECTED) return

        val payload = JSONObject().apply {
            put("communityId", communityId)
            put("channelName", channelName)
            put("isTyping", isTyping)
        }

        socket?.emit(EVENT_CHAT_TYPING, payload)
    }

    /**
     * Request chat history for a channel.
     * @param communityId The community ID
     * @param channelName The channel name
     * @param limit Number of messages to retrieve
     * @param before Timestamp to fetch messages before (for pagination)
     */
    fun requestHistory(
        communityId: String,
        channelName: String,
        limit: Int = 50,
        before: String? = null
    ) {
        if (_connectionState.value != ConnectionState.CONNECTED) {
            Log.w(TAG, "Cannot request history: not connected")
            scope.launch {
                _errors.emit(WebSocketError.NotConnected)
            }
            return
        }

        val payload = JSONObject().apply {
            put("communityId", communityId)
            put("channelName", channelName)
            put("limit", limit)
            before?.let { put("before", it) }
        }

        socket?.emit(EVENT_CHAT_HISTORY, payload)
        Log.d(TAG, "Requesting history for $channelName")
    }

    // Socket.io event listeners

    private val onConnect = Emitter.Listener {
        Log.d(TAG, "Connected to WebSocket server")
        _connectionState.value = ConnectionState.CONNECTED
        reconnectionAttempts = 0
    }

    private val onDisconnect = Emitter.Listener { args ->
        val reason = args.getOrNull(0)?.toString() ?: "Unknown"
        Log.d(TAG, "Disconnected: $reason")
        _connectionState.value = ConnectionState.DISCONNECTED

        if (reason == "io server disconnect") {
            // Server disconnected, attempt reconnection
            attemptReconnection()
        }
    }

    private val onConnectError = Emitter.Listener { args ->
        val error = args.getOrNull(0)?.toString() ?: "Unknown error"
        Log.e(TAG, "Connection error: $error")
        _connectionState.value = ConnectionState.ERROR

        scope.launch {
            _errors.emit(WebSocketError.ConnectionFailed(error))
        }

        attemptReconnection()
    }

    private val onMessageReceived = Emitter.Listener { args ->
        val data = args.getOrNull(0) as? JSONObject ?: return@Listener

        try {
            val message = ChatMessage(
                id = data.getString("id"),
                communityId = data.getString("communityId"),
                senderId = data.getString("senderId"),
                senderUsername = data.getString("senderUsername"),
                senderAvatarUrl = data.optString("senderAvatarUrl", null),
                content = data.getString("content"),
                type = data.getString("type"),
                createdAt = data.getString("createdAt")
            )

            scope.launch {
                _incomingMessages.emit(message)
            }
            Log.d(TAG, "Message received from ${message.senderUsername}")
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing message", e)
        }
    }

    private val onTypingReceived = Emitter.Listener { args ->
        val data = args.getOrNull(0) as? JSONObject ?: return@Listener

        try {
            val event = TypingEvent(
                communityId = data.getString("communityId"),
                channelName = data.getString("channelName"),
                userId = data.getString("userId"),
                username = data.getString("username"),
                isTyping = data.getBoolean("isTyping")
            )

            scope.launch {
                _typingUsers.emit(event)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing typing event", e)
        }
    }

    private val onHistoryReceived = Emitter.Listener { args ->
        val data = args.getOrNull(0) as? JSONObject ?: return@Listener

        try {
            val messagesArray = data.getJSONArray("messages")
            val messages = mutableListOf<ChatMessage>()

            for (i in 0 until messagesArray.length()) {
                val msgObj = messagesArray.getJSONObject(i)
                messages.add(
                    ChatMessage(
                        id = msgObj.getString("id"),
                        communityId = msgObj.getString("communityId"),
                        senderId = msgObj.getString("senderId"),
                        senderUsername = msgObj.getString("senderUsername"),
                        senderAvatarUrl = msgObj.optString("senderAvatarUrl", null),
                        content = msgObj.getString("content"),
                        type = msgObj.getString("type"),
                        createdAt = msgObj.getString("createdAt")
                    )
                )
            }

            scope.launch {
                _chatHistory.emit(messages)
            }
            Log.d(TAG, "Received ${messages.size} history messages")
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing history", e)
        }
    }

    private fun attemptReconnection() {
        if (reconnectionAttempts >= MAX_RECONNECTION_ATTEMPTS) {
            Log.w(TAG, "Max reconnection attempts reached")
            _connectionState.value = ConnectionState.ERROR
            scope.launch {
                _errors.emit(WebSocketError.MaxReconnectionAttemptsReached)
            }
            return
        }

        reconnectionAttempts++
        Log.d(TAG, "Attempting reconnection ($reconnectionAttempts/$MAX_RECONNECTION_ATTEMPTS)")

        authToken?.let { token ->
            disconnect()
            connect(token)
        }
    }
}

/**
 * Represents the WebSocket connection state.
 */
enum class ConnectionState {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    ERROR
}

/**
 * Represents a chat message received from the server.
 */
data class ChatMessage(
    val id: String,
    val communityId: String,
    val senderId: String,
    val senderUsername: String,
    val senderAvatarUrl: String?,
    val content: String,
    val type: String,
    val createdAt: String
)

/**
 * Represents a typing indicator event.
 */
data class TypingEvent(
    val communityId: String,
    val channelName: String,
    val userId: String,
    val username: String,
    val isTyping: Boolean
)

/**
 * Sealed class for WebSocket errors.
 */
sealed class WebSocketError {
    data class ConnectionFailed(val message: String) : WebSocketError()
    data object NotConnected : WebSocketError()
    data object MaxReconnectionAttemptsReached : WebSocketError()
}
