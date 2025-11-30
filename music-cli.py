#!/usr/bin/env python3
"""
HastingTX Music CLI - Command line interface for managing music database.

Usage:
    ./music-cli.py <command> <subcommand> [options]

Commands:
    songs       - Manage songs (list, show, update, search, etc.)
    playlists   - Manage playlists (list, show, create, add/remove songs)
    genres      - Manage genres (list, create, assign)
    albums      - Manage albums (list, show, rename, merge)
    stats       - View statistics and reports
    export      - Export data to various formats
    maintenance - Database maintenance tasks
"""

import argparse
import sys
import os
import json
import csv
from datetime import datetime
from tabulate import tabulate

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import db
from models import Song, Playlist, Genre, Rating, Comment, Subscriber


def format_duration(seconds):
    """Format duration in seconds to MM:SS."""
    if not seconds:
        return '-'
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"


def truncate(text, length=50):
    """Truncate text to specified length."""
    if not text:
        return '-'
    if len(text) <= length:
        return text
    return text[:length-3] + '...'


# ============================================================================
# SONG COMMANDS
# ============================================================================

def cmd_songs_list(args):
    """List all songs."""
    query = "SELECT * FROM songs ORDER BY "

    if args.order == 'title':
        query += "title"
    elif args.order == 'date':
        query += "upload_date DESC"
    elif args.order == 'album':
        query += "album, title"
    elif args.order == 'listens':
        query += "listen_count DESC"
    elif args.order == 'rating':
        query += "id"  # Will need subquery for rating
    else:
        query += "id"

    if args.limit:
        query += f" LIMIT {args.limit}"

    songs = db.execute(query)

    if args.format == 'json':
        print(json.dumps([dict(s) for s in songs], default=str, indent=2))
        return

    # Table format
    headers = ['ID', 'Title', 'Artist', 'Album', 'Genre', 'Duration', 'Listens', 'DLs']
    rows = []
    for s in songs:
        rows.append([
            s['id'],
            truncate(s['title'], 40),
            truncate(s['artist'], 20) if s['artist'] else '-',
            truncate(s['album'], 20) if s['album'] else '-',
            truncate(s['genre'], 15) if s['genre'] else '-',
            format_duration(s['duration']),
            s['listen_count'] or 0,
            s['download_count'] or 0
        ])

    print(tabulate(rows, headers=headers, tablefmt='simple'))
    print(f"\nTotal: {len(songs)} songs")


def cmd_songs_show(args):
    """Show detailed info for a song."""
    song = Song.get_by_id(args.id) if args.id else Song.get_by_identifier(args.identifier)

    if not song:
        print(f"Error: Song not found", file=sys.stderr)
        sys.exit(1)

    if args.format == 'json':
        print(json.dumps(dict(song), default=str, indent=2))
        return

    # Get rating stats
    rating_stats = Rating.get_song_stats(song['id'])

    print(f"\n{'='*60}")
    print(f"Song #{song['id']}: {song['title']}")
    print(f"{'='*60}")
    print(f"  Identifier:    {song['identifier']}")
    print(f"  Artist:        {song['artist'] or '-'}")
    print(f"  Album:         {song['album'] or '-'}")
    print(f"  Genre:         {song['genre'] or '-'}")
    print(f"  Duration:      {format_duration(song['duration'])}")
    print(f"  File:          {song['filename']}")
    print(f"  File Size:     {song['file_size'] or 0:,} bytes")
    print(f"  Composer:      {song['composer'] or '-'}")
    print(f"  Lyricist:      {song['lyricist'] or '-'}")
    print(f"  Recording:     {song['recording_date'] or '-'}")
    print(f"  Uploaded:      {song['upload_date']}")
    print(f"  Listens:       {song['listen_count'] or 0}")
    print(f"  Downloads:     {song['download_count'] or 0}")
    print(f"  Avg Rating:    {rating_stats['avg_rating'] or '-'} ({rating_stats['rating_count'] or 0} votes)")
    print(f"  Cover Art:     {song['cover_art'] or '-'}")
    print(f"  Tags:          {song['tags'] or '-'}")
    print(f"\n  Description:")
    print(f"    {song['description'] or '(none)'}")

    if args.lyrics and song['lyrics']:
        print(f"\n  Lyrics:")
        print(f"    {song['lyrics'][:500]}{'...' if len(song['lyrics'] or '') > 500 else ''}")


