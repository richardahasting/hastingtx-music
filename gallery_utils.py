"""Utility functions for gallery image handling and processing."""
import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
import io

# Supported image formats
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf'}
THUMBNAIL_SIZE = 300  # Width in pixels


def allowed_image_file(filename):
    """Check if file has an allowed image extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def get_file_extension(filename):
    """Get the lowercase file extension."""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


def generate_gallery_identifier(title):
    """
    Generate a URL-friendly identifier from a title.

    Args:
        title: Image title

    Returns:
        URL-safe identifier (e.g., "My Photo" -> "my-photo")
    """
    # Convert to lowercase and replace spaces/special chars with hyphens
    identifier = re.sub(r'[^\w\s-]', '', title.lower())
    identifier = re.sub(r'[-\s]+', '-', identifier)
    return identifier.strip('-')


def get_unique_filename(directory, filename):
    """
    Generate a unique filename in the given directory.

    Args:
        directory: Target directory
        filename: Original filename

    Returns:
        Unique filename
    """
    base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
    extension = filename.rsplit('.', 1)[1] if '.' in filename else ''

    counter = 1
    unique_filename = filename
    full_path = os.path.join(directory, unique_filename)

    while os.path.exists(full_path):
        unique_filename = f"{base_name}_{counter}.{extension}" if extension else f"{base_name}_{counter}"
        full_path = os.path.join(directory, unique_filename)
        counter += 1

    return unique_filename


def get_image_dimensions(filepath):
    """
    Get the dimensions of an image file.

    Args:
        filepath: Path to the image file

    Returns:
        Tuple of (width, height) or (None, None) if unable to determine
    """
    try:
        with Image.open(filepath) as img:
            return img.width, img.height
    except Exception as e:
        print(f"Error getting image dimensions: {e}")
        return None, None


def generate_thumbnail(source_path, thumbnail_dir, thumbnail_filename=None, max_width=THUMBNAIL_SIZE):
    """
    Generate a thumbnail for an image.

    Args:
        source_path: Path to the source image
        thumbnail_dir: Directory to save thumbnail
        thumbnail_filename: Optional custom thumbnail filename
        max_width: Maximum thumbnail width in pixels

    Returns:
        Thumbnail filename or None if failed
    """
    try:
        # Ensure thumbnail directory exists
        os.makedirs(thumbnail_dir, exist_ok=True)

        # Generate thumbnail filename if not provided
        if not thumbnail_filename:
            source_filename = os.path.basename(source_path)
            base_name = source_filename.rsplit('.', 1)[0]
            thumbnail_filename = f"{base_name}_thumb.jpg"

        thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)

        with Image.open(source_path) as img:
            # Convert to RGB if necessary (for PNG with transparency, etc.)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Calculate new dimensions maintaining aspect ratio
            ratio = max_width / img.width
            new_height = int(img.height * ratio)

            # Only resize if image is larger than max_width
            if img.width > max_width:
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Save thumbnail
            img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
            return thumbnail_filename

    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return None


def generate_pdf_preview(pdf_path, output_dir, output_filename=None):
    """
    Generate a preview image from the first page of a PDF.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save the preview image
        output_filename: Optional custom output filename

    Returns:
        Preview image filename or None if failed
    """
    try:
        # Try using pdf2image if available
        from pdf2image import convert_from_path

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Generate output filename if not provided
        if not output_filename:
            pdf_filename = os.path.basename(pdf_path)
            base_name = pdf_filename.rsplit('.', 1)[0]
            output_filename = f"{base_name}_preview.jpg"

        output_path = os.path.join(output_dir, output_filename)

        # Convert first page to image
        images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=150)

        if images:
            # Convert to RGB if necessary and save
            img = images[0]
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(output_path, 'JPEG', quality=90)
            return output_filename

    except ImportError:
        print("pdf2image not installed. PDF previews not available.")
        print("Install with: pip install pdf2image")
        print("Also requires poppler: sudo apt-get install poppler-utils")
    except Exception as e:
        print(f"Error generating PDF preview: {e}")

    return None


def process_uploaded_image(file, images_dir, thumbnails_dir):
    """
    Process an uploaded image file: save, get dimensions, generate thumbnail.

    Args:
        file: FileStorage object from Flask
        images_dir: Directory for full-size images
        thumbnails_dir: Directory for thumbnails

    Returns:
        Dict with file info or None if failed:
        {
            'filename': str,
            'thumbnail': str,
            'file_type': str,
            'file_size': int,
            'width': int,
            'height': int
        }
    """
    if not file or not allowed_image_file(file.filename):
        return None

    try:
        # Ensure directories exist
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(thumbnails_dir, exist_ok=True)

        # Secure and uniquify filename
        original_filename = secure_filename(file.filename)
        filename = get_unique_filename(images_dir, original_filename)
        file_path = os.path.join(images_dir, filename)

        # Get file extension/type
        file_type = get_file_extension(filename)

        # Save the file
        file.save(file_path)

        # Get file size
        file_size = os.path.getsize(file_path)

        # Handle PDF separately
        if file_type == 'pdf':
            # Generate preview from PDF
            preview_filename = generate_pdf_preview(file_path, images_dir)
            if preview_filename:
                preview_path = os.path.join(images_dir, preview_filename)
                width, height = get_image_dimensions(preview_path)
                # Generate thumbnail from preview
                thumbnail = generate_thumbnail(preview_path, thumbnails_dir)
            else:
                width, height = None, None
                thumbnail = None
        else:
            # Get dimensions
            width, height = get_image_dimensions(file_path)
            # Generate thumbnail
            thumbnail = generate_thumbnail(file_path, thumbnails_dir)

        return {
            'filename': filename,
            'thumbnail': thumbnail,
            'file_type': file_type,
            'file_size': file_size,
            'width': width,
            'height': height
        }

    except Exception as e:
        print(f"Error processing uploaded image: {e}")
        return None


def process_image_file(file_path, images_dir, thumbnails_dir):
    """
    Process an image file from disk (for CLI batch import).

    Args:
        file_path: Path to the source image file
        images_dir: Directory for full-size images
        thumbnails_dir: Directory for thumbnails

    Returns:
        Dict with file info or None if failed
    """
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return None

    filename = os.path.basename(file_path)
    if not allowed_image_file(filename):
        print(f"Unsupported file type: {filename}")
        return None

    try:
        # Ensure directories exist
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(thumbnails_dir, exist_ok=True)

        # Secure and uniquify filename
        safe_filename = secure_filename(filename)
        unique_filename = get_unique_filename(images_dir, safe_filename)
        dest_path = os.path.join(images_dir, unique_filename)

        # Get file extension/type
        file_type = get_file_extension(unique_filename)

        # Copy file to images directory
        import shutil
        shutil.copy2(file_path, dest_path)

        # Get file size
        file_size = os.path.getsize(dest_path)

        # Handle PDF separately
        if file_type == 'pdf':
            preview_filename = generate_pdf_preview(dest_path, images_dir)
            if preview_filename:
                preview_path = os.path.join(images_dir, preview_filename)
                width, height = get_image_dimensions(preview_path)
                thumbnail = generate_thumbnail(preview_path, thumbnails_dir)
            else:
                width, height = None, None
                thumbnail = None
        else:
            # Get dimensions
            width, height = get_image_dimensions(dest_path)
            # Generate thumbnail
            thumbnail = generate_thumbnail(dest_path, thumbnails_dir)

        return {
            'filename': unique_filename,
            'thumbnail': thumbnail,
            'file_type': file_type,
            'file_size': file_size,
            'width': width,
            'height': height
        }

    except Exception as e:
        print(f"Error processing image file: {e}")
        return None


def delete_image_files(filename, thumbnail, images_dir, thumbnails_dir):
    """
    Delete image and thumbnail files.

    Args:
        filename: Image filename
        thumbnail: Thumbnail filename
        images_dir: Directory containing full-size images
        thumbnails_dir: Directory containing thumbnails
    """
    # Delete main image
    if filename:
        image_path = os.path.join(images_dir, filename)
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as e:
                print(f"Error deleting image {filename}: {e}")

    # Delete thumbnail
    if thumbnail:
        thumb_path = os.path.join(thumbnails_dir, thumbnail)
        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except Exception as e:
                print(f"Error deleting thumbnail {thumbnail}: {e}")


def format_date_for_display(date_obj):
    """
    Format a date object for display.

    Args:
        date_obj: Date object or string

    Returns:
        Formatted date string (e.g., "February 1, 1968")
    """
    if not date_obj:
        return "Unknown date"

    if isinstance(date_obj, str):
        try:
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
        except ValueError:
            return date_obj

    return date_obj.strftime('%B %d, %Y')


def parse_date_input(date_str):
    """
    Parse various date input formats.

    Args:
        date_str: Date string in various formats

    Returns:
        Date object or None
    """
    if not date_str:
        return None

    formats = [
        '%Y-%m-%d',      # 1968-02-01
        '%m/%d/%Y',      # 02/01/1968
        '%d/%m/%Y',      # 01/02/1968
        '%B %d, %Y',     # February 1, 1968
        '%b %d, %Y',     # Feb 1, 1968
        '%Y%m%d',        # 19680201
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue

    return None
