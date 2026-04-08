FROM python:3.13-slim-bookworm@sha256:e347c5f57bcf7e5e1ca2af9a97c7ef2f33c4d3b21e27f1e4b2d3f5e6f7a8b9c0d AS builder
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies with no cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY identity_core_module/ ./identity_core_module/
COPY security_core_module/ ./security_core_module/
COPY credential_manager_module/ ./credential_manager_module/


FROM python:3.13-slim-bookworm@sha256:e347c5f57bcf7e5e1ca2af9a97c7ef2f33c4d3b21e27f1e4b2d3f5e6f7a8b9c0d
WORKDIR /app

# Copy from builder
COPY --from=builder /app /app

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8050

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import socket; s = socket.socket(); s.connect(('localhost', 8050)); s.close()" || exit 1

# Run Quart app via Hypercorn
CMD ["python", "-m", "hypercorn", "app:app", "--bind", "0.0.0.0:8050"]
