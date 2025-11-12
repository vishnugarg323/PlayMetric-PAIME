-- Migration: Add learning tables for user observations and AI decisions
-- Created: 2025-11-11
-- Purpose: Store meaningful learning data from both user gameplay and AI auto-play

-- ============================================
-- USER OBSERVATIONS TABLE
-- Stores what AI learned from watching user play
-- ============================================
CREATE TABLE IF NOT EXISTS user_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    game_id UUID NOT NULL,
    
    -- Timing
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sequence_number INTEGER NOT NULL, -- Order of actions in session
    
    -- Screen State (What AI saw)
    screenshot_path TEXT,
    screen_analysis JSONB, -- OCR text, UI elements detected, screen type
    
    -- User Action (What user did)
    user_action JSONB NOT NULL, -- {type: 'tap'|'swipe', coordinates, direction, etc}
    
    -- AI Analysis (What AI understood)
    ai_interpretation TEXT, -- Human-readable description
    detected_ui_element TEXT, -- What UI element was interacted with
    inferred_intent TEXT, -- What AI thinks user was trying to do
    
    -- Outcome & Learning
    outcome JSONB, -- {screen_changed: bool, new_screen_type: str, reward_signal: float}
    learned_pattern JSONB, -- Extracted pattern for future use
    confidence_score FLOAT DEFAULT 0.5, -- How confident AI is about this interpretation
    
    -- Metadata
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_obs_session ON user_observations(session_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_user_obs_game ON user_observations(game_id);
CREATE INDEX IF NOT EXISTS idx_user_obs_timestamp ON user_observations(timestamp DESC);

-- ============================================
-- AI DECISIONS TABLE
-- Stores AI's decision-making process during auto-play
-- ============================================
CREATE TABLE IF NOT EXISTS ai_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    game_id UUID NOT NULL,
    
    -- Timing
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sequence_number INTEGER NOT NULL,
    
    -- Current State (What AI sees)
    screenshot_path TEXT,
    screen_analysis JSONB, -- OCR, UI elements, current game state
    
    -- AI Decision Process
    available_actions JSONB, -- All possible actions AI could take
    reasoning TEXT NOT NULL, -- Why AI chose this action (GPT/LLM reasoning)
    decision_factors JSONB, -- {user_demo_influenced: bool, prior_experience: int, vision_based: bool}
    
    -- Chosen Action
    chosen_action JSONB NOT NULL, -- {type, coordinates, parameters}
    action_source TEXT, -- 'user_demonstration' | 'learned_experience' | 'exploration' | 'vision_analysis'
    confidence_score FLOAT,
    
    -- Execution & Outcome
    action_executed BOOLEAN DEFAULT FALSE,
    execution_error TEXT,
    outcome JSONB, -- Result after action
    reward_signal FLOAT, -- +1 for progress, -1 for stuck/crash, 0 for neutral
    
    -- Learning Feedback
    was_successful BOOLEAN,
    learned_from_outcome BOOLEAN DEFAULT FALSE,
    adjustment_made TEXT, -- What AI learned to do differently
    
    -- Performance Metrics
    decision_time_ms INTEGER,
    execution_time_ms INTEGER,
    
    -- Metadata
    agent_type TEXT NOT NULL, -- 'heuristic' | 'advanced_rl' | 'hybrid'
    model_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_decisions_session ON ai_decisions(session_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_game ON ai_decisions(game_id);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_timestamp ON ai_decisions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_source ON ai_decisions(action_source);

-- ============================================
-- LEARNING PATTERNS TABLE
-- Extracted patterns that AI can reuse
-- ============================================
CREATE TABLE IF NOT EXISTS learning_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL,
    
    -- Pattern Definition
    pattern_name TEXT NOT NULL,
    pattern_type TEXT NOT NULL, -- 'tap_sequence' | 'screen_navigation' | 'goal_achievement'
    trigger_conditions JSONB, -- When to use this pattern
    action_sequence JSONB NOT NULL, -- Steps to execute
    
    -- Learning Source
    learned_from TEXT NOT NULL, -- 'user_observation' | 'ai_experience' | 'hybrid'
    source_observation_ids UUID[], -- Links to user_observations
    source_decision_ids UUID[], -- Links to ai_decisions
    
    -- Effectiveness Metrics
    times_used INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_reward FLOAT DEFAULT 0.0,
    confidence FLOAT DEFAULT 0.5,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_patterns_game ON learning_patterns(game_id);
CREATE INDEX IF NOT EXISTS idx_patterns_type ON learning_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_confidence ON learning_patterns(confidence DESC);

-- ============================================
-- SESSION LEARNING SUMMARY
-- Aggregated learning metrics per session
-- ============================================
CREATE TABLE IF NOT EXISTS session_learning_summary (
    session_id UUID PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    
    -- User Observation Metrics
    user_actions_observed INTEGER DEFAULT 0,
    user_patterns_extracted INTEGER DEFAULT 0,
    user_data_quality_score FLOAT DEFAULT 0.0,
    
    -- AI Decision Metrics  
    ai_decisions_made INTEGER DEFAULT 0,
    ai_successful_actions INTEGER DEFAULT 0,
    ai_failed_actions INTEGER DEFAULT 0,
    ai_exploration_rate FLOAT DEFAULT 0.0,
    
    -- Learning Progress
    new_patterns_learned INTEGER DEFAULT 0,
    existing_patterns_refined INTEGER DEFAULT 0,
    total_reward_accumulated FLOAT DEFAULT 0.0,
    
    -- Performance
    avg_decision_time_ms INTEGER,
    avg_confidence_score FLOAT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to update learning summary
CREATE OR REPLACE FUNCTION update_session_learning_summary()
RETURNS TRIGGER AS $$
BEGIN
    -- Update summary based on new observation or decision
    IF TG_TABLE_NAME = 'user_observations' THEN
        INSERT INTO session_learning_summary (session_id, user_actions_observed)
        VALUES (NEW.session_id, 1)
        ON CONFLICT (session_id) DO UPDATE
        SET user_actions_observed = session_learning_summary.user_actions_observed + 1,
            updated_at = NOW();
    ELSIF TG_TABLE_NAME = 'ai_decisions' THEN
        INSERT INTO session_learning_summary (session_id, ai_decisions_made)
        VALUES (NEW.session_id, 1)
        ON CONFLICT (session_id) DO UPDATE
        SET ai_decisions_made = session_learning_summary.ai_decisions_made + 1,
            ai_successful_actions = session_learning_summary.ai_successful_actions + 
                CASE WHEN NEW.was_successful THEN 1 ELSE 0 END,
            ai_failed_actions = session_learning_summary.ai_failed_actions + 
                CASE WHEN NEW.was_successful = FALSE THEN 1 ELSE 0 END,
            total_reward_accumulated = session_learning_summary.total_reward_accumulated + COALESCE(NEW.reward_signal, 0),
            updated_at = NOW();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers
DROP TRIGGER IF EXISTS update_summary_on_observation ON user_observations;
CREATE TRIGGER update_summary_on_observation
    AFTER INSERT ON user_observations
    FOR EACH ROW
    EXECUTE FUNCTION update_session_learning_summary();

DROP TRIGGER IF EXISTS update_summary_on_decision ON ai_decisions;
CREATE TRIGGER update_summary_on_decision
    AFTER INSERT ON ai_decisions
    FOR EACH ROW
    EXECUTE FUNCTION update_session_learning_summary();

-- Grant permissions
GRANT ALL ON user_observations TO playmetric;
GRANT ALL ON ai_decisions TO playmetric;
GRANT ALL ON learning_patterns TO playmetric;
GRANT ALL ON session_learning_summary TO playmetric;
