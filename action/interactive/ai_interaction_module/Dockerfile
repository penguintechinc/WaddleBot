# Build from parent directory: docker build -f action/interactive/ai_interaction_module/Dockerfile -t waddlebot/ai-interaction:latest .

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

# uv replaces pip for dependency installation (pinned by digest)
COPY --from=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa /uv /usr/local/bin/uv

WORKDIR /app

# Copy shared library
COPY libs/flask_core /app/libs/flask_core

# Install shared library
RUN uv pip install --system --no-cache /app/libs/flask_core

# Copy module files
COPY action/interactive/ai_interaction_module/requirements.txt /app/
COPY action/interactive/ai_interaction_module /app/

# Install module dependencies
RUN uv pip install --system --no-cache -r requirements.txt

# Create log directory
RUN mkdir -p /var/log/waddlebotlog

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot -m waddlebot

# Set proper permissions for app directory and log directory
RUN chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

USER waddlebot

CMD ["sh", "-c", "exec hypercorn app:app --bind 0.0.0.0:${MODULE_PORT:-8005} --workers ${HYPERCORN_WORKERS:-1}"]
