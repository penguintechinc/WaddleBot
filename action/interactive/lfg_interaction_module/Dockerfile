# Build from repo root: docker build -f action/interactive/lfg_interaction_module/Dockerfile -t waddlebot/lfg-interaction:latest .

FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

# Copy shared library
COPY libs/flask_core /app/libs/flask_core

# Install shared library
RUN cd /app/libs/flask_core && pip install --no-cache-dir .

# Copy module files
COPY action/interactive/lfg_interaction_module/requirements.txt /app/
COPY action/interactive/lfg_interaction_module /app/

# Install module dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create log directory
RUN mkdir -p /var/log/waddlebotlog

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot -m waddlebot

# Set proper permissions for app directory and log directory
RUN chown -R waddlebot:waddlebot /app /var/log/waddlebotlog

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8096", "--workers", "4"]
