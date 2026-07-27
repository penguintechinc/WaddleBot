/// API error types — sanitized for logging (no tokens, PII, or sensitive values)
use serde::Serialize;
use thiserror::Error;

#[derive(Debug, Error, Serialize)]
#[serde(tag = "error_type", content = "message")]
pub enum ApiError {
    #[error("Keychain error: {0}")]
    KeychainError(String),

    #[error("HTTP request failed: {0}")]
    HttpError(String),

    #[error("Failed to refresh token: {status}")]
    RefreshFailed { status: u16 },

    #[error("Unauthorized (401)")]
    Unauthorized,

    #[error("Forbidden (403)")]
    Forbidden,

    #[error("Not found (404)")]
    NotFound,

    #[error("Server error ({status})")]
    ServerError { status: u16 },

    #[error("Invalid JSON response")]
    InvalidJson,

    #[error("Configuration error: {0}")]
    ConfigError(String),

    #[error("Unknown error")]
    Unknown,
}

impl ApiError {
    /// Sanitized logging representation — never logs tokens, full URLs, or sensitive values
    pub fn sanitized_message(&self) -> String {
        match self {
            ApiError::KeychainError(msg) => format!("[keychain] {}", msg),
            ApiError::HttpError(msg) => format!("[http] {}", msg),
            ApiError::RefreshFailed { status } => format!("[refresh] status={}", status),
            ApiError::Unauthorized => "[auth] 401 Unauthorized".to_string(),
            ApiError::Forbidden => "[auth] 403 Forbidden".to_string(),
            ApiError::NotFound => "[http] 404 Not Found".to_string(),
            ApiError::ServerError { status } => format!("[server] {}", status),
            ApiError::InvalidJson => "[parse] invalid JSON".to_string(),
            ApiError::ConfigError(msg) => format!("[config] {}", msg),
            ApiError::Unknown => "[unknown]".to_string(),
        }
    }
}
