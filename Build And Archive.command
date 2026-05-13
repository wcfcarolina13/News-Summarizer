#!/bin/bash
# Daily Audio Briefing — Build & Archive helper
#
# Run this after a code change to rebuild the .app while preserving the
# currently-installed .app as a revert-able archive.
#
# Safety guarantees:
#   - NEVER deletes anything in the project tree
#   - NEVER modifies the currently-installed .app in /Applications (or wherever
#     it lives) — it is only COPIED to an archive folder
#   - Outputs the new .app to dist/Daily Audio Briefing.app, leaving install
#     decisions up to the user
#   - Safe to run while the dev gui_app.py is also running — PyInstaller only
#     reads source files and writes to its own dist/build subdirs
#
# Usage:
#   Double-click this file in Finder, OR run: bash "Build And Archive.command"

set -euo pipefail

# ---------- 1. Resolve project paths ----------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/daily_audio_briefing"
BUILD_LOG="$SCRIPT_DIR/build_$(date +%Y%m%d_%H%M%S).log"
ARCHIVE_ROOT="$SCRIPT_DIR/_archive"

cd "$SCRIPT_DIR"

echo "==========================================================" | tee "$BUILD_LOG"
echo " Daily Audio Briefing — Build & Archive"                    | tee -a "$BUILD_LOG"
echo " $(date)"                                                   | tee -a "$BUILD_LOG"
echo "==========================================================" | tee -a "$BUILD_LOG"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "ERROR: Project dir not found at $PROJECT_DIR" | tee -a "$BUILD_LOG"
    read -n 1 -s -p "Press any key to close..."
    exit 1
fi

# ---------- 2. Locate the currently-installed .app via Spotlight ----------
echo "" | tee -a "$BUILD_LOG"
echo "[1/4] Locating currently-installed Daily Audio Briefing.app..." | tee -a "$BUILD_LOG"

# mdfind queries macOS Spotlight metadata (fast, no full disk scan)
INSTALLED_APP="$(mdfind 'kMDItemCFBundleIdentifier == "com.dailyaudiobriefing.app"' 2>/dev/null | head -n 1 || true)"

# Fallback if Spotlight returns nothing — check common paths
if [ -z "$INSTALLED_APP" ]; then
    for candidate in \
        "/Applications/Daily Audio Briefing.app" \
        "$HOME/Applications/Daily Audio Briefing.app" \
        "$HOME/Desktop/Daily Audio Briefing.app" \
        "$HOME/Downloads/Daily Audio Briefing.app"
    do
        if [ -d "$candidate" ]; then
            INSTALLED_APP="$candidate"
            break
        fi
    done
fi

if [ -z "$INSTALLED_APP" ] || [ ! -d "$INSTALLED_APP" ]; then
    echo "  WARNING: No currently-installed Daily Audio Briefing.app found." | tee -a "$BUILD_LOG"
    echo "           Spotlight returned nothing and the common paths were empty." | tee -a "$BUILD_LOG"
    echo "           If you have the app somewhere unusual, archive it manually" | tee -a "$BUILD_LOG"
    echo "           BEFORE replacing it with the new build." | tee -a "$BUILD_LOG"
    INSTALLED_APP=""
else
    echo "  Found at: $INSTALLED_APP" | tee -a "$BUILD_LOG"
fi

# ---------- 3. Archive the currently-installed .app (COPY, not move) ----------
echo "" | tee -a "$BUILD_LOG"
echo "[2/4] Archiving the existing .app..." | tee -a "$BUILD_LOG"

if [ -n "$INSTALLED_APP" ]; then
    TIMESTAMP="$(date +%Y-%m-%d_%H%M%S)"
    ARCHIVE_DIR="$ARCHIVE_ROOT/$TIMESTAMP"
    mkdir -p "$ARCHIVE_DIR"

    # Use ditto for proper macOS bundle copies (preserves resource forks,
    # extended attributes, codesign metadata). Falls back to cp -R if ditto
    # is not available (it always is on macOS).
    if command -v ditto >/dev/null 2>&1; then
        ditto "$INSTALLED_APP" "$ARCHIVE_DIR/Daily Audio Briefing.app"
    else
        cp -R "$INSTALLED_APP" "$ARCHIVE_DIR/Daily Audio Briefing.app"
    fi

    # Drop a small note alongside the archive describing what it is
    cat > "$ARCHIVE_DIR/README.txt" <<EOF
Daily Audio Briefing — pre-rebuild archive
Captured: $(date)
Source path: $INSTALLED_APP

