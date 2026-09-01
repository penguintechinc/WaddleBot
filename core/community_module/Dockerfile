# Build from parent directory: docker build -f community_module/Dockerfile -t waddlebot/community:latest .

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

WORKDIR /app

# Copy shared library
COPY libs/flask_core /app/libs/flask_core

# Install shared library
RUN cd /app/libs/flask_core && pip install --no-cache-dir .

# Copy module files
COPY core/community_module/requirements.txt /app/
COPY core/community_module /app/

# Install module dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create log directory
RUN mkdir -p /var/log/waddlebotlog

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set proper permissions for app directory and log directory
RUN chown -R appuser:appuser /app /var/log/waddlebotlog

USER appuser

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8020", "--workers", "4"]
