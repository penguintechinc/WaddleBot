FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

# uv replaces pip for dependency installation (pinned by digest)
COPY --from=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa /uv /usr/local/bin/uv

WORKDIR /app

# Copy and install shared library
COPY libs/flask_core /app/libs/flask_core
RUN uv pip install --system --no-cache /app/libs/flask_core

# Install dependencies
COPY action/interactive/loyalty_interaction_module/requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application
COPY action/interactive/loyalty_interaction_module /app/

# Copy standard healthcheck script
COPY scripts/healthcheck.py /usr/local/bin/healthcheck.py
RUN chmod 755 /usr/local/bin/healthcheck.py

# Create the non-root user and default file-log directory before dropping
# privileges.
RUN useradd -m -u 1000 waddlebot \
    && mkdir -p /var/log/waddlebotlog \
    && chown -R waddlebot:waddlebot /app /var/log/waddlebotlog
USER waddlebot

EXPOSE 8032

# Health check (using /healthz for Kubernetes compatibility)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 /usr/local/bin/healthcheck.py http://localhost:8032/healthz

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8032"]
