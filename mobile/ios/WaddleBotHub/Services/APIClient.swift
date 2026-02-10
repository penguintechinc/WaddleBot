import Foundation
import Combine

// MARK: - API Error

enum APIError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(statusCode: Int, message: String?)
    case decodingError(Error)
    case encodingError(Error)
    case networkError(Error)
    case unauthorized
    case serverError(String)
    case unknown

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let statusCode, let message):
            return message ?? "HTTP error: \(statusCode)"
        case .decodingError(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        case .encodingError(let error):
            return "Failed to encode request: \(error.localizedDescription)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .unauthorized:
            return "Unauthorized - please log in again"
        case .serverError(let message):
            return "Server error: \(message)"
        case .unknown:
            return "An unknown error occurred"
        }
    }
}

// MARK: - HTTP Method

enum HTTPMethod: String {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
    case patch = "PATCH"
    case delete = "DELETE"
}

// MARK: - API Client

final class APIClient {

    static let shared = APIClient()

    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder
    private let keychainService: KeychainService

    /// Publisher for unauthorized events (token expired/invalid)
    let unauthorizedPublisher = PassthroughSubject<Void, Never>()

    private init(
        keychainService: KeychainService = .shared
    ) {
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = Constants.Timeout.request
        configuration.timeoutIntervalForResource = Constants.Timeout.resource
        configuration.httpAdditionalHeaders = [
            "Accept": Constants.Headers.applicationJSON
        ]

        self.session = URLSession(configuration: configuration)
        self.decoder = .waddleBotDecoder
        self.encoder = .waddleBotEncoder
        self.keychainService = keychainService
    }

    // MARK: - Generic Request Method

    /// Performs a network request and decodes the response
    /// - Parameters:
    ///   - urlString: The URL string for the request
    ///   - method: HTTP method (default: GET)
    ///   - body: Optional request body (Encodable)
    ///   - requiresAuth: Whether to include authorization header (default: true)
    /// - Returns: Decoded response of type T
    func request<T: Decodable>(
        _ urlString: String,
        method: HTTPMethod = .get,
        body: (any Encodable)? = nil,
        requiresAuth: Bool = true
    ) async throws -> T {
        guard let url = URL(string: urlString) else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.setJSONContentType()

        // Add authorization header if required
        if requiresAuth, let token = keychainService.loadAccessToken() {
            request.setAuthorizationHeader(token: token)
        }

        // Encode body if provided
        if let body = body {
            do {
                request.httpBody = try encoder.encode(AnyEncodable(body))
            } catch {
                throw APIError.encodingError(error)
            }
        }

        // Perform request
        let data: Data
        let response: URLResponse

        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.networkError(error)
        }

        // Validate response
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        // Handle HTTP status codes
        switch httpResponse.statusCode {
        case 200...299:
            break
        case 401:
            unauthorizedPublisher.send()
            throw APIError.unauthorized
        case 400...499:
            let message = extractErrorMessage(from: data)
            throw APIError.httpError(statusCode: httpResponse.statusCode, message: message)
        case 500...599:
            let message = extractErrorMessage(from: data) ?? "Internal server error"
            throw APIError.serverError(message)
        default:
            throw APIError.httpError(statusCode: httpResponse.statusCode, message: nil)
        }

        // Decode response
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }

    /// Performs a request without expecting a response body
    func requestVoid(
        _ urlString: String,
        method: HTTPMethod = .post,
        body: (any Encodable)? = nil,
        requiresAuth: Bool = true
    ) async throws {
        guard let url = URL(string: urlString) else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.setJSONContentType()

        if requiresAuth, let token = keychainService.loadAccessToken() {
            request.setAuthorizationHeader(token: token)
        }

        if let body = body {
            do {
                request.httpBody = try encoder.encode(AnyEncodable(body))
            } catch {
                throw APIError.encodingError(error)
            }
        }

        let data: Data
        let response: URLResponse

        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.networkError(error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200...299:
            return
        case 401:
            unauthorizedPublisher.send()
            throw APIError.unauthorized
        case 400...499:
            let message = extractErrorMessage(from: data)
            throw APIError.httpError(statusCode: httpResponse.statusCode, message: message)
        case 500...599:
            let message = extractErrorMessage(from: data) ?? "Internal server error"
            throw APIError.serverError(message)
        default:
            throw APIError.httpError(statusCode: httpResponse.statusCode, message: nil)
        }
    }

    // MARK: - Auth Endpoints

    func login(email: String, password: String) async throws -> LoginResponse {
        let body = LoginRequest(email: email, password: password)
        return try await request(
            Constants.API.loginURL,
            method: .post,
            body: body,
            requiresAuth: false
        )
    }

    func refreshToken() async throws -> RefreshResponse {
        return try await request(
            Constants.API.refreshURL,
            method: .post
        )
    }

    func getCurrentUser() async throws -> UserResponse {
        return try await request(
            Constants.API.meURL,
            method: .get
        )
    }

    func logout() async throws -> LogoutResponse {
        return try await request(
            Constants.API.logoutURL,
            method: .post
        )
    }

    // MARK: - Community Endpoints

    func getMyCommunities() async throws -> CommunitiesResponse {
        return try await request(
            Constants.API.myCommunitiesURL,
            method: .get
        )
    }

    func getCommunityDashboard(communityId: String) async throws -> DashboardResponse {
        return try await request(
            Constants.API.communityDashboardURL(id: communityId),
            method: .get
        )
    }

    func getCommunityMembers(communityId: String) async throws -> MembersResponse {
        return try await request(
            Constants.API.communityMembersURL(id: communityId),
            method: .get
        )
    }

    // MARK: - Private Helpers

    private func extractErrorMessage(from data: Data) -> String? {
        struct ErrorResponse: Decodable {
            let message: String?
            let error: String?
        }

        if let errorResponse = try? decoder.decode(ErrorResponse.self, from: data) {
            return errorResponse.message ?? errorResponse.error
        }
        return nil
    }
}

// MARK: - AnyEncodable Helper

struct AnyEncodable: Encodable {
    private let encode: (Encoder) throws -> Void

    init<T: Encodable>(_ value: T) {
        encode = value.encode
    }

    func encode(to encoder: Encoder) throws {
        try encode(encoder)
    }
}
