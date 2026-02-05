/**
 * Email Service Utility
 * Handles sending verification emails and other transactional emails
 */
import crypto from 'crypto';
import { query } from '../config/database.js';
import { logger } from './logger.js';

// Encryption key (same as platformConfigController)
const ENCRYPTION_KEY = process.env.PLATFORM_ENCRYPTION_KEY ||
  crypto.scryptSync(process.env.JWT_SECRET || 'default-key', 'salt', 32);
const IV_LENGTH = 16;

/**
 * Decrypt a value
 */
function decrypt(text) {
  if (!text) return null;
  try {
    const parts = text.split(':');
    const iv = Buffer.from(parts[0], 'hex');
    const encrypted = parts[1];
    const decipher = crypto.createDecipheriv('aes-256-cbc', ENCRYPTION_KEY, iv);
    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    return decrypted;
  } catch {
    return null;
  }
}

/**
 * Get SMTP configuration from database or environment
 */
async function getEmailConfig() {
  const result = await query(
    `SELECT config_key, config_value, is_encrypted
     FROM platform_configs
     WHERE platform = 'email'`
  );

  const config = {};

  // Get from database
  for (const row of result.rows) {
    let value = row.config_value;
    if (row.is_encrypted) {
      value = decrypt(value);
    }
    config[row.config_key] = value;
  }

  // Override with environment variables
  const envMappings = {
    smtp_host: 'SMTP_HOST',
    smtp_port: 'SMTP_PORT',
    smtp_user: 'SMTP_USER',
    smtp_password: 'SMTP_PASSWORD',
    smtp_from: 'SMTP_FROM',
    smtp_from_name: 'SMTP_FROM_NAME',
    smtp_secure: 'SMTP_SECURE'
  };

  for (const [key, envVar] of Object.entries(envMappings)) {
    if (process.env[envVar]) {
      config[key] = process.env[envVar];
    }
  }

  return config;
}

/**
 * Check if email is properly configured
 */
export async function isEmailConfigured() {
  const config = await getEmailConfig();
  return !!(config.smtp_host && config.smtp_port && config.smtp_from);
}

/**
 * Create nodemailer transporter
 */
async function createTransporter() {
  const config = await getEmailConfig();

  if (!config.smtp_host || !config.smtp_port) {
    throw new Error('SMTP not configured');
  }

  const nodemailer = await import('nodemailer');

  const transportConfig = {
    host: config.smtp_host,
    port: parseInt(config.smtp_port, 10),
    secure: config.smtp_secure === 'true',
  };

  if (config.smtp_user && config.smtp_password) {
    transportConfig.auth = {
      user: config.smtp_user,
      pass: config.smtp_password
    };
  }

  return {
    transporter: nodemailer.default.createTransport(transportConfig),
    from: config.smtp_from_name
      ? `"${config.smtp_from_name}" <${config.smtp_from}>`
      : config.smtp_from
  };
}

/**
 * Generate a verification token
 */
export function generateVerificationToken() {
  return crypto.randomBytes(32).toString('hex');
}

/**
 * Send verification email to user
 */
export async function sendVerificationEmail(email, username, token) {
  try {
    const { transporter, from } = await createTransporter();

    const verificationUrl = `${process.env.HUB_URL || 'http://localhost:8060'}/verify-email?token=${token}`;

    const mailOptions = {
      from,
      to: email,
      subject: 'Verify your Waddles account',
      html: `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
          <h1 style="color: #333;">Welcome to Waddles, ${username || 'User'}!</h1>
          <p>Thanks for signing up. Please verify your email address by clicking the button below:</p>
          <div style="text-align: center; margin: 30px 0;">
            <a href="${verificationUrl}"
               style="background-color: #4CAF50; color: white; padding: 14px 28px;
                      text-decoration: none; border-radius: 4px; display: inline-block;">
              Verify Email
            </a>
          </div>
          <p>Or copy and paste this link into your browser:</p>
          <p style="color: #666; word-break: break-all;">${verificationUrl}</p>
          <p>This link will expire in 24 hours.</p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
          <p style="color: #999; font-size: 12px;">
            If you didn't create an account, you can safely ignore this email.
          </p>
        </div>
      `,
      text: `
Welcome to Waddles, ${username || 'User'}!

Thanks for signing up. Please verify your email address by visiting:
${verificationUrl}

This link will expire in 24 hours.

If you didn't create an account, you can safely ignore this email.
      `
    };

    await transporter.sendMail(mailOptions);

    logger.info('Verification email sent', { email, username });
    return { success: true };
  } catch (error) {
    logger.error('Failed to send verification email', { email, error: error.message });
    return { success: false, error: error.message };
  }
}

/**
 * Send password reset email
 */
export async function sendPasswordResetEmail(email, username, token) {
  try {
    const { transporter, from } = await createTransporter();

    const resetUrl = `${process.env.HUB_URL || 'http://localhost:8060'}/reset-password?token=${token}`;

    const mailOptions = {
      from,
      to: email,
      subject: 'Reset your Waddles password',
      html: `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
          <h1 style="color: #333;">Password Reset Request</h1>
          <p>Hi ${username || 'User'},</p>
          <p>We received a request to reset your password. Click the button below to choose a new password:</p>
          <div style="text-align: center; margin: 30px 0;">
            <a href="${resetUrl}"
               style="background-color: #2196F3; color: white; padding: 14px 28px;
                      text-decoration: none; border-radius: 4px; display: inline-block;">
              Reset Password
            </a>
          </div>
          <p>Or copy and paste this link into your browser:</p>
          <p style="color: #666; word-break: break-all;">${resetUrl}</p>
          <p>This link will expire in 1 hour.</p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
          <p style="color: #999; font-size: 12px;">
            If you didn't request a password reset, you can safely ignore this email.
          </p>
        </div>
      `,
      text: `
Password Reset Request

Hi ${username || 'User'},

We received a request to reset your password. Visit this link to choose a new password:
${resetUrl}

This link will expire in 1 hour.

If you didn't request a password reset, you can safely ignore this email.
      `
    };

    await transporter.sendMail(mailOptions);

    logger.info('Password reset email sent', { email });
    return { success: true };
  } catch (error) {
    logger.error('Failed to send password reset email', { email, error: error.message });
    return { success: false, error: error.message };
  }
}

export default {
  isEmailConfigured,
  generateVerificationToken,
  sendVerificationEmail,
  sendPasswordResetEmail
};
