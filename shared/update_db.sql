-- Update script to add learning mode tables
-- Safe to run multiple times (uses IF NOT EXISTS)

-- Drop old learning_data table if it exists with wrong schema
DROP TABLE IF EXISTS learning_data CASCADE;

-- Learning Sessions Table
CREATE TABLE IF NOT EXISTS learning_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID REFERENCES video_demonstrations(id) ON DELETE CASCADE,
    game_id UUID REFERENCES games(id),
    status VARCHAR(50) DEFAULT 'pending', -- pending, extracting, analyzing, completed, failed
    total_frames INTEGER DEFAULT 0,
    frames_analyzed INTEGER DEFAULT 0,
    current_batch_number INTEGER DEFAULT 0,
    batch_size INTEGER DEFAULT 3, -- 3 frames per batch for learning mode UI
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    config JSONB DEFAULT '{}'::jsonb -- Additional configuration
);

CREATE INDEX IF NOT EXISTS idx_learning_sessions_video_id ON learning_sessions(video_id);
CREATE INDEX IF NOT EXISTS idx_learning_sessions_game_id ON learning_sessions(game_id);
CREATE INDEX IF NOT EXISTS idx_learning_sessions_status ON learning_sessions(status);
CREATE INDEX IF NOT EXISTS idx_learning_sessions_created_at ON learning_sessions(created_at DESC);

COMMENT ON TABLE learning_sessions IS 'Learning mode sessions for video analysis with real-time UI updates';

-- Add learning_session_id to video_frames if column doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='video_frames' AND column_name='learning_session_id') THEN
        ALTER TABLE video_frames ADD COLUMN learning_session_id UUID REFERENCES learning_sessions(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Add per-model analysis columns to video_frames if they don't exist
DO $$ 
BEGIN
    -- Screen dimensions
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='screen_width') THEN
        ALTER TABLE video_frames ADD COLUMN screen_width INTEGER;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='screen_height') THEN
        ALTER TABLE video_frames ADD COLUMN screen_height INTEGER;
    END IF;
    
    -- Per-model analysis (6 models)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='ocr_analysis') THEN
        ALTER TABLE video_frames ADD COLUMN ocr_analysis JSONB;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='gemini_analysis') THEN
        ALTER TABLE video_frames ADD COLUMN gemini_analysis JSONB;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='grok_analysis') THEN
        ALTER TABLE video_frames ADD COLUMN grok_analysis JSONB;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='blip_analysis') THEN
        ALTER TABLE video_frames ADD COLUMN blip_analysis JSONB;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='opencv_analysis') THEN
        ALTER TABLE video_frames ADD COLUMN opencv_analysis JSONB;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='template_analysis') THEN
        ALTER TABLE video_frames ADD COLUMN template_analysis JSONB;
    END IF;
    
    -- Combined AI summary
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='combined_summary') THEN
        ALTER TABLE video_frames ADD COLUMN combined_summary JSONB;
    END IF;
    
    -- View-Action-Result pattern
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='view_state') THEN
        ALTER TABLE video_frames ADD COLUMN view_state JSONB;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='recommended_action') THEN
        ALTER TABLE video_frames ADD COLUMN recommended_action JSONB;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='expected_result') THEN
        ALTER TABLE video_frames ADD COLUMN expected_result JSONB;
    END IF;
    
    -- Worker tracking
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='worker_id') THEN
        ALTER TABLE video_frames ADD COLUMN worker_id VARCHAR(50);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='analysis_time_ms') THEN
        ALTER TABLE video_frames ADD COLUMN analysis_time_ms INTEGER;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='methods_used') THEN
        ALTER TABLE video_frames ADD COLUMN methods_used TEXT[];
    END IF;
    
    -- Touch position as percentage (0-1) instead of absolute pixels
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='touch_x_percent') THEN
        ALTER TABLE video_frames ADD COLUMN touch_x_percent FLOAT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='video_frames' AND column_name='touch_y_percent') THEN
        ALTER TABLE video_frames ADD COLUMN touch_y_percent FLOAT;
    END IF;
END $$;

-- Frame Comparisons Table (sequential frame diffs)
CREATE TABLE IF NOT EXISTS frame_comparisons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    learning_session_id UUID NOT NULL REFERENCES learning_sessions(id) ON DELETE CASCADE,
    frame_a_id UUID NOT NULL REFERENCES video_frames(id) ON DELETE CASCADE,
    frame_b_id UUID NOT NULL REFERENCES video_frames(id) ON DELETE CASCADE,
    
    -- What changed between frames
    scene_changed BOOLEAN DEFAULT false,
    ui_elements_changed JSONB, -- {buttons_appeared: [], buttons_disappeared: [], text_changed: []}
    text_changed JSONB, -- {added: [], removed: [], modified: []}
    game_state_changes JSONB, -- {score_delta: 100, lives_lost: 1, level_completed: true}
    
    -- Summary
    change_summary TEXT, -- Plain English: "Player tapped button, menu opened"
    pattern_recognized VARCHAR(255), -- menu_opened, level_completed, game_over, etc.
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_frame_comparisons_session ON frame_comparisons(learning_session_id);
CREATE INDEX IF NOT EXISTS idx_frame_comparisons_frame_a ON frame_comparisons(frame_a_id);
CREATE INDEX IF NOT EXISTS idx_frame_comparisons_frame_b ON frame_comparisons(frame_b_id);

COMMENT ON TABLE frame_comparisons IS 'Sequential frame-to-frame comparisons showing what changed';

-- Batch Summaries Table (3-frame batch insights)
CREATE TABLE IF NOT EXISTS batch_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    learning_session_id UUID NOT NULL REFERENCES learning_sessions(id) ON DELETE CASCADE,
    batch_number INTEGER NOT NULL,
    frame_ids UUID[] NOT NULL, -- Array of 3 frame IDs in this batch
    
    -- Batch analysis
    dominant_scene_type VARCHAR(50), -- menu, gameplay, cutscene, loading
    batch_insights JSONB, -- {common_elements: [], progression: [], key_actions: []}
    progression_summary TEXT, -- Plain English: "User navigated from menu -> settings -> back to menu"
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_batch_summaries_session ON batch_summaries(learning_session_id);
CREATE INDEX IF NOT EXISTS idx_batch_summaries_batch_number ON batch_summaries(learning_session_id, batch_number);

COMMENT ON TABLE batch_summaries IS '3-frame batch summaries for learning mode UI';
