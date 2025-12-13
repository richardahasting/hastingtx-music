#!/usr/bin/env python3
"""
HastingTX Gallery CLI - Command line interface for managing gallery images.

Usage:
    ./gallery-cli.py <command> <subcommand> [options]

Commands:
    images      - Manage images (list, add, import, update, delete)
    sections    - Manage sections (list, create, show, delete)
    export      - Export data for book integration
    stats       - View statistics
"""

import argparse
import sys
import os
import json
from datetime import datetime
from tabulate import tabulate

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import db
from config import config
from gallery_models import GallerySection, GalleryImage
from gallery_utils import (
    process_image_file, delete_image_files, generate_gallery_identifier,
    parse_date_input, format_date_for_display, allowed_image_file
)

# Gallery directories
GALLERY_IMAGES_DIR = os.path.join(config.UPLOAD_FOLDER, 'gallery', 'images')
GALLERY_THUMBNAILS_DIR = os.path.join(config.UPLOAD_FOLDER, 'gallery', 'thumbnails')


def ensure_directories():
    """Ensure gallery directories exist."""
    os.makedirs(GALLERY_IMAGES_DIR, exist_ok=True)
    os.makedirs(GALLERY_THUMBNAILS_DIR, exist_ok=True)


def truncate(text, length=50):
    """Truncate text to specified length."""
    if not text:
        return '-'
    if len(text) <= length:
        return text
    return text[:length-3] + '...'


# ============================================================================
# IMAGE COMMANDS
# ============================================================================

def cmd_images_list(args):
    """List all images."""
    if args.section:
        section = GallerySection.get_by_identifier(args.section)
        if not section:
            print(f"Error: Section '{args.section}' not found", file=sys.stderr)
            sys.exit(1)
        images = GalleryImage.get_by_section(section['id'])
    elif args.date:
        date = parse_date_input(args.date)
        if not date:
            print(f"Error: Invalid date format '{args.date}'", file=sys.stderr)
            sys.exit(1)
        images = GalleryImage.get_by_date(date)
    else:
        images = GalleryImage.get_all()

    if args.format == 'json':
        print(json.dumps([dict(i) for i in images], default=str, indent=2))
        return

    if not images:
        print("No images found.")
        return

    headers = ['ID', 'Title', 'Date', 'Section', 'Views']
    rows = []
    for img in images:
        section_name = '-'
        if img.get('section_id'):
            section = GallerySection.get_by_id(img['section_id'])
            section_name = section['name'] if section else '-'

        rows.append([
            img['id'],
            truncate(img['title'], 40),
            img['significance_date'].strftime('%Y-%m-%d') if img['significance_date'] else '-',
            truncate(section_name, 20),
            img['view_count'] or 0
        ])

    print(tabulate(rows, headers=headers, tablefmt='simple'))
    print(f"\nTotal: {len(images)} images")


def cmd_images_show(args):
    """Show detailed info for an image."""
    image = GalleryImage.get_by_id(args.id)
    if not image:
        print(f"Error: Image #{args.id} not found", file=sys.stderr)
        sys.exit(1)

    if args.format == 'json':
        print(json.dumps(dict(image), default=str, indent=2))
        return

    section = None
    if image['section_id']:
        section = GallerySection.get_by_id(image['section_id'])

    print(f"\n{'='*60}")
    print(f"Image #{image['id']}: {image['title']}")
    print(f"{'='*60}")
    print(f"  Identifier:    {image['identifier']}")
    print(f"  Date:          {image['significance_date'] or '-'}")
    print(f"  Section:       {section['name'] if section else '-'}")
    print(f"  Source:        {image['source'] or '-'}")
    print(f"  Filename:      {image['filename']}")
    print(f"  Type:          {image['file_type'] or '-'}")
    print(f"  Dimensions:    {image['width'] or '?'} x {image['height'] or '?'}")
    print(f"  File Size:     {image['file_size'] or 0:,} bytes")
    print(f"  Views:         {image['view_count'] or 0}")
    print(f"  Uploaded:      {image['upload_date']}")
    print(f"\n  Description:")
    print(f"    {image['description'] or '(none)'}")


