# Multi-stage build for combined streaming trigger receiver service
# Supports: Twitch, YouTube Live, Kick streaming receivers
# Port: 8101

FROM python:3.13-slim-bookworm@sha256:fdb97db0e06c2af9a4dd8a25a1d7d0f08cbf33cc79f9a9fc1c3c5df5a5e5f5c1 AS builder
WORKDIR /app

# Copy requirements for pip dependency resolution
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# Copy all three module directories (maintain original structure)
COPY twitch_module twitch_module/
COPY youtube_live_module youtube_live_module/
COPY kick_module_flask kick_module_flask/
COPY app.py app.py

# Runtime stage
FROM python:3.13-slim-bookworm@sha256:fdb97db0e06c2af9a4dd8a25a1d7d0f08cbf33cc79f9a9fc1c3c5df5a5e5f5c1
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

# Copy application files
COPY --from=builder /app /app

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check using native Python (no curl)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python3 -c "import httpx; httpx.get('http://localhost:8101/healthz')" || exit 1

# Expose port 8101
EXPOSE 8101

# Run Quart app
CMD ["python3", "-m", "hypercorn", "app:app", "--bind", "0.0.0.0:8101"]
