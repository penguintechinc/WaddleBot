/**
 * Hub Module Configuration
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
  port: parseInt(process.env.PORT || '8060', 10),
  host: process.env.HOST || '0.0.0.0',

  // Database
  database: {
    url: process.env.DATABASE_URL || (() => {
      const host = process.env.DATABASE_HOST || 'localhost';
      const port = process.env.DATABASE_PORT || '5432';
      const name = process.env.DATABASE_NAME || 'waddlebot';
      const user = process.env.DATABASE_USER || 'waddlebot';
      const pass = encodeURIComponent(process.env.DATABASE_PASSWORD || 'password');
      return `postgresql://${user}:${pass}@${host}:${port}/${name}`;
    })(),
    poolSize: parseInt(process.env.DATABASE_POOL_SIZE || process.env.DB_POOL_SIZE || '10', 10),
  },

  // JWT
  jwt: {
    secret: process.env.JWT_SECRET || (process.env.NODE_ENV === 'production' ? null : 'dev-secret-ONLY-FOR-DEVELOPMENT'),
    expiresIn: parseInt(process.env.JWT_EXPIRES_IN || '3600', 10),
  },

  // Session
  session: {
    ttl: parseInt(process.env.SESSION_TTL || '3600', 10),
  },

  // Temp Password
  tempPassword: {
    expiresHours: parseInt(process.env.TEMP_PASSWORD_EXPIRES_HOURS || '48', 10),
  },

  // OAuth / Identity
  identity: {
    apiUrl: process.env.IDENTITY_API_URL || 'http://identity-core:8050',
    callbackBaseUrl: process.env.OAUTH_CALLBACK_BASE_URL || 'http://localhost:8060',
  },

  // Module Integration
  modules: {
    router: process.env.ROUTER_API_URL || 'http://router:8000',
    reputation: process.env.REPUTATION_API_URL || 'http://reputation:8021',
    labels: process.env.LABELS_API_URL || 'http://labels-core:8023',
    inventory: process.env.INVENTORY_API_URL || 'http://inventory:8024',
    calendar: process.env.CALENDAR_API_URL || 'http://calendar:8030',
    memories: process.env.MEMORIES_API_URL || 'http://memories:8031',
    browserSource: process.env.BROWSER_SOURCE_API_URL || 'http://browser-source:8027',
    loyalty: process.env.LOYALTY_API_URL || 'http://loyalty-interaction:8032',
    analyticsCore: process.env.ANALYTICS_CORE_API_URL || 'http://analytics-core:8040',
  },

  // Custom Domains
  baseDomain: process.env.BASE_DOMAIN || 'waddlebot.io',
  blockedSubdomains: [
    'www', 'mail', 'smtp', 'imap', 'pop', 'ftp', 'api', 'admin', 'portal', 'hub',
    'app', 'dashboard', 'status', 'docs', 'help', 'support', 'billing',
    'cdn', 'static', 'assets', 'media', 'img', 'images', 'dev', 'staging',
    'test', 'demo', 'beta', 'auth', 'login', 'oauth', 'sso', 'identity',
  ],

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
    origin: (process.env.CORS_ORIGIN || 'http://localhost:5173')
      .split(',')
      .map(o => o.trim()),
  },
};

export default config;
