FROM python:3.13-slim-bookworm@sha256:f13a6b7565175da40695e8109f64cbc4d2e65f4c9ef2e3b321c3a44fa3c06fe7

WORKDIR /app

# Install migration dependencies
RUN pip install --no-cache-dir \
    alembic>=1.13 \
    sqlalchemy>=2.0 \
    psycopg2-binary \
    flask-sqlalchemy \
    flask-security-too

# Copy Alembic configuration
COPY alembic.ini .
COPY alembic/ alembic/

# Copy SQLAlchemy models (needed for target_metadata)
# Create __init__.py files so Python recognizes the nested package path
COPY libs/flask_core/ libs/flask_core/
RUN touch libs/__init__.py libs/flask_core/__init__.py

# Copy legacy SQL migrations (used by baseline migration)
COPY config/postgres/migrations/ config/postgres/migrations/

# Copy migration runner
COPY migrations/run-alembic.sh ./run.sh
RUN chmod +x ./run.sh

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set proper permissions for migrations
RUN chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["./run.sh"]
