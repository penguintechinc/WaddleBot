/**
 * Catalog Service — Unified module browsing
 * Queries the marketplace_catalog view (core + vendor modules)
 * with optional per-community install status.
 */
import { query } from '../config/database.js';
import { logger } from '../utils/logger.js';

/**
 * Browse the unified catalog with filters + optional community install status.
 */
export async function getCatalog({
  page = 1,
  limit = 25,
  search = '',
  category = null,
  pricingType = null,
  source = null,
  communityId = null,
}) {
  const offset = (page - 1) * limit;
  const conditions = [];
  const params = [];
  let idx = 1;

  if (search) {
    conditions.push(`(c.name ILIKE $${idx} OR c.display_name ILIKE $${idx} OR c.description ILIKE $${idx})`);
    params.push(`%${search}%`);
    idx++;
  }
  if (category) {
    conditions.push(`c.category = $${idx}`);
    params.push(category);
    idx++;
  }
  if (pricingType) {
    conditions.push(`c.pricing_type = $${idx}`);
    params.push(pricingType);
    idx++;
  }
  if (source) {
    conditions.push(`c.source = $${idx}`);
    params.push(source);
    idx++;
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

  // Total count
  const countResult = await query(
    `SELECT COUNT(*) AS count FROM marketplace_catalog c ${where}`,
    params,
  );
  const total = parseInt(countResult.rows[0]?.count || 0, 10);

  // Build the install-status columns when a community context is present
  let installSelect = '';
  let installJoin = '';

  if (communityId) {
    installSelect = `,
      CASE
        WHEN c.source = 'core' THEN (hi.id IS NOT NULL)
        WHEN c.source = 'marketplace' THEN (ms.id IS NOT NULL)
        ELSE false
      END AS is_installed,
      CASE
        WHEN c.source = 'core' THEN hi.is_enabled
        WHEN c.source = 'marketplace' THEN ms.is_enabled
        ELSE NULL
      END AS is_enabled`;
    installJoin = `
      LEFT JOIN hub_module_installations hi
        ON hi.module_id = c.source_id AND hi.community_id = $${idx} AND c.source = 'core'
      LEFT JOIN marketplace_subscriptions ms
        ON ms.module_id = c.source_id AND ms.community_id = $${idx} AND c.source = 'marketplace'`;
    params.push(communityId);
    idx++;
  }

  const modulesResult = await query(
    `SELECT c.*${installSelect}
     FROM marketplace_catalog c
     ${installJoin}
     ${where}
     ORDER BY c.is_core DESC, c.install_count DESC, c.created_at DESC
     LIMIT $${idx} OFFSET $${idx + 1}`,
    [...params, limit, offset],
  );

  return {
    modules: modulesResult.rows.map(formatCatalogEntry),
    pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
  };
}

/**
 * Get a single catalog entry by source + sourceId.
 */
export async function getCatalogEntry(source, sourceId, communityId = null) {
  let installSelect = '';
  let installJoin = '';
  const params = [source, sourceId];
  let idx = 3;

  if (communityId) {
    installSelect = `,
      CASE
        WHEN c.source = 'core' THEN (hi.id IS NOT NULL)
        WHEN c.source = 'marketplace' THEN (ms.id IS NOT NULL)
        ELSE false
      END AS is_installed,
      CASE
        WHEN c.source = 'core' THEN hi.is_enabled
        WHEN c.source = 'marketplace' THEN ms.is_enabled
        ELSE NULL
      END AS is_enabled`;
    installJoin = `
      LEFT JOIN hub_module_installations hi
        ON hi.module_id = c.source_id AND hi.community_id = $${idx} AND c.source = 'core'
      LEFT JOIN marketplace_subscriptions ms
        ON ms.module_id = c.source_id AND ms.community_id = $${idx} AND c.source = 'marketplace'`;
    params.push(communityId);
    idx++;
  }

  const result = await query(
    `SELECT c.*${installSelect}
     FROM marketplace_catalog c
     ${installJoin}
     WHERE c.source = $1 AND c.source_id = $2
     LIMIT 1`,
    params,
  );

  if (result.rows.length === 0) return null;
  return formatCatalogEntry(result.rows[0]);
}

/**
 * List distinct categories present in the catalog.
 */
export async function getCategories() {
  const result = await query(
    `SELECT DISTINCT category, COUNT(*) AS module_count
     FROM marketplace_catalog
     WHERE category IS NOT NULL
     GROUP BY category
     ORDER BY module_count DESC`,
  );
  return result.rows.map(r => ({ category: r.category, count: parseInt(r.module_count, 10) }));
}

/**
 * Get featured modules (highest install count, limited to 8).
 */
export async function getFeatured(communityId = null) {
  const params = [];
  let idx = 1;
  let installSelect = '';
  let installJoin = '';

  if (communityId) {
    installSelect = `,
      CASE
        WHEN c.source = 'core' THEN (hi.id IS NOT NULL)
        WHEN c.source = 'marketplace' THEN (ms.id IS NOT NULL)
        ELSE false
      END AS is_installed`;
    installJoin = `
      LEFT JOIN hub_module_installations hi
        ON hi.module_id = c.source_id AND hi.community_id = $${idx} AND c.source = 'core'
      LEFT JOIN marketplace_subscriptions ms
        ON ms.module_id = c.source_id AND ms.community_id = $${idx} AND c.source = 'marketplace'`;
    params.push(communityId);
    idx++;
  }

  const result = await query(
    `SELECT c.*${installSelect}
     FROM marketplace_catalog c
     ${installJoin}
     ORDER BY c.install_count DESC, c.avg_rating DESC
     LIMIT 8`,
    params,
  );
  return result.rows.map(formatCatalogEntry);
}

function formatCatalogEntry(row) {
  return {
    source: row.source,
    sourceId: row.source_id,
    name: row.name,
    displayName: row.display_name,
    description: row.description,
    category: row.category,
    iconUrl: row.icon_url,
    isCore: row.is_core,
    pricingType: row.pricing_type,
    priceCents: row.price_cents,
    pricingModel: row.pricing_model,
    version: row.version,
    author: row.author,
    communicationModel: row.communication_model,
    integrationType: row.integration_type,
    avgRating: parseFloat(row.avg_rating || 0).toFixed(1),
    reviewCount: parseInt(row.review_count || 0, 10),
    installCount: parseInt(row.install_count || 0, 10),
    isInstalled: row.is_installed ?? null,
    isEnabled: row.is_enabled ?? null,
    createdAt: row.created_at?.toISOString?.() ?? row.created_at,
    updatedAt: row.updated_at?.toISOString?.() ?? row.updated_at,
  };
}

export default {
  getCatalog,
  getCatalogEntry,
  getCategories,
  getFeatured,
};