This is a verbatim copy of the installed .app at the time of the rebuild.
To revert, delete the post-rebuild .app at "$INSTALLED_APP" and copy this one
back into place (or just double-click this archived copy to verify it still
works before reverting).
EOF

    echo "  Archived to: $ARCHIVE_DIR/Daily Audio Briefing.app" | tee -a "$BUILD_LOG"
else
    echo "  Skipping archive — no installed .app located." | tee -a "$BUILD_LOG"
fi

# ---------- 4. Verify PyInstaller is available (do not auto-install) ----------
echo "" | tee -a "$BUILD_LOG"
echo "[3/4] Checking PyInstaller availability..." | tee -a "$BUILD_LOG"

PYINSTALLER_OK=0
if python3 -c "import PyInstaller" 2>/dev/null; then
    PYINSTALLER_VERSION="$(python3 -c 'import PyInstaller; print(PyInstaller.__version__)')"
    echo "  PyInstaller $PYINSTALLER_VERSION is installed." | tee -a "$BUILD_LOG"
    PYINSTALLER_OK=1
else
    echo "  PyInstaller is NOT installed in your default python3 environment." | tee -a "$BUILD_LOG"
    echo "  To install: pip3 install pyinstaller" | tee -a "$BUILD_LOG"
    echo "  Aborting build (your installed .app and your archive remain intact)." | tee -a "$BUILD_LOG"
fi

# ---------- 5. Run the build ----------
if [ "$PYINSTALLER_OK" -eq 1 ]; then
    echo "" | tee -a "$BUILD_LOG"
    echo "[4/4] Running PyInstaller build..." | tee -a "$BUILD_LOG"
    echo "  (this typically takes 5–15 minutes; output streamed below)" | tee -a "$BUILD_LOG"
    echo "" | tee -a "$BUILD_LOG"

    cd "$PROJECT_DIR"
    if python3 build_app.py 2>&1 | tee -a "$BUILD_LOG"; then
        NEW_APP="$PROJECT_DIR/dist/Daily Audio Briefing.app"
        echo "" | tee -a "$BUILD_LOG"
        if [ -d "$NEW_APP" ]; then
            echo "==========================================================" | tee -a "$BUILD_LOG"
            echo " BUILD SUCCEEDED"                                            | tee -a "$BUILD_LOG"
            echo "==========================================================" | tee -a "$BUILD_LOG"
            echo " New .app:    $NEW_APP"                                      | tee -a "$BUILD_LOG"
            if [ -n "$INSTALLED_APP" ]; then
                echo " Archived:    $ARCHIVE_DIR/Daily Audio Briefing.app"     | tee -a "$BUILD_LOG"
                echo " Old in use:  $INSTALLED_APP  (untouched)"               | tee -a "$BUILD_LOG"
            fi
            echo ""                                                            | tee -a "$BUILD_LOG"
            echo " To install the new build:"                                  | tee -a "$BUILD_LOG"
            echo "   1. Quit any running Daily Audio Briefing.app"             | tee -a "$BUILD_LOG"
            echo "   2. Stop the daemon:"                                      | tee -a "$BUILD_LOG"
            echo "        cd \"$PROJECT_DIR\" && python3 scheduler_daemon.py stop"   | tee -a "$BUILD_LOG"
            echo "   3. Drag the new .app over the old one in Finder, OR run:" | tee -a "$BUILD_LOG"
            if [ -n "$INSTALLED_APP" ]; then
                echo "        ditto \"$NEW_APP\" \"$INSTALLED_APP\""           | tee -a "$BUILD_LOG"
            fi
            echo "   4. Re-launch the .app and re-start the daemon."           | tee -a "$BUILD_LOG"
            echo ""                                                            | tee -a "$BUILD_LOG"
            echo " Note: scheduled_tasks.json lives in"                        | tee -a "$BUILD_LOG"
            echo "   ~/Library/Application Support/Daily Audio Briefing/"      | tee -a "$BUILD_LOG"
            echo " and is shared between old/new builds — no duplicate tasks." | tee -a "$BUILD_LOG"
        else
            echo "BUILD COMMAND RAN but no .app was found at $NEW_APP" | tee -a "$BUILD_LOG"
            echo "Check the log at: $BUILD_LOG" | tee -a "$BUILD_LOG"
        fi
    else
        echo "" | tee -a "$BUILD_LOG"
        echo "BUILD FAILED — see log: $BUILD_LOG" | tee -a "$BUILD_LOG"
        echo "Your installed .app and archive are intact; nothing was destroyed." | tee -a "$BUILD_LOG"
    fi
fi

echo ""
echo "Full log: $BUILD_LOG"
echo ""
read -n 1 -s -p "Press any key to close this window..."
echo ""
