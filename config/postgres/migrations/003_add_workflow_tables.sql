-- Waddles Workflow System - Database Schema Migration
-- Creates all tables for the visual workflow automation system

-- ============================================================================
-- WORKFLOWS TABLE - Main workflow definitions
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflows (
    id SERIAL PRIMARY KEY,
    workflow_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    community_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,

    -- Metadata
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version INTEGER NOT NULL DEFAULT 1,

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'draft', -- draft, published, archived
    is_active BOOLEAN NOT NULL DEFAULT false,

    -- Workflow Structure (JSONB for flexibility)
    nodes JSONB NOT NULL DEFAULT '[]',
    connections JSONB NOT NULL DEFAULT '[]',

    -- Trigger Configuration
    trigger_type VARCHAR(100) NOT NULL, -- command, event, webhook, schedule
    trigger_config JSONB NOT NULL DEFAULT '{}',

    -- Execution Settings
    max_execution_time INTEGER NOT NULL DEFAULT 300, -- seconds
    max_iterations INTEGER NOT NULL DEFAULT 100,
    retry_config JSONB NOT NULL DEFAULT '{"enabled": false, "max_retries": 3, "backoff": "exponential"}',

    -- Statistics
    execution_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    last_executed_at TIMESTAMP,

    -- Ownership
    created_by INTEGER,
    updated_by INTEGER,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT workflows_status_check CHECK (status IN ('draft', 'published', 'archived'))
);

-- Indexes for workflows
CREATE INDEX idx_workflows_community_id ON workflows(community_id);
CREATE INDEX idx_workflows_entity_id ON workflows(entity_id);
CREATE INDEX idx_workflows_status ON workflows(status);
CREATE INDEX idx_workflows_is_active ON workflows(is_active);
CREATE INDEX idx_workflows_trigger_type ON workflows(trigger_type);
CREATE INDEX idx_workflows_created_at ON workflows(created_at);

-- ============================================================================
-- WORKFLOW_EXECUTIONS TABLE - Execution tracking and state
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflow_executions (
    id SERIAL PRIMARY KEY,
    execution_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(workflow_id) ON DELETE CASCADE,

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, running, completed, failed, cancelled, timeout

    -- Trigger Information
    trigger_source VARCHAR(100) NOT NULL, -- command, event, webhook, schedule, manual
    trigger_data JSONB NOT NULL DEFAULT '{}',

    -- Execution State
    execution_path JSONB NOT NULL DEFAULT '[]', -- Array of node IDs executed in order
    node_states JSONB NOT NULL DEFAULT '{}', -- State of each node execution
    variables JSONB NOT NULL DEFAULT '{}', -- Workflow variables
    current_node_id VARCHAR(255),

    -- Context
    entity_id INTEGER NOT NULL,
    user_id INTEGER,
    session_id VARCHAR(255),
    platform VARCHAR(50),
    channel_name VARCHAR(255),

    -- Performance Metrics
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    nodes_executed INTEGER DEFAULT 0,

    -- Error Tracking
    error_message TEXT,
    error_node_id VARCHAR(255),
    error_stack TEXT,

    -- Retry Support
    retry_count INTEGER NOT NULL DEFAULT 0,
    parent_execution_id UUID,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT workflow_executions_status_check CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'timeout'))
);

-- Indexes for workflow_executions
CREATE INDEX idx_workflow_executions_workflow_id ON workflow_executions(workflow_id);
CREATE INDEX idx_workflow_executions_status ON workflow_executions(status);
CREATE INDEX idx_workflow_executions_entity_id ON workflow_executions(entity_id);
CREATE INDEX idx_workflow_executions_user_id ON workflow_executions(user_id);
CREATE INDEX idx_workflow_executions_session_id ON workflow_executions(session_id);
CREATE INDEX idx_workflow_executions_started_at ON workflow_executions(started_at);
CREATE INDEX idx_workflow_executions_trigger_source ON workflow_executions(trigger_source);

-- ============================================================================
-- WORKFLOW_NODE_EXECUTIONS TABLE - Per-node execution details
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflow_node_executions (
    id SERIAL PRIMARY KEY,
    execution_id UUID NOT NULL REFERENCES workflow_executions(execution_id) ON DELETE CASCADE,
    node_id VARCHAR(255) NOT NULL,
    node_type VARCHAR(100) NOT NULL,

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, running, completed, failed, skipped

    -- Execution Details
    input_data JSONB,
    output_data JSONB,
    variables_before JSONB,
    variables_after JSONB,

    -- Performance
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,

    -- Error Tracking
    error_message TEXT,
    error_stack TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Sequence
    execution_order INTEGER NOT NULL,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT workflow_node_executions_status_check CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped'))
);

