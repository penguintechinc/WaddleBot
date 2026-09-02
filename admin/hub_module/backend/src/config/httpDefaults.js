/**
 * Global HTTP client defaults -- security.md DoS hardening fix (missing
 * timeouts).
 *
 * Every one of this backend's ~55 axios calls across controllers/services
 * proxying to internal modules (engagement-core, workflow-core,
 * analytics-core, security-core, server-manager, Identity Core) and
 * external OAuth providers (Discord/Twitch/Slack/Google/Kick) used to have
 * NO timeout, so a single unresponsive downstream could hang the request
 * indefinitely and exhaust the event loop / connection pool under load.
 *
 * axios merges its own `defaults.timeout` with whatever a given call
 * passes -- a per-call `timeout` always wins, but any call that never set
 * one now falls back to this instead of axios's own default of `0` (no
 * timeout at all). Setting it here, on the singleton `axios` module object,
 * covers every caller: a plain `import axios from 'axios'` anywhere in the
 * codebase, a dynamic `(await import('axios')).default` (routes/admin.js),
 * and the generic `axios(config)` call form (workflowController.js) all
 * resolve to this exact same module-cache instance. `axios.create()`
 * instances (aiChatterController.js, analyticsService.js) already set
 * their own explicit timeout and are unaffected either way.
 *
 * Imported for its side effect as the very first statement of
 * src/index.js, so it runs before any downstream controller/service
 * module's own top-level code (including any future axios.create() call
 * that omits its own timeout).
 */
import axios from 'axios';

export const DEFAULT_AXIOS_TIMEOUT_MS = 10000;

axios.defaults.timeout = DEFAULT_AXIOS_TIMEOUT_MS;
