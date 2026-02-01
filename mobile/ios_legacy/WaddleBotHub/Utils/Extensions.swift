import Foundation

// MARK: - Date Extensions

extension Date {

    /// Formats date for display (e.g., "Jan 15, 2025")
    var displayString: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .none
        return formatter.string(from: self)
    }

    /// Formats date with time (e.g., "Jan 15, 2025 at 3:30 PM")
    var displayStringWithTime: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: self)
    }

    /// Returns relative time string (e.g., "5 minutes ago")
    var relativeString: String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .full
        return formatter.localizedString(for: self, relativeTo: Date())
    }

    /// ISO8601 formatted string for API requests
    var iso8601String: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.string(from: self)
    }
}

// MARK: - String Extensions

extension String {

    /// Validates email format
    var isValidEmail: Bool {
        let emailRegex = #"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"#
        return range(of: emailRegex, options: .regularExpression) != nil
    }

    /// Validates password meets minimum requirements (8+ characters)
    var isValidPassword: Bool {
        count >= 8
    }

    /// Trims whitespace and newlines
    var trimmed: String {
        trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Returns nil if string is empty after trimming
    var nilIfEmpty: String? {
        let trimmed = self.trimmed
        return trimmed.isEmpty ? nil : trimmed
    }

    /// Safely creates URL from string
    var asURL: URL? {
        URL(string: self)
    }
}

// MARK: - Data Extensions

extension Data {

    /// Pretty prints JSON data for debugging
    var prettyPrintedJSON: String? {
        guard let object = try? JSONSerialization.jsonObject(with: self),
              let data = try? JSONSerialization.data(withJSONObject: object, options: .prettyPrinted),
              let string = String(data: data, encoding: .utf8) else {
            return nil
        }
        return string
    }
}

// MARK: - URLRequest Extensions

extension URLRequest {

    /// Adds JSON content type headers
    mutating func setJSONContentType() {
        setValue(Constants.Headers.applicationJSON, forHTTPHeaderField: Constants.Headers.contentType)
        setValue(Constants.Headers.applicationJSON, forHTTPHeaderField: Constants.Headers.accept)
    }

    /// Adds authorization header with bearer token
    mutating func setAuthorizationHeader(token: String) {
        setValue("\(Constants.Headers.bearerPrefix)\(token)", forHTTPHeaderField: Constants.Headers.authorization)
    }
}

// MARK: - Optional Extensions

extension Optional where Wrapped == String {

    /// Returns true if optional string is nil or empty
    var isNilOrEmpty: Bool {
        switch self {
        case .none:
            return true
        case .some(let value):
            return value.trimmed.isEmpty
        }
    }
}

// MARK: - JSONDecoder Extension

extension JSONDecoder {

    /// Creates a decoder configured for WaddleBot API responses
    static var waddleBotDecoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .useDefaultKeys

        // Handle multiple date formats
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)

            // Try ISO8601 with fractional seconds
            if let date = formatter.date(from: dateString) {
                return date
            }

            // Try ISO8601 without fractional seconds
            formatter.formatOptions = [.withInternetDateTime]
            if let date = formatter.date(from: dateString) {
                return date
            }

            // Try common date format
            let dateFormatter = DateFormatter()
            dateFormatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
            if let date = dateFormatter.date(from: dateString) {
                return date
            }

            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Cannot decode date string \(dateString)"
            )
        }

        return decoder
    }
}

// MARK: - JSONEncoder Extension

extension JSONEncoder {

    /// Creates an encoder configured for WaddleBot API requests
    static var waddleBotEncoder: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .useDefaultKeys
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }
}
