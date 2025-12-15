"""
Devotional Models for HastingTX
"Pull The Thread" - Daily Devotional Series
"""

from db import db
import secrets
from datetime import datetime, date, timedelta


class DevotionalThread:
    """Model for devotional threads (series)"""

    @staticmethod
    def create(identifier, title, description=None, author=None, cover_image=None,
               total_days=1, is_published=False, series=None, series_position=None):
        """Create a new devotional thread"""
        query = """
            INSERT INTO devotional_threads
            (identifier, title, description, author, cover_image, total_days, is_published, series, series_position)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        result = db.insert(query, (identifier, title, description, author, cover_image,
                                   total_days, is_published, series, series_position))
        return result['id'] if result else None

    @staticmethod
    def get_by_id(thread_id):
        """Get thread by ID"""
        query = """
            SELECT id, identifier, title, description, author, cover_image,
                   total_days, is_published, series, series_position, created_at, updated_at
            FROM devotional_threads WHERE id = %s
        """
        return db.execute_one(query, (thread_id,))

    @staticmethod
    def get_by_identifier(identifier):
        """Get thread by URL identifier"""
        query = """
            SELECT id, identifier, title, description, author, cover_image,
                   total_days, is_published, series, series_position, created_at, updated_at
            FROM devotional_threads WHERE identifier = %s
        """
        return db.execute_one(query, (identifier,))

    @staticmethod
    def get_all(published_only=False, search=None, reverse=False):
        """
        Get all threads with smart ordering.

        Ordering logic:
        - Series threads grouped together, ordered by series_position
        - Standalone threads (no series) ordered by created_at
        - reverse=True flips the order within each group

        Args:
            published_only: Only return published threads
            search: Search term for title/description
            reverse: Reverse the sort order
        """
        # Build WHERE clause
        conditions = []
        params = []

        if published_only:
            conditions.append("is_published = TRUE")

        if search:
            conditions.append("(title ILIKE %s OR description ILIKE %s)")
            search_term = f"%{search}%"
            params.extend([search_term, search_term])

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # Order direction
        series_dir = "DESC" if reverse else "ASC"
        date_dir = "ASC" if reverse else "DESC"

        query = f"""
            SELECT id, identifier, title, description, author, cover_image,
                   total_days, is_published, series, series_position, created_at, updated_at
            FROM devotional_threads
            {where_clause}
            ORDER BY
                CASE WHEN series IS NULL THEN 1 ELSE 0 END,
                series,
                series_position {series_dir},
                created_at {date_dir}
        """
        return db.execute(query, params if params else None)

    @staticmethod
    def get_series_list():
        """Get distinct series names"""
        query = """
            SELECT DISTINCT series FROM devotional_threads
            WHERE series IS NOT NULL
            ORDER BY series
        """
        results = db.execute(query)
        return [r['series'] for r in results] if results else []

    @staticmethod
    def update(thread_id, **kwargs):
        """Update thread fields"""
        allowed_fields = ['identifier', 'title', 'description', 'author',
                          'cover_image', 'total_days', 'is_published', 'series', 'series_position']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
        set_clause += ', updated_at = CURRENT_TIMESTAMP'
        values = list(updates.values()) + [thread_id]
        query = f"UPDATE devotional_threads SET {set_clause} WHERE id = %s"
        db.execute(query, values, fetch=False)
        return True

    @staticmethod
    def delete(thread_id):
        """Delete a thread and all its devotionals"""
        query = "DELETE FROM devotional_threads WHERE id = %s"
        db.execute(query, (thread_id,), fetch=False)
        return True

    @staticmethod
    def get_devotionals(thread_id):
        """Get all devotionals for a thread"""
        return Devotional.get_by_thread(thread_id)

    @staticmethod
    def count_devotionals(thread_id):
        """Count devotionals in a thread"""
        query = "SELECT COUNT(*) as count FROM devotionals WHERE thread_id = %s"
        result = db.execute_one(query, (thread_id,))
        return result['count'] if result else 0


class Devotional:
    """Model for individual devotionals (days within a thread)"""

    @staticmethod
    def create(thread_id, day_number, title, content, scripture_reference=None,
               scripture_text=None, reflection_questions=None, prayer=None,
               audio_filename=None, audio_duration=None):
        """Create a new devotional"""
        query = """
            INSERT INTO devotionals
            (thread_id, day_number, title, content, scripture_reference,
             scripture_text, reflection_questions, prayer, audio_filename, audio_duration)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        result = db.insert(query, (thread_id, day_number, title, content, scripture_reference,
                                   scripture_text, reflection_questions, prayer, audio_filename, audio_duration))
        return result['id'] if result else None

    @staticmethod
    def get_by_id(devotional_id):
        """Get devotional by ID"""
        query = """
            SELECT d.id, d.thread_id, d.day_number, d.title, d.scripture_reference,
                   d.scripture_text, d.content, d.reflection_questions, d.prayer,
                   d.audio_filename, d.audio_duration, d.created_at, d.updated_at,
                   t.identifier as thread_identifier, t.title as thread_title, t.total_days
            FROM devotionals d
            JOIN devotional_threads t ON d.thread_id = t.id
            WHERE d.id = %s
        """
        return db.execute_one(query, (devotional_id,))

    @staticmethod
    def get_by_thread_and_day(thread_id, day_number):
        """Get devotional by thread and day number"""
        query = """
            SELECT d.id, d.thread_id, d.day_number, d.title, d.scripture_reference,
                   d.scripture_text, d.content, d.reflection_questions, d.prayer,
                   d.audio_filename, d.audio_duration, d.created_at, d.updated_at,
                   t.identifier as thread_identifier, t.title as thread_title, t.total_days
            FROM devotionals d
            JOIN devotional_threads t ON d.thread_id = t.id
            WHERE d.thread_id = %s AND d.day_number = %s
        """
        return db.execute_one(query, (thread_id, day_number))

    @staticmethod
    def get_by_thread(thread_id):
        """Get all devotionals for a thread"""
        query = """
            SELECT id, thread_id, day_number, title, scripture_reference,
                   scripture_text, content, reflection_questions, prayer,
                   audio_filename, audio_duration, created_at, updated_at
            FROM devotionals WHERE thread_id = %s ORDER BY day_number
        """
        return db.execute(query, (thread_id,))

    @staticmethod
    def update(devotional_id, **kwargs):
        """Update devotional fields"""
        allowed_fields = ['day_number', 'title', 'content', 'scripture_reference',
                          'scripture_text', 'reflection_questions', 'prayer',
                          'audio_filename', 'audio_duration']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
        set_clause += ', updated_at = CURRENT_TIMESTAMP'
        values = list(updates.values()) + [devotional_id]
        query = f"UPDATE devotionals SET {set_clause} WHERE id = %s"
        db.execute(query, values, fetch=False)
        return True

    @staticmethod
    def delete(devotional_id):
        """Delete a devotional"""
        query = "DELETE FROM devotionals WHERE id = %s"
        db.execute(query, (devotional_id,), fetch=False)
        return True


