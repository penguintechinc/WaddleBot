/**
 * Tests for the polls controller's pollId validation.
 *
 * Run with the repo's configured runner: `npm test` (node --test).
 *
 * getPoll/deletePoll splice `req.params.pollId` directly into an internal
 * engagement-service URL (`${ENGAGEMENT_URL}/api/v1/polls/${pollId}`).
 * Before the fix this was unvalidated request-forgery-class input. These
 * tests assert a non-numeric pollId is rejected with 400 *before* axios is
 * ever called, and a legitimate numeric pollId still reaches the
 * downstream call.
 */
import assert from 'node:assert/strict';
import { describe, it, mock } from 'node:test';
import axios from 'axios';

import { getPoll, deletePoll } from './pollsController.js';

/** Minimal Express response double capturing status/json calls. */
function mockRes() {
  return {
    statusCode: 200,
    body: undefined,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    },
  };
}

describe('pollsController — pollId is validated before proxying', () => {
  const attackerPollIds = ['../../internal/admin', '1; DROP TABLE polls', 'abc', '1e5', '-1', ''];

  for (const pollId of attackerPollIds) {
    it(`getPoll rejects pollId=${JSON.stringify(pollId)} without calling axios`, async () => {
      const getMock = mock.method(axios, 'get', async () => {
        throw new Error('axios.get should not have been called for an invalid pollId');
      });
      try {
        const req = { params: { communityId: '1', pollId } };
        const res = mockRes();
        await getPoll(req, res);

        assert.equal(getMock.mock.callCount(), 0);
        assert.equal(res.statusCode, 400);
        assert.equal(res.body.success, false);
        assert.match(res.body.error, /pollId must be a positive integer/);
      } finally {
        getMock.mock.restore();
      }
    });

    it(`deletePoll rejects pollId=${JSON.stringify(pollId)} without calling axios`, async () => {
      const deleteMock = mock.method(axios, 'delete', async () => {
        throw new Error('axios.delete should not have been called for an invalid pollId');
      });
      try {
        const req = { params: { communityId: '1', pollId } };
        const res = mockRes();
        await deletePoll(req, res);

        assert.equal(deleteMock.mock.callCount(), 0);
        assert.equal(res.statusCode, 400);
      } finally {
        deleteMock.mock.restore();
      }
    });
  }

  it('getPoll proxies a legitimate numeric pollId to the exact expected URL', async () => {
    const getMock = mock.method(axios, 'get', async (url) => ({
      data: { poll: { id: url } },
    }));
    try {
      const req = {
        params: { communityId: '7', pollId: '13' },
        headers: { authorization: 'Bearer test-token' },
      };
      const res = mockRes();
      await getPoll(req, res);

      assert.equal(getMock.mock.callCount(), 1);
      const [url] = getMock.mock.calls[0].arguments;
      assert.match(url, /\/api\/v1\/polls\/13$/);
      assert.equal(res.statusCode, 200);
      assert.equal(res.body.success, true);
    } finally {
      getMock.mock.restore();
    }
  });

  it('deletePoll proxies a legitimate numeric pollId to the exact expected URL', async () => {
    const deleteMock = mock.method(axios, 'delete', async () => ({}));
    try {
      const req = {
        params: { communityId: '7', pollId: '13' },
        headers: { authorization: 'Bearer test-token' },
      };
      const res = mockRes();
      await deletePoll(req, res);

      assert.equal(deleteMock.mock.callCount(), 1);
      const [url] = deleteMock.mock.calls[0].arguments;
      assert.match(url, /\/api\/v1\/polls\/13$/);
      assert.equal(res.statusCode, 200);
      assert.equal(res.body.success, true);
    } finally {
      deleteMock.mock.restore();
    }
  });
});
