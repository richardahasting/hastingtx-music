#!/bin/bash
# Update Nginx configuration to integrate music app into existing hastingtx.org

set -e

SUDO_PASSWORD="!QAZ2wsx#EDC"

echo "================================================"
echo "Nginx Configuration Update"
echo "================================================"
echo
echo "This will integrate the music app into the existing"
echo "hastingtx.org Nginx configuration (with HTTPS)."
echo
echo "Changes:"
echo "  • Backup current hastingtx.org config"
echo "  • Install integrated config with music routes"
echo "  • Remove conflicting hastingtx-music config"
echo "  • Test and reload Nginx"
echo
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi
echo

# 1. Backup current config
echo "Step 1: Backing up current hastingtx.org config..."
echo "$SUDO_PASSWORD" | sudo -S cp /etc/nginx/sites-available/hastingtx.org /etc/nginx/sites-available/hastingtx.org.backup.$(date +%Y%m%d-%H%M%S)
echo "✓ Backup created"
echo

# 2. Install integrated config
echo "Step 2: Installing integrated configuration..."
echo "$SUDO_PASSWORD" | sudo -S cp hastingtx.org-integrated.nginx /etc/nginx/sites-available/hastingtx.org
echo "✓ Integrated config installed"
echo

# 3. Remove conflicting config
echo "Step 3: Removing conflicting hastingtx-music config..."
if [ -L /etc/nginx/sites-enabled/hastingtx-music ]; then
    echo "$SUDO_PASSWORD" | sudo -S rm /etc/nginx/sites-enabled/hastingtx-music
    echo "✓ Removed hastingtx-music symlink"
fi
echo

# 4. Test Nginx configuration
echo "Step 4: Testing Nginx configuration..."
echo "$SUDO_PASSWORD" | sudo -S nginx -t
if [ $? -eq 0 ]; then
    echo "✓ Nginx configuration valid"
else
    echo "✗ Nginx configuration error!"
    echo "Restoring backup..."
    echo "$SUDO_PASSWORD" | sudo -S cp /etc/nginx/sites-available/hastingtx.org.backup.* /etc/nginx/sites-available/hastingtx.org
    exit 1
fi
echo

# 5. Reload Nginx
echo "Step 5: Reloading Nginx..."
echo "$SUDO_PASSWORD" | sudo -S systemctl reload nginx
echo "✓ Nginx reloaded"
echo

echo "================================================"
echo "Nginx Update Complete!"
echo "================================================"
echo
echo "Music app is now integrated into hastingtx.org"
echo
echo "Access URLs (with HTTPS):"
echo "  • https://hastingtx.org/music/playlist/all"
echo "  • https://hastingtx.org/admin/upload"
echo
echo "Backups saved:"
echo "$SUDO_PASSWORD" | sudo -S ls -lh /etc/nginx/sites-available/hastingtx.org.backup.* 2>/dev/null | tail -3 || echo "  (check /etc/nginx/sites-available/)"
echo

touch update-nginx.complete
