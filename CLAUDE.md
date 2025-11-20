# CLAUDE.md - HastingTX Music Project

This file provides guidance to Claude Code when working in this project.

## Project Overview

**HastingTX Music** is a Flask-based web application for sharing and managing music created collaboratively by Richard and Claude, with SUNO AI turning lyrics into MP3 songs.

## Architecture

### Technology Stack
- **Backend**: Python 3.x with Flask web framework
- **Database**: PostgreSQL with psycopg2
- **Frontend**: HTML5, CSS3, vanilla JavaScript
- **Audio**: HTML5 Audio Player, Mutagen for MP3 metadata
- **Deployment**: Gunicorn WSGI server behind Nginx reverse proxy

### Key Features
1. **Song Management**: Upload, organize, share MP3 files
2. **Ratings System**: 1-10 scale, one vote per IP, shows average after 4+ votes
3. **Statistics**: Track listens and downloads per song
4. **Playlists**: Create and manage with flexible sorting (manual/title/album)
5. **Admin Interface**: IP-restricted upload and management
6. **Downloads**: Single songs or ZIP archives of playlists

## Project Structure

```
music/
├── app.py                 # Main Flask application with all routes
├── config.py             # Configuration from environment variables
├── db.py                 # PostgreSQL connection management
├── models.py             # Data models: Song, Playlist, Rating
├── utils.py              # Utilities: MP3 metadata, file handling, IP checking
├── requirements.txt      # Python dependencies
├── .env                  # Environment configuration (not in git)
├── .env.example          # Environment template
├── database/
│   ├── schema.sql        # PostgreSQL schema with all tables
│   └── init_db.py        # Database initialization script
├── static/
│   ├── css/style.css     # Main stylesheet
│   ├── js/main.js        # JavaScript utilities
│   └── uploads/          # MP3 file storage (not in git)
├── templates/            # Jinja2 templates
│   ├── base.html         # Base layout
│   ├── song.html         # Song player with ratings
│   ├── playlist.html     # Playlist view with table
│   ├── upload.html       # Upload interface with drag-drop
│   ├── admin.html        # Admin dashboard
│   └── error.html        # Error page
├── nginx.conf.example    # Nginx configuration
└── README.md            # Full documentation
```

## Database Schema

### Tables
1. **songs**: Stores song metadata, file info, listen/download counts
2. **playlists**: Playlist definitions with sort order settings
3. **playlist_songs**: Many-to-many junction table with position field
4. **ratings**: User ratings (song_id + ip_address unique constraint)

### Key Relationships
- Song can be in multiple playlists (many-to-many)
- Each playlist has configurable sort order (manual, title, album)
- One rating per IP address per song
- Cascade deletes for playlist_songs and ratings

## Important Implementation Details

### IP-Based Access Control
- Admin routes protected by `@require_admin_ip` decorator
- IP whitelist configured via `ADMIN_IP_WHITELIST` in .env
- Supports individual IPs and CIDR ranges
- Uses `request.remote_addr` for IP detection
- Respects X-Forwarded-For when behind proxy

### Rating System
- Scale: 1-10 (enforced at database and API level)
- One vote per IP address per song (unique constraint)
- Average displayed only when `rating_count >= 4`
- Uses UPSERT pattern (INSERT ... ON CONFLICT DO UPDATE)
- API endpoint: `POST /api/songs/<id>/rate`

### Statistics Tracking
- Listen count incremented on song page view
- Download count incremented on download endpoint hit
- No de-duplication (each page view/download counts)
- Could be enhanced with session-based tracking

### File Upload
- Max size: 50MB (configurable)
- Only MP3 files allowed
- Automatic metadata extraction via Mutagen
- Auto-generates URL identifier from title
- Drag-and-drop interface
- Progress indication during upload

### Playlist Sorting
Three modes:
- **manual**: User-defined order via position field
- **title**: Alphabetical by song title
- **album**: Alphabetical by album, then title

Applied dynamically in SQL queries via `Playlist.get_songs()`

## Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python database/init_db.py

# Run development server
python app.py  # Runs on http://localhost:5000

# Run with Gunicorn (production)
gunicorn -w 4 -b 127.0.0.1:5000 app:app
```

### Database Operations
```bash
# Connect to database
psql -U richard -d hastingtx_music

