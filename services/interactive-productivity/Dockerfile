# Multi-stage build for interactive-productivity service
# Combines calendar, memories, and translate modules
FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7 AS builder

WORKDIR /app

# Copy requirements and install dependencies
COPY services/interactive-productivity/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy all three module directories
COPY action/interactive/calendar_interaction_module ./calendar_interaction_module
COPY action/interactive/memories_interaction_module ./memories_interaction_module
COPY action/interactive/translate_interaction_module ./translate_interaction_module

# Copy combined app
COPY services/interactive-productivity/app.py .

# Expose ports
# Port 8030: REST API (calendar, memories, translate)
# Port 50033: gRPC (translate module)
EXPOSE 8030 50033

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python3 -c "import http.client; conn = http.client.HTTPConnection('localhost', 8030); conn.request('GET', '/healthz'); conn.getresponse().status == 200 or exit(1)" || exit 1

CMD ["python3", "app.py"]
