# Build from parent directory:
# docker build -f presence_module/Dockerfile -t waddlebot/presence-module:latest .

FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

# uv replaces pip for dependency installation (pinned by digest)
COPY --from=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa /uv /usr/local/bin/uv

WORKDIR /app

# Copy shared libraries
COPY libs/flask_core /app/libs/flask_core
COPY libs/presence /app/libs/presence

# Install shared flask_core library
RUN uv pip install --system --no-cache /app/libs/flask_core

# Copy module requirements and install dependencies
COPY action/interactive/presence_module/requirements.txt /app/
RUN uv pip install --system --no-cache -r requirements.txt

# Copy module source
COPY action/interactive/presence_module /app/

# Create log directory and non-root user, then hand over ownership.
# Combined into one layer: all three steps are simple filesystem updates.
RUN mkdir -p /var/log/waddlebotlog && \
    groupadd -r waddlebot && useradd -r -g waddlebot -m waddlebot && \
    chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

EXPOSE 8042

USER waddlebot

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8042", "--workers", "4"]
