# svc-gateway -- real Quart control-plane + supervised persistent-socket receiver tasks. Rootless.
# Base digest matches hub_api/Dockerfile and core/svc_ingest/Dockerfile
# (devops-containers.md forbids inventing a second pin for the same
# python:3.13-slim-bookworm tag). Build from parent (repo root):
#   docker build -f core/svc_gateway/Dockerfile -t waddlebot/svc-gateway:local .

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7 AS builder
WORKDIR /app

COPY core/svc_gateway/requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# flask_core (libs/flask_core) is a real installable package (setup.py) --
# pip install it directly, matching hub_api/Dockerfile's own pattern.
COPY libs/flask_core /app/libs/flask_core
RUN pip install --no-cache-dir /app/libs/flask_core

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY core/svc_gateway/app.py core/svc_gateway/config.py core/svc_gateway/fanout.py \
     core/svc_gateway/supervisor.py ./
COPY core/svc_gateway/bundles ./bundles
COPY core/svc_gateway/receivers ./receivers

EXPOSE 8209
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python3 -c "import httpx; resp = httpx.get('http://localhost:8209/healthz'); exit(0 if resp.status_code == 200 else 1)" || exit 1

RUN mkdir -p /var/log/waddlebotlog \
    && groupadd -r appuser && useradd -r -g appuser -m appuser \
    && chown -R appuser:appuser /app /var/log/waddlebotlog

USER appuser

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8209"]
