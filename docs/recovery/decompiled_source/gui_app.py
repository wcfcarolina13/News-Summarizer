# Source Generated with Decompyle++
# File: gui_app.pyc (Python 3.12)

import customtkinter as ctk
import subprocess
import threading
import os
import sys
import glob
import datetime
import json
import shutil
from urllib.parse import urlparse, parse_qs
from tkinter.filedialog import filedialog
import qrcode
from PIL import Image

def get_data_directory():
    '''Get the appropriate data directory for storing output files.

    When running as a frozen app (PyInstaller), uses Application Support.
    When running in development, uses the script directory.
    '''
    if getattr(sys, 'frozen', False):
        if sys.platform == 'darwin':
            data_dir = os.path.expanduser('~/Library/Application Support/Daily Audio Briefing')
        elif sys.platform == 'win32':
            data_dir = os.path.join(os.environ.get('APPDATA', ''), 'Daily Audio Briefing')
        else:
            data_dir = os.path.expanduser('~/.daily-audio-briefing')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok = True)
        return data_dir
    return None.path.dirname(os.path.abspath(__file__))


def get_resource_path(filename):
    """Get the path to a bundled resource file.

    When running as a PyInstaller bundle, resources are in sys._MEIPASS.
    When running normally, they're in the same directory as this script.
    """
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, filename)
    return None.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def parse_briefing_url(url_string = None):
    """Parse a dailybriefing:// URL into action parameters.

    Supported URLs:
        dailybriefing://connect?server=https://example.onrender.com

    Returns dict with 'action' and action-specific keys, or empty dict if invalid.
    """
    parsed = urlparse(url_string)
    if parsed.scheme != 'dailybriefing':
        return { }
    if not None.netloc:
        None.netloc
        if not parsed.hostname:
            parsed.hostname
    action = ''
    params = parse_qs(parsed.query, keep_blank_values = False)
    result = {
        'action': action }
    for key, values in params.items():
        result[key] = values[0] if len(values) == 1 else values
    return result
# WARNING: Decompyle incomplete

from podcast_manager import PodcastServer
from file_manager import FileManager
from audio_generator import AudioGenerator
from voice_manager import VoiceManager
from convert_to_mp3 import check_ffmpeg
from data_csv_processor import DataCSVProcessor, ExtractionConfig, load_custom_instructions
from transcription_service import get_transcription_service, get_transcription_status, is_transcription_available, transcribe_audio as service_transcribe_audio, get_license_manager, TranscriptionBackend
from transcriber import check_ffmpeg
from tkcalendar import DateEntry
APP_VERSION = '1.0.0-alpha'
_ffmpeg_cache = None

def _cached_check_ffmpeg():
    '''Return cached result of check_ffmpeg() to avoid repeated subprocess calls.'''
    pass
# WARNING: Decompyle incomplete

threading.Thread(target = _cached_check_ffmpeg, daemon = True).start()
ctk.set_appearance_mode('Dark')
ctk.set_default_color_theme('blue')
COLORS = {
    'bg_primary': '#0f0f0f',
    'bg_secondary': '#1a1a1a',
    'bg_tertiary': '#252525',
    'accent': '#4a9eff',
    'accent_hover': '#3a8eef',
    'success': '#2ecc71',
    'warning': '#f39c12',
    'danger': '#e74c3c',
    'border': '#333333',
    'text_primary': '#ffffff',
    'text_secondary': '#aaaaaa',
    'text_muted': '#666666' }
NAV_PAGES = [
    ('home', '🏠  Home'),
    ('summarize', '📰  Summarize'),
    ('extract', '📊  Extract'),
    ('audio', '🔊  Audio'),
    ('scheduler', '📅  Scheduler'),
    ('settings', '⚙️  Settings'),
    ('guide', '📖  Guide')]

class ToolTip:
    '''
    Tooltip class for CustomTkinter widgets.
    Shows a tooltip after hovering for a specified delay (default 1.2 seconds).
    '''
    
    def __init__(self, widget, text, delay = (1200,)):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.schedule_id = None
        widget.bind('<Enter>', self._on_enter)
        widget.bind('<Leave>', self._on_leave)
        widget.bind('<Button-1>', self._on_leave)

    
    def _on_enter(self, event = (None,)):
        '''Schedule tooltip to appear after delay.'''
        self._cancel_schedule()
        self.schedule_id = self.widget.after(self.delay, self._show_tooltip)

    
    def _on_leave(self, event = (None,)):
        '''Cancel scheduled tooltip and hide if visible.'''
        self._cancel_schedule()
        self._hide_tooltip()

    
    def _cancel_schedule(self):
        '''Cancel any pending tooltip display.'''
        if self.schedule_id:
            self.widget.after_cancel(self.schedule_id)
            self.schedule_id = None
            return None

    
    def _show_tooltip(self):
        '''Display the tooltip window.'''
        if self.tooltip_window:
            return None
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f'''+{x}+{y}''')
        tw.attributes('-topmost', True)
        label = ctk.CTkLabel(tw, text = self.text, fg_color = ('gray85', 'gray25'), corner_radius = 6, padx = 10, pady = 6, font = ctk.CTkFont(size = 12), wraplength = 300)
        label.pack()

    
    def _hide_tooltip(self):
        '''Hide the tooltip window.'''
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
            return None



def add_tooltip(widget, text, delay = (1200,)):
    '''Helper function to add a tooltip to any widget.'''
    return ToolTip(widget, text, delay)


class AudioBriefingApp(ctk.CTk):
    pass
# WARNING: Decompyle incomplete

if __name__ == '__main__':
    if sys.platform == 'darwin' and getattr(sys, 'frozen', False):
        from Foundation import NSBundle
        bundle = NSBundle.mainBundle()
        if not bundle.localizedInfoDictionary():
            bundle.localizedInfoDictionary()
        info = bundle.infoDictionary()
        if not info and info.get('LSUIElement'):
            pass
        from AppKit import NSApplication
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    launch_url = None
    for arg in sys.argv[1:]:
        if not arg.startswith('dailybriefing://'):
            continue
        launch_url = arg
        sys.argv[1:]
    app = AudioBriefingApp(launch_url = launch_url)
    app.mainloop()
    return None
return None
# WARNING: Decompyle incomplete
