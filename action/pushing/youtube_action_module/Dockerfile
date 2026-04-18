# YouTube Action Module - Python 3.12 Container
FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY action/pushing/youtube_action_module/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY action/pushing/youtube_action_module/ /app/

# Generate gRPC protobuf files
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./proto \
    --grpc_python_out=./proto \
    ./proto/youtube_action.proto && \
    sed -i 's/^import youtube_action_pb2/from proto import youtube_action_pb2/' ./proto/youtube_action_pb2_grpc.py

# Create log directory
RUN mkdir -p /var/log/waddlebotlog

# Copy standard healthcheck script
COPY scripts/healthcheck.py /usr/local/bin/healthcheck.py
RUN chmod 755 /usr/local/bin/healthcheck.py

# Create non-root user
RUN useradd -m -u 1000 waddlebot && \
    chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

# Switch to non-root user
USER waddlebot

# Expose ports
EXPOSE 8073 50054

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 /usr/local/bin/healthcheck.py http://localhost:8073/health

# Run with Hypercorn
CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8073", "--workers", "4"]
