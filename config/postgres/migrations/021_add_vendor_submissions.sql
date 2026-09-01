-- Migration: Add Vendor Module Submission System
-- Version: 021
-- Description: Tables for managing third-party vendor module submissions and approval workflow

-- =============================================================================
-- Vendor Submissions Table (Main Registry)
-- =============================================================================
CREATE TABLE IF NOT EXISTS vendor_submissions (
    id SERIAL PRIMARY KEY,
    submission_id VARCHAR(36) UNIQUE NOT NULL,
    vendor_name VARCHAR(255) NOT NULL,
    vendor_email VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    contact_phone VARCHAR(20),
    website_url VARCHAR(500),

    -- Module Details
    module_name VARCHAR(255) NOT NULL,
    module_description TEXT,
    module_category VARCHAR(100) NOT NULL DEFAULT 'interactive',
    module_version VARCHAR(50),
    repository_url VARCHAR(500),

    -- Webhook Configuration
    webhook_url VARCHAR(500) NOT NULL,
    webhook_secret VARCHAR(255),
    webhook_per_community BOOLEAN DEFAULT false,

    -- Scopes Required
    scopes JSONB NOT NULL DEFAULT '[]',
    scope_justification TEXT,

    -- Pricing Model
    pricing_model VARCHAR(50) NOT NULL CHECK (pricing_model IN ('flat-rate', 'per-seat')),
    pricing_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    pricing_currency VARCHAR(3) DEFAULT 'USD',

    -- Payment Information
    payment_method VARCHAR(50) NOT NULL CHECK (payment_method IN ('paypal', 'stripe', 'check', 'bank_transfer', 'other')),
    payment_details JSONB NOT NULL DEFAULT '{}',
    processor_fee_disclaimer TEXT DEFAULT 'Processor fees will be deducted by payment processors (e.g., PayPal, Stripe). These fees are not charged by Waddles and are passed directly to the processor.',

    -- Submission Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'under-review', 'approved', 'rejected', 'suspended')),
    rejection_reason TEXT,
    admin_notes TEXT,

    -- Metadata
    supported_platforms JSONB DEFAULT '["twitch", "discord", "slack"]',
    documentation_url VARCHAR(500),
    support_email VARCHAR(255),
    support_contact_url VARCHAR(500),

    -- Timestamps
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Flags
    is_verified BOOLEAN DEFAULT false,
    requires_special_review BOOLEAN DEFAULT false,

    UNIQUE(vendor_email, module_name)
);

