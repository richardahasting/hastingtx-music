-- HastingTX Music Database Schema

-- Drop tables if they exist
DROP TABLE IF EXISTS ratings CASCADE;
DROP TABLE IF EXISTS playlist_songs CASCADE;
DROP TABLE IF EXISTS playlists CASCADE;
DROP TABLE IF EXISTS songs CASCADE;

-- Songs table: stores metadata about each song
CREATE TABLE songs (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(100) UNIQUE NOT NULL,  -- URL-friendly identifier (e.g., 'fooBar')
    title VARCHAR(255) NOT NULL,
    artist VARCHAR(255),
    album VARCHAR(255),
    description TEXT,
    lyrics TEXT,
    genre VARCHAR(100),
    tags TEXT,  -- Comma-separated tags
    filename VARCHAR(255) NOT NULL,  -- Actual MP3 filename
    duration INTEGER,  -- Duration in seconds
    file_size BIGINT,  -- File size in bytes
    cover_art VARCHAR(255),  -- Filename for cover art image in static/uploads/covers/
    composer VARCHAR(255),  -- Composer/creator (e.g., "Richard & Claude", "SUNO AI")
    lyricist VARCHAR(255),  -- Lyricist/text writer
    recording_date DATE,  -- Recording or creation date
    listen_count INTEGER DEFAULT 0,  -- Number of times played
    download_count INTEGER DEFAULT 0,  -- Number of times downloaded
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Playlists table: stores playlist metadata
CREATE TABLE playlists (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(100) UNIQUE NOT NULL,  -- URL-friendly identifier
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sort_order VARCHAR(20) DEFAULT 'manual',  -- 'manual', 'title', 'album'
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Playlist songs junction table: many-to-many relationship
CREATE TABLE playlist_songs (
    id SERIAL PRIMARY KEY,
    playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
    song_id INTEGER REFERENCES songs(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,  -- For manual ordering
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(playlist_id, song_id)
);

-- Indexes for performance
CREATE INDEX idx_songs_identifier ON songs(identifier);
CREATE INDEX idx_songs_upload_date ON songs(upload_date DESC);
CREATE INDEX idx_playlists_identifier ON playlists(identifier);
CREATE INDEX idx_playlist_songs_playlist ON playlist_songs(playlist_id, position);
CREATE INDEX idx_playlist_songs_song ON playlist_songs(song_id);

-- Ratings table: stores user ratings (one per IP per song)
CREATE TABLE ratings (
    id SERIAL PRIMARY KEY,
    song_id INTEGER REFERENCES songs(id) ON DELETE CASCADE,
    ip_address VARCHAR(45) NOT NULL,  -- IPv4 or IPv6 address
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(song_id, ip_address)
);

-- Indexes for ratings
CREATE INDEX idx_ratings_song ON ratings(song_id);
CREATE INDEX idx_ratings_ip ON ratings(ip_address);

-- Comments table: stores user comments on songs
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    song_id INTEGER REFERENCES songs(id) ON DELETE CASCADE,
    commenter_name VARCHAR(100),  -- Optional name for the commenter
    comment_text TEXT NOT NULL,
    ip_address VARCHAR(45) NOT NULL,  -- IPv4 or IPv6 address
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for comments
CREATE INDEX idx_comments_song ON comments(song_id, created_at DESC);
CREATE INDEX idx_comments_ip ON comments(ip_address);

-- Email subscribers table
CREATE TABLE subscribers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    unsubscribe_token VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for subscribers
CREATE INDEX idx_subscribers_email ON subscribers(email);
CREATE INDEX idx_subscribers_active ON subscribers(is_active);
CREATE INDEX idx_subscribers_token ON subscribers(unsubscribe_token);

-- Email log table to track sent emails
CREATE TABLE email_logs (
    id SERIAL PRIMARY KEY,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    subject VARCHAR(255),
    recipient_count INTEGER,
    song_ids INTEGER[],
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Genres table: predefined list of music genres
CREATE TABLE genres (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    parent_genre_id INTEGER REFERENCES genres(id) ON DELETE SET NULL,  -- For sub-genres
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for genres
CREATE INDEX idx_genres_name ON genres(name);
CREATE INDEX idx_genres_parent ON genres(parent_genre_id);

-- Create the 'all' playlist by default
INSERT INTO playlists (identifier, name, description, sort_order)
VALUES ('all', 'All Songs', 'Complete collection of all uploaded songs', 'title');

-- Populate genres with common music genres
INSERT INTO genres (name, description) VALUES
    ('Acoustic', 'Music primarily featuring acoustic instruments'),
    ('Alternative', 'Alternative rock and non-mainstream music'),
    ('Ambient', 'Atmospheric, environmental soundscapes'),
    ('Blues', 'Traditional blues and blues-influenced music'),
    ('Bluegrass', 'American roots music with acoustic string instruments'),
    ('Children''s', 'Music for children and families'),
    ('Christian', 'Contemporary Christian and gospel music'),
    ('Classical', 'Western classical music traditions'),
    ('Country', 'Country and western music'),
    ('Dance', 'Electronic dance music (EDM)'),
    ('Easy Listening', 'Relaxed, mellow instrumental and vocal music'),
    ('Electronic', 'Electronically produced music'),
    ('Folk', 'Traditional and contemporary folk music'),
    ('Funk', 'Funk and groove-based music'),
    ('Gospel', 'Religious gospel music'),
    ('Hip-Hop', 'Hip-hop and rap music'),
    ('Holiday', 'Seasonal and holiday music'),
    ('Indie', 'Independent and indie rock music'),
    ('Instrumental', 'Music without vocals'),
    ('Jazz', 'Jazz and jazz-influenced music'),
    ('Latin', 'Latin American music styles'),
    ('Metal', 'Heavy metal and its subgenres'),
    ('New Age', 'Meditative and spiritual music'),
    ('Opera', 'Operatic vocal music'),
    ('Pop', 'Popular mainstream music'),
    ('Punk', 'Punk rock and its derivatives'),
    ('R&B', 'Rhythm and blues, soul music'),
    ('Reggae', 'Jamaican reggae and related styles'),
    ('Rock', 'Rock and roll music'),
    ('Singer-Songwriter', 'Artist-focused acoustic songwriting'),
    ('Soft Rock', 'Melodic, lighter rock music'),
    ('Soul', 'Soul and Motown-influenced music'),
    ('Soundtrack', 'Film and television soundtracks'),
    ('Spoken Word', 'Spoken word and poetry'),
    ('Swing', 'Swing and big band music'),
    ('World', 'International and world music');
