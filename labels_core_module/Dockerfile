FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY labels_core_module/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY labels_core_module/ .

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot waddlebot
RUN chown -R waddlebot:waddlebot /app
USER waddlebot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8012/health || exit 1

# Expose port
EXPOSE 8012

# Run the application
CMD ["python", "-m", "py4web", "run", "apps", "--watch=off", "--port=8012", "--host=0.0.0.0"]