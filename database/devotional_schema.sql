-- Devotional Schema for HastingTX
-- "Pull The Thread" - Daily Devotional Series

-- Devotional threads (series)
CREATE TABLE IF NOT EXISTS devotional_threads (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    author VARCHAR(255),
    cover_image VARCHAR(255),
    total_days INTEGER NOT NULL DEFAULT 1,
    is_published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Individual devotionals (days within a thread)
CREATE TABLE IF NOT EXISTS devotionals (
    id SERIAL PRIMARY KEY,
    thread_id INTEGER REFERENCES devotional_threads(id) ON DELETE CASCADE,
    day_number INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    scripture_reference VARCHAR(255),
    scripture_text TEXT,
    content TEXT NOT NULL,
    reflection_questions TEXT,
    prayer TEXT,
    audio_filename VARCHAR(255),
    audio_duration INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(thread_id, day_number)
);

-- User progress tracking (by session/cookie or email)
CREATE TABLE IF NOT EXISTS devotional_progress (
    id SERIAL PRIMARY KEY,
    thread_id INTEGER REFERENCES devotional_threads(id) ON DELETE CASCADE,
    user_identifier VARCHAR(255) NOT NULL,
    current_day INTEGER DEFAULT 1,
    completed_days INTEGER[] DEFAULT '{}',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(thread_id, user_identifier)
);

-- Devotional subscribers (for email drip and future notifications)
CREATE TABLE IF NOT EXISTS devotional_subscribers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    receive_new_threads BOOLEAN DEFAULT TRUE,
    unsubscribe_token VARCHAR(64) UNIQUE NOT NULL,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Email drip enrollments
CREATE TABLE IF NOT EXISTS devotional_enrollments (
    id SERIAL PRIMARY KEY,
    subscriber_id INTEGER REFERENCES devotional_subscribers(id) ON DELETE CASCADE,
    thread_id INTEGER REFERENCES devotional_threads(id) ON DELETE CASCADE,
    current_day INTEGER DEFAULT 1,
    next_send_date DATE,
    is_complete BOOLEAN DEFAULT FALSE,
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(subscriber_id, thread_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_devotionals_thread ON devotionals(thread_id, day_number);
CREATE INDEX IF NOT EXISTS idx_progress_user ON devotional_progress(user_identifier);
CREATE INDEX IF NOT EXISTS idx_progress_thread ON devotional_progress(thread_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_send ON devotional_enrollments(next_send_date, is_complete);
CREATE INDEX IF NOT EXISTS idx_threads_published ON devotional_threads(is_published);
CREATE INDEX IF NOT EXISTS idx_threads_identifier ON devotional_threads(identifier);
