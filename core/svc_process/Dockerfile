# svc-process -- real Quart control-plane + stage-runner. Rootless.
# Mirrors core/svc_ingest/Dockerfile exactly (same base digest pin -- see
# its own comment for the devops-containers.md rationale).

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7 AS builder
WORKDIR /app

COPY core/svc_process/requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY libs/flask_core /app/libs/flask_core
RUN pip install --no-cache-dir /app/libs/flask_core

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY core/svc_process/app.py core/svc_process/config.py core/svc_process/runner.py ./
COPY core/svc_process/bundles ./bundles

EXPOSE 8211
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python3 -c "import httpx; resp = httpx.get('http://localhost:8211/healthz'); exit(0 if resp.status_code == 200 else 1)" || exit 1

RUN mkdir -p /var/log/waddlebotlog \
    && groupadd -r appuser && useradd -r -g appuser -m appuser \
    && chown -R appuser:appuser /app /var/log/waddlebotlog

USER appuser

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8211"]
