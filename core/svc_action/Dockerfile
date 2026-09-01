# svc-action -- ACTION stage-runner. Rootless, pinned digest, mirrors the
# same shape as core/svc_streaming/Dockerfile / core/svc_presentation/Dockerfile.
# Replaces the Helm skeleton's placeholder image
# (k8s/helm/waddlebot/templates/svc-action.yaml `pipeline.pythonBaseImage`)
# once CI builds and pushes this image. Build from parent (repo root):
#   docker build -f core/svc_action/Dockerfile -t waddlebot/svc-action:local .

FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

# Shared library
COPY libs/flask_core /app/libs/flask_core
RUN cd /app/libs/flask_core && pip install --no-cache-dir .

# Module files
COPY core/svc_action/requirements.txt /app/
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
COPY core/svc_action /app/

RUN mkdir -p /var/log/waddlebotlog \
    && useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app /var/log/waddlebotlog

USER appuser

# MODULE_PORT is set by the Helm Deployment (default 8202 here too,
# values.yaml pipeline.svcAction.port) -- shell form so ${MODULE_PORT} is
# honored if overridden at runtime.
ENV MODULE_PORT=8202
CMD ["sh", "-c", "hypercorn app:app --bind 0.0.0.0:${MODULE_PORT} --workers 2"]
