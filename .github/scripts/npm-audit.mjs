import { spawnSync } from 'node:child_process';

const highSeverities = new Set(['high', 'critical']);
const allowedAdvisories = new Set(
  (process.env.NPM_AUDIT_ALLOW ?? '')
    .split(',')
    .map((advisory) => advisory.trim())
    .filter(Boolean),
);

const isWindows = process.platform === 'win32';
const npmCommand = isWindows ? process.env.ComSpec : 'npm';
const npmArguments = isWindows
  ? ['/d', '/s', '/c', 'npm audit --omit=dev --audit-level=high --json']
  : ['audit', '--omit=dev', '--audit-level=high', '--json'];
const audit = spawnSync(
  npmCommand,
  npmArguments,
  {
    encoding: 'utf8',
  },
);

if (audit.error) {
  console.error(`Unable to run npm audit: ${audit.error.message}`);
  process.exit(1);
}

let report;
try {
  report = JSON.parse(audit.stdout);
} catch {
  process.stderr.write(audit.stderr);
  console.error('npm audit did not return valid JSON.');
  process.exit(1);
}

const foundAllowed = new Set();
const blocking = [];

for (const vulnerability of Object.values(report.vulnerabilities ?? {})) {
  for (const advisory of vulnerability.via ?? []) {
    if (typeof advisory === 'string' || !highSeverities.has(advisory.severity)) {
      continue;
    }

    const advisoryId = new URL(advisory.url).pathname.split('/').filter(Boolean).at(-1);
    if (allowedAdvisories.has(advisoryId)) {
      foundAllowed.add(advisoryId);
    } else {
      blocking.push(`${advisoryId}: ${advisory.title}`);
    }
  }
}

const staleAllowances = [...allowedAdvisories].filter(
  (advisoryId) => !foundAllowed.has(advisoryId),
);

if (blocking.length > 0) {
  console.error('Blocking production dependency advisories:');
  blocking.forEach((advisory) => console.error(`- ${advisory}`));
  process.exit(1);
}

if (staleAllowances.length > 0) {
  console.error(`Remove stale npm audit allowances: ${staleAllowances.join(', ')}`);
  process.exit(1);
}

if (foundAllowed.size > 0) {
  console.warn(
    `Temporarily allowed advisories without a patched stable release: ${[...foundAllowed].join(', ')}`,
  );
}

console.log('No unapproved high or critical production dependency advisories found.');
