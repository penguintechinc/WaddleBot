/// API proxy — Rust-side HTTP requests with OS keychain token storage
pub mod keychain;
pub mod proxy;

pub use keychain::{InMemoryKeychain, OsKeychain, TokenStore};
pub use proxy::{ApiProxy, ApiRequest, ApiResponse};

/// Convenience alias for ApiProxy as the main API client
pub type ApiClient = ApiProxy;
