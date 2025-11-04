-- Migration: Initial Schema v1.0
-- Created: 2025-10-23
-- Description: Creates complete PlayMetric database schema

\echo 'Starting PlayMetric database migration v1.0...'

-- Start transaction
BEGIN;

-- Source the main schema
\i schema.sql

-- Verify tables were created
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE';
    
    RAISE NOTICE 'Created % tables', table_count;
    
    IF table_count < 15 THEN
        RAISE EXCEPTION 'Expected at least 15 tables, only found %', table_count;
    END IF;
END $$;

-- Verify TimescaleDB hypertables
DO $$
DECLARE
    hypertable_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO hypertable_count
    FROM timescaledb_information.hypertables
    WHERE schema_name = 'public';
    
    RAISE NOTICE 'Created % TimescaleDB hypertables', hypertable_count;
END $$;

-- Create version tracking table for migrations
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    description TEXT
);

-- Record this migration
INSERT INTO schema_migrations (version, description)
VALUES ('1.0', 'Initial schema with games, sessions, bugs, RL, analytics');

COMMIT;

\echo 'Migration completed successfully!'
\echo 'Run: SELECT * FROM schema_migrations; to see applied migrations'