def cmd_songs_search(args):
    """Search for songs."""
    songs = Song.search(args.query)

    if not songs:
        print("No songs found.")
        return

    headers = ['ID', 'Title', 'Artist', 'Album']
    rows = [[s['id'], truncate(s['title'], 40), truncate(s['artist'], 25), truncate(s['album'], 25)] for s in songs]
    print(tabulate(rows, headers=headers, tablefmt='simple'))
    print(f"\nFound: {len(songs)} songs")


def cmd_songs_update(args):
    """Update song metadata."""
    song = Song.get_by_id(args.id)
    if not song:
        print(f"Error: Song #{args.id} not found", file=sys.stderr)
        sys.exit(1)

    updates = {}
    if args.title:
        updates['title'] = args.title
    if args.artist:
        updates['artist'] = args.artist
    if args.album:
        updates['album'] = args.album
    if args.genre:
        updates['genre'] = args.genre
    if args.description:
        updates['description'] = args.description
    if args.tags:
        updates['tags'] = args.tags
    if args.composer:
        updates['composer'] = args.composer
    if args.lyricist:
        updates['lyricist'] = args.lyricist

    if not updates:
        print("No updates specified. Use --title, --artist, --album, --genre, --description, etc.")
        sys.exit(1)

    updated = Song.update(args.id, **updates)
    print(f"Updated song #{args.id}: {updated['title']}")
    for key, value in updates.items():
        print(f"  {key}: {truncate(str(value), 60)}")


def cmd_songs_missing(args):
    """Find songs missing specific fields."""
    field_map = {
        'description': "description IS NULL OR description = ''",
        'genre': "genre IS NULL OR genre = ''",
        'album': "album IS NULL OR album = ''",
        'lyrics': "lyrics IS NULL OR lyrics = ''",
        'cover': "cover_art IS NULL OR cover_art = ''",
        'tags': "tags IS NULL OR tags = ''",
    }

    if args.field not in field_map:
        print(f"Error: Unknown field '{args.field}'. Options: {', '.join(field_map.keys())}")
        sys.exit(1)

    query = f"SELECT * FROM songs WHERE {field_map[args.field]} ORDER BY title"
    songs = db.execute(query)

    if not songs:
        print(f"All songs have {args.field}!")
        return

    headers = ['ID', 'Title', 'Album', 'Has Lyrics']
    rows = []
    for s in songs:
        has_lyrics = 'Yes' if s['lyrics'] else 'No'
        rows.append([s['id'], truncate(s['title'], 45), truncate(s['album'], 25), has_lyrics])

    print(tabulate(rows, headers=headers, tablefmt='simple'))
    print(f"\nFound: {len(songs)} songs missing {args.field}")


def cmd_songs_set_genre(args):
    """Set genre for one or more songs."""
    # Verify genre exists
    genre = Genre.get_by_name(args.genre)
    if not genre and not args.create:
        print(f"Error: Genre '{args.genre}' not found. Use --create to create it.")
        sys.exit(1)

    if not genre and args.create:
        genre = Genre.create(args.genre)
        print(f"Created genre: {args.genre}")

    for song_id in args.song_ids:
        song = Song.get_by_id(song_id)
        if not song:
            print(f"Warning: Song #{song_id} not found, skipping")
            continue
        Song.update(song_id, genre=args.genre)
        print(f"Set genre '{args.genre}' for song #{song_id}: {song['title']}")


def cmd_songs_set_album(args):
    """Set album for one or more songs."""
    for song_id in args.song_ids:
        song = Song.get_by_id(song_id)
        if not song:
            print(f"Warning: Song #{song_id} not found, skipping")
            continue
        Song.update(song_id, album=args.album)
        print(f"Set album '{args.album}' for song #{song_id}: {song['title']}")


def cmd_songs_lyrics(args):
    """Show or update lyrics for a song."""
    song = Song.get_by_id(args.id)
    if not song:
        print(f"Error: Song #{args.id} not found", file=sys.stderr)
        sys.exit(1)

    if args.set:
        # Read lyrics from file or stdin
        if args.set == '-':
            lyrics = sys.stdin.read()
        else:
            with open(args.set, 'r') as f:
                lyrics = f.read()
        Song.update(args.id, lyrics=lyrics)
        print(f"Updated lyrics for song #{args.id}")
    else:
        if song['lyrics']:
            print(song['lyrics'])
        else:
            print("(No lyrics)")


# ============================================================================
# PLAYLIST COMMANDS
# ============================================================================

