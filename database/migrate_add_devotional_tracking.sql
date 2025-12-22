-- Migration: Add devotional_id to activity_log for tracking devotional reads
-- Date: 2024-12-19

-- Add devotional_id column to activity_log
ALTER TABLE activity_log ADD COLUMN IF NOT EXISTS devotional_id INTEGER REFERENCES devotionals(id) ON DELETE CASCADE;

-- Add index for devotional queries
CREATE INDEX IF NOT EXISTS idx_activity_log_devotional_id ON activity_log(devotional_id);

-- Add comment
COMMENT ON COLUMN activity_log.devotional_id IS 'Devotional ID for devotional_read events';
