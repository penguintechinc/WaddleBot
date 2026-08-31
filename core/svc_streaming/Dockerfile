# svc-streaming -- SCAFFOLD ONLY. Not wired into CI yet; the Helm Deployment
# (k8s/helm/waddlebot/templates/svc-streaming.yaml) still points at
# pipeline.pythonBaseImage as a placeholder until this image has a real CI
# build. Note the design spec targets Rust for the eventual control plane
# (docs/plans/2026-08-31-svc-streaming-design.md §1) -- this Dockerfile is
# the Python/Quart scaffold, mirroring core/svc_presentation/Dockerfile;
# the Rust rewrite is follow-up work. Build from parent (repo root):
#   docker build -f core/svc_streaming/Dockerfile -t waddlebot/svc-streaming:local .

FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

# Shared library
COPY libs/flask_core /app/libs/flask_core
RUN cd /app/libs/flask_core && pip install --no-cache-dir .

# Module files
COPY core/svc_streaming/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY core/svc_streaming /app/

RUN mkdir -p /var/log/waddlebotlog \
    && useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app /var/log/waddlebotlog

USER appuser

# MODULE_PORT is set by the Helm Deployment (default 8208 here too) --
# shell form so ${MODULE_PORT} is honored if overridden at runtime.
ENV MODULE_PORT=8208
CMD ["sh", "-c", "hypercorn app:app --bind 0.0.0.0:${MODULE_PORT} --workers 2"]