class DevotionalProgress:
    """Model for tracking user progress through threads"""

    @staticmethod
    def get_or_create(thread_id, user_identifier):
        """Get existing progress or create new"""
        # Try to get existing
        query = """
            SELECT id, thread_id, user_identifier, current_day, completed_days,
                   started_at, last_activity
            FROM devotional_progress
            WHERE thread_id = %s AND user_identifier = %s
        """
        existing = db.execute_one(query, (thread_id, user_identifier))
        if existing:
            # Convert completed_days to list if needed
            result = dict(existing)
            result['completed_days'] = result['completed_days'] or []
            return result

        # Create new
        insert_query = """
            INSERT INTO devotional_progress (thread_id, user_identifier, current_day, completed_days)
            VALUES (%s, %s, 1, '{}')
            RETURNING *
        """
        new_row = db.insert(insert_query, (thread_id, user_identifier))
        if new_row:
            result = dict(new_row)
            result['completed_days'] = []
            return result
        return None

    @staticmethod
    def get(thread_id, user_identifier):
        """Get progress without creating"""
        query = """
            SELECT id, thread_id, user_identifier, current_day, completed_days,
                   started_at, last_activity
            FROM devotional_progress
            WHERE thread_id = %s AND user_identifier = %s
        """
        result = db.execute_one(query, (thread_id, user_identifier))
        if result:
            result = dict(result)
            result['completed_days'] = result['completed_days'] or []
        return result

    @staticmethod
    def mark_day_complete(thread_id, user_identifier, day_number):
        """Mark a day as complete and advance to next"""
        # Get thread total days
        thread_query = "SELECT total_days FROM devotional_threads WHERE id = %s"
        thread = db.execute_one(thread_query, (thread_id,))
        total_days = thread['total_days']

        # Update progress - add day to completed_days if not already there
        next_day = min(day_number + 1, total_days)
        update_query = """
            UPDATE devotional_progress
            SET completed_days = CASE
                    WHEN %s = ANY(completed_days) THEN completed_days
                    ELSE array_append(completed_days, %s)
                END,
                current_day = %s,
                last_activity = CURRENT_TIMESTAMP
            WHERE thread_id = %s AND user_identifier = %s
        """
        db.execute(update_query, (day_number, day_number, next_day, thread_id, user_identifier), fetch=False)
        return next_day

    @staticmethod
    def is_day_accessible(thread_id, user_identifier, day_number):
        """Check if user can access a specific day"""
        if day_number == 1:
            return True

        progress = DevotionalProgress.get(thread_id, user_identifier)
        if not progress:
            return day_number == 1

        # Can access if previous day is completed
        return (day_number - 1) in (progress['completed_days'] or [])

    @staticmethod
    def is_thread_complete(thread_id, user_identifier):
        """Check if user has completed all days"""
        query = """
            SELECT p.completed_days, t.total_days
            FROM devotional_progress p
            JOIN devotional_threads t ON p.thread_id = t.id
            WHERE p.thread_id = %s AND p.user_identifier = %s
        """
        result = db.execute_one(query, (thread_id, user_identifier))
        if result:
            completed = result['completed_days'] or []
            total = result['total_days']
            return len(completed) >= total
        return False


