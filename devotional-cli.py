#!/usr/bin/env python3
"""
Devotional CLI Tool for HastingTX
Manage devotional threads and individual devotionals from the command line.

Usage:
    ./venv/bin/python devotional-cli.py <command> <subcommand> [options]

Commands:
    threads     - Manage devotional threads (series)
    days        - Manage individual devotional days
    subscribers - Manage email subscribers
    audio       - Generate TTS audio
    stats       - View statistics
"""

import argparse
import sys
import os
import json
from datetime import datetime, date

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from devotional_models import (
    DevotionalThread, Devotional, DevotionalProgress,
    DevotionalSubscriber, DevotionalEnrollment
)
from devotional_utils import (
    generate_devotional_audio, format_duration,
    generate_identifier, ensure_directories
)


def threads_list(args):
    """List all devotional threads."""
    threads = DevotionalThread.get_all()

    if not threads:
        print("No devotional threads found.")
        return

    print(f"\n{'ID':<4} {'Identifier':<25} {'Title':<35} {'Days':<5} {'Published':<10}")
    print("-" * 85)

    for t in threads:
        pub = "Yes" if t['is_published'] else "No"
        title = t['title'][:33] + '..' if len(t['title']) > 35 else t['title']
        identifier = t['identifier'][:23] + '..' if len(t['identifier']) > 25 else t['identifier']
        print(f"{t['id']:<4} {identifier:<25} {title:<35} {t['total_days']:<5} {pub:<10}")

    print(f"\nTotal: {len(threads)} thread(s)")


def threads_show(args):
    """Show details of a specific thread."""
    thread = DevotionalThread.get_by_id(args.id) if args.id else DevotionalThread.get_by_identifier(args.identifier)

    if not thread:
        print(f"Thread not found.")
        return

    print(f"\n{'='*60}")
    print(f"Thread #{thread['id']}: {thread['title']}")
    print(f"{'='*60}")
    print(f"Identifier:  {thread['identifier']}")
    print(f"Author:      {thread['author'] or '-'}")
    print(f"Total Days:  {thread['total_days']}")
    print(f"Published:   {'Yes' if thread['is_published'] else 'No'}")
    print(f"Cover Image: {thread['cover_image'] or '-'}")
    print(f"Created:     {thread['created_at']}")

    if thread['description']:
        print(f"\nDescription:")
        print(f"  {thread['description']}")

    # Get devotionals
    devotionals = DevotionalThread.get_devotionals(thread['id'])
    if devotionals:
        print(f"\nDevotionals ({len(devotionals)}):")
        for d in devotionals:
            audio = "Has audio" if d['audio_filename'] else "No audio"
            print(f"  Day {d['day_number']}: {d['title']} ({audio})")


def threads_create(args):
    """Create a new devotional thread."""
    identifier = args.identifier or generate_identifier(args.title)

    # Check if identifier exists
    existing = DevotionalThread.get_by_identifier(identifier)
    if existing:
        print(f"Error: Identifier '{identifier}' already exists.")
        return

    thread_id = DevotionalThread.create(
        identifier=identifier,
        title=args.title,
        description=args.description,
        author=args.author,
        total_days=args.days,
        is_published=args.publish
    )

    print(f"Created thread #{thread_id}: {args.title}")
    print(f"Identifier: {identifier}")
    print(f"URL: /devotionals/{identifier}")


def threads_publish(args):
    """Publish or unpublish a thread."""
    thread = DevotionalThread.get_by_id(args.id)
    if not thread:
        print(f"Thread #{args.id} not found.")
        return

    DevotionalThread.update(args.id, is_published=not args.unpublish)
    status = "unpublished" if args.unpublish else "published"
    print(f"Thread '{thread['title']}' has been {status}.")


