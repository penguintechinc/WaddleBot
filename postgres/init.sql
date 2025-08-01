-- WaddleBot Development Database Initialization
-- This script sets up the basic database structure for development

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas for different modules
CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS portal;
CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS router;

-- Set default search path
ALTER DATABASE waddlebot SET search_path TO public, portal, identity, router;

-- Create a development user with appropriate permissions
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'waddlebot_dev') THEN
        CREATE ROLE waddlebot_dev WITH LOGIN PASSWORD 'dev123';
    END IF;
END
$$;

-- Grant permissions
GRANT CONNECT ON DATABASE waddlebot TO waddlebot_dev;
GRANT USAGE ON SCHEMA public, portal, identity, router TO waddlebot_dev;
GRANT CREATE ON SCHEMA public, portal, identity, router TO waddlebot_dev;

-- Create indexes for common query patterns
-- These will be created by py4web/pydal as needed, but we can prepare some common ones

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Insert some development data (optional)
-- This would be handled by the application initialization

-- Log the initialization
INSERT INTO pg_stat_statements_info (dealloc) VALUES (0) ON CONFLICT DO NOTHING;

-- Development notice
DO $$
BEGIN
    RAISE NOTICE 'WaddleBot development database initialized successfully';
    RAISE NOTICE 'Database: waddlebot';
    RAISE NOTICE 'Main user: waddlebot / waddlebot123';
    RAISE NOTICE 'Dev user: waddlebot_dev / dev123';
END
$$;