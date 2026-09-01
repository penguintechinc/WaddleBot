-- Migration: Add Services Table for Service Discovery
-- Version: 020
-- Description: Tables for tracking Waddles microservices and their health status

-- Services table (main registry)
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(50) NOT NULL DEFAULT 'core',
    url VARCHAR(500) NOT NULL,
    port INTEGER,
    protocol VARCHAR(10) DEFAULT 'http',
    health_endpoint VARCHAR(255) DEFAULT '/health',
    status VARCHAR(20) DEFAULT 'unknown',
    response_time INTEGER,
    uptime DECIMAL(5,2),
    version VARCHAR(50),
    last_checked TIMESTAMP WITH TIME ZONE,
    dependencies JSONB DEFAULT '[]',
    environment JSONB DEFAULT '{}',
    recent_events JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Service events table (historical log)
CREATE TABLE IF NOT EXISTS service_events (
    id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    event_type VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_services_category ON services(category);
CREATE INDEX IF NOT EXISTS idx_services_status ON services(status);
CREATE INDEX IF NOT EXISTS idx_services_name ON services(name);
CREATE INDEX IF NOT EXISTS idx_service_events_service_id_created ON service_events(service_id, created_at);

-- Trigger function for updated_at timestamp
CREATE OR REPLACE FUNCTION update_services_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on services table
DROP TRIGGER IF EXISTS services_updated_at ON services;
CREATE TRIGGER services_updated_at
BEFORE UPDATE ON services
FOR EACH ROW
EXECUTE FUNCTION update_services_updated_at();

-- Comments
COMMENT ON TABLE services IS 'Registry of all Waddles microservices and their health status';
COMMENT ON TABLE service_events IS 'Historical event log for service status changes and incidents';
COMMENT ON COLUMN services.category IS 'Service category: infrastructure/core/triggers/actions/processing/admin';
COMMENT ON COLUMN services.status IS 'Service status: healthy/unhealthy/degraded/unknown/starting/stopped';
COMMENT ON COLUMN services.response_time IS 'Last recorded response time in milliseconds';
COMMENT ON COLUMN services.uptime IS 'Uptime percentage (0-100)';
COMMENT ON COLUMN services.dependencies IS 'JSON array of service names this service depends on';
COMMENT ON COLUMN services.environment IS 'JSON object of environment-specific configuration';
COMMENT ON COLUMN services.recent_events IS 'JSON array of last 10 health check events';
COMMENT ON COLUMN service_events.event_type IS 'Event type: error/warning/info/status_change';
