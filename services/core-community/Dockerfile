# Multi-stage build for Core Community Service
# Combines 4 modules: community, workflow_core, browser_source, video_proxy
# Build from repo root: docker build -f services/core-community/Dockerfile -t core-community:latest .

# NOTE: Replace placeholder SHA256 with actual digest from:
# docker pull python:3.13-slim-bookworm && \
# docker inspect python:3.13-slim-bookworm --format='{{index .RepoDigests 0}}'

# Builder stage
FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7 AS builder

WORKDIR /app

# Copy requirements and install dependencies
COPY services/core-community/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/core-community/app.py .

# Copy all 4 module directories
COPY core/community_module ./community_module
COPY core/workflow_core_module ./workflow_core_module
COPY core/browser_source_core_module ./browser_source_core_module
COPY core/video_proxy_module ./video_proxy_module

# Copy shared libs
COPY libs ./libs

# Runtime stage
FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder --chown=appuser:appuser /app .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8020/healthz').read()"

# Expose port
EXPOSE 8020

# Start application
CMD ["python3", "-m", "hypercorn", "app:app", "--bind", "0.0.0.0:8020"]
