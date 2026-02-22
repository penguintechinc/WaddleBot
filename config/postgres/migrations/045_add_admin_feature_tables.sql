-- Add missing tables for admin features: reputation config, AI researcher config, bot detection
-- These tables were referenced by adminController.js but never created in migrations

-- Community Reputation Configuration (FICO-style scoring system)
CREATE TABLE IF NOT EXISTS community_reputation_config (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    is_premium BOOLEAN DEFAULT FALSE,
    chat_message DECIMAL(10,4) DEFAULT 0.01,
    command_usage DECIMAL(10,4) DEFAULT -0.1,
    giveaway_entry DECIMAL(10,4) DEFAULT -1.0,
    follow DECIMAL(10,4) DEFAULT 1.0,
    subscription DECIMAL(10,4) DEFAULT 5.0,
    subscription_tier2 DECIMAL(10,4) DEFAULT 10.0,
    subscription_tier3 DECIMAL(10,4) DEFAULT 20.0,
    gift_subscription DECIMAL(10,4) DEFAULT 3.0,
    donation_per_dollar DECIMAL(10,4) DEFAULT 1.0,
    cheer_per_100bits DECIMAL(10,4) DEFAULT 1.0,
    raid DECIMAL(10,4) DEFAULT 2.0,
    boost DECIMAL(10,4) DEFAULT 5.0,
    warn DECIMAL(10,4) DEFAULT -25.0,
    timeout DECIMAL(10,4) DEFAULT -50.0,
    kick DECIMAL(10,4) DEFAULT -75.0,
    ban DECIMAL(10,4) DEFAULT -200.0,
    auto_ban_enabled BOOLEAN DEFAULT FALSE,
    auto_ban_threshold INTEGER DEFAULT 450,
    starting_score INTEGER DEFAULT 600,
    min_score INTEGER DEFAULT 300,
    max_score INTEGER DEFAULT 850,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(community_id)
);

-- AI Researcher Configuration
CREATE TABLE IF NOT EXISTS ai_researcher_config (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    is_enabled BOOLEAN DEFAULT FALSE,
    ai_provider VARCHAR(50) DEFAULT 'ollama',
    ai_model VARCHAR(100) DEFAULT 'tinyllama',
    custom_ai_endpoint VARCHAR(500),
    custom_api_key_encrypted TEXT,
    use_custom_endpoint BOOLEAN DEFAULT FALSE,
    stream_summary_enabled BOOLEAN DEFAULT FALSE,
    stream_summary_interval_hours INTEGER DEFAULT 6,
    weekly_rollup_enabled BOOLEAN DEFAULT FALSE,
    weekly_rollup_day VARCHAR(20) DEFAULT 'sunday',
    bot_detection_enabled BOOLEAN DEFAULT FALSE,
    bot_detection_sensitivity VARCHAR(20) DEFAULT 'medium',
    context_window_days INTEGER DEFAULT 7,
    max_context_tokens INTEGER DEFAULT 4000,
    is_premium BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(community_id)
);

-- Bot Detection Results
CREATE TABLE IF NOT EXISTS bot_detection_results (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    user_id INTEGER,
    username VARCHAR(255),
    confidence DECIMAL(5,4) DEFAULT 0,
    reasons JSONB DEFAULT '[]'::jsonb,
    review_status VARCHAR(20) DEFAULT 'pending',
    review_action VARCHAR(30),
    review_notes TEXT,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by INTEGER REFERENCES hub_users(id),
    CONSTRAINT valid_review_status CHECK (review_status IN ('pending', 'reviewed', 'dismissed'))
);

CREATE INDEX IF NOT EXISTS idx_bot_detection_community ON bot_detection_results(community_id);
CREATE INDEX IF NOT EXISTS idx_bot_detection_status ON bot_detection_results(review_status);
CREATE INDEX IF NOT EXISTS idx_reputation_config_community ON community_reputation_config(community_id);
CREATE INDEX IF NOT EXISTS idx_ai_researcher_config_community ON ai_researcher_config(community_id);