def cmd_images_add(args):
    """Add a single image to the gallery."""
    ensure_directories()

    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    if not allowed_image_file(args.file):
        print(f"Error: Unsupported file type", file=sys.stderr)
        sys.exit(1)

    # Process the image
    print(f"Processing {args.file}...")
    file_info = process_image_file(args.file, GALLERY_IMAGES_DIR, GALLERY_THUMBNAILS_DIR)

    if not file_info:
        print("Error: Failed to process image", file=sys.stderr)
        sys.exit(1)

    # Get title
    title = args.title or os.path.basename(args.file).rsplit('.', 1)[0]

    # Parse date
    significance_date = None
    if args.date:
        significance_date = parse_date_input(args.date)
        if not significance_date:
            print(f"Warning: Could not parse date '{args.date}'")

    # Get section
    section_id = None
    if args.section:
        section = GallerySection.get_by_identifier(args.section)
        if not section:
            # Try to create the section
            if args.create_section:
                section = GallerySection.create(
                    identifier=generate_gallery_identifier(args.section),
                    name=args.section
                )
                print(f"Created section: {args.section}")
            else:
                print(f"Error: Section '{args.section}' not found. Use --create-section to create it.")
                sys.exit(1)
        section_id = section['id']

    # Generate identifier
    identifier = generate_gallery_identifier(title)
    existing = GalleryImage.get_by_identifier(identifier)
    if existing:
        counter = 1
        base_identifier = identifier
        while existing:
            identifier = f"{base_identifier}-{counter}"
            existing = GalleryImage.get_by_identifier(identifier)
            counter += 1

    # Create database record
    image = GalleryImage.create(
        identifier=identifier,
        title=title,
        filename=file_info['filename'],
        file_type=file_info['file_type'],
        file_size=file_info['file_size'],
        description=args.description,
        significance_date=significance_date,
        source=args.source,
        thumbnail=file_info['thumbnail'],
        width=file_info['width'],
        height=file_info['height'],
        section_id=section_id
    )

    print(f"Added image #{image['id']}: {image['title']}")
    print(f"  Identifier: {image['identifier']}")
    if significance_date:
        print(f"  Date: {significance_date}")
    if section_id:
        print(f"  Section: {args.section}")


def cmd_images_import(args):
    """Import multiple images from a directory."""
    ensure_directories()

    if not os.path.isdir(args.directory):
        print(f"Error: Directory not found: {args.directory}", file=sys.stderr)
        sys.exit(1)

    # Get section
    section_id = None
    if args.section:
        section = GallerySection.get_by_identifier(args.section)
        if not section:
            if args.create_section:
                section = GallerySection.create(
                    identifier=generate_gallery_identifier(args.section),
                    name=args.section
                )
                print(f"Created section: {args.section}")
            else:
                print(f"Error: Section '{args.section}' not found. Use --create-section to create it.")
                sys.exit(1)
        section_id = section['id']

    # Find all image files
    files = []
    for filename in sorted(os.listdir(args.directory)):
        filepath = os.path.join(args.directory, filename)
        if os.path.isfile(filepath) and allowed_image_file(filename):
            files.append(filepath)

    if not files:
        print("No supported image files found in directory.")
        return

    print(f"Found {len(files)} images to import")
    imported = 0
    failed = 0

    for filepath in files:
        filename = os.path.basename(filepath)
        print(f"  Processing {filename}...", end=' ')

        try:
            file_info = process_image_file(filepath, GALLERY_IMAGES_DIR, GALLERY_THUMBNAILS_DIR)
            if not file_info:
                print("FAILED (processing error)")
                failed += 1
                continue

            title = filename.rsplit('.', 1)[0].replace('-', ' ').replace('_', ' ')
            identifier = generate_gallery_identifier(title)

            # Ensure unique identifier
            existing = GalleryImage.get_by_identifier(identifier)
            if existing:
                counter = 1
                base_identifier = identifier
                while existing:
                    identifier = f"{base_identifier}-{counter}"
                    existing = GalleryImage.get_by_identifier(identifier)
                    counter += 1

            image = GalleryImage.create(
                identifier=identifier,
                title=title,
                filename=file_info['filename'],
                file_type=file_info['file_type'],
                file_size=file_info['file_size'],
                thumbnail=file_info['thumbnail'],
                width=file_info['width'],
                height=file_info['height'],
                section_id=section_id
            )
            print(f"OK (#{image['id']})")
            imported += 1

        except Exception as e:
            print(f"FAILED ({e})")
            failed += 1

    print(f"\nImport complete: {imported} imported, {failed} failed")


