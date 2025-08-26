FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot waddlebot

# Copy requirements first for better caching
COPY identity_core_module/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY identity_core_module/ .
COPY libs/ ./libs/

# Create log directory
RUN mkdir -p /var/log/waddlebotlog && chown -R waddlebot:waddlebot /var/log/waddlebotlog

# Set proper permissions
RUN chown -R waddlebot:waddlebot /app

# Switch to non-root user
USER waddlebot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8050/health', timeout=5)"

# Expose port
EXPOSE 8050

# Set environment variables
ENV PYTHONPATH=/app
ENV PY4WEB_APPS_FOLDER=/app

# Run the application
CMD ["python", "-m", "py4web", "run", "apps", "--host", "0.0.0.0", "--port", "8050", "--number_workers", "4"]