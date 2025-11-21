"""Utility functions for file handling and metadata extraction."""
import os
import re
from datetime import datetime
from mutagen.mp3 import MP3
from mutagen.id3 import (
    ID3, TIT2, TPE1, TALB, COMM, USLT, APIC, TCON,
    TCOM, TEXT, TDRC, WXXX, ID3NoHeaderError
)
from werkzeug.utils import secure_filename
from PIL import Image
import io


def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'mp3'


def generate_identifier(title):
    """
    Generate a URL-friendly identifier from a title.

    Args:
        title: Song title

    Returns:
        URL-safe identifier (e.g., "My Song" -> "my-song")
    """
    # Convert to lowercase and replace spaces/special chars with hyphens
    identifier = re.sub(r'[^\w\s-]', '', title.lower())
    identifier = re.sub(r'[-\s]+', '-', identifier)
    return identifier.strip('-')


def extract_mp3_metadata(filepath, save_cover_to=None):
    """
    Extract comprehensive metadata from an MP3 file including ID3 tags.

    Args:
        filepath: Path to the MP3 file
        save_cover_to: Optional directory to save extracted cover art

    Returns:
        Dict with metadata (title, artist, album, lyrics, cover_art, etc.)
    """
    metadata = {
        'title': None,
        'artist': None,
        'album': None,
        'genre': None,
        'description': None,
        'lyrics': None,
        'composer': None,
        'lyricist': None,
        'recording_date': None,
        'duration': None,
        'file_size': None,
        'cover_art': None
    }

    try:
        # Get file size
        metadata['file_size'] = os.path.getsize(filepath)

        # Load MP3 file
        audio = MP3(filepath)

        # Get duration in seconds
        metadata['duration'] = int(audio.info.length) if audio.info.length else None

        # Try to get ID3 tags
        try:
            tags = ID3(filepath)

            # Basic tags
            if 'TIT2' in tags:  # Title
                metadata['title'] = str(tags['TIT2'])
            if 'TPE1' in tags:  # Artist
                metadata['artist'] = str(tags['TPE1'])
            if 'TALB' in tags:  # Album
                metadata['album'] = str(tags['TALB'])
            if 'TCON' in tags:  # Genre
                metadata['genre'] = str(tags['TCON'])

            # Enhanced metadata
            if 'TCOM' in tags:  # Composer
                metadata['composer'] = str(tags['TCOM'])
            if 'TEXT' in tags:  # Lyricist
                metadata['lyricist'] = str(tags['TEXT'])
            if 'TDRC' in tags:  # Recording date
                date_str = str(tags['TDRC'])
                try:
                    # Parse various date formats
                    if len(date_str) == 4:  # Year only
                        metadata['recording_date'] = f"{date_str}-01-01"
                    elif len(date_str) >= 10:  # Full date
                        metadata['recording_date'] = date_str[:10]
                except Exception:
                    pass

            # Comments/Description
            if 'COMM' in tags:
                comm = tags['COMM']
                if isinstance(comm, list) and len(comm) > 0:
                    metadata['description'] = str(comm[0])
                else:
                    metadata['description'] = str(comm)

            # Lyrics
            if 'USLT' in tags:
                uslt = tags['USLT']
                if isinstance(uslt, list) and len(uslt) > 0:
                    metadata['lyrics'] = str(uslt[0])
                else:
                    metadata['lyrics'] = str(uslt)

            # Cover Art
            if 'APIC:' in tags and save_cover_to:
                apic = tags['APIC:']
                # Save cover art as image file
                cover_filename = f"{os.path.splitext(os.path.basename(filepath))[0]}_cover.jpg"
                cover_path = os.path.join(save_cover_to, cover_filename)

                try:
                    # Open image data and save
                    img = Image.open(io.BytesIO(apic.data))
                    # Resize if too large (max 500x500)
                    if img.width > 500 or img.height > 500:
                        img.thumbnail((500, 500), Image.Resampling.LANCZOS)
                    img.save(cover_path, 'JPEG', quality=90)
                    metadata['cover_art'] = cover_filename
                except Exception as e:
                    print(f"Error saving cover art: {e}")

        except ID3NoHeaderError:
            # No ID3 tags in file
            pass
        except Exception as e:
            print(f"Error reading ID3 tags: {e}")

    except Exception as e:
        print(f"Error extracting metadata from {filepath}: {e}")

    return metadata


