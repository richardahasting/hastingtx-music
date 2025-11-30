# HastingTX Music

A Flask-based web application for sharing and managing music created by Richard & Claude, with SUNO AI turning lyrics into MP3 songs.

## Features

- **Song Management**: Upload, organize, and share MP3 files
- **Smart Metadata**: Automatic extraction from MP3 ID3 tags
- **Playlists**: Create and manage custom playlists with flexible sorting
- **Albums**: Auto-generated album playlists with album navigation dropdown
- **Genres**: Hierarchical genre system with parent/sub-genre support
- **Ratings System**: 1-10 star ratings (one vote per IP, shows average after 4+ votes)
- **Statistics**: Track listens and downloads for each song
- **Admin Interface**: IP-restricted upload and management interface
- **Download Options**: Single songs or entire playlists as ZIP files
- **Email Subscriptions**: Weekly notification of new songs
- **Hover Tooltips**: Song descriptions and genres shown on hover
- **Responsive Design**: Mobile-friendly interface
- **CLI Tool**: Command-line interface for database management

## Technology Stack

- **Backend**: Python 3.x with Flask
- **Database**: PostgreSQL
- **Frontend**: HTML5, CSS3, JavaScript
- **Audio**: HTML5 Audio Player
- **Metadata**: Mutagen library for MP3 tag reading
- **CLI**: argparse with tabulate for formatted output

## Installation

### Prerequisites

- Python 3.7 or higher
- PostgreSQL 12 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone or navigate to the project directory**
   ```bash
   cd /home/richard/projects/hastingtx/music
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   nano .env
   ```

5. **Set up PostgreSQL database**
   ```bash
   # Create database user if needed
   sudo -u postgres createuser -P richard

   # Initialize database
   python database/init_db.py

   # Add genres table (if upgrading existing installation)
   psql -U richard -d hastingtx_music -f database/add_genres.sql
   ```

6. **Configure admin IP whitelist**

   Edit `.env` and set `ADMIN_IP_WHITELIST` to your home network:
   ```
   ADMIN_IP_WHITELIST=127.0.0.1,::1,192.168.1.0/24,YOUR_PUBLIC_IP
   ```

7. **Run the development server**
   ```bash
   python app.py
   ```

   Visit: http://localhost:5000

## Configuration

### Environment Variables (.env)

```bash
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development  # Change to 'production' for deployment
SECRET_KEY=your-secret-key-here

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hastingtx_music
DB_USER=richard
DB_PASSWORD=your_db_password

# Upload Configuration
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=52428800  # 50MB

# IP Whitelist (comma-separated)
ADMIN_IP_WHITELIST=127.0.0.1,::1,192.168.1.0/24

# Application Settings
SITE_NAME=HastingTX Music
SONGS_PER_PAGE=50
```

## Usage

### Public Access

- **Home/All Songs**: `/` or `/music/playlist/all`
- **Single Song**: `/music/<identifier>`
- **Playlist**: `/music/playlist/<identifier>`
- **Album**: `/music/album/<album_name>`
- **Genre**: `/music/genre/<genre_name>`
- **Download Song**: `/download/song/<identifier>`
- **Download Playlist**: `/download/playlist/<identifier>`
- **Rate Song**: Click 1-10 rating buttons on song page
- **Subscribe**: Enter email in the subscription banner for weekly updates

### Navigation Dropdowns

The navigation bar includes dropdown menus for:
- **Albums**: All albums with songs (click to view album tracks)
- **Genres**: Only genres that have songs assigned (shows song count)
- **Playlists**: User-created playlists

### Hover Tooltips

Hovering over a song title in any playlist view will show a tooltip with:
- Genre (in blue)
- Description (if available)

### Admin Access (IP-Restricted)

- **Admin Dashboard**: `/admin`
- **Upload Song**: `/admin/upload`
- **Edit Song**: `/admin/songs/<id>/edit`
- **Create Playlist**: From admin dashboard
- **Manage Songs**: View stats, delete songs, manage playlists

### Uploading Songs

