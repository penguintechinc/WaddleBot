FROM python:3.12-slim

LABEL maintainer="WaddleBot Team"
LABEL description="WaddleBot Discord Collector Module"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 waddlebot && \
    chown -R waddlebot:waddlebot /app

USER waddlebot

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/discord/health || exit 1

# Run the application (Discord bot + py4web)
CMD ["python", "-m", "py4web", "run", "apps", "--host", "0.0.0.0", "--port", "8000"]