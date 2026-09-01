# Module RTC Dockerfile
# Multi-stage Go build

FROM golang:1.25-bookworm@sha256:3b4a11519ad929d1e1d261a12cff056f0c85b735253d7d861346b9c6f8b36437 AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy go mod files first for layer caching (build context is project root)
COPY core/module_rtc/go.mod core/module_rtc/go.sum* ./
RUN go mod download

# Copy module source code
COPY core/module_rtc/ .

# Build binary
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /build/module_rtc ./cmd/server

# Production stage
FROM debian:bookworm-slim@sha256:f06537653ac770703bc45b4b113475bd402f451e85223f0f2837acbf89ab020a

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot waddlebot

# Copy binary from builder
COPY --from=builder /build/module_rtc /app/module_rtc

# Set ownership
RUN chown -R waddlebot:waddlebot /app

USER waddlebot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8093/health || exit 1

EXPOSE 8093 50067

CMD ["/app/module_rtc"]
