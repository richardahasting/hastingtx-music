"""Data models and database operations for songs and playlists."""
import secrets
from db import db


class Song:
    """Song model and database operations."""

    @staticmethod
    def create(identifier, title, artist=None, album=None, description=None,
               lyrics=None, genre=None, tags=None, filename=None,
               duration=None, file_size=None, cover_art=None, composer=None,
               lyricist=None, recording_date=None):
        """Create a new song record with comprehensive metadata."""
        query = """
            INSERT INTO songs (identifier, title, artist, album, description,
                             lyrics, genre, tags, filename, duration, file_size,
                             cover_art, composer, lyricist, recording_date)
            VALUES (%(identifier)s, %(title)s, %(artist)s, %(album)s, %(description)s,
                    %(lyrics)s, %(genre)s, %(tags)s, %(filename)s, %(duration)s, %(file_size)s,
                    %(cover_art)s, %(composer)s, %(lyricist)s, %(recording_date)s)
            RETURNING *
        """
        params = {
            'identifier': identifier,
            'title': title,
            'artist': artist,
            'album': album,
            'description': description,
            'lyrics': lyrics,
            'genre': genre,
            'tags': tags,
            'filename': filename,
            'duration': duration,
            'file_size': file_size,
            'cover_art': cover_art,
            'composer': composer,
            'lyricist': lyricist,
            'recording_date': recording_date
        }
        return db.insert(query, params)

    @staticmethod
    def get_by_identifier(identifier):
        """Get a song by its identifier."""
        query = "SELECT * FROM songs WHERE identifier = %s"
        return db.execute_one(query, (identifier,))

    @staticmethod
    def get_by_id(song_id):
        """Get a song by its ID."""
        query = "SELECT * FROM songs WHERE id = %s"
        return db.execute_one(query, (song_id,))

    @staticmethod
    def get_all(order_by='upload_date DESC', limit=None, offset=0):
        """Get all songs with optional ordering and pagination."""
        query = f"SELECT * FROM songs ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        return db.execute(query)

    @staticmethod
    def update(song_id, **kwargs):
        """Update song fields."""
        if not kwargs:
            return None

        set_clause = ', '.join([f"{key} = %({key})s" for key in kwargs.keys()])
        query = f"UPDATE songs SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = %(id)s RETURNING *"
        kwargs['id'] = song_id
        return db.insert(query, kwargs)

    @staticmethod
    def delete(song_id):
        """Delete a song."""
        query = "DELETE FROM songs WHERE id = %s"
        db.execute(query, (song_id,), fetch=False)

    @staticmethod
    def search(search_term):
        """Search songs by title, artist, album, or tags."""
        query = """
            SELECT * FROM songs
            WHERE title ILIKE %(term)s
               OR artist ILIKE %(term)s
               OR album ILIKE %(term)s
               OR tags ILIKE %(term)s
               OR description ILIKE %(term)s
            ORDER BY upload_date DESC
        """
        return db.execute(query, {'term': f'%{search_term}%'})

    @staticmethod
    def get_by_album(album_name):
        """Get all songs in an album (case-insensitive match)."""
        query = "SELECT * FROM songs WHERE LOWER(album) = LOWER(%s) ORDER BY title"
        return db.execute(query, (album_name,))

    @staticmethod
    def get_distinct_albums():
        """Get list of distinct album names (case-insensitive)."""
        query = """
            SELECT album FROM (
                SELECT album, LOWER(album) as album_lower,
                       ROW_NUMBER() OVER (PARTITION BY LOWER(album) ORDER BY album) as rn
                FROM songs
                WHERE album IS NOT NULL AND album != ''
            ) sub
            WHERE rn = 1
            ORDER BY album
        """
        return db.execute(query)

    @staticmethod
    def increment_listen_count(song_id):
        """Increment the listen count for a song."""
        query = "UPDATE songs SET listen_count = listen_count + 1 WHERE id = %s"
        db.execute(query, (song_id,), fetch=False)

    @staticmethod
    def increment_download_count(song_id):
        """Increment the download count for a song."""
        query = "UPDATE songs SET download_count = download_count + 1 WHERE id = %s"
        db.execute(query, (song_id,), fetch=False)

    @staticmethod
    def get_with_rating_stats(song_id):
        """
        Get a song with its rating statistics.

        Returns:
            Dict with song data plus avg_rating and rating_count
        """
        query = """
            SELECT s.*,
                   ROUND(AVG(r.rating)::numeric, 1) as avg_rating,
                   COUNT(r.id)::integer as rating_count
            FROM songs s
            LEFT JOIN ratings r ON s.id = r.song_id
            WHERE s.id = %s
            GROUP BY s.id
        """
        return db.execute_one(query, (song_id,))


