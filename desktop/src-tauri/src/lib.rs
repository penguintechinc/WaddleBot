/// waddlebot-desktop API proxy library — enables Rust-side HTTP requests with keychain token storage
pub mod api;
pub mod error;

pub use api::{ApiProxy, ApiRequest, ApiResponse, TokenStore, InMemoryKeychain, OsKeychain};
pub use error::ApiError;
