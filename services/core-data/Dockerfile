# Multi-stage build for core-data service
# Combines 4 modules: analytics, engagement, reputation, labels

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7 AS builder

WORKDIR /app

# Copy requirements
COPY services/core-data/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all 4 module source directories
COPY core/analytics_core_module /app/core/analytics_core_module
COPY core/engagement_module /app/core/engagement_module
COPY core/reputation_module /app/core/reputation_module
COPY core/labels_core_module /app/core/labels_core_module

# Copy shared libs
COPY libs /app/libs

# Copy combined app files
COPY services/core-data/app.py /app/app.py
COPY services/core-data/config.py /app/config.py
COPY services/core-data/engagement_bp.py /app/engagement_bp.py

# Final stage
FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

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
