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

-- Create the 'all' playlist by default
INSERT INTO playlists (identifier, name, description, sort_order)
VALUES ('all', 'All Songs', 'Complete collection of all uploaded songs', 'title');
