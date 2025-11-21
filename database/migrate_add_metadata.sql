-- Migration: Add enhanced metadata fields
-- Run with: psql -U richard -d hastingtx_music -f migrate_add_metadata.sql

-- Add new columns for enhanced metadata
ALTER TABLE songs ADD COLUMN IF NOT EXISTS cover_art VARCHAR(255);  -- Filename for cover art image
ALTER TABLE songs ADD COLUMN IF NOT EXISTS composer VARCHAR(255);    -- Composer/Creator
ALTER TABLE songs ADD COLUMN IF NOT EXISTS lyricist VARCHAR(255);    -- Lyricist/Text Writer
ALTER TABLE songs ADD COLUMN IF NOT EXISTS recording_date DATE;      -- Recording/creation date

-- Create cover art upload directory (note for manual creation)
-- mkdir -p static/uploads/covers

COMMENT ON COLUMN songs.cover_art IS 'Filename of cover art image in static/uploads/covers/';
COMMENT ON COLUMN songs.composer IS 'Composer/creator (e.g., "Richard & Claude", "SUNO AI")';
COMMENT ON COLUMN songs.lyricist IS 'Lyricist/text writer';
COMMENT ON COLUMN songs.recording_date IS 'Recording or creation date';
