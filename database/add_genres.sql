-- Migration: Add genres table
-- Run this on existing database to add genres without dropping other tables

-- Genres table: predefined list of music genres
CREATE TABLE IF NOT EXISTS genres (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    parent_genre_id INTEGER REFERENCES genres(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for genres
CREATE INDEX IF NOT EXISTS idx_genres_name ON genres(name);
CREATE INDEX IF NOT EXISTS idx_genres_parent ON genres(parent_genre_id);

-- Populate genres with common music genres (skip if already exists)
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
    ('World', 'International and world music')
ON CONFLICT (name) DO NOTHING;
