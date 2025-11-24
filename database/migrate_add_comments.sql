-- Migration: Add comments table
-- Run with: psql -U richard -d hastingtx_music -f migrate_add_comments.sql

-- Create comments table
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    song_id INTEGER REFERENCES songs(id) ON DELETE CASCADE,
    commenter_name VARCHAR(100),  -- Optional name for the commenter
    comment_text TEXT NOT NULL,
    ip_address VARCHAR(45) NOT NULL,  -- IPv4 or IPv6 address
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_comments_song ON comments(song_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_comments_ip ON comments(ip_address);

COMMENT ON TABLE comments IS 'User comments on songs';
COMMENT ON COLUMN comments.commenter_name IS 'Optional display name for commenter';
COMMENT ON COLUMN comments.comment_text IS 'The comment text content';
COMMENT ON COLUMN comments.ip_address IS 'IP address of commenter for tracking';
