"""HastingTX Music - Flask application for sharing and managing music."""
import os
import zipfile
from io import BytesIO
from functools import wraps
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, abort
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
from PIL import Image

from config import config
from models import Song, Playlist, Rating, Comment, Subscriber, EmailLog, Genre, Tag, ActivityLog
from utils import (
    allowed_file, generate_identifier, extract_mp3_metadata, write_mp3_metadata,
    save_uploaded_file, is_ip_allowed, format_duration, format_file_size
)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(config)
config.init_app(app)


# IP whitelist decorator
def require_admin_ip(f):
    """Decorator to restrict access to whitelisted IPs."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr

        if not is_ip_allowed(client_ip, config.ADMIN_IP_WHITELIST):
            abort(403, description="Access denied: IP not whitelisted")

        return f(*args, **kwargs)
    return decorated_function


# Template context processor
@app.context_processor
def inject_admin_status():
    """Make admin IP status, playlists, albums, and genres available to all templates."""
    client_ip = request.remote_addr
    is_admin = is_ip_allowed(client_ip, config.ADMIN_IP_WHITELIST)
    # Get all playlists for navigation (exclude 'all' as it's shown separately)
    all_playlists = Playlist.get_all()
    nav_playlists = [p for p in all_playlists if p['identifier'] != 'all']
    # Get distinct albums for navigation
    albums = Song.get_distinct_albums()
    nav_albums = [a['album'] for a in albums if a['album']]
    # Get genres that have songs for navigation
    nav_genres = Genre.get_with_songs()
    # Get tags that have songs for navigation
    nav_tags = Tag.get_with_songs()
    return dict(is_admin_ip=is_admin, nav_playlists=nav_playlists, nav_albums=nav_albums, nav_genres=nav_genres, nav_tags=nav_tags)


# Request hooks for activity logging
@app.before_request
def log_page_visit():
    """Log page visits for stats tracking (excludes static files, API calls, and admin pages)."""
    path = request.path

    # Skip logging for certain paths
    skip_prefixes = (
        '/static/',
        '/api/',
        '/admin/',
        '/download/',
        '/favicon',
    )

    # Skip static files and API calls
    if any(path.startswith(prefix) for prefix in skip_prefixes):
        return

    # Skip if path ends with common static file extensions
    if path.endswith(('.css', '.js', '.ico', '.png', '.jpg', '.mp3', '.woff', '.woff2')):
        return

    # Log the page visit
    try:
        ActivityLog.log_event('visit', request.remote_addr, page_path=path, user_agent=request.user_agent.string)
    except Exception:
        pass  # Don't break the request if logging fails


# Template filters
@app.template_filter('duration')
def duration_filter(seconds):
    """Format duration for templates."""
    return format_duration(seconds)


@app.template_filter('filesize')
def filesize_filter(bytes_size):
    """Format file size for templates."""
    return format_file_size(bytes_size)


# Error handlers
@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return render_template('error.html', error="Page not found", code=404), 404


@app.errorhandler(403)
def forbidden(e):
    """Handle 403 errors."""
    return render_template('error.html', error=str(e.description), code=403), 403


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(e):
    """Handle file upload size errors."""
    return render_template('error.html',
                         error="File too large. Maximum size is 50MB.",
                         code=413), 413


# Public routes
@app.route('/')
def index():
    """Home page - redirect to all songs."""
    return redirect(url_for('playlist', identifier='all'))


@app.route('/music/')
@app.route('/music')
def music_home():
    """Redirect /music to all songs."""
    return redirect(url_for('playlist', identifier='all'))


@app.route('/music/<identifier>')
def song(identifier):
    """Display a single song player page."""
    song = Song.get_by_identifier(identifier)
    if not song:
        abort(404, description=f"Song '{identifier}' not found")

    # Track listen (both legacy counter and activity log)
    Song.increment_listen_count(song['id'])
    ActivityLog.log_event('play', request.remote_addr, song_id=song['id'], user_agent=request.user_agent.string)

    # Get rating stats
    rating_stats = Rating.get_song_stats(song['id'])
    user_rating = Rating.get_user_rating(song['id'], request.remote_addr)

    # Get comments
    comments = Comment.get_by_song(song['id'])
    comment_count = Comment.get_count(song['id'])

    # Get tags for this song
    song_tags = Tag.get_tags_for_song(song['id'])

    return render_template('song.html',
                         song=song,
                         avg_rating=rating_stats['avg_rating'] if rating_stats else None,
                         rating_count=rating_stats['rating_count'] if rating_stats else 0,
                         user_rating=user_rating['rating'] if user_rating else None,
                         comments=comments,
                         comment_count=comment_count,
                         song_tags=song_tags)


def get_song_tags_map(songs):
    """Get a map of song_id -> list of tags for a list of songs."""
    song_tags_map = {}
    for song in songs:
        tags = Tag.get_tags_for_song(song['id'])
        song_tags_map[song['id']] = tags
    return song_tags_map


@app.route('/music/playlist/<identifier>')
def playlist(identifier):
    """Display a playlist player page."""
    playlist = Playlist.get_by_identifier(identifier)
    if not playlist:
        abort(404, description=f"Playlist '{identifier}' not found")

    # Get songs in playlist
    songs = Playlist.get_songs(playlist['id'])

    # If this is the 'all' playlist, get all songs
    if identifier == 'all':
        songs = Song.get_all(order_by='title')

    # Get tags for each song
    song_tags_map = get_song_tags_map(songs)

    return render_template('playlist.html', playlist=playlist, songs=songs, song_tags_map=song_tags_map)


@app.route('/music/album/<path:album_name>')
def album(album_name):
    """Display all songs from an album."""
    # Get songs in the album
    songs = Song.get_by_album(album_name)

    if not songs:
        abort(404, description=f"Album '{album_name}' not found")

    # Create a virtual playlist object for the template
    album_playlist = {
        'id': None,
        'identifier': 'album-' + album_name.lower().replace(' ', '-'),
        'name': album_name,
        'description': f'All songs from the album "{album_name}"',
        'sort_order': 'title'
    }

    # Get tags for each song
    song_tags_map = get_song_tags_map(songs)

    return render_template('playlist.html', playlist=album_playlist, songs=songs, is_album=True, song_tags_map=song_tags_map)


@app.route('/music/genre/<path:genre_name>')
def genre(genre_name):
    """Display all songs in a genre."""
    # Get songs in the genre
    songs = Song.get_by_genre(genre_name)

    if not songs:
        abort(404, description=f"Genre '{genre_name}' not found or has no songs")

    # Get genre info for description
    genre_info = Genre.get_by_name(genre_name)
    genre_desc = genre_info['description'] if genre_info else None

    # Create a virtual playlist object for the template
    genre_playlist = {
        'id': None,
        'identifier': 'genre-' + genre_name.lower().replace(' ', '-'),
        'name': genre_name,
        'description': genre_desc or f'All songs in the {genre_name} genre',
        'sort_order': 'title'
    }

    # Get tags for each song
    song_tags_map = get_song_tags_map(songs)

    return render_template('playlist.html', playlist=genre_playlist, songs=songs, is_genre=True, song_tags_map=song_tags_map)


@app.route('/music/tag/<path:tag_name>')
def tag(tag_name):
    """Display all songs with a specific tag."""
    # Get songs with this tag
    songs = Song.get_by_tag(tag_name)

    if not songs:
        abort(404, description=f"Tag '{tag_name}' not found or has no songs")

    # Get tag info for description
    tag_info = Tag.get_by_name(tag_name)
    tag_desc = tag_info['description'] if tag_info else None

    # Create a virtual playlist object for the template
    tag_playlist = {
        'id': None,
        'identifier': 'tag-' + tag_name.lower().replace(' ', '-'),
        'name': f'#{tag_name}',
        'description': tag_desc or f'All songs tagged with #{tag_name}',
        'sort_order': 'title'
    }

    # Get tags for each song
    song_tags_map = get_song_tags_map(songs)

    return render_template('playlist.html', playlist=tag_playlist, songs=songs, is_tag=True, song_tags_map=song_tags_map)


@app.route('/download/song/<identifier>')
def download_song(identifier):
    """Download a single MP3 file."""
    song = Song.get_by_identifier(identifier)
    if not song:
        abort(404, description=f"Song '{identifier}' not found")

    file_path = os.path.join(config.UPLOAD_FOLDER, song['filename'])
    if not os.path.exists(file_path):
        abort(404, description="File not found on server")

    # Track download (both legacy counter and activity log)
    Song.increment_download_count(song['id'])
    ActivityLog.log_event('download', request.remote_addr, song_id=song['id'], user_agent=request.user_agent.string)

    # Use original filename or song title
    download_name = f"{song['title']}.mp3" if song['title'] else song['filename']

    return send_file(file_path, as_attachment=True, download_name=download_name)


@app.route('/download/playlist/<identifier>')
def download_playlist(identifier):
    """Download all songs in a playlist as a ZIP file."""
    playlist = Playlist.get_by_identifier(identifier)
    if not playlist:
        abort(404, description=f"Playlist '{identifier}' not found")

    # Get songs
    if identifier == 'all':
        songs = Song.get_all(order_by='title')
    else:
        songs = Playlist.get_songs(playlist['id'])

    if not songs:
        abort(404, description="No songs in playlist")

    # Create ZIP file in memory
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for song in songs:
            file_path = os.path.join(config.UPLOAD_FOLDER, song['filename'])
            if os.path.exists(file_path):
                # Use song title for filename in ZIP
                zip_filename = f"{song['title']}.mp3" if song['title'] else song['filename']
                zf.write(file_path, zip_filename)

    memory_file.seek(0)
    zip_name = f"{playlist['name']}.zip"

    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=zip_name
    )


# Admin routes (IP-restricted)
@app.route('/admin')
@require_admin_ip
def admin():
    """Admin dashboard."""
    songs = Song.get_all()
    playlists = Playlist.get_all()
    return render_template('admin.html', songs=songs, playlists=playlists)


@app.route('/admin/stats')
@require_admin_ip
def admin_stats():
    """Admin stats dashboard showing visitor and song activity."""
    # Get time filter from query string (default: 24 hours)
    hours = request.args.get('hours', 24, type=int)
    if hours not in [24, 168, 720]:  # 24h, 7d, 30d
        hours = 24

    # Get visitor stats
    visitor_stats = ActivityLog.get_visitor_stats()

    # Get song stats for the selected time period
    song_stats = ActivityLog.get_song_stats(hours=hours)

    # Get recent activity
    recent_activity = ActivityLog.get_recent_activity(limit=50)

    # Get top songs for the period
    top_songs = ActivityLog.get_top_songs(hours=hours, limit=10)

    return render_template('admin_stats.html',
                         visitor_stats=visitor_stats,
                         song_stats=song_stats,
                         recent_activity=recent_activity,
                         top_songs=top_songs,
                         selected_hours=hours)


@app.route('/admin/upload', methods=['GET', 'POST'])
@require_admin_ip
def upload():
    """Upload a new song."""
    if request.method == 'GET':
        playlists = Playlist.get_all()
        albums = Song.get_distinct_albums()
        album_names = [a['album'] for a in albums if a['album']]
        genres = Genre.get_all()
        tags = Tag.get_all()
        return render_template('upload.html', playlists=playlists, albums=album_names, genres=genres, tags=tags)

    # Handle POST - file upload
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only MP3 files allowed.'}), 400

    # Save file
    filename, filepath = save_uploaded_file(file, config.UPLOAD_FOLDER)
    if not filename:
        return jsonify({'error': 'Error saving file'}), 500

    # Extract comprehensive metadata from MP3 (including cover art)
    cover_art_dir = os.path.join(config.UPLOAD_FOLDER, 'covers')
    mp3_metadata = extract_mp3_metadata(filepath, save_cover_to=cover_art_dir)

    # Get form data, preferring form input over extracted metadata
    title = request.form.get('title') or mp3_metadata.get('title') or file.filename.rsplit('.', 1)[0]
    artist = request.form.get('artist') or mp3_metadata.get('artist')
    album = request.form.get('album') or mp3_metadata.get('album')
    description = request.form.get('description') or mp3_metadata.get('description')
    lyrics = request.form.get('lyrics') or mp3_metadata.get('lyrics')
    genre = request.form.get('genre') or mp3_metadata.get('genre')
    tags = request.form.get('tags')
    composer = request.form.get('composer') or mp3_metadata.get('composer') or 'Richard & Claude'
    lyricist = request.form.get('lyricist') or mp3_metadata.get('lyricist') or 'Richard & Claude'
    recording_date = request.form.get('recording_date') or mp3_metadata.get('recording_date')

    # Handle cover art upload if provided
    cover_art = mp3_metadata.get('cover_art')  # From MP3 file
    if 'cover_art' in request.files and request.files['cover_art'].filename:
        cover_file = request.files['cover_art']
        if cover_file.filename:
            cover_filename = secure_filename(f"{os.path.splitext(filename)[0]}_cover.jpg")
            cover_path = os.path.join(cover_art_dir, cover_filename)
            # Save and resize if needed
            img = Image.open(cover_file)
            if img.width > 500 or img.height > 500:
                img.thumbnail((500, 500), Image.Resampling.LANCZOS)
            img.save(cover_path, 'JPEG', quality=90)
            cover_art = cover_filename

    # Generate identifier
    identifier = request.form.get('identifier')
    if not identifier:
        identifier = generate_identifier(title)

    # Create song record
    try:
        song = Song.create(
            identifier=identifier,
            title=title,
            artist=artist,
            album=album,
            description=description,
            lyrics=lyrics,
            genre=genre,
            tags=tags,
            filename=filename,
            duration=mp3_metadata.get('duration'),
            file_size=mp3_metadata.get('file_size'),
            cover_art=cover_art,
            composer=composer,
            lyricist=lyricist,
            recording_date=recording_date
        )

        # Write comprehensive metadata back to MP3 file
        song_url = request.url_root.rstrip('/') + url_for('song', identifier=song['identifier'])
        song_data = {
            'title': title,
            'artist': artist,
            'album': album,
            'genre': genre,
            'description': description,
            'lyrics': lyrics,
            'composer': composer,
            'lyricist': lyricist,
            'recording_date': recording_date
        }
        if cover_art:
            song_data['cover_art_path'] = os.path.join(cover_art_dir, cover_art)

        write_mp3_metadata(filepath, song_data, song_url=song_url)

        # Add to 'all' playlist
        all_playlist = Playlist.get_by_identifier('all')
        if all_playlist:
            Playlist.add_song(all_playlist['id'], song['id'])

        # Auto-add to album playlist if album is specified
        if album:
            album_playlist = Playlist.get_or_create_album_playlist(album)
            if album_playlist:
                Playlist.add_song(album_playlist['id'], song['id'])

        # Add to selected playlists
        playlist_ids = request.form.getlist('playlists[]')
        for playlist_id in playlist_ids:
            if playlist_id:
                Playlist.add_song(int(playlist_id), song['id'])

        # Add selected tags
        tag_ids = request.form.getlist('tags[]')
        for tag_id in tag_ids:
            if tag_id:
                Tag.add_song_tag(song['id'], int(tag_id))

        return jsonify({
            'success': True,
            'song': dict(song),
            'url': url_for('song', identifier=song['identifier'])
        })

    except Exception as e:
        # Clean up file on error
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': str(e)}), 500


@app.route('/admin/songs/<int:song_id>/edit', methods=['GET', 'POST'])
@require_admin_ip
def edit_song(song_id):
    """Edit song metadata."""
    song = Song.get_by_id(song_id)
    if not song:
        abort(404, description="Song not found")

    if request.method == 'GET':
        playlists = Playlist.get_all()
        song_playlists = Playlist.get_playlists_for_song(song_id)
        song_playlist_ids = [p['id'] for p in song_playlists]
        genres = Genre.get_all()
        tags = Tag.get_all()
        song_tags = Tag.get_tags_for_song(song_id)
        song_tag_ids = [t['id'] for t in song_tags]
        return render_template('edit_song.html', song=song, playlists=playlists, song_playlist_ids=song_playlist_ids, genres=genres, tags=tags, song_tag_ids=song_tag_ids)

    # Handle POST - update metadata
    try:
        update_data = {}

        # Update fields if provided
        if request.form.get('title'):
            update_data['title'] = request.form.get('title')
        if request.form.get('artist'):
            update_data['artist'] = request.form.get('artist')
        if request.form.get('album'):
            update_data['album'] = request.form.get('album')
        if 'description' in request.form:
            update_data['description'] = request.form.get('description')
        if 'lyrics' in request.form:
            update_data['lyrics'] = request.form.get('lyrics')
        if request.form.get('genre'):
            update_data['genre'] = request.form.get('genre')
        if 'tags' in request.form:
            update_data['tags'] = request.form.get('tags')
        if request.form.get('identifier'):
            update_data['identifier'] = request.form.get('identifier')
        if request.form.get('composer'):
            update_data['composer'] = request.form.get('composer')
        if request.form.get('lyricist'):
            update_data['lyricist'] = request.form.get('lyricist')
        if request.form.get('recording_date'):
            update_data['recording_date'] = request.form.get('recording_date')

        # Handle cover art upload if provided
        cover_art_dir = os.path.join(config.UPLOAD_FOLDER, 'covers')
        if 'cover_art' in request.files and request.files['cover_art'].filename:
            cover_file = request.files['cover_art']
            if cover_file.filename:
                cover_filename = secure_filename(f"{os.path.splitext(song['filename'])[0]}_cover.jpg")
                cover_path = os.path.join(cover_art_dir, cover_filename)
                # Save and resize if needed
                img = Image.open(cover_file)
                if img.width > 500 or img.height > 500:
                    img.thumbnail((500, 500), Image.Resampling.LANCZOS)
                img.save(cover_path, 'JPEG', quality=90)
                update_data['cover_art'] = cover_filename

        # Update the song in database
        updated_song = Song.update(song_id, **update_data)

        # Write comprehensive metadata back to MP3 file
        filepath = os.path.join(config.UPLOAD_FOLDER, updated_song['filename'])
        song_url = request.url_root.rstrip('/') + url_for('song', identifier=updated_song['identifier'])
        song_data = {
            'title': updated_song.get('title'),
            'artist': updated_song.get('artist'),
            'album': updated_song.get('album'),
            'genre': updated_song.get('genre'),
            'description': updated_song.get('description'),
            'lyrics': updated_song.get('lyrics'),
            'composer': updated_song.get('composer'),
            'lyricist': updated_song.get('lyricist'),
            'recording_date': updated_song.get('recording_date')
        }
        if updated_song.get('cover_art'):
            song_data['cover_art_path'] = os.path.join(cover_art_dir, updated_song['cover_art'])

        write_mp3_metadata(filepath, song_data, song_url=song_url)

        # Update playlist memberships
        playlist_ids = request.form.getlist('playlists[]')
        playlist_ids = [int(pid) for pid in playlist_ids if pid]
        Playlist.set_song_playlists(song_id, playlist_ids)

        # Update tag memberships
        tag_ids = request.form.getlist('tags[]')
        tag_ids = [int(tid) for tid in tag_ids if tid]
        Tag.set_song_tags(song_id, tag_ids)

        return jsonify({
            'success': True,
            'song': dict(updated_song),
            'url': url_for('song', identifier=updated_song['identifier'])
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/playlists/create', methods=['POST'])
@require_admin_ip
def create_playlist():
    """Create a new playlist."""
    data = request.get_json()

    name = data.get('name')
    if not name:
        return jsonify({'error': 'Playlist name required'}), 400

    identifier = data.get('identifier', generate_identifier(name))
    description = data.get('description')
    sort_order = data.get('sort_order', 'manual')

    try:
        playlist = Playlist.create(
            identifier=identifier,
            name=name,
            description=description,
            sort_order=sort_order
        )
        return jsonify({'success': True, 'playlist': dict(playlist)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/playlists/<int:playlist_id>/add_song', methods=['POST'])
@require_admin_ip
def add_song_to_playlist(playlist_id):
    """Add a song to a playlist."""
    data = request.get_json()
    song_id = data.get('song_id')

    if not song_id:
        return jsonify({'error': 'Song ID required'}), 400

    try:
        Playlist.add_song(playlist_id, song_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/playlists/<int:playlist_id>/remove_song', methods=['POST'])
@require_admin_ip
def remove_song_from_playlist(playlist_id):
    """Remove a song from a playlist."""
    data = request.get_json()
    song_id = data.get('song_id')

    if not song_id:
        return jsonify({'error': 'Song ID required'}), 400

    try:
        Playlist.remove_song(playlist_id, song_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/playlists/<int:playlist_id>/reorder', methods=['POST'])
@require_admin_ip
def reorder_playlist(playlist_id):
    """Reorder songs in a playlist."""
    data = request.get_json()
    song_order = data.get('song_order')  # List of song IDs in new order

    if not song_order:
        return jsonify({'error': 'Song order required'}), 400

    try:
        # Convert to (song_id, position) tuples
        positions = [(song_id, idx + 1) for idx, song_id in enumerate(song_order)]
        Playlist.reorder_songs(playlist_id, positions)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/playlists/<int:playlist_id>/set_songs', methods=['POST'])
@require_admin_ip
def set_playlist_songs(playlist_id):
    """Set which songs are in a playlist."""
    data = request.get_json()
    song_ids = data.get('song_ids', [])

    try:
        playlist = Playlist.get_by_id(playlist_id)
        if not playlist:
            return jsonify({'error': 'Playlist not found'}), 404

        # Get current songs
        current_songs = Playlist.get_songs(playlist_id)
        current_ids = {s['id'] for s in current_songs}
        new_ids = set(song_ids)

        # Remove songs no longer in list
        for song_id in current_ids - new_ids:
            Playlist.remove_song(playlist_id, song_id)

        # Add new songs
        for song_id in new_ids - current_ids:
            Playlist.add_song(playlist_id, song_id)

        return jsonify({'success': True, 'count': len(song_ids)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/playlists/<int:playlist_id>', methods=['DELETE'])
@require_admin_ip
def delete_playlist(playlist_id):
    """Delete a playlist."""
    try:
        Playlist.delete(playlist_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/songs/<int:song_id>', methods=['DELETE'])
@require_admin_ip
def delete_song(song_id):
    """Delete a song."""
    song = Song.get_by_id(song_id)
    if not song:
        return jsonify({'error': 'Song not found'}), 404

    try:
        # Delete file
        file_path = os.path.join(config.UPLOAD_FOLDER, song['filename'])
        if os.path.exists(file_path):
            os.remove(file_path)

        # Delete database record
        Song.delete(song_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# API routes for AJAX requests
@app.route('/api/songs')
def api_songs():
    """Get all songs as JSON."""
    songs = Song.get_all()
    return jsonify([dict(song) for song in songs])


@app.route('/api/playlists')
def api_playlists():
    """Get all playlists as JSON."""
    playlists = Playlist.get_all()
    return jsonify([dict(playlist) for playlist in playlists])


@app.route('/api/playlists/<identifier>/songs')
def api_playlist_songs(identifier):
    """Get songs in a playlist as JSON."""
    playlist = Playlist.get_by_identifier(identifier)
    if not playlist:
        return jsonify({'error': 'Playlist not found'}), 404

    if identifier == 'all':
        songs = Song.get_all(order_by='title')
    else:
        songs = Playlist.get_songs(playlist['id'])

    return jsonify([dict(song) for song in songs])


@app.route('/api/playlists/<int:playlist_id>/song_ids')
def api_playlist_song_ids(playlist_id):
    """Get song IDs in a playlist as JSON."""
    playlist = Playlist.get_by_id(playlist_id)
    if not playlist:
        return jsonify({'error': 'Playlist not found'}), 404

    songs = Playlist.get_songs(playlist_id)
    return jsonify({'song_ids': [song['id'] for song in songs]})


@app.route('/api/songs/<int:song_id>/listen', methods=['POST'])
def record_listen(song_id):
    """Record a listen for a song (called from playlist player after 10+ seconds)."""
    try:
        song = Song.get_by_id(song_id)
        if not song:
            return jsonify({'error': 'Song not found'}), 404

        Song.increment_listen_count(song_id)
        ActivityLog.log_event('play', request.remote_addr, song_id=song_id, user_agent=request.user_agent.string)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/songs/<int:song_id>/rate', methods=['POST'])
def rate_song(song_id):
    """Submit a rating for a song."""
    data = request.get_json()
    rating_value = data.get('rating')

    if not rating_value or not isinstance(rating_value, int) or rating_value < 1 or rating_value > 10:
        return jsonify({'error': 'Rating must be an integer between 1 and 10'}), 400

    try:
        Rating.submit_rating(song_id, request.remote_addr, rating_value)

        # Get updated stats
        stats = Rating.get_song_stats(song_id)

        return jsonify({
            'success': True,
            'avg_rating': float(stats['avg_rating']) if stats['avg_rating'] else None,
            'rating_count': stats['rating_count']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/songs/<int:song_id>/comments', methods=['POST'])
def submit_comment(song_id):
    """Submit a comment on a song."""
    data = request.get_json()
    comment_text = data.get('comment_text', '').strip()
    commenter_name = data.get('commenter_name', '').strip() or None

    if not comment_text:
        return jsonify({'error': 'Comment text is required'}), 400

    if len(comment_text) > 2000:
        return jsonify({'error': 'Comment must be 2000 characters or less'}), 400

    try:
        # Check if song exists
        song = Song.get_by_id(song_id)
        if not song:
            return jsonify({'error': 'Song not found'}), 404

        # Create comment
        comment = Comment.create(
            song_id=song_id,
            comment_text=comment_text,
            ip_address=request.remote_addr,
            commenter_name=commenter_name
        )

        return jsonify({
            'success': True,
            'comment': {
                'id': comment['id'],
                'commenter_name': comment['commenter_name'],
                'comment_text': comment['comment_text'],
                'created_at': comment['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@require_admin_ip
def delete_comment(comment_id):
    """Delete a comment (admin only)."""
    try:
        comment = Comment.get_by_id(comment_id)
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404

        Comment.delete(comment_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/genres')
def api_genres():
    """Get all genres as JSON."""
    genres = Genre.get_all()
    return jsonify([dict(g) for g in genres])


@app.route('/api/genres', methods=['POST'])
@require_admin_ip
def create_genre():
    """Create a new genre."""
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip() or None
    parent_genre_id = data.get('parent_genre_id')

    if not name:
        return jsonify({'error': 'Genre name is required'}), 400

    # Check for case-insensitive duplicate
    existing = Genre.get_all()
    for g in existing:
        if g['name'].lower() == name.lower():
            return jsonify({'error': f'Genre "{g["name"]}" already exists'}), 400

    try:
        genre = Genre.create(name, description, parent_genre_id)
        return jsonify({'success': True, 'genre': dict(genre)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tags')
def api_tags():
    """Get all tags as JSON."""
    tags = Tag.get_all()
    return jsonify([dict(t) for t in tags])


@app.route('/api/tags', methods=['POST'])
@require_admin_ip
def create_tag():
    """Create a new tag."""
    data = request.get_json()
    name = data.get('name', '').strip().lower()
    description = data.get('description', '').strip() or None

    if not name:
        return jsonify({'error': 'Tag name is required'}), 400

    # Check for case-insensitive duplicate
    existing = Tag.get_by_name(name)
    if existing:
        return jsonify({'error': f'Tag "{existing["name"]}" already exists'}), 400

    try:
        tag = Tag.create(name, description)
        return jsonify({'success': True, 'tag': dict(tag)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    """Subscribe to email notifications."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': 'Email address is required'}), 400

    # Basic email validation
    import re
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return jsonify({'error': 'Invalid email address'}), 400

    try:
        # Check if already subscribed
        existing = Subscriber.get_by_email(email)

        if existing and existing['is_active']:
            return jsonify({
                'success': True,
                'message': 'This email is already subscribed to our weekly updates!'
            })

        # Create new subscription or re-activate
        subscriber = Subscriber.create(email)

        if existing and not existing['is_active']:
            # Was previously unsubscribed, now re-activated
            message = 'Welcome back! Your subscription has been reactivated.'
        else:
            # New subscriber
            message = 'Successfully subscribed! You\'ll receive weekly updates about new songs.'

        return jsonify({
            'success': True,
            'message': message
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/unsubscribe/<token>')
def unsubscribe(token):
    """Unsubscribe from email notifications."""
    try:
        subscriber = Subscriber.get_by_token(token)
        if not subscriber:
            return render_template('error.html',
                                 error="Invalid unsubscribe link",
                                 code=404), 404

        Subscriber.unsubscribe(token)
        return render_template('unsubscribe.html', email=subscriber['email'])
    except Exception as e:
        return render_template('error.html',
                             error=str(e),
                             code=500), 500


# ============================================================================
# GALLERY ROUTES - Letters From Dick Image Gallery
# ============================================================================

from gallery_models import GallerySection, GalleryImage
from gallery_utils import (
    allowed_image_file, generate_gallery_identifier, process_uploaded_image,
    delete_image_files, format_date_for_display, parse_date_input
)

# Gallery directories
GALLERY_IMAGES_DIR = os.path.join(config.UPLOAD_FOLDER, 'gallery', 'images')
GALLERY_THUMBNAILS_DIR = os.path.join(config.UPLOAD_FOLDER, 'gallery', 'thumbnails')


# Public gallery routes
@app.route('/letters-from-dick')
@app.route('/letters-from-dick/')
def gallery_index():
    """Main gallery page - grid of all images."""
    # Get filter parameters
    section_filter = request.args.get('section')
    date_filter = request.args.get('date')
    sort_by = request.args.get('sort', 'date')  # date, title, upload

    # Get sections for filter dropdown
    sections = GallerySection.get_with_counts()

    # Get images based on filters
    if section_filter:
        section = GallerySection.get_by_identifier(section_filter)
        if section:
            images = GalleryImage.get_by_section(section['id'])
        else:
            images = []
    elif date_filter:
        parsed_date = parse_date_input(date_filter)
        if parsed_date:
            images = GalleryImage.get_by_date(parsed_date)
        else:
            images = []
    else:
        # Get all images
        if sort_by == 'title':
            images = GalleryImage.get_all(order_by='title, significance_date')
        elif sort_by == 'upload':
            images = GalleryImage.get_all(order_by='upload_date DESC')
        else:  # date (default)
            images = GalleryImage.get_all(order_by='significance_date DESC NULLS LAST, upload_date DESC')

    return render_template('gallery/index.html',
                         images=images,
                         sections=sections,
                         current_section=section_filter,
                         current_date=date_filter,
                         current_sort=sort_by)


@app.route('/letters-from-dick/section/<identifier>')
def gallery_section(identifier):
    """Display images in a specific section."""
    section = GallerySection.get_by_identifier(identifier)
    if not section:
        abort(404, description=f"Section '{identifier}' not found")

    images = GalleryImage.get_by_section(section['id'])
    sections = GallerySection.get_with_counts()

    return render_template('gallery/section.html',
                         section=section,
                         images=images,
                         sections=sections)


@app.route('/letters-from-dick/image/<identifier>')
def gallery_image(identifier):
    """Display a single image with full details."""
    image = GalleryImage.get_by_identifier(identifier)
    if not image:
        abort(404, description=f"Image '{identifier}' not found")

    # Track view
    GalleryImage.increment_view_count(image['id'])

    # Get section info if assigned
    section = None
    if image['section_id']:
        section = GallerySection.get_by_id(image['section_id'])

    # Get prev/next for navigation
    prev_img, next_img = GalleryImage.get_navigation(image['id'], image['section_id'])

    return render_template('gallery/image.html',
                         image=image,
                         section=section,
                         prev_image=prev_img,
                         next_image=next_img)


@app.route('/letters-from-dick/date/<date_str>')
def gallery_by_date(date_str):
    """Display all images for a specific date."""
    parsed_date = parse_date_input(date_str)
    if not parsed_date:
        abort(404, description=f"Invalid date format: {date_str}")

    images = GalleryImage.get_by_date(parsed_date)
    sections = GallerySection.get_with_counts()

    return render_template('gallery/index.html',
                         images=images,
                         sections=sections,
                         current_date=date_str,
                         date_display=format_date_for_display(parsed_date))


@app.route('/letters-from-dick/download/<identifier>')
def gallery_download(identifier):
    """Download full-size image."""
    image = GalleryImage.get_by_identifier(identifier)
    if not image:
        abort(404, description=f"Image '{identifier}' not found")

    file_path = os.path.join(GALLERY_IMAGES_DIR, image['filename'])
    if not os.path.exists(file_path):
        abort(404, description="File not found on server")

    # Use title for download name
    ext = image['file_type'] or 'jpg'
    download_name = f"{image['title']}.{ext}" if image['title'] else image['filename']

    return send_file(file_path, as_attachment=True, download_name=download_name)


# Admin gallery routes
@app.route('/admin/gallery')
@require_admin_ip
def admin_gallery():
    """Gallery admin dashboard."""
    images = GalleryImage.get_with_section()
    sections = GallerySection.get_with_counts()
    total_images = GalleryImage.get_count()

    return render_template('gallery/admin.html',
                         images=images,
                         sections=sections,
                         total_images=total_images)


@app.route('/admin/gallery/upload', methods=['GET', 'POST'])
@require_admin_ip
def gallery_upload():
    """Upload a new gallery image."""
    if request.method == 'GET':
        sections = GallerySection.get_all()
        return render_template('upload_image.html', sections=sections)

    # Handle POST - file upload
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_image_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: JPG, PNG, GIF, WebP, PDF'}), 400

    # Process uploaded image
    file_info = process_uploaded_image(file, GALLERY_IMAGES_DIR, GALLERY_THUMBNAILS_DIR)
    if not file_info:
        return jsonify({'error': 'Error processing image'}), 500

    # Get form data
    title = request.form.get('title') or file.filename.rsplit('.', 1)[0]
    description = request.form.get('description')
    significance_date = request.form.get('significance_date')
    source = request.form.get('source')
    section_id = request.form.get('section_id')

    # Parse date
    if significance_date:
        significance_date = parse_date_input(significance_date)

    # Parse section_id
    if section_id:
        section_id = int(section_id) if section_id.isdigit() else None

    # Generate identifier
    identifier = request.form.get('identifier')
    if not identifier:
        identifier = generate_gallery_identifier(title)

    # Ensure unique identifier
    existing = GalleryImage.get_by_identifier(identifier)
    if existing:
        counter = 1
        base_identifier = identifier
        while existing:
            identifier = f"{base_identifier}-{counter}"
            existing = GalleryImage.get_by_identifier(identifier)
            counter += 1

    try:
        image = GalleryImage.create(
            identifier=identifier,
            title=title,
            filename=file_info['filename'],
            file_type=file_info['file_type'],
            file_size=file_info['file_size'],
            description=description,
            significance_date=significance_date,
            source=source,
            thumbnail=file_info['thumbnail'],
            width=file_info['width'],
            height=file_info['height'],
            section_id=section_id
        )

        return jsonify({
            'success': True,
            'image': dict(image),
            'url': url_for('gallery_image', identifier=image['identifier'])
        })

    except Exception as e:
        # Clean up files on error
        delete_image_files(file_info['filename'], file_info['thumbnail'],
                          GALLERY_IMAGES_DIR, GALLERY_THUMBNAILS_DIR)
        return jsonify({'error': str(e)}), 500


@app.route('/admin/gallery/images/<int:image_id>/edit', methods=['GET', 'POST'])
@require_admin_ip
def edit_gallery_image(image_id):
    """Edit gallery image metadata."""
    image = GalleryImage.get_by_id(image_id)
    if not image:
        abort(404, description="Image not found")

    if request.method == 'GET':
        sections = GallerySection.get_all()
        return render_template('gallery/edit_image.html', image=image, sections=sections)

    # Handle POST - update metadata
    try:
        update_data = {}

        if request.form.get('title'):
            update_data['title'] = request.form.get('title')
        if 'description' in request.form:
            update_data['description'] = request.form.get('description')
        if request.form.get('significance_date'):
            update_data['significance_date'] = parse_date_input(request.form.get('significance_date'))
        if 'source' in request.form:
            update_data['source'] = request.form.get('source')
        if 'section_id' in request.form:
            section_id = request.form.get('section_id')
            update_data['section_id'] = int(section_id) if section_id and section_id.isdigit() else None
        if request.form.get('identifier'):
            update_data['identifier'] = request.form.get('identifier')

        updated_image = GalleryImage.update(image_id, **update_data)

        return jsonify({
            'success': True,
            'image': dict(updated_image),
            'url': url_for('gallery_image', identifier=updated_image['identifier'])
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/gallery/images/<int:image_id>', methods=['DELETE'])
@require_admin_ip
def delete_gallery_image(image_id):
    """Delete a gallery image."""
    image = GalleryImage.get_by_id(image_id)
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    try:
        # Delete files
        delete_image_files(image['filename'], image['thumbnail'],
                          GALLERY_IMAGES_DIR, GALLERY_THUMBNAILS_DIR)

        # Delete database record
        GalleryImage.delete(image_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/gallery/images/<int:image_id>/move', methods=['POST'])
@require_admin_ip
def move_gallery_image(image_id):
    """Move an image to a different section."""
    data = request.get_json()
    section_id = data.get('section_id')

    try:
        GalleryImage.move_to_section(image_id, section_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/gallery/sections/create', methods=['POST'])
@require_admin_ip
def create_gallery_section():
    """Create a new gallery section."""
    data = request.get_json()

    name = data.get('name')
    if not name:
        return jsonify({'error': 'Section name required'}), 400

    identifier = data.get('identifier', generate_gallery_identifier(name))
    description = data.get('description')
    sort_order = data.get('sort_order', 0)

    try:
        section = GallerySection.create(
            identifier=identifier,
            name=name,
            description=description,
            sort_order=sort_order
        )
        return jsonify({'success': True, 'section': dict(section)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/gallery/sections/<int:section_id>', methods=['DELETE'])
@require_admin_ip
def delete_gallery_section(section_id):
    """Delete a gallery section."""
    try:
        GallerySection.delete(section_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Gallery API routes
@app.route('/api/gallery/images')
def api_gallery_images():
    """Get all gallery images as JSON."""
    images = GalleryImage.get_all()
    return jsonify([dict(img) for img in images])


@app.route('/api/gallery/images/date/<date_str>')
def api_gallery_images_by_date(date_str):
    """Get gallery images for a specific date as JSON (for book integration)."""
    parsed_date = parse_date_input(date_str)
    if not parsed_date:
        return jsonify({'error': 'Invalid date format'}), 400

    images = GalleryImage.get_by_date(parsed_date)

    # Format for book integration
    result = []
    for img in images:
        result.append({
            'id': img['id'],
            'identifier': img['identifier'],
            'title': img['title'],
            'description': img['description'],
            'significance_date': str(img['significance_date']) if img['significance_date'] else None,
            'source': img['source'],
            'thumbnail_url': url_for('static', filename=f'uploads/gallery/thumbnails/{img["thumbnail"]}') if img['thumbnail'] else None,
            'image_url': url_for('static', filename=f'uploads/gallery/images/{img["filename"]}'),
            'page_url': url_for('gallery_image', identifier=img['identifier']),
            'width': img['width'],
            'height': img['height']
        })

    return jsonify({
        'date': str(parsed_date),
        'count': len(result),
        'images': result
    })


@app.route('/api/gallery/sections')
def api_gallery_sections():
    """Get all gallery sections as JSON."""
    sections = GallerySection.get_with_counts()
    return jsonify([dict(s) for s in sections])


# ============================================================================
# DEVOTIONAL ROUTES - Pull The Thread Devotional Series
# ============================================================================

from devotional_models import (
    DevotionalThread, Devotional, DevotionalProgress,
    DevotionalSubscriber, DevotionalEnrollment
)
from devotional_utils import (
    generate_devotional_audio, format_duration as format_audio_duration,
    generate_identifier as generate_devotional_identifier,
    process_cover_image, ensure_directories as ensure_devotional_directories
)

# Ensure directories exist
ensure_devotional_directories()

# Devotional directories
DEVOTIONAL_AUDIO_DIR = os.path.join(config.UPLOAD_FOLDER, 'devotionals', 'audio')
DEVOTIONAL_COVERS_DIR = os.path.join(config.UPLOAD_FOLDER, 'devotionals', 'covers')


def get_user_identifier():
    """Get unique user identifier from session or create one."""
    from flask import session
    if 'devotional_user_id' not in session:
        import uuid
        session['devotional_user_id'] = str(uuid.uuid4())
    session.permanent = True  # Make session last 1 year
    return session['devotional_user_id']


# Public devotional routes
@app.route('/devotionals')
@app.route('/devotionals/')
def devotionals_index():
    """List all published devotional threads."""
    # Get search and sort parameters
    search_query = request.args.get('q', '').strip()
    reverse_sort = request.args.get('reverse') == '1'

    threads = DevotionalThread.get_all(
        published_only=True,
        search=search_query if search_query else None,
        reverse=reverse_sort
    )

    # Add progress info for current user
    user_id = get_user_identifier()
    for thread in threads:
        progress = DevotionalProgress.get(thread['id'], user_id)
        if progress:
            thread['user_progress'] = progress
            thread['is_complete'] = DevotionalProgress.is_thread_complete(thread['id'], user_id)
        else:
            thread['user_progress'] = None
            thread['is_complete'] = False

    return render_template('devotionals/index.html',
                         threads=threads,
                         search_query=search_query,
                         reverse_sort=reverse_sort)


@app.route('/devotionals/<identifier>')
def devotional_thread(identifier):
    """Thread overview/start page."""
    thread = DevotionalThread.get_by_identifier(identifier)
    if not thread:
        abort(404, description=f"Thread '{identifier}' not found")

    if not thread['is_published']:
        # Only admins can view unpublished
        if not is_ip_allowed(request.remote_addr, config.ADMIN_IP_WHITELIST):
            abort(404, description=f"Thread '{identifier}' not found")

    # Get devotionals for this thread
    devotionals = DevotionalThread.get_devotionals(thread['id'])

    # Get user progress
    user_id = get_user_identifier()
    progress = DevotionalProgress.get(thread['id'], user_id)
    is_complete = DevotionalProgress.is_thread_complete(thread['id'], user_id) if progress else False

    return render_template('devotionals/thread.html',
                         thread=thread,
                         devotionals=devotionals,
                         progress=progress,
                         is_complete=is_complete)


@app.route('/devotionals/<identifier>/day/<int:day_number>')
def devotional_day(identifier, day_number):
    """View a specific day's devotional."""
    thread = DevotionalThread.get_by_identifier(identifier)
    if not thread:
        abort(404, description=f"Thread '{identifier}' not found")

    if not thread['is_published']:
        if not is_ip_allowed(request.remote_addr, config.ADMIN_IP_WHITELIST):
            abort(404, description=f"Thread '{identifier}' not found")

    # Get the devotional
    devotional = Devotional.get_by_thread_and_day(thread['id'], day_number)
    if not devotional:
        abort(404, description=f"Day {day_number} not found")

    # Check if user can access this day
    user_id = get_user_identifier()
    if day_number > 1:
        if not DevotionalProgress.is_day_accessible(thread['id'], user_id, day_number):
            # Redirect to their current day
            progress = DevotionalProgress.get(thread['id'], user_id)
            current_day = progress['current_day'] if progress else 1
            return redirect(url_for('devotional_day', identifier=identifier, day_number=current_day))

    # Get or create progress
    progress = DevotionalProgress.get_or_create(thread['id'], user_id)

    # Check if this day is completed
    is_day_complete = day_number in (progress['completed_days'] or [])

    # Get prev/next navigation
    prev_day = day_number - 1 if day_number > 1 else None
    next_day = day_number + 1 if day_number < thread['total_days'] else None

    # Can only go to next if current is complete
    next_accessible = next_day and is_day_complete

    return render_template('devotionals/day.html',
                         thread=thread,
                         devotional=devotional,
                         progress=progress,
                         is_day_complete=is_day_complete,
                         prev_day=prev_day,
                         next_day=next_day,
                         next_accessible=next_accessible)


@app.route('/devotionals/<identifier>/start', methods=['POST'])
def start_devotional_thread(identifier):
    """Start a thread (create progress record)."""
    thread = DevotionalThread.get_by_identifier(identifier)
    if not thread:
        return jsonify({'error': 'Thread not found'}), 404

    user_id = get_user_identifier()
    progress = DevotionalProgress.get_or_create(thread['id'], user_id)

    return jsonify({
        'success': True,
        'redirect': url_for('devotional_day', identifier=identifier, day_number=1)
    })


@app.route('/devotionals/<identifier>/day/<int:day_number>/complete', methods=['POST'])
def complete_devotional_day(identifier, day_number):
    """Mark a day as complete."""
    thread = DevotionalThread.get_by_identifier(identifier)
    if not thread:
        return jsonify({'error': 'Thread not found'}), 404

    user_id = get_user_identifier()

    # Verify user has started this thread
    progress = DevotionalProgress.get(thread['id'], user_id)
    if not progress:
        return jsonify({'error': 'Thread not started'}), 400

    # Verify this is the current day or already completed
    if day_number not in progress['completed_days'] and day_number != progress['current_day']:
        return jsonify({'error': 'Cannot complete this day yet'}), 400

    # Mark complete
    next_day = DevotionalProgress.mark_day_complete(thread['id'], user_id, day_number)

    # Check if thread is now complete
    is_thread_complete = DevotionalProgress.is_thread_complete(thread['id'], user_id)

    if is_thread_complete:
        redirect_url = url_for('devotional_complete', identifier=identifier)
    elif next_day <= thread['total_days']:
        redirect_url = url_for('devotional_day', identifier=identifier, day_number=next_day)
    else:
        redirect_url = url_for('devotional_complete', identifier=identifier)

    return jsonify({
        'success': True,
        'next_day': next_day,
        'is_thread_complete': is_thread_complete,
        'redirect': redirect_url
    })


@app.route('/devotionals/<identifier>/complete')
def devotional_complete(identifier):
    """Thread completion page."""
    thread = DevotionalThread.get_by_identifier(identifier)
    if not thread:
        abort(404, description=f"Thread '{identifier}' not found")

    user_id = get_user_identifier()
    is_complete = DevotionalProgress.is_thread_complete(thread['id'], user_id)

    # Get other available threads to suggest
    all_threads = DevotionalThread.get_all(published_only=True)
    other_threads = [t for t in all_threads if t['identifier'] != identifier]

    return render_template('devotionals/complete.html',
                         thread=thread,
                         is_complete=is_complete,
                         other_threads=other_threads)


# Devotional email routes
@app.route('/devotionals/subscribe', methods=['POST'])
def devotional_subscribe():
    """Subscribe for email delivery of a thread."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    name = data.get('name', '').strip() or None
    thread_identifier = data.get('thread_identifier')
    receive_new_threads = data.get('receive_new_threads', True)

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    # Basic email validation
    import re
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return jsonify({'error': 'Invalid email address'}), 400

    try:
        # Create or update subscriber
        subscriber = DevotionalSubscriber.create(email, name, receive_new_threads)

        # If thread specified, create enrollment
        if thread_identifier:
            thread = DevotionalThread.get_by_identifier(thread_identifier)
            if thread:
                DevotionalEnrollment.create(subscriber['id'], thread['id'])

        return jsonify({
            'success': True,
            'message': 'Successfully subscribed! You\'ll receive your first devotional shortly.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/devotionals/unsubscribe/<token>')
def devotional_unsubscribe(token):
    """Unsubscribe from devotional emails."""
    subscriber = DevotionalSubscriber.get_by_token(token)
    if not subscriber:
        return render_template('error.html',
                             error="Invalid unsubscribe link",
                             code=404), 404

    DevotionalSubscriber.unsubscribe(token)
    return render_template('devotionals/unsubscribed.html', email=subscriber['email'])


@app.route('/devotionals/save-progress', methods=['POST'])
def devotional_save_progress():
    """Save progress via email - sends sync link."""
    from devotional_utils import send_sync_email

    data = request.get_json()
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    # Basic email validation
    import re
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return jsonify({'error': 'Invalid email address'}), 400

    # Get current user identifier
    user_id = get_user_identifier()

    # Check if subscriber exists
    existing = DevotionalSubscriber.get_by_email(email)

    if existing:
        # Rate limiting - check if we recently sent an email
        if not DevotionalSubscriber.can_send_sync_email(email, minutes=15):
            return jsonify({
                'success': True,
                'message': 'A sync link was recently sent to this email. Please check your inbox (and spam folder).'
            })

        # Update user_identifier if not set
        if not existing['user_identifier']:
            DevotionalSubscriber.link_user_identifier(email, user_id)

        # Send sync email
        if send_sync_email(email, existing['unsubscribe_token']):
            DevotionalSubscriber.update_sync_email_sent(email)
            return jsonify({
                'success': True,
                'message': 'Sync link sent! Check your email to access your progress from any device.'
            })
        else:
            return jsonify({'error': 'Failed to send email. Please try again.'}), 500
    else:
        # Create new subscriber with user_identifier
        subscriber = DevotionalSubscriber.create(email, user_identifier=user_id)
        if subscriber:
            if send_sync_email(email, subscriber['unsubscribe_token']):
                DevotionalSubscriber.update_sync_email_sent(email)
                return jsonify({
                    'success': True,
                    'message': 'Sync link sent! Check your email to access your progress from any device.'
                })
            else:
                return jsonify({'error': 'Failed to send email. Please try again.'}), 500
        else:
            return jsonify({'error': 'Failed to save. Please try again.'}), 500


@app.route('/devotionals/sync/<token>')
def devotional_sync(token):
    """Sync progress from email link - sets user's session to match subscriber's progress."""
    subscriber = DevotionalSubscriber.get_by_token(token)
    if not subscriber:
        return render_template('error.html',
                             error="Invalid or expired sync link",
                             code=404), 404

    if not subscriber['user_identifier']:
        # No progress to sync - just set up fresh
        new_user_id = get_user_identifier()
        DevotionalSubscriber.link_user_identifier(subscriber['email'], new_user_id)
        flash_message = "Your email is now linked. Your progress will be saved automatically."
    else:
        # Set session to use the subscriber's user_identifier
        from flask import session
        session['devotional_user_id'] = subscriber['user_identifier']
        session.permanent = True
        flash_message = "Progress synced! You can continue where you left off."

    # Redirect to devotionals index
    return redirect(url_for('devotionals_index'))


# Admin devotional routes
@app.route('/admin/devotionals')
@require_admin_ip
def admin_devotionals():
    """Devotional admin dashboard."""
    threads = DevotionalThread.get_all()
    subscribers = DevotionalSubscriber.get_all_active()

    # Add devotional counts to threads
    for thread in threads:
        thread['devotional_count'] = DevotionalThread.count_devotionals(thread['id'])

    return render_template('devotionals/admin.html',
                         threads=threads,
                         subscribers=subscribers)


@app.route('/admin/devotionals/threads/create', methods=['GET', 'POST'])
@require_admin_ip
def create_devotional_thread():
    """Create a new devotional thread."""
    if request.method == 'GET':
        return render_template('devotionals/create_thread.html')

    # Handle POST
    try:
        title = request.form.get('title')
        if not title:
            return jsonify({'error': 'Title is required'}), 400

        identifier = request.form.get('identifier')
        if not identifier:
            identifier = generate_devotional_identifier(title)

        # Check for duplicate identifier
        existing = DevotionalThread.get_by_identifier(identifier)
        if existing:
            return jsonify({'error': f'Identifier "{identifier}" already exists'}), 400

        description = request.form.get('description')
        author = request.form.get('author')
        total_days = int(request.form.get('total_days', 1))
        is_published = request.form.get('is_published') == 'on'

        # Handle cover image upload
        cover_image = None
        if 'cover_image' in request.files and request.files['cover_image'].filename:
            # Create thread first to get ID
            thread_id = DevotionalThread.create(
                identifier=identifier,
                title=title,
                description=description,
                author=author,
                total_days=total_days,
                is_published=is_published
            )
            cover_image = process_cover_image(request.files['cover_image'], thread_id)
            if cover_image:
                DevotionalThread.update(thread_id, cover_image=cover_image)
        else:
            thread_id = DevotionalThread.create(
                identifier=identifier,
                title=title,
                description=description,
                author=author,
                total_days=total_days,
                is_published=is_published
            )

        thread = DevotionalThread.get_by_id(thread_id)

        return jsonify({
            'success': True,
            'thread': dict(thread),
            'url': url_for('admin_edit_thread', thread_id=thread_id)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/devotionals/threads/<int:thread_id>/edit', methods=['GET', 'POST'])
@require_admin_ip
def admin_edit_thread(thread_id):
    """Edit a devotional thread."""
    thread = DevotionalThread.get_by_id(thread_id)
    if not thread:
        abort(404, description="Thread not found")

    if request.method == 'GET':
        devotionals = DevotionalThread.get_devotionals(thread_id)
        return render_template('devotionals/create_thread.html',
                             thread=thread,
                             devotionals=devotionals,
                             editing=True)

    # Handle POST
    try:
        update_data = {}

        if request.form.get('title'):
            update_data['title'] = request.form.get('title')
        if request.form.get('identifier'):
            update_data['identifier'] = request.form.get('identifier')
        if 'description' in request.form:
            update_data['description'] = request.form.get('description')
        if 'author' in request.form:
            update_data['author'] = request.form.get('author')
        if request.form.get('total_days'):
            update_data['total_days'] = int(request.form.get('total_days'))

        update_data['is_published'] = request.form.get('is_published') == 'on'

        # Handle cover image upload
        if 'cover_image' in request.files and request.files['cover_image'].filename:
            cover_image = process_cover_image(request.files['cover_image'], thread_id)
            if cover_image:
                update_data['cover_image'] = cover_image

        DevotionalThread.update(thread_id, **update_data)
        updated_thread = DevotionalThread.get_by_id(thread_id)

        return jsonify({
            'success': True,
            'thread': dict(updated_thread)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/devotionals/threads/<int:thread_id>/days/create', methods=['GET', 'POST'])
@require_admin_ip
def create_devotional_day(thread_id):
    """Add a new day to a thread."""
    thread = DevotionalThread.get_by_id(thread_id)
    if not thread:
        abort(404, description="Thread not found")

    if request.method == 'GET':
        # Suggest next day number
        existing_count = DevotionalThread.count_devotionals(thread_id)
        suggested_day = existing_count + 1
        return render_template('devotionals/create_day.html',
                             thread=thread,
                             suggested_day=suggested_day)

    # Handle POST
    try:
        day_number = int(request.form.get('day_number', 1))
        title = request.form.get('title')
        if not title:
            return jsonify({'error': 'Title is required'}), 400

        content = request.form.get('content')
        if not content:
            return jsonify({'error': 'Content is required'}), 400

        devotional_id = Devotional.create(
            thread_id=thread_id,
            day_number=day_number,
            title=title,
            content=content,
            scripture_reference=request.form.get('scripture_reference'),
            scripture_text=request.form.get('scripture_text'),
            reflection_questions=request.form.get('reflection_questions'),
            prayer=request.form.get('prayer')
        )

        # Update thread total_days if needed
        if day_number > thread['total_days']:
            DevotionalThread.update(thread_id, total_days=day_number)

        # Queue audio generation in background
        from devotional_utils import queue_audio_generation
        queue_audio_generation(devotional_id)

        devotional = Devotional.get_by_id(devotional_id)

        return jsonify({
            'success': True,
            'devotional': dict(devotional),
            'url': url_for('admin_edit_thread', thread_id=thread_id)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/devotionals/days/<int:devotional_id>/edit', methods=['GET', 'POST'])
@require_admin_ip
def admin_edit_devotional(devotional_id):
    """Edit a devotional day."""
    devotional = Devotional.get_by_id(devotional_id)
    if not devotional:
        abort(404, description="Devotional not found")

    thread = DevotionalThread.get_by_id(devotional['thread_id'])

    if request.method == 'GET':
        return render_template('devotionals/create_day.html',
                             thread=thread,
                             devotional=devotional,
                             editing=True)

    # Handle POST
    try:
        update_data = {}

        if request.form.get('day_number'):
            update_data['day_number'] = int(request.form.get('day_number'))
        if request.form.get('title'):
            update_data['title'] = request.form.get('title')
        if 'content' in request.form:
            update_data['content'] = request.form.get('content')
        if 'scripture_reference' in request.form:
            update_data['scripture_reference'] = request.form.get('scripture_reference')
        if 'scripture_text' in request.form:
            update_data['scripture_text'] = request.form.get('scripture_text')
        if 'reflection_questions' in request.form:
            update_data['reflection_questions'] = request.form.get('reflection_questions')
        if 'prayer' in request.form:
            update_data['prayer'] = request.form.get('prayer')

        Devotional.update(devotional_id, **update_data)
        updated = Devotional.get_by_id(devotional_id)

        return jsonify({
            'success': True,
            'devotional': dict(updated)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/devotionals/days/<int:devotional_id>/generate-audio', methods=['POST'])
@require_admin_ip
def generate_devotional_audio_route(devotional_id):
    """Generate TTS audio for a devotional."""
    devotional = Devotional.get_by_id(devotional_id)
    if not devotional:
        return jsonify({'error': 'Devotional not found'}), 404

    try:
        filename, duration = generate_devotional_audio(devotional)
        if filename:
            Devotional.update(devotional_id, audio_filename=filename, audio_duration=duration)
            return jsonify({
                'success': True,
                'filename': filename,
                'duration': duration,
                'duration_formatted': format_audio_duration(duration) if duration else None
            })
        else:
            return jsonify({'error': 'Audio generation failed. Check Google Cloud credentials.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/devotionals/threads/<int:thread_id>', methods=['DELETE'])
@require_admin_ip
def delete_devotional_thread(thread_id):
    """Delete a devotional thread."""
    try:
        DevotionalThread.delete(thread_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/devotionals/days/<int:devotional_id>', methods=['DELETE'])
@require_admin_ip
def delete_devotional_day(devotional_id):
    """Delete a devotional day."""
    try:
        Devotional.delete(devotional_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/devotionals/import', methods=['POST'])
@require_admin_ip
def import_devotional_json():
    """Import a devotional thread from a JSON file."""
    from devotional_utils import import_devotional_from_json
    import json

    try:
        # Check for file upload
        if 'json_file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['json_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.endswith('.json'):
            return jsonify({'error': 'File must be a JSON file'}), 400

        # Parse JSON
        try:
            json_data = json.load(file)
        except json.JSONDecodeError as e:
            return jsonify({'error': f'Invalid JSON: {str(e)}'}), 400

        # Get options from form
        publish = request.form.get('publish') == 'on'
        skip_audio = request.form.get('skip_audio') == 'on'

        # Import the devotional (audio generated in parallel by default)
        result = import_devotional_from_json(
            json_data,
            publish=publish,
            skip_audio=skip_audio
        )

        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'thread_id': result['thread_id'],
                'identifier': result['identifier'],
                'title': result['title'],
                'days_created': result['days_created']
            })
        else:
            return jsonify({'error': result['message']}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Devotional API routes
@app.route('/api/devotionals/threads')
def api_devotional_threads():
    """Get all published threads as JSON."""
    threads = DevotionalThread.get_all(published_only=True)
    return jsonify([dict(t) for t in threads])


@app.route('/api/devotionals/progress/<identifier>')
def api_devotional_progress(identifier):
    """Get user's progress for a thread."""
    thread = DevotionalThread.get_by_identifier(identifier)
    if not thread:
        return jsonify({'error': 'Thread not found'}), 404

    user_id = get_user_identifier()
    progress = DevotionalProgress.get(thread['id'], user_id)

    if progress:
        return jsonify({
            'current_day': progress['current_day'],
            'completed_days': progress['completed_days'],
            'is_complete': DevotionalProgress.is_thread_complete(thread['id'], user_id),
            'total_days': thread['total_days']
        })
    else:
        return jsonify({
            'current_day': 0,
            'completed_days': [],
            'is_complete': False,
            'total_days': thread['total_days']
        })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