class DevotionalSubscriber:
    """Model for email subscribers"""

    @staticmethod
    def create(email, name=None, receive_new_threads=True, user_identifier=None):
        """Create a new subscriber"""
        unsubscribe_token = secrets.token_urlsafe(32)
        query = """
            INSERT INTO devotional_subscribers
            (email, name, receive_new_threads, unsubscribe_token, user_identifier)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                name = COALESCE(EXCLUDED.name, devotional_subscribers.name),
                user_identifier = COALESCE(EXCLUDED.user_identifier, devotional_subscribers.user_identifier),
                is_active = TRUE
            RETURNING id, unsubscribe_token, user_identifier
        """
        result = db.insert(query, (email, name, receive_new_threads, unsubscribe_token, user_identifier))
        return {'id': result['id'], 'unsubscribe_token': result['unsubscribe_token'], 'user_identifier': result['user_identifier']} if result else None

    @staticmethod
    def get_by_email(email):
        """Get subscriber by email"""
        query = """
            SELECT id, email, name, is_active, receive_new_threads,
                   unsubscribe_token, user_identifier, last_sync_email_sent, subscribed_at
            FROM devotional_subscribers WHERE email = %s
        """
        return db.execute_one(query, (email,))

    @staticmethod
    def get_by_token(token):
        """Get subscriber by unsubscribe token"""
        query = """
            SELECT id, email, name, is_active, receive_new_threads,
                   unsubscribe_token, user_identifier, last_sync_email_sent, subscribed_at
            FROM devotional_subscribers WHERE unsubscribe_token = %s
        """
        return db.execute_one(query, (token,))

    @staticmethod
    def get_by_user_identifier(user_identifier):
        """Get subscriber by user identifier"""
        query = """
            SELECT id, email, name, is_active, receive_new_threads,
                   unsubscribe_token, user_identifier, last_sync_email_sent, subscribed_at
            FROM devotional_subscribers WHERE user_identifier = %s
        """
        return db.execute_one(query, (user_identifier,))

    @staticmethod
    def unsubscribe(token):
        """Unsubscribe by token"""
        query = """
            UPDATE devotional_subscribers SET is_active = FALSE
            WHERE unsubscribe_token = %s
        """
        db.execute(query, (token,), fetch=False)
        return True

    @staticmethod
    def get_all_active():
        """Get all active subscribers"""
        query = """
            SELECT id, email, name, is_active, receive_new_threads,
                   unsubscribe_token, user_identifier, last_sync_email_sent, subscribed_at
            FROM devotional_subscribers WHERE is_active = TRUE
            ORDER BY subscribed_at DESC
        """
        return db.execute(query)

    @staticmethod
    def can_send_sync_email(email, minutes=15):
        """Check if we can send a sync email (rate limiting)"""
        query = """
            SELECT last_sync_email_sent
            FROM devotional_subscribers
            WHERE email = %s
              AND last_sync_email_sent > NOW() - INTERVAL '%s minutes'
        """
        result = db.execute_one(query, (email, minutes))
        return result is None  # Can send if no recent email

    @staticmethod
    def update_sync_email_sent(email):
        """Update the last sync email sent timestamp"""
        query = """
            UPDATE devotional_subscribers
            SET last_sync_email_sent = NOW()
            WHERE email = %s
        """
        db.execute(query, (email,), fetch=False)

    @staticmethod
    def link_user_identifier(email, user_identifier):
        """Link a user_identifier to a subscriber"""
        query = """
            UPDATE devotional_subscribers
            SET user_identifier = %s
            WHERE email = %s
        """
        db.execute(query, (user_identifier, email), fetch=False)


