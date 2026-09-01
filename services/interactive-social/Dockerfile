FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7 AS builder
WORKDIR /app
COPY services/interactive-social/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copy and install flask_core from shared libs
COPY libs/flask_core /app/libs/flask_core
RUN pip install --no-cache-dir /app/libs/flask_core

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY services/interactive-social/app.py .
COPY action/interactive/alias_interaction_module ./alias_interaction_module
COPY action/interactive/shoutout_interaction_module ./shoutout_interaction_module
COPY action/interactive/presence_module ./presence_module
COPY action/interactive/quote_interaction_module ./quote_interaction_module

EXPOSE 8010
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python3 -c "import httpx; resp = httpx.get('http://localhost:8010/healthz'); exit(0 if resp.status_code == 200 else 1)" || exit 1

RUN groupadd -r appuser && useradd -r -g appuser -m appuser && chown -R appuser:appuser /app

USER appuser

CMD ["python3", "app.py"]
