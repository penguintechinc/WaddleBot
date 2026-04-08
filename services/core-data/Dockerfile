# Multi-stage build for core-data service
# Combines 4 modules: analytics, engagement, reputation, labels

FROM python:3.13-slim-bookworm@sha256:e0d3a84e83d6b90ae6aa7f0e9d7d4ba1c2b9b3e8f1a2c3d4e5f6a7b8c9d0e1f2 AS builder

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all 4 module source directories
COPY ../../core/analytics_core_module /app/core/analytics_core_module
COPY ../../core/engagement_module /app/core/engagement_module
COPY ../../core/reputation_module /app/core/reputation_module
COPY ../../core/labels_core_module /app/core/labels_core_module

# Copy shared libs
COPY ../../libs /app/libs

# Copy combined app.py
COPY app.py /app/app.py

# Final stage
FROM python:3.13-slim-bookworm@sha256:e0d3a84e83d6b90ae6aa7f0e9d7d4ba1c2b9b3e8f1a2c3d4e5f6a7b8c9d0e1f2

WORKDIR /app

# Copy installed packages and app from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

# Create non-root user for security
RUN useradd -m -u 1000 app && chown -R app:app /app
USER app

# Health check using native Python (no curl/wget)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8040/healthz').read()" || exit 1

# Expose port 8040 (unified port for all 4 modules)
EXPOSE 8040

# Run the combined service
CMD ["python3", "-m", "hypercorn", "app:app", "--bind", "0.0.0.0:8040"]