def cmd_images_update(args):
    """Update image metadata."""
    image = GalleryImage.get_by_id(args.id)
    if not image:
        print(f"Error: Image #{args.id} not found", file=sys.stderr)
        sys.exit(1)

    updates = {}
    if args.title:
        updates['title'] = args.title
    if args.description:
        updates['description'] = args.description
    if args.date:
        updates['significance_date'] = parse_date_input(args.date)
    if args.source:
        updates['source'] = args.source
    if args.section:
        section = GallerySection.get_by_identifier(args.section)
        if not section:
            print(f"Error: Section '{args.section}' not found", file=sys.stderr)
            sys.exit(1)
        updates['section_id'] = section['id']

    if not updates:
        print("No updates specified. Use --title, --description, --date, --source, or --section.")
        sys.exit(1)

    updated = GalleryImage.update(args.id, **updates)
    print(f"Updated image #{args.id}: {updated['title']}")
    for key, value in updates.items():
        print(f"  {key}: {truncate(str(value), 60)}")


def cmd_images_delete(args):
    """Delete an image."""
    image = GalleryImage.get_by_id(args.id)
    if not image:
        print(f"Error: Image #{args.id} not found", file=sys.stderr)
        sys.exit(1)

    if not args.force:
        confirm = input(f"Delete '{image['title']}'? This cannot be undone. (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return

    # Delete files
    delete_image_files(image['filename'], image['thumbnail'],
                      GALLERY_IMAGES_DIR, GALLERY_THUMBNAILS_DIR)

    # Delete database record
    GalleryImage.delete(args.id)
    print(f"Deleted image #{args.id}: {image['title']}")


def cmd_images_search(args):
    """Search for images."""
    images = GalleryImage.search(args.query)

    if not images:
        print("No images found.")
        return

    headers = ['ID', 'Title', 'Date', 'Source']
    rows = [[i['id'], truncate(i['title'], 40),
             i['significance_date'].strftime('%Y-%m-%d') if i['significance_date'] else '-',
             truncate(i['source'], 30)] for i in images]
    print(tabulate(rows, headers=headers, tablefmt='simple'))
    print(f"\nFound: {len(images)} images")


# ============================================================================
# SECTION COMMANDS
# ============================================================================

def cmd_sections_list(args):
    """List all sections."""
    sections = GallerySection.get_with_counts()

    if args.format == 'json':
        print(json.dumps([dict(s) for s in sections], default=str, indent=2))
        return

    headers = ['ID', 'Identifier', 'Name', 'Images', 'Sort Order']
    rows = []
    for s in sections:
        rows.append([s['id'], s['identifier'], s['name'], s['image_count'], s['sort_order']])

    print(tabulate(rows, headers=headers, tablefmt='simple'))
    print(f"\nTotal: {len(sections)} sections")


def cmd_sections_create(args):
    """Create a new section."""
    identifier = args.identifier or generate_gallery_identifier(args.name)

    existing = GallerySection.get_by_identifier(identifier)
    if existing:
        print(f"Error: Section with identifier '{identifier}' already exists", file=sys.stderr)
        sys.exit(1)

    section = GallerySection.create(
        identifier=identifier,
        name=args.name,
        description=args.description,
        sort_order=args.sort_order or 0
    )

    print(f"Created section #{section['id']}: {section['name']}")
    print(f"  Identifier: {section['identifier']}")


def cmd_sections_show(args):
    """Show section details."""
    section = GallerySection.get_by_identifier(args.identifier)
    if not section:
        print(f"Error: Section '{args.identifier}' not found", file=sys.stderr)
        sys.exit(1)

    images = GalleryImage.get_by_section(section['id'])

    print(f"\n{'='*60}")
    print(f"Section: {section['name']}")
    print(f"{'='*60}")
    print(f"  ID:          {section['id']}")
    print(f"  Identifier:  {section['identifier']}")
    print(f"  Description: {section['description'] or '-'}")
    print(f"  Sort Order:  {section['sort_order']}")
    print(f"  Images:      {len(images)}")

    if images:
        print(f"\n  Image List:")
        for i, img in enumerate(images, 1):
            date_str = img['significance_date'].strftime('%Y-%m-%d') if img['significance_date'] else 'No date'
            print(f"    {i:2}. [{img['id']:3}] {truncate(img['title'], 40)} ({date_str})")


def cmd_sections_delete(args):
    """Delete a section."""
    section = GallerySection.get_by_identifier(args.identifier)
    if not section:
        print(f"Error: Section '{args.identifier}' not found", file=sys.stderr)
        sys.exit(1)

    if section['identifier'] == 'uncategorized':
        print("Error: Cannot delete the Uncategorized section", file=sys.stderr)
        sys.exit(1)

    image_count = GallerySection.get_image_count(section['id'])

    if not args.force:
        confirm = input(f"Delete section '{section['name']}' ({image_count} images will be moved to Uncategorized)? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return

    GallerySection.delete(section['id'])
    print(f"Deleted section: {section['name']}")
    if image_count > 0:
        print(f"  {image_count} images moved to Uncategorized")


# ============================================================================
# EXPORT COMMANDS
# ============================================================================

def cmd_export_date(args):
    """Export images for a specific date."""
    date = parse_date_input(args.date)
    if not date:
        print(f"Error: Invalid date format '{args.date}'", file=sys.stderr)
        sys.exit(1)

    images = GalleryImage.get_by_date(date)

    result = {
        'date': str(date),
        'date_display': format_date_for_display(date),
        'count': len(images),
        'images': []
    }

    for img in images:
        result['images'].append({
            'id': img['id'],
            'identifier': img['identifier'],
            'title': img['title'],
            'description': img['description'],
            'source': img['source'],
            'filename': img['filename'],
            'thumbnail': img['thumbnail'],
            'width': img['width'],
            'height': img['height']
        })

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Exported {len(images)} images for {date} to {args.output}")
    else:
        print(json.dumps(result, indent=2))


def cmd_export_section(args):
    """Export images in a section."""
    section = GallerySection.get_by_identifier(args.section)
    if not section:
        print(f"Error: Section '{args.section}' not found", file=sys.stderr)
        sys.exit(1)

    images = GalleryImage.get_by_section(section['id'])

    if args.format == 'html':
        # Generate HTML snippet
        html = f'<div class="gallery-section" data-section="{section["identifier"]}">\n'
        html += f'  <h2>{section["name"]}</h2>\n'
        if section['description']:
            html += f'  <p class="section-description">{section["description"]}</p>\n'
        html += '  <div class="gallery-grid">\n'
        for img in images:
            html += f'    <figure class="gallery-item" data-date="{img["significance_date"] or ""}">\n'
            html += f'      <img src="/static/uploads/gallery/images/{img["filename"]}" alt="{img["title"]}">\n'
            html += f'      <figcaption>{img["title"]}</figcaption>\n'
            html += '    </figure>\n'
        html += '  </div>\n'
        html += '</div>\n'

        if args.output:
            with open(args.output, 'w') as f:
                f.write(html)
            print(f"Exported {len(images)} images to {args.output}")
        else:
            print(html)
    else:
        # JSON format
        result = {
            'section': dict(section),
            'count': len(images),
            'images': [dict(img) for img in images]
        }

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            print(f"Exported {len(images)} images to {args.output}")
        else:
            print(json.dumps(result, indent=2, default=str))


# ============================================================================
# STATS COMMANDS
# ============================================================================

def cmd_stats_overview(args):
    """Show overall statistics."""
    total_images = GalleryImage.get_count()
    sections = GallerySection.get_with_counts()

    # Get images with dates
    dates = GalleryImage.get_dates_with_images()

    print(f"\n{'='*40}")
    print(f"Letters From Dick Gallery - Statistics")
    print(f"{'='*40}")
    print(f"  Total Images:     {total_images}")
    print(f"  Sections:         {len(sections)}")
    print(f"  Unique Dates:     {len(dates)}")

    if dates:
        print(f"\n  Date Range:")
        print(f"    Earliest: {dates[0]['significance_date']}")
        print(f"    Latest:   {dates[-1]['significance_date']}")

    print(f"\n  Images per Section:")
    for s in sections:
        print(f"    {s['name']:30} {s['image_count']:5}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='HastingTX Gallery CLI - Manage gallery images',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Command category')

    # ---- IMAGES ----
    images_parser = subparsers.add_parser('images', help='Manage images')
    images_sub = images_parser.add_subparsers(dest='subcommand')

    # images list
    p = images_sub.add_parser('list', help='List all images')
    p.add_argument('--section', '-s', help='Filter by section identifier')
    p.add_argument('--date', '-d', help='Filter by date (YYYY-MM-DD)')
    p.add_argument('--format', choices=['table', 'json'], default='table')
    p.set_defaults(func=cmd_images_list)

    # images show
    p = images_sub.add_parser('show', help='Show image details')
    p.add_argument('id', type=int, help='Image ID')
    p.add_argument('--format', choices=['table', 'json'], default='table')
    p.set_defaults(func=cmd_images_show)

    # images add
    p = images_sub.add_parser('add', help='Add a single image')
    p.add_argument('file', help='Image file path')
    p.add_argument('--title', '-t', help='Image title')
    p.add_argument('--date', '-d', help='Significance date (YYYY-MM-DD)')
    p.add_argument('--section', '-s', help='Section identifier')
    p.add_argument('--description', help='Description')
    p.add_argument('--source', help='Image source')
    p.add_argument('--create-section', action='store_true', help='Create section if not exists')
    p.set_defaults(func=cmd_images_add)

    # images import
    p = images_sub.add_parser('import', help='Import images from directory')
    p.add_argument('directory', help='Directory containing images')
    p.add_argument('--section', '-s', help='Section identifier')
    p.add_argument('--create-section', action='store_true', help='Create section if not exists')
    p.set_defaults(func=cmd_images_import)

    # images update
    p = images_sub.add_parser('update', help='Update image metadata')
    p.add_argument('id', type=int, help='Image ID')
    p.add_argument('--title', help='New title')
    p.add_argument('--description', help='New description')
    p.add_argument('--date', help='New significance date')
    p.add_argument('--source', help='New source')
    p.add_argument('--section', help='New section identifier')
    p.set_defaults(func=cmd_images_update)

    # images delete
    p = images_sub.add_parser('delete', help='Delete an image')
    p.add_argument('id', type=int, help='Image ID')
    p.add_argument('--force', '-f', action='store_true', help='Skip confirmation')
    p.set_defaults(func=cmd_images_delete)

    # images search
    p = images_sub.add_parser('search', help='Search images')
    p.add_argument('query', help='Search query')
    p.set_defaults(func=cmd_images_search)

    # ---- SECTIONS ----
    sections_parser = subparsers.add_parser('sections', help='Manage sections')
    sections_sub = sections_parser.add_subparsers(dest='subcommand')

    # sections list
    p = sections_sub.add_parser('list', help='List all sections')
    p.add_argument('--format', choices=['table', 'json'], default='table')
    p.set_defaults(func=cmd_sections_list)

    # sections create
    p = sections_sub.add_parser('create', help='Create a section')
    p.add_argument('name', help='Section name')
    p.add_argument('--identifier', help='URL identifier')
    p.add_argument('--description', help='Description')
    p.add_argument('--sort-order', type=int, help='Sort order')
    p.set_defaults(func=cmd_sections_create)

    # sections show
    p = sections_sub.add_parser('show', help='Show section details')
    p.add_argument('identifier', help='Section identifier')
    p.set_defaults(func=cmd_sections_show)

    # sections delete
    p = sections_sub.add_parser('delete', help='Delete a section')
    p.add_argument('identifier', help='Section identifier')
    p.add_argument('--force', '-f', action='store_true', help='Skip confirmation')
    p.set_defaults(func=cmd_sections_delete)

    # ---- EXPORT ----
    export_parser = subparsers.add_parser('export', help='Export data')
    export_sub = export_parser.add_subparsers(dest='subcommand')

    # export date
    p = export_sub.add_parser('date', help='Export images for a date')
    p.add_argument('date', help='Date (YYYY-MM-DD)')
    p.add_argument('--output', '-o', help='Output file')
    p.set_defaults(func=cmd_export_date)

    # export section
    p = export_sub.add_parser('section', help='Export images in a section')
    p.add_argument('section', help='Section identifier')
    p.add_argument('--format', choices=['json', 'html'], default='json')
    p.add_argument('--output', '-o', help='Output file')
    p.set_defaults(func=cmd_export_section)

    # ---- STATS ----
    stats_parser = subparsers.add_parser('stats', help='View statistics')
    stats_sub = stats_parser.add_subparsers(dest='subcommand')

    # stats overview
    p = stats_sub.add_parser('overview', help='Overview statistics')
    p.set_defaults(func=cmd_stats_overview)

    # Parse and execute
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if not hasattr(args, 'func'):
        if args.command == 'images':
            images_parser.print_help()
        elif args.command == 'sections':
            sections_parser.print_help()
        elif args.command == 'export':
            export_parser.print_help()
        elif args.command == 'stats':
            stats_parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()
