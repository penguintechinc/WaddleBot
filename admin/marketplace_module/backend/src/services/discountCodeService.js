/**
 * Discount Code Service — vendor discount code management and redemption
 */
import { query, transaction } from '../config/database.js';
import { logger } from '../utils/logger.js';
import { errors } from '../middleware/errorHandler.js';

const VALID_DISCOUNT_TYPES = ['percentage', 'fixed_cents'];

/**
 * Lists discount codes owned by a vendor with pagination and optional status filter.
 * @param {number} userId
 * @param {{ page?: number, limit?: number, status?: string }} options
 */
export async function getVendorDiscountCodes(userId, { page = 1, limit = 20, status = 'all' } = {}) {
  const offset = (page - 1) * limit;

  let statusClause = '';
  const params = [userId, limit, offset];

  if (status === 'active') {
    statusClause = `
      AND dc.is_active = true
      AND (dc.valid_from IS NULL OR dc.valid_from <= NOW())
      AND (dc.valid_until IS NULL OR dc.valid_until >= NOW())
      AND (dc.max_uses IS NULL OR dc.current_uses < dc.max_uses)
    `;
  } else if (status === 'expired') {
    statusClause = `
      AND (
        dc.is_active = false
        OR (dc.valid_until IS NOT NULL AND dc.valid_until < NOW())
        OR (dc.max_uses IS NOT NULL AND dc.current_uses >= dc.max_uses)
      )
    `;
  }

  const [codesResult, countResult] = await Promise.all([
    query(
      `SELECT dc.*
         FROM marketplace_discount_codes dc
         JOIN marketplace_sellers ms ON ms.id = dc.seller_id
        WHERE ms.user_id = $1
          ${statusClause}
        ORDER BY dc.created_at DESC
        LIMIT $2 OFFSET $3`,
      params
    ),
    query(
      `SELECT COUNT(*) AS total
         FROM marketplace_discount_codes dc
         JOIN marketplace_sellers ms ON ms.id = dc.seller_id
        WHERE ms.user_id = $1
          ${statusClause}`,
      [userId]
    ),
  ]);

  return {
    discountCodes: codesResult.rows,
    pagination: {
      page,
      limit,
      total: parseInt(countResult.rows[0].total, 10),
    },
  };
}

/**
 * Creates a new discount code for a vendor.
 * Code is auto-uppercased. Uniqueness is enforced per vendor.
 * @param {number} userId
 * @param {object} codeData
 */
export async function createDiscountCode(userId, codeData) {
  const {
    code,
    discountType,
    discountValue,
    moduleId = null,
    validFrom = null,
    validUntil = null,
    maxUses = null,
    description = null,
  } = codeData;

  if (!code || typeof code !== 'string' || code.trim() === '') {
    throw errors.validation('code is required');
  }
  if (!VALID_DISCOUNT_TYPES.includes(discountType)) {
    throw errors.validation(`discountType must be one of: ${VALID_DISCOUNT_TYPES.join(', ')}`);
  }
  if (discountValue === undefined || discountValue === null) {
    throw errors.validation('discountValue is required');
  }
  if (typeof discountValue !== 'number' || discountValue <= 0) {
    throw errors.validation('discountValue must be a positive number');
  }
  if (discountType === 'percentage' && discountValue > 100) {
    throw errors.validation('discountValue cannot exceed 100 for percentage discounts');
  }

  const upperCode = code.trim().toUpperCase();

  const sellerResult = await query(
    `SELECT id FROM marketplace_sellers WHERE user_id = $1 LIMIT 1`,
    [userId]
  );
  if (!sellerResult.rows[0]) {
    throw errors.notFound('Vendor profile not found');
  }
  const sellerId = sellerResult.rows[0].id;

  let result;
  try {
    result = await query(
      `INSERT INTO marketplace_discount_codes
         (seller_id, module_id, code, discount_type, discount_value,
          valid_from, valid_until, max_uses, current_uses, is_active, description,
          created_at, updated_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 0, true, $9, NOW(), NOW())
       RETURNING *`,
      [sellerId, moduleId, upperCode, discountType, discountValue,
       validFrom, validUntil, maxUses, description]
    );
  } catch (err) {
    if (err.code === '23505') {
      throw errors.conflict('A discount code with that value already exists for this vendor');
    }
    throw err;
  }

  return result.rows[0];
}

