/**
 * Discount Code Controller — vendor discount code CRUD and redemption
 */
import * as discountCodeService from '../services/discountCodeService.js';

/**
 * GET /vendor/discount-codes
 * Lists discount codes for the authenticated vendor with pagination and status filter.
 */
export async function listDiscountCodes(req, res, next) {
  try {
    const page = Math.max(1, parseInt(req.query.page, 10) || 1);
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit, 10) || 20));
    const status = ['active', 'expired', 'all'].includes(req.query.status)
      ? req.query.status
      : 'all';

    const result = await discountCodeService.getVendorDiscountCodes(req.user.id, { page, limit, status });
    res.json({ success: true, data: result });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /vendor/discount-codes
 * Creates a new discount code for the authenticated vendor.
 */
export async function createDiscountCode(req, res, next) {
  try {
    const {
      code,
      discountType,
      discountValue,
      moduleId,
      validFrom,
      validUntil,
      maxUses,
      description,
    } = req.body;

    if (!code || typeof code !== 'string' || code.trim() === '') {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'code is required' },
      });
    }

    if (!discountType) {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'discountType is required' },
      });
    }

    if (discountValue === undefined || discountValue === null) {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'discountValue is required' },
      });
    }

    const parsedValue = Number(discountValue);
    if (isNaN(parsedValue) || parsedValue <= 0) {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'discountValue must be a positive number' },
      });
    }

    if (discountType === 'percentage' && parsedValue > 100) {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'discountValue cannot exceed 100 for percentage discounts' },
      });
    }

    const discountCode = await discountCodeService.createDiscountCode(req.user.id, {
      code,
      discountType,
      discountValue: parsedValue,
      moduleId: moduleId || null,
      validFrom: validFrom || null,
      validUntil: validUntil || null,
      maxUses: maxUses ? parseInt(maxUses, 10) : null,
      description: description || null,
    });

    res.status(201).json({ success: true, data: { discountCode } });
  } catch (err) {
    next(err);
  }
}

/**
 * PUT /vendor/discount-codes/:id
 * Partially updates a discount code owned by the authenticated vendor.
 */
export async function updateDiscountCode(req, res, next) {
  try {
    const codeId = parseInt(req.params.id, 10);
    if (isNaN(codeId)) {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'Invalid discount code ID' },
      });
    }

    const updates = req.body;

    if (updates.discountValue !== undefined) {
      const parsedValue = Number(updates.discountValue);
      if (isNaN(parsedValue) || parsedValue <= 0) {
        return res.status(400).json({
          success: false,
          error: { code: 'VALIDATION_ERROR', message: 'discountValue must be a positive number' },
        });
      }
      updates.discountValue = parsedValue;
    }

    const discountCode = await discountCodeService.updateDiscountCode(req.user.id, codeId, updates);
    res.json({ success: true, data: { discountCode } });
  } catch (err) {
    next(err);
  }
}

/**
 * DELETE /vendor/discount-codes/:id
 * Soft-deletes a discount code (sets is_active=false) owned by the authenticated vendor.
 */
export async function deleteDiscountCode(req, res, next) {
  try {
    const codeId = parseInt(req.params.id, 10);
    if (isNaN(codeId)) {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'Invalid discount code ID' },
      });
    }

    const discountCode = await discountCodeService.deleteDiscountCode(req.user.id, codeId);
    res.json({ success: true, data: { discountCode } });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /vendor/discount-codes/validate
 * Validates a discount code (requires auth). Body: { code, moduleId? }
 */
export async function validateCode(req, res, next) {
  try {
    const { code, moduleId } = req.body;

    if (!code || typeof code !== 'string' || code.trim() === '') {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'code is required' },
      });
    }

    const result = await discountCodeService.validateDiscountCode(
      code,
      moduleId ? parseInt(moduleId, 10) : null
    );

    res.json({ success: true, data: result });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /vendor/discount-codes/redeem
 * Redeems a discount code (internal/admin). Body: { codeId, communityId, subscriptionId, originalPriceCents }
 */
export async function redeemCode(req, res, next) {
  try {
    const { codeId, communityId, subscriptionId, originalPriceCents } = req.body;

    if (!codeId) {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'codeId is required' },
      });
    }
    if (!communityId) {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'communityId is required' },
      });
    }
    if (!subscriptionId) {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'subscriptionId is required' },
      });
    }
    if (originalPriceCents === undefined || originalPriceCents === null) {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'originalPriceCents is required' },
      });
    }

    const parsedPrice = Number(originalPriceCents);
    if (isNaN(parsedPrice) || parsedPrice < 0) {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'originalPriceCents must be a non-negative number' },
      });
    }

    const result = await discountCodeService.redeemDiscountCode(
      parseInt(codeId, 10),
      parseInt(communityId, 10),
      parseInt(subscriptionId, 10),
      parsedPrice
    );

    res.json({ success: true, data: result });
  } catch (err) {
    next(err);
  }
}
