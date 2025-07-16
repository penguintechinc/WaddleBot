FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot waddlebot
RUN chown -R waddlebot:waddlebot /app
USER waddlebot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8024/health || exit 1

# Expose port
EXPOSE 8024

# Environment variables
ENV PYTHONPATH=/app
ENV MODULE_NAME=inventory_interaction_module
ENV MODULE_VERSION=1.0.0
ENV MODULE_PORT=8024

# Run the application
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8024"]