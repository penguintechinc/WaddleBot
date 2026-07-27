/// waddlebot-desktop API proxy library — enables Rust-side HTTP requests with keychain token storage
pub mod api;
pub mod error;

pub use api::ApiClient;
pub use error::ApiError;
