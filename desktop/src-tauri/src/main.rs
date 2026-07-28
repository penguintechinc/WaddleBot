/// waddlebot-desktop — Tauri app shell for the waddlebot hub webui
/// M1: Auth core — token storage, login, and Rust-proxied API requests

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;

use std::sync::Arc;
use waddlebot_desktop::api::{ApiProxy, OsKeychain};

fn main() {
    // Initialize tracing for structured logging (JSON format for observability)
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::DEBUG)
        .with_writer(std::io::stdout)
        .init();

    // Initialize API client with OS keychain and default hub URL
    let client = Arc::new(ApiProxy::new(
        Arc::new(OsKeychain),
        "https://waddles.app".to_string(),
    ));

    tracing::info!("[waddlebot-desktop] Initializing Tauri app");
    tracing::info!("[waddlebot-desktop] API client ready (keychain: OS backend, hub: waddles.app)");

    let app_state = commands::AppState { client };

    tauri::Builder::default()
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            commands::store_token,
            commands::get_token,
            commands::clear_token,
            commands::api_request,
            commands::login,
            commands::logout,
            commands::start_oauth,
            commands::handle_oauth_callback,
            commands::greet
        ])
        .setup(|app| {
            // Register deep-link handler for OAuth callbacks
            #[cfg(feature = "desktop-tauri")]
            {
                use tauri_plugin_deep_link::DeepLinkExt;

                // Register the waddles:// protocol for OAuth callbacks
                let app_handle = app.handle().clone();

                app.deep_link().register("waddles", move |request| {
                    tracing::info!("[deep-link] Received: {}", request);

                    // Parse the deep-link URL: waddles://oauth/callback?token=...
                    if let Some(url) = request.split("waddles://").nth(1) {
                        if url.starts_with("oauth/callback") {
                            // Extract token from query string
                            if let Some(token_param) = url.split("token=").nth(1) {
                                let token = token_param.split('&').next().unwrap_or("");
                                tracing::info!("[deep-link] Extracted token, emitting event to frontend");

                                // Emit event to the frontend to handle the OAuth callback
                                let _ = app_handle.emit("oauth-callback", serde_json::json!({
                                    "token": token.to_string()
                                }));
                            }
                        }
                    }
                })?;
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
