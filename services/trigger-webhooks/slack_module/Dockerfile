# Build from parent directory: docker build -f slack_module/Dockerfile -t waddlebot/slack:latest .

FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

# Copy shared libraries
COPY libs/flask_core /app/libs/flask_core
COPY libs/platform_receiver /app/libs/platform_receiver

# Install shared libraries
RUN cd /app/libs/flask_core && pip install --no-cache-dir . && \
    cd /app/libs/platform_receiver && pip install --no-cache-dir .

# Copy module files
COPY trigger/receiver/slack_module/requirements.txt /app/
COPY trigger/receiver/slack_module /app/

# Install module dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create log directory
RUN mkdir -p /var/log/waddlebotlog

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot -m waddlebot

# Set proper permissions for app directory and log directory
RUN chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8004", "--workers", "4"]
