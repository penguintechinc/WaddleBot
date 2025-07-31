FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r waddlebot && useradd -r -g waddlebot waddlebot
RUN chown -R waddlebot:waddlebot /app
USER waddlebot

# Expose port
EXPOSE 8030

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8030/health', timeout=5)"

# Run the application
CMD ["python", "app.py"]