-- Indexes for workflow_node_executions
CREATE INDEX idx_workflow_node_executions_execution_id ON workflow_node_executions(execution_id);
CREATE INDEX idx_workflow_node_executions_node_id ON workflow_node_executions(node_id);
CREATE INDEX idx_workflow_node_executions_status ON workflow_node_executions(status);
CREATE INDEX idx_workflow_node_executions_order ON workflow_node_executions(execution_order);

-- ============================================================================
-- WORKFLOW_SCHEDULES TABLE - Cron and scheduled workflows
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflow_schedules (
    id SERIAL PRIMARY KEY,
    schedule_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(workflow_id) ON DELETE CASCADE,

    -- Schedule Configuration
    schedule_type VARCHAR(50) NOT NULL, -- cron, interval, one_time
    cron_expression VARCHAR(255), -- For cron type
    interval_seconds INTEGER, -- For interval type
    scheduled_time TIMESTAMP, -- For one_time type
    timezone VARCHAR(100) DEFAULT 'UTC',

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,

    -- Execution Tracking
    next_execution_at TIMESTAMP,
    last_execution_at TIMESTAMP,
    last_execution_id UUID,

    -- Limits
    max_executions INTEGER, -- NULL = unlimited
    execution_count INTEGER NOT NULL DEFAULT 0,

    -- Context
    context_data JSONB NOT NULL DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT workflow_schedules_type_check CHECK (schedule_type IN ('cron', 'interval', 'one_time'))
);

-- Indexes for workflow_schedules
CREATE INDEX idx_workflow_schedules_workflow_id ON workflow_schedules(workflow_id);
CREATE INDEX idx_workflow_schedules_is_active ON workflow_schedules(is_active);
CREATE INDEX idx_workflow_schedules_next_execution ON workflow_schedules(next_execution_at);
CREATE INDEX idx_workflow_schedules_schedule_type ON workflow_schedules(schedule_type);

-- ============================================================================
-- WORKFLOW_PERMISSIONS TABLE - Access control
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflow_permissions (
    id SERIAL PRIMARY KEY,
    workflow_id UUID NOT NULL REFERENCES workflows(workflow_id) ON DELETE CASCADE,

    -- Permission Target
    permission_type VARCHAR(50) NOT NULL, -- user, role, entity
    target_id INTEGER NOT NULL, -- user_id, role_id, or entity_id

    -- Permissions (granular)
    can_view BOOLEAN NOT NULL DEFAULT false,
    can_edit BOOLEAN NOT NULL DEFAULT false,
    can_execute BOOLEAN NOT NULL DEFAULT false,
    can_delete BOOLEAN NOT NULL DEFAULT false,
    can_manage_permissions BOOLEAN NOT NULL DEFAULT false,

    -- Granted By
    granted_by INTEGER,
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT workflow_permissions_type_check CHECK (permission_type IN ('user', 'role', 'entity')),
    CONSTRAINT workflow_permissions_unique UNIQUE (workflow_id, permission_type, target_id)
);

-- Indexes for workflow_permissions
CREATE INDEX idx_workflow_permissions_workflow_id ON workflow_permissions(workflow_id);
CREATE INDEX idx_workflow_permissions_target ON workflow_permissions(permission_type, target_id);

