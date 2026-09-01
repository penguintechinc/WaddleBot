FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

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

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set proper permissions
RUN chown -R appuser:appuser /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8095/health || exit 1

EXPOSE 8095

USER appuser

CMD ["python", "-m", "quart", "--app", "app:app", "run", "--host", "0.0.0.0", "--port", "8095"]
