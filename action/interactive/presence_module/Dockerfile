# Build from parent directory:
# docker build -f presence_module/Dockerfile -t waddlebot/presence-module:latest .

FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

# Copy shared libraries
COPY libs/flask_core /app/libs/flask_core
COPY libs/presence /app/libs/presence

# Install shared flask_core library
RUN cd /app/libs/flask_core && pip install --no-cache-dir .

# Copy module requirements and install dependencies
COPY action/interactive/presence_module/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy module source
COPY action/interactive/presence_module /app/

# Create log directory
RUN mkdir -p /var/log/waddlebotlog

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot -m waddlebot

# Set proper permissions for app directory and log directory
RUN chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

EXPOSE 8042

USER waddlebot

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8042", "--workers", "4"]
