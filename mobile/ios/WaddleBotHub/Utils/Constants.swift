import Foundation

enum Constants {

    // MARK: - API Configuration

    enum API {
        static let baseURL = "https://hub.waddlebot.io"
        static let apiVersion = "v1"

        static var baseAPIURL: String {
            "\(baseURL)/api/\(apiVersion)"
        }

        // Auth endpoints
        static var loginURL: String { "\(baseAPIURL)/auth/login" }
        static var refreshURL: String { "\(baseAPIURL)/auth/refresh" }
        static var meURL: String { "\(baseAPIURL)/auth/me" }
        static var logoutURL: String { "\(baseAPIURL)/auth/logout" }

        // Community endpoints
        static var myCommunitiesURL: String { "\(baseAPIURL)/community/my" }

        static func communityDashboardURL(id: String) -> String {
            "\(baseAPIURL)/community/\(id)/dashboard"
        }

        static func communityMembersURL(id: String) -> String {
            "\(baseAPIURL)/community/\(id)/members"
        }
    }

    // MARK: - Keychain Keys

    enum Keychain {
        static let service = "io.waddlebot.hub"
        static let accessTokenKey = "access_token"
        static let refreshTokenKey = "refresh_token"
        static let userIdKey = "user_id"
    }

    // MARK: - HTTP Headers

    enum Headers {
        static let authorization = "Authorization"
        static let contentType = "Content-Type"
        static let accept = "Accept"
        static let bearerPrefix = "Bearer "
        static let applicationJSON = "application/json"
    }

    // MARK: - Timeouts

    enum Timeout {
        static let request: TimeInterval = 30.0
        static let resource: TimeInterval = 60.0
    }

    // MARK: - App Info

    enum App {
        static let name = "WaddleBot"
        static let bundleId = "io.waddlebot.hub"
        static let minimumIOSVersion = "15.0"
    }
}
