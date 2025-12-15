"""
Devotional Utilities for HastingTX
TTS generation, email helpers, and other utilities
"""

import os
import re
import smtplib
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from html import unescape

# Background audio generation queue
_audio_queue = queue.Queue()
_audio_worker = None
_audio_worker_lock = threading.Lock()

# Parallel generation settings
AUDIO_PARALLEL_WORKERS = 7  # Number of parallel TTS requests


def strip_html(text):
    """Strip HTML tags and convert entities to plain text for TTS"""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', ' ', text)
    # Convert HTML entities
    clean = unescape(clean)
    # Normalize whitespace
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()

# Audio directory for TTS files
AUDIO_DIR = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'devotionals', 'audio')
COVERS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'devotionals', 'covers')


def ensure_directories():
    """Ensure upload directories exist"""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(COVERS_DIR, exist_ok=True)


def generate_devotional_audio(devotional, voice_name="en-US-Neural2-D"):
    """
    Generate audio for a devotional using Google Cloud TTS.

    Args:
        devotional: Dictionary with devotional data
        voice_name: Google TTS voice name (default: en-US-Neural2-D - natural male)

    Returns:
        tuple: (filename, duration_seconds) or (None, None) on failure
    """
    try:
        from google.cloud import texttospeech
    except ImportError:
        print("Error: google-cloud-texttospeech not installed")
        print("Run: pip install google-cloud-texttospeech")
        return None, None

    # Check for credentials
    if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        print("Warning: GOOGLE_APPLICATION_CREDENTIALS not set")
        print("TTS generation requires Google Cloud credentials")
        return None, None

    ensure_directories()

    try:
        client = texttospeech.TextToSpeechClient()

        # Build text content for audio (strip HTML from all fields)
        text_parts = []

        # Title
        text_parts.append(f"{strip_html(devotional['title'])}.")

        # Scripture
        if devotional.get('scripture_reference'):
            text_parts.append(f"\nScripture: {strip_html(devotional['scripture_reference'])}.")
            if devotional.get('scripture_text'):
                text_parts.append(strip_html(devotional['scripture_text']))

        # Main content
        text_parts.append(f"\n\n{strip_html(devotional['content'])}")

        # Reflection questions
        if devotional.get('reflection_questions'):
            text_parts.append(f"\n\nReflection Questions:\n{strip_html(devotional['reflection_questions'])}")

        # Prayer
        if devotional.get('prayer'):
            text_parts.append(f"\n\nPrayer:\n{strip_html(devotional['prayer'])}")

        full_text = '\n'.join(text_parts)

        # TTS request
        synthesis_input = texttospeech.SynthesisInput(text=full_text)

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.95,  # Slightly slower for meditation
            pitch=0.0
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        # Save audio file
        filename = f"devotional_{devotional['id']}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        with open(filepath, 'wb') as f:
            f.write(response.audio_content)

        # Get duration
        duration = get_audio_duration(filepath)

        return filename, duration

    except Exception as e:
        print(f"TTS generation error: {e}")
        return None, None


def generate_audio_parallel(devotional_ids, max_workers=None):
    """
    Generate audio for multiple devotionals in parallel.

    Args:
        devotional_ids: List of devotional IDs to generate audio for
        max_workers: Number of parallel workers (default: AUDIO_PARALLEL_WORKERS)

    Returns:
        dict: {devotional_id: (filename, duration) or (None, None) on failure}
    """
    from devotional_models import Devotional

    if max_workers is None:
        max_workers = AUDIO_PARALLEL_WORKERS

    results = {}

    def generate_one(dev_id):
        """Generate audio for a single devotional."""
        devotional = Devotional.get_by_id(dev_id)
        if not devotional:
            return dev_id, (None, None)

        filename, duration = generate_devotional_audio(devotional)
        if filename:
            Devotional.update(dev_id, audio_filename=filename, audio_duration=duration)
        return dev_id, (filename, duration)

    # Submit all jobs in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(generate_one, dev_id): dev_id for dev_id in devotional_ids}

        for future in as_completed(futures):
            dev_id, result = future.result()
            results[dev_id] = result
            if result[0]:
                print(f"[Parallel Audio] Generated {result[0]} ({result[1]}s)")
            else:
                print(f"[Parallel Audio] Failed for devotional {dev_id}")

    return results


