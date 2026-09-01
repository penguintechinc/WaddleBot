/**
 * AI Knowledge Service
 * Manages knowledge source indexing, vector chunk storage, similarity search,
 * and AI-generated support ticket suggestions via local Ollama.
 */
import crypto from 'crypto';
import { query, transaction } from '../config/database.js';
import logger from '../utils/logger.js';
import { htmlToText } from '../utils/htmlSanitizer.js';
import { guardedFetch, SSRFError } from '../utils/urlGuard.js';

const OLLAMA_BASE_URL = process.env.OLLAMA_URL || 'http://localhost:11434';
const EMBED_MODEL = process.env.OLLAMA_EMBED_MODEL || 'nomic-embed-text';
const LLM_MODEL = process.env.OLLAMA_LLM_MODEL || 'llama3.2:3b';

/** Tokens per chunk (approximate — 1 token ≈ 4 chars) */
const CHUNK_SIZE_TOKENS = 500;
const CHUNK_OVERLAP_TOKENS = 50;
const CHARS_PER_TOKEN = 4;
const CHUNK_SIZE_CHARS = CHUNK_SIZE_TOKENS * CHARS_PER_TOKEN;
const CHUNK_OVERLAP_CHARS = CHUNK_OVERLAP_TOKENS * CHARS_PER_TOKEN;

/** Minimum confidence score to generate a suggestion */
const SUGGESTION_CONFIDENCE_THRESHOLD = 0.7;

/** Maximum number of knowledge chunks to retrieve per query */
const DEFAULT_TOP_K = 5;

// ── Embedding & LLM helpers ───────────────────────────────────────────────────

/**
 * Generate an embedding vector for a text string via Ollama.
 * @param {string} text
 * @returns {Promise<number[]>}
 */
async function generateEmbedding(text) {
  const response = await fetch(`${OLLAMA_BASE_URL}/api/embeddings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: EMBED_MODEL, prompt: text }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Ollama embeddings error ${response.status}: ${body}`);
  }

  const data = await response.json();
  return data.embedding;
}

/**
 * Generate a completion from Ollama.
 * @param {string} prompt
 * @returns {Promise<string>}
 */
async function generateCompletion(prompt) {
  const response = await fetch(`${OLLAMA_BASE_URL}/api/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: LLM_MODEL, prompt, stream: false }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Ollama generate error ${response.status}: ${body}`);
  }

  const data = await response.json();
  return data.response;
}

// ── Text chunking ─────────────────────────────────────────────────────────────

/**
 * Split text into overlapping chunks of approximately CHUNK_SIZE_CHARS characters.
 * @param {string} text
 * @returns {{ content: string; chunkIndex: number; tokenCount: number }[]}
 */
function chunkText(text) {
  const chunks = [];
  let offset = 0;
  let index = 0;

  while (offset < text.length) {
    const end = Math.min(offset + CHUNK_SIZE_CHARS, text.length);
    const content = text.slice(offset, end).trim();

    if (content.length > 0) {
      chunks.push({
        content,
        chunkIndex: index++,
        tokenCount: Math.ceil(content.length / CHARS_PER_TOKEN),
      });
    }

    if (end === text.length) break;
    offset = end - CHUNK_OVERLAP_CHARS;
  }

  return chunks;
}

// ── Content fetchers ──────────────────────────────────────────────────────────

/**
 * Fetch raw markdown content from a GitHub repo path using the GitHub Contents API.
 * Handles both single files and directory listings (recursively fetches .md files).
 * @param {string} sourceUrl  e.g. "https://github.com/owner/repo" or "owner/repo"
 * @param {string} branch
 * @param {string} docsPath   path within repo, e.g. "/docs"
 * @param {string|null} encryptedToken  PAT (already decrypted by caller) or null
 * @returns {Promise<{ url: string; title: string; content: string }[]>}
 */
