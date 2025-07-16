import Foundation
import Combine

class AuthenticationManager: ObservableObject {
    @Published var isAuthenticated = false
    @Published var currentUser: User? = nil
    @Published var isLoading = false
    @Published var errorMessage: String? = nil
    
    private var cancellables = Set<AnyCancellable>()
    private let apiClient = APIClient.shared
    
    init() {
        // Check if user is already authenticated
        isAuthenticated = UserDefaults.standard.string(forKey: StorageKeys.userToken) != nil
        currentUser = UserDefaults.standard.getObject(User.self, forKey: StorageKeys.userData)
    }
    
    // MARK: - Authentication Methods
    func login(email: String, password: String) async {
        await MainActor.run {
            isLoading = true
            errorMessage = nil
        }
        
        apiClient.login(email: email, password: password)
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { [weak self] completion in
                    self?.isLoading = false
                    if case .failure(let error) = completion {
                        self?.handleAuthError(error)
                    }
                },
                receiveValue: { [weak self] authResponse in
                    self?.handleSuccessfulAuth(authResponse)
                }
            )
            .store(in: &cancellables)
    }
    
    func logout() async {
        await MainActor.run {
            isLoading = true
        }
        
        apiClient.logout()
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { [weak self] completion in
                    self?.isLoading = false
                    // Clear local data regardless of API response
                    self?.clearAuthData()
                },
                receiveValue: { [weak self] _ in
                    self?.clearAuthData()
                }
            )
            .store(in: &cancellables)
    }
    
    func refreshToken() async {
        guard UserDefaults.standard.string(forKey: StorageKeys.refreshToken) != nil else {
            await logout()
            return
        }
        
        apiClient.refreshToken()
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { [weak self] completion in
                    if case .failure(_) = completion {
                        // Refresh failed, logout user
                        Task {
                            await self?.logout()
                        }
                    }
                },
                receiveValue: { [weak self] authResponse in
                    self?.handleSuccessfulAuth(authResponse)
                }
            )
            .store(in: &cancellables)
    }
    
    func checkAuthenticationStatus() async {
        guard let token = UserDefaults.standard.string(forKey: StorageKeys.userToken) else {
            await MainActor.run {
                isAuthenticated = false
                currentUser = nil
            }
            return
        }
        
        // Check if token is expired
        if isTokenExpired() {
            await refreshToken()
        } else {
            await MainActor.run {
                isAuthenticated = true
                currentUser = UserDefaults.standard.getObject(User.self, forKey: StorageKeys.userData)
            }
        }
        
        // Verify premium status if required
        if AppConfig.premiumRequired {
            await verifyPremiumStatus()
        }
    }
    
    func verifyPremiumStatus() async {
        apiClient.verifyPremium()
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { [weak self] completion in
                    if case .failure(_) = completion {
                        // Premium verification failed
                        self?.errorMessage = "Premium subscription required"
                        Task {
                            await self?.logout()
                        }
                    }
                },
                receiveValue: { [weak self] premiumStatus in
                    if !premiumStatus.isPremium {
                        self?.errorMessage = "Premium subscription required"
                        Task {
                            await self?.logout()
                        }
                    } else {
                        UserDefaults.standard.set(premiumStatus.isPremium, forKey: StorageKeys.premiumStatus)
                    }
                }
            )
            .store(in: &cancellables)
    }
    
    // MARK: - Private Methods
    private func handleSuccessfulAuth(_ authResponse: AuthResponse) {
        // Save tokens and user data
        UserDefaults.standard.set(authResponse.token, forKey: StorageKeys.userToken)
        UserDefaults.standard.set(authResponse.refreshToken, forKey: StorageKeys.refreshToken)
        UserDefaults.standard.setObject(authResponse.user, forKey: StorageKeys.userData)
        
        // Update state
        isAuthenticated = true
        currentUser = authResponse.user
        errorMessage = nil
        
        // Schedule token refresh
        scheduleTokenRefresh(expiresAt: authResponse.expiresAt)
    }
    
    private func handleAuthError(_ error: NetworkError) {
        switch error {
        case .unauthorized:
            errorMessage = "Invalid email or password"
        case .forbidden:
            errorMessage = "Access denied"
        case .networkError:
            errorMessage = "Network error. Please check your connection."
        case .serverError:
            errorMessage = "Server error. Please try again later."
        case .timeout:
            errorMessage = "Request timeout. Please try again."
        default:
            errorMessage = "An unexpected error occurred"
        }
        
        isAuthenticated = false
        currentUser = nil
    }
    
    private func clearAuthData() {
        UserDefaults.standard.removeObject(forKey: StorageKeys.userToken)
        UserDefaults.standard.removeObject(forKey: StorageKeys.refreshToken)
        UserDefaults.standard.removeObject(forKey: StorageKeys.userData)
        UserDefaults.standard.removeObject(forKey: StorageKeys.premiumStatus)
        
        isAuthenticated = false
        currentUser = nil
        errorMessage = nil
    }
    
    private func isTokenExpired() -> Bool {
        // Check if token is close to expiration
        // This is a simplified check - in real implementation, you'd decode the JWT
        guard let lastLogin = UserDefaults.standard.object(forKey: "last_login") as? Date else {
            return true
        }
        
        let expirationTime = lastLogin.addingTimeInterval(AppConfig.sessionTimeout)
        let refreshThreshold = expirationTime.addingTimeInterval(-AppConfig.refreshTokenThreshold)
        
        return Date() > refreshThreshold
    }
    
    private func scheduleTokenRefresh(expiresAt: Date) {
        let refreshTime = expiresAt.addingTimeInterval(-AppConfig.refreshTokenThreshold)
        let timeInterval = refreshTime.timeIntervalSinceNow
        
        if timeInterval > 0 {
            Timer.scheduledTimer(withTimeInterval: timeInterval, repeats: false) { [weak self] _ in
                Task {
                    await self?.refreshToken()
                }
            }
        }
    }
    
    // MARK: - Permission Helpers
    func hasPermission(_ permission: String, in communityId: String) -> Bool {
        // This would typically fetch permissions from the API or cache
        // For now, we'll use a simplified role-based check
        guard let user = currentUser else { return false }
        
        // In a real implementation, you'd fetch the user's role for the specific community
        // For demo purposes, we'll assume admin role
        return PermissionUtils.hasPermission(userRole: "admin", permission: permission)
    }
    
    func getUserRole(in communityId: String) -> String? {
        // This would typically be fetched from the API
        // For demo purposes, return admin
        return "admin"
    }
}