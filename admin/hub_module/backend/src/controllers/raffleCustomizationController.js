/**
 * Raffle Customization Controller
 * Manages custom sounds and messages for community raffles and giveaways.
 * Supports per-event-type configuration with file upload to local filesystem.
 */
import fs from 'fs';
import path from 'path';
import { db } from '../db/index.js';
import { logger } from '../utils/logger.js';

const VALID_EVENT_TYPES = [
  'raffle_start',
  'raffle_winner',
  'raffle_end',
  'giveaway_start',
  'giveaway_winner',
  'giveaway_end',
];

const VALID_FORMATS = ['mp3', 'ogg', 'wav'];
const MAX_FILE_SIZE = 2 * 1024 * 1024; // 2MB
const UPLOAD_BASE_DIR = process.env.UPLOAD_DIR || '/app/uploads/raffle-sounds';

/**
 * GET /:communityId/raffle-customization
 * Returns all custom sounds/messages for a community, keyed by event_type.
 */
export async function getRaffleCustomization(req, res) {
  const { communityId } = req.params;

  try {
    const result = await db.query(
      `SELECT id, community_id, event_type, sound_url, sound_filename,
              sound_size_bytes, sound_format, message_template, is_active,
              created_at, updated_at
       FROM community_raffle_sounds
       WHERE community_id = $1
       ORDER BY event_type`,
      [communityId]
    );

    // Build a map of event_type -> config for easy frontend consumption
    const customizations = {};
    for (const row of result.rows) {
      customizations[row.event_type] = row;
    }

    return res.json({
      success: true,
      customizations,
    });
  } catch (err) {
    logger.error({ err, communityId }, 'Failed to fetch raffle customization');
    return res.status(500).json({
      success: false,
      error: { message: 'Failed to fetch raffle customization' },
    });
  }
}

/**
 * PUT /:communityId/raffle-customization/:eventType
 * Upsert message_template and/or is_active for an event type.
 * Sound upload is handled separately via the /upload endpoint.
 */
export async function upsertRaffleCustomization(req, res) {
  const { communityId, eventType } = req.params;

  if (!VALID_EVENT_TYPES.includes(eventType)) {
    return res.status(400).json({
      success: false,
      error: { message: `Invalid event type. Must be one of: ${VALID_EVENT_TYPES.join(', ')}` },
    });
  }

  const { message_template, is_active } = req.body;

  try {
    const result = await db.query(
      `INSERT INTO community_raffle_sounds (community_id, event_type, message_template, is_active, updated_at)
       VALUES ($1, $2, $3, $4, NOW())
       ON CONFLICT (community_id, event_type) DO UPDATE SET
         message_template = COALESCE(EXCLUDED.message_template, community_raffle_sounds.message_template),
         is_active = COALESCE(EXCLUDED.is_active, community_raffle_sounds.is_active),
         updated_at = NOW()
       RETURNING *`,
      [communityId, eventType, message_template ?? null, is_active ?? true]
    );

    return res.json({
      success: true,
      customization: result.rows[0],
    });
  } catch (err) {
    logger.error({ err, communityId, eventType }, 'Failed to upsert raffle customization');
    return res.status(500).json({
      success: false,
      error: { message: 'Failed to save raffle customization' },
    });
  }
}

/**
 * DELETE /:communityId/raffle-customization/:eventType
 * Reset event type to defaults — removes the row (and uploaded sound file if present).
 */
export async function deleteRaffleCustomization(req, res) {
  const { communityId, eventType } = req.params;

  if (!VALID_EVENT_TYPES.includes(eventType)) {
    return res.status(400).json({
      success: false,
      error: { message: `Invalid event type. Must be one of: ${VALID_EVENT_TYPES.join(', ')}` },
    });
  }

  try {
    const result = await db.query(
      `DELETE FROM community_raffle_sounds
       WHERE community_id = $1 AND event_type = $2
       RETURNING sound_filename`,
      [communityId, eventType]
    );

    // Clean up uploaded sound file if one existed
    if (result.rows.length > 0 && result.rows[0].sound_filename) {
      const filePath = path.join(UPLOAD_BASE_DIR, String(communityId), result.rows[0].sound_filename);
      try {
        fs.unlinkSync(filePath);
      } catch (fsErr) {
        // Non-fatal — log and continue
        logger.warn({ fsErr, filePath }, 'Could not delete sound file during reset');
      }
    }

    return res.json({ success: true });
  } catch (err) {
    logger.error({ err, communityId, eventType }, 'Failed to delete raffle customization');
    return res.status(500).json({
      success: false,
      error: { message: 'Failed to reset raffle customization' },
    });
  }
}

