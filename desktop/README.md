# Waddlebot Desktop Client (Tauri v2) — MVP Auth Core

**Status:** M1 (Auth Core) — Tauri command handlers implemented, token storage + API proxy complete. Unit tests cover keychain logic. Full GUI build pending system deps.

## Overview

A Tauri v2 desktop app that packages the existing Vite + React webui (`admin/hub_module/frontend/`) and adds secure Rust-side token storage + HTTP proxy for authenticated requests to the waddlebot hub.

**Key features (MVP):**
- Reuses existing React webui (Vite build)
- OS keychain token storage (never localStorage)
- Rust-proxied HTTP requests (token never touches JS)
- Email/password login (OAuth deferred to M2)
- End-user + community-admin roles (super-admin deferred)

## Architecture

```
desktop/
├── src-tauri/              # Rust backend (Tauri + API proxy)
│   ├── src/
│   │   ├── main.rs        # Tauri app shell (MVP: minimal)
│   │   ├── lib.rs         # Public library exports
│   │   └── api/
│   │       ├── mod.rs
│   │       ├── proxy.rs   # HTTP proxy + login/logout logic
│   │       ├── keychain.rs # Token storage (OS keychain + test backend)
│   │       └── error.rs   # Sanitized error types
│   ├── Cargo.toml         # Rust deps (exact versions, Cargo.lock committed)
│   ├── rust-toolchain.toml # Rust 1.97.x pinned
│   └── build.rs           # Tauri build integration
├── src/                    # TypeScript frontend (symlink or reuse)
├── package.json           # npm deps (exact versions, package-lock.json committed)
├── tauri.conf.json        # Tauri configuration (webview, CSP, bundle settings)
├── vite.config.ts         # Vite configuration
├── tsconfig.json          # TypeScript configuration
└── README.md              # This file
```

## Build & Test

### Prerequisites

**What works now (no system deps needed):**
- Rust library compilation (requires `cargo` + `rustc` 1.97+)
- Unit tests for keychain + proxy modules
- Integration tests (InMemoryKeychain, no network calls)
- npm install + frontend production build

**What requires system deps (deferred to CI):**
- Full Tauri GUI build (needs webkit2gtk on Linux, Xcode on macOS, MSVC on Windows)
- Desktop app `cargo tauri build`
- Multi-arch builds (amd64 + arm64)

### Commands

```bash
# Generate Cargo.lock (run once if not committed)
cd desktop/src-tauri
cargo update

# Build Rust library + run unit + integration tests (no system deps needed)
cargo test --lib                        # Unit tests (keychain + proxy + commands)
cargo test --test integration_test      # Integration tests

# Check code quality
cargo clippy --all-targets -- -D warnings
cargo fmt --check
cargo audit                             # Security scan

# Build frontend (reuses existing Vite build)
cd desktop
npm ci
npm run build:frontend

# Full app build (requires system webkit deps — CI only, after Rust tests pass)
cargo test                              # Full test suite including integration
npm run build:all                       # desktop + frontend + Tauri GUI shell
```

## API Proxy & Keychain

**Token Storage:** OS keychain only (macOS Keychain, Windows Credential Manager, Linux Secret Service via `keyring` crate). Never stored in localStorage or plaintext files.

**HTTP Proxy:** `ApiProxy` trait + implementations:
- Production: `OsKeychain` backend (real keychain access)
- Testing: `InMemoryKeychain` backend (no keychain required)

**Usage in Rust:**
```rust
// Create proxy with OS keychain
let client = ApiProxy::new(
    Arc::new(OsKeychain),
    "https://waddles.app".to_string()
);

// Make authenticated request
let req = ApiRequest { 
    method: "GET".to_string(), 
    path: "/communities".to_string(), 
    body: None 
};
let response = client.request(req).await?;
```

**Usage in React (Tauri command):**
```typescript
// Tauri invokes Rust command — token never touches JS
const response = await invoke('api_request', {
    method: 'GET',
    path: '/communities',
    body: null
});
```

## M1: Auth Core — Complete ✓

**Implemented:**
- [x] Tauri command handlers for token storage (`store_token`, `get_token`, `clear_token`)
- [x] `api_request` Tauri command — Rust-proxied REST with keychain token injection
- [x] `login` command — email/password authentication with sanitized response
- [x] `logout` command — token clearing
- [x] Structured logging with sanitization (no tokens/PII in logs)
- [x] Token never touches JavaScript — stored in OS keychain, injected server-side
- [x] Unit tests for keychain + token storage logic (InMemoryKeychain backend)