def generate_thread_audio_parallel(thread_id, max_workers=None):
    """
    Generate audio for all devotionals in a thread in parallel.

    Args:
        thread_id: Thread ID
        max_workers: Number of parallel workers

    Returns:
        dict: Results for each devotional
    """
    from devotional_models import DevotionalThread

    devotionals = DevotionalThread.get_devotionals(thread_id)
    # Only generate for those missing audio
    ids_to_generate = [d['id'] for d in devotionals if not d.get('audio_filename')]

    if not ids_to_generate:
        print(f"[Parallel Audio] All devotionals in thread {thread_id} already have audio")
        return {}

    print(f"[Parallel Audio] Generating audio for {len(ids_to_generate)} devotionals in parallel...")
    return generate_audio_parallel(ids_to_generate, max_workers)


def _audio_worker_thread():
    """Background worker thread for audio generation."""
    while True:
        try:
            devotional_id = _audio_queue.get(timeout=60)
            if devotional_id is None:  # Shutdown signal
                break

            # Import here to avoid circular imports
            from devotional_models import Devotional

            devotional = Devotional.get_by_id(devotional_id)
            if devotional and not devotional.get('audio_filename'):
                print(f"[Audio Worker] Generating audio for devotional {devotional_id}: {devotional['title']}")
                filename, duration = generate_devotional_audio(devotional)
                if filename:
                    Devotional.update(devotional_id, audio_filename=filename, audio_duration=duration)
                    print(f"[Audio Worker] Completed: {filename} ({duration}s)")
                else:
                    print(f"[Audio Worker] Failed to generate audio for devotional {devotional_id}")

            _audio_queue.task_done()

        except queue.Empty:
            # No items in queue, continue waiting
            continue
        except Exception as e:
            print(f"[Audio Worker] Error: {e}")


def _ensure_audio_worker():
    """Ensure the audio worker thread is running."""
    global _audio_worker

    with _audio_worker_lock:
        if _audio_worker is None or not _audio_worker.is_alive():
            _audio_worker = threading.Thread(target=_audio_worker_thread, daemon=True)
            _audio_worker.start()
            print("[Audio Worker] Started background audio generation worker")


def queue_audio_generation(devotional_id):
    """
    Queue a devotional for background audio generation.

    Args:
        devotional_id: ID of the devotional to generate audio for
    """
    _ensure_audio_worker()
    _audio_queue.put(devotional_id)
    print(f"[Audio Queue] Queued devotional {devotional_id} for audio generation")


def queue_missing_audio():
    """Queue all devotionals that are missing audio."""
    from devotional_models import DevotionalThread

    count = 0
    threads = DevotionalThread.get_all()
    for t in threads:
        devotionals = DevotionalThread.get_devotionals(t['id'])
        for d in devotionals:
            if not d.get('audio_filename'):
                queue_audio_generation(d['id'])
                count += 1

    print(f"[Audio Queue] Queued {count} devotionals for audio generation")
    return count


def get_audio_duration(filepath):
    """
    Get duration of MP3 file in seconds.

    Args:
        filepath: Path to MP3 file

    Returns:
        int: Duration in seconds, or None on failure
    """
    try:
        from mutagen.mp3 import MP3
        audio = MP3(filepath)
        return int(audio.info.length)
    except Exception as e:
        print(f"Error getting audio duration: {e}")
        return None


def format_duration(seconds):
    """Format duration in seconds to MM:SS"""
    if not seconds:
        return "0:00"
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def send_devotional_email(to_email, to_name, subject, devotional, thread, day_number,
                          total_days, unsubscribe_token, base_url="https://hastingtx.org"):
    """
    Send a devotional email.

    Args:
        to_email: Recipient email
        to_name: Recipient name
        subject: Email subject
        devotional: Devotional data dict
        thread: Thread data dict
        day_number: Current day number
        total_days: Total days in thread
        unsubscribe_token: Unsubscribe token
        base_url: Base URL for links

    Returns:
        bool: True if sent successfully
    """
    try:
        # Build HTML email
        html_content = build_devotional_email_html(
            devotional, thread, day_number, total_days,
            unsubscribe_token, base_url, to_name
        )

        # Build plain text version
        text_content = build_devotional_email_text(
            devotional, thread, day_number, total_days,
            unsubscribe_token, base_url
        )

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = 'devotionals@hastingtx.org'
        msg['To'] = to_email

        # Attach both versions
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        # Send via local Postfix
        with smtplib.SMTP('localhost', 25) as server:
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Email send error: {e}")
        return False


