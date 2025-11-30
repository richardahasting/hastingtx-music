#!/usr/bin/env python3
"""Send weekly email to subscribers about new songs."""
import os
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from models import Song, Subscriber, EmailLog
from utils import format_duration

# Email configuration
SMTP_HOST = 'localhost'
SMTP_PORT = 25
FROM_EMAIL = 'noreply@hastingtx.org'
FROM_NAME = 'HastingTX Music'
SITE_URL = 'https://hastingtx.org'


def get_new_songs_since_last_email():
    """Get songs added since the last email was sent."""
    # Get last email log
    last_log = EmailLog.get_last_sent()

    if last_log and last_log['sent_at']:
        # Get songs added after last email
        cutoff_date = last_log['sent_at']
    else:
        # If no previous email, get songs from last 7 days
        cutoff_date = datetime.now() - timedelta(days=7)

    # Get all songs ordered by upload date
    all_songs = Song.get_all(order_by='upload_date DESC')

    # Filter songs added after cutoff
    new_songs = [
        song for song in all_songs
        if song['upload_date'] and song['upload_date'] > cutoff_date
    ]

    return new_songs


def generate_email_html(songs, unsubscribe_token):
    """Generate HTML email content."""
    unsubscribe_url = f"{SITE_URL}/unsubscribe/{unsubscribe_token}"

    if not songs:
        return None  # Don't send email if no new songs

    # Start HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
            .song {{ border: 1px solid #ecf0f1; padding: 15px; margin: 15px 0; border-radius: 5px; }}
            .song-title {{ font-size: 1.2em; font-weight: bold; color: #2c3e50; margin-bottom: 5px; }}
            .song-meta {{ color: #7f8c8d; font-size: 0.9em; margin: 5px 0; }}
            .song-description {{ margin: 10px 0; }}
            .btn {{ display: inline-block; background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-top: 10px; }}
            .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ecf0f1; color: #7f8c8d; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>New Songs at HastingTX Music!</h1>
                <p>{len(songs)} new song{"s" if len(songs) != 1 else ""} added this week</p>
            </div>

            <p>Hello! We've added some new music created by Richard & Claude. Check out what's new:</p>
    """

    # Add each song
    for song in songs:
        song_url = f"{SITE_URL}/music/{song['identifier']}"
        artist = song['artist'] or 'Richard & Claude'
        album_text = f" • Album: {song['album']}" if song['album'] else ""
        duration_text = f" • {format_duration(song['duration'])}" if song['duration'] else ""

        html += f"""
            <div class="song">
                <div class="song-title">{song['title']}</div>
                <div class="song-meta">by {artist}{album_text}{duration_text}</div>
        """

        if song['description']:
            html += f"""
                <div class="song-description">{song['description']}</div>
            """

        html += f"""
                <a href="{song_url}" class="btn">Listen Now</a>
            </div>
        """

    # Add footer
    html += f"""
            <div class="footer">
                <p><a href="{SITE_URL}/music/playlist/all">Browse All Songs</a></p>
                <p>&copy; 2025 HastingTX Music • Songs created by Richard & Claude</p>
                <p><a href="{unsubscribe_url}">Unsubscribe from these emails</a></p>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def send_email_to_subscribers(songs):
    """Send email to all active subscribers."""
    if not songs:
        print("No new songs to send")
        return

    subscribers = Subscriber.get_active_subscribers()

    if not subscribers:
        print("No active subscribers")
        return

    print(f"Sending email about {len(songs)} new song(s) to {len(subscribers)} subscriber(s)")

    subject = f"New Music: {len(songs)} Song{'s' if len(songs) != 1 else ''} Added to HastingTX!"

    sent_count = 0
    failed_count = 0

    for subscriber in subscribers:
        try:
            # Generate email with personalized unsubscribe link
            html_content = generate_email_html(songs, subscriber['unsubscribe_token'])

            if not html_content:
                continue

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{FROM_NAME} <{FROM_EMAIL}>"
            msg['To'] = subscriber['email']

            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Send via SMTP
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.send_message(msg)

            sent_count += 1
            print(f"  ✓ Sent to {subscriber['email']}")

        except Exception as e:
            failed_count += 1
            print(f"  ✗ Failed to send to {subscriber['email']}: {e}")

    # Log the email send
    song_ids = [song['id'] for song in songs]
    success = failed_count == 0
    error_msg = f"{failed_count} failed" if failed_count > 0 else None

    EmailLog.create(
        subject=subject,
        recipient_count=sent_count,
        song_ids=song_ids,
        success=success,
        error_message=error_msg
    )

    print(f"\nSummary: {sent_count} sent, {failed_count} failed")
    return sent_count > 0


def main():
    """Main function to send weekly email."""
    print(f"Weekly email send starting at {datetime.now()}")

    # Get new songs
    new_songs = get_new_songs_since_last_email()

    if not new_songs:
        print("No new songs since last email")
        return 0

    print(f"Found {len(new_songs)} new song(s):")
    for song in new_songs:
        print(f"  - {song['title']} (uploaded {song['upload_date']})")

    # Send emails
    success = send_email_to_subscribers(new_songs)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
