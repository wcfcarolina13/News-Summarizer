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
        # For .app bundles, MacOS/ is inside Contents/, Frameworks/ is a sibling
        if bundle_dir.endswith('MacOS'):
            frameworks_dir = os.path.join(os.path.dirname(bundle_dir), 'Frameworks')
            if os.path.exists(frameworks_dir):
                # PyInstaller 6.x uses _tcl_data/_tk_data; older versions use tcl8.6/tk8.6
                for tcl_name in ('_tcl_data', 'tcl8.6'):
                    tcl_lib = os.path.join(frameworks_dir, tcl_name)
                    if os.path.exists(tcl_lib) and 'TCL_LIBRARY' not in os.environ:
                        os.environ['TCL_LIBRARY'] = tcl_lib
                        break
                for tk_name in ('_tk_data', 'tk8.6'):
                    tk_lib = os.path.join(frameworks_dir, tk_name)
                    if os.path.exists(tk_lib) and 'TK_LIBRARY' not in os.environ:
                        os.environ['TK_LIBRARY'] = tk_lib
                        break

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