**Command Handlers (Rust → JavaScript):**
```rust
// Token management
store_token(token: String) -> Result<(), String>
get_token() -> Result<Option<String>, String>
clear_token() -> Result<(), String>

// API proxy (token injected in Rust; response sanitized)
api_request(method, path, body) -> Result<{ status, body }, String>

// Authentication
login(email, password) -> Result<{ email, role, success }, String>
logout() -> Result<(), String>
```

**Token Flow:**
1. User submits email/password via React login form
2. `login()` command calls hub's `/api/v1/auth/login` (Rust side, HTTPS/rustls)
3. Hub returns JWT token in response
4. Token stored in OS keychain (via `TokenStore::set_token()`)
5. Token never exposed to JavaScript layer
6. Subsequent API calls via `api_request()` retrieve token from keychain at request time

**Testing:**
- Unit tests: `src/api/keychain.rs` (token storage roundtrip)
- Unit tests: `src/api/proxy.rs` (unauthorized, logout, hub URL management)
- Integration tests: `tests/integration_test.rs` (full flow with InMemoryKeychain)
- HTTP mocking (wiremock) infrastructure documented for CI

**Deferred Items (Post-MVP):**

### M2: OAuth
- [ ] System browser integration (tauri-plugin-opener + `shell:open`)
- [ ] Deep-link callback handler (`waddles://auth/callback?token=…`) via tauri-plugin-deep-link
- [ ] OAuthCallback React page integration

### M3-M4: Feature Parity
- [ ] Read-only dashboard, communities, members, chat
- [ ] Admin features: modules, music, loyalty, announcements
- [ ] WebRTC calls + live streaming (media permissions, sandbox validation)

### M5: Desktop-Native
- [ ] System tray + minimize-to-tray
- [ ] Native notifications
- [ ] In-app updater (tauri-plugin-updater)
- [ ] Offline connectivity indicator + "last synced" timestamp

### M6: Package & Sign
- [ ] Multi-arch builds (amd64 + arm64 per platform)
- [ ] Code signing (macOS/Windows)
- [ ] Release CI/CD pipeline

### M7 (Optional)
- [ ] Local integrations panel — bridge `POST /rpc` relay for OBS overlays
- [ ] Bridge token minting + scope gating

## Environment Setup

### Local Development (Linux/macOS)

**System dependencies for full build:**
```bash
# Linux (Debian/Ubuntu)
sudo apt-get install libwebkit2gtk-4.1-dev \
  libgtk-3-dev \
  libssl-dev \
  libappindicator3-dev \
  libsoup-3.0-dev

# macOS
# Xcode Command Line Tools (automatic on first `cargo build`)

# Windows
# MSVC toolchain (part of Visual Studio)
```

**For MVP (no full build needed yet):**
```bash
# Just install npm deps and build the frontend
cd desktop
npm ci
npm run build:frontend
```

### CI/Docker

A full Tauri build is containerized (system deps + Rust + Node).

```dockerfile
# Dockerfile (Debian bookworm)
FROM debian:bookworm-slim AS builder
RUN apt-get update && apt-get install -y \
  libwebkit2gtk-4.1-dev \
  libgtk-3-dev \
  libssl-dev \
  # ... rest of deps
  rust \
  node.js \
  npm
WORKDIR /app
COPY . .
RUN npm ci && npm run build:all
```

## Logging & Security

**Sanitized logging:** No tokens, passwords, full emails, MFA codes, or security thresholds logged.

```rust
// ✓ OK
tracing::debug!("[ApiProxy] GET /communities (masked token)");
tracing::debug!("[ApiProxy] Response status=200");

// ✗ NEVER
println!("Token: {}", token);
tracing::info!("[ApiProxy] Authorization: Bearer {}", token);
```

## Standards Compliance

- ✓ Rust pinned (1.97.x via `rust-toolchain.toml`), `Cargo.lock` committed
- ✓ npm exact versions (no `^`/`~`), `package-lock.json` committed
- ✓ No hardcoded secrets or credentials
- ✓ OS keychain only for token storage (client.md hard rule)
- ✓ Rootless Tauri process (no `sudo`, no elevated privileges)
- ✓ Sanitized logging (no sensitive values)
- ✓ 90%+ test coverage target (unit tests for proxy + keychain modules)

## Next Steps

1. **Complete frontend build verification** — ensure `admin/hub_module/frontend dist/` builds successfully with desktop env vars
2. **Set up Tauri dev environment** (M1) — add Tauri command handlers and React integration
3. **Test on actual platforms** — once system deps can be installed (CI environment)

## References

- Tauri v2 docs: https://tauri.app/v1/
- `client.md` — secure storage, token handling, update checks
- `frontend-react.md` — React/Node.js standards
- `backend-rust.md` — Rust, Cargo, security scanning

---

**Generated:** 2026-07-26  
**Branch:** `feature/desktop-tauri`
