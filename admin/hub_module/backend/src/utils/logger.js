/**
 * AAA Logging Utility
 * Authentication, Authorization, and Auditing logging
 * following Waddles logging patterns.
 */
import { config } from '../config/index.js';

const LOG_LEVELS = {
  error: 0,
  warn: 1,
  info: 2,
  debug: 3,
};

const currentLevel = LOG_LEVELS[config.logging.level] ?? LOG_LEVELS.info;

/**
 * Format log entry with timestamp and structured data
 */
function formatLog(level, message, data = {}) {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    level: level.toUpperCase(),
    module: 'hub_module',
    version: '1.0.0',
    message,
    ...data,
  };
  return JSON.stringify(logEntry);
}

/**
 * Write log to console (and optionally file in production)
 */
function writeLog(level, message, data) {
  if (LOG_LEVELS[level] > currentLevel) return;

  const formatted = formatLog(level, message, data);

  switch (level) {
    case 'error':
      console.error(formatted);
      break;
    case 'warn':
      console.warn(formatted);
      break;
    default:
      console.log(formatted);
  }
}

export const logger = {
  error: (message, data) => writeLog('error', message, data),
  warn: (message, data) => writeLog('warn', message, data),
  info: (message, data) => writeLog('info', message, data),
  debug: (message, data) => writeLog('debug', message, data),

  /**
   * Authentication event logging
   */
  auth: (action, data) => writeLog('info', `AUTH: ${action}`, {
    category: 'AUTH',
    ...data,
  }),

  /**
   * Authorization event logging
   */
  authz: (action, data) => writeLog('info', `AUTHZ: ${action}`, {
    category: 'AUTHZ',
    ...data,
  }),

  /**
   * Audit event logging
   */
  audit: (action, data) => writeLog('info', `AUDIT: ${action}`, {
    category: 'AUDIT',
    ...data,
  }),

  /**
   * System event logging
   */
  system: (message, data) => writeLog('info', `SYSTEM: ${message}`, {
    category: 'SYSTEM',
    ...data,
  }),

  /**
   * HTTP request logging
   */
  http: (req, res, duration) => {
    const data = {
      category: 'HTTP',
      method: req.method,
      path: req.path,
      status: res.statusCode,
      duration: `${duration}ms`,
      ip: req.ip,
      userAgent: req.get('user-agent')?.substring(0, 100),
    };
    if (req.user) {
      data.userId = req.user.id;
    }
    writeLog('info', `${req.method} ${req.path} ${res.statusCode}`, data);
  },
};

export default logger;