async function fetchGitHubMarkdown(sourceUrl, branch, docsPath, token) {
  // Normalise to "owner/repo"
  const match = sourceUrl.match(/github\.com\/([^/]+\/[^/]+)/);
  const repoPath = match ? match[1].replace(/\.git$/, '') : sourceUrl.replace(/^https?:\/\/github\.com\//, '').replace(/\.git$/, '');

  const headers = { Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' };
  if (token) headers.Authorization = `Bearer ${token}`;

  const normalizedPath = docsPath.startsWith('/') ? docsPath.slice(1) : docsPath;
  const contentsUrl = `https://api.github.com/repos/${repoPath}/contents/${normalizedPath}?ref=${branch}`;

  const pages = [];

  async function crawlDirectory(url) {
    // `url` is always an `api.github.com` URL here (either `contentsUrl`,
    // built from a hardcoded host, or `item.url` from GitHub's own API
    // response) -- `guardedFetch` is still applied for defense in depth
    // (matches the Python port's "apply to EVERY fetch, including
    // github" posture) and to re-validate any redirect hop.
    let res;
    try {
      res = await guardedFetch(url, { headers });
    } catch (err) {
      if (err instanceof SSRFError) {
        logger.warn({ url, err: err.message }, 'GitHub fetch blocked by SSRF guard');
        return;
      }
      throw err;
    }
    if (!res.ok) {
      logger.warn({ url, status: res.status }, 'GitHub API non-OK response during crawl');
      return;
    }
    const items = await res.json();

    if (!Array.isArray(items)) {
      // Single file
      if (items.type === 'file' && items.name.endsWith('.md')) {
        const decoded = Buffer.from(items.content, 'base64').toString('utf8');
        pages.push({
          url: items.html_url,
          title: items.name.replace(/\.md$/, '').replace(/-/g, ' '),
          content: decoded,
        });
      }
      return;
    }

    for (const item of items) {
      if (item.type === 'dir') {
        await crawlDirectory(item.url);
      } else if (item.type === 'file' && item.name.endsWith('.md')) {
        let fileRes;
        try {
          fileRes = await guardedFetch(item.url, { headers });
        } catch (err) {
          if (err instanceof SSRFError) {
            logger.warn(
              { url: item.url, err: err.message },
              'GitHub file fetch blocked by SSRF guard'
            );
            continue;
          }
          throw err;
        }
        if (!fileRes.ok) continue;
        const fileData = await fileRes.json();
        const decoded = Buffer.from(fileData.content, 'base64').toString('utf8');
        pages.push({
          url: item.html_url,
          title: item.name.replace(/\.md$/, '').replace(/-/g, ' '),
          content: decoded,
        });
      }
    }
  }

  await crawlDirectory(contentsUrl);
  return pages;
}

/**
 * Fetch documentation pages from a site with sitemap.xml.
 * Crawls sitemap, fetches each page, strips HTML to extract main text content.
 * @param {string} baseUrl
 * @returns {Promise<{ url: string; title: string; content: string }[]>}
 */
async function fetchSitemapPages(baseUrl) {
  const sitemapUrl = baseUrl.replace(/\/$/, '') + '/sitemap.xml';
  const pages = [];
  const crawlerHeaders = { 'User-Agent': 'WaddleBot/2.0 Knowledge Indexer' };

  // `baseUrl` is fully user-supplied (`mkdocs`/`docusaurus`/`generic_url`
  // source types) and the sitemap's `<loc>` entries are attacker-
  // controlled content on that same user-supplied origin -- both the
  // sitemap fetch and every per-page fetch go through `guardedFetch`
  // (SSRF guard + redirect re-validation), not a bare `fetch()`.
  let sitemapRes;
  try {
    sitemapRes = await guardedFetch(sitemapUrl, { headers: crawlerHeaders });
  } catch (err) {
    if (err instanceof SSRFError) {
      logger.warn({ sitemapUrl, err: err.message }, 'Sitemap fetch blocked by SSRF guard');
    } else {
      logger.warn({ sitemapUrl, err: err.message }, 'Could not fetch sitemap');
    }
    return pages;
  }

  if (!sitemapRes.ok) {
    logger.warn({ sitemapUrl, status: sitemapRes.status }, 'Sitemap not found, skipping');
    return pages;
  }

  const xml = await sitemapRes.text();
  const urlMatches = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1].trim());

  for (const pageUrl of urlMatches) {
    try {
      const res = await guardedFetch(pageUrl, { headers: crawlerHeaders });
      if (!res.ok) continue;

      const html = await res.text();

      // Extract <title>
      const titleMatch = html.match(/<title>([^<]+)<\/title>/i);
      const title = titleMatch ? titleMatch[1].trim() : pageUrl;

      // Extract main content: prefer <main> or <article>, fall back to <body>
      const mainMatch = html.match(/<main[^>]*>([\s\S]*?)<\/main>/i)
        || html.match(/<article[^>]*>([\s\S]*?)<\/article>/i)
        || html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);

      if (!mainMatch) continue;

      // Strip HTML tags via a real parser-based sanitizer (not a regex
      // tag filter -- see `htmlToText`'s docstring), then collapse
      // whitespace.
      const text = htmlToText(mainMatch[1]).replace(/\s+/g, ' ').trim();

      if (text.length > 100) {
        pages.push({ url: pageUrl, title, content: text });
      }
    } catch (err) {
      if (err instanceof SSRFError) {
        logger.warn({ pageUrl, err: err.message }, 'Page fetch blocked by SSRF guard');
      } else {
        logger.warn({ pageUrl, err: err.message }, 'Failed to fetch knowledge page');
      }
    }
  }

  return pages;
}

