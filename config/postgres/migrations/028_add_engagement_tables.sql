-- Migration 028: Add Community Engagement Tables (Polls and Forms)
-- Description: Adds tables for community polls and forms with visibility controls
-- Author: Waddles Engineering
-- Date: 2026-01-21

BEGIN;

-- Community Polls Table
CREATE TABLE IF NOT EXISTS community_polls (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    created_by INTEGER NOT NULL REFERENCES hub_users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    view_visibility visibility_level NOT NULL DEFAULT 'community',
    submit_visibility visibility_level NOT NULL DEFAULT 'community',
    allow_multiple_choices BOOLEAN DEFAULT FALSE,
    max_choices INTEGER DEFAULT 1,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Poll Options Table
CREATE TABLE IF NOT EXISTS poll_options (
    id SERIAL PRIMARY KEY,
    poll_id INTEGER NOT NULL REFERENCES community_polls(id) ON DELETE CASCADE,
    option_text VARCHAR(500) NOT NULL,
    sort_order INTEGER DEFAULT 0
);

-- Poll Votes Table
CREATE TABLE IF NOT EXISTS poll_votes (
    id SERIAL PRIMARY KEY,
    poll_id INTEGER NOT NULL REFERENCES community_polls(id) ON DELETE CASCADE,
    option_id INTEGER NOT NULL REFERENCES poll_options(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES hub_users(id),
    ip_hash VARCHAR(64),
    voted_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_vote UNIQUE(poll_id, option_id, user_id)
);

-- Community Forms Table
CREATE TABLE IF NOT EXISTS community_forms (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    created_by INTEGER NOT NULL REFERENCES hub_users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    view_visibility visibility_level NOT NULL DEFAULT 'community',
    submit_visibility visibility_level NOT NULL DEFAULT 'community',
    is_active BOOLEAN DEFAULT TRUE,
    allow_anonymous BOOLEAN DEFAULT FALSE,
    submit_once_per_user BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Form Fields Table
CREATE TABLE IF NOT EXISTS form_fields (
    id SERIAL PRIMARY KEY,
    form_id INTEGER NOT NULL REFERENCES community_forms(id) ON DELETE CASCADE,
    field_type VARCHAR(50) NOT NULL CHECK (field_type IN ('text', 'textarea', 'select', 'checkbox', 'radio', 'date', 'number')),
    label VARCHAR(255) NOT NULL,
    placeholder VARCHAR(255),
    is_required BOOLEAN DEFAULT FALSE,
    options_json JSONB,
    validation_json JSONB,
    sort_order INTEGER DEFAULT 0
);

-- Form Submissions Table
CREATE TABLE IF NOT EXISTS form_submissions (
    id SERIAL PRIMARY KEY,
    form_id INTEGER NOT NULL REFERENCES community_forms(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES hub_users(id),
    ip_hash VARCHAR(64),
    submitted_at TIMESTAMPTZ DEFAULT NOW()
);

-- Form Field Values Table
CREATE TABLE IF NOT EXISTS form_field_values (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES form_submissions(id) ON DELETE CASCADE,
    field_id INTEGER NOT NULL REFERENCES form_fields(id) ON DELETE CASCADE,
    value_text TEXT,
    value_json JSONB
);

-- Indexes for community_polls
CREATE INDEX IF NOT EXISTS idx_community_polls_community_id ON community_polls(community_id);
CREATE INDEX IF NOT EXISTS idx_community_polls_created_by ON community_polls(created_by);
CREATE INDEX IF NOT EXISTS idx_community_polls_is_active ON community_polls(is_active);
CREATE INDEX IF NOT EXISTS idx_community_polls_expires_at ON community_polls(expires_at);
CREATE INDEX IF NOT EXISTS idx_community_polls_active_unexpired
    ON community_polls(community_id, is_active)
    WHERE is_active = TRUE AND (expires_at IS NULL OR expires_at > NOW());

-- Indexes for poll_options
CREATE INDEX IF NOT EXISTS idx_poll_options_poll_id ON poll_options(poll_id);
CREATE INDEX IF NOT EXISTS idx_poll_options_sort_order ON poll_options(poll_id, sort_order);

-- Indexes for poll_votes
CREATE INDEX IF NOT EXISTS idx_poll_votes_poll_id ON poll_votes(poll_id);
CREATE INDEX IF NOT EXISTS idx_poll_votes_option_id ON poll_votes(option_id);
CREATE INDEX IF NOT EXISTS idx_poll_votes_user_id ON poll_votes(user_id);
CREATE INDEX IF NOT EXISTS idx_poll_votes_ip_hash ON poll_votes(ip_hash);

-- Indexes for community_forms
CREATE INDEX IF NOT EXISTS idx_community_forms_community_id ON community_forms(community_id);
CREATE INDEX IF NOT EXISTS idx_community_forms_created_by ON community_forms(created_by);
CREATE INDEX IF NOT EXISTS idx_community_forms_is_active ON community_forms(is_active);
CREATE INDEX IF NOT EXISTS idx_community_forms_active
    ON community_forms(community_id, is_active)
    WHERE is_active = TRUE;

-- Indexes for form_fields
CREATE INDEX IF NOT EXISTS idx_form_fields_form_id ON form_fields(form_id);
CREATE INDEX IF NOT EXISTS idx_form_fields_sort_order ON form_fields(form_id, sort_order);

-- Indexes for form_submissions
CREATE INDEX IF NOT EXISTS idx_form_submissions_form_id ON form_submissions(form_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_user_id ON form_submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_ip_hash ON form_submissions(ip_hash);
CREATE INDEX IF NOT EXISTS idx_form_submissions_submitted_at ON form_submissions(submitted_at);

-- Indexes for form_field_values
CREATE INDEX IF NOT EXISTS idx_form_field_values_submission_id ON form_field_values(submission_id);
CREATE INDEX IF NOT EXISTS idx_form_field_values_field_id ON form_field_values(field_id);

-- Trigger for updated_at on community_polls
DROP TRIGGER IF EXISTS trigger_update_community_polls_timestamp ON community_polls;
CREATE TRIGGER trigger_update_community_polls_timestamp
    BEFORE UPDATE ON community_polls
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for updated_at on community_forms
DROP TRIGGER IF EXISTS trigger_update_community_forms_timestamp ON community_forms;
CREATE TRIGGER trigger_update_community_forms_timestamp
    BEFORE UPDATE ON community_forms
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMIT;