class Playlist:
    """Playlist model and database operations."""

    @staticmethod
    def create(identifier, name, description=None, sort_order='manual'):
        """Create a new playlist."""
        query = """
            INSERT INTO playlists (identifier, name, description, sort_order)
            VALUES (%(identifier)s, %(name)s, %(description)s, %(sort_order)s)
            RETURNING *
        """
        params = {
            'identifier': identifier,
            'name': name,
            'description': description,
            'sort_order': sort_order
        }
        return db.insert(query, params)

    @staticmethod
    def get_by_identifier(identifier):
        """Get a playlist by its identifier."""
        query = "SELECT * FROM playlists WHERE identifier = %s"
        return db.execute_one(query, (identifier,))

    @staticmethod
    def get_by_id(playlist_id):
        """Get a playlist by its ID."""
        query = "SELECT * FROM playlists WHERE id = %s"
        return db.execute_one(query, (playlist_id,))

    @staticmethod
    def get_all():
        """Get all playlists."""
        query = "SELECT * FROM playlists ORDER BY name"
        return db.execute(query)

    @staticmethod
    def get_or_create_album_playlist(album_name):
        """
        Get or create a playlist for an album.

        Args:
            album_name: Name of the album

        Returns:
            Playlist record
        """
        # Generate identifier from album name
        import re
        identifier = 'album-' + re.sub(r'[^a-z0-9]+', '-', album_name.lower()).strip('-')

        # Check if playlist already exists
        existing = Playlist.get_by_identifier(identifier)
        if existing:
            return existing

        # Create new album playlist
        return Playlist.create(
            identifier=identifier,
            name=album_name,
            description=f'All songs from the album "{album_name}"',
            sort_order='title'
        )

    @staticmethod
    def update(playlist_id, **kwargs):
        """Update playlist fields."""
        if not kwargs:
            return None

        set_clause = ', '.join([f"{key} = %({key})s" for key in kwargs.keys()])
        query = f"UPDATE playlists SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = %(id)s RETURNING *"
        kwargs['id'] = playlist_id
        return db.insert(query, kwargs)

    @staticmethod
    def delete(playlist_id):
        """Delete a playlist."""
        query = "DELETE FROM playlists WHERE id = %s"
        db.execute(query, (playlist_id,), fetch=False)

    @staticmethod
    def get_songs(playlist_id, apply_sort=True):
        """
        Get all songs in a playlist.

        Args:
            playlist_id: ID of the playlist
            apply_sort: Whether to apply playlist's sort_order setting

        Returns:
            List of song dicts with position information
        """
        # Get playlist to check sort order
        playlist = Playlist.get_by_id(playlist_id)
        if not playlist:
            return []

        # Base query
        query = """
            SELECT s.*, ps.position
            FROM songs s
            JOIN playlist_songs ps ON s.id = ps.song_id
            WHERE ps.playlist_id = %s
        """

        # Apply sorting based on playlist settings
        if apply_sort:
            if playlist['sort_order'] == 'title':
                query += " ORDER BY s.title"
            elif playlist['sort_order'] == 'album':
                query += " ORDER BY s.album, s.title"
            else:  # manual
                query += " ORDER BY ps.position"
        else:
            query += " ORDER BY ps.position"

        return db.execute(query, (playlist_id,))

    @staticmethod
    def add_song(playlist_id, song_id, position=None):
        """Add a song to a playlist."""
        if position is None:
            # Get the next position
            query = "SELECT COALESCE(MAX(position), 0) + 1 as next_pos FROM playlist_songs WHERE playlist_id = %s"
            result = db.execute_one(query, (playlist_id,))
            position = result['next_pos'] if result else 1

        query = """
            INSERT INTO playlist_songs (playlist_id, song_id, position)
            VALUES (%s, %s, %s)
            ON CONFLICT (playlist_id, song_id) DO UPDATE SET position = EXCLUDED.position
            RETURNING *
        """
        return db.insert(query, (playlist_id, song_id, position))

    @staticmethod
    def remove_song(playlist_id, song_id):
        """Remove a song from a playlist."""
        query = "DELETE FROM playlist_songs WHERE playlist_id = %s AND song_id = %s"
        db.execute(query, (playlist_id, song_id), fetch=False)

    @staticmethod
    def reorder_songs(playlist_id, song_positions):
        """
        Reorder songs in a playlist.

        Args:
            playlist_id: ID of the playlist
            song_positions: List of tuples [(song_id, position), ...]
        """
        query = """
            UPDATE playlist_songs
            SET position = %s
            WHERE playlist_id = %s AND song_id = %s
        """
        conn = db.connect()
        with conn.cursor() as cur:
            for song_id, position in song_positions:
                cur.execute(query, (position, playlist_id, song_id))
            conn.commit()

    @staticmethod
    def get_playlists_for_song(song_id):
        """Get all playlists that contain a specific song."""
        query = """
            SELECT p.* FROM playlists p
            JOIN playlist_songs ps ON p.id = ps.playlist_id
            WHERE ps.song_id = %s
            ORDER BY p.name
        """
        return db.execute(query, (song_id,))

    @staticmethod
    def set_song_playlists(song_id, playlist_ids):
        """
        Set which playlists a song belongs to.
        Removes from playlists not in the list, adds to new ones.

        Args:
            song_id: ID of the song
            playlist_ids: List of playlist IDs the song should belong to
        """
        # Get current playlists
        current = Playlist.get_playlists_for_song(song_id)
        current_ids = {p['id'] for p in current}
        new_ids = set(playlist_ids)

        # Remove from playlists no longer selected
        for playlist_id in current_ids - new_ids:
            Playlist.remove_song(playlist_id, song_id)

        # Add to new playlists
        for playlist_id in new_ids - current_ids:
            Playlist.add_song(playlist_id, song_id)


