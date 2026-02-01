import Foundation
import Combine

/// WebSocket manager for real-time chat communication.
/// Uses native URLSessionWebSocketTask for WebSocket connections with Socket.io protocol support.
@MainActor
final class WebSocketManager: NSObject, ObservableObject {

    // MARK: - Published Properties

    @Published private(set) var connectionState: ConnectionState = .disconnected
    @Published private(set) var lastError: WebSocketError?

    // MARK: - Publishers

    let incomingMessages = PassthroughSubject<ChatMessage, Never>()
    let typingEvents = PassthroughSubject<TypingEvent, Never>()
    let chatHistory = PassthroughSubject<[ChatMessage], Never>()

    // MARK: - Private Properties

    private var webSocketTask: URLSessionWebSocketTask?
    private var session: URLSession?
    private var authToken: String?
    private var baseURL: URL
    private var reconnectionAttempts = 0
    private var pingTimer: Timer?

    private let maxReconnectionAttempts = 5
    private let reconnectionDelay: TimeInterval = 1.0
    private let pingInterval: TimeInterval = 25.0

    // MARK: - Socket.io Protocol

    private enum SocketIOPacketType: String {
        case connect = "0"
        case disconnect = "1"
        case event = "2"
        case ack = "3"
        case connectError = "4"
        case binaryEvent = "5"
        case binaryAck = "6"
    }

    // MARK: - Initialization

    /// Initialize WebSocketManager with the server URL.
    /// - Parameter baseURL: The WebSocket server URL
    init(baseURL: URL) {
        self.baseURL = baseURL
        super.init()
    }

    // MARK: - Connection Management

    /// Connect to the WebSocket server with authentication.
    /// - Parameter token: JWT authentication token
    func connect(token: String) {
        guard connectionState != .connected else {
            return
        }

        authToken = token
        connectionState = .connecting

        // Build WebSocket URL with Socket.io parameters
        var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: true)!
        components.queryItems = [
            URLQueryItem(name: "EIO", value: "4"),
            URLQueryItem(name: "transport", value: "websocket"),
            URLQueryItem(name: "token", value: token)
        ]

        guard let wsURL = components.url else {
            connectionState = .error
            lastError = .invalidURL
            return
        }

        var request = URLRequest(url: wsURL)
        request.timeoutInterval = 30
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        let configuration = URLSessionConfiguration.default
        session = URLSession(configuration: configuration, delegate: self, delegateQueue: nil)
        webSocketTask = session?.webSocketTask(with: request)

