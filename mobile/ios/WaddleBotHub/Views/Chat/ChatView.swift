import SwiftUI
import Combine

/// Main chat view displaying messages and input field.
struct ChatView: View {
    let communityId: String
    let channelName: String
    let currentUserId: String

    @StateObject private var viewModel: ChatViewModel
    @FocusState private var isInputFocused: Bool

    init(communityId: String, channelName: String, currentUserId: String, webSocketManager: WebSocketManager) {
        self.communityId = communityId
        self.channelName = channelName
        self.currentUserId = currentUserId
        _viewModel = StateObject(wrappedValue: ChatViewModel(webSocketManager: webSocketManager))
    }

    var body: some View {
        VStack(spacing: 0) {
            // Connection status bar
            ConnectionStatusBar(
                connectionState: viewModel.connectionState,
                onReconnect: { viewModel.reconnect() }
            )

            // Typing indicator
            if !viewModel.typingUsers.isEmpty {
                TypingIndicatorView(typingUsers: viewModel.typingUsers)
            }

            // Message list
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 8) {
                        if viewModel.isLoadingHistory {
                            ProgressView()
                                .padding()
                        }

                        ForEach(viewModel.messages) { message in
                            ChatMessageRow(
                                message: message,
                                isOwnMessage: message.senderId == currentUserId
                            )
                            .id(message.id)
                        }
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 8)
                }
                .onChange(of: viewModel.messages.count) { _ in
                    if let lastMessage = viewModel.messages.last {
                        withAnimation {
                            proxy.scrollTo(lastMessage.id, anchor: .bottom)
                        }
                    }
                }
            }

            // Message input
            MessageInputView(
                text: $viewModel.messageInput,
                isEnabled: viewModel.connectionState == .connected,
                onSend: {
                    viewModel.sendMessage(communityId: communityId, channelName: channelName)
                },
                onTypingChange: { isTyping in
                    viewModel.sendTypingIndicator(
                        communityId: communityId,
                        channelName: channelName,
                        isTyping: isTyping
                    )
                }
            )
            .focused($isInputFocused)
        }
        .onAppear {
            viewModel.joinChannel(communityId: communityId, channelName: channelName)
        }
        .alert("Error", isPresented: .constant(viewModel.errorMessage != nil)) {
            Button("OK") {
                viewModel.clearError()
            }
        } message: {
            if let error = viewModel.errorMessage {
                Text(error)
            }
        }
    }
}

// MARK: - Connection Status Bar

struct ConnectionStatusBar: View {
    let connectionState: ConnectionState
    let onReconnect: () -> Void

    var body: some View {
        switch connectionState {
        case .connecting:
            HStack {
                ProgressView()
                    .scaleEffect(0.8)
                Text("Connecting...")
                    .font(.caption)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 8)
            .background(Color.blue.opacity(0.1))

        case .disconnected, .error:
            HStack {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundColor(.red)
                Text(connectionState == .error ? "Connection error" : "Disconnected")
                    .font(.caption)
                Spacer()
                Button("Reconnect") {
                    onReconnect()
                }
                .font(.caption)
                .buttonStyle(.bordered)
            }
            .padding(.horizontal)
            .padding(.vertical, 8)
            .background(Color.red.opacity(0.1))

        case .connected:
            EmptyView()
        }
    }
}

// MARK: - Typing Indicator

struct TypingIndicatorView: View {
    let typingUsers: Set<String>

    var body: some View {
        let text: String = {
            let users = Array(typingUsers)
            switch users.count {
            case 1:
                return "\(users[0]) is typing..."
            case 2:
                return "\(users.joined(separator: " and ")) are typing..."
            default:
                return "\(users.prefix(2).joined(separator: ", ")) and others are typing..."
            }
        }()

        Text(text)
            .font(.caption)
            .foregroundColor(.secondary)
            .padding(.horizontal)
            .padding(.vertical, 4)
            .frame(maxWidth: .infinity, alignment: .leading)
    }
}

// MARK: - Chat Message Row

struct ChatMessageRow: View {
    let message: ChatMessage
    let isOwnMessage: Bool

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            if !isOwnMessage {
                AvatarView(
                    avatarUrl: message.senderAvatarUrl,
                    username: message.senderUsername
                )
            }

            if isOwnMessage {
                Spacer(minLength: 60)
            }

            VStack(alignment: isOwnMessage ? .trailing : .leading, spacing: 4) {
                if !isOwnMessage {
                    Text(message.senderUsername)
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(.secondary)
                }

                Text(message.content)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(
                        isOwnMessage
                            ? Color.blue
                            : Color(.systemGray5)
                    )
                    .foregroundColor(isOwnMessage ? .white : .primary)
                    .clipShape(
                        RoundedRectangle(
                            cornerRadius: 16,
                            style: .continuous
                        )
                    )

                Text(message.formattedTime)
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }

            if !isOwnMessage {
                Spacer(minLength: 60)
            }
        }
    }
}

// MARK: - Avatar View

