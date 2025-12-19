-- Migration: Add activity_log table for visitor and song stats tracking
-- Date: 2024-12-19

-- Create activity log table to track visits, plays, and downloads
CREATE TABLE IF NOT EXISTS activity_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(20) NOT NULL,  -- 'visit', 'play', 'download'
    ip_address VARCHAR(45) NOT NULL,  -- IPv4 or IPv6 address
    song_id INTEGER REFERENCES songs(id) ON DELETE CASCADE,  -- NULL for page visits
    page_path VARCHAR(255),           -- For page visits (e.g., '/music', '/albums')
    user_agent TEXT,                  -- Browser/client info
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at);
CREATE INDEX IF NOT EXISTS idx_activity_log_event_type ON activity_log(event_type);
CREATE INDEX IF NOT EXISTS idx_activity_log_song_id ON activity_log(song_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_ip ON activity_log(ip_address);

-- Composite index for time-based event queries
CREATE INDEX IF NOT EXISTS idx_activity_log_event_time ON activity_log(event_type, created_at);

-- Add comment for documentation
COMMENT ON TABLE activity_log IS 'Tracks visitor activity: page visits, song plays, and downloads';
COMMENT ON COLUMN activity_log.event_type IS 'Type of event: visit, play, or download';
COMMENT ON COLUMN activity_log.ip_address IS 'Client IP address (IPv4 or IPv6)';
COMMENT ON COLUMN activity_log.song_id IS 'Song ID for play/download events, NULL for visits';
COMMENT ON COLUMN activity_log.page_path IS 'Page path for visit events';