        webSocketTask?.resume()
        startReceiving()
        startPingTimer()
    }

    /// Disconnect from the WebSocket server.
    func disconnect() {
        stopPingTimer()
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        webSocketTask = nil
        session?.invalidateAndCancel()
        session = nil
        connectionState = .disconnected
        reconnectionAttempts = 0
    }

    /// Attempt to reconnect to the server.
    func reconnect() {
        guard let token = authToken else {
            lastError = .notAuthenticated
            return
        }

        disconnect()
        connect(token: token)
    }

    // MARK: - Chat Operations

    /// Join a chat channel.
    /// - Parameters:
    ///   - communityId: The community ID
    ///   - channelName: The channel name to join
    func joinChannel(communityId: String, channelName: String) {
        let payload: [String: Any] = [
            "communityId": communityId,
            "channelName": channelName
        ]
        emit(event: "chat:join", data: payload)
    }

    /// Send a chat message.
    /// - Parameters:
    ///   - communityId: The community ID
    ///   - channelName: The channel name
    ///   - content: The message content
    ///   - type: The message type (default: "text")
    func sendMessage(communityId: String, channelName: String, content: String, type: String = "text") {
        guard connectionState == .connected else {
            lastError = .notConnected
            return
        }

        let payload: [String: Any] = [
            "communityId": communityId,
            "channelName": channelName,
            "content": content,
            "type": type
        ]
        emit(event: "chat:message", data: payload)
    }

    /// Send typing indicator.
    /// - Parameters:
    ///   - communityId: The community ID
    ///   - channelName: The channel name
    ///   - isTyping: Whether the user is typing
    func sendTypingIndicator(communityId: String, channelName: String, isTyping: Bool) {
        guard connectionState == .connected else { return }

        let payload: [String: Any] = [
            "communityId": communityId,
            "channelName": channelName,
            "isTyping": isTyping
        ]
        emit(event: "chat:typing", data: payload)
    }

    /// Request chat history for a channel.
    /// - Parameters:
    ///   - communityId: The community ID
    ///   - channelName: The channel name
    ///   - limit: Number of messages to retrieve
    ///   - before: Timestamp to fetch messages before (for pagination)
    func requestHistory(communityId: String, channelName: String, limit: Int = 50, before: String? = nil) {
        guard connectionState == .connected else {
            lastError = .notConnected
            return
        }

        var payload: [String: Any] = [
            "communityId": communityId,
            "channelName": channelName,
            "limit": limit
        ]

        if let before = before {
            payload["before"] = before
        }

        emit(event: "chat:history", data: payload)
    }

    // MARK: - Private Methods

    private func emit(event: String, data: [String: Any]) {
        guard connectionState == .connected else {
            lastError = .notConnected
            return
        }

        do {
            let jsonData = try JSONSerialization.data(withJSONObject: data)
            guard let jsonString = String(data: jsonData, encoding: .utf8) else {
                return
            }

            // Socket.io event format: 42["event",{data}]
            let message = "42[\"\(event)\",\(jsonString)]"
            send(text: message)
        } catch {
            lastError = .encodingError
        }
    }

    private func send(text: String) {
        let message = URLSessionWebSocketTask.Message.string(text)
        webSocketTask?.send(message) { [weak self] error in
            if let error = error {
                Task { @MainActor in
                    self?.handleError(error)
                }
            }
        }
    }

    private func startReceiving() {
        webSocketTask?.receive { [weak self] result in
            Task { @MainActor in
                switch result {
                case .success(let message):
                    self?.handleMessage(message)
                    self?.startReceiving()
                case .failure(let error):
                    self?.handleError(error)
                }
            }
        }
    }

    private func handleMessage(_ message: URLSessionWebSocketTask.Message) {
        switch message {
        case .string(let text):
            parseSocketIOMessage(text)
        case .data(let data):
            if let text = String(data: data, encoding: .utf8) {
                parseSocketIOMessage(text)
            }
        @unknown default:
            break
        }
    }

    private func parseSocketIOMessage(_ text: String) {
        // Socket.io protocol: first character(s) indicate packet type
        guard !text.isEmpty else { return }

        // Handle Socket.io open packet (contains session info)
        if text.hasPrefix("0{") {
            connectionState = .connected
            reconnectionAttempts = 0
            return
        }

        // Handle ping/pong
        if text == "2" {
            send(text: "3") // Pong response
            return
        }

        // Handle event messages (42["event", data])
        if text.hasPrefix("42") {
            let jsonPart = String(text.dropFirst(2))
            parseEventMessage(jsonPart)
        }
    }

    private func parseEventMessage(_ jsonString: String) {
        guard let data = jsonString.data(using: .utf8),
              let array = try? JSONSerialization.jsonObject(with: data) as? [Any],
              let eventName = array.first as? String else {
            return
        }

        let eventData = array.count > 1 ? array[1] : nil

        switch eventName {
        case "chat:message":
            if let dict = eventData as? [String: Any] {
                handleIncomingMessage(dict)
            }
        case "chat:typing":
            if let dict = eventData as? [String: Any] {
                handleTypingEvent(dict)
            }
        case "chat:history":
            if let dict = eventData as? [String: Any] {
                handleHistoryResponse(dict)
            }
        default:
            break
        }
    }

    private func handleIncomingMessage(_ data: [String: Any]) {
        guard let id = data["id"] as? String,
              let communityId = data["communityId"] as? String,
              let senderId = data["senderId"] as? String,
              let senderUsername = data["senderUsername"] as? String,
              let content = data["content"] as? String,
              let type = data["type"] as? String,
              let createdAt = data["createdAt"] as? String else {
            return
        }

        let message = ChatMessage(
            id: id,
            communityId: communityId,
            senderId: senderId,
            senderUsername: senderUsername,
            senderAvatarUrl: data["senderAvatarUrl"] as? String,
            content: content,
            type: type,
            createdAt: createdAt
        )

        incomingMessages.send(message)
    }

    private func handleTypingEvent(_ data: [String: Any]) {
        guard let communityId = data["communityId"] as? String,
              let channelName = data["channelName"] as? String,
              let userId = data["userId"] as? String,
              let username = data["username"] as? String,
              let isTyping = data["isTyping"] as? Bool else {
            return
        }

        let event = TypingEvent(
            communityId: communityId,
            channelName: channelName,
            userId: userId,
            username: username,
            isTyping: isTyping
        )

        typingEvents.send(event)
    }

    private func handleHistoryResponse(_ data: [String: Any]) {
        guard let messagesArray = data["messages"] as? [[String: Any]] else {
            return
        }

        let messages = messagesArray.compactMap { dict -> ChatMessage? in
            guard let id = dict["id"] as? String,
                  let communityId = dict["communityId"] as? String,
                  let senderId = dict["senderId"] as? String,
                  let senderUsername = dict["senderUsername"] as? String,
                  let content = dict["content"] as? String,
                  let type = dict["type"] as? String,
                  let createdAt = dict["createdAt"] as? String else {
                return nil
            }

            return ChatMessage(
                id: id,
                communityId: communityId,
                senderId: senderId,
                senderUsername: senderUsername,
                senderAvatarUrl: dict["senderAvatarUrl"] as? String,
                content: content,
                type: type,
                createdAt: createdAt
            )
        }

        chatHistory.send(messages)
    }

    private func handleError(_ error: Error) {
        connectionState = .error
        lastError = .connectionFailed(error.localizedDescription)
        attemptReconnection()
    }

    private func attemptReconnection() {
        guard reconnectionAttempts < maxReconnectionAttempts else {
            lastError = .maxReconnectionAttemptsReached
            return
        }

        reconnectionAttempts += 1

        DispatchQueue.main.asyncAfter(deadline: .now() + reconnectionDelay) { [weak self] in
            self?.reconnect()
        }
    }

    private func startPingTimer() {
        pingTimer = Timer.scheduledTimer(withTimeInterval: pingInterval, repeats: true) { [weak self] _ in
            self?.send(text: "2") // Socket.io ping
        }
    }

    private func stopPingTimer() {
        pingTimer?.invalidate()
        pingTimer = nil
    }
}

