#!/bin/bash
# HastingTX Music - Setup Script

echo "================================================"
echo "HastingTX Music - Initial Setup"
echo "================================================"
echo

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "Error: Please run this script from the music directory"
    exit 1
fi

# 1. Install Python dependencies
echo "Step 1: Installing Python dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error installing dependencies"
    exit 1
fi
echo "✓ Dependencies installed"
echo

# 2. Set up environment file
if [ ! -f ".env" ]; then
    echo "Step 2: Creating .env file..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo
    echo "IMPORTANT: Edit .env and configure:"
    echo "  - DB_PASSWORD (PostgreSQL password)"
    echo "  - SECRET_KEY (generate with: python -c 'import secrets; print(secrets.token_hex(32))')"
    echo "  - ADMIN_IP_WHITELIST (add your home IP addresses)"
    echo
    read -p "Press Enter after you've edited .env..."
else
    echo "Step 2: .env file already exists, skipping..."
    echo
fi

# 3. Create upload directory
echo "Step 3: Creating upload directory..."
mkdir -p static/uploads
chmod 755 static/uploads
echo "✓ Upload directory created"
echo

# 4. Initialize database
echo "Step 4: Initializing PostgreSQL database..."
echo "This will create the 'hastingtx_music' database and tables."
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python database/init_db.py
    if [ $? -ne 0 ]; then
        echo "Error initializing database"
        exit 1
    fi
    echo "✓ Database initialized"
else
    echo "Skipped database initialization"
fi
echo

# 5. Done!
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo
echo "Next steps:"
echo "1. Start the development server: python app.py"
echo "2. Visit: http://localhost:5000"
echo "3. Access admin: http://localhost:5000/admin (from whitelisted IP)"
echo
echo "For production deployment, see README.md for:"
echo "  - Gunicorn setup"
echo "  - Nginx configuration"
echo "  - Systemd service"
echo

touch runme.complete