def cmd_playlists_list(args):
    """List all playlists."""
    playlists = Playlist.get_all()

    if args.format == 'json':
        print(json.dumps([dict(p) for p in playlists], default=str, indent=2))
        return

    headers = ['ID', 'Identifier', 'Name', 'Songs', 'Sort Order']
    rows = []
    for p in playlists:
        song_count = len(Playlist.get_songs(p['id']))
        rows.append([p['id'], p['identifier'], p['name'], song_count, p['sort_order']])

    print(tabulate(rows, headers=headers, tablefmt='simple'))


def cmd_playlists_show(args):
    """Show playlist details and songs."""
    playlist = Playlist.get_by_id(args.id) if args.id else Playlist.get_by_identifier(args.identifier)

    if not playlist:
        print(f"Error: Playlist not found", file=sys.stderr)
        sys.exit(1)

    songs = Playlist.get_songs(playlist['id'])

    print(f"\n{'='*60}")
    print(f"Playlist: {playlist['name']}")
    print(f"{'='*60}")
    print(f"  ID:          {playlist['id']}")
    print(f"  Identifier:  {playlist['identifier']}")
    print(f"  Description: {playlist['description'] or '-'}")
    print(f"  Sort Order:  {playlist['sort_order']}")
    print(f"  Songs:       {len(songs)}")
    print(f"\n  Song List:")

    for i, s in enumerate(songs, 1):
        print(f"    {i:2}. [{s['id']:3}] {truncate(s['title'], 45)}")


def cmd_playlists_create(args):
    """Create a new playlist."""
    from utils import generate_identifier

    identifier = args.identifier or generate_identifier(args.name)

    playlist = Playlist.create(
        identifier=identifier,
        name=args.name,
        description=args.description,
        sort_order=args.sort or 'manual'
    )

    print(f"Created playlist #{playlist['id']}: {playlist['name']}")
    print(f"  Identifier: {playlist['identifier']}")


def cmd_playlists_add(args):
    """Add songs to a playlist."""
    playlist = Playlist.get_by_id(args.playlist_id)
    if not playlist:
        print(f"Error: Playlist #{args.playlist_id} not found", file=sys.stderr)
        sys.exit(1)

    for song_id in args.song_ids:
        song = Song.get_by_id(song_id)
        if not song:
            print(f"Warning: Song #{song_id} not found, skipping")
            continue
        Playlist.add_song(args.playlist_id, song_id)
        print(f"Added song #{song_id} '{song['title']}' to playlist '{playlist['name']}'")


def cmd_playlists_remove(args):
    """Remove songs from a playlist."""
    playlist = Playlist.get_by_id(args.playlist_id)
    if not playlist:
        print(f"Error: Playlist #{args.playlist_id} not found", file=sys.stderr)
        sys.exit(1)

    for song_id in args.song_ids:
        Playlist.remove_song(args.playlist_id, song_id)
        print(f"Removed song #{song_id} from playlist '{playlist['name']}'")


# ============================================================================
# GENRE COMMANDS
# ============================================================================

def cmd_genres_list(args):
    """List all genres."""
    genres = Genre.get_all()

    if args.format == 'json':
        print(json.dumps([dict(g) for g in genres], default=str, indent=2))
        return

    # Count songs per genre
    genre_counts = {}
    for g in genres:
        query = "SELECT COUNT(*) as count FROM songs WHERE genre = %s"
        result = db.execute_one(query, (g['name'],))
        genre_counts[g['id']] = result['count'] if result else 0

    headers = ['ID', 'Name', 'Parent', 'Songs', 'Description']
    rows = []
    for g in genres:
        parent_name = '-'
        if g['parent_genre_id']:
            parent = Genre.get_by_id(g['parent_genre_id'])
            parent_name = parent['name'] if parent else '-'
        rows.append([
            g['id'],
            g['name'],
            parent_name,
            genre_counts.get(g['id'], 0),
            truncate(g['description'], 40) if g['description'] else '-'
        ])

    print(tabulate(rows, headers=headers, tablefmt='simple'))
    print(f"\nTotal: {len(genres)} genres")


def cmd_genres_create(args):
    """Create a new genre."""
    # Check for duplicate
    existing = Genre.get_by_name(args.name)
    if existing:
        print(f"Error: Genre '{args.name}' already exists", file=sys.stderr)
        sys.exit(1)

    parent_id = None
    if args.parent:
        parent = Genre.get_by_name(args.parent)
        if not parent:
            print(f"Error: Parent genre '{args.parent}' not found", file=sys.stderr)
            sys.exit(1)
        parent_id = parent['id']

    genre = Genre.create(args.name, args.description, parent_id)
    print(f"Created genre #{genre['id']}: {genre['name']}")
    if parent_id:
        print(f"  Parent: {args.parent}")


