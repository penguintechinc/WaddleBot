# Chat Filter Module Dockerfile - High Performance Container
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libc-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r waddlebot && useradd -r -g waddlebot waddlebot

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create log directory
RUN mkdir -p /var/log/waddlebotlog && \
    chown -R waddlebot:waddlebot /var/log/waddlebotlog && \
    chown -R waddlebot:waddlebot /app

# Switch to non-root user
USER waddlebot

# Expose the port
EXPOSE 8040

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8040/health')" || exit 1

# Run the application
CMD ["python", "-m", "py4web", "run", "apps", "--host", "0.0.0.0", "--port", "8040", "--number_workers", "4"]