// MARK: - URLSessionWebSocketDelegate

extension WebSocketManager: URLSessionWebSocketDelegate {
    nonisolated func urlSession(
        _ session: URLSession,
        webSocketTask: URLSessionWebSocketTask,
        didOpenWithProtocol protocol: String?
    ) {
        Task { @MainActor in
            connectionState = .connecting
        }
    }

    nonisolated func urlSession(
        _ session: URLSession,
        webSocketTask: URLSessionWebSocketTask,
        didCloseWith closeCode: URLSessionWebSocketTask.CloseCode,
        reason: Data?
    ) {
        Task { @MainActor in
            connectionState = .disconnected
            if closeCode != .goingAway {
                attemptReconnection()
            }
        }
    }
}

// MARK: - Supporting Types

/// Connection state for the WebSocket.
enum ConnectionState: Equatable {
    case disconnected
    case connecting
    case connected
    case error
}

/// WebSocket error types.
enum WebSocketError: LocalizedError, Equatable {
    case invalidURL
    case notConnected
    case notAuthenticated
    case connectionFailed(String)
    case encodingError
    case maxReconnectionAttemptsReached

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid WebSocket URL"
        case .notConnected:
            return "Not connected to server"
        case .notAuthenticated:
            return "Authentication token not set"
        case .connectionFailed(let message):
            return "Connection failed: \(message)"
        case .encodingError:
            return "Failed to encode message"
        case .maxReconnectionAttemptsReached:
            return "Unable to connect after multiple attempts"
        }
    }
}

/// Chat message model.
struct ChatMessage: Identifiable, Equatable, Hashable {
    let id: String
    let communityId: String
    let senderId: String
    let senderUsername: String
    let senderAvatarUrl: String?
    let content: String
    let type: String
    let createdAt: String

    var formattedTime: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        guard let date = formatter.date(from: createdAt) else {
            return createdAt
        }

        let displayFormatter = DateFormatter()
        displayFormatter.timeStyle = .short
        return displayFormatter.string(from: date)
    }
}

/// Typing event model.
struct TypingEvent: Equatable {
    let communityId: String
    let channelName: String
    let userId: String
    let username: String
    let isTyping: Bool
}
