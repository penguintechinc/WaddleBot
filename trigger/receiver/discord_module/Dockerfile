# Build from parent directory: docker build -f discord_module/Dockerfile -t waddlebot/discord:latest .

FROM python:3.12-slim

WORKDIR /app

# Copy shared libraries
COPY libs/flask_core /app/libs/flask_core
COPY libs/platform_receiver /app/libs/platform_receiver

# Install shared libraries
RUN cd /app/libs/flask_core && pip install --no-cache-dir . && \
    cd /app/libs/platform_receiver && pip install --no-cache-dir .

# Copy module files
COPY trigger/receiver/discord_module/requirements.txt /app/
COPY trigger/receiver/discord_module /app/

# Install module dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create log directory
RUN mkdir -p /var/log/waddlebotlog

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot -m waddlebot

# Set proper permissions for app directory and log directory
RUN chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8003", "--workers", "4"]
