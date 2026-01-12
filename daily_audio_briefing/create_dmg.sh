#!/bin/bash
#
# Create a professional DMG installer for Daily Audio Briefing
#
# This creates a DMG with:
# - App icon on the left
# - Applications folder shortcut on the right
# - Clean, professional appearance
#

set -e

APP_NAME="Daily Audio Briefing"
DMG_NAME="DailyAudioBriefing"
VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="$SCRIPT_DIR/dist"
APP_PATH="$DIST_DIR/$APP_NAME.app"
DMG_PATH="$DIST_DIR/${DMG_NAME}-${VERSION}-macOS.dmg"

echo "=============================================="
echo "  Creating DMG Installer"
echo "=============================================="
echo ""

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: App not found at $APP_PATH"
    echo "Run 'python3 build_app.py' first to build the app."
    exit 1
fi

# Remove old DMG if exists
if [ -f "$DMG_PATH" ]; then
    echo "Removing old DMG..."
    rm -f "$DMG_PATH"
fi

echo "Creating DMG from: $APP_PATH"
echo "Output: $DMG_PATH"
echo ""

# Create the DMG with create-dmg
# This creates a professional installer with:
# - Custom window size
# - App positioned on left
# - Applications symlink on right
# - Icon size optimized for visibility

create-dmg \
    --volname "$APP_NAME" \
    --volicon "$APP_PATH/Contents/Resources/AppIcon.icns" 2>/dev/null || true

# Try with simpler options if no icon exists
create-dmg \
    --volname "$APP_NAME" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "$APP_NAME.app" 150 185 \
    --hide-extension "$APP_NAME.app" \
    --app-drop-link 450 185 \
    --no-internet-enable \
    "$DMG_PATH" \
    "$APP_PATH"

echo ""
echo "=============================================="
echo "  DMG Created Successfully!"
echo "=============================================="
echo ""
echo "Output: $DMG_PATH"
echo "Size: $(du -h "$DMG_PATH" | cut -f1)"
echo ""
echo "To test: open '$DMG_PATH'"
echo ""
