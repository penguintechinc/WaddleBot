# Engagement Module Dockerfile
# Build from parent directory: docker build -f core/engagement_module/Dockerfile -t waddlebot/engagement:latest .

FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

# uv replaces pip for dependency installation (pinned by digest)
COPY --from=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared library
COPY libs/flask_core /app/libs/flask_core

# Install shared library
RUN cd /app/libs/flask_core && uv pip install --system --no-cache .

# Copy requirements
COPY core/engagement_module/requirements.txt /app/

# Install Python dependencies
RUN uv pip install --system --no-cache -r requirements.txt

# Copy module files
COPY core/engagement_module /app/

# Create log directory
RUN mkdir -p /var/log/waddlebotlog

# Create PyDAL migration log directory
RUN mkdir -p /app/databases

# Copy standard healthcheck script
COPY scripts/healthcheck.py /usr/local/bin/healthcheck.py
RUN chmod 755 /usr/local/bin/healthcheck.py

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot -m waddlebot

# Set proper permissions for app directory and log directory
RUN chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

# Switch to non-root user
USER waddlebot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8091/health || exit 1

EXPOSE 8091 50066

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8091", "--workers", "4"]
