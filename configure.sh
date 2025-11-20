#!/bin/bash
# Complete configuration script for HastingTX Music

set -e

echo "================================================"
echo "HastingTX Music - Complete Configuration"
echo "================================================"
echo

cd /home/richard/projects/hastingtx/music

# 1. Create virtual environment
echo "Step 1: Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo

# 2. Install Python dependencies
echo "Step 2: Installing Python dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed"
else
    echo "✗ Error installing dependencies"
    exit 1
fi
echo

# 3. Create upload directory
echo "Step 3: Creating upload directory..."
mkdir -p static/uploads
chmod 755 static/uploads
echo "✓ Upload directory ready"
echo

# 4. Configuration file
echo "Step 4: Configuration file..."
if [ -f ".env" ]; then
    echo "✓ .env file exists"
else
    echo "✗ .env file missing (should have been created)"
    exit 1
fi
echo

# 5. Database setup
echo "Step 5: Setting up PostgreSQL database..."
echo "This requires sudo access to configure PostgreSQL."
read -p "Continue with database setup? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ./setup_db.sh
    echo "✓ Database configured"
else
    echo "⚠ Skipped database setup - you'll need to run ./setup_db.sh later"
fi
echo

# 6. Test configuration
echo "Step 6: Testing configuration..."
./venv/bin/python -c "
from config import config
print(f'  Database: {config.DB_NAME}')
print(f'  Upload folder: {config.UPLOAD_FOLDER}')
print(f'  Admin IPs: {config.ADMIN_IP_WHITELIST}')
print('✓ Configuration loaded successfully')
"
echo

echo "================================================"
echo "Configuration Complete!"
echo "================================================"
echo
echo "Your HastingTX Music application is configured:"
echo
echo "  • Virtual environment: venv/"
echo "  • Python dependencies: Installed"
echo "  • Upload directory: static/uploads/"
echo "  • Database: hastingtx_music"
echo "  • Admin IP whitelist: 192.168.0.0/24"
echo
echo "Next steps:"
echo "  1. Activate venv: source venv/bin/activate"
echo "  2. Start the app: python app.py"
echo "     OR directly: ./venv/bin/python app.py"
echo "  3. Visit: http://localhost:5000"
echo "  4. Admin panel: http://localhost:5000/admin"
echo
echo "For production deployment, see README.md"
echo

touch configure.complete
