# HastingTX Music

A Flask-based web application for sharing and managing music created by Richard & Claude, with SUNO AI turning lyrics into MP3 songs.

## Features

- **Song Management**: Upload, organize, and share MP3 files
- **Smart Metadata**: Automatic extraction from MP3 ID3 tags
- **Playlists**: Create and manage custom playlists with flexible sorting
- **Ratings System**: 1-10 star ratings (one vote per IP, shows average after 4+ votes)
- **Statistics**: Track listens and downloads for each song
- **Admin Interface**: IP-restricted upload and management interface
- **Download Options**: Single songs or entire playlists as ZIP files
- **Responsive Design**: Mobile-friendly interface

## Technology Stack

- **Backend**: Python 3.x with Flask
- **Database**: PostgreSQL
- **Frontend**: HTML5, CSS3, JavaScript
- **Audio**: HTML5 Audio Player
- **Metadata**: Mutagen library for MP3 tag reading

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

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   nano .env
   ```

4. **Set up PostgreSQL database**
   ```bash
   # Create database user if needed
   sudo -u postgres createuser -P richard

   # Initialize database
   python database/init_db.py
   ```

5. **Configure admin IP whitelist**

   Edit `.env` and set `ADMIN_IP_WHITELIST` to your home network:
   ```
   ADMIN_IP_WHITELIST=127.0.0.1,::1,192.168.1.0/24,YOUR_PUBLIC_IP
   ```

6. **Run the development server**
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
- **Download Song**: `/download/song/<identifier>`
- **Download Playlist**: `/download/playlist/<identifier>`
- **Rate Song**: Click 1-10 rating buttons on song page

### Admin Access (IP-Restricted)

- **Admin Dashboard**: `/admin`
- **Upload Song**: `/admin/upload`
- **Create Playlist**: From admin dashboard
- **Manage Songs**: View stats, delete songs

### Uploading Songs

1. Access `/admin/upload` from a whitelisted IP
2. Drag and drop or select an MP3 file
3. Fill in song information:
   - **Title** (required) - auto-filled from filename
   - **Artist** (optional) - defaults to "Richard & Claude"
   - **Album** (optional)
   - **Genre** (optional)
   - **Description** (optional)
   - **Lyrics** (optional) - recommended!
   - **Tags** (optional) - comma-separated
   - **Identifier** (optional) - auto-generated from title
4. Select playlists to add song to
5. Click "Upload Song"

### Creating Playlists

1. Go to `/admin`
2. Click "Create Playlist"
3. Enter:
   - **Name** (required)
   - **Description** (optional)
   - **Sort Order**: manual, title, or album
4. Click "Create"

## URL Structure

- Song pages: `https://hastingtx.org/music/<identifier>`
- Playlists: `https://hastingtx.org/music/playlist/<identifier>`
- Special "all songs" playlist: `https://hastingtx.org/music/playlist/all`

## Database Schema

### Tables

1. **songs**: Song metadata and file information
2. **playlists**: Playlist definitions
3. **playlist_songs**: Many-to-many relationship between playlists and songs
4. **ratings**: User ratings (one per IP per song)

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
   gunicorn -w 4 -b 127.0.0.1:5000 app:app
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
   ExecStart=/home/richard/projects/hastingtx/music/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start the service**:
   ```bash
   sudo systemctl enable hastingtx-music
   sudo systemctl start hastingtx-music
   sudo systemctl status hastingtx-music
   ```

4. **Set environment to production**:
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

## Development

### Project Structure

```
music/
├── app.py                 # Main Flask application
├── config.py             # Configuration management
├── db.py                 # Database connection
├── models.py             # Data models (Song, Playlist, Rating)
├── utils.py              # Utility functions
├── requirements.txt      # Python dependencies
├── .env.example          # Environment template
├── database/
│   ├── schema.sql        # Database schema
│   └── init_db.py        # Database initialization script
├── static/
│   ├── css/
│   │   └── style.css     # Stylesheet
│   ├── js/
│   │   └── main.js       # JavaScript utilities
│   └── uploads/          # MP3 file storage
└── templates/
    ├── base.html         # Base template
    ├── song.html         # Song player page
    ├── playlist.html     # Playlist page
    ├── upload.html       # Upload interface
    ├── admin.html        # Admin dashboard
    └── error.html        # Error page
```

## License

Private project for HastingTX.org

## Credits

- **Music Creation**: Richard & Claude
- **AI Music Generation**: SUNO
- **Development**: Richard & Claude Code

## Support

For issues or questions, contact the administrator.
