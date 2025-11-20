"""Database connection and query helpers."""
import psycopg2
from psycopg2.extras import RealDictCursor
from config import config


class Database:
    """Database connection manager."""

    def __init__(self):
        self.conn = None

    def connect(self):
        """Establish database connection."""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
        return self.conn

    def close(self):
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()

    def execute(self, query, params=None, fetch=True):
        """
        Execute a query and return results.

        Args:
            query: SQL query string
            params: Query parameters (tuple or dict)
            fetch: Whether to fetch results (False for INSERT/UPDATE/DELETE)

        Returns:
            List of dict rows if fetch=True, otherwise None
        """
        conn = self.connect()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()
            conn.commit()
            return None

    def execute_one(self, query, params=None):
        """Execute a query and return a single row."""
        conn = self.connect()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def insert(self, query, params=None, returning=True):
        """
        Execute an INSERT query.

        Args:
            query: SQL INSERT query
            params: Query parameters
            returning: Whether to return the inserted row (expects RETURNING clause)

        Returns:
            Inserted row dict if returning=True, otherwise None
        """
        conn = self.connect()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            result = cur.fetchone() if returning else None
            conn.commit()
            return result


# Global database instance
db = Database()
