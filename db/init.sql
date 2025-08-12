-- Complete AI-Powered Game Testing Database Schema
-- Supports intelligent gameplay, knowledge sharing, and real-time learning

-- Create database extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Games table (represents unique games by package_name, each game can have multiple versions)
CREATE TABLE games (
    game_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    package_name VARCHAR(255) NOT NULL UNIQUE,
    game_name VARCHAR(255) NOT NULL,
    icon_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_versions INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    total_bugs_found INTEGER DEFAULT 0,
    
    -- AI Intelligence & Knowledge Sharing
    shared_knowledge JSONB DEFAULT '{}'::jsonb,
    ai_learned_patterns JSONB DEFAULT '{}'::jsonb,
    version_history JSONB DEFAULT '[]',
    ai_analysis_summary JSONB,
    testing_completeness_score FLOAT DEFAULT 0.0,
    max_level_discovered INTEGER DEFAULT 0,
    game_mechanics_learned JSONB DEFAULT '{}'::jsonb,
    ui_patterns_learned JSONB DEFAULT '{}'::jsonb
);

-- Game versions table (each version of a game)
CREATE TABLE game_versions (
    version_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    version VARCHAR(100) NOT NULL,
    version_code INTEGER DEFAULT 1,
    build_number VARCHAR(50),
    release_date TIMESTAMP,
    apk_path VARCHAR(500),
    apk_size BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- AI Learning Progress for this version
    ai_progress_data JSONB DEFAULT '{}'::jsonb,
    levels_explored JSONB DEFAULT '[]'::jsonb,
    mechanics_discovered JSONB DEFAULT '{}'::jsonb,
    optimal_strategies JSONB DEFAULT '{}'::jsonb,
    bug_patterns JSONB DEFAULT '{}'::jsonb,
    
    UNIQUE(game_id, version)
);

-- Sessions table (each testing session)
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    version_id UUID REFERENCES game_versions(version_id) ON DELETE CASCADE,
    
    -- Session basics
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Game progress tracking
    max_level_reached INTEGER DEFAULT 0,
    max_score BIGINT DEFAULT 0,
    total_actions INTEGER DEFAULT 0,
    total_bugs_found INTEGER DEFAULT 0,
    
    -- AI Intelligence tracking
    ai_actions_count INTEGER DEFAULT 0,
    ai_api_calls_count INTEGER DEFAULT 0,
    knowledge_learned_count INTEGER DEFAULT 0,
    ai_performance_score FLOAT DEFAULT 0.0,
    learning_efficiency FLOAT DEFAULT 0.0,
    
    -- Knowledge sharing with other sessions
    inherited_knowledge JSONB DEFAULT '{}'::jsonb,
    contributed_knowledge JSONB DEFAULT '{}'::jsonb,
    
    -- AI model tracking
    ai_model_version VARCHAR(50) DEFAULT '1.0',
    
    -- Emulator and environment data
    emulator_data JSONB,
    environment_config JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enhanced bugs table with AI intelligence
