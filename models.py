"""Data models and database operations for songs and playlists."""
from db import db


class Song:
    """Song model and database operations."""

    @staticmethod
    def create(identifier, title, artist=None, album=None, description=None,
               lyrics=None, genre=None, tags=None, filename=None,
               duration=None, file_size=None):
        """Create a new song record."""
        query = """
            INSERT INTO songs (identifier, title, artist, album, description,
                             lyrics, genre, tags, filename, duration, file_size)
            VALUES (%(identifier)s, %(title)s, %(artist)s, %(album)s, %(description)s,
                    %(lyrics)s, %(genre)s, %(tags)s, %(filename)s, %(duration)s, %(file_size)s)
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
            'file_size': file_size
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
