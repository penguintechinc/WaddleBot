# Multi-stage build for combined serverless action module
FROM python:3.13-slim-bookworm@sha256:d0be73fcf9fc3c01a86f61a0a0be81eb2ac3f69f64c5f8db92aafd71b91da5c2 AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Runtime stage
# ============================================================================
FROM python:3.13-slim-bookworm@sha256:d0be73fcf9fc3c01a86f61a0a0be81eb2ac3f69f64c5f8db92aafd71b91da5c2

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app.py .
COPY lambda_action_module/ ./lambda_action_module/
COPY openwhisk_action_module/ ./openwhisk_action_module/
COPY gcp_functions_action_module/ ./gcp_functions_action_module/

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check - use native Python HTTP module (no curl required)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python3 -c "import http.client; conn = http.client.HTTPConnection('localhost', 8103); conn.request('GET', '/health'); exit(0 if conn.getresponse().status == 200 else 1)"

# Expose REST port (8103) and gRPC ports (50051, 50052, 50053)
EXPOSE 8103 50051 50052 50053

# Run application
CMD ["python3", "app.py"]
