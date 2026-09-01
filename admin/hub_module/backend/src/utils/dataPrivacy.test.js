/**
 * Tests for GDPR data subject rights and the CCPA/CPRA opt-out signal.
 *
 * Run with the repo's configured runner: `npm test` (node --test).
 *
 * The export is tested through collectUserData, which takes its query function
 * as an argument — that keeps the assertions on *what is disclosed and what is
 * withheld* rather than on database plumbing, which is the part with a
 * compliance consequence.
 */
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { collectUserData } from './userDataExport.js';
import {
  applyGlobalPrivacyControl,
  hasGlobalPrivacyControl,
} from './globalPrivacyControl.js';

/** Records every SQL statement issued and returns one row per source. */
function recordingQuery(rowsBySql = () => [{ ok: true }]) {
  const statements = [];
  const fn = async (sql, params) => {
    statements.push({ sql, params });
    return { rows: rowsBySql(sql) };
  };
  fn.statements = statements;
  return fn;
}

describe('collectUserData', () => {
  it('queries every source scoped to the subject', async () => {
    const q = recordingQuery();
    const { data, failures } = await collectUserData(q, 42);

    assert.equal(failures.length, 0);
    assert.ok(q.statements.length > 0, 'no sources queried — the export is empty');
    for (const { params } of q.statements) {
      assert.deepEqual(params, [42], 'a source was not scoped to the subject id');
    }
    // Access must cover retained data too, not only what erasure would remove.
    for (const key of ['account', 'profile', 'linked_identities', 'cookie_consent']) {
      assert.ok(key in data, `missing export section: ${key}`);
    }
  });

  it('never selects credential material', async () => {
    const q = recordingQuery();
    await collectUserData(q, 1);

    const forbidden = [
      'password_hash',
      'session_token',
      'public_key',
      'credential_id',
      'email_verification_token',
      'password_reset_token',
    ];

    for (const { sql } of q.statements) {
      assert.ok(!/select\s+\*/i.test(sql), `SELECT * would leak future columns: ${sql}`);
      for (const column of forbidden) {
        assert.ok(
          !sql.includes(column),
          `export would disclose credential material (${column}) in: ${sql}`,
        );
      }
    }
  });

  it('reports a failing source instead of aborting the whole export', async () => {
    let calls = 0;
    const q = async (sql, params) => {
      calls += 1;
      if (calls === 2) throw new Error('relation does not exist');
      return { rows: [] };
    };

    const { data, failures } = await collectUserData(q, 7);

    assert.equal(failures.length, 1, 'the failing source was not reported');
    assert.ok(Object.keys(data).length > 1, 'export aborted rather than continuing');
    // Silently omitting the table would understate what is held about the subject.
    assert.ok(failures[0].source, 'failure did not name the source');
  });
});

describe('Global Privacy Control', () => {
  it('recognises only the affirmative signal', () => {
    assert.equal(hasGlobalPrivacyControl({ headers: { 'sec-gpc': '1' } }), true);
    assert.equal(hasGlobalPrivacyControl({ headers: { 'sec-gpc': '0' } }), false);
    assert.equal(hasGlobalPrivacyControl({ headers: {} }), false);
    assert.equal(hasGlobalPrivacyControl({}), false);
    assert.equal(hasGlobalPrivacyControl(undefined), false);
  });

  it('forces the opt-out and disables sharing when signalled', () => {
    const { preferences, applied } = applyGlobalPrivacyControl(
      { headers: { 'sec-gpc': '1' } },
      { necessary: true, functional: true, analytics: true, marketing: true, doNotSell: false },
    );

    assert.equal(applied, true);
    assert.equal(preferences.doNotSell, true);
    // Honouring the opt-out while leaving marketing on would be an opt-out in name only.
    assert.equal(preferences.marketing, false);
    // Unrelated categories are the user's own choice and stay untouched.
    assert.equal(preferences.analytics, true);
    assert.equal(preferences.functional, true);
  });

  it('treats an absent signal as "not opted out by this mechanism", never as opt-in', () => {
    const original = { marketing: true, doNotSell: true };
    const { preferences, applied } = applyGlobalPrivacyControl({ headers: {} }, original);

    assert.equal(applied, false);
    // A missing header must not reset a user who opted out some other way.
    assert.equal(preferences.doNotSell, true);
    assert.equal(preferences.marketing, true);
  });

  it('overrides a form that asked to keep sharing on', () => {
    // A stale form rendered before GPC was enabled must not defeat the signal.
    const { preferences } = applyGlobalPrivacyControl(
      { headers: { 'sec-gpc': '1' } },
      { doNotSell: false, marketing: true },
    );

    assert.equal(preferences.doNotSell, true);
    assert.equal(preferences.marketing, false);
  });
});
