# Multi-stage Dockerfile for WaddleBot Hub Module
# Stage 1: Build frontend
FROM node:20-bookworm-slim@sha256:1e85773c98c31d4fe5b545e4cb17379e617b348832fb3738b22a08f68dec30f3 AS frontend-build

WORKDIR /build/admin/hub_module/frontend

# Copy frontend package files
COPY admin/hub_module/frontend/package*.json ./

# Install dependencies (packages are public on npm)
RUN npm install

# Copy frontend source
COPY admin/hub_module/frontend/ ./

# Build frontend
RUN npm run build

# Stage 2: Production image
FROM node:20-bookworm-slim@sha256:1e85773c98c31d4fe5b545e4cb17379e617b348832fb3738b22a08f68dec30f3

WORKDIR /app

# Install dumb-init, curl for healthcheck, and build tools for native modules (bcrypt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    dumb-init curl make g++ \
    && rm -rf /var/lib/apt/lists/*


# Create non-root user
RUN groupadd -g 1001 nodejs && \
    useradd -u 1001 -g nodejs -s /bin/bash nodejs

# Copy backend package files
COPY admin/hub_module/backend/package*.json ./

# Install production dependencies only
RUN npm install --only=production

# Remove build tools to reduce image size (keep curl for healthcheck)
RUN apt-get purge -y make g++ && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Copy backend source
COPY --chown=nodejs:nodejs admin/hub_module/backend/src ./src

# Copy built frontend from build stage
COPY --chown=nodejs:nodejs --from=frontend-build /build/admin/hub_module/frontend/dist ./public

# Create log directory and fix ownership
RUN mkdir -p /var/log/waddlebotlog && chown -R nodejs:nodejs /var/log/waddlebotlog /app

# Set environment variables
ENV NODE_ENV=production
ENV PORT=8060

# Switch to non-root user
USER nodejs

# Expose port
EXPOSE 8060

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8060/health || exit 1

# Start with dumb-init
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "src/index.js"]
