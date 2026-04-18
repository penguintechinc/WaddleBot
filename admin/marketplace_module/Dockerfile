# Dockerfile for WaddleBot Marketplace Module
FROM node:20-bookworm-slim@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

# Install dumb-init and build tools for native modules (bcrypt)
RUN apk add --no-cache dumb-init python3 make g++

# Copy standard healthcheck script
COPY scripts/healthcheck.py /usr/local/bin/healthcheck.py
RUN chmod 755 /usr/local/bin/healthcheck.py

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# Copy backend package files
COPY admin/marketplace_module/backend/package*.json ./

# Install production dependencies only
RUN npm install --only=production

# Remove build tools to reduce image size
RUN apk del python3 make g++

# Copy backend source
COPY --chown=nodejs:nodejs admin/marketplace_module/backend/src ./src

# Create log directory and fix ownership
RUN mkdir -p /var/log/waddlebotlog && chown -R nodejs:nodejs /var/log/waddlebotlog /app

# Set environment variables
ENV NODE_ENV=production
ENV PORT=8070

# Switch to non-root user
USER nodejs

# Expose port
EXPOSE 8070

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 /usr/local/bin/healthcheck.py http://localhost:8070/health

# Start with dumb-init
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "src/index.js"]
