# hub-api -- Quart control-plane service (Task 0.5 scaffold).
#
# Multi-stage, rootless. Base digest reused from services/interactive-social/
# Dockerfile (already pinned in this repo -- devops-containers.md forbids
# inventing a second one for the same python:3.13-slim-bookworm tag).
FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7 AS builder
WORKDIR /app

COPY hub_api/requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# flask_core (libs/flask_core) is a real installable package (setup.py) --
# pip install it directly rather than sys.path surgery at runtime; its own
# requirements.in is the source of truth for its transitive deps.
COPY libs/flask_core /app/libs/flask_core
RUN pip install --no-cache-dir /app/libs/flask_core

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY hub_api/app.py hub_api/config.py ./
COPY hub_api/blueprints ./blueprints
COPY hub_api/routers ./routers
COPY hub_api/openapi ./openapi

EXPOSE 8204
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python3 -c "import httpx; resp = httpx.get('http://localhost:8204/healthz'); exit(0 if resp.status_code == 200 else 1)" || exit 1

RUN mkdir -p /var/log/waddlebotlog \
    && groupadd -r appuser && useradd -r -g appuser -m appuser \
    && chown -R appuser:appuser /app /var/log/waddlebotlog

USER appuser

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8204"]
