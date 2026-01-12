# Runtime hook to fix Tk console/menu issues on macOS
# and ensure system tools like ffmpeg are accessible
# This must run before tkinter is imported

import os
import sys

if sys.platform == 'darwin':
    # Disable Tk console window which causes menu crashes
    os.environ['TK_SILENCE_DEPRECATION'] = '1'

    # Add common tool paths to PATH so ffmpeg etc. can be found
    # Homebrew paths for both Intel and Apple Silicon Macs
    extra_paths = [
        '/opt/homebrew/bin',      # Apple Silicon Homebrew
        '/usr/local/bin',         # Intel Homebrew / MacPorts
        '/usr/bin',
        '/bin',
    ]
    current_path = os.environ.get('PATH', '')
    for p in extra_paths:
        if os.path.exists(p) and p not in current_path:
            current_path = p + ':' + current_path
    os.environ['PATH'] = current_path

    # Ensure proper Tcl/Tk library paths in frozen app
    if getattr(sys, 'frozen', False):
        bundle_dir = os.path.dirname(sys.executable)
        # For .app bundles, go up to Frameworks
        if bundle_dir.endswith('MacOS'):
            frameworks_dir = os.path.join(os.path.dirname(bundle_dir), 'Frameworks')
            if os.path.exists(frameworks_dir):
                tcl_lib = os.path.join(frameworks_dir, 'tcl8.6')
                tk_lib = os.path.join(frameworks_dir, 'tk8.6')
                if os.path.exists(tcl_lib):
                    os.environ['TCL_LIBRARY'] = tcl_lib
                if os.path.exists(tk_lib):
                    os.environ['TK_LIBRARY'] = tk_lib

elif sys.platform == 'win32':
    # Windows: Add common tool paths
    extra_paths = [
        r'C:\Program Files\ffmpeg\bin',
        r'C:\ffmpeg\bin',
        os.path.expandvars(r'%LOCALAPPDATA%\Programs\ffmpeg\bin'),
    ]
    current_path = os.environ.get('PATH', '')
    for p in extra_paths:
        if os.path.exists(p) and p not in current_path:
            current_path = p + ';' + current_path
    os.environ['PATH'] = current_path
