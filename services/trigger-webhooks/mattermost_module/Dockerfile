# Build from parent directory: docker build -f mattermost_module/Dockerfile -t waddlebot/mattermost:latest .

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

WORKDIR /app

# Copy shared libraries
COPY libs/flask_core /app/libs/flask_core
COPY libs/platform_receiver /app/libs/platform_receiver

# Install shared libraries
RUN cd /app/libs/flask_core && pip install --no-cache-dir . && \
    cd /app/libs/platform_receiver && pip install --no-cache-dir .

# Copy module files
COPY trigger/receiver/mattermost_module/requirements.txt /app/
COPY trigger/receiver/mattermost_module /app/

# Install module dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create log directory
RUN mkdir -p /var/log/waddlebotlog

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot -m waddlebot

# Set proper permissions for app directory and log directory
RUN chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

EXPOSE 8009

USER waddlebot

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8009", "--workers", "4"]
