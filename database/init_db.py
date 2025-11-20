#!/usr/bin/env python3
"""
Database initialization script for HastingTX Music.
Creates the database and sets up tables from schema.sql.
"""
import sys
import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config


def create_database():
    """Create the database if it doesn't exist."""
    print(f"Checking if database '{config.DB_NAME}' exists...")

    # Connect to PostgreSQL server (default 'postgres' database)
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database='postgres',
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        conn.autocommit = True

        with conn.cursor() as cur:
            # Check if database exists
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (config.DB_NAME,)
            )
            exists = cur.fetchone()

            if exists:
                print(f"Database '{config.DB_NAME}' already exists.")
            else:
                # Create database
                cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(config.DB_NAME)
                    )
                )
                print(f"Database '{config.DB_NAME}' created successfully.")

        conn.close()
        return True

    except Exception as e:
        print(f"Error creating database: {e}")
        return False


def init_schema():
    """Initialize database schema from schema.sql."""
    print("Initializing database schema...")

    schema_file = os.path.join(
        os.path.dirname(__file__),
        'schema.sql'
    )

    if not os.path.exists(schema_file):
        print(f"Error: Schema file not found: {schema_file}")
        return False

    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )

        with open(schema_file, 'r') as f:
            schema_sql = f.read()

        with conn.cursor() as cur:
            cur.execute(schema_sql)

        conn.commit()
        conn.close()

        print("Database schema initialized successfully.")
        return True

    except Exception as e:
        print(f"Error initializing schema: {e}")
        return False


def main():
    """Main initialization function."""
    print("=" * 60)
    print("HastingTX Music - Database Initialization")
    print("=" * 60)
    print()

    # Load environment variables
    load_dotenv()

    print(f"Database Host: {config.DB_HOST}")
    print(f"Database Port: {config.DB_PORT}")
    print(f"Database Name: {config.DB_NAME}")
    print(f"Database User: {config.DB_USER}")
    print()

    # Create database
    if not create_database():
        print("\nDatabase creation failed. Exiting.")
        sys.exit(1)

    print()

    # Initialize schema
    if not init_schema():
        print("\nSchema initialization failed. Exiting.")
        sys.exit(1)

    print()
    print("=" * 60)
    print("Database initialization complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Copy .env.example to .env and configure settings")
    print("2. Run: python app.py")
    print("3. Visit: http://localhost:5000")
    print()


if __name__ == '__main__':
    main()
