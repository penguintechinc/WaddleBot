# Build from parent directory: docker build -f identity_core_module/Dockerfile -t waddlebot/identity-core:latest .

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

# uv replaces pip for dependency installation (pinned by digest)
COPY --from=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa /uv /usr/local/bin/uv

WORKDIR /app

# Copy shared library
COPY libs/flask_core /app/libs/flask_core

# Install shared library
RUN uv pip install --system --no-cache /app/libs/flask_core

# Copy module files
COPY core/identity_core_module/requirements.txt /app/
COPY core/identity_core_module /app/
COPY libs/grpc_protos /tmp/grpc_protos

# Install module dependencies
RUN uv pip install --system --no-cache -r requirements.txt

# Generate and validate the shared Identity gRPC contract in a real Python
# package. Relative imports prevent collisions with the third-party `proto`
# package.
RUN python -m grpc_tools.protoc \
    -I/tmp/grpc_protos \
    --python_out=/app/proto \
    --grpc_python_out=/app/proto \
    /tmp/grpc_protos/common.proto \
    /tmp/grpc_protos/identity.proto && \
    sed -i 's/^import common_pb2/from . import common_pb2/' /app/proto/identity_pb2.py && \
    sed -i 's/^import identity_pb2/from . import identity_pb2/' /app/proto/identity_pb2_grpc.py && \
    python -c "from proto import identity_pb2, identity_pb2_grpc; assert identity_pb2_grpc.IdentityServiceStub"

# Create log directory
RUN mkdir -p /var/log/waddlebotlog

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set proper permissions for app directory and log directory
RUN chown -R appuser:appuser /app /var/log/waddlebotlog

USER appuser

EXPOSE 8050 50030

# The gRPC listener is process-local, so the HTTP and gRPC servers must share
# one worker unless gRPC is split into a separate deployment.
CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8050", "--workers", "1"]