CREATE TABLE bugs (
    bug_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    version_id UUID REFERENCES game_versions(version_id) ON DELETE CASCADE,
    
    -- Bug identification
    bug_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    description TEXT,
    screenshot TEXT,
    action_data JSONB,
    location JSONB,
    
    -- AI Detection & Analysis
    ai_detected BOOLEAN DEFAULT FALSE,
    ai_confidence FLOAT DEFAULT 0.0,
    ai_analysis JSONB,
    screenshot_context JSONB,
    fix_suggestions JSONB,
    
    -- Version tracking for bug lifecycle
    introduced_version VARCHAR(50),
    introduced_version_id UUID REFERENCES game_versions(version_id),
    resolved_version VARCHAR(50),
    resolved_version_id UUID REFERENCES game_versions(version_id),
    
    -- Bug lifecycle
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'open',
    priority INTEGER DEFAULT 3, -- 1=highest, 5=lowest
    
    -- Cross-session learning
    similar_bugs_found JSONB DEFAULT '[]'::jsonb,
    pattern_signature VARCHAR(255), -- For matching similar bugs across sessions
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI Game Knowledge Base (shared learning across sessions)
CREATE TABLE game_knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    knowledge_type VARCHAR(100) NOT NULL, -- 'ui_pattern', 'game_mechanic', 'bug_pattern', 'strategy', 'level_progression'
    knowledge_data JSONB NOT NULL,
    confidence_score FLOAT DEFAULT 0.0,
    source_sessions UUID[] DEFAULT '{}', -- Array of session IDs that contributed
    learning_count INTEGER DEFAULT 1, -- How many times this was learned
    success_rate FLOAT DEFAULT 0.0, -- Success rate when applied
    last_validated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applicable_versions VARCHAR[] DEFAULT '{}', -- Which versions this applies to
    
    -- Performance tracking
    times_applied INTEGER DEFAULT 0,
    successful_applications INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI Analysis Results (detailed AI decision tracking)
CREATE TABLE ai_analysis_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    screenshot_id VARCHAR(255),
    analysis_type VARCHAR(100) NOT NULL, -- 'gpt4_vision', 'game_state', 'bug_detection', 'strategy_planning'
    analysis_data JSONB NOT NULL,
    confidence_score FLOAT DEFAULT 0.0,
    processing_time_ms INTEGER DEFAULT 0,
    api_used VARCHAR(100), -- 'openai', 'anthropic', 'gemini', 'local'
    tokens_used INTEGER DEFAULT 0,
    cost_estimate DECIMAL(10,6) DEFAULT 0.0,
    
    -- Context and learning
    game_context JSONB, -- Current game state when analysis was done
    learned_patterns JSONB, -- What new patterns were discovered
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI Action Recommendations (intelligent gameplay decisions)
CREATE TABLE ai_action_recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    analysis_id UUID REFERENCES ai_analysis_results(id),
    
    action_type VARCHAR(100) NOT NULL, -- 'tap', 'swipe', 'drag', 'wait', 'explore', 'retry'
    action_parameters JSONB NOT NULL,
    reasoning TEXT,
    confidence_score FLOAT DEFAULT 0.0,
    priority VARCHAR(20) DEFAULT 'medium', -- 'high', 'medium', 'low'
    
    -- Execution tracking
    executed BOOLEAN DEFAULT FALSE,
    execution_result JSONB,
    execution_time TIMESTAMP,
    success BOOLEAN,
    
    -- Learning from execution
    outcome_analysis JSONB,
    knowledge_gained JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Telemetry table (real-time game performance data)
CREATE TABLE telemetry (
    telemetry_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fps REAL,
    memory_usage REAL,
    cpu_usage REAL,
    current_level INTEGER,
    score BIGINT,
    
    -- Enhanced game state tracking
    game_state JSONB, -- Complete game state snapshot
    ui_elements JSONB, -- Detected UI elements
    player_position JSONB, -- Player position if applicable
    
    -- AI decision context
    ai_action_taken JSONB, -- What AI action was taken at this moment
    ai_reasoning TEXT, -- Why AI took this action
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Real-time session synchronization
CREATE TABLE session_sync (
    sync_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    sync_type VARCHAR(50) NOT NULL, -- 'knowledge_update', 'bug_discovery', 'strategy_update'
    sync_data JSONB NOT NULL,
    source_session_id UUID REFERENCES sessions(session_id),
    target_sessions UUID[] DEFAULT '{}', -- Which sessions should receive this update
    
    -- Synchronization status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'synced', 'failed'
    synced_count INTEGER DEFAULT 0,
    total_targets INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP
);

-- Analytics for AI performance tracking
CREATE TABLE analytics_ai_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    version VARCHAR(100),
    metric_type VARCHAR(100) NOT NULL, -- 'ai_accuracy', 'bug_detection_rate', 'action_success_rate', 'learning_speed'
    metric_value FLOAT NOT NULL,
    session_count INTEGER DEFAULT 1,
    date_recorded DATE DEFAULT CURRENT_DATE,
    metadata JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI Performance monitoring
CREATE TABLE ai_performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operation_type VARCHAR(100) NOT NULL, -- 'screen_analysis', 'action_recommendation', 'bug_detection', 'knowledge_sync'
    api_provider VARCHAR(50), -- 'openai', 'anthropic', 'local', etc.
    response_time_ms INTEGER NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    cost_estimate DECIMAL(10,6) DEFAULT 0.0,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- Context
    game_id UUID REFERENCES games(game_id),
    session_id UUID REFERENCES sessions(session_id),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Activity log for debugging and monitoring
CREATE TABLE activities (
    activity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    game_id UUID REFERENCES games(game_id),
    session_id UUID REFERENCES sessions(session_id),
    data JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create comprehensive indexes for performance
CREATE INDEX idx_games_package_name ON games(package_name);
CREATE INDEX idx_game_versions_game_version ON game_versions(game_id, version);
CREATE INDEX idx_sessions_game_status ON sessions(game_id, status);
CREATE INDEX idx_sessions_start_time ON sessions(start_time DESC);
CREATE INDEX idx_bugs_session_discovered ON bugs(session_id, discovered_at DESC);
CREATE INDEX idx_bugs_game_type_severity ON bugs(game_id, bug_type, severity);
CREATE INDEX idx_bugs_pattern_signature ON bugs(pattern_signature);
CREATE INDEX idx_telemetry_session_timestamp ON telemetry(session_id, timestamp DESC);
CREATE INDEX idx_activities_timestamp ON activities(timestamp DESC);
CREATE INDEX idx_activities_game_type ON activities(game_id, type);

-- AI-specific indexes
CREATE INDEX idx_knowledge_base_game_type ON game_knowledge_base(game_id, knowledge_type);
CREATE INDEX idx_knowledge_base_confidence ON game_knowledge_base(confidence_score DESC);
CREATE INDEX idx_ai_analysis_session_time ON ai_analysis_results(session_id, created_at DESC);
CREATE INDEX idx_ai_analysis_game_type ON ai_analysis_results(game_id, analysis_type);
CREATE INDEX idx_ai_actions_session_created ON ai_action_recommendations(session_id, created_at);
CREATE INDEX idx_ai_actions_executed ON ai_action_recommendations(executed, success);
CREATE INDEX idx_session_sync_game_status ON session_sync(game_id, status);
CREATE INDEX idx_session_sync_created ON session_sync(created_at DESC);
CREATE INDEX idx_ai_metrics_game_date ON analytics_ai_metrics(game_id, date_recorded DESC);
CREATE INDEX idx_ai_performance_operation ON ai_performance_metrics(operation_type, created_at);

-- Advanced analytics views for AI insights
CREATE OR REPLACE VIEW ai_testing_dashboard AS
SELECT 
    g.game_id,
    g.game_name,
    gv.version,
    COUNT(DISTINCT s.session_id) as total_sessions,
    COUNT(DISTINCT aar.id) as ai_actions_taken,
    COUNT(DISTINCT b.bug_id) as bugs_found,
    COUNT(DISTINCT CASE WHEN b.ai_detected = TRUE THEN b.bug_id END) as ai_detected_bugs,
    AVG(s.ai_performance_score) as avg_ai_performance,
    AVG(g.testing_completeness_score) as testing_completeness,
    MAX(s.max_level_reached) as highest_level_reached,
    MAX(s.end_time) as last_tested,
    
    -- Knowledge sharing metrics
    (SELECT COUNT(*) FROM game_knowledge_base kb WHERE kb.game_id = g.game_id) as knowledge_entries,
    (SELECT AVG(confidence_score) FROM game_knowledge_base kb WHERE kb.game_id = g.game_id) as avg_knowledge_confidence
FROM games g
LEFT JOIN game_versions gv ON g.game_id = gv.game_id
LEFT JOIN sessions s ON g.game_id = s.game_id AND s.version_id = gv.version_id
LEFT JOIN ai_action_recommendations aar ON s.session_id = aar.session_id
LEFT JOIN bugs b ON s.session_id = b.session_id
GROUP BY g.game_id, g.game_name, gv.version;

CREATE OR REPLACE VIEW session_learning_progress AS
SELECT 
    s.session_id,
    s.game_id,
    g.game_name,
    s.max_level_reached,
    s.ai_performance_score,
    s.knowledge_learned_count,
    s.total_bugs_found,
    s.duration_seconds,
    
    -- Learning efficiency metrics
    CASE 
        WHEN s.duration_seconds > 0 THEN s.knowledge_learned_count::FLOAT / (s.duration_seconds / 3600.0)
        ELSE 0 
    END as knowledge_per_hour,
    
    CASE 
        WHEN s.ai_actions_count > 0 THEN s.total_bugs_found::FLOAT / s.ai_actions_count
        ELSE 0 
    END as bugs_per_action,
    
    -- Knowledge inheritance
    jsonb_array_length(COALESCE(s.inherited_knowledge, '[]'::jsonb)) as inherited_knowledge_count,
    jsonb_array_length(COALESCE(s.contributed_knowledge, '[]'::jsonb)) as contributed_knowledge_count
FROM sessions s
JOIN games g ON s.game_id = g.game_id
WHERE s.status = 'completed';

-- Functions for AI knowledge management

-- Function to automatically update knowledge confidence based on success rate
CREATE OR REPLACE FUNCTION update_knowledge_confidence()
RETURNS TRIGGER AS $$
BEGIN
    -- Update confidence based on success rate, learning count, and recent performance
    NEW.confidence_score = LEAST(1.0, 
        (NEW.success_rate * 0.6) + 
        (LEAST(NEW.learning_count, 20) * 0.02) + 
        (CASE WHEN NEW.last_validated > CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 0.2 ELSE 0 END)
    );
    NEW.updated_at = CURRENT_TIMESTAMP;
    
    -- Update success rate based on applications
    IF NEW.times_applied > 0 THEN
        NEW.success_rate = NEW.successful_applications::FLOAT / NEW.times_applied;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_knowledge_confidence
    BEFORE UPDATE ON game_knowledge_base
    FOR EACH ROW
    EXECUTE FUNCTION update_knowledge_confidence();

-- Function to sync knowledge across active sessions
CREATE OR REPLACE FUNCTION sync_knowledge_to_sessions(
    p_game_id UUID,
    p_knowledge_type VARCHAR,
    p_knowledge_data JSONB,
    p_source_session_id UUID
)
RETURNS UUID AS $$
DECLARE
    sync_record_id UUID;
    active_sessions UUID[];
BEGIN
    -- Get all active sessions for this game
    SELECT ARRAY_AGG(session_id) INTO active_sessions
    FROM sessions 
    WHERE game_id = p_game_id 
    AND status IN ('running', 'active') 
    AND session_id != p_source_session_id;
    
    -- Create sync record
    INSERT INTO session_sync (
        game_id, 
        sync_type, 
        sync_data, 
        source_session_id, 
        target_sessions,
        total_targets
    ) VALUES (
        p_game_id,
        'knowledge_update',
        jsonb_build_object(
            'type', p_knowledge_type,
            'data', p_knowledge_data
        ),
        p_source_session_id,
        active_sessions,
        array_length(active_sessions, 1)
    ) RETURNING sync_id INTO sync_record_id;
    
    RETURN sync_record_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get inherited knowledge for a new session
CREATE OR REPLACE FUNCTION get_inherited_knowledge(p_game_id UUID, p_version VARCHAR DEFAULT NULL)
RETURNS JSONB AS $$
DECLARE
    inherited_knowledge JSONB;
BEGIN
    SELECT jsonb_agg(
        jsonb_build_object(
            'type', knowledge_type,
            'data', knowledge_data,
            'confidence', confidence_score,
            'success_rate', success_rate
        )
    ) INTO inherited_knowledge
    FROM game_knowledge_base
    WHERE game_id = p_game_id
    AND confidence_score > 0.3  -- Only inherit reasonably confident knowledge
    AND (p_version IS NULL OR p_version = ANY(applicable_versions) OR applicable_versions = '{}')
    ORDER BY confidence_score DESC, success_rate DESC
    LIMIT 50;  -- Limit to top 50 knowledge pieces
    
    RETURN COALESCE(inherited_knowledge, '[]'::jsonb);
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old data but preserve learning
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Clean up old AI analysis data (keep last 30 days)
    DELETE FROM ai_analysis_results WHERE created_at < CURRENT_DATE - INTERVAL '30 days';
    
    -- Clean up old action recommendations (keep last 30 days)
    DELETE FROM ai_action_recommendations WHERE created_at < CURRENT_DATE - INTERVAL '30 days';
    
    -- Clean up old performance metrics (keep last 7 days)
    DELETE FROM ai_performance_metrics WHERE created_at < CURRENT_DATE - INTERVAL '7 days';
    
    -- Clean up old telemetry (keep last 7 days, except for sessions with bugs)
    DELETE FROM telemetry 
    WHERE created_at < CURRENT_DATE - INTERVAL '7 days'
    AND session_id NOT IN (
        SELECT DISTINCT session_id FROM bugs WHERE status = 'open'
    );
    
    -- Clean up completed sync records (keep last 24 hours)
    DELETE FROM session_sync 
    WHERE status = 'synced' 
    AND synced_at < CURRENT_TIMESTAMP - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Game Analysis table - stores detailed AI analysis of games
CREATE TABLE game_analysis (
    analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    category_primary VARCHAR(100),
    category_secondary VARCHAR(100),
    difficulty_score FLOAT DEFAULT 0.0,
    complexity_rating INTEGER DEFAULT 1,
    ui_complexity JSONB DEFAULT '{}'::jsonb,
    gameplay_mechanics JSONB DEFAULT '{}'::jsonb,
    level_progression JSONB DEFAULT '{}'::jsonb,
    monetization_patterns JSONB DEFAULT '{}'::jsonb,
    accessibility_features JSONB DEFAULT '{}'::jsonb,
    performance_metrics JSONB DEFAULT '{}'::jsonb,
    ai_recommendations JSONB DEFAULT '{}'::jsonb,
    analysis_confidence FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Testing Reports table - stores comprehensive test results
CREATE TABLE testing_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    test_duration_seconds INTEGER DEFAULT 0,
    actions_performed INTEGER DEFAULT 0,
    screens_explored INTEGER DEFAULT 0,
    bugs_discovered INTEGER DEFAULT 0,
    crashes_encountered INTEGER DEFAULT 0,
    performance_issues INTEGER DEFAULT 0,
    ui_issues INTEGER DEFAULT 0,
    coverage_percentage FLOAT DEFAULT 0.0,
    final_metrics JSONB DEFAULT '{}'::jsonb,
    ai_insights JSONB DEFAULT '{}'::jsonb,
    test_completeness FLOAT DEFAULT 0.0,
    recommendations JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- AI agent specific columns
    game_understanding JSONB DEFAULT '{}'::jsonb,
    levels_discovered JSONB DEFAULT '[]'::jsonb,
    performance_summary JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Performance summary
    avg_response_time_ms FLOAT DEFAULT 0.0,
    memory_usage_peak_mb FLOAT DEFAULT 0.0,
    cpu_usage_avg_percent FLOAT DEFAULT 0.0,
    
    -- Test quality metrics
    unique_paths_explored INTEGER DEFAULT 0,
    repeated_actions_count INTEGER DEFAULT 0,
    exploration_efficiency FLOAT DEFAULT 0.0
);

-- Create indexes for better performance
CREATE INDEX idx_game_analysis_game_id ON game_analysis(game_id);
CREATE INDEX idx_game_analysis_session_id ON game_analysis(session_id);
CREATE INDEX idx_game_analysis_created_at ON game_analysis(created_at);

CREATE INDEX idx_testing_reports_session_id ON testing_reports(session_id);
CREATE INDEX idx_testing_reports_game_id ON testing_reports(game_id);
CREATE INDEX idx_testing_reports_created_at ON testing_reports(created_at);

-- Additional tables required by AI agent
CREATE TABLE action_patterns (
    pattern_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    action_type VARCHAR(100),
    action_x INTEGER,
    action_y INTEGER,
    outcome VARCHAR(100),
    reward FLOAT,
    screen_change BOOLEAN DEFAULT FALSE,
    confidence FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE performance_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    metric_type VARCHAR(100),
    metric_value FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE successful_actions (
    action_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    action_type VARCHAR(100),
    success_rate FLOAT,
    context JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE enhanced_telemetry (
    telemetry_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    action_type VARCHAR(100),
    screen_analysis JSONB DEFAULT '{}'::jsonb,
    performance_data JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_thoughts (
    thought_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    thought_type VARCHAR(100),
    thought_content TEXT,
    confidence FLOAT DEFAULT 0.0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE enhanced_test_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE UNIQUE,
    game_id UUID REFERENCES games(game_id) ON DELETE CASCADE,
    comprehensive_analysis JSONB DEFAULT '{}'::jsonb,
    performance_summary JSONB DEFAULT '{}'::jsonb,
    bug_analysis JSONB DEFAULT '{}'::jsonb,
    learning_insights JSONB DEFAULT '{}'::jsonb,
    recommendations JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Database schema complete - ready for APK uploads
COMMIT;
