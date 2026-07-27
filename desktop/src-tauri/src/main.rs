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
            commands::greet
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
