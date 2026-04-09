/**
 * Database Module
 * Centralized export of database connection and utilities
 */
import { query, getClient, transaction, checkConnection, closePool, getPoolMetrics, pool } from '../config/database.js';

export const db = {
  query,
  getClient,
  transaction,
  checkConnection,
  closePool,
  getPoolMetrics,
  pool,
};

export default db;