/**
 * Partially updates a discount code, verifying ownership.
 * @param {number} userId
 * @param {number} codeId
 * @param {object} updates
 */
export async function updateDiscountCode(userId, codeId, updates) {
  const existing = await _getOwnedCode(userId, codeId);

  const allowed = ['discount_type', 'discount_value', 'valid_from', 'valid_until',
                   'max_uses', 'is_active', 'description', 'module_id'];
  const setClauses = [];
  const params = [];
  let idx = 1;

  // Map camelCase inputs to snake_case columns
  const fieldMap = {
    discountType: 'discount_type',
    discountValue: 'discount_value',
    validFrom: 'valid_from',
    validUntil: 'valid_until',
    maxUses: 'max_uses',
    isActive: 'is_active',
    description: 'description',
    moduleId: 'module_id',
  };

  for (const [camel, col] of Object.entries(fieldMap)) {
    if (camel in updates) {
      if (!allowed.includes(col)) continue;
      setClauses.push(`${col} = $${idx}`);
      params.push(updates[camel]);
      idx++;
    }
  }

  // Validate updated discountType/discountValue if provided
  const newType = updates.discountType || existing.discount_type;
  const newValue = updates.discountValue !== undefined ? updates.discountValue : existing.discount_value;

  if (!VALID_DISCOUNT_TYPES.includes(newType)) {
    throw errors.validation(`discountType must be one of: ${VALID_DISCOUNT_TYPES.join(', ')}`);
  }
  if (typeof newValue !== 'number' || newValue <= 0) {
    throw errors.validation('discountValue must be a positive number');
  }
  if (newType === 'percentage' && newValue > 100) {
    throw errors.validation('discountValue cannot exceed 100 for percentage discounts');
  }

  if (setClauses.length === 0) {
    return existing;
  }

  setClauses.push(`updated_at = NOW()`);
  params.push(codeId);

  const result = await query(
    `UPDATE marketplace_discount_codes
        SET ${setClauses.join(', ')}
      WHERE id = $${idx}
      RETURNING *`,
    params
  );

  return result.rows[0];
}

/**
 * Soft-deletes a discount code (sets is_active=false), verifying ownership.
 * @param {number} userId
 * @param {number} codeId
 */
export async function deleteDiscountCode(userId, codeId) {
  await _getOwnedCode(userId, codeId);

  const result = await query(
    `UPDATE marketplace_discount_codes
        SET is_active = false, updated_at = NOW()
      WHERE id = $1
      RETURNING *`,
    [codeId]
  );

  return result.rows[0];
}

/**
 * Public validation of a discount code. Checks: active, within dates,
 * under max_uses, and optionally scoped to the correct module.
 * @param {string} code
 * @param {number|null} moduleId
 */
export async function validateDiscountCode(code, moduleId = null) {
  if (!code) {
    throw errors.validation('code is required');
  }

  const result = await query(
    `SELECT dc.*, ms.user_id AS seller_user_id
       FROM marketplace_discount_codes dc
       JOIN marketplace_sellers ms ON ms.id = dc.seller_id
      WHERE dc.code = $1
      LIMIT 1`,
    [code.trim().toUpperCase()]
  );

  const dc = result.rows[0];

  if (!dc) {
    return { valid: false, reason: 'CODE_NOT_FOUND' };
  }
  if (!dc.is_active) {
    return { valid: false, reason: 'CODE_INACTIVE' };
  }
  if (dc.valid_from && new Date(dc.valid_from) > new Date()) {
    return { valid: false, reason: 'CODE_NOT_YET_VALID' };
  }
  if (dc.valid_until && new Date(dc.valid_until) < new Date()) {
    return { valid: false, reason: 'CODE_EXPIRED' };
  }
  if (dc.max_uses !== null && dc.current_uses >= dc.max_uses) {
    return { valid: false, reason: 'CODE_MAX_USES_REACHED' };
  }
  if (dc.module_id !== null && moduleId !== null && dc.module_id !== moduleId) {
    return { valid: false, reason: 'CODE_WRONG_MODULE' };
  }

  return {
    valid: true,
    discountCodeId: dc.id,
    discountType: dc.discount_type,
    discountValue: dc.discount_value,
    sellerId: dc.seller_id,
    moduleId: dc.module_id,
    usesRemaining: dc.max_uses !== null ? dc.max_uses - dc.current_uses : null,
  };
}