def build_devotional_email_html(devotional, thread, day_number, total_days,
                                 unsubscribe_token, base_url, recipient_name=None):
    """Build HTML email content"""
    thread_url = f"{base_url}/devotionals/{thread['identifier']}"
    day_url = f"{thread_url}/day/{day_number}"
    unsubscribe_url = f"{base_url}/devotionals/unsubscribe/{unsubscribe_token}"

    greeting = f"Hello {recipient_name}," if recipient_name else "Hello,"

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Georgia, serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; border-bottom: 2px solid #8B4513; padding-bottom: 20px; margin-bottom: 20px; }}
        .header h1 {{ color: #8B4513; margin: 0; }}
        .day-indicator {{ color: #666; font-size: 14px; }}
        .scripture {{ background: #f5f5dc; padding: 15px; border-left: 4px solid #8B4513; margin: 20px 0; }}
        .scripture-ref {{ font-weight: bold; color: #8B4513; }}
        .content {{ margin: 20px 0; }}
        .reflection {{ background: #f0f8ff; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .reflection h3 {{ color: #2c5aa0; margin-top: 0; }}
        .prayer {{ font-style: italic; background: #fff8dc; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .cta {{ text-align: center; margin: 30px 0; }}
        .cta a {{ background: #8B4513; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }}
        .footer {{ text-align: center; font-size: 12px; color: #666; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Pull The Thread</h1>
        <p class="day-indicator">Day {day_number} of {total_days}: {thread['title']}</p>
    </div>

    <p>{greeting}</p>

    <h2>{devotional['title']}</h2>
"""

    if devotional.get('scripture_reference'):
        html += f"""
    <div class="scripture">
        <p class="scripture-ref">{devotional['scripture_reference']}</p>
        <p>{devotional.get('scripture_text', '')}</p>
    </div>
"""

    html += f"""
    <div class="content">
        {devotional['content'].replace(chr(10), '<br>')}
    </div>
"""

    if devotional.get('reflection_questions'):
        html += f"""
    <div class="reflection">
        <h3>Reflection Questions</h3>
        {devotional['reflection_questions'].replace(chr(10), '<br>')}
    </div>
"""

    if devotional.get('prayer'):
        html += f"""
    <div class="prayer">
        <strong>Prayer:</strong><br>
        {devotional['prayer'].replace(chr(10), '<br>')}
    </div>
"""

    if devotional.get('audio_filename'):
        html += f"""
    <div class="cta">
        <a href="{day_url}">Listen to Audio Version</a>
    </div>
"""

    html += f"""
    <div class="cta">
        <a href="{day_url}">Read Online</a>
    </div>

    <div class="footer">
        <p>You're receiving this because you subscribed to "{thread['title']}" on hastingtx.org</p>
        <p><a href="{unsubscribe_url}">Unsubscribe</a> from devotional emails</p>
    </div>
</body>
</html>
"""
    return html


def build_devotional_email_text(devotional, thread, day_number, total_days,
                                 unsubscribe_token, base_url):
    """Build plain text email content"""
    thread_url = f"{base_url}/devotionals/{thread['identifier']}"
    day_url = f"{thread_url}/day/{day_number}"
    unsubscribe_url = f"{base_url}/devotionals/unsubscribe/{unsubscribe_token}"

    text = f"""PULL THE THREAD
Day {day_number} of {total_days}: {thread['title']}

{devotional['title']}
{'=' * len(devotional['title'])}

"""

    if devotional.get('scripture_reference'):
        text += f"""Scripture: {devotional['scripture_reference']}
{devotional.get('scripture_text', '')}

"""

    text += f"""{devotional['content']}

"""

    if devotional.get('reflection_questions'):
        text += f"""REFLECTION QUESTIONS
{devotional['reflection_questions']}

"""

    if devotional.get('prayer'):
        text += f"""PRAYER
{devotional['prayer']}

"""

    text += f"""---
Read online: {day_url}
Unsubscribe: {unsubscribe_url}
"""

    return text


def generate_identifier(title):
    """Generate URL-safe identifier from title"""
    import re
    # Convert to lowercase
    identifier = title.lower()
    # Replace spaces with hyphens
    identifier = identifier.replace(' ', '-')
    # Remove non-alphanumeric characters except hyphens
    identifier = re.sub(r'[^a-z0-9-]', '', identifier)
    # Remove multiple consecutive hyphens
    identifier = re.sub(r'-+', '-', identifier)
    # Remove leading/trailing hyphens
    identifier = identifier.strip('-')
    return identifier


def process_cover_image(file_storage, thread_id):
    """
    Process and save a cover image.

    Args:
        file_storage: Flask FileStorage object
        thread_id: Thread ID for filename

    Returns:
        str: Filename or None on failure
    """
    try:
        from PIL import Image

        ensure_directories()

        # Get file extension
        original_filename = file_storage.filename
        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return None

        # Save and resize
        filename = f"cover_{thread_id}{ext}"
        filepath = os.path.join(COVERS_DIR, filename)

        img = Image.open(file_storage)

        # Resize to max 800x600 maintaining aspect ratio
        img.thumbnail((800, 600), Image.Resampling.LANCZOS)

        # Convert RGBA to RGB if needed
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        img.save(filepath, quality=85, optimize=True)

        return filename

    except Exception as e:
        print(f"Cover image processing error: {e}")
        return None


def send_sync_email(to_email, sync_token, base_url="https://hastingtx.org"):
    """
    Send a progress sync email with magic link.

    Args:
        to_email: Recipient email
        sync_token: The unsubscribe_token (used as sync token)
        base_url: Base URL for links

    Returns:
        bool: True if sent successfully
    """
    try:
        sync_url = f"{base_url}/devotionals/sync/{sync_token}"

        subject = "Your Devotional Progress Link - Pull The Thread"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Georgia, serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; border-bottom: 2px solid #8B4513; padding-bottom: 20px; margin-bottom: 20px; }}
        .header h1 {{ color: #8B4513; margin: 0; }}
        .content {{ margin: 20px 0; }}
        .cta {{ text-align: center; margin: 30px 0; }}
        .cta a {{ background: #8B4513; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px; }}
        .note {{ background: #f5f5dc; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .footer {{ text-align: center; font-size: 12px; color: #666; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Pull The Thread</h1>
        <p>Your Progress Sync Link</p>
    </div>

    <div class="content">
        <p>Hello,</p>
        <p>Here's your personal link to access your devotional progress from any device:</p>
    </div>

    <div class="cta">
        <a href="{sync_url}">Access My Progress</a>
    </div>

    <div class="note">
        <strong>Save this email!</strong> You can use this link anytime to:
        <ul>
            <li>Continue your devotionals on a new device</li>
            <li>Restore your progress if you clear your browser</li>
            <li>Switch between your phone and computer</li>
        </ul>
    </div>

    <div class="content">
        <p>This link is unique to you. Anyone with this link can access your progress, so keep it private.</p>
    </div>

    <div class="footer">
        <p>You'll also receive notifications when new devotional series are available.</p>
        <p><a href="{base_url}/devotionals/unsubscribe/{sync_token}">Unsubscribe</a> from emails</p>
    </div>
</body>
</html>
"""

        text_content = f"""PULL THE THREAD
Your Progress Sync Link

Hello,

Here's your personal link to access your devotional progress from any device:

{sync_url}

SAVE THIS EMAIL! You can use this link anytime to:
- Continue your devotionals on a new device
- Restore your progress if you clear your browser
- Switch between your phone and computer

This link is unique to you. Anyone with this link can access your progress, so keep it private.

---
Unsubscribe: {base_url}/devotionals/unsubscribe/{sync_token}
"""

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = 'devotionals@hastingtx.org'
        msg['To'] = to_email

        # Attach both versions
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        # Send via local Postfix
        with smtplib.SMTP('localhost', 25) as server:
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Sync email send error: {e}")
        return False


def text_to_html(text):
    """Convert plain text with newlines to HTML paragraphs."""
    if not text:
        return ""
    # Split by double newlines (paragraphs)
    paragraphs = text.strip().split('\n\n')
    html_parts = []
    for p in paragraphs:
        # Clean up single newlines within paragraphs
        p = p.replace('\n', ' ').strip()
        if p:
            html_parts.append(f'<p>{p}</p>')
    return '\n\n'.join(html_parts)


def import_devotional_from_json(json_data, author_override=None, publish=False, skip_audio=False):
    """
    Import a devotional thread from JSON data.

    Audio is generated in parallel by default (~5-10 seconds for any size thread).

    Args:
        json_data: Dictionary with thread and days data
        author_override: Override author from JSON (optional)
        publish: Whether to publish immediately
        skip_audio: Set True to skip audio generation (default: False = generate audio)

    Returns:
        dict: {'success': bool, 'thread_id': int, 'message': str, 'days_created': int}

    JSON format:
        {
            "thread_id": "identifier",
            "thread_title": "Title",
            "thread_description": "Description",
            "author": "Author Name",
            "series": "Series Name",          # Optional - for grouping
            "series_position": 0,             # Optional - order within series
            "days": [...]
        }
    """
    from devotional_models import DevotionalThread, Devotional

    # Extract thread info
    thread_id_str = json_data.get('thread_id')
    thread_title = json_data.get('thread_title')
    thread_description = json_data.get('thread_description', '')
    days = json_data.get('days', [])

    # Series info (optional)
    series = json_data.get('series')
    series_position = json_data.get('series_position')

    if not thread_id_str or not thread_title:
        return {'success': False, 'message': "JSON must contain 'thread_id' and 'thread_title'"}

    if not days:
        return {'success': False, 'message': "JSON must contain 'days' array"}

    # Check if thread already exists
    existing = DevotionalThread.get_by_identifier(thread_id_str)
    if existing:
        return {'success': False, 'message': f"Thread '{thread_id_str}' already exists"}

    # Determine author (JSON field > override > default)
    author = json_data.get('author') or author_override or "Rick Hasting & Claude"

    # Create the thread
    db_thread_id = DevotionalThread.create(
        identifier=thread_id_str,
        title=thread_title,
        description=thread_description,
        author=author,
        total_days=len(days),
        is_published=publish,
        series=series,
        series_position=series_position
    )

    if not db_thread_id:
        return {'success': False, 'message': 'Failed to create thread in database'}

    # Create each day
    days_created = 0
    created_ids = []
    for day_data in days:
        day_num = day_data.get('day')
        title = day_data.get('title', f'Day {day_num}')
        scripture_ref = day_data.get('scripture_reference', '')
        scripture_text = day_data.get('scripture_text', '')
        devotional_text = day_data.get('devotional', '')
        reflection = day_data.get('reflection', '')
        prayer = day_data.get('prayer', '')

        # Convert devotional text to HTML
        content_html = text_to_html(devotional_text)

        devotional_id = Devotional.create(
            thread_id=db_thread_id,
            day_number=day_num,
            title=title,
            scripture_reference=scripture_ref,
            scripture_text=scripture_text,
            content=content_html,
            reflection_questions=reflection,
            prayer=prayer
        )

        if devotional_id:
            days_created += 1
            created_ids.append(devotional_id)

    # Generate audio for all created devotionals in parallel (unless skipped)
    if created_ids and not skip_audio:
        print(f"[Import] Generating audio for {len(created_ids)} devotionals in parallel...")
        generate_audio_parallel(created_ids)

    return {
        'success': True,
        'thread_id': db_thread_id,
        'identifier': thread_id_str,
        'title': thread_title,
        'days_created': days_created,
        'message': f"Created '{thread_title}' with {days_created} days"
    }
