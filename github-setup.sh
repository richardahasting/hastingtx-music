#!/bin/bash
# GitHub repository setup helper

echo "================================================"
echo "HastingTX Music - GitHub Setup"
echo "================================================"
echo
echo "Git repository initialized with initial commit!"
echo
echo "To create a GitHub repository:"
echo
echo "1. Using GitHub CLI (gh):"
echo "   gh repo create hastingtx-music --public --source=. --remote=origin"
echo "   gh repo create hastingtx-music --private --source=. --remote=origin"
echo
echo "2. Manually via web:"
echo "   a. Go to https://github.com/new"
echo "   b. Repository name: hastingtx-music"
echo "   c. Description: Music sharing platform for Richard & Claude's SUNO creations"
echo "   d. Choose Public or Private"
echo "   e. DO NOT initialize with README (we have one)"
echo "   f. Click 'Create repository'"
echo
echo "3. After creating on GitHub, connect this repo:"
echo "   git remote add origin git@github.com:YOUR_USERNAME/hastingtx-music.git"
echo "   git push -u origin main"
echo
echo "Repository stats:"
git log --oneline
echo
echo "Files ready to push:"
git ls-files | wc -l
echo " files tracked"
echo
