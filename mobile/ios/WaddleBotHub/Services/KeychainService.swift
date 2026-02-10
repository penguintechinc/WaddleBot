import Foundation
import Security

/// Keychain service for secure token storage
final class KeychainService {

    static let shared = KeychainService()

    private init() {}

    // MARK: - Public Methods

    /// Saves a string value to the keychain
    /// - Parameters:
    ///   - value: The string value to save
    ///   - key: The key to associate with the value
    /// - Returns: True if save was successful
    @discardableResult
    func save(_ value: String, forKey key: String) -> Bool {
        guard let data = value.data(using: .utf8) else {
            return false
        }
        return save(data, forKey: key)
    }

    /// Saves data to the keychain
    /// - Parameters:
    ///   - data: The data to save
    ///   - key: The key to associate with the data
    /// - Returns: True if save was successful
    @discardableResult
    func save(_ data: Data, forKey key: String) -> Bool {
        // Delete existing item first
        delete(forKey: key)

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Constants.Keychain.service,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]

        let status = SecItemAdd(query as CFDictionary, nil)
        return status == errSecSuccess
    }

    /// Loads a string value from the keychain
    /// - Parameter key: The key associated with the value
    /// - Returns: The string value if found, nil otherwise
    func loadString(forKey key: String) -> String? {
        guard let data = loadData(forKey: key) else {
            return nil
        }
        return String(data: data, encoding: .utf8)
    }

    /// Loads data from the keychain
    /// - Parameter key: The key associated with the data
    /// - Returns: The data if found, nil otherwise
    func loadData(forKey key: String) -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Constants.Keychain.service,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess else {
            return nil
        }

        return result as? Data
    }

    /// Deletes a value from the keychain
    /// - Parameter key: The key associated with the value to delete
    /// - Returns: True if deletion was successful or item didn't exist
    @discardableResult
    func delete(forKey key: String) -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Constants.Keychain.service,
            kSecAttrAccount as String: key
        ]

        let status = SecItemDelete(query as CFDictionary)
        return status == errSecSuccess || status == errSecItemNotFound
    }

    /// Checks if a value exists in the keychain
    /// - Parameter key: The key to check
    /// - Returns: True if the key exists
    func exists(forKey key: String) -> Bool {
        loadData(forKey: key) != nil
    }

    /// Deletes all items for this service
    @discardableResult
    func deleteAll() -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Constants.Keychain.service
        ]

        let status = SecItemDelete(query as CFDictionary)
        return status == errSecSuccess || status == errSecItemNotFound
    }

    // MARK: - Token Convenience Methods

    /// Saves the access token
    @discardableResult
    func saveAccessToken(_ token: String) -> Bool {
        save(token, forKey: Constants.Keychain.accessTokenKey)
    }

    /// Loads the access token
    func loadAccessToken() -> String? {
        loadString(forKey: Constants.Keychain.accessTokenKey)
    }

    /// Deletes the access token
    @discardableResult
    func deleteAccessToken() -> Bool {
        delete(forKey: Constants.Keychain.accessTokenKey)
    }

    /// Saves the refresh token
    @discardableResult
    func saveRefreshToken(_ token: String) -> Bool {
        save(token, forKey: Constants.Keychain.refreshTokenKey)
    }

    /// Loads the refresh token
    func loadRefreshToken() -> String? {
        loadString(forKey: Constants.Keychain.refreshTokenKey)
    }

    /// Deletes the refresh token
    @discardableResult
    func deleteRefreshToken() -> Bool {
        delete(forKey: Constants.Keychain.refreshTokenKey)
    }

    /// Clears all authentication tokens
    func clearAuthTokens() {
        deleteAccessToken()
        deleteRefreshToken()
        delete(forKey: Constants.Keychain.userIdKey)
    }
}
