# Browser Source Core Module Dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 waddlebot && \
    mkdir -p /var/log/waddlebotlog && \
    chown -R waddlebot:waddlebot /var/log/waddlebotlog

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=waddlebot:waddlebot . .

# Create required directories
RUN mkdir -p databases static templates && \
    chown -R waddlebot:waddlebot /app

# Switch to non-root user
USER waddlebot

# Expose ports (HTTP and WebSocket)
EXPOSE 8027 8028

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8027/browser/source/health').raise_for_status()"

# Run the application
CMD ["py4web", "run", "--host", "0.0.0.0", "--port", "8027", "--workers", "4", "app.py"]