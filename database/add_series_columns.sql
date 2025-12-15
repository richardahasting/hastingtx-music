-- Add series support and ordering to devotional_threads
-- Run with: psql -U richard -d hastingtx_music -f database/add_series_columns.sql

-- Series name for grouping related threads
ALTER TABLE devotional_threads ADD COLUMN IF NOT EXISTS series VARCHAR(100);

-- Position within a series (0, 1, 2, etc.)
ALTER TABLE devotional_threads ADD COLUMN IF NOT EXISTS series_position INTEGER;

-- Index for efficient series queries
CREATE INDEX IF NOT EXISTS idx_threads_series ON devotional_threads(series, series_position);

-- Verify
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'devotional_threads'
AND column_name IN ('series', 'series_position');
