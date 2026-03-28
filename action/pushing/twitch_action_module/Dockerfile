# Twitch Action Module Dockerfile
# Build from parent directory: docker build -f action/pushing/twitch_action_module/Dockerfile -t waddlebot/twitch-action:latest .

FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY action/pushing/twitch_action_module/requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy module files
COPY action/pushing/twitch_action_module /app/

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

# Expose ports
EXPOSE 8072

# Switch to non-root user
USER waddlebot

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8072", "--workers", "4"]