class Rating:
    """Rating model and database operations."""

    @staticmethod
    def submit_rating(song_id, ip_address, rating):
        """
        Submit or update a rating for a song.

        Args:
            song_id: ID of the song
            ip_address: IP address of the voter
            rating: Rating value (1-10)

        Returns:
            Rating record
        """
        query = """
            INSERT INTO ratings (song_id, ip_address, rating)
            VALUES (%s, %s, %s)
            ON CONFLICT (song_id, ip_address)
            DO UPDATE SET rating = EXCLUDED.rating, updated_at = CURRENT_TIMESTAMP
            RETURNING *
        """
        return db.insert(query, (song_id, ip_address, rating))

    @staticmethod
    def get_user_rating(song_id, ip_address):
        """Get a user's rating for a song."""
        query = "SELECT * FROM ratings WHERE song_id = %s AND ip_address = %s"
        return db.execute_one(query, (song_id, ip_address))

    @staticmethod
    def get_song_stats(song_id):
        """
        Get rating statistics for a song.

        Returns:
            Dict with avg_rating and rating_count
        """
        query = """
            SELECT ROUND(AVG(rating)::numeric, 1) as avg_rating,
                   COUNT(*)::integer as rating_count
            FROM ratings
            WHERE song_id = %s
        """
        return db.execute_one(query, (song_id,))


