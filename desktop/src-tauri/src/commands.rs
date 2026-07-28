/// Tauri command handlers for desktop authentication and API proxying
/// All commands use the AppState to access the API client and keychain
use serde_json::json;
use tauri::State;
use waddlebot_desktop::api::ApiRequest;
use waddlebot_desktop::error::ApiError;

/// Application state containing the initialized API proxy client
pub struct AppState {
    pub client: std::sync::Arc<waddlebot_desktop::api::ApiProxy>,
}

/// Store token in OS keychain (Tauri command)
#[tauri::command]
pub async fn store_token(token: String, state: State<'_, AppState>) -> Result<(), String> {
    tracing::info!("[store_token] Storing token in OS keychain");
    state
        .client
        .get_keychain()
        .set_token(token)
        .await
        .map_err(|e| e.sanitized_message())
}

/// Get token from OS keychain (Tauri command)
/// Returns None if token not found; error if keychain access fails
#[tauri::command]
pub async fn get_token(state: State<'_, AppState>) -> Result<Option<String>, String> {
    state
        .client
        .get_keychain()
        .get_token()
        .await
        .map_err(|e| e.sanitized_message())
}

/// Clear token from OS keychain (Tauri command)
#[tauri::command]
pub async fn clear_token(state: State<'_, AppState>) -> Result<(), String> {
    tracing::info!("[clear_token] Clearing token from OS keychain");
    state
        .client
        .get_keychain()
        .clear_token()
        .await
        .map_err(|e| e.sanitized_message())
}

/// Make an authenticated API request to the hub (Tauri command)
/// Token is injected server-side in Rust; never exposed to JavaScript
/// Returns { status: u16, body: String } on success
#[tauri::command]
pub async fn api_request(
    method: String,
    path: String,
    body: Option<String>,
    state: State<'_, AppState>,
) -> Result<serde_json::Value, String> {
    let req = ApiRequest { method, path, body };
    match state.client.request(req).await {
        Ok(response) => Ok(json!({
            "status": response.status,
            "body": response.body
        })),
        Err(e) => {
            tracing::warn!("[api_request] Error: {}", e.sanitized_message());
            Err(e.sanitized_message())
        }
    }
}

/// Login with email and password (Tauri command)
/// On success, token is stored in OS keychain and a sanitized response is returned.
/// The token is NEVER included in the response or logged.
/// Returns { email, role, success } on success
#[tauri::command]
pub async fn login(
    email: String,
    password: String,
    state: State<'_, AppState>,
) -> Result<serde_json::Value, String> {
    tracing::info!("[login] Attempting login");
    match state.client.login(email.clone(), password).await {
        Ok(response) => {
            // Return sanitized response: user info, role, etc., but NEVER the token
            let sanitized = json!({
                "email": email,
                "role": response.get("role").and_then(|r| r.as_str()).unwrap_or("user"),
                "success": true
            });
            tracing::info!("[login] Login successful");
            Ok(sanitized)
        }
        Err(e) => {
            tracing::warn!("[login] Login failed: {}", e.sanitized_message());
            Err(e.sanitized_message())
        }
    }
}

/// Logout (Tauri command)
/// Clears the token from OS keychain
#[tauri::command]
pub async fn logout(state: State<'_, AppState>) -> Result<(), String> {
    tracing::info!("[logout] Logging out");
    state
        .client
        .logout()
        .await
        .map_err(|e| e.sanitized_message())
}

/// Start OAuth login flow with system browser (Tauri command)
/// Opens the hub's OAuth authorize URL in the system default browser
/// The hub must have registered `waddles://oauth/callback` as a redirect URI
#[tauri::command]
pub async fn start_oauth(
    platform: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    tracing::info!("[start_oauth] Starting OAuth flow for platform: {}", platform);

    let hub_base = state.client.hub_base();

    // Get the authorize URL from the hub
    let url = format!("{}/api/v1/auth/oauth/{}", hub_base, platform);
    let client = reqwest::Client::new();

    let response = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("Failed to get OAuth URL: {}", e))?;

    let status = response.status().as_u16();
    let text = response
        .text()
        .await
        .map_err(|e| format!("Failed to read response: {}", e))?;

    if status != 200 {
        return Err(format!("Failed to get OAuth URL: status {}", status));
    }

    let data: serde_json::Value = serde_json::from_str(&text)
        .map_err(|_| "Failed to parse OAuth response".to_string())?;

    let authorize_url = data
        .get("authorizeUrl")
        .and_then(|v| v.as_str())
        .ok_or("No authorizeUrl in response")?;

    // Open the URL in the system browser using tauri-plugin-opener or tauri::api::shell::open
    #[cfg(feature = "desktop-tauri")]
    {
        // Use tauri-plugin-opener if available (better cross-platform support)
        use tauri_plugin_opener::open;
        open(authorize_url).map_err(|e| format!("Failed to open browser: {}", e))?;
    }

    #[cfg(not(feature = "desktop-tauri"))]
    {
        // Fallback to system shell command
        std::process::Command::new("xdg-open")
            .arg(authorize_url)
            .spawn()
            .map_err(|e| format!("Failed to open browser: {}", e))?;
    }

    tracing::info!("[start_oauth] Opened browser for OAuth flow");
    Ok("Browser opened for OAuth login".to_string())
}

/// Handle OAuth callback token (Tauri command)
/// Called by the deep-link handler when `waddles://oauth/callback?token=...` is received
#[tauri::command]
pub async fn handle_oauth_callback(
    token: String,
    state: State<'_, AppState>,
) -> Result<serde_json::Value, String> {
    tracing::info!("[handle_oauth_callback] Processing OAuth token");

    // Store the token in keychain
    state
        .client
        .get_keychain()
        .set_token(token.clone())
        .await
        .map_err(|e| e.sanitized_message())?;

    // Return user info (sanitized, no token)
    Ok(serde_json::json!({
        "success": true,
        "message": "OAuth login successful"
    }))
}

/// Simple greeting command (for testing)
#[tauri::command]
pub fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}

#[cfg(test)]
mod tests {
    use super::*;

    // NOTE: Tauri command tests require the Tauri runtime to be initialized.
    // These tests verify the command logic without the runtime.
    // For full integration tests with mocked HTTP, use a test server or wiremock.

    #[test]
    fn test_greet() {
        assert_eq!(greet("World"), "Hello, World!");
    }
}
