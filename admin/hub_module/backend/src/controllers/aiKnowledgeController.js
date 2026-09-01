/**
 * AI Knowledge Controller
 * Handles CRUD for knowledge sources, manual reindexing, knowledge search,
 * AI-powered ticket suggestion generation, and suggestion feedback.
 */
import logger from '../utils/logger.js';
import {
  addKnowledgeSource,
  listKnowledgeSources,
  updateKnowledgeSource,
  deleteKnowledgeSource,
  indexSource,
  searchKnowledge,
  generateSuggestion,
  recordFeedback,
} from '../services/aiKnowledgeService.js';

// ── Knowledge Source CRUD ─────────────────────────────────────────────────────

/**
 * GET /ai-knowledge/sources
 * List knowledge sources, optionally filtered by ?communityId=
 */
export async function listSources(req, res) {
  try {
    const { communityId } = req.query;
    const sources = await listKnowledgeSources(req.user.id, {
      communityId: communityId ? parseInt(communityId, 10) : undefined,
    });
    return res.json({ success: true, sources });
  } catch (err) {
    logger.error({ err: err.message }, 'Failed to list knowledge sources');
    return res.status(err.status || 500).json({
      success: false,
      error: { message: err.message || 'Failed to list knowledge sources' },
    });
  }
}

/**
 * POST /ai-knowledge/sources
 * Create a new knowledge source and trigger initial indexing.
 */
export async function createSource(req, res) {
  try {
    const source = await addKnowledgeSource(req.user.id, req.body);
    return res.status(201).json({ success: true, source });
  } catch (err) {
    logger.error({ err: err.message }, 'Failed to create knowledge source');
    return res.status(err.status || 500).json({
      success: false,
      error: { message: err.message || 'Failed to create knowledge source' },
    });
  }
}

/**
 * PUT /ai-knowledge/sources/:id
 * Update knowledge source configuration.
 */
export async function updateSource(req, res) {
  try {
    const sourceId = parseInt(req.params.id, 10);
    const source = await updateKnowledgeSource(req.user.id, sourceId, req.body);
    return res.json({ success: true, source });
  } catch (err) {
    logger.error({ err: err.message, sourceId: req.params.id }, 'Failed to update knowledge source');
    return res.status(err.status || 500).json({
      success: false,
      error: { message: err.message || 'Failed to update knowledge source' },
    });
  }
}

/**
 * DELETE /ai-knowledge/sources/:id
 * Delete a knowledge source and cascade its chunks.
 */
export async function deleteSource(req, res) {
  try {
    const sourceId = parseInt(req.params.id, 10);
    await deleteKnowledgeSource(req.user.id, sourceId);
    return res.json({ success: true });
  } catch (err) {
    logger.error({ err: err.message, sourceId: req.params.id }, 'Failed to delete knowledge source');
    return res.status(err.status || 500).json({
      success: false,
      error: { message: err.message || 'Failed to delete knowledge source' },
    });
  }
}

// ── Indexing ──────────────────────────────────────────────────────────────────

/**
 * POST /ai-knowledge/sources/:id/reindex
 * Trigger a manual reindex of a knowledge source.
 * Responds immediately; indexing runs asynchronously.
 */
export async function reindexSource(req, res) {
  const sourceId = parseInt(req.params.id, 10);

  // Respond immediately — indexing is async
  res.json({ success: true, message: 'Reindex started', sourceId });

  indexSource(sourceId).catch(err => {
    logger.error({ sourceId, err: err.message }, 'Manual reindex failed');
  });
}

// ── Search ────────────────────────────────────────────────────────────────────

/**
 * POST /ai-knowledge/search
 * Perform vector similarity search against the knowledge base.
 * Body: { query, communityId?, vendorId?, topK? }
 */
export async function searchKnowledgeBase(req, res) {
  try {
    const { query: queryText, communityId, vendorId, topK } = req.body;

    if (!queryText || !String(queryText).trim()) {
      return res.status(400).json({
        success: false,
        error: { message: 'query is required' },
      });
    }

    const results = await searchKnowledge(String(queryText), {
      communityId: communityId ? parseInt(communityId, 10) : undefined,
      vendorId: vendorId ? parseInt(vendorId, 10) : undefined,
      topK: topK ? parseInt(topK, 10) : undefined,
    });

    return res.json({ success: true, results });
  } catch (err) {
    logger.error({ err: err.message }, 'Knowledge search failed');
    return res.status(err.status || 500).json({
      success: false,
      error: { message: err.message || 'Knowledge search failed' },
    });
  }
}

// ── Suggestions ───────────────────────────────────────────────────────────────

/**
 * POST /ai-knowledge/suggest
 * Generate an AI suggestion for a support ticket.
 * Body: { ticketId, ticketText, communityId? }
 */
export async function suggestForTicket(req, res) {
  try {
    const { ticketId, ticketText, communityId } = req.body;

    if (!ticketId || !ticketText || !String(ticketText).trim()) {
      return res.status(400).json({
        success: false,
        error: { message: 'ticketId and ticketText are required' },
      });
    }

    const suggestion = await generateSuggestion(
      parseInt(ticketId, 10),
      String(ticketText).trim(),
      { communityId: communityId ? parseInt(communityId, 10) : undefined }
    );

    if (!suggestion) {
      return res.json({
        success: true,
        suggestion: null,
        message: 'No suggestion generated — knowledge base confidence below threshold',
      });
    }

    return res.status(201).json({ success: true, suggestion });
  } catch (err) {
    logger.error({ err: err.message }, 'Suggestion generation failed');
    return res.status(err.status || 500).json({
      success: false,
      error: { message: err.message || 'Suggestion generation failed' },
    });
  }
}

/**
 * POST /ai-knowledge/suggestions/:id/feedback
 * Record helpfulness feedback for a suggestion.
 * Body: { feedback: 'helpful' | 'not_helpful' }
 */
export async function submitFeedback(req, res) {
  try {
    const suggestionId = parseInt(req.params.id, 10);
    const { feedback } = req.body;

    if (!feedback) {
      return res.status(400).json({
        success: false,
        error: { message: 'feedback is required' },
      });
    }

    const updated = await recordFeedback(suggestionId, feedback);
    return res.json({ success: true, suggestion: updated });
  } catch (err) {
    logger.error({ err: err.message, suggestionId: req.params.id }, 'Failed to record suggestion feedback');
    return res.status(err.status || 500).json({
      success: false,
      error: { message: err.message || 'Failed to record feedback' },
    });
  }
}
