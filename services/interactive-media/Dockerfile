# Multi-stage build for Interactive Media Service
# Combines clip, spotify, and youtube_music interaction modules

FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7 AS builder
WORKDIR /app

# Copy requirements and install dependencies
COPY services/interactive-media/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY services/interactive-media/app.py .

# Copy module directories
COPY action/interactive/clip_interaction_module ./clip_interaction_module
COPY action/interactive/spotify_interaction_module ./spotify_interaction_module
COPY action/interactive/youtube_music_interaction_module ./youtube_music_interaction_module

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV MODULE_NAME=interactive_media_service
ENV MODULE_VERSION=1.0.0
ENV MODULE_PORT=8105

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python3 -c "import asyncio; import sys; \
    async def check(): \
      import httpx; \
      try: \
        async with httpx.AsyncClient() as client: \
          r = await client.get('http://localhost:8105/healthz', timeout=2); \
          sys.exit(0 if r.status_code == 200 else 1); \
      except: sys.exit(1); \
    asyncio.run(check())" || exit 1

# Run the application
CMD ["python3", "app.py"]

# Expose port
EXPOSE 8105
