# HastingTX Music - Deployment Status

**Date:** 2025-11-20
**Status:** ✅ DEPLOYED TO PRODUCTION

## 🎉 Deployment Complete!

Your HastingTX Music application is now running in production mode.

## 📍 GitHub Repository

**URL:** https://github.com/richardahasting/hastingtx-music
**Visibility:** Public
**Branch:** main
**Initial Commit:** b9df803

## 🚀 Production Environment

### Service Status
- **Service:** `hastingtx-music.service` (systemd)
- **Status:** Active and running
- **Workers:** 4 Gunicorn workers
- **Port:** 127.0.0.1:5000 (behind Nginx)
- **Auto-start:** Enabled (starts on boot)

### Web Server
- **Nginx:** Configured and active
- **Configuration:** `/etc/nginx/sites-available/hastingtx-music`
- **Max Upload:** 50MB

### Database
- **PostgreSQL:** hastingtx_music
- **User:** richard
- **Tables:** songs, playlists, playlist_songs, ratings
- **Default Playlist:** "All Songs" created

## 🌐 Access URLs

### Public Access
- **Home:** http://hastingtx.org/
- **All Songs:** http://hastingtx.org/music/playlist/all
- **Single Song:** http://hastingtx.org/music/<identifier>

### Admin Access (IP-Restricted)
- **Dashboard:** http://hastingtx.org/admin
- **Upload:** http://hastingtx.org/admin/upload
- **Allowed IPs:** 127.0.0.1, 192.168.0.0/24

## 📊 Features Enabled

✅ Song upload with drag-drop interface
✅ Automatic MP3 metadata extraction
✅ HTML5 audio player
✅ Rating system (1-10, one vote per IP)
✅ Listen/download statistics
✅ Playlist management with sorting
✅ ZIP downloads
✅ IP-based admin access control

## 📝 Logs

### Application Logs
- **Gunicorn Access:** `/var/log/hastingtx-music/access.log`
- **Gunicorn Error:** `/var/log/hastingtx-music/error.log`
- **Systemd Journal:** `sudo journalctl -u hastingtx-music -f`

### Nginx Logs
- **Access:** `/var/log/nginx/hastingtx-music-access.log`
- **Error:** `/var/log/nginx/hastingtx-music-error.log`

## 🔧 Service Management

### Control Commands
```bash
# View status
sudo systemctl status hastingtx-music

# Restart service
sudo systemctl restart hastingtx-music

# Stop service
sudo systemctl stop hastingtx-music

# Start service
sudo systemctl start hastingtx-music

# View live logs
sudo journalctl -u hastingtx-music -f
```

### Nginx Commands
```bash
# Reload Nginx
sudo systemctl reload nginx

# Test configuration
sudo nginx -t

# View error log
sudo tail -f /var/log/nginx/hastingtx-music-error.log
```

## 📁 Project Structure

```
/home/richard/projects/hastingtx/music/
├── venv/                   # Python virtual environment
├── app.py                  # Main Flask application
├── config.py              # Configuration
├── models.py              # Database models
├── database/
│   ├── schema.sql         # PostgreSQL schema
│   └── init_db.py        # Database initialization
├── static/
│   ├── css/              # Stylesheets
│   ├── js/               # JavaScript
│   └── uploads/          # MP3 storage
├── templates/            # Jinja2 templates
├── .env                  # Configuration (not in git)
├── deploy.sh            # Production deployment script
├── configure.sh         # Initial configuration script
└── setup_db.sh          # Database setup script
```

## 🎵 Uploading Your First Song

1. Navigate to: http://hastingtx.org/admin/upload
2. Drag and drop an MP3 file
3. Fill in:
   - **Title** (required)
   - **Artist** (defaults to "Richard & Claude")
   - **Lyrics** (highly recommended!)
   - **Description, Genre, Tags** (optional)
4. Click "Upload Song"
5. Song will be available at: http://hastingtx.org/music/song-title

## 🔒 Security Notes

- Admin access restricted to 192.168.0.0/24 network
- Only MP3 files accepted
- 50MB file size limit
- One rating per IP address per song
- PostgreSQL password protected
- Session-based CSRF protection

## ⚠️ Known Issues

### Nginx Warning
There's a conflicting server name "hastingtx.org" warning. This means another Nginx config is also using hastingtx.org. The music app is configured to handle specific routes (/music/, /admin, etc.). Make sure your main hastingtx.org config doesn't conflict with these paths.

## 🔄 Updating the Application

```bash
cd /home/richard/projects/hastingtx/music

# Pull latest changes
git pull origin main

# Restart service
sudo systemctl restart hastingtx-music
```

## 📦 Backup Recommendations

### Database Backup
```bash
# Backup database
pg_dump -U richard hastingtx_music > hastingtx_music_backup.sql

# Restore database
psql -U richard hastingtx_music < hastingtx_music_backup.sql
```

### File Backup
- **MP3 files:** `static/uploads/`
- **Configuration:** `.env` (contains passwords!)
- **Database:** Regular pg_dump backups

## 📞 Support

For issues or questions:
- Check logs: `sudo journalctl -u hastingtx-music -f`
- Test service: `sudo systemctl status hastingtx-music`
- Verify database: `psql -U richard -d hastingtx_music`
- Review Nginx: `sudo nginx -t`

## 🎯 Next Steps

1. Upload your first song from SUNO
2. Create custom playlists
3. Share song links with friends
4. Monitor stats (listens/downloads)
5. Collect ratings

---

**Built by:** Richard & Claude
**Technology:** Flask, PostgreSQL, Gunicorn, Nginx
**Purpose:** Sharing SUNO AI-generated music
**Repository:** https://github.com/richardahasting/hastingtx-music
