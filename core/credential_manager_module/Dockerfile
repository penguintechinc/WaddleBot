FROM python:3.13-slim-bookworm

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY core/credential_manager_module/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY core/credential_manager_module/ .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8095/health || exit 1

EXPOSE 8095

CMD ["python", "-m", "quart", "--app", "app:app", "run", "--host", "0.0.0.0", "--port", "8095"]
