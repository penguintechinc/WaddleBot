/**
 * Marketplace Module Configuration
 * Loads environment variables and provides typed configuration object.
 */
import dotenv from 'dotenv';

dotenv.config();

// Validate critical secrets in production
if (process.env.NODE_ENV === 'production') {
  if (!process.env.JWT_SECRET || process.env.JWT_SECRET.includes('dev-secret') || process.env.JWT_SECRET.includes('change-in-production')) {
    throw new Error('FATAL: JWT_SECRET must be set to a strong secret in production. Do not use default values.');
  }
  if (!process.env.SERVICE_API_KEY || process.env.SERVICE_API_KEY.includes('dev-service') || process.env.SERVICE_API_KEY.includes('change-in-production')) {
    throw new Error('FATAL: SERVICE_API_KEY must be set to a strong key in production. Do not use default values.');
  }
}

export const config = {
  // Server
  env: process.env.NODE_ENV || 'development',
  port: parseInt(process.env.MODULE_PORT || process.env.PORT || '8070', 10),
  host: process.env.HOST || '0.0.0.0',

  // Database
  database: {
    url: process.env.DATABASE_URL || 'postgresql://waddlebot:password@localhost:5432/waddlebot',
    poolSize: parseInt(process.env.DATABASE_POOL_SIZE || '10', 10),
  },

  // JWT
  jwt: {
    secret: process.env.JWT_SECRET || (process.env.NODE_ENV === 'production' ? null : 'dev-secret-ONLY-FOR-DEVELOPMENT'),
    expiresIn: parseInt(process.env.JWT_EXPIRES_IN || '3600', 10),
  },

  // Hub API
  hub: {
    apiUrl: process.env.HUB_API_URL || 'http://hub-module:8060',
  },

  // Module Integration
  modules: {
    router: process.env.ROUTER_API_URL || 'http://router:8000',
  },

  // Rate Limiting
  rateLimit: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '60000', 10),
    maxRequests: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '100', 10),
  },

  // Internal Service API Key (for service-to-service communication)
  serviceApiKey: process.env.SERVICE_API_KEY || (process.env.NODE_ENV === 'production' ? null : 'dev-service-key-ONLY-FOR-DEVELOPMENT'),

  // Logging
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    dir: process.env.LOG_DIR || '/var/log/waddlebotlog',
  },

  // CORS
  cors: {
    origin: process.env.CORS_ORIGIN || 'http://localhost:5173',
  },
};

export default config;
