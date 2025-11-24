-- PlayMetric Database Schema for Railway PostgreSQL (without TimescaleDB)
-- PostgreSQL 15+ compatible

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CORE ENTITIES
-- ============================================================================

-- Games
CREATE TABLE IF NOT EXISTS games (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    package_name VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    genre VARCHAR(100),
    developer VARCHAR(255),
    description TEXT,
    icon_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_games_package_name ON games(package_name);
CREATE INDEX IF NOT EXISTS idx_games_genre ON games(genre);

-- Game Versions
CREATE TABLE IF NOT EXISTS game_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    version_code INTEGER NOT NULL,
    version_name VARCHAR(100) NOT NULL,
    apk_path TEXT NOT NULL,
    apk_size_bytes BIGINT,
    apk_hash VARCHAR(64),
    min_sdk_version INTEGER,
    target_sdk_version INTEGER,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    uploaded_by VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    release_notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(game_id, version_code)
);

CREATE INDEX IF NOT EXISTS idx_game_versions_game_id ON game_versions(game_id);
CREATE INDEX IF NOT EXISTS idx_game_versions_status ON game_versions(status);

-- Sessions
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_version_id UUID NOT NULL REFERENCES game_versions(id) ON DELETE CASCADE,
    session_name VARCHAR(255),
    agent_mode VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    target_duration_minutes INTEGER,
    total_actions INTEGER DEFAULT 0,
    total_screenshots INTEGER DEFAULT 0,
    crashes_detected INTEGER DEFAULT 0,
    config JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_game_version_id ON sessions(game_version_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at);

-- ============================================================================
-- BUG TRACKING
-- ============================================================================

-- Bugs
CREATE TABLE IF NOT EXISTS bugs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_version_id UUID NOT NULL REFERENCES game_versions(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    bug_type VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    stack_trace TEXT,
    logcat_excerpt TEXT,
    screenshot_path TEXT,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'open',
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_in_version UUID REFERENCES game_versions(id),
    resolution_notes TEXT,
    duplicate_of UUID REFERENCES bugs(id),
    reproduction_steps TEXT[],
    tags VARCHAR(100)[],
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_bugs_game_version_id ON bugs(game_version_id);
CREATE INDEX IF NOT EXISTS idx_bugs_session_id ON bugs(session_id);
CREATE INDEX IF NOT EXISTS idx_bugs_status ON bugs(status);
CREATE INDEX IF NOT EXISTS idx_bugs_severity ON bugs(severity);
CREATE INDEX IF NOT EXISTS idx_bugs_detected_at ON bugs(detected_at);

-- Bug History
CREATE TABLE IF NOT EXISTS bug_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bug_id UUID NOT NULL REFERENCES bugs(id) ON DELETE CASCADE,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    changed_by VARCHAR(255),
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    comment TEXT
);

CREATE INDEX IF NOT EXISTS idx_bug_history_bug_id ON bug_history(bug_id);

-- System Config
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(255)
);

-- Initial system configuration
INSERT INTO system_config (key, value, description) VALUES
('max_concurrent_sessions', '10', 'Maximum number of parallel test sessions'),
('screenshot_retention_days', '30', 'Days to keep screenshots before cleanup'),
('default_agent_mode', '"heuristic"', 'Default agent mode for new sessions'),
('enable_cross_game_learning', 'true', 'Enable shared knowledge across games'),
('demo_video_url', 'null', 'URL of the investor demo video')
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger
CREATE OR REPLACE TRIGGER update_games_updated_at BEFORE UPDATE ON games
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically create bug history entry
CREATE OR REPLACE FUNCTION log_bug_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO bug_history (bug_id, field_name, old_value, new_value)
        VALUES (NEW.id, 'status', OLD.status, NEW.status);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER track_bug_changes AFTER UPDATE ON bugs
    FOR EACH ROW EXECUTE FUNCTION log_bug_changes();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Active sessions view
CREATE OR REPLACE VIEW active_sessions_view AS
SELECT 
    s.id,
    s.session_name,
    g.display_name AS game_name,
    gv.version_name,
    s.agent_mode,
    s.status,
    s.started_at,
    EXTRACT(EPOCH FROM (NOW() - s.started_at)) AS running_seconds,
    s.total_actions,
    s.total_screenshots,
    s.crashes_detected
FROM sessions s
JOIN game_versions gv ON s.game_version_id = gv.id
JOIN games g ON gv.game_id = g.id
WHERE s.status IN ('pending', 'running')
ORDER BY s.started_at DESC;

-- Recent bugs view
CREATE OR REPLACE VIEW recent_bugs_view AS
SELECT 
    b.id,
    b.title,
    b.bug_type,
    b.severity,
    b.status,
    g.display_name AS game_name,
    gv.version_name,
    b.detected_at,
    b.resolved_at
FROM bugs b
JOIN game_versions gv ON b.game_version_id = gv.id
JOIN games g ON gv.game_id = g.id
WHERE b.detected_at > NOW() - INTERVAL '30 days'
ORDER BY b.detected_at DESC;
