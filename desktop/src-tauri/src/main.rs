/// waddlebot-desktop — Tauri app shell for the waddlebot hub webui
/// MVP shell: initializes the API client with OS keychain and default hub URL
/// Tauri command handlers are deferred to M1 (auth core)

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Arc;
use waddlebot_desktop::api::{ApiProxy, OsKeychain};

fn main() {
    // TODO M1: Initialize API client with OS keychain and default hub URL
    // TODO M1: Register Tauri command handlers (store_token, get_token, clear_token, api_request, login, logout)
    // TODO M1: Initialize Tauri builder and event system

    // For now, verify the API client initializes without error
    let _client = Arc::new(ApiProxy::new(
        Arc::new(OsKeychain),
        "https://waddles.app".to_string(),
    ));

    // MVP: just log startup
    println!("[waddlebot-desktop] Initializing...");
    println!("[waddlebot-desktop] API client ready (keychain: OS backend, hub: waddles.app)");
}