def write_mp3_metadata(filepath, song_data, song_url=None):
    """
    Write comprehensive metadata to an MP3 file's ID3 tags.

    Args:
        filepath: Path to the MP3 file
        song_data: Dict with metadata to write
        song_url: Optional URL to the song page

    Returns:
        Boolean indicating success
    """
    try:
        # Load or create ID3 tags
        try:
            tags = ID3(filepath)
        except ID3NoHeaderError:
            tags = ID3()

        # Basic tags
        if song_data.get('title'):
            tags['TIT2'] = TIT2(encoding=3, text=song_data['title'])
        if song_data.get('artist'):
            tags['TPE1'] = TPE1(encoding=3, text=song_data['artist'])
        if song_data.get('album'):
            tags['TALB'] = TALB(encoding=3, text=song_data['album'])
        if song_data.get('genre'):
            tags['TCON'] = TCON(encoding=3, text=song_data['genre'])

        # Enhanced metadata
        if song_data.get('composer'):
            tags['TCOM'] = TCOM(encoding=3, text=song_data['composer'])
        if song_data.get('lyricist'):
            tags['TEXT'] = TEXT(encoding=3, text=song_data['lyricist'])
        if song_data.get('recording_date'):
            tags['TDRC'] = TDRC(encoding=3, text=str(song_data['recording_date']))

        # Comments/Description
        if song_data.get('description'):
            tags['COMM'] = COMM(encoding=3, lang='eng', desc='', text=song_data['description'])

        # Lyrics
        if song_data.get('lyrics'):
            tags['USLT'] = USLT(encoding=3, lang='eng', desc='', text=song_data['lyrics'])

        # Song URL
        if song_url:
            tags['WXXX'] = WXXX(encoding=3, desc='Song Page', url=song_url)

        # Cover Art (if cover_art_path provided)
        if song_data.get('cover_art_path') and os.path.exists(song_data['cover_art_path']):
            with open(song_data['cover_art_path'], 'rb') as img_file:
                tags['APIC:'] = APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,  # Cover (front)
                    desc='Cover',
                    data=img_file.read()
                )

        # Save tags to file
        tags.save(filepath, v2_version=3)
        return True

    except Exception as e:
        print(f"Error writing metadata to {filepath}: {e}")
        return False


def save_uploaded_file(file, upload_folder):
    """
    Save an uploaded file and return the filename.

    Args:
        file: FileStorage object from Flask
        upload_folder: Directory to save the file

    Returns:
        Tuple of (saved_filename, full_path)
    """
    if not file or not allowed_file(file.filename):
        return None, None

    filename = secure_filename(file.filename)

    # Ensure unique filename
    base_name = filename.rsplit('.', 1)[0]
    extension = filename.rsplit('.', 1)[1]
    counter = 1
    full_path = os.path.join(upload_folder, filename)

    while os.path.exists(full_path):
        filename = f"{base_name}_{counter}.{extension}"
        full_path = os.path.join(upload_folder, filename)
        counter += 1

    # Save the file
    file.save(full_path)
    return filename, full_path


def format_duration(seconds):
    """
    Format duration in seconds to MM:SS or HH:MM:SS.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string
    """
    if seconds is None:
        return "Unknown"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def format_file_size(bytes_size):
    """
    Format file size in bytes to human-readable format.

    Args:
        bytes_size: Size in bytes

    Returns:
        Formatted string (e.g., "3.5 MB")
    """
    if bytes_size is None:
        return "Unknown"

    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0

    return f"{bytes_size:.1f} TB"


def is_ip_allowed(ip_address, whitelist):
    """
    Check if an IP address is in the whitelist.

    Args:
        ip_address: IP address to check
        whitelist: List of allowed IPs or CIDR ranges

    Returns:
        Boolean
    """
    from ipaddress import ip_address as parse_ip, ip_network

    try:
        ip = parse_ip(ip_address)

        for allowed in whitelist:
            allowed = allowed.strip()
            try:
                # Try as network/CIDR
                if '/' in allowed:
                    if ip in ip_network(allowed, strict=False):
                        return True
                # Try as single IP
                else:
                    if ip == parse_ip(allowed):
                        return True
            except Exception:
                continue

    except Exception:
        pass

    return False
