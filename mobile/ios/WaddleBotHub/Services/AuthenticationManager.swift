import Foundation
import Combine

/// Authentication state for the app
enum AuthenticationState: Equatable {
    case unknown
    case authenticated(User)
    case unauthenticated
}

/// Manages authentication state and operations
@MainActor
final class AuthenticationManager: ObservableObject {

    static let shared = AuthenticationManager()

    // MARK: - Published Properties

    @Published private(set) var state: AuthenticationState = .unknown
    @Published private(set) var currentUser: User?
    @Published private(set) var isLoading: Bool = false
    @Published private(set) var error: String?

    // MARK: - Private Properties

    private let apiClient: APIClient
    private let keychainService: KeychainService
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Computed Properties

    var isAuthenticated: Bool {
        if case .authenticated = state {
            return true
        }
        return false
    }

    var hasToken: Bool {
        keychainService.loadAccessToken() != nil
    }

    // MARK: - Initialization

    private init(
        apiClient: APIClient = .shared,
        keychainService: KeychainService = .shared
    ) {
        self.apiClient = apiClient
        self.keychainService = keychainService

        setupUnauthorizedHandler()
    }

    // MARK: - Setup

    private func setupUnauthorizedHandler() {
        apiClient.unauthorizedPublisher
            .receive(on: DispatchQueue.main)
            .sink { [weak self] in
                self?.handleUnauthorized()
            }
            .store(in: &cancellables)
    }

    // MARK: - Public Methods

    /// Checks for existing token and validates session on app launch
    func checkAuthenticationStatus() async {
        guard hasToken else {
            state = .unauthenticated
            return
        }

        isLoading = true
        error = nil

        do {
            let response = try await apiClient.getCurrentUser()

            if response.success, let user = response.user {
                currentUser = user
                state = .authenticated(user)
            } else {
                // Token is invalid, clear and set unauthenticated
                await logout()
            }
        } catch {
            // Token validation failed, but keep user logged in if network error
            if case APIError.networkError = error {
                // Assume still authenticated for network errors
                state = .unauthenticated
            } else {
                await logout()
            }
        }

        isLoading = false
    }

    /// Logs in with email and password
    /// - Parameters:
    ///   - email: User's email address
    ///   - password: User's password
    /// - Returns: The authenticated user
    @discardableResult
    func login(email: String, password: String) async throws -> User {
        isLoading = true
        error = nil

        defer { isLoading = false }

        do {
            let response = try await apiClient.login(email: email, password: password)

            guard response.success else {
                let errorMessage = response.message ?? "Login failed"
                self.error = errorMessage
                throw APIError.serverError(errorMessage)
            }

            guard let token = response.token, let user = response.user else {
                let errorMessage = "Invalid login response"
                self.error = errorMessage
                throw APIError.serverError(errorMessage)
            }

            // Save token to keychain
            keychainService.saveAccessToken(token)
            keychainService.save(user.id, forKey: Constants.Keychain.userIdKey)

            // Update state
            currentUser = user
            state = .authenticated(user)

            return user
        } catch let apiError as APIError {
            self.error = apiError.localizedDescription
            throw apiError
        } catch {
            self.error = error.localizedDescription
            throw error
        }
    }

    /// Refreshes the authentication token
    func refreshToken() async throws {
        guard hasToken else {
            throw APIError.unauthorized
        }

        let response = try await apiClient.refreshToken()

        guard response.success, let newToken = response.token else {
            throw APIError.serverError(response.message ?? "Token refresh failed")
        }

        keychainService.saveAccessToken(newToken)
    }

    /// Logs out the current user
    func logout() async {
        isLoading = true

        // Try to notify server (ignore errors)
        do {
            _ = try await apiClient.logout()
        } catch {
            // Ignore logout API errors
        }

        // Clear local state
        keychainService.clearAuthTokens()
        currentUser = nil
        state = .unauthenticated
        error = nil
        isLoading = false
    }

    /// Fetches the current user profile
    func fetchCurrentUser() async throws -> User {
        let response = try await apiClient.getCurrentUser()

        guard response.success, let user = response.user else {
            throw APIError.serverError(response.message ?? "Failed to fetch user")
        }

        currentUser = user
        state = .authenticated(user)
        return user
    }

    /// Clears any error state
    func clearError() {
        error = nil
    }

    // MARK: - Private Methods

    private func handleUnauthorized() {
        Task {
            await logout()
        }
    }
}

// MARK: - Preview Helper

#if DEBUG
extension AuthenticationManager {
    static var preview: AuthenticationManager {
        let manager = AuthenticationManager()
        return manager
    }

    static var previewAuthenticated: AuthenticationManager {
        let manager = AuthenticationManager()
        let mockUser = User(
            id: "preview-user-id",
            email: "test@example.com",
            username: "testuser",
            avatarUrl: nil,
            isSuperAdmin: false,
            linkedPlatforms: ["twitch", "discord"]
        )
        manager.currentUser = mockUser
        manager.state = .authenticated(mockUser)
        return manager
    }
}
#endif
