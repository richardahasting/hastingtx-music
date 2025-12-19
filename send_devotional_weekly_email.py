#!/usr/bin/env python3
"""Send weekly email to devotional subscribers about new threads."""
import os
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from devotional_models import DevotionalThread, DevotionalSubscriber

# Email configuration
SMTP_HOST = 'localhost'
SMTP_PORT = 25
FROM_EMAIL = 'noreply@hastingtx.org'
FROM_NAME = 'HastingTX Devotionals'
SITE_URL = 'https://hastingtx.org'

# Track last send time in a simple file
LAST_SEND_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.devotional_email_last_send')


def get_last_send_time():
    """Get the timestamp of the last email send."""
    try:
        if os.path.exists(LAST_SEND_FILE):
            with open(LAST_SEND_FILE, 'r') as f:
                timestamp = float(f.read().strip())
                return datetime.fromtimestamp(timestamp)
    except Exception:
        pass
    # Default to 7 days ago
    return datetime.now() - timedelta(days=7)


def save_last_send_time():
    """Save the current timestamp as the last send time."""
    with open(LAST_SEND_FILE, 'w') as f:
        f.write(str(datetime.now().timestamp()))


def get_new_threads_since_last_email():
    """Get published threads added since the last email was sent."""
    cutoff_date = get_last_send_time()

    # Get all published threads
    all_threads = DevotionalThread.get_all(published_only=True)

    # Filter threads created after cutoff
    new_threads = [
        thread for thread in all_threads
        if thread['created_at'] and thread['created_at'] > cutoff_date
    ]

    return new_threads


def generate_email_html(threads, unsubscribe_token):
    """Generate HTML email content."""
    unsubscribe_url = f"{SITE_URL}/devotionals/unsubscribe/{unsubscribe_token}"

    if not threads:
        return None  # Don't send email if no new threads

    # Start HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #7c3aed; color: white; padding: 20px; text-align: center; }}
            .thread {{ border: 1px solid #ecf0f1; padding: 15px; margin: 15px 0; border-radius: 5px; }}
            .thread-title {{ font-size: 1.2em; font-weight: bold; color: #7c3aed; margin-bottom: 5px; }}
            .thread-meta {{ color: #7f8c8d; font-size: 0.9em; margin: 5px 0; }}
            .thread-description {{ margin: 10px 0; }}
            .btn {{ display: inline-block; background-color: #7c3aed; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-top: 10px; }}
            .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ecf0f1; color: #7f8c8d; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>New Devotionals Available!</h1>
                <p>{len(threads)} new devotional{"s" if len(threads) != 1 else ""} added this week</p>
            </div>

            <p>Hello! New devotional threads have been added to Pull The Thread. Take a moment to explore:</p>
    """

    # Add each thread
    for thread in threads:
        thread_url = f"{SITE_URL}/devotionals/{thread['identifier']}"
        author = thread['author'] or 'Richard'
        days_text = f"{thread['total_days']} day{'s' if thread['total_days'] != 1 else ''}"
        series_text = f" • Series: {thread['series']}" if thread['series'] else ""

        html += f"""
            <div class="thread">
                <div class="thread-title">{thread['title']}</div>
                <div class="thread-meta">by {author} • {days_text}{series_text}</div>
        """

        if thread['description']:
            # Truncate long descriptions
            desc = thread['description'][:200] + '...' if len(thread['description']) > 200 else thread['description']
            html += f"""
                <div class="thread-description">{desc}</div>
            """

        html += f"""
                <a href="{thread_url}" class="btn">Start Reading</a>
            </div>
        """

    # Add footer
    html += f"""
            <div class="footer">
                <p><a href="{SITE_URL}/devotionals">Browse All Devotionals</a></p>
                <p>Pull The Thread - Daily Devotionals from HastingTX</p>
                <p><a href="{unsubscribe_url}">Unsubscribe from these emails</a></p>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def send_email_to_subscribers(threads):
    """Send email to all active subscribers who want new thread notifications."""
    if not threads:
        print("No new threads to send")
        return False

    # Get subscribers who want new thread notifications
    all_subscribers = DevotionalSubscriber.get_all_active()
    subscribers = [s for s in all_subscribers if s.get('receive_new_threads', True)]

    if not subscribers:
        print("No active subscribers with new thread notifications enabled")
        return False

    print(f"Sending email about {len(threads)} new thread(s) to {len(subscribers)} subscriber(s)")

    subject = f"New Devotional{'s' if len(threads) != 1 else ''}: {threads[0]['title']}" + (f" and {len(threads)-1} more" if len(threads) > 1 else "")

    sent_count = 0
    failed_count = 0

    for subscriber in subscribers:
        try:
            # Generate email with personalized unsubscribe link
            html_content = generate_email_html(threads, subscriber['unsubscribe_token'])

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
            print(f"  Sent to {subscriber['email']}")

        except Exception as e:
            failed_count += 1
            print(f"  Failed to send to {subscriber['email']}: {e}")

    print(f"\nSummary: {sent_count} sent, {failed_count} failed")

    # Save the send time on success
    if sent_count > 0:
        save_last_send_time()

    return sent_count > 0


def main():
    """Main function to send weekly devotional email."""
    print(f"Devotional weekly email send starting at {datetime.now()}")

    # Get new threads
    new_threads = get_new_threads_since_last_email()

    if not new_threads:
        print("No new devotional threads since last email")
        return 0

    print(f"Found {len(new_threads)} new thread(s):")
    for thread in new_threads:
        print(f"  - {thread['title']} (created {thread['created_at']})")

    # Send emails
    success = send_email_to_subscribers(new_threads)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
