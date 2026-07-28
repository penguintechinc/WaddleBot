/// Secure token storage abstraction — OS keychain (Keychain/Credential Manager/Secret Service) or in-memory test backend
use crate::error::ApiError;
use async_trait::async_trait;
use std::sync::Mutex;

const KEYCHAIN_SERVICE: &str = "waddlebot-desktop";
const TOKEN_KEY: &str = "hub_token";

/// Token storage backend — abstracts over OS keychain vs in-memory test backend
#[async_trait]
pub trait TokenStore: Send + Sync {
    /// Retrieve the stored token
    async fn get_token(&self) -> Result<Option<String>, ApiError>;
    /// Store a token
    async fn set_token(&self, token: String) -> Result<(), ApiError>;
    /// Clear the stored token
    async fn clear_token(&self) -> Result<(), ApiError>;
}

/// Production implementation — OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service)
pub struct OsKeychain;

#[async_trait]
impl TokenStore for OsKeychain {
    async fn get_token(&self) -> Result<Option<String>, ApiError> {
        match keyring::Entry::new(KEYCHAIN_SERVICE, TOKEN_KEY) {
            Ok(entry) => match entry.get_password() {
                Ok(token) => Ok(Some(token)),
                Err(keyring::Error::NoEntry) => Ok(None),
                Err(e) => Err(ApiError::KeychainError(format!("get failed: {}", e))),
            },
            Err(e) => Err(ApiError::KeychainError(format!("init failed: {}", e))),
        }
    }

    async fn set_token(&self, token: String) -> Result<(), ApiError> {
        match keyring::Entry::new(KEYCHAIN_SERVICE, TOKEN_KEY) {
            Ok(entry) => entry
                .set_password(&token)
                .map_err(|e| ApiError::KeychainError(format!("set failed: {}", e))),
            Err(e) => Err(ApiError::KeychainError(format!("init failed: {}", e))),
        }
    }

    async fn clear_token(&self) -> Result<(), ApiError> {
        match keyring::Entry::new(KEYCHAIN_SERVICE, TOKEN_KEY) {
            Ok(entry) => entry
                .delete_credential()
                .map_err(|e| ApiError::KeychainError(format!("delete failed: {}", e))),
            Err(e) => Err(ApiError::KeychainError(format!("init failed: {}", e))),
        }
    }
}

/// Test implementation — in-memory storage (no keychain access)
pub struct InMemoryKeychain {
    tokens: Mutex<Option<String>>,
}

impl InMemoryKeychain {
    pub fn new() -> Self {
        InMemoryKeychain {
            tokens: Mutex::new(None),
        }
    }
}

#[async_trait]
impl TokenStore for InMemoryKeychain {
    async fn get_token(&self) -> Result<Option<String>, ApiError> {
        Ok(self.tokens.lock().unwrap().clone())
    }

    async fn set_token(&self, token: String) -> Result<(), ApiError> {
        *self.tokens.lock().unwrap() = Some(token);
        Ok(())
    }

    async fn clear_token(&self) -> Result<(), ApiError> {
        *self.tokens.lock().unwrap() = None;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_in_memory_store() {
        let store = InMemoryKeychain::new();
        assert_eq!(store.get_token().await.unwrap(), None);

        store
            .set_token("test_token_123".to_string())
            .await
            .unwrap();
        assert_eq!(
            store.get_token().await.unwrap(),
            Some("test_token_123".to_string())
        );

        store.clear_token().await.unwrap();
        assert_eq!(store.get_token().await.unwrap(), None);
    }
}
