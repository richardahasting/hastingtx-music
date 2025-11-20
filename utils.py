"""Utility functions for file handling and metadata extraction."""
import os
import re
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, COMM
from werkzeug.utils import secure_filename


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


def extract_mp3_metadata(filepath):
    """
    Extract metadata from an MP3 file.

    Args:
        filepath: Path to the MP3 file

    Returns:
        Dict with metadata (title, artist, album, duration, etc.)
    """
    metadata = {
        'title': None,
        'artist': None,
        'album': None,
        'duration': None,
        'file_size': None
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

            # Extract common tags
            if 'TIT2' in tags:  # Title
                metadata['title'] = str(tags['TIT2'])
            if 'TPE1' in tags:  # Artist
                metadata['artist'] = str(tags['TPE1'])
            if 'TALB' in tags:  # Album
                metadata['album'] = str(tags['TALB'])

        except Exception:
            # No ID3 tags or error reading them
            pass

    except Exception as e:
        print(f"Error extracting metadata from {filepath}: {e}")

    return metadata


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
