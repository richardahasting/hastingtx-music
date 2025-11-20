#!/bin/bash
# Database setup script for HastingTX Music

set -e

SUDO_PASSWORD="!QAZ2wsx#EDC"

echo "Setting up PostgreSQL database..."
echo

# Check if richard user exists
if echo "$SUDO_PASSWORD" | sudo -S -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename = 'richard'" 2>/dev/null | grep -q 1; then
    echo "✓ PostgreSQL user 'richard' exists"
else
    echo "Creating PostgreSQL user 'richard'..."
    echo "$SUDO_PASSWORD" | sudo -S -u postgres psql -c "CREATE USER richard WITH PASSWORD '!QAZ2wsx#EDC';" 2>/dev/null
    echo "✓ PostgreSQL user 'richard' created"
fi
echo

# Check if database exists
if echo "$SUDO_PASSWORD" | sudo -S -u postgres psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw hastingtx_music; then
    echo "⚠ Database 'hastingtx_music' already exists"
    echo "  To recreate, manually run:"
    echo "  sudo -u postgres psql -c 'DROP DATABASE hastingtx_music;'"
    echo "  Then run this script again"
else
    echo "Creating database 'hastingtx_music'..."
    echo "$SUDO_PASSWORD" | sudo -S -u postgres psql -c "CREATE DATABASE hastingtx_music OWNER richard;" 2>/dev/null
    echo "✓ Database created"
fi
echo

# Grant privileges
echo "$SUDO_PASSWORD" | sudo -S -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE hastingtx_music TO richard;" 2>/dev/null
echo "✓ Privileges granted"
echo

# Initialize schema
echo "Initializing database schema..."
PGPASSWORD='!QAZ2wsx#EDC' psql -U richard -d hastingtx_music -f database/schema.sql 2>/dev/null
echo "✓ Schema initialized"
echo

echo "================================================"
echo "Database setup complete!"
echo "================================================"
echo
echo "Database: hastingtx_music"
echo "User: richard"
echo "Tables: songs, playlists, playlist_songs, ratings"
echo

touch setup_db.complete
