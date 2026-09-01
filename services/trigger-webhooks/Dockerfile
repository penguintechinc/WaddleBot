# Multi-stage build for combined webhook receiver service
FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7 as builder

WORKDIR /app

# Copy requirements and install dependencies
COPY services/trigger-webhooks/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install flask_core from shared libs
COPY libs/flask_core /app/libs/flask_core
RUN pip install --no-cache-dir /app/libs/flask_core

# Final stage
FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy application code and module directories with ownership
COPY --chown=appuser:appuser services/trigger-webhooks/app.py .
COPY --chown=appuser:appuser trigger/receiver/slack_module slack_module
COPY --chown=appuser:appuser trigger/receiver/teams_module teams_module
COPY --chown=appuser:appuser trigger/receiver/mattermost_module mattermost_module
COPY --chown=appuser:appuser trigger/receiver/googlechat_module googlechat_module
COPY --chown=appuser:appuser libs/platform_receiver libs/platform_receiver
RUN touch libs/__init__.py && chown appuser:appuser libs/__init__.py

# Health check using Quart's health endpoint
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/healthz').read()" || exit 1

EXPOSE 8100

USER appuser

CMD ["python3", "-m", "hypercorn", "app:app", "--bind", "0.0.0.0:8100"]
