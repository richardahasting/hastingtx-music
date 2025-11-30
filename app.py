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
from models import Song, Playlist, Rating, Comment, Subscriber, EmailLog, Genre
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
    """Make admin IP status, playlists, and albums available to all templates."""
    client_ip = request.remote_addr
    is_admin = is_ip_allowed(client_ip, config.ADMIN_IP_WHITELIST)
    # Get all playlists for navigation (exclude 'all' as it's shown separately)
    all_playlists = Playlist.get_all()
    nav_playlists = [p for p in all_playlists if p['identifier'] != 'all']
    # Get distinct albums for navigation
    albums = Song.get_distinct_albums()
    nav_albums = [a['album'] for a in albums if a['album']]
    return dict(is_admin_ip=is_admin, nav_playlists=nav_playlists, nav_albums=nav_albums)


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

    # Track listen
    Song.increment_listen_count(song['id'])

    # Get rating stats
    rating_stats = Rating.get_song_stats(song['id'])
    user_rating = Rating.get_user_rating(song['id'], request.remote_addr)

    # Get comments
    comments = Comment.get_by_song(song['id'])
    comment_count = Comment.get_count(song['id'])

    return render_template('song.html',
                         song=song,
                         avg_rating=rating_stats['avg_rating'] if rating_stats else None,
                         rating_count=rating_stats['rating_count'] if rating_stats else 0,
                         user_rating=user_rating['rating'] if user_rating else None,
                         comments=comments,
                         comment_count=comment_count)


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

    return render_template('playlist.html', playlist=playlist, songs=songs)


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

    return render_template('playlist.html', playlist=album_playlist, songs=songs, is_album=True)


@app.route('/download/song/<identifier>')
def download_song(identifier):
    """Download a single MP3 file."""
    song = Song.get_by_identifier(identifier)
    if not song:
        abort(404, description=f"Song '{identifier}' not found")

    file_path = os.path.join(config.UPLOAD_FOLDER, song['filename'])
    if not os.path.exists(file_path):
        abort(404, description="File not found on server")

    # Track download
    Song.increment_download_count(song['id'])

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


@app.route('/admin/upload', methods=['GET', 'POST'])
@require_admin_ip
def upload():
    """Upload a new song."""
    if request.method == 'GET':
        playlists = Playlist.get_all()
        albums = Song.get_distinct_albums()
        album_names = [a['album'] for a in albums if a['album']]
        genres = Genre.get_all()
        return render_template('upload.html', playlists=playlists, albums=album_names, genres=genres)

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
        return render_template('edit_song.html', song=song, playlists=playlists, song_playlist_ids=song_playlist_ids, genres=genres)

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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
