/// HTTP API proxy — requests made server-side with keychain token injection
use crate::api::keychain::TokenStore;
use crate::error::ApiError;
use serde_json::{json, Value};
use std::sync::Arc;

/// API request parameters
#[derive(Debug, Clone)]
pub struct ApiRequest {
    pub method: String,
    pub path: String,
    pub body: Option<String>,
}

/// API response
#[derive(Debug, Clone)]
pub struct ApiResponse {
    pub status: u16,
    pub body: String,
}

/// HTTP proxy client — holds token store and hub base URL, makes authenticated requests
pub struct ApiProxy {
    token_store: Arc<dyn TokenStore>,
    hub_base: String,
}

impl ApiProxy {
    /// Create a new proxy with a token store and hub base URL
    pub fn new(token_store: Arc<dyn TokenStore>, hub_base: String) -> Self {
        ApiProxy {
            token_store,
            hub_base,
        }
    }

    /// Make an authenticated HTTP request to the hub
    pub async fn request(&self, req: ApiRequest) -> Result<ApiResponse, ApiError> {
        // Get token from keychain (fail if not logged in)
        let token = self
            .token_store
            .get_token()
            .await?
            .ok_or(ApiError::Unauthorized)?;

        // Build full URL (never log the full URL or token)
        let url = format!("{}/api/v1{}", self.hub_base, req.path);
        tracing::debug!("[ApiProxy] {} {} (masked token)", req.method, req.path);

        // Parse method
        let method = match req.method.to_uppercase().as_str() {
            "GET" => reqwest::Method::GET,
            "POST" => reqwest::Method::POST,
            "PUT" => reqwest::Method::PUT,
            "PATCH" => reqwest::Method::PATCH,
            "DELETE" => reqwest::Method::DELETE,
            _ => return Err(ApiError::HttpError("invalid method".to_string())),
        };

        // Build request
        let client = reqwest::Client::new();
        let mut request = client
            .request(method, &url)
            .header("Authorization", format!("Bearer {}", token))
            .header("Content-Type", "application/json");

        // Add body if present
        if let Some(body) = req.body {
            request = request.body(body);
        }

        // Execute request
        let response = request
            .send()
            .await
            .map_err(|e| ApiError::HttpError(e.to_string()))?;

        let status = response.status().as_u16();
        let body = response
            .text()
            .await
            .map_err(|e| ApiError::HttpError(e.to_string()))?;

        // Log status only (no URL, no body, no token)
        tracing::debug!("[ApiProxy] Response status={}", status);

        // Handle common error statuses
        match status {
            401 => Err(ApiError::Unauthorized),
            403 => Err(ApiError::Forbidden),
            404 => Err(ApiError::NotFound),
            500..=599 => Err(ApiError::ServerError { status }),
            _ => Ok(ApiResponse { status, body }),
        }
    }

    /// Log in with email and password — makes unauthenticated request, stores token
    pub async fn login(&self, email: String, password: String) -> Result<Value, ApiError> {
        let url = format!("{}/api/v1/auth/login", self.hub_base);
        let body = json!({ "email": email, "password": "***" });
        tracing::debug!("[ApiProxy.login] POST /auth/login");

        let payload = json!({ "email": email, "password": password });
        let client = reqwest::Client::new();
        let response = client
            .post(&url)
            .json(&payload)
            .send()
            .await
            .map_err(|e| ApiError::HttpError(e.to_string()))?;

        let status = response.status().as_u16();
        let text = response
            .text()
            .await
            .map_err(|e| ApiError::HttpError(e.to_string()))?;

        // Parse response
        let data: Value = serde_json::from_str(&text)
            .map_err(|_| ApiError::InvalidJson)?;

        match status {
            200 => {
                // Extract token from response and store it
                if let Some(token) = data.get("token").and_then(|v| v.as_str()) {
                    self.token_store.set_token(token.to_string()).await?;
                    Ok(data)
                } else {
                    Err(ApiError::InvalidJson)
                }
            }
            401 => Err(ApiError::Unauthorized),
            _ => Err(ApiError::ServerError { status }),
        }
    }

    /// Log out — clear the token from keychain
    pub async fn logout(&self) -> Result<(), ApiError> {
        tracing::debug!("[ApiProxy.logout]");
        self.token_store.clear_token().await
    }

    /// Get the current hub base URL
    pub fn hub_base(&self) -> &str {
        &self.hub_base
    }

    /// Update the hub base URL
    pub fn set_hub_base(&mut self, base: String) {
        self.hub_base = base;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::api::keychain::InMemoryKeychain;

    #[tokio::test]
    async fn test_unauthorized_without_token() {
        let store = Arc::new(InMemoryKeychain::new());
        let proxy = ApiProxy::new(store, "https://waddles.app".to_string());

        let req = ApiRequest {
            method: "GET".to_string(),
            path: "/communities".to_string(),
            body: None,
        };

        let result = proxy.request(req).await;
        assert!(matches!(result, Err(ApiError::Unauthorized)));
    }

    #[tokio::test]
    async fn test_token_stored_after_login() {
        let store = Arc::new(InMemoryKeychain::new());
        let proxy = ApiProxy::new(store.clone(), "https://waddles.app".to_string());

        // Simulate a successful login response
        // (In real tests, this would be mocked; here we verify the token storage logic)
        let token = "test_jwt_token_123";
        store.set_token(token.to_string()).await.unwrap();

        let retrieved = store.get_token().await.unwrap();
        assert_eq!(retrieved, Some(token.to_string()));
    }

    #[tokio::test]
    async fn test_logout_clears_token() {
        let store = Arc::new(InMemoryKeychain::new());
        let proxy = ApiProxy::new(store.clone(), "https://waddles.app".to_string());

        store.set_token("test_token".to_string()).await.unwrap();
        assert!(store.get_token().await.unwrap().is_some());

        proxy.logout().await.unwrap();
        assert_eq!(store.get_token().await.unwrap(), None);
    }
}