/**
 * POST /:communityId/raffle-customization/:eventType/upload
 * Upload a sound file for an event type.
 * Validates format (mp3/ogg/wav) and size (max 2MB).
 * Stores file to /app/uploads/raffle-sounds/{communityId}/.
 */
export async function uploadRaffleSound(req, res) {
  const { communityId, eventType } = req.params;

  if (!VALID_EVENT_TYPES.includes(eventType)) {
    return res.status(400).json({
      success: false,
      error: { message: `Invalid event type. Must be one of: ${VALID_EVENT_TYPES.join(', ')}` },
    });
  }

  if (!req.file) {
    return res.status(400).json({
      success: false,
      error: { message: 'No file uploaded' },
    });
  }

  const { originalname, size, buffer } = req.file;

  // Validate file size
  if (size > MAX_FILE_SIZE) {
    return res.status(400).json({
      success: false,
      error: { message: 'File exceeds 2MB limit' },
    });
  }

  // Validate file format by extension
  const ext = path.extname(originalname).toLowerCase().replace('.', '');
  if (!VALID_FORMATS.includes(ext)) {
    return res.status(400).json({
      success: false,
      error: { message: `Invalid file format. Must be one of: ${VALID_FORMATS.join(', ')}` },
    });
  }

  // Build target directory and filename
  const communityDir = path.join(UPLOAD_BASE_DIR, String(communityId));
  const timestamp = Date.now();
  const safeFilename = `${eventType}_${timestamp}.${ext}`;
  const destPath = path.join(communityDir, safeFilename);

  try {
    // Ensure upload directory exists
    fs.mkdirSync(communityDir, { recursive: true });

    // Remove existing sound file for this event type if present (avoid orphaned files)
    const existing = await db.query(
      `SELECT sound_filename FROM community_raffle_sounds
       WHERE community_id = $1 AND event_type = $2`,
      [communityId, eventType]
    );
    if (existing.rows.length > 0 && existing.rows[0].sound_filename) {
      const oldPath = path.join(communityDir, existing.rows[0].sound_filename);
      try {
        fs.unlinkSync(oldPath);
      } catch (_) {
        // Non-fatal
      }
    }

    // Write file to disk
    fs.writeFileSync(destPath, buffer);

    // Persist metadata in DB (upsert)
    // sound_url is a relative path; absolute URL generation handled by the serving layer
    const soundUrl = `/uploads/raffle-sounds/${communityId}/${safeFilename}`;
    const result = await db.query(
      `INSERT INTO community_raffle_sounds
         (community_id, event_type, sound_url, sound_filename, sound_size_bytes, sound_format, is_active, updated_at)
       VALUES ($1, $2, $3, $4, $5, $6, true, NOW())
       ON CONFLICT (community_id, event_type) DO UPDATE SET
         sound_url = EXCLUDED.sound_url,
         sound_filename = EXCLUDED.sound_filename,
         sound_size_bytes = EXCLUDED.sound_size_bytes,
         sound_format = EXCLUDED.sound_format,
         is_active = true,
         updated_at = NOW()
       RETURNING *`,
      [communityId, eventType, soundUrl, safeFilename, size, ext]
    );

    return res.json({
      success: true,
      customization: result.rows[0],
    });
  } catch (err) {
    // Clean up partially written file
    try { fs.unlinkSync(destPath); } catch (_) { /* ignore */ }
    logger.error({ err, communityId, eventType }, 'Failed to upload raffle sound');
    return res.status(500).json({
      success: false,
      error: { message: 'Failed to upload sound file' },
    });
  }
}
