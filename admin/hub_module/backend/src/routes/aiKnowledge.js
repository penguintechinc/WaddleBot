/**
 * AI Knowledge Routes
 * Provides endpoints for managing knowledge sources, triggering reindexing,
 * searching the knowledge base, and generating AI-powered ticket suggestions.
 *
 * All routes are mounted under /admin (see routes/index.js).
 * Full paths (relative to /api/v1/admin):
 *   GET    /ai-knowledge/sources               — list knowledge sources
 *   POST   /ai-knowledge/sources               — add a knowledge source
 *   PUT    /ai-knowledge/sources/:id           — update a knowledge source
 *   DELETE /ai-knowledge/sources/:id           — delete a knowledge source
 *   POST   /ai-knowledge/sources/:id/reindex   — trigger manual reindex
 *   POST   /ai-knowledge/search                — vector similarity search
 *   POST   /ai-knowledge/suggest               — generate ticket suggestion
 *   POST   /ai-knowledge/suggestions/:id/feedback — record suggestion feedback
 */
import { Router } from 'express';
import { requireAuth } from '../middleware/auth.js';
import {
  listSources,
  createSource,
  updateSource,
  deleteSource,
  reindexSource,
  searchKnowledgeBase,
  suggestForTicket,
  submitFeedback,
} from '../controllers/aiKnowledgeController.js';

const router = Router();

router.use(requireAuth);

// ── Knowledge Source CRUD ─────────────────────────────────────────────────────
router.get('/ai-knowledge/sources', listSources);
router.post('/ai-knowledge/sources', createSource);
router.put('/ai-knowledge/sources/:id', updateSource);
router.delete('/ai-knowledge/sources/:id', deleteSource);

// ── Manual Reindex ────────────────────────────────────────────────────────────
router.post('/ai-knowledge/sources/:id/reindex', reindexSource);

// ── Search ────────────────────────────────────────────────────────────────────
router.post('/ai-knowledge/search', searchKnowledgeBase);

// ── Suggestions ───────────────────────────────────────────────────────────────
router.post('/ai-knowledge/suggest', suggestForTicket);
router.post('/ai-knowledge/suggestions/:id/feedback', submitFeedback);

export default router;