# Reset database (WARNING: deletes all data)
python database/init_db.py  # Drops and recreates tables

# Manual schema application
psql -U richard -d hastingtx_music -f database/schema.sql
```

### Deployment
```bash
# Copy Nginx config
sudo cp nginx.conf.example /etc/nginx/sites-available/hastingtx-music
sudo ln -s /etc/nginx/sites-available/hastingtx-music /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Set up systemd service (see README.md)
sudo systemctl enable hastingtx-music
sudo systemctl start hastingtx-music
```

## Configuration

### Required Environment Variables
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: PostgreSQL connection
- `SECRET_KEY`: Flask session encryption key
- `ADMIN_IP_WHITELIST`: Comma-separated IPs/CIDR ranges
- `UPLOAD_FOLDER`: Path to MP3 storage (default: static/uploads)
- `MAX_CONTENT_LENGTH`: Upload size limit in bytes (default: 52428800 = 50MB)

See `.env.example` for full configuration options.

## Security Considerations

1. **IP Whitelisting**: Admin functions only accessible from configured IPs
2. **File Type Validation**: Only MP3 files accepted
3. **SQL Injection Prevention**: Parameterized queries throughout
4. **CSRF Protection**: Flask built-in session management
5. **File Upload Limits**: 50MB max, enforced at Flask and Nginx levels
6. **Path Traversal Prevention**: `secure_filename()` for all uploads

## Known Limitations

1. **Listen/Download Tracking**: No de-duplication, every page view counts
2. **Rating System**: IP-based (VPN/proxy can allow multiple votes)
3. **File Storage**: Local filesystem only (no S3/CDN)
4. **Playlist Management**: Basic UI, no drag-drop reordering yet
5. **Search**: Simple ILIKE queries, no full-text search
6. **Batch Operations**: No bulk upload or batch management

## Future Enhancement Ideas

1. Add drag-drop playlist reordering
2. Implement full-text search (PostgreSQL tsvector)
3. Add audio waveform visualization
4. Create playlist cover images
5. Export playlists as M3U/PLS
6. Add song comments/discussion
7. Create user accounts for personalized playlists
8. Add play history tracking
9. Implement audio transcoding for browser compatibility
10. Add lyrics timing/synchronization

## Troubleshooting

### Common Issues

1. **Database connection errors**: Check PostgreSQL is running and credentials in .env
2. **403 on admin pages**: Verify IP is in whitelist, check Flask logs for actual IP
3. **Upload failures**: Check permissions on static/uploads, verify 50MB limit
4. **Audio not playing**: Verify MP3 is valid, check browser console for MIME type issues
5. **Rating not submitting**: Check browser console for JS errors, verify API endpoint

### Debug Mode

Set in `.env`:
```
FLASK_ENV=development
```

This enables:
- Detailed error pages
- Auto-reload on code changes
- Debug toolbar (if installed)

## Testing Checklist

When making changes, test:
- [ ] Song upload with drag-drop
- [ ] MP3 playback in song page
- [ ] Rating submission (1-10 scale)
- [ ] Download single song
- [ ] Download playlist as ZIP
- [ ] Playlist creation and sorting
- [ ] Admin access from whitelisted IP
- [ ] Admin block from non-whitelisted IP
- [ ] Listen/download counters increment
- [ ] Rating average displays after 4 votes
- [ ] Mobile responsive design

## Development Guidelines

1. **Follow existing patterns**: Use established model/route structure
2. **SQL injection prevention**: Always use parameterized queries
3. **Error handling**: Return appropriate HTTP status codes
4. **Template inheritance**: Extend base.html for consistency
5. **CSS organization**: Keep styles in style.css, avoid inline styles
6. **JavaScript**: Use vanilla JS, avoid unnecessary libraries
7. **Database changes**: Update schema.sql and provide migration path
8. **Documentation**: Update README.md for user-facing changes
9. **Security**: Consider IP-based access, file validation, input sanitization

## Support Resources

- Flask documentation: https://flask.palletsprojects.com/
- PostgreSQL docs: https://www.postgresql.org/docs/
- Mutagen (MP3 tags): https://mutagen.readthedocs.io/
- Nginx config: https://nginx.org/en/docs/

## Contact

For questions or issues with this project, contact Richard.
