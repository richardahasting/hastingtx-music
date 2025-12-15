-- Add sync columns to devotional_subscribers table
-- For cross-device progress sync via email

-- Link subscriber to their session user_identifier
ALTER TABLE devotional_subscribers
ADD COLUMN IF NOT EXISTS user_identifier VARCHAR(255);

-- Track when last sync email was sent (for rate limiting)
ALTER TABLE devotional_subscribers
ADD COLUMN IF NOT EXISTS last_sync_email_sent TIMESTAMP;

-- Index for looking up by user_identifier
CREATE INDEX IF NOT EXISTS idx_subscribers_user_id ON devotional_subscribers(user_identifier);
