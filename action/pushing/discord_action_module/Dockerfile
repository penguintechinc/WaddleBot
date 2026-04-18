# Discord Action Module Dockerfile
# Build: docker compose build discord-action

FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY action/pushing/discord_action_module/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY action/pushing/discord_action_module/ /app/

# Generate protobuf Python files
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./proto \
    --grpc_python_out=./proto \
    ./proto/discord_action.proto && \
    sed -i 's/^import discord_action_pb2/from proto import discord_action_pb2/' ./proto/discord_action_pb2_grpc.py

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
EXPOSE 50051 8070

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 /usr/local/bin/healthcheck.py http://localhost:50051/healthz

# Run application
CMD ["python", "app.py"]
