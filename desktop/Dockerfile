# Multi-stage build for waddlebot-desktop (Tauri v2)
# System deps for full Tauri build (linux/amd64 + linux/arm64)

FROM debian:bookworm-slim@sha256:5d3a6ef55f3c75c81cea39dcc1cb75a8a36b91de5e2a0cf1f1c7cc31b6cbaef9 AS builder

# Install system dependencies for Tauri + Rust + Node
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libwebkit2gtk-4.1-dev \
    libgtk-3-dev \
    libssl-dev \
    libappindicator3-dev \
    libsoup-3.0-dev \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (pinned toolchain via rust-toolchain.toml)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain none
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_26.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source
COPY . .

# Build frontend
WORKDIR /app/admin/hub_module/frontend
RUN npm ci && npm run build

# Build Tauri app
WORKDIR /app/desktop
RUN npm ci
RUN cargo build --release --locked

# Final image (runtime only)
FROM debian:bookworm-slim@sha256:5d3a6ef55f3c75c81cea39dcc1cb75a8a36b91de5e2a0cf1f1c7cc31b6cbaef9

RUN apt-get update && apt-get install -y --no-install-recommends \
    libwebkit2gtk-4.1-0 \
    libgtk-3-0 \
    libssl3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app/target/release/waddlebot-desktop /app/waddlebot-desktop
COPY --from=builder --chown=appuser:appuser /app/admin/hub_module/frontend/dist /app/frontend/dist

USER appuser

# Health check: verify binary exists and is executable
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD test -x /app/waddlebot-desktop || exit 1

ENTRYPOINT ["/app/waddlebot-desktop"]
