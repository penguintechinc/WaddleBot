/**
 * API Type Safety Tests
 * Verifies no integer/varchar type mismatches cause 500 errors on JOIN queries.
 *
 * Background: A pre-existing 500 error on GET /api/v1/communities/:id/members
 * was caused by `integer = character varying` mismatch in the LEFT JOIN between
 * hub_users.id (INTEGER) and community_members.user_id (VARCHAR).  The fix
 * (adding ::integer cast) was deployed, but these tests prevent regressions
 * across all endpoints that perform similar cross-type JOINs.
 */

const request = require('supertest');

const API_BASE_URL = global.TEST_CONFIG.API_BASE_URL;
const ADMIN_USER = global.TEST_CONFIG.ADMIN_USER;

describe('API Type Safety - No integer/varchar mismatches', () => {
  let authToken;
  let csrfToken;
  let testCommunityId;

  beforeAll(async () => {
    // Get CSRF token
    const csrfResponse = await request(API_BASE_URL)
      .get('/api/v1/auth/csrf');

    if (csrfResponse.body && csrfResponse.body.csrfToken) {
      csrfToken = csrfResponse.body.csrfToken;
    }

    // Login as admin to get auth token
    const loginResponse = await request(API_BASE_URL)
      .post('/api/v1/auth/login')
      .set('X-CSRF-Token', csrfToken || '')
      .send({
        email: ADMIN_USER.email,
        password: ADMIN_USER.password
      });

    if (loginResponse.status === 200 && loginResponse.body.token) {
      authToken = loginResponse.body.token;
    }

    // Find a community to test against
    if (authToken) {
      const commResponse = await request(API_BASE_URL)
        .get('/api/v1/communities')
        .set('Authorization', `Bearer ${authToken}`);

      if (commResponse.status === 200) {
        const communities = commResponse.body.communities || commResponse.body.data || [];
        if (communities.length > 0) {
          testCommunityId = communities[0].id;
        }
      }
    }
  });

  // Endpoints that perform JOINs between hub_users and community_members
  // (or similar cross-type-column JOINs) and historically broke with
  // "operator does not exist: integer = character varying"
  const joinEndpoints = [
    { method: 'GET', path: '/members', desc: 'community members list' },
    { method: 'GET', path: '/members?page=1&limit=25', desc: 'community members paginated' },
    { method: 'GET', path: '/leaderboard', desc: 'community leaderboard' },
    { method: 'GET', path: '/activity', desc: 'community activity' },
  ];

  describe('Community member endpoints (hub_users JOIN community_members)', () => {
    test.each(joinEndpoints)(
      '$desc ($method /api/v1/communities/:id$path) does not return 500',
      async ({ method, path }) => {
        if (!authToken) {
          console.warn('Skipping: could not obtain auth token');
          return;
        }
        if (!testCommunityId) {
          console.warn('Skipping: no test community found');
          return;
        }

        const url = `/api/v1/communities/${testCommunityId}${path}`;
        const res = await request(API_BASE_URL)
          [method.toLowerCase()](url)
          .set('Authorization', `Bearer ${authToken}`);

        // Primary assertion: must not be a 500 server error
        expect(res.status).not.toBe(500);

        // Secondary: if somehow 500, verify it's not the type mismatch
        if (res.status >= 500) {
          const body = JSON.stringify(res.body);
          expect(body).not.toContain('operator does not exist');
          expect(body).not.toContain('integer = character varying');
        }
      }
    );
  });

  describe('Admin member endpoints', () => {
    it('GET /api/v1/admin/:id/members does not return 500', async () => {
      if (!authToken || !testCommunityId) {
        console.warn('Skipping: missing auth token or community');
        return;
      }

      const res = await request(API_BASE_URL)
        .get(`/api/v1/admin/${testCommunityId}/members`)
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).not.toBe(500);

      if (res.status >= 500) {
        const body = JSON.stringify(res.body);
        expect(body).not.toContain('operator does not exist');
      }
    });
  });

  describe('Interaction channel endpoints', () => {
    it('GET /api/v1/community/:id/interact/channels does not return 500', async () => {
      if (!authToken || !testCommunityId) {
        console.warn('Skipping: missing auth token or community');
        return;
      }

      const res = await request(API_BASE_URL)
        .get(`/api/v1/community/${testCommunityId}/interact/channels`)
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).not.toBe(500);

      if (res.status >= 500) {
        const body = JSON.stringify(res.body);
        expect(body).not.toContain('operator does not exist');
      }
    });
  });
});
