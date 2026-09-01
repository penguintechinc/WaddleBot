# Lambda Action Module Dockerfile
# Build from parent directory: docker build -f action/pushing/lambda_action_module/Dockerfile -t waddlebot/lambda-action:latest .

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY action/pushing/lambda_action_module/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY action/pushing/lambda_action_module /app/

# Compile Protobuf messages
RUN python -m grpc_tools.protoc -I./grpc_proto --python_out=./grpc_proto --grpc_python_out=./grpc_proto ./grpc_proto/lambda_action.proto && \
    sed -i 's/import lambda_action_pb2/from grpc_proto import lambda_action_pb2/g' ./grpc_proto/lambda_action_pb2_grpc.py

# Create log directory
RUN mkdir -p /var/log/waddlebotlog

# Copy standard healthcheck script
COPY scripts/healthcheck.py /usr/local/bin/healthcheck.py
RUN chmod 755 /usr/local/bin/healthcheck.py

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot -m waddlebot

# Set proper permissions for app directory and log directory
RUN chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

# Switch to non-root user
USER waddlebot

# Expose port
EXPOSE 8080

# Run application
CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8080", "--workers", "4"]
