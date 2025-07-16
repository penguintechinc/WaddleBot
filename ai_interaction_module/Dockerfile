FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY ai_interaction_module/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ai_interaction_module/ .
COPY libs/ ./libs/

# Create non-root user
RUN useradd -m -u 1000 waddlebot && \
    chown -R waddlebot:waddlebot /app
USER waddlebot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PY4WEB_APPS_FOLDER=/app
ENV PY4WEB_PASSWORD_FILE=/dev/null

# Run the application
CMD ["python", "-m", "py4web", "run", "apps", "--host", "0.0.0.0", "--port", "8000", "--number_workers", "4"]