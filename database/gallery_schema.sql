-- Letters From Dick Gallery Schema
-- Run this to add gallery tables to existing hastingtx_music database

-- Sections (chapters) for organizing images
CREATE TABLE IF NOT EXISTS gallery_sections (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Images/artifacts
CREATE TABLE IF NOT EXISTS gallery_images (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    significance_date DATE,           -- Key: the date this image relates to (matches letter dates)
    source VARCHAR(255),              -- Optional: where image came from
    filename VARCHAR(255) NOT NULL,   -- Original file in static/uploads/gallery/images/
    thumbnail VARCHAR(255),           -- Generated thumbnail in static/uploads/gallery/thumbnails/
    file_type VARCHAR(20),            -- jpg, png, gif, webp, pdf
    file_size BIGINT,
    width INTEGER,
    height INTEGER,
    section_id INTEGER REFERENCES gallery_sections(id) ON DELETE SET NULL,
    sort_order INTEGER DEFAULT 0,     -- Within section or by date
    view_count INTEGER DEFAULT 0,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_gallery_images_date ON gallery_images(significance_date);
CREATE INDEX IF NOT EXISTS idx_gallery_images_section ON gallery_images(section_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_gallery_images_identifier ON gallery_images(identifier);
CREATE INDEX IF NOT EXISTS idx_gallery_sections_identifier ON gallery_sections(identifier);
CREATE INDEX IF NOT EXISTS idx_gallery_sections_sort ON gallery_sections(sort_order);

-- Create a default "Uncategorized" section
INSERT INTO gallery_sections (identifier, name, description, sort_order)
VALUES ('uncategorized', 'Uncategorized', 'Images not yet assigned to a section', 999)
ON CONFLICT (identifier) DO NOTHING;
