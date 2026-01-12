# Runtime hook to fix Tk console/menu issues on macOS
# This must run before tkinter is imported

import os
import sys

if sys.platform == 'darwin':
    # Disable Tk console window which causes menu crashes
    os.environ['TK_SILENCE_DEPRECATION'] = '1'

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
