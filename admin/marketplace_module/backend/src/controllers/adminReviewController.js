import { query, transaction } from '../config/database.js';
import { logger } from '../utils/logger.js';
import { errors } from '../middleware/errorHandler.js';

export async function getVendorRequests(req, res, next) {
  try {
    const { status } = req.query;
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 25;
    const offset = (page - 1) * limit;

    const params = [];
    let whereClause = '';

    if (status) {
      params.push(status);
      whereClause = 'WHERE vrr.status = $1';
    }

    const dataParams = [...params, limit, offset];
    const limitIdx = params.length + 1;
    const offsetIdx = params.length + 2;

    const { rows: requests } = await query(
      `SELECT vrr.*, hu.username, hu.email
       FROM vendor_role_requests vrr
       LEFT JOIN hub_users hu ON hu.id = vrr.user_id
       ${whereClause}
       ORDER BY vrr.created_at DESC
       LIMIT $${limitIdx} OFFSET $${offsetIdx}`,
      dataParams
    );

    const { rows: countRows } = await query(
      `SELECT COUNT(*) AS total FROM vendor_role_requests vrr ${whereClause}`,
      params
    );

    const total = parseInt(countRows[0].total);

    return res.json({
      success: true,
      requests,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    });
  } catch (err) {
    next(err);
  }
}

export async function approveVendorRequest(req, res, next) {
  try {
    const { id } = req.params;
    const { notes } = req.body;
    const reviewedBy = req.user.id;

    const { rows } = await query(
      `UPDATE vendor_role_requests
       SET status='approved', reviewed_by=$1, reviewed_at=NOW(), admin_notes=$2
       WHERE id=$3
       RETURNING user_id`,
      [reviewedBy, notes, id]
    );

    if (rows.length > 0 && rows[0].user_id) {
      const userId = rows[0].user_id;
      await query(
        `INSERT INTO marketplace_sellers (user_id, is_verified, verified_at, created_at, updated_at)
         VALUES ($1, true, NOW(), NOW(), NOW())
         ON CONFLICT (user_id) DO UPDATE SET is_verified=true, verified_at=NOW()`,
        [userId]
      );
    }

    logger.audit('Vendor request approved', {
      requestId: id,
      reviewedBy,
      notes,
    });

    return res.json({ success: true, message: 'Vendor request approved' });
  } catch (err) {
    next(err);
  }
}

export async function rejectVendorRequest(req, res, next) {
  try {
    const { id } = req.params;
    const { reason, notes } = req.body;
    const reviewedBy = req.user.id;

    await query(
      `UPDATE vendor_role_requests
       SET status='rejected', rejection_reason=$1, admin_notes=$2, reviewed_by=$3, reviewed_at=NOW()
       WHERE id=$4`,
      [reason, notes, reviewedBy, id]
    );

    return res.json({ success: true, message: 'Vendor request rejected' });
  } catch (err) {
    next(err);
  }
}

export async function getSubmissions(req, res, next) {
  try {
    const { status } = req.query;
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 25;
    const offset = (page - 1) * limit;

    const params = [];
    let whereClause = '';

    if (status) {
      params.push(status);
      whereClause = 'WHERE ms.status = $1';
    }

    const limitIdx = params.length + 1;
    const offsetIdx = params.length + 2;

    const { rows: submissions } = await query(
      `SELECT ms.*, mm.name AS module_name, mm.category, hu.username AS submitter_username
       FROM marketplace_submissions ms
       JOIN marketplace_modules mm ON mm.id = ms.module_id
       LEFT JOIN hub_users hu ON hu.id = ms.submitted_by
       ${whereClause}
       ORDER BY ms.submitted_at DESC
       LIMIT $${limitIdx} OFFSET $${offsetIdx}`,
      [...params, limit, offset]
    );

    const { rows: countRows } = await query(
      `SELECT COUNT(*) AS total FROM marketplace_submissions ms ${whereClause}`,
      params
    );

    const total = parseInt(countRows[0].total);

    return res.json({
      success: true,
      submissions,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    });
  } catch (err) {
    next(err);
  }
}

export async function approveSubmission(req, res, next) {
  try {
    const { id } = req.params;
    const { notes } = req.body;
    const reviewedBy = req.user.id;

    const { rows } = await query(
      `SELECT module_id FROM marketplace_submissions WHERE id=$1`,
      [id]
    );

    if (rows.length === 0) {
      return next(errors.notFound('Submission not found'));
    }

    const moduleId = rows[0].module_id;

    await query(
      `UPDATE marketplace_submissions
       SET status='approved', reviewed_by=$1, reviewed_at=NOW(), review_notes=$2
       WHERE id=$3`,
      [reviewedBy, notes, id]
    );

    await query(
      `UPDATE marketplace_modules
       SET status='approved', approved_by=$1, approved_at=NOW(), updated_at=NOW()
       WHERE id=$2`,
      [reviewedBy, moduleId]
    );

    logger.audit('Submission approved', {
      submissionId: id,
      moduleId,
      reviewedBy,
      notes,
    });

    return res.json({ success: true, message: 'Submission approved' });
  } catch (err) {
    next(err);
  }
}

export async function rejectSubmission(req, res, next) {
  try {
    const { id } = req.params;
    const { reason, notes } = req.body;
    const reviewedBy = req.user.id;

    const { rows } = await query(
      `SELECT module_id FROM marketplace_submissions WHERE id=$1`,
      [id]
    );

    if (rows.length === 0) {
      return next(errors.notFound('Submission not found'));
    }

    const moduleId = rows[0].module_id;

    await query(
      `UPDATE marketplace_submissions
       SET status='rejected', reviewed_by=$1, reviewed_at=NOW(), review_notes=$2
       WHERE id=$3`,
      [reviewedBy, notes, id]
    );

    await query(
      `UPDATE marketplace_modules
       SET status='rejected', rejection_reason=$1, updated_at=NOW()
       WHERE id=$2`,
      [reason, moduleId]
    );

    return res.json({ success: true });
  } catch (err) {
    next(err);
  }
}

export async function getMarketplaceSettings(req, res, next) {
  try {
    const { rows } = await query(
      `SELECT setting_key, setting_value FROM marketplace_settings ORDER BY setting_key`
    );

    return res.json({
      success: true,
      settings: Object.fromEntries(rows.map((r) => [r.setting_key, r.setting_value])),
    });
  } catch (err) {
    next(err);
  }
}

export async function updateMarketplaceSettings(req, res, next) {
  try {
    const { settings } = req.body;
    const updatedBy = req.user.id;

    for (const [key, value] of Object.entries(settings)) {
      await query(
        `INSERT INTO marketplace_settings (setting_key, setting_value, updated_by, updated_at)
         VALUES ($1, $2, $3, NOW())
         ON CONFLICT (setting_key) DO UPDATE
           SET setting_value=EXCLUDED.setting_value,
               updated_by=EXCLUDED.updated_by,
               updated_at=NOW()`,
        [key, value, updatedBy]
      );
    }

    return res.json({ success: true, message: 'Settings updated' });
  } catch (err) {
    next(err);
  }
}