/**
 * Atomically increments current_uses and inserts a redemption record.
 * Calculates discounted price based on discount_type and discount_value.
 * @param {number} codeId
 * @param {number} communityId
 * @param {number} subscriptionId
 * @param {number} originalPriceCents
 */
export async function redeemDiscountCode(codeId, communityId, subscriptionId, originalPriceCents) {
  if (!codeId || !communityId || !subscriptionId || originalPriceCents === undefined) {
    throw errors.validation('codeId, communityId, subscriptionId, and originalPriceCents are required');
  }
  if (typeof originalPriceCents !== 'number' || originalPriceCents < 0) {
    throw errors.validation('originalPriceCents must be a non-negative number');
  }

  return await transaction(async (client) => {
    // Lock the row and verify it's still redeemable
    const lockResult = await client.query(
      `SELECT * FROM marketplace_discount_codes
        WHERE id = $1
          AND is_active = true
          AND (valid_from IS NULL OR valid_from <= NOW())
          AND (valid_until IS NULL OR valid_until >= NOW())
          AND (max_uses IS NULL OR current_uses < max_uses)
        FOR UPDATE`,
      [codeId]
    );

    if (!lockResult.rows[0]) {
      throw errors.conflict('Discount code is no longer valid or has reached its usage limit');
    }

    const dc = lockResult.rows[0];

    // Calculate discounted price
    let discountedPriceCents;
    if (dc.discount_type === 'percentage') {
      const discountAmount = Math.round(originalPriceCents * (dc.discount_value / 100));
      discountedPriceCents = Math.max(0, originalPriceCents - discountAmount);
    } else {
      // fixed_cents
      discountedPriceCents = Math.max(0, originalPriceCents - dc.discount_value);
    }

    const savingsCents = originalPriceCents - discountedPriceCents;

    // Increment usage count
    await client.query(
      `UPDATE marketplace_discount_codes
          SET current_uses = current_uses + 1, updated_at = NOW()
        WHERE id = $1`,
      [codeId]
    );

    // Insert redemption record
    const redemptionResult = await client.query(
      `INSERT INTO marketplace_discount_code_redemptions
         (discount_code_id, community_id, subscription_id,
          original_price_cents, discounted_price_cents, savings_cents,
          redeemed_at)
       VALUES ($1, $2, $3, $4, $5, $6, NOW())
       RETURNING *`,
      [codeId, communityId, subscriptionId, originalPriceCents, discountedPriceCents, savingsCents]
    );

    logger.info({ codeId, communityId, subscriptionId, savingsCents }, 'Discount code redeemed');

    return {
      redemption: redemptionResult.rows[0],
      originalPriceCents,
      discountedPriceCents,
      savingsCents,
    };
  });
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Fetches a discount code and verifies the requesting user owns it.
 * Throws 404 if not found or 403 if not owned.
 * @param {number} userId
 * @param {number} codeId
 */
async function _getOwnedCode(userId, codeId) {
  const result = await query(
    `SELECT dc.*
       FROM marketplace_discount_codes dc
       JOIN marketplace_sellers ms ON ms.id = dc.seller_id
      WHERE dc.id = $1
      LIMIT 1`,
    [codeId]
  );

  const dc = result.rows[0];
  if (!dc) {
    throw errors.notFound('Discount code not found');
  }

  // Verify ownership by re-checking with user_id join
  const ownerResult = await query(
    `SELECT dc.id
       FROM marketplace_discount_codes dc
       JOIN marketplace_sellers ms ON ms.id = dc.seller_id
      WHERE dc.id = $1 AND ms.user_id = $2
      LIMIT 1`,
    [codeId, userId]
  );

  if (!ownerResult.rows[0]) {
    throw errors.forbidden('You do not have permission to modify this discount code');
  }

  return dc;
}