struct AvatarView: View {
    let avatarUrl: String?
    let username: String

    var body: some View {
        Group {
            if let urlString = avatarUrl, let url = URL(string: urlString) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                    case .failure, .empty:
                        PlaceholderAvatar(username: username)
                    @unknown default:
                        PlaceholderAvatar(username: username)
                    }
                }
            } else {
                PlaceholderAvatar(username: username)
            }
        }
        .frame(width: 36, height: 36)
        .clipShape(Circle())
    }
}

struct PlaceholderAvatar: View {
    let username: String

    var body: some View {
        ZStack {
            Color.blue
            Text(String(username.prefix(1)).uppercased())
                .font(.system(size: 16, weight: .medium))
                .foregroundColor(.white)
        }
    }
}

// MARK: - Message Input View

struct MessageInputView: View {
    @Binding var text: String
    let isEnabled: Bool
    let onSend: () -> Void
    let onTypingChange: (Bool) -> Void

    @State private var wasEmpty = true

    var body: some View {
        HStack(spacing: 8) {
            TextField("Type a message...", text: $text, axis: .vertical)
                .textFieldStyle(.roundedBorder)
                .lineLimit(1...4)
                .disabled(!isEnabled)
                .onChange(of: text) { newValue in
                    let isEmpty = newValue.isEmpty
                    if wasEmpty && !isEmpty {
                        onTypingChange(true)
                    } else if !wasEmpty && isEmpty {
                        onTypingChange(false)
                    }
                    wasEmpty = isEmpty
                }
                .onSubmit {
                    if !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        onSend()
                        onTypingChange(false)
                    }
                }

            Button(action: {
                if !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    onSend()
                    onTypingChange(false)
                }
            }) {
                Image(systemName: "paperplane.fill")
                    .foregroundColor(
                        isEnabled && !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                            ? .blue
                            : .gray
                    )
            }
            .disabled(!isEnabled || text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        }
        .padding()
        .background(Color(.systemBackground))
        .overlay(
            Rectangle()
                .frame(height: 1)
                .foregroundColor(Color(.separator)),
            alignment: .top
        )
    }
}

// MARK: - Chat View Model

@MainActor
final class ChatViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var messageInput: String = ""
    @Published var typingUsers: Set<String> = []
    @Published var isLoadingHistory: Bool = false
    @Published var errorMessage: String?

    var connectionState: ConnectionState {
        webSocketManager.connectionState
    }

    private let webSocketManager: WebSocketManager
    private var cancellables = Set<AnyCancellable>()

    init(webSocketManager: WebSocketManager) {
        self.webSocketManager = webSocketManager
        setupSubscriptions()
    }

    func joinChannel(communityId: String, channelName: String) {
        messages = []
        typingUsers = []
        isLoadingHistory = true

        webSocketManager.joinChannel(communityId: communityId, channelName: channelName)
        webSocketManager.requestHistory(communityId: communityId, channelName: channelName)
    }

    func sendMessage(communityId: String, channelName: String) {
        let content = messageInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !content.isEmpty else { return }

        webSocketManager.sendMessage(
            communityId: communityId,
            channelName: channelName,
            content: content,
            type: "text"
        )

        messageInput = ""
    }

    func sendTypingIndicator(communityId: String, channelName: String, isTyping: Bool) {
        webSocketManager.sendTypingIndicator(
            communityId: communityId,
            channelName: channelName,
            isTyping: isTyping
        )
    }

    func reconnect() {
        webSocketManager.reconnect()
    }

    func clearError() {
        errorMessage = nil
    }

    private func setupSubscriptions() {
        webSocketManager.incomingMessages
            .receive(on: DispatchQueue.main)
            .sink { [weak self] message in
                self?.messages.append(message)
            }
            .store(in: &cancellables)

        webSocketManager.typingEvents
            .receive(on: DispatchQueue.main)
            .sink { [weak self] event in
                if event.isTyping {
                    self?.typingUsers.insert(event.username)
                } else {
                    self?.typingUsers.remove(event.username)
                }
            }
            .store(in: &cancellables)

        webSocketManager.chatHistory
            .receive(on: DispatchQueue.main)
            .sink { [weak self] history in
                guard let self = self else { return }
                let existingIds = Set(self.messages.map { $0.id })
                let newMessages = history.filter { !existingIds.contains($0.id) }
                self.messages = newMessages + self.messages
                self.isLoadingHistory = false
            }
            .store(in: &cancellables)

        webSocketManager.$lastError
            .compactMap { $0?.errorDescription }
            .receive(on: DispatchQueue.main)
            .sink { [weak self] error in
                self?.errorMessage = error
            }
            .store(in: &cancellables)
    }
}

// MARK: - Preview

#Preview {
    ChatView(
        communityId: "test-community",
        channelName: "general",
        currentUserId: "user-123",
        webSocketManager: WebSocketManager(baseURL: URL(string: "wss://hub.waddlebot.io")!)
    )
}
