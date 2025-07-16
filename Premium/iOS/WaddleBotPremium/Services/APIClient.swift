import Foundation
import Combine

class APIClient: ObservableObject {
    static let shared = APIClient()
    
    private var cancellables = Set<AnyCancellable>()
    private let session = URLSession.shared
    private let baseURL = URL(string: APIConfig.baseURL)!
    
    // MARK: - Authentication Headers
    private var authHeaders: [String: String] {
        var headers = [
            "Content-Type": "application/json",
            "Accept": "application/json"
        ]
        
        if let token = UserDefaults.standard.string(forKey: StorageKeys.userToken) {
            headers["Authorization"] = "Bearer \(token)"
        }
        
        return headers
    }
    
    // MARK: - Generic Request Methods
    func request<T: Codable>(
        endpoint: String,
        method: HTTPMethod = .GET,
        body: Data? = nil,
        headers: [String: String]? = nil
    ) -> AnyPublisher<T, NetworkError> {
        guard let url = URL(string: endpoint, relativeTo: baseURL) else {
            return Fail(error: NetworkError.invalidURL)
                .eraseToAnyPublisher()
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.httpBody = body
        request.timeoutInterval = APIConfig.timeout
        
        // Set headers
        var requestHeaders = authHeaders
        if let additionalHeaders = headers {
            requestHeaders.merge(additionalHeaders) { _, new in new }
        }
        
        for (key, value) in requestHeaders {
            request.setValue(value, forHTTPHeaderField: key)
        }
        
        return session.dataTaskPublisher(for: request)
            .map(\.data)
            .decode(type: APIResponse<T>.self, decoder: JSONDecoder.waddleBotDecoder)
            .tryMap { response in
                if response.success, let data = response.data {
                    return data
                } else {
                    throw NetworkError.serverError
                }
            }
            .mapError { error in
                if let networkError = error as? NetworkError {
                    return networkError
                } else if let decodingError = error as? DecodingError {
                    print("Decoding error: \(decodingError)")
                    return NetworkError.decodingError
                } else {
                    return NetworkError.networkError(error)
                }
            }
            .eraseToAnyPublisher()
    }
    
    func requestPaginated<T: Codable>(
        endpoint: String,
        method: HTTPMethod = .GET,
        body: Data? = nil,
        headers: [String: String]? = nil
    ) -> AnyPublisher<PaginatedResponse<T>, NetworkError> {
        guard let url = URL(string: endpoint, relativeTo: baseURL) else {
            return Fail(error: NetworkError.invalidURL)
                .eraseToAnyPublisher()
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.httpBody = body
        request.timeoutInterval = APIConfig.timeout
        
        // Set headers
        var requestHeaders = authHeaders
        if let additionalHeaders = headers {
            requestHeaders.merge(additionalHeaders) { _, new in new }
        }
        
        for (key, value) in requestHeaders {
            request.setValue(value, forHTTPHeaderField: key)
        }
        
        return session.dataTaskPublisher(for: request)
            .map(\.data)
            .decode(type: PaginatedResponse<T>.self, decoder: JSONDecoder.waddleBotDecoder)
            .mapError { error in
                if let decodingError = error as? DecodingError {
                    print("Decoding error: \(decodingError)")
                    return NetworkError.decodingError
                } else {
                    return NetworkError.networkError(error)
                }
            }
            .eraseToAnyPublisher()
    }
    
    // MARK: - Authentication
    func login(email: String, password: String) -> AnyPublisher<AuthResponse, NetworkError> {
        let loginRequest = LoginRequest(email: email, password: password)
        let body = try? JSONEncoder().encode(loginRequest)
        
        return request<AuthResponse>(
            endpoint: Endpoints.login,
            method: .POST,
            body: body
        )
    }
    
    func refreshToken() -> AnyPublisher<AuthResponse, NetworkError> {
        guard let refreshToken = UserDefaults.standard.string(forKey: StorageKeys.refreshToken) else {
            return Fail(error: NetworkError.unauthorized)
                .eraseToAnyPublisher()
        }
        
        let refreshRequest = RefreshTokenRequest(refreshToken: refreshToken)
        let body = try? JSONEncoder().encode(refreshRequest)
        
        return request<AuthResponse>(
            endpoint: Endpoints.refresh,
            method: .POST,
            body: body
        )
    }
    
    func logout() -> AnyPublisher<Void, NetworkError> {
        return request<EmptyResponse>(
            endpoint: Endpoints.logout,
            method: .POST
        )
        .map { _ in () }
        .eraseToAnyPublisher()
    }
    
    func verifyPremium() -> AnyPublisher<PremiumStatus, NetworkError> {
        return request<PremiumStatus>(
            endpoint: Endpoints.verifyPremium,
            method: .GET
        )
    }
    
    // MARK: - User Management
    func getUserProfile() -> AnyPublisher<User, NetworkError> {
        return request<User>(
            endpoint: Endpoints.userProfile,
            method: .GET
        )
    }
    
    func getUserCommunities() -> AnyPublisher<[Community], NetworkError> {
        return request<[Community]>(
            endpoint: Endpoints.userCommunities,
            method: .GET
        )
    }
    
    func getUserPermissions(communityId: String) -> AnyPublisher<[String], NetworkError> {
        return request<[String]>(
            endpoint: "\(Endpoints.userPermissions)?communityId=\(communityId)",
            method: .GET
        )
    }
    
    // MARK: - Community Management
    func getCommunities() -> AnyPublisher<PaginatedResponse<Community>, NetworkError> {
        return requestPaginated<Community>(
            endpoint: Endpoints.communities,
            method: .GET
        )
    }
    
    func getCommunity(id: String) -> AnyPublisher<Community, NetworkError> {
        return request<Community>(
            endpoint: "\(Endpoints.communities)/\(id)",
            method: .GET
        )
    }
    
    func getCommunitySettings(id: String) -> AnyPublisher<CommunitySettings, NetworkError> {
        return request<CommunitySettings>(
            endpoint: Endpoints.communitySettings.replacingOccurrences(of: "{id}", with: id),
            method: .GET
        )
    }
    
    func updateCommunitySettings(id: String, settings: CommunitySettings) -> AnyPublisher<CommunitySettings, NetworkError> {
        let body = try? JSONEncoder().encode(settings)
        return request<CommunitySettings>(
            endpoint: Endpoints.communitySettings.replacingOccurrences(of: "{id}", with: id),
            method: .PUT,
            body: body
        )
    }
    
    // MARK: - Member Management
    func getCommunityMembers(communityId: String, page: Int = 1, limit: Int = 20) -> AnyPublisher<PaginatedResponse<Member>, NetworkError> {
        let endpoint = "\(Endpoints.communityMembers.replacingOccurrences(of: "{id}", with: communityId))?page=\(page)&limit=\(limit)"
        return requestPaginated<Member>(
            endpoint: endpoint,
            method: .GET
        )
    }
    
    func getMember(communityId: String, memberId: String) -> AnyPublisher<Member, NetworkError> {
        return request<Member>(
            endpoint: "\(Endpoints.communityMembers.replacingOccurrences(of: "{id}", with: communityId))/\(memberId)",
            method: .GET
        )
    }
    
    func updateMember(communityId: String, memberId: String, update: MemberUpdate) -> AnyPublisher<Member, NetworkError> {
        let body = try? JSONEncoder().encode(update)
        return request<Member>(
            endpoint: "\(Endpoints.communityMembers.replacingOccurrences(of: "{id}", with: communityId))/\(memberId)",
            method: .PUT,
            body: body
        )
    }
    
    func removeMember(communityId: String, memberId: String) -> AnyPublisher<Void, NetworkError> {
        return request<EmptyResponse>(
            endpoint: "\(Endpoints.communityMembers.replacingOccurrences(of: "{id}", with: communityId))/\(memberId)",
            method: .DELETE
        )
        .map { _ in () }
        .eraseToAnyPublisher()
    }
    
    // MARK: - Currency Management
    func getCurrencySettings(communityId: String) -> AnyPublisher<CurrencySettings, NetworkError> {
        return request<CurrencySettings>(
            endpoint: Endpoints.currencySettings.replacingOccurrences(of: "{id}", with: communityId),
            method: .GET
        )
    }
    
    func updateCurrencySettings(communityId: String, settings: CurrencySettings) -> AnyPublisher<CurrencySettings, NetworkError> {
        let body = try? JSONEncoder().encode(settings)
        return request<CurrencySettings>(
            endpoint: Endpoints.currencySettings.replacingOccurrences(of: "{id}", with: communityId),
            method: .PUT,
            body: body
        )
    }
    
    func getMemberCurrencyBalance(communityId: String, memberId: String) -> AnyPublisher<CurrencyBalance, NetworkError> {
        return request<CurrencyBalance>(
            endpoint: Endpoints.currencyBalance
                .replacingOccurrences(of: "{id}", with: communityId)
                .replacingOccurrences(of: "{memberId}", with: memberId),
            method: .GET
        )
    }
    
    func getCurrencyTransactions(communityId: String, page: Int = 1, limit: Int = 20) -> AnyPublisher<PaginatedResponse<CurrencyTransaction>, NetworkError> {
        let endpoint = "\(Endpoints.currencyTransactions.replacingOccurrences(of: "{id}", with: communityId))?page=\(page)&limit=\(limit)"
        return requestPaginated<CurrencyTransaction>(
            endpoint: endpoint,
            method: .GET
        )
    }
    
    func getCurrencyStatistics(communityId: String) -> AnyPublisher<CurrencyStatistics, NetworkError> {
        return request<CurrencyStatistics>(
            endpoint: "\(Endpoints.currencySettings.replacingOccurrences(of: "{id}", with: communityId))/stats",
            method: .GET
        )
    }
    
    // MARK: - Payment Management
    func getPaymentMethods(communityId: String) -> AnyPublisher<[PaymentMethod], NetworkError> {
        return request<[PaymentMethod]>(
            endpoint: "\(Endpoints.paymentMethods)?communityId=\(communityId)",
            method: .GET
        )
    }
    
    func processPayment(request: PaymentRequest) -> AnyPublisher<PaymentTransaction, NetworkError> {
        let body = try? JSONEncoder().encode(request)
        return self.request<PaymentTransaction>(
            endpoint: Endpoints.paymentProcess,
            method: .POST,
            body: body
        )
    }
    
    func getPaymentHistory(communityId: String, page: Int = 1, limit: Int = 20) -> AnyPublisher<PaginatedResponse<PaymentTransaction>, NetworkError> {
        let endpoint = "\(Endpoints.paymentHistory)?communityId=\(communityId)&page=\(page)&limit=\(limit)"
        return requestPaginated<PaymentTransaction>(
            endpoint: endpoint,
            method: .GET
        )
    }
    
    // MARK: - Raffle Management
    func getRaffles(communityId: String, page: Int = 1, limit: Int = 20) -> AnyPublisher<PaginatedResponse<Raffle>, NetworkError> {
        let endpoint = "\(Endpoints.raffles.replacingOccurrences(of: "{id}", with: communityId))?page=\(page)&limit=\(limit)"
        return requestPaginated<Raffle>(
            endpoint: endpoint,
            method: .GET
        )
    }
    
    func createRaffle(communityId: String, raffle: RaffleCreate) -> AnyPublisher<Raffle, NetworkError> {
        let body = try? JSONEncoder().encode(raffle)
        return request<Raffle>(
            endpoint: Endpoints.raffles.replacingOccurrences(of: "{id}", with: communityId),
            method: .POST,
            body: body
        )
    }
    
    func getRaffleEntries(communityId: String, raffleId: String) -> AnyPublisher<[RaffleEntry], NetworkError> {
        return request<[RaffleEntry]>(
            endpoint: Endpoints.raffleEntries
                .replacingOccurrences(of: "{id}", with: communityId)
                .replacingOccurrences(of: "{raffleId}", with: raffleId),
            method: .GET
        )
    }
    
    func enterRaffle(communityId: String, raffleId: String, entries: Int) -> AnyPublisher<RaffleEntry, NetworkError> {
        let body = try? JSONEncoder().encode(["entries": entries])
        return request<RaffleEntry>(
            endpoint: Endpoints.raffleEntries
                .replacingOccurrences(of: "{id}", with: communityId)
                .replacingOccurrences(of: "{raffleId}", with: raffleId),
            method: .POST,
            body: body
        )
    }
    
    // MARK: - Giveaway Management
    func getGiveaways(communityId: String, page: Int = 1, limit: Int = 20) -> AnyPublisher<PaginatedResponse<Giveaway>, NetworkError> {
        let endpoint = "\(Endpoints.giveaways.replacingOccurrences(of: "{id}", with: communityId))?page=\(page)&limit=\(limit)"
        return requestPaginated<Giveaway>(
            endpoint: endpoint,
            method: .GET
        )
    }
    
    func createGiveaway(communityId: String, giveaway: GiveawayCreate) -> AnyPublisher<Giveaway, NetworkError> {
        let body = try? JSONEncoder().encode(giveaway)
        return request<Giveaway>(
            endpoint: Endpoints.giveaways.replacingOccurrences(of: "{id}", with: communityId),
            method: .POST,
            body: body
        )
    }
    
    func enterGiveaway(communityId: String, giveawayId: String) -> AnyPublisher<GiveawayEntry, NetworkError> {
        return request<GiveawayEntry>(
            endpoint: Endpoints.giveawayEntries
                .replacingOccurrences(of: "{id}", with: communityId)
                .replacingOccurrences(of: "{giveawayId}", with: giveawayId),
            method: .POST
        )
    }
}

// MARK: - Supporting Types
enum HTTPMethod: String {
    case GET = "GET"
    case POST = "POST"
    case PUT = "PUT"
    case DELETE = "DELETE"
    case PATCH = "PATCH"
}

struct EmptyResponse: Codable {}

struct PremiumStatus: Codable {
    let isPremium: Bool
    let expiresAt: Date?
    let plan: String?
    
    enum CodingKeys: String, CodingKey {
        case plan
        case isPremium = "is_premium"
        case expiresAt = "expires_at"
    }
}

struct RaffleCreate: Codable {
    let title: String
    let description: String
    let entryCost: Int
    let maxEntries: Int
    let maxWinners: Int
    let duration: Int
    
    enum CodingKeys: String, CodingKey {
        case title, description, duration
        case entryCost = "entry_cost"
        case maxEntries = "max_entries"
        case maxWinners = "max_winners"
    }
}

struct GiveawayCreate: Codable {
    let title: String
    let description: String
    let entryCost: Int
    let maxWinners: Int
    let duration: Int
    
    enum CodingKeys: String, CodingKey {
        case title, description, duration
        case entryCost = "entry_cost"
        case maxWinners = "max_winners"
    }
}

// MARK: - JSON Decoder Extension
extension JSONDecoder {
    static let waddleBotDecoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }()
}

extension JSONEncoder {
    static let waddleBotEncoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }()
}