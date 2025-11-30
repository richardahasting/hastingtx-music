-- Migration: Add email subscribers table
-- Run with: psql -U richard -d hastingtx_music -f migrate_add_subscribers.sql

-- Create subscribers table
CREATE TABLE IF NOT EXISTS subscribers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    unsubscribe_token VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_subscribers_email ON subscribers(email);
CREATE INDEX IF NOT EXISTS idx_subscribers_active ON subscribers(is_active);
CREATE INDEX IF NOT EXISTS idx_subscribers_token ON subscribers(unsubscribe_token);

-- Create email log table to track what was sent
CREATE TABLE IF NOT EXISTS email_logs (
    id SERIAL PRIMARY KEY,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    subject VARCHAR(255),
    recipient_count INTEGER,
    song_ids INTEGER[],
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

COMMENT ON TABLE subscribers IS 'Email subscribers for new song notifications';
COMMENT ON COLUMN subscribers.unsubscribe_token IS 'Unique token for unsubscribe links';
COMMENT ON COLUMN subscribers.is_active IS 'Whether subscription is active';
COMMENT ON TABLE email_logs IS 'Log of sent weekly emails';