1. Access `/admin/upload` from a whitelisted IP
2. Drag and drop or select an MP3 file
3. Fill in song information:
   - **Title** (required) - auto-filled from filename
   - **Artist** (optional) - defaults to "Richard & Claude"
   - **Album** (optional) - select existing or create new (case-insensitive duplicate detection)
   - **Genre** (optional) - select from dropdown with sub-genre support, or create new
   - **Description** (optional)
   - **Lyrics** (optional) - recommended!
   - **Tags** (optional) - comma-separated
   - **Identifier** (optional) - auto-generated from title
4. Select playlists to add song to
5. Click "Upload Song"

Songs are automatically added to the "All Songs" playlist and their album playlist (if album specified).

### Creating Playlists

1. Go to `/admin`
2. Click "Create Playlist"
3. Enter:
   - **Name** (required)
   - **Description** (optional)
   - **Sort Order**: manual, title, or album
4. Click "Create"

## CLI Tool (music-cli.py)

A comprehensive command-line interface for database management:

```bash
./venv/bin/python music-cli.py <command> <subcommand> [options]
```

### Song Commands
```bash
./venv/bin/python music-cli.py songs list --limit 10
./venv/bin/python music-cli.py songs show <id>
./venv/bin/python music-cli.py songs search "keyword"
./venv/bin/python music-cli.py songs missing description|lyrics|genre
./venv/bin/python music-cli.py songs lyrics <id>
./venv/bin/python music-cli.py songs update <id> --title "New Title" --genre "Rock"
./venv/bin/python music-cli.py songs set-genre <id> "Progressive"
./venv/bin/python music-cli.py songs set-album <id> "Album Name"
```

### Playlist Commands
```bash
./venv/bin/python music-cli.py playlists list
./venv/bin/python music-cli.py playlists show <id>
./venv/bin/python music-cli.py playlists create "New Playlist"
./venv/bin/python music-cli.py playlists add <playlist_id> <song_id>
./venv/bin/python music-cli.py playlists remove <playlist_id> <song_id>
```

### Genre Commands
```bash
./venv/bin/python music-cli.py genres list
./venv/bin/python music-cli.py genres create "New Genre" --parent "Rock" --description "Description"
./venv/bin/python music-cli.py genres songs "Progressive"
```

### Album Commands
```bash
./venv/bin/python music-cli.py albums list
./venv/bin/python music-cli.py albums show "Album Name"
./venv/bin/python music-cli.py albums rename "Old Name" "New Name"
./venv/bin/python music-cli.py albums merge "Source Album" "Target Album"
```

### Statistics Commands
```bash
./venv/bin/python music-cli.py stats overview
./venv/bin/python music-cli.py stats top listens|downloads|rating
./venv/bin/python music-cli.py stats missing
./venv/bin/python music-cli.py stats activity
```

### Export Commands
```bash
./venv/bin/python music-cli.py export csv songs.csv
./venv/bin/python music-cli.py export json songs.json
./venv/bin/python music-cli.py export m3u playlist.m3u --playlist "All Songs"
```

### Maintenance Commands
```bash
./venv/bin/python music-cli.py maintenance duplicates
./venv/bin/python music-cli.py maintenance orphans
./venv/bin/python music-cli.py maintenance fix-case
```

## URL Structure

- Song pages: `https://hastingtx.org/music/<identifier>`
- Playlists: `https://hastingtx.org/music/playlist/<identifier>`
- Albums: `https://hastingtx.org/music/album/<album_name>`
- Genres: `https://hastingtx.org/music/genre/<genre_name>`
- Special "all songs" playlist: `https://hastingtx.org/music/playlist/all`

## Database Schema

### Tables

1. **songs**: Song metadata and file information
2. **playlists**: Playlist definitions
3. **playlist_songs**: Many-to-many relationship between playlists and songs
4. **ratings**: User ratings (one per IP per song)
5. **genres**: Hierarchical genre definitions with parent/child relationships
6. **subscribers**: Email subscribers for new song notifications
7. **comments**: Song comments (future feature)