// ── Source management ─────────────────────────────────────────────────────────

/**
 * Add a new knowledge source and trigger an initial index.
 * @param {number} userId
 * @param {object} sourceData
 * @returns {Promise<object>} created source row
 */
export async function addKnowledgeSource(userId, sourceData) {
  const {
    community_id,
    vendor_id,
    module_id,
    source_name,
    source_type,
    source_url,
    branch = 'main',
    docs_path = '/',
    refresh_interval = 'weekly',
    encrypted_token,
  } = sourceData;

  if (!source_name || !source_name.trim()) {
    throw Object.assign(new Error('source_name is required'), { status: 400 });
  }

  const VALID_TYPES = ['github_wiki', 'github_repo_markdown', 'mkdocs', 'docusaurus', 'generic_url', 'manual'];
  if (!VALID_TYPES.includes(source_type)) {
    throw Object.assign(new Error(`source_type must be one of: ${VALID_TYPES.join(', ')}`), { status: 400 });
  }

  const result = await query(
    `INSERT INTO ai_knowledge_sources
       (community_id, vendor_id, module_id, source_name, source_type, source_url,
        branch, docs_path, refresh_interval, encrypted_token, is_active)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, true)
     RETURNING *`,
    [
      community_id || null,
      vendor_id || null,
      module_id || null,
      source_name.trim(),
      source_type,
      source_url || null,
      branch,
      docs_path,
      refresh_interval,
      encrypted_token || null,
    ]
  );

  const source = result.rows[0];

  // Trigger initial index asynchronously — do not await so the API responds quickly
  if (source_type !== 'manual') {
    setImmediate(() => {
      indexSource(source.id).catch(err =>
        logger.error({ sourceId: source.id, err: err.message }, 'Initial index failed')
      );
    });
  }

  return source;
}

/**
 * List knowledge sources, optionally filtered by communityId.
 * @param {number} userId
 * @param {{ communityId?: number }} opts
 * @returns {Promise<object[]>}
 */