-- ============================================================================
-- WORKFLOW_WEBHOOKS TABLE - Webhook trigger endpoints
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflow_webhooks (
    id SERIAL PRIMARY KEY,
    webhook_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(workflow_id) ON DELETE CASCADE,

    -- Webhook Configuration
    webhook_token VARCHAR(255) UNIQUE NOT NULL,
    webhook_url VARCHAR(500), -- Full URL (auto-generated)

    -- Security
    hmac_secret VARCHAR(255), -- For signature verification
    ip_allowlist JSONB DEFAULT '[]', -- Array of allowed IP addresses/ranges
    require_signature BOOLEAN NOT NULL DEFAULT false,

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,

    -- Statistics
    trigger_count INTEGER NOT NULL DEFAULT 0,
    last_triggered_at TIMESTAMP,
    last_trigger_ip VARCHAR(100),

    -- Limits
    rate_limit_per_minute INTEGER DEFAULT 60,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for workflow_webhooks
CREATE INDEX idx_workflow_webhooks_workflow_id ON workflow_webhooks(workflow_id);
CREATE INDEX idx_workflow_webhooks_token ON workflow_webhooks(webhook_token);
CREATE INDEX idx_workflow_webhooks_is_active ON workflow_webhooks(is_active);

-- ============================================================================
-- WORKFLOW_AUDIT_LOG TABLE - Audit trail for workflow changes
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflow_audit_log (
    id SERIAL PRIMARY KEY,
    workflow_id UUID NOT NULL,

    -- Action Details
    action VARCHAR(100) NOT NULL, -- created, updated, published, archived, executed, deleted
    action_by INTEGER NOT NULL, -- user_id

    -- Change Details
    changes JSONB, -- What changed (for updates)
    metadata JSONB DEFAULT '{}',

    -- Context
    ip_address VARCHAR(100),
    user_agent TEXT,

    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for workflow_audit_log
CREATE INDEX idx_workflow_audit_log_workflow_id ON workflow_audit_log(workflow_id);
CREATE INDEX idx_workflow_audit_log_action ON workflow_audit_log(action);
CREATE INDEX idx_workflow_audit_log_created_at ON workflow_audit_log(created_at);

-- ============================================================================
-- WORKFLOW_TEMPLATES TABLE - Reusable workflow templates
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflow_templates (
    id SERIAL PRIMARY KEY,
    template_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),

    -- Template Info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    tags JSONB DEFAULT '[]',

    -- Template Structure
    template_data JSONB NOT NULL, -- Contains nodes, connections, config

    -- Visibility
    is_public BOOLEAN NOT NULL DEFAULT false,
    created_by INTEGER,

    -- Statistics
    use_count INTEGER NOT NULL DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for workflow_templates
CREATE INDEX idx_workflow_templates_category ON workflow_templates(category);
CREATE INDEX idx_workflow_templates_is_public ON workflow_templates(is_public);
CREATE INDEX idx_workflow_templates_created_by ON workflow_templates(created_by);

-- ============================================================================
-- TRIGGERS for automatic timestamp updates
-- ============================================================================

-- Update workflows.updated_at
CREATE OR REPLACE FUNCTION update_workflows_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_workflows_updated_at
    BEFORE UPDATE ON workflows
    FOR EACH ROW
    EXECUTE FUNCTION update_workflows_timestamp();

-- Update workflow_executions.updated_at
CREATE OR REPLACE FUNCTION update_workflow_executions_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_workflow_executions_updated_at
    BEFORE UPDATE ON workflow_executions
    FOR EACH ROW
    EXECUTE FUNCTION update_workflow_executions_timestamp();

-- Update workflow_schedules.updated_at
CREATE OR REPLACE FUNCTION update_workflow_schedules_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_workflow_schedules_updated_at
    BEFORE UPDATE ON workflow_schedules
    FOR EACH ROW
    EXECUTE FUNCTION update_workflow_schedules_timestamp();

-- Update workflow_webhooks.updated_at
CREATE OR REPLACE FUNCTION update_workflow_webhooks_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_workflow_webhooks_updated_at
    BEFORE UPDATE ON workflow_webhooks
    FOR EACH ROW
    EXECUTE FUNCTION update_workflow_webhooks_timestamp();

-- ============================================================================
-- Comments for documentation
-- ============================================================================

COMMENT ON TABLE workflows IS 'Main workflow definitions with graph structure and configuration';
COMMENT ON TABLE workflow_executions IS 'Tracks individual workflow executions with state and performance metrics';
COMMENT ON TABLE workflow_node_executions IS 'Detailed per-node execution logs for debugging and analysis';
COMMENT ON TABLE workflow_schedules IS 'Cron and scheduled workflow configurations';
COMMENT ON TABLE workflow_permissions IS 'Granular access control for workflow operations';
COMMENT ON TABLE workflow_webhooks IS 'Webhook endpoints for triggering workflows externally';
COMMENT ON TABLE workflow_audit_log IS 'Audit trail for workflow changes and actions';
COMMENT ON TABLE workflow_templates IS 'Reusable workflow templates for quick setup';

-- ============================================================================
-- Grant permissions (adjust as needed for your setup)
-- ============================================================================

-- Grant permissions to the waddlebot role if it exists
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'waddlebot') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO waddlebot;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO waddlebot;
    END IF;
END
$$;