def cmd_genres_songs(args):
    """List songs in a genre."""
    genre = Genre.get_by_name(args.name)
    if not genre:
        print(f"Error: Genre '{args.name}' not found", file=sys.stderr)
        sys.exit(1)

    query = "SELECT * FROM songs WHERE genre = %s ORDER BY title"
    songs = db.execute(query, (args.name,))

    if not songs:
        print(f"No songs in genre '{args.name}'")
        return

    headers = ['ID', 'Title', 'Artist', 'Album']
    rows = [[s['id'], truncate(s['title'], 40), truncate(s['artist'], 25), truncate(s['album'], 25)] for s in songs]
    print(tabulate(rows, headers=headers, tablefmt='simple'))
    print(f"\nFound: {len(songs)} songs in '{args.name}'")


# ============================================================================
# ALBUM COMMANDS
# ============================================================================

def cmd_albums_list(args):
    """List all albums."""
    albums = Song.get_distinct_albums()

    if args.format == 'json':
        print(json.dumps([a['album'] for a in albums], indent=2))
        return

    headers = ['Album', 'Songs']
    rows = []
    for a in albums:
        if a['album']:
            songs = Song.get_by_album(a['album'])
            rows.append([a['album'], len(songs)])

    print(tabulate(rows, headers=headers, tablefmt='simple'))
    print(f"\nTotal: {len(rows)} albums")


