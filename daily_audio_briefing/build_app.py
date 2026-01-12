#!/usr/bin/env python3
"""
Build script for Daily Audio Briefing desktop application.

This script helps build the application for macOS, Windows, and Linux.

Usage:
    python build_app.py              # Build for current platform
    python build_app.py --clean      # Clean build artifacts first
    python build_app.py --install    # Install dependencies first

Requirements:
    pip install pyinstaller

Note: FFmpeg must be installed separately on the target system:
    - macOS:   brew install ffmpeg
    - Windows: choco install ffmpeg  (or download from ffmpeg.org)
    - Linux:   sudo apt install ffmpeg
"""

import subprocess
import sys
import os
import shutil
import platform

# Script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SPEC_FILE = os.path.join(SCRIPT_DIR, "DailyAudioBriefing.spec")
DIST_DIR = os.path.join(SCRIPT_DIR, "dist")
BUILD_DIR = os.path.join(SCRIPT_DIR, "build")


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    if result.returncode != 0:
        print(f"\nError: {description} failed with code {result.returncode}")
        sys.exit(1)
    return result


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        return False


def install_dependencies():
    """Install required dependencies for building."""
    print("\nInstalling build dependencies...")

    # Install PyInstaller
    run_command(
        [sys.executable, "-m", "pip", "install", "pyinstaller"],
        "Installing PyInstaller"
    )

    # Install app dependencies
    requirements_file = os.path.join(SCRIPT_DIR, "requirements-desktop.txt")
    if os.path.exists(requirements_file):
        run_command(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file],
            "Installing application dependencies"
        )
    else:
        print(f"Warning: {requirements_file} not found")


def clean_build():
    """Remove build artifacts."""
    print("\nCleaning build artifacts...")

    for dir_path in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(dir_path):
            print(f"  Removing {dir_path}")
            shutil.rmtree(dir_path)

    # Remove __pycache__ directories
    for root, dirs, files in os.walk(SCRIPT_DIR):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                pycache_path = os.path.join(root, dir_name)
                print(f"  Removing {pycache_path}")
                shutil.rmtree(pycache_path)

    print("Clean complete.")


def build_app():
    """Build the application using PyInstaller."""
    if not check_pyinstaller():
        print("PyInstaller not found. Installing...")
        install_dependencies()

    # Check for spec file
    if not os.path.exists(SPEC_FILE):
        print(f"Error: Spec file not found: {SPEC_FILE}")
        sys.exit(1)

    # Check for required data files
    required_files = ["voices.bin", "channels.txt", "sources.json"]
    missing_files = []
    for f in required_files:
        if not os.path.exists(os.path.join(SCRIPT_DIR, f)):
            missing_files.append(f)

    if missing_files:
        print(f"Warning: Missing data files: {missing_files}")
        print("The build may fail or the app may not work correctly.")

    # Run PyInstaller
    run_command(
        [sys.executable, "-m", "PyInstaller", SPEC_FILE, "--noconfirm"],
        f"Building application for {platform.system()}"
    )

    # Report results
    print("\n" + "="*60)
    print("  BUILD COMPLETE")
    print("="*60)

    system = platform.system()
    if system == "Darwin":
        app_path = os.path.join(DIST_DIR, "Daily Audio Briefing.app")
        if os.path.exists(app_path):
            print(f"\nmacOS app bundle created at:")
            print(f"  {app_path}")
            print(f"\nTo run: open '{app_path}'")
            print(f"\nTo distribute: Create a DMG or zip the .app bundle")
    elif system == "Windows":
        exe_path = os.path.join(DIST_DIR, "DailyAudioBriefing.exe")
        if os.path.exists(exe_path):
            print(f"\nWindows executable created at:")
            print(f"  {exe_path}")
            print(f"\nTo run: Double-click the .exe file")
    else:
        exe_path = os.path.join(DIST_DIR, "daily-audio-briefing")
        if os.path.exists(exe_path):
            print(f"\nLinux executable created at:")
            print(f"  {exe_path}")
            print(f"\nTo run: ./daily-audio-briefing")

    print("\nIMPORTANT: Users must have FFmpeg installed on their system.")
    print("  macOS:   brew install ffmpeg")
    print("  Windows: choco install ffmpeg")
    print("  Linux:   sudo apt install ffmpeg")


def main():
    """Main entry point."""
    print("Daily Audio Briefing - Build Script")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Python: {sys.version}")

    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    if "--clean" in args:
        clean_build()
        if len(args) == 1:
            sys.exit(0)

    if "--install" in args:
        install_dependencies()
        if len(args) == 1:
            sys.exit(0)

    build_app()


if __name__ == "__main__":
    main()
