-- PlayMetric Comprehensive Database Schema
-- PostgreSQL 15+ with TimescaleDB for time-series data

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- ============================================================================
-- CORE ENTITIES
-- ============================================================================

-- Games: Master table for all games being tested
CREATE TABLE games (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    package_name VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    genre VARCHAR(100), -- puzzle, action, strategy, etc.
    developer VARCHAR(255),
    description TEXT,
    icon_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_games_package_name ON games(package_name);
CREATE INDEX idx_games_genre ON games(genre);

-- Game Versions: Track different versions of each game
CREATE TABLE game_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    version_code INTEGER NOT NULL,
    version_name VARCHAR(100) NOT NULL,
    apk_path TEXT NOT NULL,
    apk_size_bytes BIGINT,
    apk_hash VARCHAR(64), -- SHA-256 hash
    min_sdk_version INTEGER,
    target_sdk_version INTEGER,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    uploaded_by VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active', -- active, archived, deprecated
    release_notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(game_id, version_code)
);

CREATE INDEX idx_game_versions_game_id ON game_versions(game_id);
CREATE INDEX idx_game_versions_status ON game_versions(status);

-- Sessions: Individual test sessions
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_version_id UUID NOT NULL REFERENCES game_versions(id) ON DELETE CASCADE,
    session_name VARCHAR(255),
    agent_mode VARCHAR(50) NOT NULL, -- random, heuristic, rl
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    target_duration_minutes INTEGER,
    total_actions INTEGER DEFAULT 0,
    total_screenshots INTEGER DEFAULT 0,
    crashes_detected INTEGER DEFAULT 0,
    config JSONB DEFAULT '{}'::jsonb, -- agent config, intervals, etc.
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sessions_game_version_id ON sessions(game_version_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_started_at ON sessions(started_at);

-- ============================================================================
-- BUG TRACKING
-- ============================================================================

-- Bugs: Track all detected issues
CREATE TABLE bugs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_version_id UUID NOT NULL REFERENCES game_versions(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    bug_type VARCHAR(100) NOT NULL, -- crash, anr, freeze, ui_issue, performance
    severity VARCHAR(50) NOT NULL, -- critical, high, medium, low
    title VARCHAR(500) NOT NULL,
    description TEXT,
    stack_trace TEXT,
    logcat_excerpt TEXT,
    screenshot_path TEXT,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'open', -- open, investigating, fixed, wontfix, duplicate
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_in_version UUID REFERENCES game_versions(id),
    resolution_notes TEXT,
    duplicate_of UUID REFERENCES bugs(id),
    reproduction_steps TEXT[],
    tags VARCHAR(100)[],
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_bugs_game_version_id ON bugs(game_version_id);
CREATE INDEX idx_bugs_session_id ON bugs(session_id);
CREATE INDEX idx_bugs_status ON bugs(status);
CREATE INDEX idx_bugs_severity ON bugs(severity);
CREATE INDEX idx_bugs_detected_at ON bugs(detected_at);

-- Bug History: Track bug state changes
CREATE TABLE bug_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bug_id UUID NOT NULL REFERENCES bugs(id) ON DELETE CASCADE,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    changed_by VARCHAR(255),
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    comment TEXT
);

CREATE INDEX idx_bug_history_bug_id ON bug_history(bug_id);

-- ============================================================================
-- REINFORCEMENT LEARNING
-- ============================================================================

-- RL Experiences: Store state-action-reward transitions
CREATE TABLE rl_experiences (
    id BIGSERIAL PRIMARY KEY,
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- State information
    state_features FLOAT[] NOT NULL, -- Encoded game state (screen features, etc.)
    state_hash VARCHAR(64), -- Hash for deduplication
    
    -- Action taken
    action_type VARCHAR(50) NOT NULL, -- tap, swipe_up, swipe_down, etc.
    action_params JSONB, -- x, y, duration, etc.
    
    -- Result
    reward FLOAT NOT NULL,
    next_state_features FLOAT[],
    done BOOLEAN DEFAULT false, -- Episode ended?
    
    -- Metadata
    level_identifier VARCHAR(255), -- Which level/screen this happened in
    difficulty_estimate FLOAT,
    priority FLOAT DEFAULT 1.0, -- For prioritized experience replay
    times_used INTEGER DEFAULT 0, -- How many times used in training
    
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Convert to TimescaleDB hypertable for efficient time-series queries
SELECT create_hypertable('rl_experiences', 'timestamp', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_rl_experiences_game_id ON rl_experiences(game_id);
CREATE INDEX idx_rl_experiences_session_id ON rl_experiences(session_id);
CREATE INDEX idx_rl_experiences_state_hash ON rl_experiences(state_hash);
CREATE INDEX idx_rl_experiences_priority ON rl_experiences(priority DESC);

-- RL Models: Track trained models
CREATE TABLE rl_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID REFERENCES games(id) ON DELETE CASCADE,
    model_name VARCHAR(255) NOT NULL,
    algorithm VARCHAR(100) NOT NULL, -- DQN, PPO, SAC, etc.
    version INTEGER NOT NULL,
    model_path TEXT NOT NULL,
    training_episodes INTEGER,
    training_steps BIGINT,
    average_reward FLOAT,
    best_reward FLOAT,
    hyperparameters JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'active', -- active, archived, deprecated
    performance_metrics JSONB DEFAULT '{}'::jsonb,
    UNIQUE(game_id, model_name, version)
);

CREATE INDEX idx_rl_models_game_id ON rl_models(game_id);
CREATE INDEX idx_rl_models_status ON rl_models(status);

-- Shared Knowledge: Cross-game learning insights
CREATE TABLE shared_knowledge (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_type VARCHAR(100) NOT NULL, -- ui_pattern, bug_pattern, strategy, etc.
    applicable_genres VARCHAR(100)[], -- Which game genres this applies to
    title VARCHAR(255) NOT NULL,
    description TEXT,
    pattern_data JSONB NOT NULL, -- The actual pattern/insight
    confidence_score FLOAT DEFAULT 0.5, -- 0-1, how reliable is this
    times_applied INTEGER DEFAULT 0,
    success_rate FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_sessions UUID[] DEFAULT ARRAY[]::UUID[], -- Which sessions contributed
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_shared_knowledge_type ON shared_knowledge(knowledge_type);
CREATE INDEX idx_shared_knowledge_genres ON shared_knowledge USING GIN(applicable_genres);

-- ============================================================================
-- ANALYTICS & METRICS
-- ============================================================================

-- Session Metrics: Time-series metrics per session
CREATE TABLE session_metrics (
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Performance metrics
    fps FLOAT,
    memory_usage_mb FLOAT,
    cpu_usage_percent FLOAT,
    battery_drain_percent FLOAT,
    
    -- Gameplay metrics
    current_level VARCHAR(255),
    score INTEGER,
    actions_per_minute FLOAT,
    progress_percentage FLOAT,
    
    -- AI metrics
    exploration_rate FLOAT, -- epsilon in epsilon-greedy
    average_reward FLOAT,
    q_value_estimate FLOAT,
    
    metadata JSONB DEFAULT '{}'::jsonb,
    PRIMARY KEY (session_id, timestamp)
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('session_metrics', 'timestamp',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

CREATE INDEX idx_session_metrics_session_id ON session_metrics(session_id);

-- Difficulty Analysis: Per-level difficulty scores
CREATE TABLE difficulty_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    level_identifier VARCHAR(255) NOT NULL,
    difficulty_score FLOAT NOT NULL, -- 0-1
    attempts_count INTEGER DEFAULT 1,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    average_time_seconds FLOAT,
    fastest_completion_seconds FLOAT,
    completion_rate FLOAT,
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    factors JSONB DEFAULT '{}'::jsonb, -- What contributes to difficulty
    UNIQUE(session_id, level_identifier)
);

CREATE INDEX idx_difficulty_analysis_session_id ON difficulty_analysis(session_id);
CREATE INDEX idx_difficulty_analysis_difficulty_score ON difficulty_analysis(difficulty_score DESC);

-- Retention Analysis: Estimated retention metrics
CREATE TABLE retention_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_version_id UUID NOT NULL REFERENCES game_versions(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    
    -- Retention estimates
    day1_retention_estimate FLOAT,
    day7_retention_estimate FLOAT,
    day30_retention_estimate FLOAT,
    
    -- Engagement metrics
    engagement_score FLOAT, -- 0-1
    session_length_score FLOAT,
    progression_score FLOAT,
    
    -- Churn risks
    churn_risk_score FLOAT, -- 0-1, higher = more risk
    churn_factors VARCHAR(100)[],
    
    -- Recommendations
    recommendations TEXT[],
    
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analysis_basis JSONB DEFAULT '{}'::jsonb -- What data this was based on
);

CREATE INDEX idx_retention_analysis_game_version_id ON retention_analysis(game_version_id);
CREATE INDEX idx_retention_analysis_session_id ON retention_analysis(session_id);

-- Screenshots: Track all captured screenshots
CREATE TABLE screenshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    captured_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    width INTEGER,
    height INTEGER,
    file_size_bytes INTEGER,
    screen_hash VARCHAR(64), -- For detecting duplicate/similar screens
    
    -- Extracted information
    detected_ui_elements JSONB, -- Buttons, text, etc.
    detected_level VARCHAR(255),
    ocr_text TEXT,
    
    -- Features for RL
    feature_vector FLOAT[], -- Extracted features for ML
    
    -- Annotations
    is_crash BOOLEAN DEFAULT false,
    is_level_complete BOOLEAN DEFAULT false,
    is_game_over BOOLEAN DEFAULT false,
    tags VARCHAR(100)[],
    
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('screenshots', 'captured_at',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_screenshots_session_id ON screenshots(session_id);
CREATE INDEX idx_screenshots_screen_hash ON screenshots(screen_hash);

-- Actions: Record all actions taken
CREATE TABLE actions (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    action_type VARCHAR(50) NOT NULL,
    action_params JSONB,
    
    -- Context
    screenshot_before UUID REFERENCES screenshots(id),
    screenshot_after UUID REFERENCES screenshots(id),
    
    -- Result
    success BOOLEAN,
    error_message TEXT,
    
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('actions', 'executed_at',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_actions_session_id ON actions(session_id);

-- ============================================================================
-- VERSION COMPARISON & REPORTING
-- ============================================================================

-- Version Comparisons: Compare metrics between versions
CREATE TABLE version_comparisons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    base_version_id UUID NOT NULL REFERENCES game_versions(id) ON DELETE CASCADE,
    compare_version_id UUID NOT NULL REFERENCES game_versions(id) ON DELETE CASCADE,
    compared_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Bug comparison
    bugs_fixed_count INTEGER DEFAULT 0,
    bugs_introduced_count INTEGER DEFAULT 0,
    regression_bugs_count INTEGER DEFAULT 0,
    
    -- Performance comparison
    performance_change_percent FLOAT,
    crash_rate_change_percent FLOAT,
    
    -- Difficulty comparison
    difficulty_change_percent FLOAT,
    levels_easier INTEGER DEFAULT 0,
    levels_harder INTEGER DEFAULT 0,
    
    -- Retention comparison
    retention_change_percent FLOAT,
    
    -- Detailed differences
    detailed_diff JSONB DEFAULT '{}'::jsonb,
    
    -- Report
    summary TEXT,
    recommendations TEXT[],
    
    UNIQUE(base_version_id, compare_version_id)
);

CREATE INDEX idx_version_comparisons_base_version ON version_comparisons(base_version_id);
CREATE INDEX idx_version_comparisons_compare_version ON version_comparisons(compare_version_id);

-- ============================================================================
-- SYSTEM & AUDIT
-- ============================================================================

-- Audit Log: Track all important system events
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    event_type VARCHAR(100) NOT NULL, -- session_started, bug_detected, model_trained, etc.
    entity_type VARCHAR(100), -- game, session, bug, etc.
    entity_id UUID,
    user_id VARCHAR(255),
    details JSONB DEFAULT '{}'::jsonb,
    ip_address INET
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('audit_log', 'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX idx_audit_log_entity_type_id ON audit_log(entity_type, entity_id);

-- System Config: Store system-wide configuration
CREATE TABLE system_config (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(255)
);

-- ============================================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- ============================================================================

-- Game statistics summary
CREATE MATERIALIZED VIEW game_statistics AS
SELECT 
    g.id AS game_id,
    g.package_name,
    g.display_name,
    COUNT(DISTINCT gv.id) AS total_versions,
    COUNT(DISTINCT s.id) AS total_sessions,
    COUNT(DISTINCT CASE WHEN s.status = 'completed' THEN s.id END) AS completed_sessions,
    SUM(s.total_actions) AS total_actions,
    COUNT(DISTINCT b.id) AS total_bugs,
    COUNT(DISTINCT CASE WHEN b.status = 'open' THEN b.id END) AS open_bugs,
    MAX(s.started_at) AS last_tested_at,
    AVG(CASE WHEN s.status = 'completed' THEN s.duration_seconds END) AS avg_session_duration
FROM games g
LEFT JOIN game_versions gv ON g.id = gv.game_id
LEFT JOIN sessions s ON gv.id = s.game_version_id
LEFT JOIN bugs b ON gv.id = b.game_version_id
GROUP BY g.id, g.package_name, g.display_name;

CREATE UNIQUE INDEX idx_game_statistics_game_id ON game_statistics(game_id);

-- Version statistics summary
CREATE MATERIALIZED VIEW version_statistics AS
SELECT 
    gv.id AS version_id,
    gv.game_id,
    gv.version_name,
    COUNT(DISTINCT s.id) AS total_sessions,
    COUNT(DISTINCT CASE WHEN s.status = 'completed' THEN s.id END) AS completed_sessions,
    COUNT(DISTINCT b.id) AS total_bugs,
    COUNT(DISTINCT CASE WHEN b.status = 'open' THEN b.id END) AS open_bugs,
    COUNT(DISTINCT CASE WHEN b.severity = 'critical' THEN b.id END) AS critical_bugs,
    AVG(CASE WHEN s.status = 'completed' THEN s.duration_seconds END) AS avg_session_duration,
    SUM(s.crashes_detected) AS total_crashes,
    MAX(s.started_at) AS last_tested_at
FROM game_versions gv
LEFT JOIN sessions s ON gv.id = s.game_version_id
LEFT JOIN bugs b ON gv.id = b.game_version_id
GROUP BY gv.id, gv.game_id, gv.version_name;

CREATE UNIQUE INDEX idx_version_statistics_version_id ON version_statistics(version_id);

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

-- Apply trigger to relevant tables
CREATE TRIGGER update_games_updated_at BEFORE UPDATE ON games
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_shared_knowledge_updated_at BEFORE UPDATE ON shared_knowledge
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically create bug history entry
CREATE OR REPLACE FUNCTION log_bug_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO bug_history (bug_id, field_name, old_value, new_value)
        VALUES (NEW.id, 'status', OLD.status, NEW.status);
    END IF;
    
    IF OLD.resolved_at IS DISTINCT FROM NEW.resolved_at THEN
        INSERT INTO bug_history (bug_id, field_name, old_value, new_value)
        VALUES (NEW.id, 'resolved_at', 
                OLD.resolved_at::TEXT, 
                NEW.resolved_at::TEXT);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER track_bug_changes AFTER UPDATE ON bugs
    FOR EACH ROW EXECUTE FUNCTION log_bug_changes();

-- Function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_statistics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY game_statistics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY version_statistics;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Default system configuration
INSERT INTO system_config (key, value, description) VALUES
('max_concurrent_sessions', '10', 'Maximum number of parallel test sessions'),
('screenshot_retention_days', '30', 'Days to keep screenshots before cleanup'),
('rl_experience_retention_days', '90', 'Days to keep RL experiences'),
('min_experiences_for_training', '1000', 'Minimum experiences before RL training'),
('default_agent_mode', '"heuristic"', 'Default agent mode for new sessions'),
('enable_cross_game_learning', 'true', 'Enable shared knowledge across games')
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Active sessions view
CREATE VIEW active_sessions_view AS
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
CREATE VIEW recent_bugs_view AS
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

-- RL training readiness view
CREATE VIEW rl_training_readiness AS
SELECT 
    g.id AS game_id,
    g.package_name,
    g.display_name,
    COUNT(e.id) AS total_experiences,
    COUNT(DISTINCT e.session_id) AS contributing_sessions,
    MIN(e.timestamp) AS oldest_experience,
    MAX(e.timestamp) AS newest_experience,
    AVG(e.reward) AS average_reward,
    MAX(m.version) AS current_model_version,
    CASE 
        WHEN COUNT(e.id) >= (SELECT value::int FROM system_config WHERE key = 'min_experiences_for_training')
        THEN true
        ELSE false
    END AS ready_for_training
FROM games g
LEFT JOIN rl_experiences e ON g.id = e.game_id
LEFT JOIN rl_models m ON g.id = m.game_id AND m.status = 'active'
GROUP BY g.id, g.package_name, g.display_name;

-- Version comparison summary view
CREATE VIEW version_comparison_summary AS
SELECT 
    g.display_name AS game_name,
    base_v.version_name AS base_version,
    comp_v.version_name AS compare_version,
    vc.bugs_fixed_count,
    vc.bugs_introduced_count,
    vc.regression_bugs_count,
    vc.performance_change_percent,
    vc.crash_rate_change_percent,
    vc.retention_change_percent,
    vc.compared_at
FROM version_comparisons vc
JOIN game_versions base_v ON vc.base_version_id = base_v.id
JOIN game_versions comp_v ON vc.compare_version_id = comp_v.id
JOIN games g ON base_v.game_id = g.id
ORDER BY vc.compared_at DESC;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE games IS 'Master table for all games being tested';
COMMENT ON TABLE game_versions IS 'Tracks different versions of each game with APK metadata';
COMMENT ON TABLE sessions IS 'Individual test sessions with status and metrics';
COMMENT ON TABLE bugs IS 'All detected bugs with tracking and resolution status';
COMMENT ON TABLE rl_experiences IS 'State-action-reward transitions for reinforcement learning';
COMMENT ON TABLE rl_models IS 'Trained RL models with versioning and performance metrics';
COMMENT ON TABLE shared_knowledge IS 'Cross-game learning insights and patterns';
COMMENT ON TABLE session_metrics IS 'Time-series performance and gameplay metrics';
COMMENT ON TABLE screenshots IS 'All captured screenshots with extracted features';
COMMENT ON TABLE actions IS 'All actions taken during sessions';
COMMENT ON TABLE version_comparisons IS 'Comparison reports between game versions';

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Additional performance indexes
CREATE INDEX idx_sessions_game_version_status ON sessions(game_version_id, status);
CREATE INDEX idx_bugs_game_version_status_severity ON bugs(game_version_id, status, severity);
CREATE INDEX idx_rl_experiences_game_timestamp ON rl_experiences(game_id, timestamp DESC);

-- GIN indexes for JSONB columns
CREATE INDEX idx_games_metadata ON games USING GIN(metadata);
CREATE INDEX idx_sessions_config ON sessions USING GIN(config);
CREATE INDEX idx_rl_experiences_metadata ON rl_experiences USING GIN(metadata);
CREATE INDEX idx_shared_knowledge_pattern_data ON shared_knowledge USING GIN(pattern_data);

-- ============================================================================
-- CLEANUP POLICIES
-- ============================================================================

-- TimescaleDB retention policies (optional - uncomment if needed)
-- Keep screenshot data for 30 days
-- SELECT add_retention_policy('screenshots', INTERVAL '30 days');

-- Keep RL experiences for 90 days
-- SELECT add_retention_policy('rl_experiences', INTERVAL '90 days');

-- Keep audit log for 180 days
-- SELECT add_retention_policy('audit_log', INTERVAL '180 days');

-- ============================================================================
-- GRANTS (adjust based on your security requirements)
-- ============================================================================

-- Create roles for different access levels
-- CREATE ROLE playmetric_admin;
-- CREATE ROLE playmetric_service;
-- CREATE ROLE playmetric_readonly;

-- GRANT ALL ON ALL TABLES IN SCHEMA public TO playmetric_admin;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO playmetric_service;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO playmetric_readonly;

-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO playmetric_admin;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO playmetric_service;

