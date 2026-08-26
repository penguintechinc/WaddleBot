# Build from parent directory: docker build -f googlechat_module/Dockerfile -t waddlebot/googlechat:latest .

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

# uv replaces pip for dependency installation (pinned by digest)
COPY --from=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa /uv /usr/local/bin/uv

WORKDIR /app

# Copy shared libraries
COPY libs/flask_core /app/libs/flask_core
COPY libs/platform_receiver /app/libs/platform_receiver

# Install shared libraries
RUN uv pip install --system --no-cache /app/libs/flask_core /app/libs/platform_receiver

# Copy module files
COPY trigger/receiver/googlechat_module/requirements.txt /app/
COPY trigger/receiver/googlechat_module /app/

# Install module dependencies
RUN uv pip install --system --no-cache -r requirements.txt

# Create log directory
RUN mkdir -p /var/log/waddlebotlog

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot -m waddlebot

# Set proper permissions for app directory and log directory
RUN chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

EXPOSE 8012

USER waddlebot

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8012", "--workers", "4"]
