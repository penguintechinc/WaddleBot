# GCP Functions Action Module Dockerfile
# Build from parent directory: docker build -f action/pushing/gcp_functions_action_module/Dockerfile -t waddlebot/gcp-functions-action:latest .

FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

# Set working directory
WORKDIR /app

# Install system dependencies (build-essential needed for google-cloud-functions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY action/pushing/gcp_functions_action_module/requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy module files
COPY action/pushing/gcp_functions_action_module /app/

# Create log directory
RUN mkdir -p /var/log/waddlebotlog

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot -m waddlebot

# Set proper permissions for app directory and log directory
RUN chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

# Create databases directory for PyDAL
RUN mkdir -p /app/databases

# Generate gRPC code from proto file
RUN python -m grpc_tools.protoc \
    -I./grpc_proto \
    --python_out=./grpc_proto \
    --grpc_python_out=./grpc_proto \
    ./grpc_proto/gcp_functions_action.proto && \
    # Fix import paths in generated grpc file
    sed -i 's/^import gcp_functions_action_pb2/from grpc_proto import gcp_functions_action_pb2/' ./grpc_proto/gcp_functions_action_pb2_grpc.py

# Copy standard healthcheck script
COPY scripts/healthcheck.py /usr/local/bin/healthcheck.py
RUN chmod 755 /usr/local/bin/healthcheck.py

# Switch to non-root user
USER waddlebot

# Expose ports (REST and gRPC)
EXPOSE 8081 50061

# Health check (using /healthz for Kubernetes compatibility)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 /usr/local/bin/healthcheck.py http://localhost:8081/healthz

# Run with Hypercorn (async ASGI server)
CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8081", "--workers", "4"]
