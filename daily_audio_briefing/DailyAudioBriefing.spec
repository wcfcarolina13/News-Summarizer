# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Daily Audio Briefing
Cross-platform build: macOS, Windows, Linux

Build commands:
  macOS:   pyinstaller DailyAudioBriefing.spec
  Windows: pyinstaller DailyAudioBriefing.spec
  Linux:   pyinstaller DailyAudioBriefing.spec

The output will be in the 'dist' folder.
"""

import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

# Get the directory containing this spec file
spec_dir = os.path.dirname(os.path.abspath(SPEC))

# Collect all customtkinter data (themes, images)
customtkinter_datas, customtkinter_binaries, customtkinter_hiddenimports = collect_all('customtkinter')

# Collect tkcalendar if available
try:
    tkcalendar_datas, tkcalendar_binaries, tkcalendar_hiddenimports = collect_all('tkcalendar')
except:
    tkcalendar_datas = []
    tkcalendar_binaries = []
    tkcalendar_hiddenimports = []

# Collect PIL/Pillow
pillow_datas, pillow_binaries, pillow_hiddenimports = collect_all('PIL')

# Data files to include
datas = [
    # Voice model files
    (os.path.join(spec_dir, 'voices.bin'), '.'),
    # Channel list
    (os.path.join(spec_dir, 'channels.txt'), '.'),
    # Sources configuration
    (os.path.join(spec_dir, 'sources.json'), '.'),
    # Extraction instruction templates
    (os.path.join(spec_dir, 'extraction_instructions'), 'extraction_instructions'),
]

# Add collected data files
datas += customtkinter_datas
datas += tkcalendar_datas
datas += pillow_datas

# Hidden imports that PyInstaller might miss
hiddenimports = [
    # Core modules
    'customtkinter',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'qrcode',
    'qrcode.image.pil',

    # Audio
    'numpy',
    'soundfile',
    'kokoro_onnx',

    # Web/Data
    'requests',
    'bs4',
    'lxml',
    'lxml.etree',
    'lxml.html',
    'dateparser',
    'dotenv',

    # YouTube
    'youtube_transcript_api',
    'scrapetube',
    'yt_dlp',

    # Google APIs
    'google.generativeai',
    'google.auth',
    'google.oauth2',
    'googleapiclient',
    'googleapiclient.discovery',

    # TTS
    'gtts',

    # Standard library often missed
    'tkinter',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.ttk',
    'json',
    'csv',
    'threading',
    'subprocess',
    'shutil',
    'glob',
    'datetime',
    'hashlib',
    'uuid',
    're',
]

hiddenimports += customtkinter_hiddenimports
hiddenimports += tkcalendar_hiddenimports
hiddenimports += pillow_hiddenimports

# Binary files (platform-specific)
binaries = []
binaries += customtkinter_binaries
binaries += tkcalendar_binaries
binaries += pillow_binaries

# Analysis
a = Analysis(
    ['gui_app.py'],
    pathex=[spec_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(spec_dir, 'hook-tk-fix.py')],
    excludes=[
        # Exclude heavy optional dependencies
        'faster_whisper',  # Large transcription library
        'torch',           # Not needed for base app
        'tensorflow',      # Not needed
        'matplotlib',      # Not needed for GUI
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Platform-specific settings
if sys.platform == 'darwin':
    # macOS: Create .app bundle
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Daily Audio Briefing',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,  # No terminal window
        disable_windowed_traceback=False,
        argv_emulation=False,  # Disabled - causes Tk menu crashes on macOS
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Daily Audio Briefing',
    )

    app = BUNDLE(
        coll,
        name='Daily Audio Briefing.app',
        icon=None,  # Add icon path here if you have one: 'icon.icns'
        bundle_identifier='com.dailyaudiobriefing.app',
        info_plist={
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSRequiresAquaSystemAppearance': False,  # Support dark mode
        },
    )

elif sys.platform == 'win32':
    # Windows: Create single .exe
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='DailyAudioBriefing',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,  # No console window
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,  # Add icon path here if you have one: 'icon.ico'
    )

else:
    # Linux: Create executable
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='daily-audio-briefing',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
