# Multi-stage build for combined webhook receiver service
FROM python:3.13-slim-bookworm@sha256:PLACEHOLDER_SHA as builder

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.13-slim-bookworm@sha256:PLACEHOLDER_SHA

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code and module directories
COPY app.py .
COPY slack_module slack_module
COPY teams_module teams_module
COPY mattermost_module mattermost_module
COPY googlechat_module googlechat_module

# Health check using Quart's health endpoint
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/healthz').read()" || exit 1

EXPOSE 8100

CMD ["python3", "-m", "hypercorn", "app:app", "--bind", "0.0.0.0:8100"]