def threads_delete(args):
    """Delete a devotional thread."""
    thread = DevotionalThread.get_by_id(args.id)
    if not thread:
        print(f"Thread #{args.id} not found.")
        return

    if not args.force:
        confirm = input(f"Delete '{thread['title']}' and all its devotionals? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return

    DevotionalThread.delete(args.id)
    print(f"Deleted thread '{thread['title']}'.")


def days_list(args):
    """List devotionals in a thread."""
    thread = DevotionalThread.get_by_id(args.thread_id)
    if not thread:
        print(f"Thread #{args.thread_id} not found.")
        return

    devotionals = DevotionalThread.get_devotionals(args.thread_id)

    print(f"\nDevotionals in '{thread['title']}':\n")
    print(f"{'Day':<5} {'ID':<5} {'Title':<40} {'Scripture':<25} {'Audio':<8}")
    print("-" * 90)

    for d in devotionals:
        audio = "Yes" if d['audio_filename'] else "No"
        scripture = (d['scripture_reference'] or '-')[:23]
        title = d['title'][:38] + '..' if len(d['title']) > 40 else d['title']
        print(f"{d['day_number']:<5} {d['id']:<5} {title:<40} {scripture:<25} {audio:<8}")


def days_add(args):
    """Add a new devotional day."""
    thread = DevotionalThread.get_by_id(args.thread_id)
    if not thread:
        print(f"Thread #{args.thread_id} not found.")
        return

    # Read content from file if specified
    content = args.content
    if args.content_file:
        with open(args.content_file, 'r') as f:
            content = f.read()

    if not content:
        print("Error: Content is required. Use --content or --content-file.")
        return

    devotional_id = Devotional.create(
        thread_id=args.thread_id,
        day_number=args.day,
        title=args.title,
        content=content,
        scripture_reference=args.scripture_ref,
        scripture_text=args.scripture_text,
        reflection_questions=args.reflection,
        prayer=args.prayer
    )

    # Update thread total_days if needed
    if args.day > thread['total_days']:
        DevotionalThread.update(args.thread_id, total_days=args.day)

    print(f"Created Day {args.day}: {args.title} (ID: {devotional_id})")


def days_show(args):
    """Show details of a devotional."""
    devotional = Devotional.get_by_id(args.id)
    if not devotional:
        print(f"Devotional #{args.id} not found.")
        return

    print(f"\n{'='*60}")
    print(f"Day {devotional['day_number']}: {devotional['title']}")
    print(f"{'='*60}")
    print(f"Thread: {devotional['thread_title']} (ID: {devotional['thread_id']})")

    if devotional['scripture_reference']:
        print(f"\nScripture: {devotional['scripture_reference']}")
        if devotional['scripture_text']:
            print(f"{devotional['scripture_text'][:200]}{'...' if len(devotional['scripture_text'] or '') > 200 else ''}")

    print(f"\nContent ({len(devotional['content'])} chars):")
    print(f"{devotional['content'][:500]}{'...' if len(devotional['content']) > 500 else ''}")

    if devotional['reflection_questions']:
        print(f"\nReflection Questions:")
        print(f"{devotional['reflection_questions'][:200]}...")

    if devotional['prayer']:
        print(f"\nPrayer:")
        print(f"{devotional['prayer'][:200]}...")

    print(f"\nAudio: {devotional['audio_filename'] or 'Not generated'}")
    if devotional['audio_duration']:
        print(f"Duration: {format_duration(devotional['audio_duration'])}")


def days_delete(args):
    """Delete a devotional."""
    devotional = Devotional.get_by_id(args.id)
    if not devotional:
        print(f"Devotional #{args.id} not found.")
        return

    if not args.force:
        confirm = input(f"Delete Day {devotional['day_number']}: '{devotional['title']}'? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return

    Devotional.delete(args.id)
    print(f"Deleted devotional.")


def audio_generate(args):
    """Generate TTS audio for a devotional."""
    devotional = Devotional.get_by_id(args.id)
    if not devotional:
        print(f"Devotional #{args.id} not found.")
        return

    print(f"Generating audio for Day {devotional['day_number']}: {devotional['title']}...")

    filename, duration = generate_devotional_audio(devotional, args.voice)

    if filename:
        Devotional.update(args.id, audio_filename=filename, audio_duration=duration)
        print(f"Audio generated: {filename}")
        print(f"Duration: {format_duration(duration)}")
    else:
        print("Audio generation failed. Check Google Cloud credentials.")


def audio_generate_all(args):
    """Generate audio for all devotionals in a thread."""
    thread = DevotionalThread.get_by_id(args.thread_id)
    if not thread:
        print(f"Thread #{args.thread_id} not found.")
        return

    devotionals = DevotionalThread.get_devotionals(args.thread_id)
    if not devotionals:
        print("No devotionals in this thread.")
        return

    print(f"Generating audio for {len(devotionals)} devotional(s)...")

    for d in devotionals:
        if d['audio_filename'] and not args.regenerate:
            print(f"  Day {d['day_number']}: Skipped (already has audio)")
            continue

        print(f"  Day {d['day_number']}: {d['title']}...")
        filename, duration = generate_devotional_audio(d, args.voice)

        if filename:
            Devotional.update(d['id'], audio_filename=filename, audio_duration=duration)
            print(f"    -> {filename} ({format_duration(duration)})")
        else:
            print(f"    -> Failed")

    print("Done!")


def subscribers_list(args):
    """List email subscribers."""
    subscribers = DevotionalSubscriber.get_all_active()

    if not subscribers:
        print("No active subscribers.")
        return

    print(f"\n{'ID':<5} {'Email':<35} {'Name':<20} {'Notify New':<12} {'Subscribed':<12}")
    print("-" * 90)

    for s in subscribers:
        notify = "Yes" if s['receive_new_threads'] else "No"
        name = (s['name'] or '-')[:18]
        email = s['email'][:33] + '..' if len(s['email']) > 35 else s['email']
        sub_date = s['subscribed_at'].strftime('%Y-%m-%d') if s['subscribed_at'] else '-'
        print(f"{s['id']:<5} {email:<35} {name:<20} {notify:<12} {sub_date:<12}")

    print(f"\nTotal: {len(subscribers)} subscriber(s)")


def stats_overview(args):
    """Show devotional statistics."""
    threads = DevotionalThread.get_all()
    subscribers = DevotionalSubscriber.get_all_active()

    published = len([t for t in threads if t['is_published']])
    total_devotionals = sum(DevotionalThread.count_devotionals(t['id']) for t in threads)

    print("\n" + "="*40)
    print("Devotional Statistics")
    print("="*40)
    print(f"Total Threads:      {len(threads)}")
    print(f"Published Threads:  {published}")
    print(f"Draft Threads:      {len(threads) - published}")
    print(f"Total Devotionals:  {total_devotionals}")
    print(f"Active Subscribers: {len(subscribers)}")
    print("="*40)


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


def import_json(args):
    """Import a devotional thread from a JSON file."""
    # Read JSON file
    try:
        with open(args.file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {args.file}")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        return

    # Extract thread info
    thread_id_str = data.get('thread_id')
    thread_title = data.get('thread_title')
    thread_description = data.get('thread_description', '')
    days = data.get('days', [])

    if not thread_id_str or not thread_title:
        print("Error: JSON must contain 'thread_id' and 'thread_title'")
        return

    if not days:
        print("Error: JSON must contain 'days' array")
        return

    # Check if thread already exists
    existing = DevotionalThread.get_by_identifier(thread_id_str)
    if existing:
        if not args.force:
            print(f"Error: Thread '{thread_id_str}' already exists. Use --force to overwrite.")
            return
        else:
            print(f"Deleting existing thread '{thread_id_str}'...")
            DevotionalThread.delete(existing['id'])

    # Determine author (JSON field > CLI arg > default)
    author = data.get('author') or args.author or "Rick Hasting & Claude"

    # Create the thread
    print(f"\nCreating thread: {thread_title}")
    print(f"  Identifier: {thread_id_str}")
    print(f"  Days: {len(days)}")

    db_thread_id = DevotionalThread.create(
        identifier=thread_id_str,
        title=thread_title,
        description=thread_description,
        author=author,
        total_days=len(days),
        is_published=args.publish
    )

    if not db_thread_id:
        print("Error: Failed to create thread")
        return

    print(f"  Created thread ID: {db_thread_id}")

    # Create each day
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

        print(f"  Day {day_num}: {title} (ID: {devotional_id})")

    print(f"\nThread created successfully!")
    print(f"URL: /devotionals/{thread_id_str}")

    # Generate audio if requested
    if args.audio:
        print(f"\nGenerating audio for {len(days)} devotional(s)...")
        devotionals = DevotionalThread.get_devotionals(db_thread_id)
        for d in devotionals:
            print(f"  Day {d['day_number']}: {d['title']}...")
            filename, duration = generate_devotional_audio(d)
            if filename:
                Devotional.update(d['id'], audio_filename=filename, audio_duration=duration)
                print(f"    -> {filename} ({format_duration(duration)})")
            else:
                print(f"    -> Failed")
        print("Audio generation complete!")


def import_all_json(args):
    """Import all JSON files from a directory."""
    import glob

    pattern = os.path.join(args.directory, '*.json')
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"No JSON files found in {args.directory}")
        return

    print(f"Found {len(files)} JSON file(s):\n")
    for f in files:
        print(f"  {os.path.basename(f)}")

    if not args.force:
        confirm = input(f"\nImport all {len(files)} files? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return

    # Create a mock args object for each file
    class MockArgs:
        def __init__(self, file_path, publish, audio, author, force):
            self.file = file_path
            self.publish = publish
            self.audio = audio
            self.author = author
            self.force = force

    for f in files:
        print(f"\n{'='*60}")
        print(f"Importing: {os.path.basename(f)}")
        print(f"{'='*60}")
        mock_args = MockArgs(f, args.publish, args.audio, args.author, True)
        import_json(mock_args)

    print(f"\n{'='*60}")
    print(f"Import complete! Processed {len(files)} file(s).")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description='Devotional CLI Tool for HastingTX',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Threads commands
    threads_parser = subparsers.add_parser('threads', help='Manage devotional threads')
    threads_sub = threads_parser.add_subparsers(dest='subcommand')

    # threads list
    threads_sub.add_parser('list', help='List all threads')

    # threads show
    show_parser = threads_sub.add_parser('show', help='Show thread details')
    show_group = show_parser.add_mutually_exclusive_group(required=True)
    show_group.add_argument('--id', type=int, help='Thread ID')
    show_group.add_argument('--identifier', help='Thread identifier')

    # threads create
    create_parser = threads_sub.add_parser('create', help='Create a new thread')
    create_parser.add_argument('title', help='Thread title')
    create_parser.add_argument('--identifier', help='URL identifier (auto-generated if not provided)')
    create_parser.add_argument('--description', help='Thread description')
    create_parser.add_argument('--author', help='Author name')
    create_parser.add_argument('--days', type=int, default=5, help='Number of days (default: 5)')
    create_parser.add_argument('--publish', action='store_true', help='Publish immediately')

    # threads publish/unpublish
    pub_parser = threads_sub.add_parser('publish', help='Publish or unpublish a thread')
    pub_parser.add_argument('id', type=int, help='Thread ID')
    pub_parser.add_argument('--unpublish', action='store_true', help='Unpublish instead')

    # threads delete
    del_parser = threads_sub.add_parser('delete', help='Delete a thread')
    del_parser.add_argument('id', type=int, help='Thread ID')
    del_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')

    # Days commands
    days_parser = subparsers.add_parser('days', help='Manage devotional days')
    days_sub = days_parser.add_subparsers(dest='subcommand')

    # days list
    list_parser = days_sub.add_parser('list', help='List devotionals in a thread')
    list_parser.add_argument('thread_id', type=int, help='Thread ID')

    # days add
    add_parser = days_sub.add_parser('add', help='Add a new devotional day')
    add_parser.add_argument('thread_id', type=int, help='Thread ID')
    add_parser.add_argument('day', type=int, help='Day number')
    add_parser.add_argument('title', help='Devotional title')
    add_parser.add_argument('--content', help='Devotional content')
    add_parser.add_argument('--content-file', help='Read content from file')
    add_parser.add_argument('--scripture-ref', help='Scripture reference')
    add_parser.add_argument('--scripture-text', help='Scripture text')
    add_parser.add_argument('--reflection', help='Reflection questions')
    add_parser.add_argument('--prayer', help='Closing prayer')

    # days show
    show_d_parser = days_sub.add_parser('show', help='Show devotional details')
    show_d_parser.add_argument('id', type=int, help='Devotional ID')

    # days delete
    del_d_parser = days_sub.add_parser('delete', help='Delete a devotional')
    del_d_parser.add_argument('id', type=int, help='Devotional ID')
    del_d_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')

    # Audio commands
    audio_parser = subparsers.add_parser('audio', help='Generate TTS audio')
    audio_sub = audio_parser.add_subparsers(dest='subcommand')

    # audio generate
    gen_parser = audio_sub.add_parser('generate', help='Generate audio for a devotional')
    gen_parser.add_argument('id', type=int, help='Devotional ID')
    gen_parser.add_argument('--voice', default='en-US-Neural2-D', help='TTS voice name')

    # audio generate-all
    gen_all_parser = audio_sub.add_parser('generate-all', help='Generate audio for all devotionals in a thread')
    gen_all_parser.add_argument('thread_id', type=int, help='Thread ID')
    gen_all_parser.add_argument('--voice', default='en-US-Neural2-D', help='TTS voice name')
    gen_all_parser.add_argument('--regenerate', action='store_true', help='Regenerate existing audio')

    # Subscribers commands
    subs_parser = subparsers.add_parser('subscribers', help='Manage email subscribers')
    subs_sub = subs_parser.add_subparsers(dest='subcommand')
    subs_sub.add_parser('list', help='List all subscribers')

    # Stats commands
    stats_parser = subparsers.add_parser('stats', help='View statistics')
    stats_sub = stats_parser.add_subparsers(dest='subcommand')
    stats_sub.add_parser('overview', help='Show overview statistics')

    # Import commands
    import_parser = subparsers.add_parser('import', help='Import devotionals from JSON')
    import_sub = import_parser.add_subparsers(dest='subcommand')

    # import file
    import_file_parser = import_sub.add_parser('file', help='Import a single JSON file')
    import_file_parser.add_argument('file', help='Path to JSON file')
    import_file_parser.add_argument('--publish', action='store_true', help='Publish immediately')
    import_file_parser.add_argument('--audio', action='store_true', help='Generate audio after import')
    import_file_parser.add_argument('--author', help='Author name (default: Rick Hasting & Claude)')
    import_file_parser.add_argument('--force', '-f', action='store_true', help='Overwrite existing thread')

    # import directory
    import_dir_parser = import_sub.add_parser('directory', help='Import all JSON files from a directory')
    import_dir_parser.add_argument('directory', help='Path to directory containing JSON files')
    import_dir_parser.add_argument('--publish', action='store_true', help='Publish all immediately')
    import_dir_parser.add_argument('--audio', action='store_true', help='Generate audio after import')
    import_dir_parser.add_argument('--author', help='Author name (default: Rick Hasting & Claude)')
    import_dir_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')

    args = parser.parse_args()

    # Ensure directories exist
    ensure_directories()

    # Route to appropriate function
    if args.command == 'threads':
        if args.subcommand == 'list':
            threads_list(args)
        elif args.subcommand == 'show':
            threads_show(args)
        elif args.subcommand == 'create':
            threads_create(args)
        elif args.subcommand == 'publish':
            threads_publish(args)
        elif args.subcommand == 'delete':
            threads_delete(args)
        else:
            threads_parser.print_help()
    elif args.command == 'days':
        if args.subcommand == 'list':
            days_list(args)
        elif args.subcommand == 'add':
            days_add(args)
        elif args.subcommand == 'show':
            days_show(args)
        elif args.subcommand == 'delete':
            days_delete(args)
        else:
            days_parser.print_help()
    elif args.command == 'audio':
        if args.subcommand == 'generate':
            audio_generate(args)
        elif args.subcommand == 'generate-all':
            audio_generate_all(args)
        else:
            audio_parser.print_help()
    elif args.command == 'subscribers':
        if args.subcommand == 'list':
            subscribers_list(args)
        else:
            subs_parser.print_help()
    elif args.command == 'stats':
        if args.subcommand == 'overview':
            stats_overview(args)
        else:
            stats_parser.print_help()
    elif args.command == 'import':
        if args.subcommand == 'file':
            import_json(args)
        elif args.subcommand == 'directory':
            import_all_json(args)
        else:
            import_parser.print_help()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
