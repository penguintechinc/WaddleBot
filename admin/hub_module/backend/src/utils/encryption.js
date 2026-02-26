/**
 * AES-256-GCM encryption utilities for server credentials
 */
import crypto from 'crypto';

const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 12;
const AUTH_TAG_LENGTH = 16;

function getKey() {
  const hex = process.env.RCON_ENCRYPTION_KEY;
  if (!hex || hex.length !== 64) {
    throw new Error('RCON_ENCRYPTION_KEY must be a 64-character hex string');
  }
  return Buffer.from(hex, 'hex');
}

/**
 * Encrypt a plaintext string.
 * @param {string} plaintext - The string to encrypt
 * @returns {{ ciphertext: Buffer, iv: Buffer }} Encrypted data and IV
 */
export function encrypt(plaintext) {
  const key = getKey();
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv(ALGORITHM, key, iv, { authTagLength: AUTH_TAG_LENGTH });
  const encrypted = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const authTag = cipher.getAuthTag();
  // Append auth tag to ciphertext (Python cryptography expects this)
  const ciphertext = Buffer.concat([encrypted, authTag]);
  return { ciphertext, iv };
}

/**
 * Decrypt a ciphertext buffer.
 * @param {Buffer} ciphertext - The encrypted data (with auth tag appended)
 * @param {Buffer} iv - The initialization vector
 * @returns {string} The decrypted plaintext
 */
export function decrypt(ciphertext, iv) {
  const key = getKey();
  const authTag = ciphertext.slice(-AUTH_TAG_LENGTH);
  const encrypted = ciphertext.slice(0, -AUTH_TAG_LENGTH);
  const decipher = crypto.createDecipheriv(ALGORITHM, key, iv, { authTagLength: AUTH_TAG_LENGTH });
  decipher.setAuthTag(authTag);
  const decrypted = Buffer.concat([decipher.update(encrypted), decipher.final()]);
  return decrypted.toString('utf8');
}
