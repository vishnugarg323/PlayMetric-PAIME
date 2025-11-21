-- Migration: Fix CASCADE delete constraints for session-related tables
-- This ensures that when a session is deleted, all related data is properly cleaned up

-- Drop and recreate foreign key constraints with CASCADE delete

-- 1. Fix bugs table
ALTER TABLE bugs 
DROP CONSTRAINT IF EXISTS bugs_session_id_fkey;

ALTER TABLE bugs 
ADD CONSTRAINT bugs_session_id_fkey 
FOREIGN KEY (session_id) 
REFERENCES sessions(id) 
ON DELETE CASCADE;

-- 2. Fix rl_experiences table
ALTER TABLE rl_experiences 
DROP CONSTRAINT IF EXISTS rl_experiences_session_id_fkey;

ALTER TABLE rl_experiences 
ADD CONSTRAINT rl_experiences_session_id_fkey 
FOREIGN KEY (session_id) 
REFERENCES sessions(id) 
ON DELETE CASCADE;

-- 3. Fix retention_analysis table
ALTER TABLE retention_analysis 
DROP CONSTRAINT IF EXISTS retention_analysis_session_id_fkey;

ALTER TABLE retention_analysis 
ADD CONSTRAINT retention_analysis_session_id_fkey 
FOREIGN KEY (session_id) 
REFERENCES sessions(id) 
ON DELETE CASCADE;

-- Verify the changes
DO $$
BEGIN
    RAISE NOTICE 'CASCADE delete constraints updated successfully for:';
    RAISE NOTICE '  - bugs.session_id';
    RAISE NOTICE '  - rl_experiences.session_id';
    RAISE NOTICE '  - retention_analysis.session_id';
END $$;
