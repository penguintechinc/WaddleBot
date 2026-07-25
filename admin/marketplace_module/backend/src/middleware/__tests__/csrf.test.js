import { describe, expect, it, jest } from '@jest/globals';
import cookieParser from 'cookie-parser';
import express from 'express';
import request from 'supertest';

jest.unstable_mockModule('../../utils/logger.js', () => ({
  logger: {
    authz: jest.fn(),
  },
}));

jest.unstable_mockModule('../../config/index.js', () => ({
  config: {
    cors: {
      origin: 'http://localhost:5173',
    },
    env: 'test',
  },
}));

const {
  CSRF_COOKIE_NAME,
  CSRF_HEADER_NAME,
  setCsrfToken,
  verifyCsrfToken,
} = await import('../csrf.js');

function createApp() {
  const app = express();
  app.use(express.json());
  app.use(cookieParser());
  app.use(setCsrfToken);
  app.use(verifyCsrfToken);
  app.get('/api/v1/resource', (_req, res) => res.json({ success: true }));
  app.post('/api/v1/resource', (_req, res) => res.json({ success: true }));
  app.post('/api/v1/webhooks/stripe', (_req, res) => res.json({ success: true }));
  return app;
}

function cookieValue(setCookieHeader, name) {
  const cookie = setCookieHeader.find((value) => value.startsWith(`${name}=`));
  return cookie.split(';', 1)[0].slice(name.length + 1);
}

describe('marketplace CSRF middleware', () => {
  it('issues a secure double-submit token cookie', async () => {
    const response = await request(createApp()).get('/api/v1/resource');

    expect(response.status).toBe(200);
    expect(response.headers['set-cookie']).toEqual([
      expect.stringContaining(`${CSRF_COOKIE_NAME}=`),
    ]);
    expect(response.headers['set-cookie'][0]).toContain('SameSite=Strict');
    expect(response.headers['set-cookie'][0]).toContain('Path=/');
  });

  it('rejects a cookie-authenticated request without a CSRF header', async () => {
    const response = await request(createApp())
      .post('/api/v1/resource')
      .set('Origin', 'http://localhost:5173')
      .set('Cookie', 'token=session-token');

    expect(response.status).toBe(403);
    expect(response.body.error.code).toBe('CSRF_ERROR');
  });

  it('rejects a matching token sent from an untrusted origin', async () => {
    const token = 'a'.repeat(64);
    const response = await request(createApp())
      .post('/api/v1/resource')
      .set('Origin', 'https://attacker.example')
      .set(CSRF_HEADER_NAME, token)
      .set('Cookie', [`token=session-token`, `${CSRF_COOKIE_NAME}=${token}`]);

    expect(response.status).toBe(403);
    expect(response.body.error.code).toBe('CSRF_ERROR');
  });

  it('accepts a matching token from an allowed origin', async () => {
    const app = createApp();
    const tokenResponse = await request(app).get('/api/v1/resource');
    const token = cookieValue(tokenResponse.headers['set-cookie'], CSRF_COOKIE_NAME);

    const response = await request(app)
      .post('/api/v1/resource')
      .set('Origin', 'http://localhost:5173')
      .set(CSRF_HEADER_NAME, token)
      .set('Cookie', [`token=session-token`, `${CSRF_COOKIE_NAME}=${token}`]);

    expect(response.status).toBe(200);
    expect(response.body).toEqual({ success: true });
  });

  it('does not require CSRF tokens for explicit bearer authentication', async () => {
    const response = await request(createApp())
      .post('/api/v1/resource')
      .set('Authorization', 'Bearer api-token');

    expect(response.status).toBe(200);
  });

  it('leaves provider webhooks available for signature verification', async () => {
    const response = await request(createApp())
      .post('/api/v1/webhooks/stripe')
      .set('Cookie', 'token=session-token');

    expect(response.status).toBe(200);
  });
});
