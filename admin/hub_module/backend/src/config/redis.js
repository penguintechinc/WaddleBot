/**
 * Redis Configuration
 * A single lazily-connected shared client using node-redis (redis v4).
 *
 * The hub backend uses Redis only for lightweight pub/sub cache-invalidation
 * signalling (e.g. the "feature_flags:reload" channel the Python router
 * subscribes to). It is NOT a hard dependency: if REDIS_URL is unset the
 * exported client is null, and if Redis is unreachable every operation fails
 * soft (logged, never thrown). The app must run fine with Redis down or absent.
 */
import { createClient } from 'redis';
import { logger } from '../utils/logger.js';

// REDIS_URL example (see docker-compose.yml): redis://hub:<pw>@infra-redis:6379/0
const redisUrl = process.env.REDIS_URL || null;

/**
 * Build the shared client. Connection is deferred until first use so that
 * importing this module never blocks startup or crashes when Redis is absent.
 * Returns null when no REDIS_URL is configured.
 */
function buildClient() {
  if (!redisUrl) {
    logger.debug('Redis disabled: REDIS_URL is not set');
    return null;
  }

  const c = createClient({
    url: redisUrl,
    socket: {
      connectTimeout: 5000,
      // Give up after a handful of attempts so an absent Redis does not
      // produce an endless reconnect/error loop in the logs.
      reconnectStrategy: (retries) => (retries > 10 ? false : Math.min(retries * 200, 3000)),
    },
  });

  // An 'error' listener is mandatory: without one, node-redis emits on the
  // process and an unhandled 'error' would crash the app.
  c.on('error', (err) => logger.warn('Redis client error', { error: err.message }));
  c.on('ready', () => logger.info('Redis client ready'));
  c.on('end', () => logger.debug('Redis connection closed'));

  return c;
}

// Single shared client instance (or null when Redis is not configured).
const client = buildClient();

// De-dupe concurrent connect attempts.
let connecting = null;

/**
 * Return a connected client, or null if Redis is unavailable/unconfigured.
 * Never throws.
 * @returns {Promise<import('redis').RedisClientType|null>}
 */
export async function getRedisClient() {
  if (!client) return null;
  if (client.isOpen) return client;

  if (!connecting) {
    connecting = client.connect().catch((err) => {
      logger.warn('Redis connection failed', { error: err.message });
      return null;
    }).finally(() => {
      connecting = null;
    });
  }
  await connecting;
  return client.isOpen ? client : null;
}

/**
 * Fire-and-forget publish. Returns true if the message was handed to Redis,
 * false if Redis is unavailable. Never throws.
 * @param {string} channel
 * @param {string} message
 * @returns {Promise<boolean>}
 */
export async function publish(channel, message) {
  const c = await getRedisClient();
  if (!c) return false;
  await c.publish(channel, message);
  return true;
}

/**
 * Check Redis connectivity. Never throws.
 * @returns {Promise<boolean>}
 */
export async function checkConnection() {
  try {
    const c = await getRedisClient();
    if (!c) return false;
    const pong = await c.ping();
    return pong === 'PONG';
  } catch {
    return false;
  }
}

/**
 * Close the shared client (best-effort, for graceful shutdown).
 */
export async function closeRedis() {
  if (client && client.isOpen) {
    try {
      await client.quit();
      logger.info('Redis client closed');
    } catch (err) {
      logger.warn('Error closing Redis client', { error: err.message });
    }
  }
}

export { client };
export default { getRedisClient, publish, checkConnection, closeRedis, client };
