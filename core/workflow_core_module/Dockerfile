# Build from parent directory: docker build -f core/workflow_core_module/Dockerfile -t waddlebot/workflow-core:latest .

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

# uv replaces pip for dependency installation (pinned by digest)
COPY --from=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa /uv /usr/local/bin/uv

WORKDIR /app

# Copy shared library
COPY libs/flask_core /app/libs/flask_core

# Install shared library
RUN uv pip install --system --no-cache /app/libs/flask_core

# Copy module files
COPY core/workflow_core_module/requirements.txt /app/
COPY core/workflow_core_module /app/

# Install module dependencies
RUN uv pip install --system --no-cache -r requirements.txt

# Compile Protobuf messages
RUN python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/workflow.proto

# Create non-root user
RUN useradd -m -u 1000 waddlebot && \
    mkdir -p /var/log/waddlebotlog && \
    chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

# Switch to non-root user
USER waddlebot

# Expose port
EXPOSE 8090

# Copy standard healthcheck script
COPY scripts/healthcheck.py /usr/local/bin/healthcheck.py

# Health check (using /health for consistency with other modules)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 /usr/local/bin/healthcheck.py http://localhost:${MODULE_PORT:-8090}/health

# Run with Hypercorn (shell form so MODULE_PORT env var is substituted)
CMD hypercorn app:app --bind "0.0.0.0:${MODULE_PORT:-8090}" --workers 4
