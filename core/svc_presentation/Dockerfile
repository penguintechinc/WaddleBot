# svc-presentation -- overlay/music-station presentation container. Not
# wired into CI yet; the Helm Deployment
# (k8s/helm/waddlebot/templates/svc-presentation.yaml) still points at
# pipeline.pythonBaseImage as a placeholder until this image has a real CI
# build. Build from parent (repo root):
#   docker build -f core/svc_presentation/Dockerfile -t waddlebot/svc-presentation:local .

FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

# Shared library
COPY libs/flask_core /app/libs/flask_core
RUN cd /app/libs/flask_core && pip install --no-cache-dir .

# Module files -- requirements.txt is hash-pinned (uv pip compile
# --generate-hashes, requirements.in is the source); --require-hashes
# fails the build if a future edit ever reintroduces an unhashed line.
COPY core/svc_presentation/requirements.txt /app/
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
COPY core/svc_presentation /app/

RUN mkdir -p /var/log/waddlebotlog \
    && useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app /var/log/waddlebotlog

USER appuser

# MODULE_PORT is set by the Helm Deployment (default 8207 here too) --
# shell form so ${MODULE_PORT} is honored if overridden at runtime.
ENV MODULE_PORT=8207
CMD ["sh", "-c", "hypercorn app:app --bind 0.0.0.0:${MODULE_PORT} --workers 2"]
