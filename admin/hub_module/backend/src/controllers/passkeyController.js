/**
 * Passkey Controller - WebAuthn passkey registration and authentication
 * Uses @simplewebauthn/server for credential management
 */
import { query } from '../config/database.js';
import { errors } from '../middleware/errorHandler.js';
import { logger } from '../utils/logger.js';
import {
  generateRegistrationOptions,
  verifyRegistrationResponse,
  generateAuthenticationOptions,
  verifyAuthenticationResponse,
} from '@simplewebauthn/server';
import jwt from 'jsonwebtoken';
import { config } from '../config/index.js';

const RP_NAME = process.env.PASSKEY_RP_NAME || 'Waddles';
const RP_ID = process.env.PASSKEY_RP_ID || 'localhost';
const ORIGIN = process.env.PASSKEY_ORIGIN || 'http://localhost:5173';

// In-memory challenge store (replace with Redis/DB for multi-instance prod)
const challengeStore = new Map();

/**
 * Start passkey registration — generate options for the browser
 * POST /user/passkey/register/start
 */
export async function startRegistration(req, res, next) {
  try {
    if (!req.user?.userId) return next(errors.unauthorized());

    const userRow = await query(
      'SELECT id, username, email FROM hub_users WHERE id = $1',
      [req.user.userId]
    );
    if (!userRow.rows.length) return next(errors.notFound('User not found'));
    const user = userRow.rows[0];

    const existingCredentials = await query(
      'SELECT credential_id FROM user_passkeys WHERE user_id = $1',
      [req.user.userId]
    );

    const options = await generateRegistrationOptions({
      rpName: RP_NAME,
      rpID: RP_ID,
      userID: Buffer.from(String(user.id)),
      userName: user.email,
      userDisplayName: user.username || user.email,
      attestationType: 'none',
      excludeCredentials: existingCredentials.rows.map(r => ({
        id: r.credential_id,
        type: 'public-key',
      })),
      authenticatorSelection: {
        residentKey: 'preferred',
        userVerification: 'preferred',
      },
    });

    challengeStore.set(req.user.userId, options.challenge);
    setTimeout(() => challengeStore.delete(req.user.userId), 5 * 60 * 1000);

    res.json({ success: true, options });
  } catch (err) {
    next(err);
  }
}

/**
 * Finish passkey registration — verify and store credential
 * POST /user/passkey/register/finish
 */
export async function finishRegistration(req, res, next) {
  try {
    if (!req.user?.userId) return next(errors.unauthorized());

    const { credential, deviceName } = req.body;
    const expectedChallenge = challengeStore.get(req.user.userId);
    if (!expectedChallenge) {
      return next(errors.badRequest('Registration challenge expired or not started'));
    }

    const verification = await verifyRegistrationResponse({
      response: credential,
      expectedChallenge,
      expectedOrigin: ORIGIN,
      expectedRPID: RP_ID,
    });

    if (!verification.verified || !verification.registrationInfo) {
      return next(errors.badRequest('Passkey verification failed'));
    }

    const { credentialID, credentialPublicKey, counter } = verification.registrationInfo;

    await query(
      `INSERT INTO user_passkeys (user_id, credential_id, public_key, sign_count, device_name)
       VALUES ($1, $2, $3, $4, $5)`,
      [
        req.user.userId,
        Buffer.from(credentialID).toString('base64url'),
        Buffer.from(credentialPublicKey).toString('base64url'),
        counter,
        deviceName || 'Passkey',
      ]
    );

    challengeStore.delete(req.user.userId);
    logger.audit('Passkey registered', { userId: req.user.userId });
    res.json({ success: true });
  } catch (err) {
    next(err);
  }
}

/**
 * Start passkey login — generate authentication options
 * POST /auth/passkey/login/start
 */
export async function startLogin(req, res, next) {
  try {
    const options = await generateAuthenticationOptions({
      rpID: RP_ID,
      userVerification: 'preferred',
    });

    // Store challenge keyed by challenge string itself
    challengeStore.set(`auth_${options.challenge}`, options.challenge);
    setTimeout(() => challengeStore.delete(`auth_${options.challenge}`), 5 * 60 * 1000);

    res.json({ success: true, options });
  } catch (err) {
    next(err);
  }
}

/**
 * Finish passkey login — verify and issue JWT
 * POST /auth/passkey/login/finish
 */
export async function finishLogin(req, res, next) {
  try {
    const { credential } = req.body;

    const credentialId = credential?.id;
    if (!credentialId) return next(errors.badRequest('Missing credential'));

    const passkeyRow = await query(
      `SELECT pk.*, u.id as uid, u.username, u.email, u.role
       FROM user_passkeys pk
       JOIN hub_users u ON u.id = pk.user_id
       WHERE pk.credential_id = $1`,
      [credentialId]
    );
    if (!passkeyRow.rows.length) return next(errors.unauthorized('Passkey not found'));
    const passkey = passkeyRow.rows[0];

    const expectedChallenge = challengeStore.get(`auth_${credential.response?.clientDataJSON}`);
    // Find challenge from stored map — look for any matching auth_ key
    let challenge = null;
    for (const [k, v] of challengeStore.entries()) {
      if (k.startsWith('auth_')) { challenge = v; break; }
    }
    if (!challenge) return next(errors.badRequest('Authentication challenge expired'));

    const verification = await verifyAuthenticationResponse({
      response: credential,
      expectedChallenge: challenge,
      expectedOrigin: ORIGIN,
      expectedRPID: RP_ID,
      authenticator: {
        credentialID: Buffer.from(passkey.credential_id, 'base64url'),
        credentialPublicKey: Buffer.from(passkey.public_key, 'base64url'),
        counter: passkey.sign_count,
      },
    });

    if (!verification.verified) return next(errors.unauthorized('Passkey verification failed'));

    // Update sign count and last_used_at
    await query(
      'UPDATE user_passkeys SET sign_count = $1, last_used_at = NOW() WHERE id = $2',
      [verification.authenticationInfo.newCounter, passkey.id]
    );
    for (const k of challengeStore.keys()) {
      if (k.startsWith('auth_')) challengeStore.delete(k);
    }

    const token = jwt.sign(
      { userId: passkey.uid, email: passkey.email, username: passkey.username, role: passkey.role },
      config.jwtSecret,
      { expiresIn: '7d' }
    );

    res.json({ success: true, token, user: { id: passkey.uid, email: passkey.email, username: passkey.username, role: passkey.role } });
  } catch (err) {
    next(err);
  }
}

/**
 * List user's registered passkeys
 * GET /user/passkey/credentials
 */
export async function listCredentials(req, res, next) {
  try {
    if (!req.user?.userId) return next(errors.unauthorized());
    const result = await query(
      'SELECT id, device_name, created_at, last_used_at FROM user_passkeys WHERE user_id = $1 ORDER BY created_at DESC',
      [req.user.userId]
    );
    res.json({ success: true, credentials: result.rows });
  } catch (err) {
    next(err);
  }
}

/**
 * Remove a passkey
 * DELETE /user/passkey/credentials/:id
 */
export async function removeCredential(req, res, next) {
  try {
    if (!req.user?.userId) return next(errors.unauthorized());
    const { id } = req.params;
    await query(
      'DELETE FROM user_passkeys WHERE id = $1 AND user_id = $2',
      [parseInt(id, 10), req.user.userId]
    );
    res.json({ success: true });
  } catch (err) {
    next(err);
  }
}