class Comment:
    """Comment model and database operations."""

    @staticmethod
    def create(song_id, comment_text, ip_address, commenter_name=None):
        """
        Create a new comment on a song.

        Args:
            song_id: ID of the song
            comment_text: The comment text
            ip_address: IP address of the commenter
            commenter_name: Optional display name for the commenter

        Returns:
            Comment record
        """
        query = """
            INSERT INTO comments (song_id, comment_text, ip_address, commenter_name)
            VALUES (%s, %s, %s, %s)
            RETURNING *
        """
        return db.insert(query, (song_id, comment_text, ip_address, commenter_name))

    @staticmethod
    def get_by_song(song_id):
        """
        Get all comments for a song, ordered by creation date (newest first).

        Args:
            song_id: ID of the song

        Returns:
            List of comment records
        """
        query = """
            SELECT * FROM comments
            WHERE song_id = %s
            ORDER BY created_at DESC
        """
        return db.execute(query, (song_id,))

    @staticmethod
    def get_by_id(comment_id):
        """Get a comment by its ID."""
        query = "SELECT * FROM comments WHERE id = %s"
        return db.execute_one(query, (comment_id,))

    @staticmethod
    def delete(comment_id):
        """Delete a comment."""
        query = "DELETE FROM comments WHERE id = %s"
        db.execute(query, (comment_id,), fetch=False)

    @staticmethod
    def get_count(song_id):
        """Get the number of comments on a song."""
        query = "SELECT COUNT(*)::integer as count FROM comments WHERE song_id = %s"
        result = db.execute_one(query, (song_id,))
        return result['count'] if result else 0


class Subscriber:
    """Email subscriber model and database operations."""

    @staticmethod
    def create(email):
        """
        Create a new email subscriber.

        Args:
            email: Email address to subscribe

        Returns:
            Subscriber record
        """
        # Generate unique unsubscribe token
        unsubscribe_token = secrets.token_urlsafe(32)

        query = """
            INSERT INTO subscribers (email, unsubscribe_token)
            VALUES (%s, %s)
            ON CONFLICT (email)
            DO UPDATE SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP
            RETURNING *
        """
        return db.insert(query, (email, unsubscribe_token))

    @staticmethod
    def get_by_email(email):
        """Get a subscriber by email address."""
        query = "SELECT * FROM subscribers WHERE email = %s"
        return db.execute_one(query, (email,))

    @staticmethod
    def get_by_token(token):
        """Get a subscriber by unsubscribe token."""
        query = "SELECT * FROM subscribers WHERE unsubscribe_token = %s"
        return db.execute_one(query, (token,))

    @staticmethod
    def get_active_subscribers():
        """Get all active subscribers."""
        query = "SELECT * FROM subscribers WHERE is_active = TRUE ORDER BY subscribed_at"
        return db.execute(query)

    @staticmethod
    def unsubscribe(token):
        """Unsubscribe using token."""
        query = """
            UPDATE subscribers
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE unsubscribe_token = %s
            RETURNING *
        """
        return db.insert(query, (token,))

    @staticmethod
    def get_count():
        """Get count of active subscribers."""
        query = "SELECT COUNT(*)::integer as count FROM subscribers WHERE is_active = TRUE"
        result = db.execute_one(query)
        return result['count'] if result else 0


class EmailLog:
    """Email log model and database operations."""

    @staticmethod
    def create(subject, recipient_count, song_ids, success=True, error_message=None):
        """
        Log a sent email.

        Args:
            subject: Email subject
            recipient_count: Number of recipients
            song_ids: List of song IDs included in email
            success: Whether email sent successfully
            error_message: Error message if failed

        Returns:
            Log record
        """
        query = """
            INSERT INTO email_logs (subject, recipient_count, song_ids, success, error_message)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
        """
        return db.insert(query, (subject, recipient_count, song_ids, success, error_message))

    @staticmethod
    def get_last_sent():
        """Get the most recent email log."""
        query = "SELECT * FROM email_logs ORDER BY sent_at DESC LIMIT 1"
        return db.execute_one(query)

    @staticmethod
    def get_recent_logs(limit=10):
        """Get recent email logs."""
        query = "SELECT * FROM email_logs ORDER BY sent_at DESC LIMIT %s"
        return db.execute(query, (limit,))
