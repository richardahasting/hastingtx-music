"""Data models and database operations for gallery sections and images."""
from db import db


class GallerySection:
    """Gallery section (chapter) model and database operations."""

    @staticmethod
    def get_all(order_by='sort_order, name'):
        """Get all sections ordered by sort_order then name."""
        query = f"SELECT * FROM gallery_sections ORDER BY {order_by}"
        return db.execute(query)

    @staticmethod
    def get_by_id(section_id):
        """Get a section by its ID."""
        query = "SELECT * FROM gallery_sections WHERE id = %s"
        return db.execute_one(query, (section_id,))

    @staticmethod
    def get_by_identifier(identifier):
        """Get a section by its identifier."""
        query = "SELECT * FROM gallery_sections WHERE identifier = %s"
        return db.execute_one(query, (identifier,))

    @staticmethod
    def create(identifier, name, description=None, sort_order=0):
        """Create a new section."""
        query = """
            INSERT INTO gallery_sections (identifier, name, description, sort_order)
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
    def update(section_id, **kwargs):
        """Update section fields."""
        if not kwargs:
            return None

        set_clause = ', '.join([f"{key} = %({key})s" for key in kwargs.keys()])
        query = f"UPDATE gallery_sections SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = %(id)s RETURNING *"
        kwargs['id'] = section_id
        return db.insert(query, kwargs)

    @staticmethod
    def delete(section_id):
        """Delete a section (images will have section_id set to NULL)."""
        query = "DELETE FROM gallery_sections WHERE id = %s"
        db.execute(query, (section_id,), fetch=False)

    @staticmethod
    def get_image_count(section_id):
        """Get the number of images in a section."""
        query = "SELECT COUNT(*)::integer as count FROM gallery_images WHERE section_id = %s"
        result = db.execute_one(query, (section_id,))
        return result['count'] if result else 0

    @staticmethod
    def get_with_counts():
        """Get all sections with their image counts."""
        query = """
            SELECT s.*, COUNT(i.id)::integer as image_count
            FROM gallery_sections s
            LEFT JOIN gallery_images i ON s.id = i.section_id
            GROUP BY s.id
            ORDER BY s.sort_order, s.name
        """
        return db.execute(query)


class GalleryImage:
    """Gallery image model and database operations."""

    @staticmethod
    def create(identifier, title, filename, file_type, file_size=None,
               description=None, significance_date=None, source=None,
               thumbnail=None, width=None, height=None, section_id=None,
               sort_order=0):
        """Create a new image record."""
        query = """
            INSERT INTO gallery_images (
                identifier, title, filename, file_type, file_size,
                description, significance_date, source, thumbnail,
                width, height, section_id, sort_order
            )
            VALUES (
                %(identifier)s, %(title)s, %(filename)s, %(file_type)s, %(file_size)s,
                %(description)s, %(significance_date)s, %(source)s, %(thumbnail)s,
                %(width)s, %(height)s, %(section_id)s, %(sort_order)s
            )
            RETURNING *
        """
        params = {
            'identifier': identifier,
            'title': title,
            'filename': filename,
            'file_type': file_type,
            'file_size': file_size,
            'description': description,
            'significance_date': significance_date,
            'source': source,
            'thumbnail': thumbnail,
            'width': width,
            'height': height,
            'section_id': section_id,
            'sort_order': sort_order
        }
        return db.insert(query, params)

    @staticmethod
    def get_by_id(image_id):
        """Get an image by its ID."""
        query = "SELECT * FROM gallery_images WHERE id = %s"
        return db.execute_one(query, (image_id,))

    @staticmethod
    def get_by_identifier(identifier):
        """Get an image by its identifier."""
        query = "SELECT * FROM gallery_images WHERE identifier = %s"
        return db.execute_one(query, (identifier,))

    @staticmethod
    def get_all(order_by='significance_date DESC NULLS LAST, upload_date DESC', limit=None, offset=0):
        """Get all images with optional ordering and pagination."""
        query = f"SELECT * FROM gallery_images ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        return db.execute(query)

    @staticmethod
    def get_by_section(section_id, order_by='sort_order, significance_date'):
        """Get all images in a section."""
        query = f"""
            SELECT * FROM gallery_images
            WHERE section_id = %s
            ORDER BY {order_by}
        """
        return db.execute(query, (section_id,))

    @staticmethod
    def get_by_date(date):
        """Get all images for a specific significance date."""
        query = """
            SELECT * FROM gallery_images
            WHERE significance_date = %s
            ORDER BY sort_order, title
        """
        return db.execute(query, (date,))

    @staticmethod
    def get_by_date_range(start_date, end_date):
        """Get all images within a date range."""
        query = """
            SELECT * FROM gallery_images
            WHERE significance_date >= %s AND significance_date <= %s
            ORDER BY significance_date, sort_order, title
        """
        return db.execute(query, (start_date, end_date))

    @staticmethod
    def get_dates_with_images():
        """Get all unique dates that have images."""
        query = """
            SELECT DISTINCT significance_date, COUNT(*)::integer as image_count
            FROM gallery_images
            WHERE significance_date IS NOT NULL
            GROUP BY significance_date
            ORDER BY significance_date
        """
        return db.execute(query)

    @staticmethod
    def update(image_id, **kwargs):
        """Update image fields."""
        if not kwargs:
            return None

        set_clause = ', '.join([f"{key} = %({key})s" for key in kwargs.keys()])
        query = f"UPDATE gallery_images SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = %(id)s RETURNING *"
        kwargs['id'] = image_id
        return db.insert(query, kwargs)

    @staticmethod
    def delete(image_id):
        """Delete an image."""
        query = "DELETE FROM gallery_images WHERE id = %s"
        db.execute(query, (image_id,), fetch=False)

    @staticmethod
    def search(search_term):
        """Search images by title, description, or source."""
        query = """
            SELECT * FROM gallery_images
            WHERE title ILIKE %(term)s
               OR description ILIKE %(term)s
               OR source ILIKE %(term)s
            ORDER BY significance_date DESC NULLS LAST, title
        """
        return db.execute(query, {'term': f'%{search_term}%'})

    @staticmethod
    def increment_view_count(image_id):
        """Increment the view count for an image."""
        query = "UPDATE gallery_images SET view_count = view_count + 1 WHERE id = %s"
        db.execute(query, (image_id,), fetch=False)

    @staticmethod
    def get_count():
        """Get total number of images."""
        query = "SELECT COUNT(*)::integer as count FROM gallery_images"
        result = db.execute_one(query)
        return result['count'] if result else 0

    @staticmethod
    def get_recent(limit=10):
        """Get most recently uploaded images."""
        query = """
            SELECT * FROM gallery_images
            ORDER BY upload_date DESC
            LIMIT %s
        """
        return db.execute(query, (limit,))

    @staticmethod
    def get_with_section():
        """Get all images with their section information."""
        query = """
            SELECT i.*, s.name as section_name, s.identifier as section_identifier
            FROM gallery_images i
            LEFT JOIN gallery_sections s ON i.section_id = s.id
            ORDER BY i.significance_date DESC NULLS LAST, i.upload_date DESC
        """
        return db.execute(query)

    @staticmethod
    def move_to_section(image_id, section_id):
        """Move an image to a different section."""
        return GalleryImage.update(image_id, section_id=section_id)

    @staticmethod
    def get_navigation(image_id, section_id=None):
        """
        Get previous and next images for navigation.
        If section_id is provided, navigate within section.
        Otherwise navigate by date/upload order.
        """
        image = GalleryImage.get_by_id(image_id)
        if not image:
            return None, None

        if section_id:
            # Navigate within section
            prev_query = """
                SELECT * FROM gallery_images
                WHERE section_id = %s AND (sort_order < %s OR (sort_order = %s AND id < %s))
                ORDER BY sort_order DESC, id DESC
                LIMIT 1
            """
            next_query = """
                SELECT * FROM gallery_images
                WHERE section_id = %s AND (sort_order > %s OR (sort_order = %s AND id > %s))
                ORDER BY sort_order, id
                LIMIT 1
            """
            prev_img = db.execute_one(prev_query, (section_id, image['sort_order'], image['sort_order'], image_id))
            next_img = db.execute_one(next_query, (section_id, image['sort_order'], image['sort_order'], image_id))
        else:
            # Navigate by date
            prev_query = """
                SELECT * FROM gallery_images
                WHERE (significance_date > %s OR (significance_date = %s AND id < %s))
                   OR (significance_date IS NULL AND %s IS NOT NULL)
                ORDER BY significance_date NULLS LAST, id DESC
                LIMIT 1
            """
            next_query = """
                SELECT * FROM gallery_images
                WHERE (significance_date < %s OR (significance_date = %s AND id > %s))
                   OR (%s IS NULL AND significance_date IS NOT NULL)
                ORDER BY significance_date DESC NULLS LAST, id
                LIMIT 1
            """
            sig_date = image['significance_date']
            prev_img = db.execute_one(prev_query, (sig_date, sig_date, image_id, sig_date))
            next_img = db.execute_one(next_query, (sig_date, sig_date, image_id, sig_date))

        return prev_img, next_img
