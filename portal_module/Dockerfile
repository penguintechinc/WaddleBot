# WaddleBot Unified Community Portal - py4web Application
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for logs and data
RUN mkdir -p /var/log/waddlebotlog /app/databases /app/sessions

# Set environment variables
ENV PYTHONPATH=/app
ENV PY4WEB_FOLDER=/app
ENV PY4WEB_APPS_FOLDER=/app

# Environment variables with defaults
ENV DATABASE_URL="sqlite://portal.db"
ENV PORTAL_URL="http://localhost:8000"
ENV APP_NAME="WaddleBot Community Portal"

# SMTP Configuration (optional)
ENV SMTP_HOST=""
ENV SMTP_PORT="587"
ENV SMTP_USERNAME=""
ENV SMTP_PASSWORD=""
ENV SMTP_TLS="true"
ENV FROM_EMAIL="noreply@waddlebot.com"

# Identity Service Integration
ENV IDENTITY_API_URL="http://identity-core:8050"
ENV PORTAL_API_KEY=""
ENV API_TIMEOUT="30"

# Browser Source Integration
ENV BROWSER_SOURCE_BASE_URL="http://browser-source:8027"

# S3 Storage Configuration
ENV S3_STORAGE_ENABLED="false"
ENV S3_BUCKET_NAME="waddlebot-assets"
ENV S3_REGION="us-east-1"
ENV S3_ENDPOINT_URL=""
ENV S3_ACCESS_KEY_ID=""
ENV S3_SECRET_ACCESS_KEY=""
ENV S3_PUBLIC_BASE_URL=""
ENV S3_CDN_BASE_URL=""

# Image Settings
ENV S3_MAX_FILE_SIZE="10485760"
ENV S3_ALLOWED_EXTENSIONS="jpg,jpeg,png,gif,webp,svg"
ENV S3_IMAGE_QUALITY="85"
ENV S3_GENERATE_THUMBNAILS="true"
ENV S3_FALLBACK_STORAGE="/app/static/uploads"

# Logging Configuration
ENV LOG_LEVEL="INFO"
ENV LOG_DIR="/var/log/waddlebotlog"
ENV ENABLE_SYSLOG="false"
ENV SYSLOG_HOST="localhost"
ENV SYSLOG_PORT="514"
ENV SYSLOG_FACILITY="LOCAL0"

# Performance Settings
ENV MAX_WORKERS="10"
ENV REQUEST_TIMEOUT="30"
ENV SESSION_TTL="28800"

# Module Info
ENV MODULE_NAME="portal"
ENV MODULE_VERSION="1.0.0"
ENV MODULE_PORT="8000"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/cleanup || exit 1

# Expose port
EXPOSE 8000

# Create non-root user
RUN useradd -r -u 1000 -m -c "WaddleBot Portal User" -d /app -s /bin/bash waddlebot && \
    chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

# Switch to non-root user
USER waddlebot

# Start the application
CMD ["python", "-m", "py4web", "run", "--host", "0.0.0.0", "--port", "8000", "--folder", "/app", "portal_module"]