def cmd_albums_show(args):
    """Show album details and songs."""
    songs = Song.get_by_album(args.name)

    if not songs:
        print(f"Error: Album '{args.name}' not found or empty", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Album: {args.name}")
    print(f"{'='*60}")
    print(f"  Songs: {len(songs)}")

    total_duration = sum(s['duration'] or 0 for s in songs)
    print(f"  Total Duration: {format_duration(total_duration)}")

    print(f"\n  Track List:")
    for i, s in enumerate(songs, 1):
        print(f"    {i:2}. [{s['id']:3}] {truncate(s['title'], 40)} ({format_duration(s['duration'])})")


def cmd_albums_rename(args):
    """Rename an album (updates all songs)."""
    songs = Song.get_by_album(args.old_name)

    if not songs:
        print(f"Error: Album '{args.old_name}' not found", file=sys.stderr)
        sys.exit(1)

    for song in songs:
        Song.update(song['id'], album=args.new_name)

    print(f"Renamed album '{args.old_name}' to '{args.new_name}'")
    print(f"Updated {len(songs)} songs")


def cmd_albums_merge(args):
    """Merge multiple albums into one."""
    all_songs = []
    for album_name in args.source_albums:
        songs = Song.get_by_album(album_name)
        all_songs.extend(songs)

    if not all_songs:
        print("Error: No songs found in source albums", file=sys.stderr)
        sys.exit(1)

    for song in all_songs:
        Song.update(song['id'], album=args.target)

    print(f"Merged {len(args.source_albums)} albums into '{args.target}'")
    print(f"Updated {len(all_songs)} songs")


# ============================================================================
# STATS COMMANDS
# ============================================================================

def cmd_stats_overview(args):
    """Show overall statistics."""
    # Song stats
    song_count = db.execute_one("SELECT COUNT(*) as count FROM songs")['count']
    total_duration = db.execute_one("SELECT SUM(duration) as total FROM songs")['total'] or 0
    total_listens = db.execute_one("SELECT SUM(listen_count) as total FROM songs")['total'] or 0
    total_downloads = db.execute_one("SELECT SUM(download_count) as total FROM songs")['total'] or 0

    # Other counts
    playlist_count = db.execute_one("SELECT COUNT(*) as count FROM playlists")['count']
    genre_count = db.execute_one("SELECT COUNT(*) as count FROM genres")['count']
    rating_count = db.execute_one("SELECT COUNT(*) as count FROM ratings")['count']
    comment_count = db.execute_one("SELECT COUNT(*) as count FROM comments")['count']
    subscriber_count = db.execute_one("SELECT COUNT(*) as count FROM subscribers WHERE is_active = TRUE")['count']

    # Albums
    albums = Song.get_distinct_albums()
    album_count = len([a for a in albums if a['album']])

    print(f"\n{'='*40}")
    print(f"HastingTX Music - Statistics")
    print(f"{'='*40}")
    print(f"  Songs:        {song_count}")
    print(f"  Total Time:   {format_duration(total_duration)} ({total_duration // 3600}h {(total_duration % 3600) // 60}m)")
    print(f"  Playlists:    {playlist_count}")
    print(f"  Albums:       {album_count}")
    print(f"  Genres:       {genre_count}")
    print(f"  Total Listens:    {total_listens:,}")
    print(f"  Total Downloads:  {total_downloads:,}")
    print(f"  Ratings:      {rating_count}")
    print(f"  Comments:     {comment_count}")
    print(f"  Subscribers:  {subscriber_count}")


def cmd_stats_top(args):
    """Show top songs by various metrics."""
    if args.metric == 'listens':
        query = "SELECT * FROM songs ORDER BY listen_count DESC NULLS LAST LIMIT %s"
    elif args.metric == 'downloads':
        query = "SELECT * FROM songs ORDER BY download_count DESC NULLS LAST LIMIT %s"
    elif args.metric == 'rating':
        query = """
            SELECT s.*, ROUND(AVG(r.rating)::numeric, 2) as avg_rating, COUNT(r.id) as vote_count
            FROM songs s
            LEFT JOIN ratings r ON s.id = r.song_id
            GROUP BY s.id
            HAVING COUNT(r.id) >= 1
            ORDER BY avg_rating DESC NULLS LAST
            LIMIT %s
        """
    else:
        print(f"Error: Unknown metric '{args.metric}'. Options: listens, downloads, rating")
        sys.exit(1)

    songs = db.execute(query, (args.limit,))

    print(f"\nTop {args.limit} Songs by {args.metric.title()}")
    print(f"{'='*50}")

    for i, s in enumerate(songs, 1):
        if args.metric == 'listens':
            value = s['listen_count'] or 0
        elif args.metric == 'downloads':
            value = s['download_count'] or 0
        else:
            value = f"{s['avg_rating']} ({s['vote_count']} votes)"
        print(f"  {i:2}. [{s['id']:3}] {truncate(s['title'], 35):38} {value}")


def cmd_stats_missing(args):
    """Show summary of missing data."""
    fields = {
        'description': "description IS NULL OR description = ''",
        'genre': "genre IS NULL OR genre = ''",
        'album': "album IS NULL OR album = ''",
        'lyrics': "lyrics IS NULL OR lyrics = ''",
        'cover_art': "cover_art IS NULL OR cover_art = ''",
        'tags': "tags IS NULL OR tags = ''",
        'composer': "composer IS NULL OR composer = ''",
        'lyricist': "lyricist IS NULL OR lyricist = ''",
    }

    total = db.execute_one("SELECT COUNT(*) as count FROM songs")['count']

    print(f"\nMissing Data Summary")
    print(f"{'='*40}")
    print(f"Total songs: {total}")
    print()

    for field, condition in fields.items():
        result = db.execute_one(f"SELECT COUNT(*) as count FROM songs WHERE {condition}")
        count = result['count']
        pct = (count / total * 100) if total > 0 else 0
        bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
        print(f"  {field:12} {count:3}/{total:3} missing  {bar} {pct:5.1f}%")


def cmd_stats_activity(args):
    """Show recent activity."""
    print(f"\nRecent Activity")
    print(f"{'='*50}")

    # Recent uploads
    print("\nRecent Uploads:")
    recent = db.execute("SELECT * FROM songs ORDER BY upload_date DESC LIMIT 5")
    for s in recent:
        print(f"  [{s['id']:3}] {truncate(s['title'], 40)} - {s['upload_date'].strftime('%Y-%m-%d')}")

    # Recent ratings
    print("\nRecent Ratings:")
    ratings = db.execute("""
        SELECT r.*, s.title FROM ratings r
        JOIN songs s ON r.song_id = s.id
        ORDER BY r.created_at DESC LIMIT 5
    """)
    for r in ratings:
        print(f"  {r['rating']}/10 for '{truncate(r['title'], 35)}' - {r['created_at'].strftime('%Y-%m-%d')}")

    # Recent comments
    print("\nRecent Comments:")
    comments = db.execute("""
        SELECT c.*, s.title FROM comments c
        JOIN songs s ON c.song_id = s.id
        ORDER BY c.created_at DESC LIMIT 5
    """)
    for c in comments:
        name = c['commenter_name'] or 'Anonymous'
        print(f"  {name} on '{truncate(c['title'], 30)}': {truncate(c['comment_text'], 30)}")


# ============================================================================
# EXPORT COMMANDS
# ============================================================================

def cmd_export_csv(args):
    """Export songs to CSV."""
    songs = db.execute("SELECT * FROM songs ORDER BY id")

    output = args.output or sys.stdout
    if isinstance(output, str):
        output = open(output, 'w', newline='')

    writer = csv.writer(output)

    # Headers
    headers = ['id', 'identifier', 'title', 'artist', 'album', 'genre', 'description',
               'duration', 'listen_count', 'download_count', 'tags', 'upload_date']
    writer.writerow(headers)

    for s in songs:
        writer.writerow([
            s['id'], s['identifier'], s['title'], s['artist'], s['album'], s['genre'],
            s['description'], s['duration'], s['listen_count'], s['download_count'],
            s['tags'], s['upload_date']
        ])

    if args.output:
        output.close()
        print(f"Exported {len(songs)} songs to {args.output}")


def cmd_export_json(args):
    """Export songs to JSON."""
    songs = db.execute("SELECT * FROM songs ORDER BY id")

    data = [dict(s) for s in songs]

    output = json.dumps(data, default=str, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Exported {len(songs)} songs to {args.output}")
    else:
        print(output)


def cmd_export_m3u(args):
    """Export playlist to M3U format."""
    playlist = Playlist.get_by_identifier(args.playlist)
    if not playlist:
        print(f"Error: Playlist '{args.playlist}' not found", file=sys.stderr)
        sys.exit(1)

    if args.playlist == 'all':
        songs = Song.get_all(order_by='title')
    else:
        songs = Playlist.get_songs(playlist['id'])

    lines = ['#EXTM3U', f'#PLAYLIST:{playlist["name"]}']

    for s in songs:
        duration = s['duration'] or 0
        lines.append(f'#EXTINF:{duration},{s["artist"] or "Unknown"} - {s["title"]}')
        lines.append(s['filename'])

    output = '\n'.join(lines)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Exported playlist '{playlist['name']}' to {args.output}")
    else:
        print(output)


# ============================================================================
# MAINTENANCE COMMANDS
# ============================================================================

def cmd_maintenance_duplicates(args):
    """Find potential duplicate songs."""
    # By title similarity
    songs = db.execute("SELECT * FROM songs ORDER BY title")

    print(f"\nPotential Duplicates (by title)")
    print(f"{'='*50}")

    from difflib import SequenceMatcher

    found = []
    for i, s1 in enumerate(songs):
        for s2 in songs[i+1:]:
            ratio = SequenceMatcher(None, s1['title'].lower(), s2['title'].lower()).ratio()
            if ratio > 0.8:
                found.append((s1, s2, ratio))

    if not found:
        print("No potential duplicates found.")
        return

    for s1, s2, ratio in found:
        print(f"\n  Similarity: {ratio:.0%}")
        print(f"    [{s1['id']:3}] {s1['title']}")
        print(f"    [{s2['id']:3}] {s2['title']}")


def cmd_maintenance_orphans(args):
    """Find orphaned files or database entries."""
    import os
    from config import config

    # Get all filenames from database
    db_files = set()
    songs = db.execute("SELECT filename FROM songs")
    for s in songs:
        db_files.add(s['filename'])

    # Get all files in upload directory
    upload_dir = config.UPLOAD_FOLDER
    disk_files = set()
    if os.path.exists(upload_dir):
        for f in os.listdir(upload_dir):
            if f.endswith('.mp3'):
                disk_files.add(f)

    # Find orphans
    db_only = db_files - disk_files
    disk_only = disk_files - db_files

    print(f"\nOrphan Check")
    print(f"{'='*50}")

    if db_only:
        print(f"\nFiles in database but not on disk ({len(db_only)}):")
        for f in db_only:
            print(f"  - {f}")

    if disk_only:
        print(f"\nFiles on disk but not in database ({len(disk_only)}):")
        for f in disk_only:
            print(f"  - {f}")

    if not db_only and not disk_only:
        print("No orphans found. All files are synced.")


def cmd_maintenance_fix_case(args):
    """Fix inconsistent casing in album/genre names."""
    print("Checking for case inconsistencies...")

    # Albums
    albums = db.execute("SELECT DISTINCT album FROM songs WHERE album IS NOT NULL AND album != ''")
    album_groups = {}
    for a in albums:
        key = a['album'].lower()
        if key not in album_groups:
            album_groups[key] = []
        album_groups[key].append(a['album'])

    album_issues = {k: v for k, v in album_groups.items() if len(v) > 1}

    if album_issues:
        print(f"\nAlbum case inconsistencies:")
        for key, variants in album_issues.items():
            print(f"  {variants}")
    else:
        print("No album case issues found.")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='HastingTX Music CLI - Manage music database',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Command category')

    # ---- SONGS ----
    songs_parser = subparsers.add_parser('songs', help='Manage songs')
    songs_sub = songs_parser.add_subparsers(dest='subcommand')

    # songs list
    p = songs_sub.add_parser('list', help='List all songs')
    p.add_argument('--order', choices=['id', 'title', 'date', 'album', 'listens'], default='id')
    p.add_argument('--limit', type=int, help='Limit results')
    p.add_argument('--format', choices=['table', 'json'], default='table')
    p.set_defaults(func=cmd_songs_list)

    # songs show
    p = songs_sub.add_parser('show', help='Show song details')
    p.add_argument('id', type=int, nargs='?', help='Song ID')
    p.add_argument('--identifier', '-i', help='Song identifier')
    p.add_argument('--lyrics', '-l', action='store_true', help='Include lyrics')
    p.add_argument('--format', choices=['table', 'json'], default='table')
    p.set_defaults(func=cmd_songs_show)

    # songs search
    p = songs_sub.add_parser('search', help='Search songs')
    p.add_argument('query', help='Search query')
    p.set_defaults(func=cmd_songs_search)

    # songs update
    p = songs_sub.add_parser('update', help='Update song metadata')
    p.add_argument('id', type=int, help='Song ID')
    p.add_argument('--title', help='New title')
    p.add_argument('--artist', help='New artist')
    p.add_argument('--album', help='New album')
    p.add_argument('--genre', help='New genre')
    p.add_argument('--description', help='New description')
    p.add_argument('--tags', help='New tags')
    p.add_argument('--composer', help='New composer')
    p.add_argument('--lyricist', help='New lyricist')
    p.set_defaults(func=cmd_songs_update)

    # songs missing
    p = songs_sub.add_parser('missing', help='Find songs missing a field')
    p.add_argument('field', choices=['description', 'genre', 'album', 'lyrics', 'cover', 'tags'])
    p.set_defaults(func=cmd_songs_missing)

    # songs set-genre
    p = songs_sub.add_parser('set-genre', help='Set genre for songs')
    p.add_argument('genre', help='Genre name')
    p.add_argument('song_ids', type=int, nargs='+', help='Song IDs')
    p.add_argument('--create', action='store_true', help='Create genre if missing')
    p.set_defaults(func=cmd_songs_set_genre)

    # songs set-album
    p = songs_sub.add_parser('set-album', help='Set album for songs')
    p.add_argument('album', help='Album name')
    p.add_argument('song_ids', type=int, nargs='+', help='Song IDs')
    p.set_defaults(func=cmd_songs_set_album)

    # songs lyrics
    p = songs_sub.add_parser('lyrics', help='Show or set lyrics')
    p.add_argument('id', type=int, help='Song ID')
    p.add_argument('--set', metavar='FILE', help='Set lyrics from file (or - for stdin)')
    p.set_defaults(func=cmd_songs_lyrics)

    # ---- PLAYLISTS ----
    playlists_parser = subparsers.add_parser('playlists', help='Manage playlists')
    playlists_sub = playlists_parser.add_subparsers(dest='subcommand')

    # playlists list
    p = playlists_sub.add_parser('list', help='List all playlists')
    p.add_argument('--format', choices=['table', 'json'], default='table')
    p.set_defaults(func=cmd_playlists_list)

    # playlists show
    p = playlists_sub.add_parser('show', help='Show playlist details')
    p.add_argument('id', type=int, nargs='?', help='Playlist ID')
    p.add_argument('--identifier', '-i', help='Playlist identifier')
    p.set_defaults(func=cmd_playlists_show)

    # playlists create
    p = playlists_sub.add_parser('create', help='Create playlist')
    p.add_argument('name', help='Playlist name')
    p.add_argument('--identifier', help='URL identifier')
    p.add_argument('--description', help='Description')
    p.add_argument('--sort', choices=['manual', 'title', 'album'])
    p.set_defaults(func=cmd_playlists_create)

    # playlists add
    p = playlists_sub.add_parser('add', help='Add songs to playlist')
    p.add_argument('playlist_id', type=int, help='Playlist ID')
    p.add_argument('song_ids', type=int, nargs='+', help='Song IDs to add')
    p.set_defaults(func=cmd_playlists_add)

    # playlists remove
    p = playlists_sub.add_parser('remove', help='Remove songs from playlist')
    p.add_argument('playlist_id', type=int, help='Playlist ID')
    p.add_argument('song_ids', type=int, nargs='+', help='Song IDs to remove')
    p.set_defaults(func=cmd_playlists_remove)

    # ---- GENRES ----
    genres_parser = subparsers.add_parser('genres', help='Manage genres')
    genres_sub = genres_parser.add_subparsers(dest='subcommand')

    # genres list
    p = genres_sub.add_parser('list', help='List all genres')
    p.add_argument('--format', choices=['table', 'json'], default='table')
    p.set_defaults(func=cmd_genres_list)

    # genres create
    p = genres_sub.add_parser('create', help='Create genre')
    p.add_argument('name', help='Genre name')
    p.add_argument('--description', help='Description')
    p.add_argument('--parent', help='Parent genre name (for sub-genres)')
    p.set_defaults(func=cmd_genres_create)

    # genres songs
    p = genres_sub.add_parser('songs', help='List songs in genre')
    p.add_argument('name', help='Genre name')
    p.set_defaults(func=cmd_genres_songs)

    # ---- ALBUMS ----
    albums_parser = subparsers.add_parser('albums', help='Manage albums')
    albums_sub = albums_parser.add_subparsers(dest='subcommand')

    # albums list
    p = albums_sub.add_parser('list', help='List all albums')
    p.add_argument('--format', choices=['table', 'json'], default='table')
    p.set_defaults(func=cmd_albums_list)

    # albums show
    p = albums_sub.add_parser('show', help='Show album details')
    p.add_argument('name', help='Album name')
    p.set_defaults(func=cmd_albums_show)

    # albums rename
    p = albums_sub.add_parser('rename', help='Rename album')
    p.add_argument('old_name', help='Current album name')
    p.add_argument('new_name', help='New album name')
    p.set_defaults(func=cmd_albums_rename)

    # albums merge
    p = albums_sub.add_parser('merge', help='Merge albums')
    p.add_argument('target', help='Target album name')
    p.add_argument('source_albums', nargs='+', help='Source album names to merge')
    p.set_defaults(func=cmd_albums_merge)

    # ---- STATS ----
    stats_parser = subparsers.add_parser('stats', help='View statistics')
    stats_sub = stats_parser.add_subparsers(dest='subcommand')

    # stats overview
    p = stats_sub.add_parser('overview', help='Overview statistics')
    p.set_defaults(func=cmd_stats_overview)

    # stats top
    p = stats_sub.add_parser('top', help='Top songs')
    p.add_argument('metric', choices=['listens', 'downloads', 'rating'])
    p.add_argument('--limit', type=int, default=10)
    p.set_defaults(func=cmd_stats_top)

    # stats missing
    p = stats_sub.add_parser('missing', help='Missing data summary')
    p.set_defaults(func=cmd_stats_missing)

    # stats activity
    p = stats_sub.add_parser('activity', help='Recent activity')
    p.set_defaults(func=cmd_stats_activity)

    # ---- EXPORT ----
    export_parser = subparsers.add_parser('export', help='Export data')
    export_sub = export_parser.add_subparsers(dest='subcommand')

    # export csv
    p = export_sub.add_parser('csv', help='Export to CSV')
    p.add_argument('--output', '-o', help='Output file')
    p.set_defaults(func=cmd_export_csv)

    # export json
    p = export_sub.add_parser('json', help='Export to JSON')
    p.add_argument('--output', '-o', help='Output file')
    p.set_defaults(func=cmd_export_json)

    # export m3u
    p = export_sub.add_parser('m3u', help='Export playlist to M3U')
    p.add_argument('playlist', help='Playlist identifier')
    p.add_argument('--output', '-o', help='Output file')
    p.set_defaults(func=cmd_export_m3u)

    # ---- MAINTENANCE ----
    maint_parser = subparsers.add_parser('maintenance', help='Maintenance tasks')
    maint_sub = maint_parser.add_subparsers(dest='subcommand')

    # maintenance duplicates
    p = maint_sub.add_parser('duplicates', help='Find duplicate songs')
    p.set_defaults(func=cmd_maintenance_duplicates)

    # maintenance orphans
    p = maint_sub.add_parser('orphans', help='Find orphaned files')
    p.set_defaults(func=cmd_maintenance_orphans)

    # maintenance fix-case
    p = maint_sub.add_parser('fix-case', help='Check case inconsistencies')
    p.set_defaults(func=cmd_maintenance_fix_case)

    # Parse and execute
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if not hasattr(args, 'func'):
        # Print subcommand help
        if args.command == 'songs':
            songs_parser.print_help()
        elif args.command == 'playlists':
            playlists_parser.print_help()
        elif args.command == 'genres':
            genres_parser.print_help()
        elif args.command == 'albums':
            albums_parser.print_help()
        elif args.command == 'stats':
            stats_parser.print_help()
        elif args.command == 'export':
            export_parser.print_help()
        elif args.command == 'maintenance':
            maint_parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()
