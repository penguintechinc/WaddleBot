/**
 * Hub Module - Express Application Entry Point
 * Unified Community Portal and Admin Interface
 */
// MUST be the first import: sets the global axios.defaults.timeout before
// any downstream module (controllers, services, routes) gets a chance to
// call axios.create() or make a bare axios.get/post call of its own -- see
// that module's docstring for why this closes ~55 previously-unbounded
// outbound HTTP calls in one place.
import './config/httpDefaults.js';
import crypto from 'crypto';
import express from 'express';
import { createServer } from 'http';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import cookieParser from 'cookie-parser';
import path from 'path';
import { fileURLToPath } from 'url';

import { config } from './config/index.js';
import { checkConnection, closePool, query } from './config/database.js';
import { logger } from './utils/logger.js';
import { bootstrapInitialAdmin } from './utils/adminBootstrap.js';
import { errorHandler, notFoundHandler } from './middleware/errorHandler.js';
import { sanitizeBody } from './middleware/validation.js';
import { setCsrfToken, verifyCsrfToken } from './middleware/csrf.js';
import routes from './routes/index.js';
import { setupWebSocket } from './websocket/index.js';

/**
 * Initialize database tables and default admin
 */
async function initializeDatabase() {
  if (process.env.SKIP_DB_INIT === 'true') {
    logger.system('SKIP_DB_INIT=true — skipping Node.js schema creation (Alembic owns schema)');
    return;
  }
  try {
    // Create hub_admins table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS hub_admins (
        id SERIAL PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        email VARCHAR(255),
        is_active BOOLEAN DEFAULT true,
        is_super_admin BOOLEAN DEFAULT false,
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create hub_sessions table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS hub_sessions (
        id SERIAL PRIMARY KEY,
        session_token TEXT NOT NULL,
        user_id INTEGER,
        platform VARCHAR(50),
        platform_user_id VARCHAR(255),
        platform_username VARCHAR(255),
        avatar_url TEXT,
        is_active BOOLEAN DEFAULT true,
        expires_at TIMESTAMP,
        revoked_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create hub_temp_passwords table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS hub_temp_passwords (
        id SERIAL PRIMARY KEY,
        user_identifier VARCHAR(255) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        community_id INTEGER,
        force_oauth_link BOOLEAN DEFAULT false,
        linked_oauth_platform VARCHAR(50),
        linked_oauth_user_id VARCHAR(255),
        is_used BOOLEAN DEFAULT false,
        used_at TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create hub_users table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS hub_users (
        id SERIAL PRIMARY KEY,
        display_name VARCHAR(255),
        username VARCHAR(255) UNIQUE,
        email VARCHAR(255) UNIQUE,
        password_hash VARCHAR(255),
        avatar_url TEXT,
        is_super_admin BOOLEAN DEFAULT false,
        is_vendor BOOLEAN DEFAULT false,
        email_verified BOOLEAN DEFAULT false,
        email_verification_token VARCHAR(255),
        password_reset_token VARCHAR(255),
        password_reset_expires TIMESTAMP,
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT true
      )
    `);

    // Add missing columns to hub_users if they don't exist (for existing databases)
    await query(`
      DO $$
      BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hub_users' AND column_name = 'avatar_url') THEN
          ALTER TABLE hub_users ADD COLUMN avatar_url TEXT;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hub_users' AND column_name = 'is_vendor') THEN
          ALTER TABLE hub_users ADD COLUMN is_vendor BOOLEAN DEFAULT false;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hub_users' AND column_name = 'username') THEN
          ALTER TABLE hub_users ADD COLUMN username VARCHAR(255) UNIQUE;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hub_users' AND column_name = 'password_hash') THEN
          ALTER TABLE hub_users ADD COLUMN password_hash VARCHAR(255);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hub_users' AND column_name = 'is_super_admin') THEN
          ALTER TABLE hub_users ADD COLUMN is_super_admin BOOLEAN DEFAULT false;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hub_users' AND column_name = 'email_verified') THEN
          ALTER TABLE hub_users ADD COLUMN email_verified BOOLEAN DEFAULT false;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hub_users' AND column_name = 'last_login') THEN
          ALTER TABLE hub_users ADD COLUMN last_login TIMESTAMP;
        END IF;
      END
      $$;
    `);

    // Create hub_user_identities table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS hub_user_identities (
        id SERIAL PRIMARY KEY,
        hub_user_id INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
        platform VARCHAR(50) NOT NULL,
        platform_user_id VARCHAR(255) NOT NULL,
        platform_username VARCHAR(255),
        avatar_url TEXT,
        is_primary BOOLEAN DEFAULT false,
        linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used TIMESTAMP,
        UNIQUE(hub_user_id, platform),
        UNIQUE(platform, platform_user_id)
      )
    `);

    // Create community_type enum if not exists
    await query(`
      DO $$
      BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'community_type') THEN
          CREATE TYPE community_type AS ENUM (
            'shared_interest_group', 'gaming', 'creator', 'corporate', 'other'
          );
        END IF;
      END $$
    `);

    // Create communities table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS communities (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) UNIQUE NOT NULL,
        display_name VARCHAR(255),
        description TEXT,
        logo_url TEXT,
        banner_url TEXT,
        primary_platform VARCHAR(50) NOT NULL DEFAULT 'discord',
        platform VARCHAR(50) NOT NULL DEFAULT 'discord',
        platform_server_id VARCHAR(255),
        owner_id VARCHAR(255),
        owner_name VARCHAR(255),
        community_type community_type NOT NULL DEFAULT 'creator',
        join_mode VARCHAR(50) DEFAULT 'open',
        member_count INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT true,
        is_public BOOLEAN DEFAULT true,
        config JSONB DEFAULT '{}',
        created_by VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        deleted_at TIMESTAMP,
        deleted_by VARCHAR(255)
      )
    `);

    // Create community_members table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS community_members (
        id SERIAL PRIMARY KEY,
        community_id INTEGER REFERENCES communities(id) ON DELETE CASCADE,
        user_id VARCHAR(255),
        platform VARCHAR(50),
        platform_user_id VARCHAR(255),
        display_name VARCHAR(255),
        avatar_url TEXT,
        bio TEXT,
        social_links JSONB DEFAULT '{}',
        role VARCHAR(50) DEFAULT 'member',
        reputation INTEGER DEFAULT 600,
        is_active BOOLEAN DEFAULT true,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        left_at TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(community_id, platform, platform_user_id)
      )
    `);

    // Create hub_chat_messages table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS hub_chat_messages (
        id SERIAL PRIMARY KEY,
        community_id INTEGER NOT NULL,
        channel_name VARCHAR(255),
        sender_hub_user_id INTEGER,
        sender_platform VARCHAR(50),
        sender_username VARCHAR(255),
        sender_avatar_url TEXT,
        message_content TEXT NOT NULL,
        message_type VARCHAR(50) DEFAULT 'text',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create index for chat messages
    await query(`
      CREATE INDEX IF NOT EXISTS idx_chat_messages_community
      ON hub_chat_messages(community_id, created_at DESC)
    `);

    // Create hub_modules table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS hub_modules (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) UNIQUE NOT NULL,
        display_name VARCHAR(255),
        description TEXT,
        version VARCHAR(50),
        author VARCHAR(255),
        category VARCHAR(100),
        icon_url TEXT,
        is_published BOOLEAN DEFAULT false,
        is_core BOOLEAN DEFAULT false,
        config_schema JSONB DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create hub_module_installations table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS hub_module_installations (
        id SERIAL PRIMARY KEY,
        community_id INTEGER NOT NULL,
        module_id INTEGER REFERENCES hub_modules(id),
        installed_by INTEGER,
        config JSONB DEFAULT '{}',
        is_enabled BOOLEAN DEFAULT true,
        installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(community_id, module_id)
      )
    `);

    // Create hub_module_reviews table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS hub_module_reviews (
        id SERIAL PRIMARY KEY,
        module_id INTEGER REFERENCES hub_modules(id),
        community_id INTEGER,
        user_id INTEGER,
        rating INTEGER CHECK (rating >= 1 AND rating <= 5),
        review_text TEXT,
        admin_notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create announcements table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS announcements (
        id SERIAL PRIMARY KEY,
        community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
        title VARCHAR(255) NOT NULL,
        content TEXT NOT NULL,
        announcement_type VARCHAR(50) DEFAULT 'general',
        priority INTEGER DEFAULT 0,
        status VARCHAR(50) DEFAULT 'published',
        is_pinned BOOLEAN DEFAULT false,
        broadcast_to_platforms BOOLEAN DEFAULT false,
        broadcasted_platforms JSONB DEFAULT '[]',
        created_by INTEGER REFERENCES hub_users(id),
        created_by_name VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_by INTEGER REFERENCES hub_users(id),
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        published_at TIMESTAMP,
        archived_at TIMESTAMP
      )
    `);

    // Create index for announcements
    await query(`
      CREATE INDEX IF NOT EXISTS idx_announcements_community
      ON announcements(community_id, created_at DESC)
    `);

    await query(`
      CREATE INDEX IF NOT EXISTS idx_announcements_pinned
      ON announcements(community_id, is_pinned, created_at DESC)
    `);

    // Create announcement_broadcasts table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS announcement_broadcasts (
        id SERIAL PRIMARY KEY,
        announcement_id INTEGER NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
        community_server_id INTEGER,
        platform VARCHAR(50) NOT NULL,
        channel_id VARCHAR(255),
        status VARCHAR(50) DEFAULT 'pending',
        platform_message_id VARCHAR(255),
        error_message TEXT,
        broadcasted_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create index for announcement broadcasts
    await query(`
      CREATE INDEX IF NOT EXISTS idx_announcement_broadcasts_announcement
      ON announcement_broadcasts(announcement_id)
    `);

    // Create community_overlay_tokens table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS community_overlay_tokens (
        id SERIAL PRIMARY KEY,
        community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
        overlay_key VARCHAR(64) NOT NULL UNIQUE,
        previous_key VARCHAR(64),
        is_active BOOLEAN DEFAULT true,
        theme_config JSONB DEFAULT '{}',
        enabled_sources JSONB DEFAULT '["alerts", "chat", "goals", "ticker"]',
        last_accessed TIMESTAMP,
        access_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        rotated_at TIMESTAMP,
        UNIQUE(community_id)
      )
    `);

    // Create overlay_access_log table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS overlay_access_log (
        id SERIAL PRIMARY KEY,
        community_id INTEGER NOT NULL,
        overlay_key VARCHAR(64),
        ip_address VARCHAR(45),
        user_agent TEXT,
        accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create index for overlay access log
    await query(`
      CREATE INDEX IF NOT EXISTS idx_overlay_access_log_community
      ON overlay_access_log(community_id, accessed_at DESC)
    `);

    // Create analytics_bot_scores table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS analytics_bot_scores (
        id SERIAL PRIMARY KEY,
        community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
        score INTEGER NOT NULL CHECK (score >= 0 AND score <= 100),
        grade VARCHAR(1) NOT NULL CHECK (grade IN ('A', 'B', 'C', 'D', 'F')),
        bad_actor_score INTEGER DEFAULT 0,
        reputation_score INTEGER DEFAULT 0,
        security_score INTEGER DEFAULT 0,
        ai_behavioral_score INTEGER DEFAULT 0,
        suspected_bot_count INTEGER DEFAULT 0,
        high_confidence_bot_count INTEGER DEFAULT 0,
        total_users_analyzed INTEGER DEFAULT 0,
        community_size_category VARCHAR(20) DEFAULT 'small',
        calculation_metadata JSONB DEFAULT '{}',
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(community_id)
      )
    `);

    // Create index for bot scores
    await query(`
      CREATE INDEX IF NOT EXISTS idx_analytics_bot_scores_community
      ON analytics_bot_scores(community_id)
    `);

    await query(`
      CREATE INDEX IF NOT EXISTS idx_analytics_bot_scores_grade
      ON analytics_bot_scores(grade)
    `);

    // Create analytics_suspected_bots table for detailed bot analysis
    await query(`
      CREATE TABLE IF NOT EXISTS analytics_suspected_bots (
        id SERIAL PRIMARY KEY,
        community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
        platform VARCHAR(50) NOT NULL,
        platform_user_id VARCHAR(255) NOT NULL,
        username VARCHAR(255),
        confidence_score INTEGER NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 100),
        detection_reasons JSONB DEFAULT '[]',
        ai_analysis TEXT,
        behavioral_flags JSONB DEFAULT '[]',
        first_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_activity_at TIMESTAMP,
        is_confirmed_bot BOOLEAN DEFAULT false,
        is_false_positive BOOLEAN DEFAULT false,
        reviewed_by INTEGER REFERENCES hub_users(id),
        reviewed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(community_id, platform, platform_user_id)
      )
    `);

    // Create index for suspected bots
    await query(`
      CREATE INDEX IF NOT EXISTS idx_analytics_suspected_bots_community
      ON analytics_suspected_bots(community_id, confidence_score DESC)
    `);

    // Create hub_settings table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS hub_settings (
        id SERIAL PRIMARY KEY,
        setting_key VARCHAR(255) UNIQUE NOT NULL,
        setting_value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_by INTEGER REFERENCES hub_users(id)
      )
    `);

    // Create index for hub_settings
    await query(`
      CREATE INDEX IF NOT EXISTS idx_hub_settings_key
      ON hub_settings(setting_key)
    `);

    // Create cookie_policy_versions table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS cookie_policy_versions (
        id SERIAL PRIMARY KEY,
        version VARCHAR(50) UNIQUE NOT NULL,
        content TEXT NOT NULL,
        changes_summary TEXT,
        is_active BOOLEAN DEFAULT false,
        effective_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER REFERENCES hub_users(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create index for active cookie policy
    await query(`
      CREATE INDEX IF NOT EXISTS idx_cookie_policy_active
      ON cookie_policy_versions(is_active) WHERE is_active = true
    `);

    // Create cookie_consent table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS cookie_consent (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
        consent_id VARCHAR(255) UNIQUE NOT NULL,
        preferences JSONB DEFAULT '{"necessary": true, "functional": false, "analytics": false, "marketing": false}',
        consent_version VARCHAR(50) NOT NULL,
        consent_method VARCHAR(50) DEFAULT 'banner',
        ip_address VARCHAR(45),
        user_agent TEXT,
        consented_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
      )
    `);

    // Create indexes for cookie_consent
    await query(`
      CREATE INDEX IF NOT EXISTS idx_cookie_consent_user
      ON cookie_consent(user_id) WHERE user_id IS NOT NULL
    `);

    await query(`
      CREATE INDEX IF NOT EXISTS idx_cookie_consent_expires
      ON cookie_consent(expires_at)
    `);

    // Create cookie_audit_log table if not exists
    await query(`
      CREATE TABLE IF NOT EXISTS cookie_audit_log (
        id SERIAL PRIMARY KEY,
        consent_id VARCHAR(255),
        user_id INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
        action VARCHAR(50) NOT NULL,
        category VARCHAR(50),
        previous_value BOOLEAN,
        new_value BOOLEAN,
        consent_version VARCHAR(50),
        ip_address VARCHAR(45),
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create index for cookie audit log
    await query(`
      CREATE INDEX IF NOT EXISTS idx_cookie_audit_log_user
      ON cookie_audit_log(user_id, created_at DESC)
    `);

    // Create hub_oauth_states table for OAuth flow state management
    await query(`
      CREATE TABLE IF NOT EXISTS hub_oauth_states (
        id SERIAL PRIMARY KEY,
        state VARCHAR(255) UNIQUE NOT NULL,
        mode VARCHAR(50) NOT NULL DEFAULT 'login',
        platform VARCHAR(50) NOT NULL,
        user_id INTEGER REFERENCES hub_users(id) ON DELETE CASCADE,
        redirect_uri TEXT,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create index for hub_oauth_states cleanup
    await query(`
      CREATE INDEX IF NOT EXISTS idx_hub_oauth_states_expires
      ON hub_oauth_states(expires_at)
    `);

    // Create hub_user_profiles table for extended profile info
    await query(`
      CREATE TABLE IF NOT EXISTS hub_user_profiles (
        id SERIAL PRIMARY KEY,
        hub_user_id INTEGER UNIQUE NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
        display_name VARCHAR(255),
        bio TEXT,
        location VARCHAR(255),
        location_city VARCHAR(100),
        location_state VARCHAR(100),
        location_country VARCHAR(2),
        website_url VARCHAR(500),
        custom_avatar_url TEXT,
        banner_url TEXT,
        visibility VARCHAR(50) DEFAULT 'public',
        show_activity BOOLEAN DEFAULT true,
        show_communities BOOLEAN DEFAULT true,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create platform_configs table for platform OAuth and settings
    await query(`
      CREATE TABLE IF NOT EXISTS platform_configs (
        id SERIAL PRIMARY KEY,
        platform VARCHAR(50) NOT NULL,
        config_key VARCHAR(100) NOT NULL,
        config_value TEXT,
        is_encrypted BOOLEAN DEFAULT false,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_by INTEGER REFERENCES hub_users(id),
        UNIQUE(platform, config_key)
      )
    `);

    // Create audit_log table for security and activity logging
    await query(`
      CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
        action VARCHAR(100) NOT NULL,
        target_type VARCHAR(50),
        target_id VARCHAR(255),
        details JSONB DEFAULT '{}',
        ip_address VARCHAR(45),
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create index for audit_log queries
    await query(`
      CREATE INDEX IF NOT EXISTS idx_audit_log_user
      ON audit_log(user_id, created_at DESC)
    `);

    await query(`
      CREATE INDEX IF NOT EXISTS idx_audit_log_action
      ON audit_log(action, created_at DESC)
    `);

    // Create community_servers table for multi-platform server linking
    await query(`
      CREATE TABLE IF NOT EXISTS community_servers (
        id SERIAL PRIMARY KEY,
        community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
        platform VARCHAR(50) NOT NULL,
        platform_server_id VARCHAR(255) NOT NULL,
        platform_server_name VARCHAR(255),
        link_type VARCHAR(50) DEFAULT 'standard',
        status VARCHAR(50) DEFAULT 'pending',
        is_primary BOOLEAN DEFAULT false,
        config JSONB DEFAULT '{}',
        added_by INTEGER REFERENCES hub_users(id),
        approved_by INTEGER REFERENCES hub_users(id),
        verified_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(community_id, platform, platform_server_id)
      )
    `);

    // Create index for community_servers
    await query(`
      CREATE INDEX IF NOT EXISTS idx_community_servers_community
      ON community_servers(community_id)
    `);

    // First-run admin bootstrap: fail-closed, env-driven only.
    // No default account/password is ever planted (CWE-798). An initial
    // super-admin is created ONLY when both INITIAL_ADMIN_EMAIL and
    // INITIAL_ADMIN_PASSWORD are set AND no super-admin exists yet.
    await bootstrapInitialAdmin(query);

    // Seed default hub_settings if not exists
    const defaultSettings = [
      { key: 'signup_enabled', value: 'true' },
      { key: 'email_configured', value: 'false' },
      { key: 'signup_allowed_domains', value: '' },
      { key: 'require_email_verification', value: 'false' },
      { key: 'storage_type', value: 'local' },
    ];

    for (const setting of defaultSettings) {
      await query(
        `INSERT INTO hub_settings (setting_key, setting_value, updated_at)
         VALUES ($1, $2, NOW())
         ON CONFLICT (setting_key) DO NOTHING`,
        [setting.key, setting.value]
      );
    }
    logger.system('Default hub settings initialized');

    // Seed default cookie policy if none exists
    const policyCheck = await query(
      'SELECT id FROM cookie_policy_versions LIMIT 1'
    );

    if (policyCheck.rows.length === 0) {
      const defaultPolicyContent = `
# Cookie Policy

## What Are Cookies
Cookies are small text files stored on your device when you visit our website.

## Types of Cookies We Use

### Necessary Cookies (Required)
These cookies are essential for the website to function properly. They enable basic features like page navigation and access to secure areas.

### Functional Cookies (Optional)
These cookies enable enhanced functionality and personalization, such as remembering your preferences and settings.

### Analytics Cookies (Optional)
These cookies help us understand how visitors interact with our website by collecting and reporting information anonymously.

### Marketing Cookies (Optional)
These cookies are used to track visitors across websites to display relevant advertisements.

## Your Choices
You can manage your cookie preferences at any time through the cookie settings panel. Note that disabling certain cookies may affect website functionality.

## Contact Us
If you have questions about our cookie policy, please contact us at privacy@waddlebot.io.
      `.trim();

      await query(
        `INSERT INTO cookie_policy_versions (version, content, changes_summary, is_active, effective_date)
         VALUES ($1, $2, $3, true, NOW())`,
        ['1.0.0', defaultPolicyContent, 'Initial cookie policy']
      );
      logger.system('Default cookie policy created');
    }

    // Add 'support' to community_type enum if not exists
    await query(`
      DO $$
      BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'support' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'community_type')) THEN
          ALTER TYPE community_type ADD VALUE IF NOT EXISTS 'support';
        END IF;
      END $$
    `);

    // Support ticket system tables
    await query(`
      CREATE TABLE IF NOT EXISTS support_ticket_categories (
        id SERIAL PRIMARY KEY,
        community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        sort_order INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT true,
        form_fields JSONB DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    await query(`
      CREATE TABLE IF NOT EXISTS support_tickets (
        id SERIAL PRIMARY KEY,
        community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
        category_id INTEGER REFERENCES support_ticket_categories(id),
        ticket_number VARCHAR(20) NOT NULL,
        subject VARCHAR(500) NOT NULL,
        description TEXT,
        status VARCHAR(20) NOT NULL DEFAULT 'open',
        priority VARCHAR(20) NOT NULL DEFAULT 'medium',
        reporter_user_id INTEGER,
        reporter_name VARCHAR(255),
        reporter_email VARCHAR(255),
        assignee_user_id INTEGER,
        custom_fields JSONB DEFAULT '{}',
        resolved_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    await query(`
      CREATE TABLE IF NOT EXISTS support_ticket_comments (
        id SERIAL PRIMARY KEY,
        ticket_id INTEGER NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
        author_user_id INTEGER,
        author_name VARCHAR(255),
        content TEXT NOT NULL,
        is_internal BOOLEAN DEFAULT false,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    await query('CREATE INDEX IF NOT EXISTS idx_support_tickets_community ON support_tickets(community_id)');
    await query('CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status)');
    await query('CREATE INDEX IF NOT EXISTS idx_support_tickets_assignee ON support_tickets(assignee_user_id)');
    await query('CREATE INDEX IF NOT EXISTS idx_support_tickets_reporter ON support_tickets(reporter_user_id)');
    await query('CREATE INDEX IF NOT EXISTS idx_support_ticket_comments_ticket ON support_ticket_comments(ticket_id)');

    logger.system('Database initialized successfully');
  } catch (err) {
    logger.error('Database initialization failed', { error: err.message });
    throw err;
  }
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Create Express app
const app = express();

// Trust proxy (for rate limiting behind reverse proxy)
app.set('trust proxy', 1);

// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "'unsafe-inline'"], // unsafe-inline for React dev
      styleSrc: ["'self'", "'unsafe-inline'"], // unsafe-inline for Tailwind/inline styles
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: ["'self'", "ws:", "wss:"], // WebSocket support
      fontSrc: ["'self'", "data:"],
      objectSrc: ["'none'"],
      mediaSrc: ["'self'"],
      frameSrc: ["'none'"],
    },
  },
  crossOriginEmbedderPolicy: false, // Allow embedding for OBS browser source
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true,
  },
}));

// CORS
app.use(cors({
  origin: config.cors.origin,
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'],
  allowedHeaders: ['Authorization', 'Content-Type', 'X-API-Key', 'X-Request-ID', 'X-Requested-With', 'Accept', 'Origin'],
  exposedHeaders: ['X-Request-ID'],
}));

// Correlation ID (replaces Kong correlation-id plugin)
app.use((req, res, next) => {
  const requestId = req.headers['x-request-id'] || crypto.randomUUID();
  req.headers['x-request-id'] = requestId;
  res.setHeader('X-Request-ID', requestId);
  next();
});

// Rate limiting
const limiter = rateLimit({
  windowMs: config.rateLimit.windowMs,
  max: config.rateLimit.maxRequests,
  message: { success: false, error: { code: 'RATE_LIMITED', message: 'Too many requests' } },
  standardHeaders: true,
  legacyHeaders: false,
});
app.use('/api/', limiter);

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Cookie parsing (required for CSRF tokens)
app.use(cookieParser());

// XSS protection - sanitize all string inputs
app.use(sanitizeBody);

// CSRF protection for state-changing requests
// Set CSRF token for all requests
app.use(setCsrfToken);
// Verify CSRF token on POST/PUT/PATCH/DELETE
app.use(verifyCsrfToken);

// Request logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    // Only log API requests, not static files
    if (req.path.startsWith('/api/') || req.path === '/health') {
      logger.http(req, res, duration);
    }
  });
  next();
});

// Health check endpoint
app.get('/health', async (req, res) => {
  const dbHealthy = await checkConnection();
  const status = dbHealthy ? 'healthy' : 'degraded';

  res.status(dbHealthy ? 200 : 503).json({
    module: 'hub_module',
    version: '1.0.0',
    status,
    timestamp: new Date().toISOString(),
    database: dbHealthy ? 'connected' : 'disconnected',
  });
});

// Metrics endpoint (for internal monitoring)
app.get('/metrics', async (req, res) => {
  const { getPoolMetrics } = await import('./config/database.js');
  const poolMetrics = getPoolMetrics();

  res.json({
    module: 'hub_module',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    database: {
      pool: poolMetrics,
      health: await checkConnection(),
    },
    uptime: process.uptime(),
    memory: process.memoryUsage(),
  });
});

// API routes
app.use('/api/v1', routes);

// Serve frontend static files (both production and development)
// In Docker, frontend is built to /app/public; in dev, use relative path
const frontendPath = process.env.STATIC_PATH || path.join(__dirname, '../public');
app.use(express.static(frontendPath));

// SPA fallback - serve index.html for all non-API routes
app.get('*', (req, res, next) => {
  if (req.path.startsWith('/api/')) {
    return next();
  }
  res.sendFile(path.join(frontendPath, 'index.html'));
});

// 404 handler for API routes
app.use('/api/', notFoundHandler);

// Global error handler
app.use(errorHandler);

// Create HTTP server for Express and Socket.io
const httpServer = createServer(app);

// Graceful shutdown
async function shutdown(signal, io) {
  logger.system(`${signal} received, shutting down gracefully`);

  // Close Socket.io connections
  if (io) {
    io.close();
  }

  // Close HTTP server
  httpServer.close();

  // Close database pool
  await closePool();

  process.exit(0);
}

// Start server
async function start() {
  // Initialize database tables and default admin
  await initializeDatabase();

  // Setup WebSocket
  const io = setupWebSocket(httpServer);

  // Start HTTP server
  httpServer.listen(config.port, config.host, () => {
    logger.system('Hub module started', {
      port: config.port,
      host: config.host,
      env: config.env,
      websocket: 'enabled',
    });
  });

  // Handle server errors
  httpServer.on('error', (err) => {
    logger.error('Server error', { error: err.message });
    process.exit(1);
  });

  // Setup graceful shutdown handlers
  process.on('SIGTERM', () => shutdown('SIGTERM', io));
  process.on('SIGINT', () => shutdown('SIGINT', io));
}

start().catch((err) => {
  logger.error('Failed to start server', { error: err.message });
  process.exit(1);
});

export default app;
