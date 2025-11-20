#!/bin/bash
# Production deployment script for HastingTX Music

set -e

SUDO_PASSWORD="!QAZ2wsx#EDC"

echo "================================================"
echo "HastingTX Music - Production Deployment"
echo "================================================"
echo

cd /home/richard/projects/hastingtx/music

# 1. Create log directory
echo "Step 1: Creating log directory..."
echo "$SUDO_PASSWORD" | sudo -S mkdir -p /var/log/hastingtx-music
echo "$SUDO_PASSWORD" | sudo -S chown richard:richard /var/log/hastingtx-music
echo "✓ Log directory created"
echo

# 2. Install systemd service
echo "Step 2: Installing systemd service..."
echo "$SUDO_PASSWORD" | sudo -S cp hastingtx-music.service /etc/systemd/system/
echo "$SUDO_PASSWORD" | sudo -S systemctl daemon-reload
echo "✓ Service installed"
echo

# 3. Install Nginx configuration
echo "Step 3: Installing Nginx configuration..."
echo "$SUDO_PASSWORD" | sudo -S cp hastingtx-music.nginx /etc/nginx/sites-available/hastingtx-music

# Create symlink if it doesn't exist
if [ ! -L /etc/nginx/sites-enabled/hastingtx-music ]; then
    echo "$SUDO_PASSWORD" | sudo -S ln -s /etc/nginx/sites-available/hastingtx-music /etc/nginx/sites-enabled/
    echo "✓ Nginx site enabled"
else
    echo "✓ Nginx site already enabled"
fi

# Test Nginx configuration
echo "Testing Nginx configuration..."
echo "$SUDO_PASSWORD" | sudo -S nginx -t
echo "✓ Nginx configuration valid"
echo

# 4. Set proper permissions
echo "Step 4: Setting permissions..."
chmod 755 /home/richard/projects/hastingtx/music/static
chmod 755 /home/richard/projects/hastingtx/music/static/uploads
echo "✓ Permissions set"
echo

# 5. Enable and start the service
echo "Step 5: Starting HastingTX Music service..."
echo "$SUDO_PASSWORD" | sudo -S systemctl enable hastingtx-music
echo "$SUDO_PASSWORD" | sudo -S systemctl restart hastingtx-music
sleep 2
echo "✓ Service started"
echo

# 6. Reload Nginx
echo "Step 6: Reloading Nginx..."
echo "$SUDO_PASSWORD" | sudo -S systemctl reload nginx
echo "✓ Nginx reloaded"
echo

# 7. Check status
echo "Step 7: Checking service status..."
echo "$SUDO_PASSWORD" | sudo -S systemctl status hastingtx-music --no-pager -l | head -20
echo

echo "================================================"
echo "Deployment Complete!"
echo "================================================"
echo
echo "Service Status:"
echo "  • systemctl status hastingtx-music"
echo
echo "Logs:"
echo "  • Application: /var/log/hastingtx-music/error.log"
echo "  • Access: /var/log/hastingtx-music/access.log"
echo "  • Nginx: /var/log/nginx/hastingtx-music-*.log"
echo
echo "Service Control:"
echo "  • Restart: sudo systemctl restart hastingtx-music"
echo "  • Stop: sudo systemctl stop hastingtx-music"
echo "  • Logs: sudo journalctl -u hastingtx-music -f"
echo
echo "Access URLs:"
echo "  • http://hastingtx.org/music/playlist/all"
echo "  • http://hastingtx.org/admin/upload"
echo

touch deploy.complete