export async function listKnowledgeSources(userId, { communityId } = {}) {
  const conditions = [];
  const params = [];

  if (communityId) {
    conditions.push(`community_id = $${params.length + 1}`);
    params.push(communityId);
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

  const result = await query(
    `SELECT id, community_id, vendor_id, module_id, source_name, source_type,
            source_url, branch, docs_path, refresh_interval, is_active,
            last_indexed_at, indexed_page_count, index_errors, created_at, updated_at
     FROM ai_knowledge_sources
     ${where}
     ORDER BY source_name ASC`,
    params
  );

  return result.rows;
}

/**
 * Update knowledge source configuration.
 * @param {number} userId
 * @param {number} sourceId
 * @param {object} updates
 * @returns {Promise<object>} updated source row
 */
export async function updateKnowledgeSource(userId, sourceId, updates) {
  const allowedFields = [
    'source_name', 'source_url', 'branch', 'docs_path',
    'refresh_interval', 'encrypted_token', 'is_active',
  ];

  const fields = [];
  const params = [];

  for (const [key, value] of Object.entries(updates)) {
    if (allowedFields.includes(key)) {
      params.push(value);
      fields.push(`${key} = $${params.length}`);
    }
  }

  if (fields.length === 0) {
    throw Object.assign(new Error('No valid fields provided for update'), { status: 400 });
  }

  params.push(sourceId);
  const result = await query(
    `UPDATE ai_knowledge_sources
     SET ${fields.join(', ')}, updated_at = NOW()
     WHERE id = $${params.length}
     RETURNING *`,
    params
  );

  if (result.rows.length === 0) {
    throw Object.assign(new Error('Knowledge source not found'), { status: 404 });
  }

  return result.rows[0];
}

/**
 * Delete a knowledge source and cascade its chunks.
 * @param {number} userId
 * @param {number} sourceId
 */
export async function deleteKnowledgeSource(userId, sourceId) {
  const result = await query(
    `DELETE FROM ai_knowledge_sources WHERE id = $1 RETURNING id`,
    [sourceId]
  );

  if (result.rows.length === 0) {
    throw Object.assign(new Error('Knowledge source not found'), { status: 404 });
  }
}

// ── Indexing ──────────────────────────────────────────────────────────────────

/**
 * Index a knowledge source: fetch content, chunk it, generate embeddings, upsert chunks.
 * @param {number} sourceId
 */
export async function indexSource(sourceId) {
  const sourceResult = await query(
    `SELECT * FROM ai_knowledge_sources WHERE id = $1`,
    [sourceId]
  );

  if (sourceResult.rows.length === 0) {
    throw new Error(`Knowledge source ${sourceId} not found`);
  }

  const source = sourceResult.rows[0];

  // Mark as indexing in progress
  await query(
    `UPDATE ai_knowledge_sources SET index_errors = NULL, updated_at = NOW() WHERE id = $1`,
    [sourceId]
  );

  let pages = [];

  try {
    switch (source.source_type) {
      case 'github_wiki':
      case 'github_repo_markdown': {
        // encrypted_token is stored encrypted; for now pass raw (encryption handled at storage layer)
        const token = source.encrypted_token || null;
        pages = await fetchGitHubMarkdown(source.source_url, source.branch, source.docs_path, token);
        break;
      }
      case 'mkdocs':
      case 'docusaurus':
      case 'generic_url': {
        pages = await fetchSitemapPages(source.source_url);
        break;
      }
      case 'manual':
        // Manual sources have content inserted directly via the API; nothing to crawl
        logger.info({ sourceId }, 'Manual source — skipping crawl');
        return;
      default:
        throw new Error(`Unknown source_type: ${source.source_type}`);
    }
  } catch (err) {
    await query(
      `UPDATE ai_knowledge_sources
       SET index_errors = $1, updated_at = NOW()
       WHERE id = $2`,
      [err.message, sourceId]
    );
    throw err;
  }

  let totalChunks = 0;
  const errors = [];

  for (const page of pages) {
    const rawChunks = chunkText(page.content);

    for (const chunk of rawChunks) {
      try {
        const contentHash = crypto.createHash('sha256').update(chunk.content).digest('hex');
        const embedding = await generateEmbedding(chunk.content);

        // Format embedding as pgvector literal: [0.1, 0.2, ...]
        const embeddingLiteral = `[${embedding.join(',')}]`;

        await query(
          `INSERT INTO ai_knowledge_chunks
             (source_id, content, content_hash, source_url, source_title, chunk_index, embedding, token_count, updated_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7::vector, $8, NOW())
           ON CONFLICT (source_id, content_hash) DO UPDATE SET
             source_url = EXCLUDED.source_url,
             source_title = EXCLUDED.source_title,
             chunk_index = EXCLUDED.chunk_index,
             embedding = EXCLUDED.embedding,
             token_count = EXCLUDED.token_count,
             updated_at = NOW()`,
          [
            sourceId,
            chunk.content,
            contentHash,
            page.url,
            page.title,
            chunk.chunkIndex,
            embeddingLiteral,
            chunk.tokenCount,
          ]
        );

        totalChunks++;
      } catch (err) {
        errors.push(`${page.url}: ${err.message}`);
        logger.warn({ sourceId, url: page.url, err: err.message }, 'Chunk index error');
      }
    }
  }

  await query(
    `UPDATE ai_knowledge_sources
     SET last_indexed_at = NOW(),
         indexed_page_count = $1,
         index_errors = $2,
         updated_at = NOW()
     WHERE id = $3`,
    [
      pages.length,
      errors.length > 0 ? errors.slice(0, 10).join('\n') : null,
      sourceId,
    ]
  );

  logger.info({ sourceId, pages: pages.length, chunks: totalChunks }, 'Knowledge source indexed');
}

// ── Search & suggestions ──────────────────────────────────────────────────────

/**
 * Search the knowledge base using vector similarity.
 * @param {string} queryText
 * @param {{ communityId?: number; vendorId?: number; topK?: number }} opts
 * @returns {Promise<{ chunk: object; score: number }[]>}
 */
export async function searchKnowledge(queryText, { communityId, vendorId, topK = DEFAULT_TOP_K } = {}) {
  if (!queryText || !queryText.trim()) {
    throw Object.assign(new Error('Query text is required'), { status: 400 });
  }

  const embedding = await generateEmbedding(queryText.trim());
  const embeddingLiteral = `[${embedding.join(',')}]`;

  // Build filter on source scope
  const conditions = [`ks.is_active = true`];
  const params = [embeddingLiteral, topK];

  if (communityId) {
    params.push(communityId);
    conditions.push(`ks.community_id = $${params.length}`);
  }
  if (vendorId) {
    params.push(vendorId);
    conditions.push(`ks.vendor_id = $${params.length}`);
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

  const result = await query(
    `SELECT kc.id, kc.source_id, kc.content, kc.source_url, kc.source_title,
            kc.chunk_index, kc.token_count,
            1 - (kc.embedding <=> $1::vector) AS score
     FROM ai_knowledge_chunks kc
     JOIN ai_knowledge_sources ks ON ks.id = kc.source_id
     ${where}
     ORDER BY kc.embedding <=> $1::vector
     LIMIT $2`,
    params
  );

  return result.rows.map(row => ({
    chunk: {
      id: row.id,
      source_id: row.source_id,
      content: row.content,
      source_url: row.source_url,
      source_title: row.source_title,
      chunk_index: row.chunk_index,
      token_count: row.token_count,
    },
    score: parseFloat(row.score),
  }));
}

/**
 * Generate an AI-powered suggestion for a support ticket.
 * Searches the knowledge base and, if top result exceeds confidence threshold,
 * calls Ollama to compose a suggestion with citations.
 *
 * @param {number} ticketId
 * @param {string} ticketText  the ticket subject + body to answer
 * @param {{ communityId?: number }} opts
 * @returns {Promise<object|null>} inserted ai_ticket_suggestions row, or null if confidence too low
 */
export async function generateSuggestion(ticketId, ticketText, { communityId } = {}) {
  const results = await searchKnowledge(ticketText, { communityId, topK: DEFAULT_TOP_K });

  if (results.length === 0 || results[0].score < SUGGESTION_CONFIDENCE_THRESHOLD) {
    logger.info(
      { ticketId, topScore: results[0]?.score ?? 0 },
      'Knowledge search below threshold — no suggestion generated'
    );
    return null;
  }

  const topChunks = results.filter(r => r.score >= SUGGESTION_CONFIDENCE_THRESHOLD);
  const confidenceScore = topChunks[0].score;

  // Build prompt with relevant knowledge chunks as context
  const context = topChunks
    .map((r, i) => `[${i + 1}] From "${r.chunk.source_title || r.chunk.source_url}":\n${r.chunk.content}`)
    .join('\n\n---\n\n');

  const prompt = [
    'You are a helpful support assistant. Using only the provided knowledge base excerpts, ',
    'write a concise, helpful response to the following support ticket. ',
    'Cite the source numbers (e.g. [1], [2]) inline where relevant. ',
    'If the knowledge base does not contain enough information to answer, say so clearly.\n\n',
    `Support ticket:\n${ticketText}\n\n`,
    `Knowledge base:\n${context}\n\n`,
    'Response:',
  ].join('');

  const suggestionText = await generateCompletion(prompt);
  const citedChunkIds = topChunks.map(r => r.chunk.id);

  const insertResult = await query(
    `INSERT INTO ai_ticket_suggestions
       (ticket_id, suggestion_text, confidence_score, cited_chunks, is_auto_posted)
     VALUES ($1, $2, $3, $4, false)
     RETURNING *`,
    [ticketId, suggestionText.trim(), confidenceScore.toFixed(3), citedChunkIds]
  );

  return insertResult.rows[0];
}

/**
 * Record helpfulness feedback for a suggestion.
 * @param {number} suggestionId
 * @param {'helpful'|'not_helpful'} feedback
 * @returns {Promise<object>} updated row
 */
export async function recordFeedback(suggestionId, feedback) {
  const VALID_FEEDBACK = ['helpful', 'not_helpful'];
  if (!VALID_FEEDBACK.includes(feedback)) {
    throw Object.assign(
      new Error(`feedback must be one of: ${VALID_FEEDBACK.join(', ')}`),
      { status: 400 }
    );
  }

  const result = await query(
    `UPDATE ai_ticket_suggestions
     SET feedback = $1
     WHERE id = $2
     RETURNING *`,
    [feedback, suggestionId]
  );

  if (result.rows.length === 0) {
    throw Object.assign(new Error('Suggestion not found'), { status: 404 });
  }

  return result.rows[0];
}