See `database/schema.sql` for full schema definition.

## Deployment with Nginx

### Nginx Configuration

Create `/etc/nginx/sites-available/hastingtx-music`:

```nginx
server {
    listen 80;
    server_name hastingtx.org;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name hastingtx.org;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/hastingtx.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hastingtx.org/privkey.pem;

    # Limit file uploads to 50MB
    client_max_body_size 50M;

    # Serve static files directly
    location /static/ {
        alias /home/richard/projects/hastingtx/music/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Proxy to Flask application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase timeout for file uploads
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    # Optional: specific location for music subdomain
    location /music/ {
        proxy_pass http://127.0.0.1:5000/music/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/hastingtx-music /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Production Deployment

1. **Use a production WSGI server** (Gunicorn recommended):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 127.0.0.1:5000 --timeout 300 app:app
   ```

2. **Create a systemd service** (`/etc/systemd/system/hastingtx-music.service`):
   ```ini
   [Unit]
   Description=HastingTX Music Flask Application
   After=network.target postgresql.service

   [Service]
   User=richard
   WorkingDirectory=/home/richard/projects/hastingtx/music
   Environment="PATH=/home/richard/projects/hastingtx/music/venv/bin"
   ExecStart=/home/richard/projects/hastingtx/music/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 --timeout 300 --access-logfile /var/log/hastingtx-music/access.log --error-logfile /var/log/hastingtx-music/error.log app:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. **Create log directory**:
   ```bash
   sudo mkdir -p /var/log/hastingtx-music
   sudo chown richard:richard /var/log/hastingtx-music
   ```

4. **Enable and start the service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable hastingtx-music
   sudo systemctl start hastingtx-music
   sudo systemctl status hastingtx-music
   ```

5. **Set environment to production**:
   Update `.env`:
   ```
   FLASK_ENV=production
   ```

## Security Notes

- Admin functions are IP-restricted via middleware
- One rating per IP address per song
- File uploads limited to MP3 only
- 50MB maximum file size
- CSRF protection via Flask session
- SQL injection prevention via parameterized queries
- Case-insensitive duplicate detection for albums and genres

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check credentials in `.env`
- Ensure database exists: `psql -l`

### Upload Failures
- Check UPLOAD_FOLDER permissions: `ls -la static/uploads`
- Verify file size is under 50MB
- Ensure MP3 file is valid

### 403 Forbidden on Admin Pages
- Verify your IP is in ADMIN_IP_WHITELIST
- Check Flask logs for rejected IP
- Try adding your current IP: get it from admin logs

### Audio Not Playing
- Verify MP3 file is valid
- Check browser console for errors
- Ensure file exists in static/uploads

### CSS Not Updating
- Clear browser cache or use incognito mode
- Check that cache-busting query string is updated in base.html

## Development

### Project Structure

```
music/
├── app.py                 # Main Flask application
├── config.py              # Configuration management
├── db.py                  # Database connection
├── models.py              # Data models (Song, Playlist, Genre, Rating)
├── utils.py               # Utility functions
├── music-cli.py           # CLI tool for database management
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
├── database/
│   ├── schema.sql         # Database schema
│   ├── add_genres.sql     # Genres migration script
│   └── init_db.py         # Database initialization script
├── static/
│   ├── css/
│   │   └── style.css      # Stylesheet
│   ├── js/
│   │   └── main.js        # JavaScript utilities
│   └── uploads/           # MP3 file storage
│       └── covers/        # Cover art images
└── templates/
    ├── base.html          # Base template with navigation
    ├── song.html          # Song player page
    ├── playlist.html      # Playlist/Album/Genre view
    ├── upload.html        # Upload interface
    ├── edit_song.html     # Song editor
    ├── admin.html         # Admin dashboard
    └── error.html         # Error page
```

## License

Private project for HastingTX.org

## Credits

- **Music Creation**: Richard & Claude
- **AI Music Generation**: SUNO
- **Development**: Richard & Claude Code

## Support

For issues or questions, contact the administrator.
