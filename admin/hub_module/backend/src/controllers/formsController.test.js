/**
 * Tests for the forms controller's formId validation.
 *
 * Run with the repo's configured runner: `npm test` (node --test).
 *
 * getForm/deleteForm/getFormSubmissions splice `req.params.formId`
 * directly into an internal engagement-service URL
 * (`${ENGAGEMENT_URL}/api/v1/forms/${formId}`). Before the fix this was
 * unvalidated request-forgery-class input — a crafted formId such as
 * `../../internal/admin` could redirect the proxied request to an
 * unintended downstream path. These tests assert a non-numeric formId is
 * rejected with 400 *before* axios is ever called, and a legitimate
 * numeric formId still reaches the downstream call.
 */
import assert from 'node:assert/strict';
import { describe, it, mock } from 'node:test';
import axios from 'axios';

import { getForm, deleteForm, getFormSubmissions } from './formsController.js';

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

describe('formsController — formId is validated before proxying', () => {
  const attackerFormIds = [
    '../../internal/admin',
    '1; DROP TABLE forms',
    'abc',
    '1e5',
    '-1',
    '1/../2',
    '',
  ];

  for (const formId of attackerFormIds) {
    it(`getForm rejects formId=${JSON.stringify(formId)} without calling axios`, async () => {
      const getMock = mock.method(axios, 'get', async () => {
        throw new Error('axios.get should not have been called for an invalid formId');
      });
      try {
        const req = { params: { communityId: '1', formId } };
        const res = mockRes();
        await getForm(req, res);

        assert.equal(getMock.mock.callCount(), 0);
        assert.equal(res.statusCode, 400);
        assert.equal(res.body.success, false);
        assert.match(res.body.error, /formId must be a positive integer/);
      } finally {
        getMock.mock.restore();
      }
    });

    it(`deleteForm rejects formId=${JSON.stringify(formId)} without calling axios`, async () => {
      const deleteMock = mock.method(axios, 'delete', async () => {
        throw new Error('axios.delete should not have been called for an invalid formId');
      });
      try {
        const req = { params: { communityId: '1', formId } };
        const res = mockRes();
        await deleteForm(req, res);

        assert.equal(deleteMock.mock.callCount(), 0);
        assert.equal(res.statusCode, 400);
      } finally {
        deleteMock.mock.restore();
      }
    });
  }

  it('getForm proxies a legitimate numeric formId to the exact expected URL', async () => {
    const getMock = mock.method(axios, 'get', async (url) => ({
      data: { form: { id: url } },
    }));
    try {
      const req = {
        params: { communityId: '7', formId: '42' },
        headers: { authorization: 'Bearer test-token' },
      };
      const res = mockRes();
      await getForm(req, res);

      assert.equal(getMock.mock.callCount(), 1);
      const [url] = getMock.mock.calls[0].arguments;
      assert.match(url, /\/api\/v1\/forms\/42$/);
      assert.equal(res.statusCode, 200);
      assert.equal(res.body.success, true);
    } finally {
      getMock.mock.restore();
    }
  });

  it('getFormSubmissions rejects a non-numeric formId without calling axios', async () => {
    const getMock = mock.method(axios, 'get', async () => {
      throw new Error('axios.get should not have been called');
    });
    try {
      const req = { params: { communityId: '1', formId: '../../internal/admin' } };
      const res = mockRes();
      await getFormSubmissions(req, res);

      assert.equal(getMock.mock.callCount(), 0);
      assert.equal(res.statusCode, 400);
    } finally {
      getMock.mock.restore();
    }
  });

  it('getFormSubmissions proxies a legitimate numeric formId', async () => {
    const getMock = mock.method(axios, 'get', async () => ({ data: { submissions: [] } }));
    try {
      const req = {
        params: { communityId: '1', formId: '9' },
        headers: { authorization: 'Bearer test-token' },
      };
      const res = mockRes();
      await getFormSubmissions(req, res);

      assert.equal(getMock.mock.callCount(), 1);
      const [url] = getMock.mock.calls[0].arguments;
      assert.match(url, /\/api\/v1\/forms\/9\/submissions$/);
      assert.equal(res.statusCode, 200);
    } finally {
      getMock.mock.restore();
    }
  });
});
