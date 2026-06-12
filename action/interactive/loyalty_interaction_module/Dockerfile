FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

# Copy and install shared library
COPY libs/flask_core /app/libs/flask_core
RUN pip install --no-cache-dir /app/libs/flask_core

# Install dependencies
COPY action/interactive/loyalty_interaction_module/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY action/interactive/loyalty_interaction_module /app/

# Copy standard healthcheck script
COPY scripts/healthcheck.py /usr/local/bin/healthcheck.py
RUN chmod 755 /usr/local/bin/healthcheck.py

# Create non-root user
RUN useradd -m -u 1000 waddlebot && chown -R waddlebot:waddlebot /app
USER waddlebot

EXPOSE 8032

# Health check (using /healthz for Kubernetes compatibility)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 /usr/local/bin/healthcheck.py http://localhost:8032/healthz

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8032"]
