/**
 * Regression tests for the first-run admin bootstrap (CWE-798 / OWASP A07).
 *
 * A prior version of this codebase planted a super-admin with a static,
 * publicly-known password ('admin123') on every fresh boot, with no env
 * gate. These tests prove the replacement is fail-closed: no env vars set
 * -> no admin created; env vars set -> exactly one admin created; a second
 * boot does not duplicate it.
 *
 * Run with the repo's configured runner: `npm test` (node --test).
 */
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import bcrypt from 'bcrypt';

import { bootstrapInitialAdmin } from './adminBootstrap.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

const OLD_DEFAULT_EMAIL = 'admin@localhost.local';
const OLD_DEFAULT_PASSWORD = 'admin123';
const OLD_STATIC_HASH = '$2b$12$4bHCtATjQNY//n42FMy/P.Uieygqwj.Hh5FbuPJJweqXcZbaTSK0u';

/** Records every SQL statement and answers from a scripted table of rows. */
function fakeDb({ superAdminExists = false, emailTaken = false } = {}) {
  const statements = [];
  const fn = async (sql, params = []) => {
    statements.push({ sql, params });
    if (/SELECT id FROM hub_users WHERE is_super_admin/.test(sql)) {
      return { rows: superAdminExists ? [{ id: 1 }] : [] };
    }
    if (/^\s*INSERT INTO hub_users/.test(sql)) {
      if (emailTaken) {
        return { rows: [] }; // ON CONFLICT DO NOTHING -> no row returned
      }
      return { rows: [{ id: 42 }] };
    }
    if (/SELECT id FROM communities/.test(sql)) {
      return { rows: [] }; // no global community configured in these tests
    }
    return { rows: [] };
  };
  fn.statements = statements;
  return fn;
}

describe('bootstrapInitialAdmin (fail-closed, env-driven)', () => {
  it('creates NO admin when INITIAL_ADMIN_EMAIL/PASSWORD are unset', async () => {
    const db = fakeDb();
    const result = await bootstrapInitialAdmin(db, {});

    assert.equal(result.created, false);
    assert.equal(result.reason, 'env_not_set');

    const inserts = db.statements.filter((s) => /^\s*INSERT INTO hub_users/.test(s.sql));
    assert.equal(inserts.length, 0, 'no admin row should be inserted without env vars');
  });

  it('creates NO admin when only one of the two env vars is set', async () => {
    const db = fakeDb();
    const emailOnly = await bootstrapInitialAdmin(db, { INITIAL_ADMIN_EMAIL: 'a@b.com' });
    const passwordOnly = await bootstrapInitialAdmin(db, { INITIAL_ADMIN_PASSWORD: 'x' });

    assert.equal(emailOnly.created, false);
    assert.equal(passwordOnly.created, false);
    assert.equal(db.statements.filter((s) => /^\s*INSERT INTO hub_users/.test(s.sql)).length, 0);
  });

  it('creates exactly one admin from env vars when none exists yet, with a fresh bcrypt hash', async () => {
    const db = fakeDb({ superAdminExists: false });
    const env = { INITIAL_ADMIN_EMAIL: 'owner@example.com', INITIAL_ADMIN_PASSWORD: 'Correct-Horse-Battery-42!' };

    const result = await bootstrapInitialAdmin(db, env);

    assert.equal(result.created, true);
    assert.equal(result.adminId, 42);

    const inserts = db.statements.filter((s) => /^\s*INSERT INTO hub_users/.test(s.sql));
    assert.equal(inserts.length, 1, 'exactly one admin row must be inserted');

    const [email, username, passwordHash] = inserts[0].params;
    assert.equal(email, env.INITIAL_ADMIN_EMAIL);
    assert.equal(username, env.INITIAL_ADMIN_EMAIL);

    // The hash must not be the old static/known hash, and must actually
    // validate against the supplied password (real bcrypt.hash, not a stub).
    assert.notEqual(passwordHash, OLD_STATIC_HASH);
    assert.ok(await bcrypt.compare(env.INITIAL_ADMIN_PASSWORD, passwordHash));
    assert.ok(!(await bcrypt.compare(OLD_DEFAULT_PASSWORD, passwordHash)));
  });

  it('does NOT duplicate the admin on a second boot (idempotent)', async () => {
    const db = fakeDb({ superAdminExists: true });
    const env = { INITIAL_ADMIN_EMAIL: 'owner@example.com', INITIAL_ADMIN_PASSWORD: 'Correct-Horse-Battery-42!' };

    const result = await bootstrapInitialAdmin(db, env);

    assert.equal(result.created, false);
    assert.equal(result.reason, 'admin_exists');
    assert.equal(db.statements.filter((s) => /^\s*INSERT INTO hub_users/.test(s.sql)).length, 0);
  });

  it('does not silently escalate an existing non-admin account with the same email', async () => {
    const db = fakeDb({ superAdminExists: false, emailTaken: true });
    const env = { INITIAL_ADMIN_EMAIL: 'existing-user@example.com', INITIAL_ADMIN_PASSWORD: 'Correct-Horse-Battery-42!' };

    const result = await bootstrapInitialAdmin(db, env);

    assert.equal(result.created, false);
    assert.equal(result.reason, 'email_conflict');
  });

  it('never uses the old default email/password as a fallback', async () => {
    const db = fakeDb();
    // No env provided at all -- if a fallback default still existed, this
    // would insert OLD_DEFAULT_EMAIL / OLD_DEFAULT_PASSWORD.
    await bootstrapInitialAdmin(db, {});
    const inserts = db.statements.filter((s) => /^\s*INSERT INTO hub_users/.test(s.sql));
    assert.equal(inserts.length, 0);
    assert.ok(
      !inserts.some((s) => s.params?.includes(OLD_DEFAULT_EMAIL)),
      'no insert should ever reference the old default email'
    );
  });
});

describe('source no longer contains the old hardcoded default admin credential', () => {
  const files = [
    join(__dirname, '..', 'index.js'),
    join(__dirname, 'adminBootstrap.js'),
  ];

  for (const file of files) {
    it(`${file.split('/').slice(-2).join('/')} contains no static default credential`, () => {
      const source = readFileSync(file, 'utf8');
      assert.ok(
        !source.includes(OLD_DEFAULT_PASSWORD),
        `${file} still references the old default password literal`
      );
      assert.ok(
        !source.includes(OLD_STATIC_HASH),
        `${file} still references the old static bcrypt hash`
      );
    });
  }

  it('index.js delegates admin creation to the fail-closed bootstrap helper', () => {
    const source = readFileSync(join(__dirname, '..', 'index.js'), 'utf8');
    assert.match(source, /bootstrapInitialAdmin\(query\)/);
  });
});