-- =============================================================================
-- Vendor Submission Scopes (Normalized for easier querying)
-- =============================================================================
CREATE TABLE IF NOT EXISTS vendor_submission_scopes (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES vendor_submissions(id) ON DELETE CASCADE,
    scope_name VARCHAR(100) NOT NULL,
    risk_level VARCHAR(50) NOT NULL DEFAULT 'low' CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    description TEXT,
    data_shared TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Vendor Submission Review History
-- =============================================================================
CREATE TABLE IF NOT EXISTS vendor_submission_reviews (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES vendor_submissions(id) ON DELETE CASCADE,
    reviewer_id INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL CHECK (action IN ('submitted', 'requested_info', 'approved', 'rejected', 'suspended', 'unsuspended')),
    comments TEXT,
    review_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Vendor Submission Status Tracking
-- =============================================================================
CREATE TABLE IF NOT EXISTS vendor_submission_status_log (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES vendor_submissions(id) ON DELETE CASCADE,
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    status_reason TEXT,
    changed_by INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Approved Vendors (Published Modules)
-- =============================================================================
CREATE TABLE IF NOT EXISTS approved_vendor_modules (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES vendor_submissions(id) ON DELETE CASCADE,
    vendor_name VARCHAR(255) NOT NULL,
    module_name VARCHAR(255) NOT NULL,
    module_slug VARCHAR(255) UNIQUE NOT NULL,
    webhook_url VARCHAR(500) NOT NULL,
    webhook_secret VARCHAR(255),
    webhook_per_community BOOLEAN DEFAULT false,

    -- Active Status
    is_active BOOLEAN DEFAULT true,
    suspension_reason TEXT,
    suspended_at TIMESTAMP WITH TIME ZONE,

    -- Marketplace Info
    is_featured BOOLEAN DEFAULT false,
    feature_position INTEGER,
    install_count INTEGER DEFAULT 0,
    rating DECIMAL(3, 2),
    review_count INTEGER DEFAULT 0,

    -- Metadata
    published_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Community Module Installations
-- =============================================================================
CREATE TABLE IF NOT EXISTS community_vendor_installations (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    vendor_module_id INTEGER NOT NULL REFERENCES approved_vendor_modules(id) ON DELETE CASCADE,

    -- Installation Status
    is_enabled BOOLEAN DEFAULT true,
    installed_by INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,

    -- Configuration
    module_config JSONB DEFAULT '{}',
    api_key VARCHAR(255),

    -- Webhooks (per-community if enabled)
    webhook_url VARCHAR(500),
    webhook_secret VARCHAR(255),

    -- Timestamps
    installed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(community_id, vendor_module_id)
);

-- =============================================================================
-- Vendor Module Reviews/Ratings (from communities)
-- =============================================================================
CREATE TABLE IF NOT EXISTS vendor_module_reviews (
    id SERIAL PRIMARY KEY,
    vendor_module_id INTEGER NOT NULL REFERENCES approved_vendor_modules(id) ON DELETE CASCADE,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    reviewer_id INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,

    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,

    is_verified_install BOOLEAN DEFAULT true,
    is_helpful_count INTEGER DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(vendor_module_id, community_id, reviewer_id)
);

-- =============================================================================
-- Vendor Payments/Revenue Tracking
-- =============================================================================
CREATE TABLE IF NOT EXISTS vendor_payments (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES vendor_submissions(id) ON DELETE CASCADE,

    -- Payment Details
    payment_period_start DATE NOT NULL,
    payment_period_end DATE NOT NULL,

    -- Amounts
    gross_amount DECIMAL(10, 2) NOT NULL,
    processor_fee_amount DECIMAL(10, 2) NOT NULL,
    processor_fee_percentage DECIMAL(5, 2),
    net_amount DECIMAL(10, 2) NOT NULL,

    -- Status
    payment_status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (payment_status IN ('pending', 'processing', 'completed', 'failed', 'refunded')),
    payment_method VARCHAR(50) NOT NULL,
    payment_reference VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,

    UNIQUE(submission_id, payment_period_start, payment_period_end)
);

-- =============================================================================
-- Vendor Module Installation Events (for analytics)
-- =============================================================================
CREATE TABLE IF NOT EXISTS vendor_module_events (
    id SERIAL PRIMARY KEY,
    vendor_module_id INTEGER NOT NULL REFERENCES approved_vendor_modules(id) ON DELETE CASCADE,
    community_id INTEGER REFERENCES communities(id) ON DELETE SET NULL,

    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('installed', 'uninstalled', 'enabled', 'disabled', 'updated', 'error')),
    event_data JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Indexes for Performance
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_vendor_submissions_status ON vendor_submissions(status);
CREATE INDEX IF NOT EXISTS idx_vendor_submissions_vendor_email ON vendor_submissions(vendor_email);
CREATE INDEX IF NOT EXISTS idx_vendor_submissions_submitted_at ON vendor_submissions(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_vendor_submissions_reviewed_by ON vendor_submissions(reviewed_by);

CREATE INDEX IF NOT EXISTS idx_vendor_submission_scopes_submission_id ON vendor_submission_scopes(submission_id);
CREATE INDEX IF NOT EXISTS idx_vendor_submission_scopes_risk_level ON vendor_submission_scopes(risk_level);

CREATE INDEX IF NOT EXISTS idx_vendor_submission_reviews_submission_id ON vendor_submission_reviews(submission_id);
CREATE INDEX IF NOT EXISTS idx_vendor_submission_reviews_reviewer_id ON vendor_submission_reviews(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_vendor_submission_reviews_created_at ON vendor_submission_reviews(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_vendor_submission_status_log_submission_id ON vendor_submission_status_log(submission_id);
CREATE INDEX IF NOT EXISTS idx_vendor_submission_status_log_created_at ON vendor_submission_status_log(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_approved_vendor_modules_slug ON approved_vendor_modules(module_slug);
CREATE INDEX IF NOT EXISTS idx_approved_vendor_modules_is_active ON approved_vendor_modules(is_active);
CREATE INDEX IF NOT EXISTS idx_approved_vendor_modules_is_featured ON approved_vendor_modules(is_featured);

CREATE INDEX IF NOT EXISTS idx_community_vendor_installations_community_id ON community_vendor_installations(community_id);
CREATE INDEX IF NOT EXISTS idx_community_vendor_installations_vendor_module_id ON community_vendor_installations(vendor_module_id);
CREATE INDEX IF NOT EXISTS idx_community_vendor_installations_is_enabled ON community_vendor_installations(is_enabled);

CREATE INDEX IF NOT EXISTS idx_vendor_module_reviews_vendor_module_id ON vendor_module_reviews(vendor_module_id);
CREATE INDEX IF NOT EXISTS idx_vendor_module_reviews_community_id ON vendor_module_reviews(community_id);
CREATE INDEX IF NOT EXISTS idx_vendor_module_reviews_rating ON vendor_module_reviews(rating);

CREATE INDEX IF NOT EXISTS idx_vendor_payments_submission_id ON vendor_payments(submission_id);
CREATE INDEX IF NOT EXISTS idx_vendor_payments_status ON vendor_payments(payment_status);
CREATE INDEX IF NOT EXISTS idx_vendor_payments_period ON vendor_payments(payment_period_start, payment_period_end);

CREATE INDEX IF NOT EXISTS idx_vendor_module_events_vendor_module_id ON vendor_module_events(vendor_module_id);
CREATE INDEX IF NOT EXISTS idx_vendor_module_events_community_id ON vendor_module_events(community_id);
CREATE INDEX IF NOT EXISTS idx_vendor_module_events_type ON vendor_module_events(event_type);

-- =============================================================================
-- Trigger: Update last_updated on vendor_submissions
-- =============================================================================
CREATE OR REPLACE FUNCTION update_vendor_submissions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS vendor_submissions_updated_at ON vendor_submissions;
CREATE TRIGGER vendor_submissions_updated_at
BEFORE UPDATE ON vendor_submissions
FOR EACH ROW
EXECUTE FUNCTION update_vendor_submissions_updated_at();

-- =============================================================================
-- Trigger: Update approved_vendor_modules updated_at
-- =============================================================================
CREATE OR REPLACE FUNCTION update_approved_vendor_modules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS approved_vendor_modules_updated_at ON approved_vendor_modules;
CREATE TRIGGER approved_vendor_modules_updated_at
BEFORE UPDATE ON approved_vendor_modules
FOR EACH ROW
EXECUTE FUNCTION update_approved_vendor_modules_updated_at();

-- =============================================================================
-- Trigger: Auto log status changes to vendor_submission_status_log
-- =============================================================================
CREATE OR REPLACE FUNCTION log_vendor_submission_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO vendor_submission_status_log (submission_id, old_status, new_status, created_at)
        VALUES (NEW.id, OLD.status, NEW.status, NOW());
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS vendor_submissions_status_log ON vendor_submissions;
CREATE TRIGGER vendor_submissions_status_log
AFTER UPDATE ON vendor_submissions
FOR EACH ROW
EXECUTE FUNCTION log_vendor_submission_status_change();

-- =============================================================================
-- Comments/Documentation
-- =============================================================================
COMMENT ON TABLE vendor_submissions IS 'Main registry for third-party vendor module submissions awaiting approval';
COMMENT ON TABLE vendor_submission_scopes IS 'Normalized list of scopes/permissions requested by each vendor submission';
COMMENT ON TABLE vendor_submission_reviews IS 'Audit trail of all admin reviews and actions on submissions';
COMMENT ON TABLE vendor_submission_status_log IS 'Timeline of status changes for each submission (pending→approved→published)';
COMMENT ON TABLE approved_vendor_modules IS 'Approved and published vendor modules available in marketplace';
COMMENT ON TABLE community_vendor_installations IS 'Tracks which communities have installed which vendor modules';
COMMENT ON TABLE vendor_module_reviews IS 'Community ratings and reviews for published vendor modules';
COMMENT ON TABLE vendor_payments IS 'Revenue tracking and payment records for vendors';
COMMENT ON TABLE vendor_module_events IS 'Analytics events for vendor module installations and usage';

COMMENT ON COLUMN vendor_submissions.scopes IS 'JSONB array of scope objects: [{name, riskLevel, dataShared}]';
COMMENT ON COLUMN vendor_submissions.payment_details IS 'JSONB with payment method-specific details (paypal_email, check_address, bank_account, etc.)';
COMMENT ON COLUMN vendor_submissions.status IS 'Workflow status: pending (initial) → under-review → approved → published OR rejected';
COMMENT ON COLUMN approved_vendor_modules.module_slug IS 'URL-friendly slug for marketplace URLs (e.g., vendor-name-module-name)';

-- Migration Complete