class DevotionalEnrollment:
    """Model for email drip enrollments"""

    @staticmethod
    def create(subscriber_id, thread_id, start_date=None):
        """Create a new enrollment"""
        next_send = start_date or (date.today() + timedelta(days=1))
        query = """
            INSERT INTO devotional_enrollments
            (subscriber_id, thread_id, current_day, next_send_date)
            VALUES (%s, %s, 1, %s)
            ON CONFLICT (subscriber_id, thread_id) DO NOTHING
            RETURNING id
        """
        result = db.insert(query, (subscriber_id, thread_id, next_send))
        return result['id'] if result else None

    @staticmethod
    def get_due_today():
        """Get all enrollments due to send today"""
        query = """
            SELECT e.id, e.subscriber_id, e.thread_id, e.current_day, e.next_send_date,
                   s.email, s.name, s.unsubscribe_token,
                   t.title as thread_title, t.total_days
            FROM devotional_enrollments e
            JOIN devotional_subscribers s ON e.subscriber_id = s.id
            JOIN devotional_threads t ON e.thread_id = t.id
            WHERE e.next_send_date <= CURRENT_DATE
              AND e.is_complete = FALSE
              AND s.is_active = TRUE
            ORDER BY e.next_send_date
        """
        return db.execute(query)

    @staticmethod
    def advance_day(enrollment_id):
        """Advance to next day or mark complete"""
        # Get current state
        query = """
            SELECT e.current_day, t.total_days
            FROM devotional_enrollments e
            JOIN devotional_threads t ON e.thread_id = t.id
            WHERE e.id = %s
        """
        result = db.execute_one(query, (enrollment_id,))
        if not result:
            return False

        current_day, total_days = result['current_day'], result['total_days']

        if current_day >= total_days:
            # Mark complete
            update_query = """
                UPDATE devotional_enrollments
                SET is_complete = TRUE, next_send_date = NULL
                WHERE id = %s
            """
            db.execute(update_query, (enrollment_id,), fetch=False)
        else:
            # Advance to next day
            update_query = """
                UPDATE devotional_enrollments
                SET current_day = current_day + 1,
                    next_send_date = CURRENT_DATE + INTERVAL '1 day'
                WHERE id = %s
            """
            db.execute(update_query, (enrollment_id,), fetch=False)

        return True

    @staticmethod
    def get_by_subscriber_and_thread(subscriber_id, thread_id):
        """Get enrollment for a subscriber and thread"""
        query = """
            SELECT id, subscriber_id, thread_id, current_day, next_send_date,
                   is_complete, enrolled_at
            FROM devotional_enrollments
            WHERE subscriber_id = %s AND thread_id = %s
        """
        return db.execute_one(query, (subscriber_id, thread_id))
