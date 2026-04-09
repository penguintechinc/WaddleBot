# Multi-stage build for combined webhook receiver service
FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7 as builder

WORKDIR /app

# Copy requirements and install dependencies
COPY services/trigger-webhooks/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code and module directories
COPY services/trigger-webhooks/app.py .
COPY trigger/receiver/slack_module slack_module
COPY trigger/receiver/teams_module teams_module
COPY trigger/receiver/mattermost_module mattermost_module
COPY trigger/receiver/googlechat_module googlechat_module

# Health check using Quart's health endpoint
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/healthz').read()" || exit 1

EXPOSE 8100

CMD ["python3", "-m", "hypercorn", "app:app", "--bind", "0.0.0.0:8100"]
