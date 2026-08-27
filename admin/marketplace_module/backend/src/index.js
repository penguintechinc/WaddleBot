/**
 * Marketplace Module - Express Application Entry Point
 * Module Distribution and Community Subscriptions
 */
import express from 'express';
import { createServer } from 'http';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import cookieParser from 'cookie-parser';

import { config } from './config/index.js';
import { checkConnection, closePool, query } from './config/database.js';
import { logger } from './utils/logger.js';
import { errorHandler, notFoundHandler } from './middleware/errorHandler.js';
import { sanitizeBody } from './middleware/validation.js';
import { setCsrfToken, verifyCsrfToken } from './middleware/csrf.js';
import routes from './routes/index.js';

/**
 * Initialize database tables
 */
async function initializeDatabase() {
  try {
    // Note: Tables are created in hub_module, we just verify they exist

    // Verify hub_modules table exists
    await query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'hub_modules'
      )
    `);

    // Verify hub_module_installations table exists
    await query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'hub_module_installations'
      )
    `);

    // Verify hub_module_reviews table exists
    await query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'hub_module_reviews'
      )
    `);

    logger.system('Database tables verified successfully');
  } catch (err) {
    logger.error('Database verification failed', { error: err.message });
    throw err;
  }
}

// Create Express app
const app = express();

// Trust proxy (for rate limiting behind reverse proxy)
app.set('trust proxy', 1);

// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "'unsafe-inline'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: ["'self'"],
      fontSrc: ["'self'", "data:"],
      objectSrc: ["'none'"],
      mediaSrc: ["'self'"],
      frameSrc: ["'none'"],
    },
  },
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true,
  },
}));

// CORS
app.use(cors({
  origin: config.cors.origin,
  credentials: true,
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: config.rateLimit.windowMs,
  max: config.rateLimit.maxRequests,
  message: { success: false, error: { code: 'RATE_LIMITED', message: 'Too many requests' } },
  standardHeaders: true,
  legacyHeaders: false,
});
app.use('/api/', limiter);

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Cookie parsing
app.use(cookieParser());

// CSRF protection for browser sessions that authenticate with a cookie.
// Bearer-token, service-key, and provider-webhook requests do not rely on
// ambient browser credentials and are handled explicitly by the middleware.
app.use(setCsrfToken);
app.use(verifyCsrfToken);

// XSS protection - sanitize all string inputs
app.use(sanitizeBody);

// Request logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    // Only log API requests
    if (req.path.startsWith('/api/') || req.path === '/health') {
      logger.http(req, res, duration);
    }
  });
  next();
});

// Health check endpoint
app.get('/health', async (req, res) => {
  const dbHealthy = await checkConnection();
  const status = dbHealthy ? 'healthy' : 'degraded';

  res.status(dbHealthy ? 200 : 503).json({
    module: 'marketplace_module',
    version: '1.0.0',
    status,
    timestamp: new Date().toISOString(),
    database: dbHealthy ? 'connected' : 'disconnected',
  });
});

// Metrics endpoint (for internal monitoring)
app.get('/metrics', async (req, res) => {
  const { getPoolMetrics } = await import('./config/database.js');
  const poolMetrics = getPoolMetrics();

  res.json({
    module: 'marketplace_module',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    database: {
      pool: poolMetrics,
      health: await checkConnection(),
    },
    uptime: process.uptime(),
    memory: process.memoryUsage(),
  });
});

// API routes
app.use('/api/v1', routes);

// 404 handler for API routes
app.use('/api/', notFoundHandler);

// Global error handler
app.use(errorHandler);

// Create HTTP server
const httpServer = createServer(app);

// Graceful shutdown
async function shutdown(signal) {
  logger.system(`${signal} received, shutting down gracefully`);

  // Close HTTP server
  httpServer.close();

  // Close database pool
  await closePool();

  process.exit(0);
}

// Start server
async function start() {
  // Initialize/verify database tables
  await initializeDatabase();

  // Start HTTP server
  httpServer.listen(config.port, config.host, () => {
    logger.system('Marketplace module started', {
      port: config.port,
      host: config.host,
      env: config.env,
    });
  });

  // Handle server errors
  httpServer.on('error', (err) => {
    logger.error('Server error', { error: err.message });
    process.exit(1);
  });

  // Setup graceful shutdown handlers
  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));
}

start().catch((err) => {
  logger.error('Failed to start server', { error: err.message });
  process.exit(1);
});

export default app;
