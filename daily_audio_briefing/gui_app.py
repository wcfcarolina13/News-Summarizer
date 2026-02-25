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
import tkinter.filedialog as filedialog
import qrcode
from PIL import Image # PIL is imported by qrcode, but explicit import helps CTkImage


def get_data_directory():
    """Get the appropriate data directory for storing output files.

    When running as a frozen app (PyInstaller), uses Application Support.
    When running in development, uses the script directory.
    """
    if getattr(sys, "frozen", False):
        # Frozen app - use Application Support for persistent storage
        if sys.platform == "darwin":
            data_dir = os.path.expanduser("~/Library/Application Support/Daily Audio Briefing")
        elif sys.platform == "win32":
            data_dir = os.path.join(os.environ.get("APPDATA", ""), "Daily Audio Briefing")
        else:
            data_dir = os.path.expanduser("~/.daily-audio-briefing")

        # Create if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

        return data_dir
    else:
        # Development mode - use script directory
        return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(filename):
    """Get the path to a bundled resource file.

    When running as a PyInstaller bundle, resources are in sys._MEIPASS.
    When running normally, they're in the same directory as this script.
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        return os.path.join(sys._MEIPASS, filename)
    else:
        # Running normally - use script directory
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def parse_briefing_url(url_string: str) -> dict:
    """Parse a dailybriefing:// URL into action parameters.

    Supported URLs:
        dailybriefing://connect?server=https://example.onrender.com

    Returns dict with 'action' and action-specific keys, or empty dict if invalid.
    """
    try:
        parsed = urlparse(url_string)
        if parsed.scheme != 'dailybriefing':
            return {}
        action = parsed.netloc or parsed.hostname or ''
        params = parse_qs(parsed.query, keep_blank_values=False)
        result = {'action': action}
        for key, values in params.items():
            result[key] = values[0] if len(values) == 1 else values
        return result
    except Exception:
        return {}


from podcast_manager import PodcastServer # Import your podcast manager
from file_manager import FileManager
from audio_generator import AudioGenerator
from voice_manager import VoiceManager
from convert_to_mp3 import check_ffmpeg

# Data extraction imports
from data_csv_processor import DataCSVProcessor, ExtractionConfig, load_custom_instructions

# Transcription service (handles local and future cloud backends)
from transcription_service import (
    get_transcription_service,
    get_transcription_status,
    is_transcription_available,
    transcribe_audio as service_transcribe_audio,
    get_license_manager,
    TranscriptionBackend
)

# Legacy check functions for compression (ffmpeg)
from transcriber import check_ffmpeg
try:
    from tkcalendar import DateEntry
except Exception:
    DateEntry = None

# Google Drive sign-in and sync removed
# from drive_manager import DriveManager

# App version — displayed in sidebar and first-run wizard
APP_VERSION = "1.0.0-alpha"

# Cached ffmpeg check — subprocess is slow, only run once per session
_ffmpeg_cache = None
def _cached_check_ffmpeg():
    """Return cached result of check_ffmpeg() to avoid repeated subprocess calls."""
    global _ffmpeg_cache
    if _ffmpeg_cache is None:
        _ffmpeg_cache = check_ffmpeg()
    return _ffmpeg_cache

# Pre-warm ffmpeg cache on background thread so first Settings visit is instant
threading.Thread(target=_cached_check_ffmpeg, daemon=True).start()

# Configuration - Dark theme to match web interface
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Color tokens matching web app design
COLORS = {
    "bg_primary": "#0f0f0f",       # Main background
    "bg_secondary": "#1a1a1a",     # Cards, sidebar
    "bg_tertiary": "#252525",      # Input backgrounds, hover
    "accent": "#4a9eff",           # Primary accent (blue)
    "accent_hover": "#3a8eef",     # Hover state
    "success": "#2ecc71",          # Green
    "warning": "#f39c12",          # Orange
    "danger": "#e74c3c",           # Red
    "border": "#333333",           # Borders
    "text_primary": "#ffffff",     # Main text
    "text_secondary": "#aaaaaa",   # Secondary text
    "text_muted": "#666666",       # Muted text
}

# Navigation page definitions
NAV_PAGES = [
    ("home", "🏠  Home"),
    ("summarize", "📰  Summarize"),
    ("extract", "📊  Extract"),
    ("audio", "🔊  Audio"),
    ("scheduler", "📅  Scheduler"),
    ("settings", "⚙️  Settings"),
    ("guide", "📖  Guide"),
]


class ToolTip:
    """
    Tooltip class for CustomTkinter widgets.
    Shows a tooltip after hovering for a specified delay (default 1.2 seconds).
    """
    def __init__(self, widget, text, delay=1200):
        self.widget = widget
        self.text = text
        self.delay = delay  # milliseconds
        self.tooltip_window = None
        self.schedule_id = None

        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<Button-1>", self._on_leave)  # Hide on click

    def _on_enter(self, event=None):
        """Schedule tooltip to appear after delay."""
        self._cancel_schedule()
        self.schedule_id = self.widget.after(self.delay, self._show_tooltip)

    def _on_leave(self, event=None):
        """Cancel scheduled tooltip and hide if visible."""
        self._cancel_schedule()
        self._hide_tooltip()

    def _cancel_schedule(self):
        """Cancel any pending tooltip display."""
        if self.schedule_id:
            self.widget.after_cancel(self.schedule_id)
            self.schedule_id = None

    def _show_tooltip(self):
        """Display the tooltip window."""
        if self.tooltip_window:
            return

        # Get widget position
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        # Create tooltip window
        self.tooltip_window = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)  # Remove window decorations
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)

        # Create tooltip content
        label = ctk.CTkLabel(
            tw,
            text=self.text,
            fg_color=("gray85", "gray25"),
            corner_radius=6,
            padx=10,
            pady=6,
            font=ctk.CTkFont(size=12),
            wraplength=300
        )
        label.pack()

    def _hide_tooltip(self):
        """Hide the tooltip window."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def add_tooltip(widget, text, delay=1200):
    """Helper function to add a tooltip to any widget."""
    return ToolTip(widget, text, delay)

class AudioBriefingApp(ctk.CTk):
    def __init__(self, launch_url: str = None):
        super().__init__()
        self._pending_launch_url = launch_url

        self.title("Daily Audio Briefing")
        self.geometry("1100x900") # Wide enough for date range controls
        self.minsize(950, 650)  # Prevent shrinking below usable size

        # Main window grid - sidebar + page container
        self.grid_columnconfigure(0, weight=0)  # Sidebar fixed width
        self.grid_columnconfigure(1, weight=1)   # Page container expands
        self.grid_rowconfigure(0, weight=1)

        # Create sidebar navigation
        self._create_sidebar()

        # Create page container
        self.page_container = ctk.CTkFrame(self, fg_color=COLORS["bg_primary"], corner_radius=0)
        self.page_container.grid(row=0, column=1, sticky="nsew")
        self.page_container.grid_columnconfigure(0, weight=1)
        self.page_container.grid_rowconfigure(0, weight=1)

        # Create page frames
        self.pages = {}
        self._create_pages()

        # Backward compatibility: alias for scroll-to-widget in tutorial system
        self.main_scroll = self.pages.get("summarize")

        # Initialize managers
        self.file_manager = FileManager()
        self.selected_file_paths = []
        self.audio_generator = AudioGenerator(status_callback=self._update_status)
        self.voice_manager = VoiceManager()

        # Data extraction
        self.extracted_items = []
        self.data_processor = None  # Lazy init to avoid slow startup

        # Direct Audio cache - stores cleaned text to avoid re-processing
        # Format: {"raw_hash": hash, "cleaned_text": str}
        self._cleaned_text_cache = None

        # Unified Content Editor state
        self._editor_showing_raw = True  # True = showing raw text, False = showing cleaned
        self._raw_text_backup = ""  # Stores raw text when showing cleaned view
        self._cleaned_text_backup = ""  # Stores cleaned text when showing raw view

        # App settings
        self.settings = self._load_settings()
        self._current_text_scale = 1.0  # Initialize scale tracking

        # Push API usage limits from settings into tracker
        try:
            from api_usage_tracker import get_tracker
            get_tracker().update_limits(
                daily_max=self.settings.get("api_daily_limit", 500),
                monthly_max=self.settings.get("api_monthly_limit", 10000),
                enabled=self.settings.get("api_limits_enabled", True),
                monthly_budget_usd=self.settings.get("api_budget_usd", 0.0),
                cooldown_enabled=self.settings.get("api_cooldown_enabled", True),
            )
        except Exception:
            pass  # Tracker init failure shouldn't block app launch

        # Long-running operation flag - prevents scheduler from overwriting status
        self._long_operation_in_progress = False

        # Placeholder for status label — created in _build_summarize_page() but
        # referenced by callbacks that may fire before that page is built.
        self.label_status = None
        self.label_audio_status = None  # Audio page status (set in _build_audio_page)

        # Apply saved text scale on startup
        self._apply_text_scale()

        # self.podcast_server = PodcastServer()  # Disabled
        # self.drive_manager = None  # Google Drive features removed

        # Track which pages have been built (for deferred loading)
        self._pages_built = set()

        # ============ HOME PAGE (built immediately — visible on startup) ============
        self._build_home_page()
        self._pages_built.add("home")

        # Defer all other page construction so the window paints instantly.
        # Pages are built in priority order via after() callbacks.
        # If user navigates before a page is built, _navigate_to() triggers build on demand.
        self._deferred_build_queue = [
            ("summarize", self._build_summarize_page),
            ("audio", self._build_audio_page),
            ("extract", self._build_extract_page),
            ("scheduler", self._build_scheduler_page_widgets),
            ("settings", self._build_settings_page),
            ("guide", self._build_guide_page),
        ]
        self._schedule_deferred_builds()

    def _schedule_deferred_builds(self):
        """Schedule deferred page builds so UI renders immediately."""
        if not self._deferred_build_queue:
            # All pages built — run post-build setup
            print(f"[DEBUG] All deferred builds complete. pages_built={self._pages_built}", flush=True)
            self.after(50, self._post_build_setup)
            return

        page_id, builder = self._deferred_build_queue.pop(0)
        if page_id not in self._pages_built:
            try:
                print(f"[DEBUG] Building page: {page_id}", flush=True)
                builder()
                self._pages_built.add(page_id)
                print(f"[DEBUG] Built page: {page_id} OK", flush=True)
                # Flush geometry computation so hidden pages have correct layout
                # when later shown. Without this, CTkScrollableFrame pages built
                # while grid_remove()'d won't compute their scroll regions until
                # an explicit update_idletasks() happens (e.g. navigating to Settings).
                self.update_idletasks()
            except Exception as e:
                print(f"[DEBUG] ERROR building page {page_id}: {e}", flush=True)
                import traceback; traceback.print_exc(); sys.stdout.flush()

        # Give the event loop 100ms between page builds so the UI stays
        # responsive and paint events are processed between builds.
        self.after(100, self._schedule_deferred_builds)

    def _ensure_page_built(self, page_name: str):
        """Force-build a page if user navigates before deferred build reaches it."""
        if page_name in self._pages_built:
            return
        # Find and run the builder
        for i, (pid, builder) in enumerate(self._deferred_build_queue):
            if pid == page_name:
                print(f"[DEBUG] _ensure_page_built: force-building {page_name}", flush=True)
                builder()
                self._pages_built.add(page_name)
                self._deferred_build_queue.pop(i)
                self.update_idletasks()
                return

    def _build_summarize_page(self):
        """Build the Summarize page (deferred from __init__ for faster startup)."""
        # Page header
        self.label_header = ctk.CTkLabel(
            self.pages["summarize"],
            text="Summarize Text, Articles, and Videos",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.label_header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        # Text Area Card
        self.frame_text = ctk.CTkFrame(self.pages["summarize"], fg_color=COLORS["bg_secondary"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        self.frame_text.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.frame_text.grid_columnconfigure(0, weight=1)

        # Header with expand/collapse toggle and fetch button
        text_header = ctk.CTkFrame(self.frame_text, fg_color="transparent")
        text_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 0))
        text_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(text_header, text="Audio Content", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w")

        # Fetch Article button - for loading article content from URL
        self.btn_fetch_article = ctk.CTkButton(text_header, text="Fetch Article", width=100, fg_color="green", command=self.open_fetch_article_dialog)
        self.btn_fetch_article.grid(row=0, column=1, padx=(10, 5))

        # Settings button — navigate to Settings page
        self.btn_settings = ctk.CTkButton(text_header, text="Settings", width=70, fg_color="gray", command=lambda: self._navigate_to("settings"))
        self.btn_settings.grid(row=0, column=2, padx=(0, 5))

        # Text collapse button removed — text area is always visible on its own page

        # Text content frame (collapsible)
        self.text_content = ctk.CTkFrame(self.frame_text, fg_color="transparent")
        self.text_content.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.text_content.grid_columnconfigure(0, weight=1)
        self.text_content.grid_rowconfigure(0, weight=1)  # Allow textbox row to expand
        self.text_expanded = True  # Track expansion state

        # Textbox - 25% taller default (188px vs 150px)
        self._textbox_height = 188
        self.textbox = ctk.CTkTextbox(self.text_content, height=self._textbox_height, font=ctk.CTkFont(size=14))
        self.textbox.grid(row=0, column=0, sticky="nsew")

        # Resize handle for textbox - allows dragging to resize height
        self.textbox_resize_handle = ctk.CTkFrame(
            self.text_content,
            height=10,
            fg_color=("gray80", "gray30"),
            cursor="sb_v_double_arrow"
        )
        self.textbox_resize_handle.grid(row=1, column=0, sticky="ew", pady=(2, 0))

        # Grip icon in the center of the resize handle (three horizontal lines)
        self.resize_grip = ctk.CTkLabel(
            self.textbox_resize_handle,
            text="⋯",  # Three dots as grip indicator
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray50", "gray60"),
            cursor="sb_v_double_arrow"
        )
        self.resize_grip.place(relx=0.5, rely=0.5, anchor="center")

        # Resize drag logic
        self._resize_start_y = 0
        self._resize_start_height = 0

        def _on_resize_start(event):
            self._resize_start_y = event.y_root
            self._resize_start_height = self.textbox.winfo_height()

        def _on_resize_drag(event):
            delta = event.y_root - self._resize_start_y
            new_height = max(100, self._resize_start_height + delta)  # Minimum 100px
            self.textbox.configure(height=new_height)
            self._textbox_height = new_height

        def _on_resize_enter(event):
            self.textbox_resize_handle.configure(fg_color=("gray70", "gray40"))
            self.resize_grip.configure(text_color=("gray30", "gray80"))

        def _on_resize_leave(event):
            self.textbox_resize_handle.configure(fg_color=("gray80", "gray30"))
            self.resize_grip.configure(text_color=("gray50", "gray60"))

        self.textbox_resize_handle.bind("<Button-1>", _on_resize_start)
        self.textbox_resize_handle.bind("<B1-Motion>", _on_resize_drag)
        self.textbox_resize_handle.bind("<Enter>", _on_resize_enter)
        self.textbox_resize_handle.bind("<Leave>", _on_resize_leave)
        # Also bind the grip label so dragging on it works
        self.resize_grip.bind("<Button-1>", _on_resize_start)
        self.resize_grip.bind("<B1-Motion>", _on_resize_drag)
        self.resize_grip.bind("<Enter>", _on_resize_enter)
        self.resize_grip.bind("<Leave>", _on_resize_leave)

        # Scroll capture - prevent mouse scroll from propagating to main_scroll when over textbox
        # Use fractional scrolling for smoother feel, especially on macOS trackpads
        self._scroll_accumulator = 0.0  # Accumulate small scroll deltas for smooth scrolling

        def _on_textbox_scroll(event):
            """Handle scroll events within the textbox with smooth fractional scrolling."""
            try:
                inner_text = self.textbox._textbox

                # Get current scroll position and content info
                first_visible, last_visible = inner_text.yview()

                # Calculate scroll delta as a fraction of visible area
                if event.delta:
                    # macOS trackpad sends many small events; Windows sends fewer large ones
                    if abs(event.delta) < 10:
                        # macOS-style: small delta values (1, -1, 2, -2)
                        # Use smaller multiplier for smoother feel
                        scroll_delta = -event.delta * 0.02
                    else:
                        # Windows-style: large delta values (120, -120)
                        scroll_delta = -event.delta / 120 * 0.05
                elif event.num == 4:  # Linux scroll up
                    scroll_delta = -0.05
                elif event.num == 5:  # Linux scroll down
                    scroll_delta = 0.05
                else:
                    return "break"

                # Accumulate scroll for very small movements (trackpad momentum)
                self._scroll_accumulator += scroll_delta

                # Only apply scroll if accumulated enough (reduces jitter)
                if abs(self._scroll_accumulator) >= 0.005:
                    new_pos = first_visible + self._scroll_accumulator
                    # Clamp to valid range
                    new_pos = max(0.0, min(1.0 - (last_visible - first_visible), new_pos))
                    inner_text.yview_moveto(new_pos)
                    self._scroll_accumulator = 0.0

            except Exception as e:
                print(f"[DEBUG] Scroll error: {e}")
            return "break"  # Stop event propagation to parent

        # Store scroll handler for use in enter/leave bindings
        self._textbox_scroll_handler = _on_textbox_scroll

        # Track if mouse is over the textbox for scroll handling
        self._mouse_over_textbox = False

        def _on_textbox_enter(event):
            """When mouse enters textbox, set flag for scroll capture."""
            self._mouse_over_textbox = True

        def _on_textbox_leave(event):
            """When mouse leaves textbox, clear flag."""
            self._mouse_over_textbox = False

        # Bind enter/leave events to track mouse position
        self.textbox.bind("<Enter>", _on_textbox_enter)
        self.textbox.bind("<Leave>", _on_textbox_leave)

        # Prevent trackpad gestures from being interpreted as drag-to-select
        # This can happen when the textbox captures B1-Motion events from trackpad scrolling
        def _on_textbox_button_press(event):
            """Handle button press - only allow if intentionally clicking in textbox."""
            # Store press location to detect intentional clicks vs accidental drags
            self._textbox_press_x = event.x
            self._textbox_press_y = event.y
            self._textbox_intentional_click = True

        def _on_textbox_motion(event):
            """Prevent accidental drag-to-select from trackpad gestures."""
            # If motion is happening but we didn't have an intentional press, it might be
            # a trackpad gesture being misinterpreted - don't select text
            if not getattr(self, '_textbox_intentional_click', False):
                return "break"
            # Allow normal drag-select for intentional clicks
            return None

        def _on_textbox_button_release(event):
            """Clear the intentional click flag on release."""
            self._textbox_intentional_click = False

        # Bind to inner textbox to prevent accidental selection
        try:
            inner = self.textbox._textbox
            inner.bind("<Button-1>", _on_textbox_button_press, add="+")
            inner.bind("<ButtonRelease-1>", _on_textbox_button_release, add="+")
        except Exception:
            pass

        # Initial bindings for textbox scroll
        self.textbox.bind("<MouseWheel>", _on_textbox_scroll)
        self.textbox.bind("<Button-4>", _on_textbox_scroll)
        self.textbox.bind("<Button-5>", _on_textbox_scroll)
        try:
            self.textbox._textbox.bind("<MouseWheel>", _on_textbox_scroll)
            self.textbox._textbox.bind("<Button-4>", _on_textbox_scroll)
            self.textbox._textbox.bind("<Button-5>", _on_textbox_scroll)
        except Exception:
            pass

        # Non-textual placeholder overlay - hidden when textbox has content
        self._placeholder = ctk.CTkLabel(
            self.textbox,
            text="Paste content here, or load via Get Summaries / Upload File. URLs will be auto-detected.",
            text_color="gray"
        )
        self._placeholder.place(relx=0.02, rely=0.02, anchor="nw")
        self._placeholder_visible = True

        def _update_placeholder(event=None):
            """Update placeholder visibility based on textbox content."""
            has_text = bool(self.textbox.get("0.0", "end-1c").strip())
            if has_text and self._placeholder_visible:
                self._placeholder.place_forget()
                self._placeholder_visible = False
            elif not has_text and not self._placeholder_visible:
                self._placeholder.place(relx=0.02, rely=0.02, anchor="nw")
                self._placeholder_visible = True

        # Update placeholder on any text change, not just focus
        self.textbox.bind("<KeyRelease>", _update_placeholder)
        self.textbox.bind("<FocusIn>", _update_placeholder)
        self.textbox.bind("<FocusOut>", _update_placeholder)
        # Catch paste events (Cmd+V on macOS, Ctrl+V on Windows/Linux)
        self.textbox.bind("<<Paste>>", lambda e: self.after(10, _update_placeholder))
        self.textbox.bind("<Command-v>", lambda e: self.after(10, _update_placeholder))
        self.textbox.bind("<Control-v>", lambda e: self.after(10, _update_placeholder))
        # Also bind to the inner textbox widget for more complete coverage
        try:
            inner = self.textbox._textbox
            inner.bind("<<Paste>>", lambda e: self.after(10, _update_placeholder))
            inner.bind("<Command-v>", lambda e: self.after(10, _update_placeholder))
            inner.bind("<Control-v>", lambda e: self.after(10, _update_placeholder))
            inner.bind("<<Modified>>", lambda e: self.after(10, _update_placeholder))
        except:
            pass
        self._update_placeholder = _update_placeholder  # Store reference for external calls

        # Inline status bar (below resize handle)
        self.inline_status_frame = ctk.CTkFrame(self.text_content, fg_color="transparent")
        self.inline_status_frame.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        self.inline_status_frame.grid_columnconfigure(0, weight=1)

        self.inline_status_label = ctk.CTkLabel(
            self.inline_status_frame,
            text="",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        self.inline_status_label.grid(row=0, column=0, sticky="w")

        # View toggle button (Raw/Cleaned) - starts disabled
        self.btn_toggle_view = ctk.CTkButton(
            self.inline_status_frame,
            text="Show Cleaned",
            width=100,
            fg_color="gray",
            state="disabled",
            command=self._toggle_editor_view
        )
        self.btn_toggle_view.grid(row=0, column=1, sticky="e", padx=(10, 0))

        # URL detection banner (always visible, greyed out when no URLs detected)
        self.url_banner_frame = ctk.CTkFrame(self.text_content, fg_color=("gray85", "gray20"))
        self.url_banner_frame.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        self.url_banner_frame.grid_columnconfigure(0, weight=1)
        # Don't hide - always visible

        self.url_banner_label = ctk.CTkLabel(
            self.url_banner_frame,
            text="No articles or URLs detected",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.url_banner_label.grid(row=0, column=0, padx=10, pady=8, sticky="w")

        self.btn_fetch_urls = ctk.CTkButton(
            self.url_banner_frame,
            text="Fetch Content",
            width=110,
            fg_color="gray",
            state="disabled",
            command=self._fetch_detected_urls
        )
        self.btn_fetch_urls.grid(row=0, column=1, padx=(5, 5), pady=5)

        self.btn_ignore_urls = ctk.CTkButton(
            self.url_banner_frame,
            text="Keep as Text",
            width=100,
            fg_color="gray",
            state="disabled",
            command=self._dismiss_url_banner
        )
        self.btn_ignore_urls.grid(row=0, column=2, padx=(0, 5), pady=5)

        # Extract Data button (always visible, enabled when config-matched URLs detected)
        self.btn_extract_data = ctk.CTkButton(
            self.url_banner_frame,
            text="Extract Data",
            width=100,
            fg_color="gray",
            state="disabled",
            command=self._extract_config_urls
        )
        self.btn_extract_data.grid(row=0, column=3, padx=(0, 10), pady=5)
        # Button stays visible - greyed out as explainer of available functionality

        self._url_banner_active = False  # Track if URLs are detected
        self._current_config_urls = None  # Track config-matched URLs

        # Bind textbox changes for URL detection and placeholder
        self.textbox.bind("<KeyRelease>", self._on_textbox_change)

        self.frame_yt_api = ctk.CTkFrame(self.pages["summarize"], fg_color=COLORS["bg_secondary"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        self.frame_yt_api.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="ew")
        self.frame_yt_api.grid_columnconfigure(0, weight=0)
        self.frame_yt_api.grid_columnconfigure(1, weight=1)

        # Row 0: API Key with inline Model selection
        frame_row0 = ctk.CTkFrame(self.frame_yt_api, fg_color="transparent")
        frame_row0.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")
        frame_row0.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(frame_row0, text="API Key:").grid(row=0, column=0, padx=(0, 10), sticky="w")
        
        self.gemini_key_entry = ctk.CTkEntry(frame_row0, show="*")
        self.gemini_key_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))

        # Save API key button
        self.btn_save_key = ctk.CTkButton(
            frame_row0, text="💾", width=30,
            command=lambda: self.save_api_key(self.gemini_key_entry.get().strip())
        )
        self.btn_save_key.grid(row=0, column=2, padx=(0, 2))

        # Toggle API key visibility button
        self.btn_toggle_key = ctk.CTkButton(
            frame_row0, text="👁", width=30,
            command=self.toggle_api_key_visibility
        )
        self.btn_toggle_key.grid(row=0, column=3, padx=(0, 2))

        # API Key Manager button
        self.btn_key_manager = ctk.CTkButton(
            frame_row0, text="⚙", width=30,
            command=self.open_api_key_manager
        )
        self.btn_key_manager.grid(row=0, column=4, padx=(0, 10))

        ctk.CTkLabel(frame_row0, text="Model:").grid(row=0, column=5, padx=(0, 5), sticky="w")
        
        self.model_var = ctk.StringVar(value="gemini-2.0-flash (Fast)")
        self.model_combo = ctk.CTkComboBox(
            frame_row0,
            variable=self.model_var,
            values=["gemini-2.0-flash (Fast)", "gemini-1.5-flash (Balanced)", "gemini-1.5-pro (Best, 50/day)"],
            width=230,
            state="readonly"
        )
        self.model_combo.grid(row=0, column=6, sticky="w")

        # Row 1: Help text
        help_text = "💡 gemini-2.0-flash: 4000/min | gemini-1.5-flash: 1500/day | gemini-1.5-pro: 50/day"
        ctk.CTkLabel(self.frame_yt_api, text=help_text, font=ctk.CTkFont(size=10), text_color="gray").grid(
            row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w"
        )
        
        # Row 2: Get YouTube News & Edit Sources
        frame_row2 = ctk.CTkFrame(self.frame_yt_api, fg_color="transparent")
        frame_row2.grid(row=2, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")
        frame_row2.grid_columnconfigure(0, weight=1)
        frame_row2.grid_columnconfigure(1, weight=1)
        frame_row2.grid_columnconfigure(2, weight=1)
        
        self.btn_get_summaries = ctk.CTkButton(frame_row2, text="Get Summaries", command=self.get_summaries_from_sources)
        self.btn_get_summaries.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.btn_edit_sources = ctk.CTkButton(frame_row2, text="Edit Sources", fg_color="gray", command=self.open_sources_editor)
        self.btn_edit_sources.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.btn_edit_instructions = ctk.CTkButton(frame_row2, text="Custom Instructions", fg_color="gray", command=self.open_instructions_editor)
        self.btn_edit_instructions.grid(row=0, column=2, padx=(5, 0), sticky="ew")

        # Row 3: Fetch Options
        self.label_mode = ctk.CTkLabel(self.frame_yt_api, text="Fetch:")
        self.label_mode.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="w")
        
        self.frame_fetch_opts = ctk.CTkFrame(self.frame_yt_api, fg_color="transparent")
        self.frame_fetch_opts.grid(row=3, column=1, padx=10, pady=(5, 10), sticky="w")
        
        self.entry_value = ctk.CTkEntry(self.frame_fetch_opts, width=50)
        self.entry_value.pack(side="left", padx=(0, 5))
        self.entry_value.insert(0, "7") # Default to 7
        
        self.mode_var = ctk.StringVar(value="Days")
        self.combo_mode = ctk.CTkComboBox(self.frame_fetch_opts, variable=self.mode_var, values=["Hours", "Days", "Videos"], width=120)
        self.combo_mode.pack(side="left")
        self.combo_mode.configure(command=self.on_mode_changed)


        # Date range controls
        self.range_var = ctk.BooleanVar(value=False)
        self.chk_range = ctk.CTkCheckBox(self.frame_fetch_opts, text="Use date range", variable=self.range_var)
        self.chk_range.pack(side="left", padx=(10, 5))
        # Grey out Fetch Limit when using date range
        self.chk_range.configure(command=self.on_toggle_range)

        self.start_date_entry = ctk.CTkEntry(self.frame_fetch_opts, width=120, placeholder_text="Start YYYY-MM-DD")
        self.start_date_entry.pack(side="left", padx=(5, 2))
        
        self.btn_start_cal = ctk.CTkButton(self.frame_fetch_opts, width=28, text="📅", command=self.open_start_calendar)
        self.btn_start_cal.pack(side="left", padx=(0, 10))

        self.end_date_entry = ctk.CTkEntry(self.frame_fetch_opts, width=120, placeholder_text="End YYYY-MM-DD")
        self.end_date_entry.pack(side="left", padx=(0, 2))
        
        self.btn_end_cal = ctk.CTkButton(self.frame_fetch_opts, width=28, text="📅", command=self.open_end_calendar)
        self.btn_end_cal.pack(side="left", padx=(0, 5))
        
        # Initialize state
        self.on_toggle_range()
        self.load_current_summary()
        self.load_api_key()

        # Row 4: Upload Text File button (audio transcription moved to Advanced section)
        self.btn_upload_file = ctk.CTkButton(self.frame_yt_api, text="Upload Text File (.txt)", command=self.upload_text_file)
        self.btn_upload_file.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Note: "Specific URLs" button removed - functionality consolidated into News Summary textbox
        # Users can now paste YouTube URLs or article URLs directly and they'll be auto-detected
        # Note: Transcription features moved to collapsible "Advanced" section at bottom

        # Open Folder button — on Summarize page (convenient after generating content)
        self.btn_open = ctk.CTkButton(
            self.pages["summarize"], text="Open Output Folder",
            fg_color="transparent", border_width=2,
            text_color=COLORS["text_primary"],
            hover_color=COLORS["bg_tertiary"],
            corner_radius=8,
            command=self.open_output_folder
        )
        self.btn_open.grid(row=3, column=0, padx=20, pady=(10, 10))

        # Status label — on Summarize page
        sum_status_frame = ctk.CTkFrame(self.pages["summarize"], fg_color="transparent")
        sum_status_frame.grid(row=4, column=0, padx=20, pady=(5, 5), sticky="ew")
        sum_status_frame.grid_columnconfigure(0, weight=1)

        self.label_status = ctk.CTkLabel(sum_status_frame, text="Ready", text_color=COLORS["text_primary"], font=ctk.CTkFont(size=14, weight="bold"))
        self.label_status.grid(row=0, column=0, sticky="w")

    def _build_audio_page(self):
        """Build the Audio page (deferred from __init__ for faster startup)."""
        self.label_audio_header = ctk.CTkLabel(
            self.pages["audio"],
            text="Convert Text/Summaries to Audio",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.label_audio_header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        # Audio Controls Card
        self.frame_audio_controls = ctk.CTkFrame(self.pages["audio"], fg_color=COLORS["bg_secondary"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        self.frame_audio_controls.grid(row=1, column=0, padx=20, pady=(5, 20), sticky="ew")
        self.frame_audio_controls.grid_columnconfigure((0, 1), weight=1)

        # Row 0: Fast Generation with sample button
        self.btn_fast = ctk.CTkButton(self.frame_audio_controls, text="Generate Fast (gTTS)", command=self.start_fast_generation)
        self.btn_fast.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ew")
        self.btn_fast_sample = ctk.CTkButton(self.frame_audio_controls, text="▶ Sample", width=90, fg_color="gray", command=self.play_gtts_sample)
        self.btn_fast_sample.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="e")

        # Row 1: Quality Voice Selection Header
        ctk.CTkLabel(
            self.frame_audio_controls, text="Quality Voice (Kokoro):",
            font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=1, column=0, columnspan=2, padx=10, pady=(10, 2), sticky="w")

        # Voice descriptions for display
        VOICE_INFO = {
            "af_heart": ("Heart", "Female", "American", "Warm, natural"),
            "af_sarah": ("Sarah", "Female", "American", "Clear, professional"),
            "af_nova": ("Nova", "Female", "American", "Bright, energetic"),
            "af_sky": ("Sky", "Female", "American", "Soft, calm"),
            "af_bella": ("Bella", "Female", "American", "Smooth, articulate"),
            "am_adam": ("Adam", "Male", "American", "Deep, authoritative"),
            "am_michael": ("Michael", "Male", "American", "Warm, conversational"),
            "am_echo": ("Echo", "Male", "American", "Crisp, modern"),
            "bf_emma": ("Emma", "Female", "British", "Elegant, refined"),
            "bf_isabella": ("Isabella", "Female", "British", "Poised, expressive"),
            "bm_george": ("George", "Male", "British", "Commanding, rich"),
            "bm_lewis": ("Lewis", "Male", "British", "Friendly, measured"),
        }

        # Voice selector grid — 3 columns of voice cards with play buttons
        voice_grid_frame = ctk.CTkFrame(self.frame_audio_controls, fg_color="transparent")
        voice_grid_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 8), sticky="ew")
        for c in range(3):
            voice_grid_frame.grid_columnconfigure(c, weight=1)

        self.voice_var = ctk.StringVar(value="af_sarah")
        voice_keys = list(VOICE_INFO.keys())

        for idx, voice_id in enumerate(voice_keys):
            name, gender, accent, desc = VOICE_INFO[voice_id]
            row_i = idx // 3
            col_i = idx % 3

            card = ctk.CTkFrame(voice_grid_frame, fg_color=COLORS["bg_primary"],
                                corner_radius=8, border_width=1, border_color=COLORS["border"])
            card.grid(row=row_i, column=col_i, padx=3, pady=3, sticky="ew")
            card.grid_columnconfigure(0, weight=1)

            # Radio-style selection via the card
            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=6, pady=(4, 0))
            top_row.grid_columnconfigure(0, weight=1)

            rb = ctk.CTkRadioButton(
                top_row, text=f"{name}", variable=self.voice_var, value=voice_id,
                font=ctk.CTkFont(size=12, weight="bold"),
                radiobutton_width=16, radiobutton_height=16
            )
            rb.pack(side="left")

            btn_play = ctk.CTkButton(
                top_row, text="▶", width=28, height=24, fg_color="gray",
                hover_color=COLORS["accent"], font=ctk.CTkFont(size=11),
                command=lambda v=voice_id: self._play_voice_sample(v)
            )
            btn_play.pack(side="right")

            ctk.CTkLabel(
                card, text=f"{accent} {gender} · {desc}",
                font=ctk.CTkFont(size=10), text_color=COLORS["text_muted"]
            ).pack(anchor="w", padx=8, pady=(0, 4))

        # Keep combo_voices for backward compat with play_sample() etc.
        self.combo_voices = None  # Voice is now selected via radio buttons

        # Convert summaries by date
        self.btn_convert_dates = ctk.CTkButton(self.frame_audio_controls, text="Convert Selected Dates to Audio", command=self.select_dates_to_audio)
        self.btn_convert_dates.grid(row=3, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")

        self.btn_quality = ctk.CTkButton(self.frame_audio_controls, text="Generate Quality (Kokoro)", command=self.start_quality_generation)
        self.btn_quality.grid(row=4, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")

        # Audio page status bar (mirrors label_status on Summarize page)
        audio_status_frame = ctk.CTkFrame(self.pages["audio"], fg_color="transparent")
        audio_status_frame.grid(row=2, column=0, padx=20, pady=(5, 10), sticky="ew")

        self.label_audio_status = ctk.CTkLabel(
            audio_status_frame, text="Ready",
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.label_audio_status.grid(row=0, column=0, sticky="w")

        # Sync to Drive button
        self.btn_sync_drive = ctk.CTkButton(
            audio_status_frame, text="Sync to Drive",
            width=120, fg_color="gray", hover_color=COLORS["accent"],
            command=self._sync_to_drive
        )
        self.btn_sync_drive.grid(row=0, column=1, sticky="e", padx=(10, 0))
        audio_status_frame.grid_columnconfigure(1, weight=1)

    def _build_extract_page(self):
        """Build the Extract/Data Extractor page (deferred from __init__ for faster startup)."""
        ctk.CTkLabel(
            self.pages["extract"],
            text="Data Extractor",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Extract content card — replaces the old collapsible section
        self.frame_extract = ctk.CTkFrame(self.pages["extract"], fg_color=COLORS["bg_secondary"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        self.frame_extract.grid(row=1, column=0, padx=20, sticky="ew", pady=(0, 10))
        self.frame_extract.grid_columnconfigure(0, weight=1)

        # Extract content (always visible now — no collapsible toggle needed)
        self.extract_content = ctk.CTkFrame(self.frame_extract, fg_color="transparent")
        self.extract_content.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.extract_content.grid_columnconfigure(0, weight=1)

        # Mode tabs (URL vs HTML) - styled as toggle tabs
        tab_frame = ctk.CTkFrame(self.extract_content, fg_color="transparent")
        tab_frame.grid(row=0, column=0, sticky="w", pady=(0, 5))

        ctk.CTkLabel(tab_frame, text="Input Mode:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))

        self.extract_mode_var = ctk.StringVar(value="url")
        self.btn_tab_url = ctk.CTkButton(tab_frame, text="● From URL(s)", width=130,
                                         border_width=2, border_color=("gray40", "gray60"),
                                         command=lambda: self.set_extract_mode("url"))
        self.btn_tab_url.pack(side="left", padx=(0, 5))
        self.btn_tab_html = ctk.CTkButton(tab_frame, text="○ Paste HTML", width=120,
                                          fg_color=("gray70", "gray30"), border_width=0,
                                          command=lambda: self.set_extract_mode("html"))
        self.btn_tab_html.pack(side="left")

        # URL input section
        self.url_input_frame = ctk.CTkFrame(self.extract_content, fg_color="transparent")
        self.url_input_frame.grid(row=1, column=0, sticky="ew", pady=5)
        self.url_input_frame.grid_columnconfigure(0, weight=1)

        url_label = ctk.CTkLabel(self.url_input_frame, text="Paste URLs (any format - will auto-detect):", font=ctk.CTkFont(size=12))
        url_label.grid(row=0, column=0, sticky="w", pady=(0, 3))

        self.extract_url_text = ctk.CTkTextbox(self.url_input_frame, height=80)
        self.extract_url_text.grid(row=1, column=0, sticky="ew")
        self.extract_url_text.insert("1.0", "")

        self.extract_url_entry = ctk.CTkEntry(self.url_input_frame, placeholder_text="https://cryptosum.beehiiv.com/p/...")

        # HTML input section (hidden initially)
        self.html_input_frame = ctk.CTkFrame(self.extract_content, fg_color="transparent")
        self.html_input_frame.grid(row=1, column=0, sticky="ew", pady=5)
        self.html_input_frame.grid_columnconfigure(0, weight=1)
        self.html_input_frame.grid_remove()

        self.extract_html_text = ctk.CTkTextbox(self.html_input_frame, height=100)
        self.extract_html_text.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        self.extract_source_url = ctk.CTkEntry(self.html_input_frame, placeholder_text="Source URL (optional)")
        self.extract_source_url.grid(row=1, column=0, sticky="ew")

        # Options row
        options_frame = ctk.CTkFrame(self.extract_content, fg_color="transparent")
        options_frame.grid(row=2, column=0, sticky="ew", pady=5)

        ctk.CTkLabel(options_frame, text="Config:").pack(side="left", padx=(0, 5))

        self.extract_config_var = ctk.StringVar(value="Default")
        config_values = self._get_extraction_configs()
        self.extract_config_combo = ctk.CTkComboBox(options_frame, variable=self.extract_config_var, values=config_values, width=150, state="readonly", command=self.on_extract_config_changed)
        self.extract_config_combo.pack(side="left", padx=(0, 5))

        self.btn_manage_configs = ctk.CTkButton(options_frame, text="Manage", width=60, fg_color="gray", command=self.open_config_manager)
        self.btn_manage_configs.pack(side="left", padx=(0, 15))

        self.grid_enrich_var = ctk.BooleanVar(value=False)
        self.chk_grid_enrich = ctk.CTkCheckBox(options_frame, text="Enrich with Grid", variable=self.grid_enrich_var)
        self.chk_grid_enrich.pack(side="left")

        self.research_articles_var = ctk.BooleanVar(value=False)
        self.chk_research_articles = ctk.CTkCheckBox(options_frame, text="Research Articles", variable=self.research_articles_var)
        self.chk_research_articles.pack(side="left", padx=(15, 0))

        self.on_extract_config_changed(self.extract_config_var.get())

        self.btn_extract = ctk.CTkButton(self.extract_content, text="Extract Links", command=self.start_extraction, fg_color="green")
        self.btn_extract.grid(row=3, column=0, sticky="ew", pady=(10, 5))

        # Results section
        self.extract_results_frame = ctk.CTkFrame(self.extract_content)
        self.extract_results_frame.grid(row=4, column=0, sticky="ew", pady=5)
        self.extract_results_frame.grid_columnconfigure(0, weight=1)
        self.extract_results_frame.grid_remove()

        results_header = ctk.CTkFrame(self.extract_results_frame, fg_color="transparent")
        results_header.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        results_header.grid_columnconfigure(0, weight=1)

        self.extract_count_label = ctk.CTkLabel(results_header, text="Extracted Links (0)", font=ctk.CTkFont(weight="bold"))
        self.extract_count_label.grid(row=0, column=0, sticky="w")

        export_btns = ctk.CTkFrame(results_header, fg_color="transparent")
        export_btns.grid(row=0, column=1, sticky="e")

        self.btn_export_csv = ctk.CTkButton(export_btns, text="Save CSV", width=80, command=self.export_extracted_csv)
        self.btn_export_csv.pack(side="left", padx=(0, 5))

        self.btn_export_sheets = ctk.CTkButton(export_btns, text="To Sheets", width=80, fg_color="#0F9D58", command=self.export_to_google_sheets)
        self.btn_export_sheets.pack(side="left", padx=(0, 5))

        self.btn_copy_text = ctk.CTkButton(export_btns, text="Copy", width=60, fg_color="gray", command=self.copy_extracted_text)
        self.btn_copy_text.pack(side="left")

        self.extract_results_list = ctk.CTkScrollableFrame(self.extract_results_frame, height=150)
        self.extract_results_list.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.extract_results_list.grid_columnconfigure(0, weight=1)

        # Transcription Card — on Audio page (always visible, no toggle)
        self.frame_transcription = ctk.CTkFrame(self.pages["audio"], fg_color=COLORS["bg_secondary"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        self.frame_transcription.grid(row=2, column=0, padx=20, sticky="ew", pady=(0, 20))
        self.frame_transcription.grid_columnconfigure(0, weight=1)

        # Transcription section title inside the card
        ctk.CTkLabel(
            self.frame_transcription, text="Transcription",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        # Transcription content (always visible now)
        self.transcription_content = ctk.CTkFrame(self.frame_transcription, fg_color="transparent")
        self.transcription_content.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.transcription_content.grid_columnconfigure(0, weight=1)

        # Description
        ctk.CTkLabel(
            self.transcription_content,
            text="Audio/video transcription (requires faster-whisper installation)",
            font=("Arial", 11),
            text_color="gray"
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Upload Audio File button
        self.btn_upload_audio = ctk.CTkButton(
            self.transcription_content,
            text="Upload Audio/Video File (.mp3, .wav, .m4a)",
            command=self.upload_audio_file
        )
        self.btn_upload_audio.grid(row=1, column=0, sticky="ew", pady=(0, 5))

        # Selected files panel for transcription
        self.selected_panel = ctk.CTkFrame(self.transcription_content, fg_color=("gray90", "gray20"))
        self.selected_panel.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.selected_panel.grid_columnconfigure(0, weight=1)

        self.files_combo = ctk.CTkComboBox(self.selected_panel, values=["No files selected"], width=250, state="readonly")
        self.files_combo.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.files_combo.set("No files selected")

        self.btn_clear_selected = ctk.CTkButton(self.selected_panel, text="Clear", width=80, command=self._clear_selected_file)
        self.btn_clear_selected.grid(row=0, column=1, padx=(10, 10), pady=5)

        self.btn_transcribe = ctk.CTkButton(self.selected_panel, text="Transcribe", width=100, command=self.start_transcription, state="disabled", fg_color="green")
        self.btn_transcribe.grid(row=0, column=2, padx=(0, 10), pady=5)

        # Transcription Status Indicator
        self.transcription_service = get_transcription_service()
        transcription_text, transcription_color = get_transcription_status()
        cursor_type = "hand2" if transcription_color != "green" else "arrow"

        self.label_transcription = ctk.CTkLabel(
            self.transcription_content,
            text=transcription_text,
            text_color=transcription_color,
            font=("Arial", 11),
            cursor=cursor_type
        )
        self.label_transcription.grid(row=3, column=0, sticky="w", pady=(5, 0))
        self.label_transcription.bind("<Button-1>", lambda e: self.show_transcription_guide())

    def _build_scheduler_page_widgets(self):
        """Build the Scheduler page widgets (deferred from __init__ for faster startup)."""
        ctk.CTkLabel(
            self.pages["scheduler"],
            text="Scheduler",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Scheduler card
        self.frame_scheduler = ctk.CTkFrame(self.pages["scheduler"], fg_color=COLORS["bg_secondary"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        self.frame_scheduler.grid(row=1, column=0, padx=20, sticky="ew", pady=(0, 10))
        self.frame_scheduler.grid_columnconfigure(0, weight=1)

        # Scheduler content (always visible now — own page)
        self.scheduler_content = ctk.CTkFrame(self.frame_scheduler, fg_color="transparent")
        self.scheduler_content.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.scheduler_content.grid_columnconfigure(0, weight=1)

        # Description
        ctk.CTkLabel(
            self.scheduler_content,
            text="Automate data extraction on a schedule",
            font=("Arial", 11),
            text_color="gray"
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Scheduler status and controls
        scheduler_controls = ctk.CTkFrame(self.scheduler_content, fg_color="transparent")
        scheduler_controls.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        scheduler_controls.grid_columnconfigure(1, weight=1)

        # Scheduler on/off toggle
        self.scheduler_enabled_var = ctk.BooleanVar(value=False)
        self.scheduler_switch = ctk.CTkSwitch(
            scheduler_controls,
            text="Scheduler Active",
            variable=self.scheduler_enabled_var,
            command=self._toggle_scheduler,
            onvalue=True,
            offvalue=False
        )
        self.scheduler_switch.grid(row=0, column=0, sticky="w")

        # Status label
        self.scheduler_status_label = ctk.CTkLabel(
            scheduler_controls,
            text="● Stopped",
            text_color="gray",
            font=("Arial", 11)
        )
        self.scheduler_status_label.grid(row=0, column=1, sticky="w", padx=(15, 0))

        # Setup Guide button
        self.btn_scheduler_guide = ctk.CTkButton(
            scheduler_controls,
            text="? Setup Guide",
            width=100,
            fg_color="gray",
            command=self.show_scheduler_guide
        )
        self.btn_scheduler_guide.grid(row=0, column=2, sticky="e")

        # Tasks list frame
        self.scheduler_tasks_frame = ctk.CTkFrame(self.scheduler_content)
        self.scheduler_tasks_frame.grid(row=2, column=0, sticky="ew", pady=5)
        self.scheduler_tasks_frame.grid_columnconfigure(0, weight=1)

        # Tasks header
        tasks_header = ctk.CTkFrame(self.scheduler_tasks_frame, fg_color="transparent")
        tasks_header.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        tasks_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(tasks_header, text="Scheduled Tasks", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w")
        self.btn_add_task = ctk.CTkButton(tasks_header, text="+ Add Task", width=90, fg_color="green", command=self._open_task_editor)
        self.btn_add_task.grid(row=0, column=1, sticky="e")

        # Scrollable tasks list
        self.scheduler_tasks_list = ctk.CTkScrollableFrame(self.scheduler_tasks_frame, height=120)
        self.scheduler_tasks_list.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.scheduler_tasks_list.grid_columnconfigure(0, weight=1)

        # Placeholder for empty state
        self.scheduler_empty_label = ctk.CTkLabel(
            self.scheduler_tasks_list,
            text="No scheduled tasks. Click '+ Add Task' to create one.",
            text_color="gray",
            font=("Arial", 11)
        )
        self.scheduler_empty_label.grid(row=0, column=0, pady=20)

        # --- Collapsible Task Execution Log ---
        self._build_task_log_panel()

        # Background Scheduler Section
        bg_scheduler_frame = ctk.CTkFrame(self.scheduler_content, fg_color=("gray85", "gray20"))
        bg_scheduler_frame.grid(row=4, column=0, sticky="ew", pady=(10, 5))
        bg_scheduler_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            bg_scheduler_frame,
            text="Background Mode",
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            bg_scheduler_frame,
            text="Run scheduler even when app is closed",
            font=("Arial", 10),
            text_color="gray"
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 5))

        # Background scheduler controls row
        bg_controls = ctk.CTkFrame(bg_scheduler_frame, fg_color="transparent")
        bg_controls.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 8))
        bg_controls.grid_columnconfigure(2, weight=1)

        # Background scheduler toggle
        self.bg_scheduler_var = ctk.BooleanVar(value=False)
        self.bg_scheduler_switch = ctk.CTkSwitch(
            bg_controls,
            text="Enable Background",
            variable=self.bg_scheduler_var,
            command=self._toggle_background_scheduler,
            onvalue=True,
            offvalue=False
        )
        self.bg_scheduler_switch.grid(row=0, column=0, sticky="w")

        # Background status
        self.bg_scheduler_status = ctk.CTkLabel(
            bg_controls,
            text="● Not running",
            text_color="gray",
            font=("Arial", 10)
        )
        self.bg_scheduler_status.grid(row=0, column=1, sticky="w", padx=(15, 0))

        # Launch on login checkbox
        self.launch_on_login_var = ctk.BooleanVar(value=False)
        self.launch_on_login_check = ctk.CTkCheckBox(
            bg_controls,
            text="Start on login",
            variable=self.launch_on_login_var,
            command=self._toggle_launch_on_login,
            font=("Arial", 11)
        )
        self.launch_on_login_check.grid(row=0, column=2, sticky="e", padx=(10, 0))

        # Initialize background scheduler state
        self._init_background_scheduler_state()

        # Scheduler lazy-initialized on first Scheduler page visit
        self._scheduler = None
        self._scheduler_initialized = False
        self._task_running_id = None
        self._backfill_stop = False

        # Cloud Scheduler Card (on Scheduler page, below the local scheduler)
        self._build_cloud_scheduler_card()

    def _post_build_setup(self):
        """Run after all deferred page builds complete. Sets up cross-page references."""
        print(f"[DEBUG] _post_build_setup running. pages_built={self._pages_built}", flush=True)
        # Compression status — tracked for settings page.
        # Use cache directly to avoid any blocking — background thread should be done by now.
        ffmpeg_ok = _ffmpeg_cache if _ffmpeg_cache is not None else False
        self.compression_enabled = ffmpeg_ok
        compression_text = "✓ Compression enabled" if ffmpeg_ok else "⚠ Compression disabled"
        compression_color = "green" if ffmpeg_ok else "orange"

        self.label_compression = ctk.CTkLabel(
            self.pages["settings"],
            text=compression_text,
            text_color=compression_color,
            font=("Arial", 11),
            cursor="hand2"
        )
        self.label_compression.grid(row=10, column=0, padx=20, pady=(5, 20))
        self.label_compression.bind("<Button-1>", lambda e: self.show_compression_guide())

        # Initialize tooltips for all buttons
        self._init_tooltips()

        # Schedule placeholder check after UI fully loads (handles cached content)
        self.after(100, self._check_placeholder_on_startup)

        # Process launch URL if provided (deferred to after UI is fully built)
        if self._pending_launch_url:
            self.after(500, lambda: self._handle_launch_url(self._pending_launch_url))

        # Register macOS URL scheme handler for when app is already running
        if sys.platform == 'darwin':
            try:
                self.createcommand('::tk::mac::LaunchURL', self._handle_launch_url)
            except Exception:
                pass  # Not fatal — URL scheme just won't work for already-running app

        # Show first-run wizard if this is the first launch
        if not self.settings.get("first_run_completed", False):
            self.after(1000, self._show_first_run_wizard)

        # macOS frozen app activation fix — without this, the window appears
        # but doesn't receive click events until the user clicks to activate it.
        if sys.platform == 'darwin':
            self.after(200, self._activate_window)

    def _activate_window(self):
        """Bring window to front and make it the active/key window on macOS.

        PyInstaller apps on macOS often fail to become the active application
        on launch, causing click events to be silently ignored until the user
        manually clicks to activate. This forces activation via multiple
        strategies for maximum compatibility.
        """
        activated = False
        try:
            from AppKit import NSApplication
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            activated = True
        except ImportError:
            pass

        if not activated:
            try:
                import subprocess
                subprocess.Popen(
                    ['osascript', '-e',
                     'tell application "System Events" to set frontmost of '
                     'the first process whose unix id is '
                     f'{os.getpid()} to true'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception:
                pass

        # Tk-level activation as complement — ensures the Tk window itself
        # is raised within the app even if Cocoa activation already worked.
        self.lift()
        self.attributes('-topmost', True)
        self.after(100, lambda: self.attributes('-topmost', False))
        self.focus_force()

    def _check_placeholder_on_startup(self):
        """Check and update placeholder visibility after startup (for cached content)."""
        if hasattr(self, '_update_placeholder'):
            self._update_placeholder()
        # Also trigger URL detection in case there's existing content
        if hasattr(self, '_on_textbox_change'):
            self._on_textbox_change()

    # ========== Navigation System ==========

    def _create_sidebar(self):
        """Create the left sidebar navigation matching web app design."""
        self.sidebar_frame = ctk.CTkFrame(
            self, width=200, corner_radius=0,
            fg_color=COLORS["bg_secondary"],
            border_width=0
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)  # Fixed width
        self.sidebar_frame.grid_columnconfigure(0, weight=1)

        # App title at top
        title_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=16, pady=(20, 8), sticky="ew")

        ctk.CTkLabel(
            title_frame, text="Daily Audio",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame, text="Briefing",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(anchor="w")

        # Separator
        sep = ctk.CTkFrame(self.sidebar_frame, height=1, fg_color=COLORS["border"])
        sep.grid(row=1, column=0, padx=16, pady=(8, 12), sticky="ew")

        # Navigation buttons
        self.nav_buttons = {}
        def _make_nav_cmd(p):
            def cmd():
                print(f"[DEBUG] Nav button clicked: {p}", flush=True)
                self._navigate_to(p)
            return cmd
        for i, (page_id, label) in enumerate(NAV_PAGES):
            btn = ctk.CTkButton(
                self.sidebar_frame, text=label,
                anchor="w", height=40,
                font=ctk.CTkFont(size=14),
                fg_color="transparent",
                text_color=COLORS["text_secondary"],
                hover_color=COLORS["bg_tertiary"],
                corner_radius=8,
                command=_make_nav_cmd(page_id)
            )
            btn.grid(row=i + 2, column=0, padx=10, pady=2, sticky="ew")
            self.nav_buttons[page_id] = btn

        # Push version/status to bottom
        self.sidebar_frame.grid_rowconfigure(len(NAV_PAGES) + 2, weight=1)

        # Status area at bottom of sidebar
        status_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        status_frame.grid(row=len(NAV_PAGES) + 3, column=0, padx=16, pady=(8, 16), sticky="ew")

        self.sidebar_status_label = ctk.CTkLabel(
            status_frame, text="Ready",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.sidebar_status_label.pack(anchor="w")

        self.sidebar_version_label = ctk.CTkLabel(
            status_frame, text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        self.sidebar_version_label.pack(anchor="w", pady=(4, 0))

    def _create_pages(self):
        """Create all page frames (one per navigation item)."""
        for page_id, _ in NAV_PAGES:
            page = ctk.CTkScrollableFrame(
                self.page_container,
                fg_color=COLORS["bg_primary"],
                corner_radius=0
            )
            # Do NOT grid pages here — only the active page should be gridded.
            # Previously we did grid() + grid_remove() which caused z-order issues
            # in frozen (PyInstaller) builds where the last-created page could
            # intercept events from the sidebar.
            page.grid_columnconfigure(0, weight=1)
            # Widen scrollbar
            try:
                page._scrollbar.configure(width=14)
            except Exception:
                pass
            self.pages[page_id] = page
            self._bind_page_mousewheel(page)

        # Show home page by default — it's the only page that gets gridded
        self.pages["home"].grid(row=0, column=0, sticky="nsew")
        self._current_page = "home"
        self.nav_buttons["home"].configure(
            fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["accent"]
        )

    def _bind_page_mousewheel(self, page):
        """Bind mouse-wheel scrolling to a CTkScrollableFrame page."""
        try:
            canvas = page._parent_canvas
        except AttributeError:
            return

        def _on_mousewheel(event):
            # macOS: event.delta is positive=up, negative=down
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:   # Linux scroll up
                canvas.yview_scroll(-3, "units")
            elif event.num == 5:   # Linux scroll down
                canvas.yview_scroll(3, "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", _on_mousewheel)
        canvas.bind("<Button-5>", _on_mousewheel)
        page.bind("<MouseWheel>", _on_mousewheel)
        page.bind("<Button-4>", _on_mousewheel)
        page.bind("<Button-5>", _on_mousewheel)

    def _navigate_to(self, page_name: str):
        """Switch to a page (hides current, shows target, highlights nav)."""
        print(f"[DEBUG] _navigate_to({page_name}) current={self._current_page} pages_built={self._pages_built}", flush=True)
        if page_name == self._current_page:
            return

        # Hide current page
        if self._current_page in self.pages:
            self.pages[self._current_page].grid_remove()
            if self._current_page in self.nav_buttons:
                self.nav_buttons[self._current_page].configure(
                    fg_color="transparent",
                    text_color=COLORS["text_secondary"]
                )
            # Flush the hide immediately so user sees page disappear before new page renders
            self.update_idletasks()

        # Show target page
        if page_name in self.pages:
            # Ensure page is built (deferred loading — build on first visit if needed)
            self._ensure_page_built(page_name)
            self.pages[page_name].grid(row=0, column=0, sticky="nsew")
            if page_name in self.nav_buttons:
                self.nav_buttons[page_name].configure(
                    fg_color=COLORS["bg_tertiary"],
                    text_color=COLORS["accent"]
                )
            self._current_page = page_name

            # Page-specific refresh hooks
            if page_name == "scheduler":
                if not self._scheduler_initialized:
                    self._init_scheduler()
                    self._scheduler_initialized = True
                self._refresh_scheduler_tasks()
            elif page_name == "settings":
                self._refresh_settings_page()

    def _create_card(self, parent, title=None, padding=16):
        """Create a card-styled frame matching web app visual language."""
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        if title:
            ctk.CTkLabel(
                card, text=title,
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color=COLORS["text_primary"]
            ).grid(row=0, column=0, padx=padding, pady=(padding, 8), sticky="w")
            card._content_row = 1
        else:
            card._content_row = 0
        card.grid_columnconfigure(0, weight=1)
        return card

    def _refresh_settings_page(self):
        """Refresh settings page content (called when navigating to Settings)."""
        # Update compression status
        if hasattr(self, 'label_compression'):
            self.compression_enabled = _cached_check_ffmpeg()
            compression_text = "✓ Compression enabled" if self.compression_enabled else "⚠ Compression disabled"
            compression_color = "green" if self.compression_enabled else "orange"
            self.label_compression.configure(text=compression_text, text_color=compression_color)
        # Refresh Drive status (quick, no API call)
        self._refresh_drive_status()
        # Refresh API usage stats
        self._refresh_usage_stats()

    def _refresh_usage_stats(self):
        """Refresh the API usage display on the Settings page."""
        if not hasattr(self, 'usage_daily_label'):
            return
        try:
            from api_usage_tracker import get_tracker
            stats = get_tracker().get_stats()

            daily = stats["daily_calls"]
            daily_max = stats["daily_limit"]
            monthly = stats["monthly_calls"]
            monthly_max = stats["monthly_limit"]

            self.usage_daily_label.configure(
                text=f"Today: {daily:,} / {daily_max:,} calls"
            )
            self.usage_daily_bar.set(min(daily / max(daily_max, 1), 1.0))

            self.usage_monthly_label.configure(
                text=f"Month: {monthly:,} / {monthly_max:,} calls"
            )
            self.usage_monthly_bar.set(min(monthly / max(monthly_max, 1), 1.0))

            daily_cost = stats.get("daily_cost_estimate", 0)
            monthly_cost = stats.get("monthly_cost_estimate", 0)
            self.usage_cost_label.configure(
                text=f"Est. cost today: ${daily_cost:.4f}  |  Month: ${monthly_cost:.4f}"
            )

            # Per-task breakdown
            task_stats = get_tracker().get_task_stats()
            if task_stats:
                lines = ["Scheduler tasks this month:"]
                for tid, info in sorted(task_stats.items(), key=lambda x: x[1].get("calls_this_month", 0), reverse=True):
                    name = info.get("name", "Unknown")
                    calls = info.get("calls_this_month", 0)
                    if calls > 0:
                        lines.append(f"  {name}: {calls:,} calls")
                self.usage_tasks_label.configure(text="\n".join(lines) if len(lines) > 1 else "")
            else:
                self.usage_tasks_label.configure(text="")

            # Budget cap display
            if hasattr(self, 'budget_bar'):
                budget_cap = stats.get("monthly_budget_usd", 0)
                if budget_cap > 0:
                    pct = min(monthly_cost / budget_cap, 1.0)
                    self.budget_bar.set(pct)
                    pct_display = pct * 100
                    self.budget_status_label.configure(
                        text=f"${monthly_cost:.4f} / ${budget_cap:.2f} ({pct_display:.0f}% used)"
                    )
                    # Color coding
                    if pct >= 1.0:
                        self.budget_status_label.configure(
                            text_color=COLORS.get("error", "#ef4444")
                        )
                    elif pct >= 0.8:
                        self.budget_status_label.configure(
                            text_color=COLORS.get("warning", "#f59e0b")
                        )
                    else:
                        self.budget_status_label.configure(
                            text_color=COLORS["text_muted"]
                        )
                else:
                    self.budget_bar.set(0)
                    self.budget_status_label.configure(
                        text="No budget cap set (0 = unlimited)",
                        text_color=COLORS["text_muted"]
                    )

                # Cooldown indicator
                if hasattr(self, 'cooldown_indicator'):
                    if budget_cap > 0 and monthly_cost >= budget_cap and stats.get("cooldown_enabled", True):
                        self.cooldown_indicator.grid()
                    else:
                        self.cooldown_indicator.grid_remove()
        except Exception as e:
            print(f"[Settings] Error refreshing usage stats: {e}")

    def _save_usage_limits(self):
        """Save API usage limit settings."""
        try:
            from api_usage_tracker import get_tracker
            daily = int(self.usage_daily_limit_entry.get() or 500)
            monthly = int(self.usage_monthly_limit_entry.get() or 10000)
            enabled = self.usage_limits_var.get()

            # Budget cap and cooldown
            budget_str = self.budget_cap_entry.get().strip() if hasattr(self, 'budget_cap_entry') else "0"
            budget_usd = float(budget_str) if budget_str else 0.0
            cooldown = self.cooldown_var.get() if hasattr(self, 'cooldown_var') else True

            get_tracker().update_limits(
                daily_max=daily, monthly_max=monthly, enabled=enabled,
                monthly_budget_usd=budget_usd, cooldown_enabled=cooldown,
            )

            self.settings["api_limits_enabled"] = enabled
            self.settings["api_daily_limit"] = daily
            self.settings["api_monthly_limit"] = monthly
            self.settings["api_budget_usd"] = budget_usd
            self.settings["api_cooldown_enabled"] = cooldown
            self._save_settings()
            self._refresh_usage_stats()
        except ValueError:
            pass  # Invalid input, ignore

    def _reset_usage_today(self):
        """Reset today's API usage counter."""
        try:
            from api_usage_tracker import get_tracker
            get_tracker().reset_today()
            self._refresh_usage_stats()
        except Exception as e:
            print(f"[Settings] Error resetting usage: {e}")

    # ========== Google Drive Integration Methods ==========

    def _refresh_drive_status(self):
        """Refresh Drive status indicator (quick check, no API call)."""
        if not hasattr(self, 'drive_status_dot'):
            return
        try:
            from drive_manager import is_drive_available, is_signed_in, get_user_email
            if not is_drive_available():
                self._update_drive_status(False, "Setup required — see Guide")
                return
            if not is_signed_in():
                self._update_drive_status(False, "Not signed in — click 'Sign in with Google'")
                return
            shared_id = self.settings.get("drive_folder_id", "")
            if shared_id:
                self._update_drive_status(True, "Ready (click Test to verify)")
            else:
                self._update_drive_status(True, "Signed in — set a Drive folder below")

            # Update account label too
            if hasattr(self, 'drive_account_label'):
                email = get_user_email()
                if email:
                    self.drive_account_label.configure(
                        text=f"Signed in as {email}", text_color=COLORS["success"])
                else:
                    self.drive_account_label.configure(
                        text="Signed in", text_color=COLORS["success"])
            if hasattr(self, 'btn_drive_sign_in'):
                self.btn_drive_sign_in.configure(state="disabled")
            if hasattr(self, 'btn_drive_sign_out'):
                self.btn_drive_sign_out.configure(state="normal")
        except ImportError:
            self._update_drive_status(False, "Drive module not available")

    def _update_drive_status(self, connected: bool, message: str):
        """Update Drive connection indicator on Settings page."""
        if hasattr(self, 'drive_status_dot'):
            color = COLORS["success"] if connected else COLORS["warning"]
            self.drive_status_dot.configure(text_color=color)
        if hasattr(self, 'drive_status_label'):
            self.drive_status_label.configure(text=message)

    def _drive_sign_in(self):
        """Start OAuth2 sign-in flow (opens browser)."""
        self._update_status("Opening Google sign-in in browser...", "orange")
        self.btn_drive_sign_in.configure(state="disabled")

        def task():
            try:
                from drive_manager import sign_in
                result = sign_in()
                if result['success']:
                    email = result.get('email', 'Unknown')
                    self.after(0, lambda: [
                        self._update_status(f"Signed in to Drive as {email}", "green"),
                        self._refresh_drive_status(),
                    ])
                else:
                    err = result.get('error', 'Unknown error')[:80]
                    self.after(0, lambda: [
                        self._update_status(f"Drive sign-in failed: {err}", "red"),
                        self.btn_drive_sign_in.configure(state="normal"),
                    ])
            except Exception as e:
                self.after(0, lambda: [
                    self._update_status(f"Drive sign-in error: {str(e)[:60]}", "red"),
                    self.btn_drive_sign_in.configure(state="normal"),
                ])

        threading.Thread(target=task, daemon=True).start()

    def _drive_sign_out(self):
        """Sign out of Google Drive (remove stored token)."""
        try:
            from drive_manager import sign_out
            sign_out()
        except Exception:
            pass
        self._update_status("Signed out of Drive", "gray")
        if hasattr(self, 'drive_account_label'):
            self.drive_account_label.configure(text="Not signed in", text_color=COLORS["text_muted"])
        if hasattr(self, 'btn_drive_sign_in'):
            self.btn_drive_sign_in.configure(state="normal")
        if hasattr(self, 'btn_drive_sign_out'):
            self.btn_drive_sign_out.configure(state="disabled")
        self._update_drive_status(False, "Not signed in")

    def _save_drive_folder(self):
        """Save and verify the Drive folder URL/ID from the entry field."""
        raw_value = self.drive_folder_entry.get().strip()
        if not raw_value:
            self.settings["drive_folder_id"] = ""
            self._save_settings()
            if hasattr(self, 'drive_folder_status'):
                self.drive_folder_status.configure(text="Folder cleared.", text_color=COLORS["text_muted"])
            return

        try:
            from drive_manager import extract_folder_id_from_url, verify_folder_access
        except ImportError:
            if hasattr(self, 'drive_folder_status'):
                self.drive_folder_status.configure(text="Drive module not available", text_color=COLORS["danger"])
            return

        folder_id = extract_folder_id_from_url(raw_value)
        if not folder_id:
            if hasattr(self, 'drive_folder_status'):
                self.drive_folder_status.configure(text="Invalid URL or ID", text_color=COLORS["danger"])
            return

        # Save the clean folder ID
        self.settings["drive_folder_id"] = folder_id
        self._save_settings()

        # Update entry to show clean ID
        self.drive_folder_entry.delete(0, "end")
        self.drive_folder_entry.insert(0, folder_id)

        if hasattr(self, 'drive_folder_status'):
            self.drive_folder_status.configure(text="Verifying folder access...", text_color="orange")

        # Verify access in background
        def verify():
            try:
                result = verify_folder_access(folder_id)
                if result['accessible']:
                    msg = f"Folder: {result['name']}"
                    self.after(0, lambda: self.drive_folder_status.configure(
                        text=msg, text_color=COLORS["success"]))
                else:
                    msg = result.get('error', 'Cannot access folder')
                    self.after(0, lambda: self.drive_folder_status.configure(
                        text=msg, text_color=COLORS["danger"]))
            except Exception as e:
                self.after(0, lambda: self.drive_folder_status.configure(
                    text=f"Error: {str(e)[:50]}", text_color=COLORS["danger"]))

        threading.Thread(target=verify, daemon=True).start()

    def _on_drive_auto_upload_toggle(self):
        """Handle Drive auto-upload toggle change."""
        enabled = self.drive_auto_upload_var.get()
        self.settings["drive_auto_upload"] = enabled
        self._save_settings()
        status = "enabled" if enabled else "disabled"
        self._update_status(f"Drive auto-upload {status}", "green")

    def _test_drive_connection(self):
        """Test Google Drive connection and verify folder access."""
        self._update_drive_status(False, "Testing connection...")

        def task():
            try:
                from drive_manager import (is_signed_in, get_drive_service,
                                           verify_folder_access, get_storage_quota)
                if not is_signed_in():
                    self.after(0, lambda: self._update_drive_status(
                        False, "Not signed in. Click 'Sign in with Google' first."))
                    return
                get_drive_service()

                # Check folder access
                shared_id = self.settings.get("drive_folder_id", "")
                if shared_id:
                    check = verify_folder_access(shared_id)
                    if check['accessible']:
                        # Also get quota
                        try:
                            quota = get_storage_quota()
                            used = quota.get('used_gb', 0)
                            total = quota.get('total_gb', 0)
                            quota_str = f" — {used:.1f}GB / {total:.1f}GB" if total else ""
                        except Exception:
                            quota_str = ""
                        msg = f"Connected — {check['name']}{quota_str}"
                        self.after(0, lambda: self._update_drive_status(True, msg))
                        if hasattr(self, 'drive_folder_status'):
                            self.after(0, lambda: self.drive_folder_status.configure(
                                text=f"Folder: {check['name']}", text_color=COLORS["success"]))
                    else:
                        msg = f"Folder error: {check['error']}"
                        self.after(0, lambda: self._update_drive_status(False, msg))
                else:
                    msg = "Connected — Set a Drive folder URL to enable uploads"
                    self.after(0, lambda: self._update_drive_status(True, msg))
            except Exception as e:
                err = str(e)[:60]
                self.after(0, lambda: self._update_drive_status(False, f"Error: {err}"))

        threading.Thread(target=task, daemon=True).start()

    def _sync_to_drive(self):
        """Manual sync of all Week folders to Google Drive."""
        shared_id = self.settings.get("drive_folder_id", "")
        if not shared_id:
            self._update_status("Set a Drive folder in Settings first.", "orange")
            return

        self._update_status("Syncing to Drive...", "orange")
        self.btn_sync_drive.configure(state="disabled")

        def task():
            try:
                from drive_manager import is_signed_in, sync_week_folders
                if not is_signed_in():
                    self._update_status("Not signed in to Drive. Check Settings.", "red")
                    return
                data_dir = get_data_directory()
                root_name = self.settings.get("drive_root_folder_name", "Daily Audio Briefing")
                log = sync_week_folders(
                    data_dir, root_name,
                    shared_folder_id=shared_id,
                    status_callback=self._update_status
                )
                uploaded = sum(1 for l in log if 'Uploaded' in l)
                skipped = sum(1 for l in log if 'Skipped' in l or 'exists' in l)
                self._update_status(
                    f"Drive sync complete: {uploaded} uploaded, {skipped} skipped",
                    "green"
                )
            except Exception as e:
                self._update_status(f"Drive sync error: {str(e)[:50]}", "red")
            finally:
                self.after(0, lambda: self.btn_sync_drive.configure(state="normal"))

        threading.Thread(target=task, daemon=True).start()

    def _upload_to_drive_after_generation(self, audio_filename: str):
        """Auto-upload generated audio file to Drive (background, non-blocking).

        Called after successful audio generation if auto-upload is enabled.
        Errors are logged but don't interrupt the user.
        """
        if not self.settings.get("drive_auto_upload", False):
            return

        shared_id = self.settings.get("drive_folder_id", "")
        if not shared_id:
            return  # No folder configured, skip silently

        def task():
            try:
                from drive_manager import (is_signed_in, get_or_create_folder,
                                           upload_file, verify_folder_access)
                if not is_signed_in():
                    return

                # Verify folder access
                check = verify_folder_access(shared_id)
                if not check['accessible']:
                    print(f"[Drive] Auto-upload skipped: {check['error']}")
                    return

                # Find the local file
                data_dir = get_data_directory()
                week_num = datetime.datetime.now().isocalendar()[1]
                year = datetime.datetime.now().year
                week_folder = f"Week_{week_num}_{year}"
                local_path = os.path.join(data_dir, week_folder, audio_filename)

                if not os.path.exists(local_path):
                    # Try directly in data dir
                    local_path = os.path.join(data_dir, audio_filename)
                    if not os.path.exists(local_path):
                        return  # File not found, skip silently

                # Create folder structure: shared_folder / root / Week_N_YYYY
                root_name = self.settings.get("drive_root_folder_name", "Daily Audio Briefing")
                root_id = get_or_create_folder(root_name, parent_id=shared_id)
                week_id = get_or_create_folder(week_folder, parent_id=root_id)

                # Upload
                result = upload_file(local_path, week_id)
                if result.get('status') == 'uploaded':
                    self._update_status(f"Uploaded to Drive: {audio_filename}", "green")
                # 'skipped' = already exists, stay silent

            except Exception as e:
                print(f"[Drive] Auto-upload error: {e}")
                # Don't show error — auto-upload is a bonus feature

        threading.Thread(target=task, daemon=True).start()

    def _show_drive_storage_dialog(self):
        """Show Drive storage management dialog with quota and old file cleanup."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Drive Storage Management")
        dialog.geometry("600x520")
        dialog.minsize(500, 400)
        dialog.transient(self)
        dialog.lift()
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(
            dialog, text="Google Drive Storage",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        # Quota display
        quota_label = ctk.CTkLabel(
            dialog, text="Loading storage info...",
            font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"]
        )
        quota_label.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        # Old files heading
        ctk.CTkLabel(
            dialog, text="Audio files older than 30 days:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")

        # Scrollable file list
        files_frame = ctk.CTkScrollableFrame(
            dialog, height=250,
            fg_color=COLORS["bg_secondary"],
            corner_radius=8
        )
        files_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="nsew")
        files_frame.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(3, weight=1)

        # Loading indicator in files frame
        loading_label = ctk.CTkLabel(
            files_frame, text="Loading files...",
            text_color=COLORS["text_muted"]
        )
        loading_label.grid(row=0, column=0, pady=20)

        # Track checkbox vars
        file_checkboxes = {}  # file_id -> BooleanVar

        # Action buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")

        btn_select_all = ctk.CTkButton(
            btn_frame, text="Select All", width=100, fg_color="gray",
            command=lambda: [v.set(True) for v in file_checkboxes.values()]
        )
        btn_select_all.pack(side="left", padx=(0, 8))

        btn_deselect = ctk.CTkButton(
            btn_frame, text="Deselect All", width=100, fg_color="gray",
            command=lambda: [v.set(False) for v in file_checkboxes.values()]
        )
        btn_deselect.pack(side="left", padx=(0, 8))

        def do_delete():
            ids = [fid for fid, var in file_checkboxes.items() if var.get()]
            if not ids:
                return
            # Simple confirmation
            confirm = ctk.CTkToplevel(dialog)
            confirm.title("Confirm Deletion")
            confirm.geometry("400x150")
            confirm.transient(dialog)
            confirm.lift()
            confirm.grab_set()
            confirm.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                confirm,
                text=f"Delete {len(ids)} file(s) from Google Drive?\nThis cannot be undone.",
                font=ctk.CTkFont(size=13),
                text_color=COLORS["text_primary"]
            ).grid(row=0, column=0, padx=20, pady=(20, 15))

            cfm_btns = ctk.CTkFrame(confirm, fg_color="transparent")
            cfm_btns.grid(row=1, column=0, padx=20, pady=(0, 20))

            def cancel():
                confirm.destroy()

            def proceed():
                confirm.destroy()

                def delete_task():
                    try:
                        from drive_manager import delete_files
                        result = delete_files(ids)
                        n = result.get('deleted', 0)
                        self.after(0, lambda: self._update_status(
                            f"Deleted {n} file(s) from Drive", "green"
                        ))
                        # Close storage dialog
                        self.after(0, dialog.destroy)
                    except Exception as e:
                        self.after(0, lambda: self._update_status(
                            f"Delete error: {str(e)[:50]}", "red"
                        ))

                threading.Thread(target=delete_task, daemon=True).start()

            ctk.CTkButton(cfm_btns, text="Cancel", fg_color="gray", width=100,
                          command=cancel).pack(side="left", padx=(0, 10))
            ctk.CTkButton(cfm_btns, text="Delete", fg_color=COLORS["danger"], width=100,
                          command=proceed).pack(side="left")

        btn_delete = ctk.CTkButton(
            btn_frame, text="Delete Selected", width=130,
            fg_color=COLORS["danger"],
            command=do_delete
        )
        btn_delete.pack(side="right")

        # Load data in background
        def load_data():
            try:
                from drive_manager import get_storage_quota, list_old_audio_files
                # Update quota
                quota = get_storage_quota()
                used_gb = quota.get('used_gb', 0)
                total_gb = quota.get('total_gb', 0)
                pct = quota.get('percent_used', 0)
                if total_gb > 0:
                    quota_text = f"Using {used_gb:.1f}GB of {total_gb:.1f}GB ({pct:.0f}%)"
                else:
                    quota_text = f"Using {used_gb:.1f}GB (unlimited plan)"
                self.after(0, lambda: quota_label.configure(text=quota_text))

                # Load old files
                old_files = list_old_audio_files(
                    root_folder_name=self.settings.get("drive_root_folder_name", "Daily Audio Briefing"),
                    before_days=30,
                    shared_folder_id=self.settings.get("drive_folder_id", "")
                )

                def populate():
                    loading_label.destroy()
                    if not old_files:
                        ctk.CTkLabel(
                            files_frame, text="No audio files older than 30 days found.",
                            text_color=COLORS["text_muted"],
                            font=ctk.CTkFont(size=12)
                        ).grid(row=0, column=0, pady=20)
                        return
                    for i, f in enumerate(old_files):
                        var = ctk.BooleanVar(value=False)
                        file_checkboxes[f['id']] = var
                        label = f"{f['name']}  ({f.get('size_mb', '?')}MB, {f.get('folder', '')})"
                        ctk.CTkCheckBox(
                            files_frame, text=label, variable=var,
                            font=ctk.CTkFont(size=11)
                        ).grid(row=i, column=0, sticky="w", padx=10, pady=1)

                self.after(0, populate)

            except Exception as e:
                err = str(e)[:60]
                self.after(0, lambda: quota_label.configure(
                    text=f"Error loading Drive info: {err}"
                ))
                self.after(0, lambda: loading_label.configure(
                    text=f"Could not connect to Drive."
                ))

        threading.Thread(target=load_data, daemon=True).start()

    def _build_home_page(self):
        """Build the Home/Dashboard page with quick actions."""
        page = self.pages["home"]

        # Welcome header
        ctk.CTkLabel(
            page, text="Daily Audio Briefing",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        ctk.CTkLabel(
            page, text="Your personalized news and content briefing tool",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"]
        ).grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        # Quick Actions card
        actions_card = self._create_card(page, title="Quick Actions")
        actions_card.grid(row=2, column=0, padx=20, pady=(0, 12), sticky="ew")

        actions_frame = ctk.CTkFrame(actions_card, fg_color="transparent")
        actions_frame.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")
        actions_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Quick action buttons
        ctk.CTkButton(
            actions_frame, text="📰  Get Summaries",
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            corner_radius=8, height=40,
            command=lambda: self._navigate_to("summarize")
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            actions_frame, text="📊  Extract Data",
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            corner_radius=8, height=40,
            command=lambda: self._navigate_to("extract")
        ).grid(row=0, column=1, padx=6, sticky="ew")

        ctk.CTkButton(
            actions_frame, text="🔊  Generate Audio",
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            corner_radius=8, height=40,
            command=lambda: self._navigate_to("audio")
        ).grid(row=0, column=2, padx=(6, 0), sticky="ew")

        # Status card
        status_card = self._create_card(page, title="System Status")
        status_card.grid(row=3, column=0, padx=20, pady=(0, 12), sticky="ew")

        status_content = ctk.CTkFrame(status_card, fg_color="transparent")
        status_content.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")
        status_content.grid_columnconfigure(1, weight=1)

        # Compression status — don't block main thread waiting for ffmpeg check.
        # Show a neutral placeholder, then update once the background thread finishes.
        self._home_ffmpeg_dot = ctk.CTkLabel(
            status_content,
            text="●",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(size=14)
        )
        self._home_ffmpeg_dot.grid(row=0, column=0, padx=(0, 8), sticky="w")
        ctk.CTkLabel(
            status_content, text="ffmpeg (audio compression)",
            font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"]
        ).grid(row=0, column=1, sticky="w")

        # Update ffmpeg dot once background pre-warm thread completes
        def _update_ffmpeg_dot():
            if _ffmpeg_cache is not None:
                color = COLORS["success"] if _ffmpeg_cache else COLORS["warning"]
                self._home_ffmpeg_dot.configure(text_color=color)
            else:
                self.after(200, _update_ffmpeg_dot)  # Check again later
        self.after(200, _update_ffmpeg_dot)

        # Open output folder button
        ctk.CTkButton(
            page, text="Open Output Folder",
            fg_color="transparent", border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["bg_tertiary"],
            corner_radius=8,
            command=self.open_output_folder
        ).grid(row=4, column=0, padx=20, pady=(0, 20))

    def _build_settings_page(self):
        """Build the Settings page (replaces modal dialog)."""
        page = self.pages["settings"]

        ctk.CTkLabel(
            page, text="Settings",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Text Scale card
        scale_card = self._create_card(page, title="Display")
        scale_card.grid(row=1, column=0, padx=20, pady=(0, 12), sticky="ew")

        scale_content = ctk.CTkFrame(scale_card, fg_color="transparent")
        scale_content.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")
        scale_content.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(scale_content, text="Text Size:", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")

        self.settings_text_scale_var = ctk.DoubleVar(value=self._current_text_scale)
        self.settings_text_scale_slider = ctk.CTkSlider(
            scale_content,
            from_=0.5, to=1.5,
            number_of_steps=20,
            variable=self.settings_text_scale_var,
            command=self._on_settings_scale_change
        )
        self.settings_text_scale_slider.grid(row=0, column=1, padx=(10, 10), sticky="ew")

        self.settings_scale_label = ctk.CTkLabel(
            scale_content,
            text=f"{int(self._current_text_scale * 100)}%",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        )
        self.settings_scale_label.grid(row=0, column=2, sticky="e")

        # System status card
        sys_card = self._create_card(page, title="System Status")
        sys_card.grid(row=2, column=0, padx=20, pady=(0, 12), sticky="ew")

        sys_content = ctk.CTkFrame(sys_card, fg_color="transparent")
        sys_content.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")

        # Show dependency statuses
        deps = [
            ("ffmpeg", _cached_check_ffmpeg(), "Audio compression"),
            ("gTTS", True, "Fast text-to-speech"),  # Always available
        ]
        # Check optional deps
        try:
            import faster_whisper
            whisper_ok = True
        except ImportError:
            whisper_ok = False
        deps.append(("Whisper", whisper_ok, "Audio transcription"))

        kokoro_path = os.path.join(get_data_directory(), "kokoro-v1.0.onnx")
        kokoro_ok = os.path.exists(kokoro_path)
        deps.append(("Kokoro", kokoro_ok, "Quality text-to-speech"))

        for i, (name, available, desc) in enumerate(deps):
            dot_color = COLORS["success"] if available else COLORS["warning"]
            ctk.CTkLabel(
                sys_content, text="●", text_color=dot_color,
                font=ctk.CTkFont(size=14)
            ).grid(row=i, column=0, padx=(0, 8), sticky="w", pady=2)
            ctk.CTkLabel(
                sys_content, text=f"{name} — {desc}",
                font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"]
            ).grid(row=i, column=1, sticky="w", pady=2)

        # Setup Wizard card
        setup_card = self._create_card(page, title="Setup")
        setup_card.grid(row=3, column=0, padx=20, pady=(0, 12), sticky="ew")

        setup_content = ctk.CTkFrame(setup_card, fg_color="transparent")
        setup_content.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")

        ctk.CTkLabel(
            setup_content,
            text="Re-run the initial setup to check or install dependencies (ffmpeg, Kokoro).",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            wraplength=500, justify="left"
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        ctk.CTkButton(
            setup_content, text="Run Setup Wizard", width=160,
            fg_color=COLORS["accent"], hover_color="#2563eb",
            command=self._show_first_run_wizard
        ).grid(row=1, column=0, sticky="w")

        # Google Drive card
        drive_card = self._create_card(page, title="Google Drive")
        drive_card.grid(row=4, column=0, padx=20, pady=(0, 12), sticky="ew")

        drive_content = ctk.CTkFrame(drive_card, fg_color="transparent")
        drive_content.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")
        drive_content.grid_columnconfigure(1, weight=1)

        # Row 0: Connection status indicator
        status_row = ctk.CTkFrame(drive_content, fg_color="transparent")
        status_row.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self.drive_status_dot = ctk.CTkLabel(
            status_row, text="●", font=ctk.CTkFont(size=14),
            text_color=COLORS["warning"]
        )
        self.drive_status_dot.pack(side="left", padx=(0, 8))

        self.drive_status_label = ctk.CTkLabel(
            status_row, text="Not configured",
            font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"]
        )
        self.drive_status_label.pack(side="left")

        # Row 1: Sign in / account info row
        sign_in_row = ctk.CTkFrame(drive_content, fg_color="transparent")
        sign_in_row.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.drive_account_label = ctk.CTkLabel(
            sign_in_row, text="Not signed in",
            font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"]
        )
        self.drive_account_label.pack(side="left", padx=(0, 12))

        self.btn_drive_sign_in = ctk.CTkButton(
            sign_in_row, text="Sign in with Google", width=160,
            fg_color="#4285f4", hover_color="#3367d6",
            command=self._drive_sign_in
        )
        self.btn_drive_sign_in.pack(side="left", padx=(0, 8))

        self.btn_drive_sign_out = ctk.CTkButton(
            sign_in_row, text="Sign Out", width=80,
            fg_color="gray", hover_color=COLORS["danger"],
            command=self._drive_sign_out
        )
        self.btn_drive_sign_out.pack(side="left")

        # Show current sign-in state
        try:
            from drive_manager import is_signed_in, get_user_email
            if is_signed_in():
                email = get_user_email()
                if email:
                    self.drive_account_label.configure(
                        text=f"Signed in as {email}", text_color=COLORS["success"])
                else:
                    self.drive_account_label.configure(
                        text="Signed in", text_color=COLORS["success"])
                self.btn_drive_sign_in.configure(state="disabled")
            else:
                self.btn_drive_sign_out.configure(state="disabled")
        except Exception:
            self.btn_drive_sign_out.configure(state="disabled")

        # Row 2: Drive folder URL/ID input
        ctk.CTkLabel(
            drive_content, text="Drive Folder URL or ID:",
            font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"]
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 2))

        folder_input_row = ctk.CTkFrame(drive_content, fg_color="transparent")
        folder_input_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        folder_input_row.grid_columnconfigure(0, weight=1)

        self.drive_folder_entry = ctk.CTkEntry(
            folder_input_row, placeholder_text="Paste Drive folder URL or ID...",
            font=ctk.CTkFont(size=12), height=32
        )
        self.drive_folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        # Pre-fill saved folder ID
        saved_folder = self.settings.get("drive_folder_id", "")
        if saved_folder:
            self.drive_folder_entry.insert(0, saved_folder)

        ctk.CTkButton(
            folder_input_row, text="Save", width=70,
            fg_color=COLORS["accent"], hover_color="#2563eb",
            command=self._save_drive_folder
        ).grid(row=0, column=1)

        # Folder status label (shows folder name after verification)
        self.drive_folder_status = ctk.CTkLabel(
            drive_content, text="",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]
        )
        self.drive_folder_status.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 8))

        # Row 5: Auto-upload toggle
        self.drive_auto_upload_var = ctk.BooleanVar(
            value=self.settings.get("drive_auto_upload", False)
        )
        self.drive_auto_upload_switch = ctk.CTkSwitch(
            drive_content, text="Auto-upload after audio generation",
            variable=self.drive_auto_upload_var,
            command=self._on_drive_auto_upload_toggle,
            font=ctk.CTkFont(size=12)
        )
        self.drive_auto_upload_switch.grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 8))

        # Row 6: Action buttons
        drive_btn_frame = ctk.CTkFrame(drive_content, fg_color="transparent")
        drive_btn_frame.grid(row=6, column=0, columnspan=2, sticky="w")

        ctk.CTkButton(
            drive_btn_frame, text="Test Connection", width=130,
            fg_color=COLORS["accent"], hover_color="#2563eb",
            command=self._test_drive_connection
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            drive_btn_frame, text="Manage Storage", width=130,
            fg_color="gray",
            command=self._show_drive_storage_dialog
        ).pack(side="left", padx=(0, 8))

        # ── API Usage & Limits card ──
        usage_card = self._create_card(page, title="API Usage & Limits")
        usage_card.grid(row=5, column=0, padx=20, pady=(0, 12), sticky="ew")

        usage_content = ctk.CTkFrame(usage_card, fg_color="transparent")
        usage_content.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")
        usage_content.grid_columnconfigure(1, weight=1)

        # Daily usage
        self.usage_daily_label = ctk.CTkLabel(
            usage_content, text="Today: 0 / 500 calls",
            font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"]
        )
        self.usage_daily_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))

        self.usage_daily_bar = ctk.CTkProgressBar(usage_content, height=12)
        self.usage_daily_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.usage_daily_bar.set(0)

        # Monthly usage
        self.usage_monthly_label = ctk.CTkLabel(
            usage_content, text="Month: 0 / 10,000 calls",
            font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"]
        )
        self.usage_monthly_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 2))

        self.usage_monthly_bar = ctk.CTkProgressBar(usage_content, height=12)
        self.usage_monthly_bar.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.usage_monthly_bar.set(0)

        # Cost estimate
        self.usage_cost_label = ctk.CTkLabel(
            usage_content, text="Est. cost today: $0.00  |  Month: $0.00",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]
        )
        self.usage_cost_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 10))

        # Limits controls
        limits_sep = ctk.CTkLabel(
            usage_content, text="Limits",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text_muted"]
        )
        limits_sep.grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self.usage_limits_var = ctk.BooleanVar(
            value=self.settings.get("api_limits_enabled", True)
        )
        ctk.CTkSwitch(
            usage_content, text="Enable usage limits",
            variable=self.usage_limits_var,
            font=ctk.CTkFont(size=12)
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 8))

        limits_row = ctk.CTkFrame(usage_content, fg_color="transparent")
        limits_row.grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ctk.CTkLabel(limits_row, text="Daily:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 4))
        self.usage_daily_limit_entry = ctk.CTkEntry(limits_row, width=70, height=28, font=ctk.CTkFont(size=12))
        self.usage_daily_limit_entry.pack(side="left", padx=(0, 16))
        self.usage_daily_limit_entry.insert(0, str(self.settings.get("api_daily_limit", 500)))

        ctk.CTkLabel(limits_row, text="Monthly:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 4))
        self.usage_monthly_limit_entry = ctk.CTkEntry(limits_row, width=80, height=28, font=ctk.CTkFont(size=12))
        self.usage_monthly_limit_entry.pack(side="left")
        self.usage_monthly_limit_entry.insert(0, str(self.settings.get("api_monthly_limit", 10000)))

        # Buttons row
        usage_btn_frame = ctk.CTkFrame(usage_content, fg_color="transparent")
        usage_btn_frame.grid(row=8, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ctk.CTkButton(
            usage_btn_frame, text="Save Limits", width=100,
            fg_color=COLORS["accent"], hover_color="#2563eb",
            command=self._save_usage_limits
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            usage_btn_frame, text="Reset Today", width=100,
            fg_color="gray", hover_color=COLORS["warning"],
            command=self._reset_usage_today
        ).pack(side="left")

        # Per-task breakdown label
        self.usage_tasks_label = ctk.CTkLabel(
            usage_content, text="",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"],
            justify="left", anchor="w"
        )
        self.usage_tasks_label.grid(row=9, column=0, columnspan=2, sticky="w")

        # ── Budget Cap section ──
        budget_sep = ctk.CTkLabel(
            usage_content, text="Monthly Budget Cap",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text_muted"]
        )
        budget_sep.grid(row=10, column=0, columnspan=2, sticky="w", pady=(12, 4))

        budget_row = ctk.CTkFrame(usage_content, fg_color="transparent")
        budget_row.grid(row=11, column=0, columnspan=2, sticky="w", pady=(0, 4))

        ctk.CTkLabel(budget_row, text="$", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 2))
        self.budget_cap_entry = ctk.CTkEntry(budget_row, width=80, height=28, font=ctk.CTkFont(size=12))
        self.budget_cap_entry.pack(side="left", padx=(0, 4))
        self.budget_cap_entry.insert(0, str(self.settings.get("api_budget_usd", "0.00")))
        ctk.CTkLabel(budget_row, text="USD/month", font=ctk.CTkFont(size=11),
                     text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 16))

        self.cooldown_var = ctk.BooleanVar(
            value=self.settings.get("api_cooldown_enabled", True)
        )
        ctk.CTkSwitch(
            budget_row, text="Cooldown mode",
            variable=self.cooldown_var,
            font=ctk.CTkFont(size=12)
        ).pack(side="left")

        # Budget progress bar
        self.budget_bar = ctk.CTkProgressBar(usage_content, height=12)
        self.budget_bar.grid(row=12, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        self.budget_bar.set(0)

        # Budget status label
        self.budget_status_label = ctk.CTkLabel(
            usage_content, text="No budget cap set (0 = unlimited)",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]
        )
        self.budget_status_label.grid(row=13, column=0, columnspan=2, sticky="w", pady=(0, 4))

        # Cooldown active indicator (hidden by default)
        self.cooldown_indicator = ctk.CTkLabel(
            usage_content,
            text="⚠ Cooldown active — AI summarization paused",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS.get("warning", "#f59e0b")
        )
        self.cooldown_indicator.grid(row=14, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self.cooldown_indicator.grid_remove()  # Hidden until needed

    def _on_settings_scale_change(self, value):
        """Handle text scale slider change on Settings page."""
        pct = int(value * 100)
        if hasattr(self, 'settings_scale_label'):
            self.settings_scale_label.configure(text=f"{pct}%")
        self._current_text_scale = value
        self._apply_text_scale()
        # Save to settings
        self.settings['text_scale'] = value
        self._save_settings()

    def _build_cloud_scheduler_card(self):
        """Build the Cloud Scheduler connection card on the Scheduler page."""
        cloud_card = self._create_card(self.pages["scheduler"], title="Cloud Scheduler")
        cloud_card.grid(row=2, column=0, padx=20, pady=(0, 12), sticky="ew")

        cloud_content = ctk.CTkFrame(cloud_card, fg_color="transparent")
        cloud_content.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")
        cloud_content.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            cloud_content,
            text="Connect to your cloud server for 24/7 scheduling",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        # Server URL
        ctk.CTkLabel(
            cloud_content, text="Server URL:",
            font=ctk.CTkFont(size=12)
        ).grid(row=1, column=0, sticky="w", padx=(0, 8))

        default_url = self.settings.get('server_url', '')
        self.cloud_url_entry = ctk.CTkEntry(
            cloud_content, placeholder_text="https://your-app.onrender.com",
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            corner_radius=8
        )
        self.cloud_url_entry.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        if default_url:
            self.cloud_url_entry.insert(0, default_url)

        # Test Connection button
        self.btn_test_cloud = ctk.CTkButton(
            cloud_content, text="Test Connection",
            width=130, corner_radius=8,
            fg_color=COLORS["bg_tertiary"],
            border_width=1, border_color=COLORS["border"],
            hover_color=COLORS["accent"],
            command=self._test_cloud_connection
        )
        self.btn_test_cloud.grid(row=1, column=2, sticky="e")

        # Connection status
        self.cloud_status_label = ctk.CTkLabel(
            cloud_content, text="● Not connected",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.cloud_status_label.grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))

        # Mode selector
        mode_frame = ctk.CTkFrame(cloud_content, fg_color="transparent")
        mode_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0))

        ctk.CTkLabel(
            mode_frame, text="Scheduler Mode:",
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(0, 12))

        self._scheduler_mode = "local"
        self.scheduler_mode_seg = ctk.CTkSegmentedButton(
            mode_frame,
            values=["Local", "Cloud"],
            command=self._on_scheduler_mode_change,
            font=ctk.CTkFont(size=12),
            corner_radius=8
        )
        self.scheduler_mode_seg.set("Local")
        self.scheduler_mode_seg.pack(side="left")

        # Cloud client (initialized when needed)
        self._cloud_client = None

    def _test_cloud_connection(self):
        """Test connection to the cloud scheduler server."""
        url = self.cloud_url_entry.get().strip()
        if not url:
            self.cloud_status_label.configure(
                text="● Enter a server URL first",
                text_color=COLORS["warning"]
            )
            return

        # Save URL to settings
        self.settings['server_url'] = url
        self._save_settings()

        self.cloud_status_label.configure(
            text="● Testing...",
            text_color=COLORS["text_muted"]
        )
        self.btn_test_cloud.configure(state="disabled")

        def _test():
            from cloud_scheduler_client import CloudSchedulerClient
            api_key = self.settings.get('server_api_key', '')
            client = CloudSchedulerClient(url, api_key=api_key or None)
            ok, msg = client.test_connection()
            if ok:
                self._cloud_client = client
                client.refresh_tasks()
            self.after(0, lambda: self._on_cloud_test_result(ok, msg))

        threading.Thread(target=_test, daemon=True).start()

    def _on_cloud_test_result(self, ok: bool, msg: str):
        """Handle cloud connection test result (called on main thread)."""
        self.btn_test_cloud.configure(state="normal")
        if ok:
            task_count = len(self._cloud_client.tasks) if self._cloud_client else 0
            self.cloud_status_label.configure(
                text=f"● Connected — {task_count} task{'s' if task_count != 1 else ''}",
                text_color=COLORS["success"]
            )
        else:
            self.cloud_status_label.configure(
                text=f"● {msg}",
                text_color=COLORS["danger"]
            )

    def _on_scheduler_mode_change(self, value):
        """Handle Local/Cloud mode switch."""
        mode = value.lower()
        if mode == self._scheduler_mode:
            return

        if mode == "cloud" and not self._cloud_client:
            # Must test connection first
            self.cloud_status_label.configure(
                text="● Test connection first before switching to Cloud mode",
                text_color=COLORS["warning"]
            )
            self.scheduler_mode_seg.set("Local")
            return

        self._scheduler_mode = mode
        self._refresh_scheduler_tasks()

    def _get_active_scheduler(self):
        """Return the active scheduler backend (local or cloud)."""
        if self._scheduler_mode == "cloud" and self._cloud_client:
            return self._cloud_client
        return self._scheduler

    def _handle_launch_url(self, url_string: str):
        """Handle a dailybriefing:// URL scheme invocation.

        Called either at startup (from sys.argv) or at runtime
        (from ::tk::mac::LaunchURL when app is already running).
        """
        params = parse_briefing_url(url_string)
        if not params or not params.get('action'):
            return

        action = params['action']

        if action == 'connect':
            server_url = params.get('server', '')
            if not server_url:
                return

            # Navigate to scheduler page
            self._navigate_to('scheduler')

            # Populate the server URL entry
            if hasattr(self, 'cloud_url_entry'):
                self.cloud_url_entry.delete(0, 'end')
                self.cloud_url_entry.insert(0, server_url)

            # Save to settings
            self.settings['server_url'] = server_url
            self._save_settings()

            # Auto-test connection after a short delay (let UI update)
            self.after(200, self._test_cloud_connection)

            # Update status
            if hasattr(self, 'cloud_status_label'):
                self.cloud_status_label.configure(
                    text="Connecting via desktop link...",
                    text_color=COLORS["accent"]
                )

    def _build_guide_page(self):
        """Build the Guide/Help page."""
        page = self.pages["guide"]

        ctk.CTkLabel(
            page, text="Guide",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Alpha warning
        alpha_card = ctk.CTkFrame(
            page, fg_color="#3f3a1e", corner_radius=12,
            border_width=1, border_color="#665c1e"
        )
        alpha_card.grid(row=1, column=0, padx=20, pady=(0, 12), sticky="ew")
        alpha_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            alpha_card,
            text="⚠️  Alpha Version — Features may change. Report issues on GitHub.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["warning"],
            wraplength=600
        ).grid(row=0, column=0, padx=16, pady=12, sticky="w")

        # Getting Started card
        gs_card = self._create_card(page, title="Getting Started")
        gs_card.grid(row=2, column=0, padx=20, pady=(0, 12), sticky="ew")

        steps = [
            "1. Set your Gemini API key in Settings or on the Summarize page",
            "2. Configure your YouTube/RSS sources via the Summarize page",
            "3. Click 'Get Summaries' to fetch and summarize content",
            "4. Switch to Audio to generate a spoken briefing",
            "5. Use Scheduler to automate extraction on a schedule",
        ]
        gs_content = ctk.CTkFrame(gs_card, fg_color="transparent")
        gs_content.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")
        for i, step in enumerate(steps):
            ctk.CTkLabel(
                gs_content, text=step,
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"],
                wraplength=600, justify="left"
            ).grid(row=i, column=0, sticky="w", pady=2)

        # Pages overview card
        pages_card = self._create_card(page, title="Pages")
        pages_card.grid(row=3, column=0, padx=20, pady=(0, 12), sticky="ew")

        pages_info = [
            ("📰 Summarize", "Fetch and summarize content from YouTube, RSS, and article sources"),
            ("📊 Extract", "Extract structured data from newsletters and web pages"),
            ("🔊 Audio", "Convert text to audio using gTTS (fast) or Kokoro (quality)"),
            ("📅 Scheduler", "Automate extraction tasks on a schedule with Google Sheets export"),
            ("⚙️ Settings", "Configure API keys, text size, and system dependencies"),
        ]
        pi_content = ctk.CTkFrame(pages_card, fg_color="transparent")
        pi_content.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")
        pi_content.grid_columnconfigure(1, weight=1)
        for i, (name, desc) in enumerate(pages_info):
            ctk.CTkLabel(
                pi_content, text=name,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=COLORS["text_primary"]
            ).grid(row=i, column=0, sticky="w", padx=(0, 12), pady=3)
            ctk.CTkLabel(
                pi_content, text=desc,
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"],
                wraplength=500, justify="left"
            ).grid(row=i, column=1, sticky="w", pady=3)

        # Roadmap card
        roadmap_card = self._create_card(page, title="Roadmap")
        roadmap_card.grid(row=4, column=0, padx=20, pady=(0, 12), sticky="ew")

        roadmap_phases = [
            ("1. Alpha (Current)",
             "Admin-hosted. API keys and credentials managed centrally. macOS desktop app only."),
            ("2. User Accounts",
             "Login system. Per-user API keys and Google credentials. Windows desktop build."),
            ("3. Full Cloud",
             "Server-side audio generation. All features available via web browser."),
            ("4. SaaS",
             "Multi-tenant platform. Per-user billing, subscription tiers, mobile apps."),
        ]
        rm_content = ctk.CTkFrame(roadmap_card, fg_color="transparent")
        rm_content.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")
        for i, (phase, desc) in enumerate(roadmap_phases):
            ctk.CTkLabel(
                rm_content, text=phase,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=COLORS["text_primary"]
            ).grid(row=i*2, column=0, sticky="w", pady=(6 if i > 0 else 0, 0))
            ctk.CTkLabel(
                rm_content, text=desc,
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"],
                wraplength=600, justify="left"
            ).grid(row=i*2+1, column=0, sticky="w", pady=(0, 2))

    def _show_first_run_wizard(self):
        """Show a first-run setup wizard for dependency installation."""
        import webbrowser
        global _ffmpeg_cache

        wiz = ctk.CTkToplevel(self)
        wiz.title("Setup Wizard")
        wiz.geometry("550x620")
        wiz.transient(self)
        wiz.grab_set()
        wiz.lift()
        wiz.attributes('-topmost', True)
        wiz.resizable(False, False)

        # Main container with padding
        container = ctk.CTkFrame(wiz, fg_color=COLORS["bg_primary"])
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Welcome header
        ctk.CTkLabel(
            container, text=f"Welcome to Daily Audio Briefing",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(
            container, text=f"Version {APP_VERSION}",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", pady=(0, 16))

        # Description
        ctk.CTkLabel(
            container,
            text="The app works out of the box, but installing these optional\n"
                 "dependencies unlocks advanced features:",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
            justify="left"
        ).pack(anchor="w", pady=(0, 16))

        # Dependency checklist card
        dep_card = ctk.CTkFrame(container, fg_color=COLORS["bg_secondary"], corner_radius=12,
                                border_width=1, border_color=COLORS["border"])
        dep_card.pack(fill="x", pady=(0, 12))
        dep_card.grid_columnconfigure(1, weight=1)

        # --- ffmpeg ---
        ffmpeg_ok = _cached_check_ffmpeg()
        dot_color = COLORS["success"] if ffmpeg_ok else COLORS["warning"]
        status_text = "Installed" if ffmpeg_ok else "Not found"

        ctk.CTkLabel(dep_card, text="●", text_color=dot_color,
                      font=ctk.CTkFont(size=16)).grid(row=0, column=0, padx=(16, 8), pady=(16, 4), sticky="w")
        ctk.CTkLabel(dep_card, text="ffmpeg — Audio Compression",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      text_color=COLORS["text_primary"]).grid(row=0, column=1, pady=(16, 4), sticky="w")
        ctk.CTkLabel(dep_card, text=f"Status: {status_text}. Compresses audio files to smaller MP3 format.",
                      font=ctk.CTkFont(size=11),
                      text_color=COLORS["text_secondary"]).grid(row=1, column=1, sticky="w", pady=(0, 4))
        if not ffmpeg_ok:
            ctk.CTkButton(dep_card, text="Open Download Page", width=140,
                          fg_color=COLORS["accent"], hover_color="#2563eb",
                          command=lambda: webbrowser.open("https://ffmpeg.org/download.html")
                          ).grid(row=2, column=1, sticky="w", pady=(0, 12))
        else:
            ctk.CTkLabel(dep_card, text="✓ Ready to use",
                          font=ctk.CTkFont(size=11), text_color=COLORS["success"]
                          ).grid(row=2, column=1, sticky="w", pady=(0, 12))

        # --- Kokoro ---
        kokoro_path = os.path.join(get_data_directory(), "kokoro-v1.0.onnx")
        kokoro_ok = os.path.exists(kokoro_path)
        dot_color_k = COLORS["success"] if kokoro_ok else COLORS["warning"]
        status_text_k = "Installed" if kokoro_ok else "Not found"

        ctk.CTkLabel(dep_card, text="●", text_color=dot_color_k,
                      font=ctk.CTkFont(size=16)).grid(row=3, column=0, padx=(16, 8), pady=(8, 4), sticky="w")
        ctk.CTkLabel(dep_card, text="Kokoro Model — Quality Text-to-Speech",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      text_color=COLORS["text_primary"]).grid(row=3, column=1, pady=(8, 4), sticky="w")
        ctk.CTkLabel(dep_card, text=f"Status: {status_text_k}. Natural-sounding neural voice (vs. robotic gTTS).",
                      font=ctk.CTkFont(size=11),
                      text_color=COLORS["text_secondary"]).grid(row=4, column=1, sticky="w", pady=(0, 4))
        if not kokoro_ok:
            ctk.CTkButton(dep_card, text="Open Download Page", width=140,
                          fg_color=COLORS["accent"], hover_color="#2563eb",
                          command=lambda: webbrowser.open("https://github.com/thewh1teagle/kokoro-onnx/releases")
                          ).grid(row=5, column=1, sticky="w", pady=(0, 16))
        else:
            ctk.CTkLabel(dep_card, text="✓ Ready to use",
                          font=ctk.CTkFont(size=11), text_color=COLORS["success"]
                          ).grid(row=5, column=1, sticky="w", pady=(0, 16))

        # What happens without them
        ctk.CTkLabel(
            container,
            text="Without ffmpeg: audio files will be larger (WAV instead of MP3).\n"
                 "Without Kokoro: only the fast gTTS voice is available.",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            justify="left"
        ).pack(anchor="w", pady=(0, 12))

        # Privacy note
        privacy_frame = ctk.CTkFrame(container, fg_color="#1a2332", corner_radius=8)
        privacy_frame.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(
            privacy_frame,
            text="🔒 Privacy: All processing happens on your device. Only the Gemini API\n"
                 "key is used for external API calls. No data is shared without your knowledge.",
            font=ctk.CTkFont(size=11),
            text_color="#7cb3e0",
            justify="left"
        ).pack(padx=12, pady=10)

        # Buttons
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x")

        def finish_wizard():
            """Save first_run_completed and close."""
            global _ffmpeg_cache
            self.settings["first_run_completed"] = True
            self._save_settings()
            # Invalidate ffmpeg cache so Settings page re-checks after potential install
            _ffmpeg_cache = None
            wiz.destroy()

        ctk.CTkButton(
            btn_frame, text="Continue", width=120,
            fg_color=COLORS["accent"], hover_color="#2563eb",
            command=finish_wizard
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_frame, text="Skip for Now", width=120,
            fg_color="gray", hover_color="#555555",
            command=finish_wizard
        ).pack(side="right")

    def _init_tooltips(self):
        """Initialize tooltips for all buttons in the application.

        Uses _safe_tooltip() to guard against missing widgets — deferred page
        builds might not have created all widgets if an error occurred.
        """
        def _safe_tooltip(attr_name, text):
            widget = getattr(self, attr_name, None)
            if widget is not None:
                add_tooltip(widget, text)

        # News Summary section
        _safe_tooltip("btn_fetch_article",
            "Fetch article content from a URL and add it to the text area. Useful for importing news articles.")
        _safe_tooltip("btn_settings",
            "Open application settings including output folder and default options.")
        # text_toggle_btn removed — text area always visible on Summarize page

        # API Key section
        _safe_tooltip("btn_save_key",
            "Save your Gemini API key for future sessions.")
        _safe_tooltip("btn_toggle_key",
            "Show or hide the API key text.")
        _safe_tooltip("btn_key_manager",
            "Manage multiple API keys for different services.")
        _safe_tooltip("model_combo",
            "Select AI model quality. Fast: Quick responses, high limits. Balanced: Better quality. Best: Highest quality but limited to 50/day.")

        # YouTube/Content section
        _safe_tooltip("btn_get_summaries",
            "Fetch summaries from your configured sources (YouTube, RSS, article archives).")
        _safe_tooltip("btn_edit_sources",
            "Add or edit your content sources (YouTube channels, RSS feeds, article archives).")
        _safe_tooltip("btn_edit_instructions",
            "Customize the AI instructions for how summaries should be generated.")
        _safe_tooltip("btn_upload_file",
            "Upload a text file (.txt) to load into the News Summary area.")

        # Transcription tooltips
        _safe_tooltip("btn_upload_audio",
            "Upload audio/video files (.mp3, .wav, .m4a) for transcription.")
        _safe_tooltip("btn_clear_selected",
            "Clear the currently selected audio file.")
        _safe_tooltip("btn_transcribe",
            "Transcribe the selected audio file to text using AI (requires faster-whisper).")
        # btn_specific_urls tooltip removed - button consolidated into textbox
        _safe_tooltip("btn_start_cal",
            "Open calendar to select start date.")
        _safe_tooltip("btn_end_cal",
            "Open calendar to select end date.")
        _safe_tooltip("chk_range",
            "Enable to filter by specific date range instead of number of days/videos.")

        # Audio Generation section
        _safe_tooltip("btn_fast",
            "Generate audio quickly using Google Text-to-Speech. Free and fast, but lower quality voice.")
        _safe_tooltip("btn_fast_sample",
            "Play a sample of gTTS to hear what the fast voice sounds like.")
        _safe_tooltip("btn_sample",
            "Play a sample of the selected Kokoro voice.")
        _safe_tooltip("btn_convert_dates",
            "Select specific dates from your summaries and convert them to audio files.")
        _safe_tooltip("btn_quality",
            "Generate high-quality audio using Kokoro TTS. Better voice quality but requires more processing.")

        # Data Extractor section
        _safe_tooltip("btn_tab_url",
            "INPUT MODE: Extract from URL(s). Click to select this mode. Paste newsletter URLs and the app will fetch and extract content.")
        _safe_tooltip("btn_tab_html",
            "INPUT MODE: Paste HTML. Click to select this mode. Paste raw HTML source code directly (useful when URL fetching fails).")
        _safe_tooltip("extract_config_combo",
            "Select extraction config. 'ExecSum' is optimized for finance newsletters with trained filters.")
        _safe_tooltip("chk_grid_enrich",
            "Enrich extracted items with additional data from The Grid database.\n(Not available with ExecSum config - uses separate processor)")
        _safe_tooltip("chk_research_articles",
            "Use AI to research and categorize each extracted article.\n(Not available with ExecSum config - uses separate processor)")
        _safe_tooltip("btn_extract",
            "Extract links and headlines from the pasted URL(s). Auto-detects URLs from any format - paste messy text, it will find them.")
        _safe_tooltip("btn_export_csv",
            "Save extracted items to a CSV file.")
        _safe_tooltip("btn_export_sheets",
            "Export extracted items directly to a Google Sheet.")
        _safe_tooltip("btn_copy_text",
            "Copy all extracted items to clipboard.")

        # Fetch options
        _safe_tooltip("entry_value",
            "Enter the number of hours, days, or videos to fetch summaries for.")
        _safe_tooltip("combo_mode",
            "Select the time unit: Hours (recent), Days (by date), or Videos (count per channel).")
        _safe_tooltip("start_date_entry",
            "Start date for date range filtering (format: YYYY-MM-DD).")
        _safe_tooltip("end_date_entry",
            "End date for date range filtering (format: YYYY-MM-DD).")

        # Audio section
        _safe_tooltip("combo_voices",
            "Select the Kokoro TTS voice for quality audio generation.")

        # URL banner buttons
        _safe_tooltip("btn_toggle_view",
            "Toggle between raw text and AI-cleaned text suitable for audio.")
        _safe_tooltip("btn_fetch_urls",
            "Fetch and summarize content from detected article URLs.")
        _safe_tooltip("btn_ignore_urls",
            "Keep URLs as plain text without fetching their content.")
        _safe_tooltip("btn_extract_data",
            "Extract structured data from newsletter URLs using the matching extraction config.")

        # Data Extractor extras
        _safe_tooltip("btn_manage_configs",
            "Open the Config Manager to create, edit, or delete extraction configurations.")

        # Scheduler section
        _safe_tooltip("btn_add_task",
            "Create a new scheduled extraction task.")
        _safe_tooltip("scheduler_mode_seg",
            "Switch between Local scheduler (runs on this Mac) and Cloud scheduler (runs on Render server).")
        _safe_tooltip("_task_log_toggle",
            "Expand or collapse the task execution log.")
        _safe_tooltip("_task_log_copy",
            "Copy the task log to clipboard.")
        _safe_tooltip("_task_log_clear",
            "Clear the task log.")
        _safe_tooltip("_task_log_stop",
            "Stop a running backfill operation after the current post finishes.")

        # Bottom buttons
        _safe_tooltip("btn_open",
            "Open the folder where generated audio files and summaries are saved.")

    def _update_status(self, message, color="gray"):
        """Callback for status updates from managers.

        Updates both Summarize page and Audio page status labels.

        Args:
            message: Status message to display
            color: Text color for the message
        """
        if self.label_status:
            self.after(0, lambda m=message, c=color: self.label_status.configure(text=m, text_color=c))
        if self.label_audio_status:
            self.after(0, lambda m=message, c=color: self.label_audio_status.configure(text=m, text_color=c))
    
    def on_mode_changed(self, *args):
        """Handle mode dropdown changes (Hours/Days/Videos)."""
        # Re-enable date range controls
        self.chk_range.configure(state="normal")
        if not self.range_var.get():
            self.entry_value.configure(state="normal")
            self.combo_mode.configure(state="normal")
            
            # Restore normal placeholder
            self.entry_value.configure(placeholder_text="")
            if not self.entry_value.get():
                self.entry_value.insert(0, "7")

    def on_extract_config_changed(self, config_name):
        """Handle extraction config dropdown changes. Disable Grid/Research checkboxes for ExecSum."""
        is_execsum = config_name.lower() == "execsum"

        if is_execsum:
            # Disable and uncheck the checkboxes for ExecSum
            self.grid_enrich_var.set(False)
            self.research_articles_var.set(False)
            self.chk_grid_enrich.configure(state="disabled")
            self.chk_research_articles.configure(state="disabled")
        else:
            # Re-enable checkboxes for other configs
            self.chk_grid_enrich.configure(state="normal")
            self.chk_research_articles.configure(state="normal")

    def on_toggle_range(self):
        use_range = bool(self.range_var.get())
        state = "disabled" if use_range else "normal"
        try:
            self.entry_value.configure(state=state)
            self.combo_mode.configure(state=state)
        except Exception:
            pass

    def _open_calendar_for(self, target_entry):
        import calendar as _cal
        dlg = ctk.CTkToplevel(self)
        dlg.title("Select Date")
        dlg.geometry("420x420")
        dlg.transient(self)  # Owned by main window — proper z-layering on macOS
        dlg.grab_set()  # Make modal - prevents events from passing to underlying widgets
        dlg.lift()
        dlg.attributes('-topmost', True)
        dlg.resizable(False, False)
        body = ctk.CTkFrame(dlg); body.pack(fill="both", expand=True, padx=10, pady=10)
        top = ctk.CTkFrame(body); top.pack(fill="x")
        today = datetime.date.today()
        ent_y = ctk.CTkEntry(top, width=70); ent_y.pack(side="left", padx=4); ent_y.insert(0, str(today.year))
        ent_m = ctk.CTkEntry(top, width=50); ent_m.pack(side="left", padx=4); ent_m.insert(0, str(today.month))
        grid = ctk.CTkFrame(body); grid.pack(fill="both", expand=True, pady=8)
        sel = [None]
        def render():
            for w in grid.winfo_children(): w.destroy()
            try:
                y = int(ent_y.get()); m = int(ent_m.get())
            except: return
            cal = _cal.monthcalendar(y, m)
            hdr = ["Mo","Tu","We","Th","Fr","Sa","Su"]
            for i,h in enumerate(hdr): ctk.CTkLabel(grid, text=h).grid(row=0, column=i, padx=4, pady=2)
            def click_day(d):
                if d == 0: return
                sel[0] = datetime.date(y,m,d)
                target_entry.delete(0, "end"); target_entry.insert(0, sel[0].isoformat())
                self.range_var.set(True); self.on_toggle_range(); dlg.destroy()
            for r,row in enumerate(cal, start=1):
                for c,d in enumerate(row):
                    txt = "" if d==0 else str(d)
                    ctk.CTkButton(grid, text=txt or " ", width=36, command=(lambda dd=d: click_day(dd))).grid(row=r, column=c, padx=2, pady=2)
        render()
        bar = ctk.CTkFrame(body); bar.pack(fill="x", pady=6)
        def go_prev():
            m = int(ent_m.get())
            y = int(ent_y.get())
            if m == 1:
                m = 12
                y -= 1
            else:
                m -= 1
            ent_m.delete(0, "end"); ent_m.insert(0, str(m))
            ent_y.delete(0, "end"); ent_y.insert(0, str(y))
            render()
        def go_next():
            m = int(ent_m.get())
            y = int(ent_y.get())
            if m == 12:
                m = 1
                y += 1
            else:
                m += 1
            ent_m.delete(0, "end"); ent_m.insert(0, str(m))
            ent_y.delete(0, "end"); ent_y.insert(0, str(y))
            render()
        ctk.CTkButton(bar, text="Prev", command=go_prev).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Next", command=go_next).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Close", fg_color="gray", command=dlg.destroy).pack(side="right", padx=6)

    def open_start_calendar(self):
        self._open_calendar_for(self.start_date_entry)

    def open_end_calendar(self):
        self._open_calendar_for(self.end_date_entry)


        # Google Sign-In (disabled)
        # self.btn_google_signin = ctk.CTkButton(self.frame_audio_controls, text="Sign in to Google", fg_color="#4285F4", command=self.sign_in_google)
        # self.btn_google_signin.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

    def load_current_summary(self):
        """Load current summary from file into textbox."""
        content = self.file_manager.load_summary()
        if content:
            self.textbox.delete("0.0", "end")
            self.textbox.insert("0.0", content)

    def load_api_key(self):
        """Load API key from file into entry widget."""
        key = self.file_manager.load_api_key()
        if key:
            self.gemini_key_entry.delete(0, "end")
            self.gemini_key_entry.insert(0, key)

    def save_api_key(self, key):
        """Save API key to file.

        Args:
            key: API key to save
        """
        print(f"[API Key] Saving key: {'*' * (len(key) - 4) + key[-4:] if len(key) > 4 else '(empty)'}")
        try:
            self.file_manager.save_api_key(key)
            print(f"[API Key] Saved successfully")
            # Visual feedback - flash the button green and show checkmark
            self.btn_save_key.configure(fg_color="green", text="✓")
            # Also flash the entry border green
            self.gemini_key_entry.configure(border_color="green")
            # Update status if it exists
            if hasattr(self, 'label_status'):
                self.label_status.configure(text="API key saved!", text_color="green")
            # Reset after 1.5 seconds
            def reset_visual():
                self.btn_save_key.configure(fg_color=("#3B8ED0", "#1F6AA5"), text="💾")
                self.gemini_key_entry.configure(border_color=("#979DA2", "#565B5E"))
            self.after(1500, reset_visual)
        except Exception as e:
            print(f"[API Key] Error saving: {e}")
            self.btn_save_key.configure(fg_color="red", text="✗")
            if hasattr(self, 'label_status'):
                self.label_status.configure(text=f"Error saving API key: {e}", text_color="red")
            self.after(1500, lambda: self.btn_save_key.configure(fg_color=("#3B8ED0", "#1F6AA5"), text="💾"))

    def toggle_api_key_visibility(self):
        """Toggle showing/hiding the API key."""
        current_show = self.gemini_key_entry.cget("show")
        if current_show == "*":
            self.gemini_key_entry.configure(show="")
            self.btn_toggle_key.configure(text="🙈")
            print("[API Key] Visibility: shown")
        else:
            self.gemini_key_entry.configure(show="*")
            self.btn_toggle_key.configure(text="👁")
            print("[API Key] Visibility: hidden")

    def open_api_key_manager(self):
        """Open the API Key Manager popup window."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("API Key Manager")
        dialog.geometry("450x250")
        dialog.transient(self)
        dialog.grab_set()
        dialog.lift()

        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (450 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (250 // 2)
        dialog.geometry(f"450x250+{x}+{y}")

        # Current key display
        ctk.CTkLabel(dialog, text="Current API Key:", font=ctk.CTkFont(weight="bold")).pack(pady=(20, 5))

        current_key = self.gemini_key_entry.get().strip()
        if current_key:
            masked_key = f"{current_key[:8]}...{current_key[-4:]}" if len(current_key) > 12 else "****"
        else:
            masked_key = "(No key saved)"

        key_label = ctk.CTkLabel(dialog, text=masked_key, font=ctk.CTkFont(family="Courier"))
        key_label.pack(pady=(0, 15))

        # Key file location
        key_file = os.path.join(os.path.dirname(__file__), "gemini_api_key.txt")
        ctk.CTkLabel(dialog, text=f"Stored in: {os.path.basename(key_file)}", text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=(0, 20))

        # Buttons frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        def clear_key():
            """Clear the API key."""
            self.gemini_key_entry.delete(0, "end")
            try:
                if os.path.exists(key_file):
                    os.remove(key_file)
                print("[API Key] Cleared")
                key_label.configure(text="(No key saved)")
                if hasattr(self, 'label_status'):
                    self.label_status.configure(text="API key cleared", text_color="orange")
            except Exception as e:
                print(f"[API Key] Error clearing: {e}")

        def copy_key():
            """Copy the current key to clipboard."""
            key = self.gemini_key_entry.get().strip()
            if key:
                self.clipboard_clear()
                self.clipboard_append(key)
                print("[API Key] Copied to clipboard")
                # Flash feedback
                copy_btn.configure(text="Copied!")
                dialog.after(1000, lambda: copy_btn.configure(text="Copy Key"))

        copy_btn = ctk.CTkButton(btn_frame, text="Copy Key", width=100, command=copy_key)
        copy_btn.pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="Clear Key", width=100, fg_color="orange", hover_color="darkorange", command=clear_key).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="Close", width=100, fg_color="gray", command=dialog.destroy).pack(side="left", padx=5)

        # Info text
        ctk.CTkLabel(
            dialog,
            text="Get a free API key at: aistudio.google.com",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        ).pack(pady=(20, 10))

    def save_summary(self):
        """Save textbox content to summary file.

        Returns:
            bool: True if successful, False otherwise
        """
        text = self.textbox.get("0.0", "end-1c")
        print(f"[Save] Saving {len(text)} chars to summary.txt")
        if self.file_manager.save_summary(text):
            print(f"[Save] Success - summary.txt saved")
            return True
        else:
            self.label_status.configure(text="Error saving file", text_color="red")
            return False

    def _load_settings(self) -> dict:
        """Load app settings from settings.json."""
        default_settings = {
            "auto_fetch_urls": False,  # Auto-fetch URLs in Direct Audio mode
            "text_scale": 100,  # Text scaling percentage (50-150%)
            "server_url": "",  # Cloud scheduler server URL
            "server_api_key": "",  # API key for cloud scheduler auth
            "first_run_completed": False,  # First-run wizard shown
            "drive_auto_upload": False,  # Auto-upload audio to Google Drive
            "drive_root_folder_name": "Daily Audio Briefing",  # Drive root folder name
            "drive_folder_id": "",  # Shared Google Drive folder ID (from URL)
            "api_limits_enabled": True,  # Enable API usage limits
            "api_daily_limit": 500,  # Max Gemini API calls per day
            "api_monthly_limit": 10000,  # Max Gemini API calls per month
        }
        # In frozen mode, user settings live in the data directory (Application Support)
        # In dev mode, they live next to the script
        settings_path = os.path.join(get_data_directory(), "settings.json")
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    saved = json.load(f)
                    return {**default_settings, **saved}
        except Exception:
            pass
        # Fallback: check bundled defaults (frozen mode, first launch)
        if getattr(sys, 'frozen', False):
            bundled_path = get_resource_path("settings.json")
            try:
                if bundled_path != settings_path and os.path.exists(bundled_path):
                    with open(bundled_path, 'r') as f:
                        saved = json.load(f)
                        return {**default_settings, **saved}
            except Exception:
                pass
        return default_settings

    def _apply_text_scale(self, scale_percent: int = None):
        """Apply text scaling to the entire application."""
        if scale_percent is None:
            scale_percent = self.settings.get("text_scale", 100)

        # Calculate scale factor
        scale = scale_percent / 100.0

        # Base font sizes
        base_sizes = {
            "tiny": 9,
            "small": 11,
            "normal": 13,
            "medium": 14,
            "large": 16,
            "xlarge": 18,
            "header": 20,
        }

        # Apply scaled font to CustomTkinter default
        try:
            # Update default font scaling
            scaled_default = int(13 * scale)
            ctk.set_widget_scaling(scale)
            ctk.set_window_scaling(scale)
        except Exception as e:
            print(f"Error applying widget scaling: {e}")

        # Store current scale for use in dialogs
        self._current_text_scale = scale

    def _save_settings(self):
        """Save app settings to settings.json."""
        settings_path = os.path.join(get_data_directory(), "settings.json")
        try:
            with open(settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def open_settings_dialog(self):
        """Open the settings dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Settings")
        dialog.geometry("450x400")
        dialog.transient(self)
        dialog.lift()
        dialog.grab_set()

        # Use pack for auto-sizing
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Header
        ctk.CTkLabel(main_frame, text="App Settings", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", pady=(0, 15)
        )

        # === Text Scaling Section ===
        scale_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        scale_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            scale_frame,
            text="Text Size:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", pady=(0, 5))

        # Scale slider row
        slider_row = ctk.CTkFrame(scale_frame, fg_color="transparent")
        slider_row.pack(fill="x")

        # Current scale value
        current_scale = self.settings.get("text_scale", 100)
        scale_value_var = ctk.StringVar(value=f"{current_scale}%")

        ctk.CTkLabel(slider_row, text="50%", font=ctk.CTkFont(size=11), text_color="gray").pack(side="left")

        def on_scale_change(value):
            scale_int = int(value)
            scale_value_var.set(f"{scale_int}%")

        scale_slider = ctk.CTkSlider(
            slider_row,
            from_=50,
            to=150,
            number_of_steps=20,  # 5% increments
            command=on_scale_change,
            width=200
        )
        scale_slider.set(current_scale)
        scale_slider.pack(side="left", padx=10, expand=True, fill="x")

        ctk.CTkLabel(slider_row, text="150%", font=ctk.CTkFont(size=11), text_color="gray").pack(side="left")

        # Scale value display
        scale_label = ctk.CTkLabel(slider_row, textvariable=scale_value_var, font=ctk.CTkFont(size=13, weight="bold"), width=50)
        scale_label.pack(side="left", padx=(10, 0))

        # Apply button for immediate preview
        def apply_scale():
            new_scale = int(scale_slider.get())
            self.settings["text_scale"] = new_scale
            self._apply_text_scale(new_scale)
            self.label_status.configure(text=f"Text scale set to {new_scale}%", text_color="green")

        ctk.CTkButton(
            scale_frame,
            text="Apply Scale",
            command=apply_scale,
            width=100,
            fg_color="gray"
        ).pack(anchor="w", pady=(10, 0))

        ctk.CTkLabel(
            scale_frame,
            text="Note: Scaling applies to the entire app. You may need to restart for full effect.",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        ).pack(anchor="w", pady=(5, 0))

        # Separator
        ctk.CTkFrame(main_frame, height=2, fg_color="gray50").pack(fill="x", pady=15)

        # === Audio Generation Behavior Section ===
        ctk.CTkLabel(
            main_frame,
            text="Audio Generation Behavior:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", pady=(0, 5))

        info_text = (
            "• Text is automatically cleaned for audio when you click Generate\n"
            "• URLs are auto-detected and can be fetched via the yellow banner\n"
            "• Use the toggle button below the text area to switch between raw/cleaned views"
        )
        ctk.CTkLabel(
            main_frame,
            text=info_text,
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="left"
        ).pack(anchor="w", pady=(0, 20))

        # Separator
        ctk.CTkFrame(main_frame, height=2, fg_color="gray50").pack(fill="x", pady=15)

        # === Tutorial Section ===
        tutorial_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        tutorial_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            tutorial_frame,
            text="Need Help?",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", pady=(0, 5))

        def start_tutorial_from_settings():
            dialog.destroy()
            self.start_tutorial()

        ctk.CTkButton(
            tutorial_frame,
            text="? Start Tutorial",
            command=start_tutorial_from_settings,
            width=140,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40")
        ).pack(anchor="w")

        ctk.CTkLabel(
            tutorial_frame,
            text="Walk through the main features of the app step by step.",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        ).pack(anchor="w", pady=(5, 0))

        # Save button
        def save_and_close():
            # Save the current slider value
            self.settings["text_scale"] = int(scale_slider.get())
            self._save_settings()
            self._apply_text_scale()
            dialog.destroy()
            self.label_status.configure(text="Settings saved", text_color="green")

        ctk.CTkButton(main_frame, text="Save & Close", command=save_and_close, fg_color="green", width=120).pack(pady=(10, 0))

        # Let dialog auto-size based on content
        dialog.update_idletasks()
        dialog.minsize(450, 480)

    def open_fetch_article_dialog(self):
        """Open dialog to fetch article content from URLs."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Fetch Articles")
        dialog.geometry("650x350")
        dialog.transient(self)
        dialog.lift()
        dialog.grab_set()

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        # Instructions
        ctk.CTkLabel(
            dialog,
            text="Enter article URLs (one per line):",
            font=ctk.CTkFont(size=14)
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # URL text area (instead of single entry)
        url_textbox = ctk.CTkTextbox(dialog, height=150, font=ctk.CTkFont(size=12))
        url_textbox.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        url_textbox.insert("0.0", "https://")

        # Status label
        status_label = ctk.CTkLabel(dialog, text="Paste one or more URLs, each on a separate line", text_color="gray")
        status_label.grid(row=2, column=0, padx=20, pady=5, sticky="w")

        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        def fetch_articles():
            import re
            text = url_textbox.get("0.0", "end-1c").strip()
            if not text:
                status_label.configure(text="Please enter at least one URL", text_color="orange")
                return

            # Extract all URLs from the text
            url_pattern = r'https?://[^\s]+'
            urls = re.findall(url_pattern, text)

            if not urls:
                # Try adding https:// to lines that look like domains
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                urls = []
                for line in lines:
                    if not line.startswith("http"):
                        line = "https://" + line
                    urls.append(line)

            if not urls:
                status_label.configure(text="No valid URLs found", text_color="orange")
                return

            status_label.configure(text=f"Fetching {len(urls)} article(s)...", text_color="orange")
            dialog.update()

            # Fetch in background
            def fetch_thread():
                all_content = []
                success_count = 0

                for i, url in enumerate(urls):
                    self.after(0, lambda i=i: status_label.configure(
                        text=f"Fetching article {i+1}/{len(urls)}...", text_color="orange"
                    ))
                    print(f"[Fetch] Fetching URL {i+1}/{len(urls)}: {url[:60]}...")

                    content = self._fetch_article_content(url)
                    if content and len(content) > 100:
                        if all_content:
                            all_content.append("\n\n---\n\n")
                        all_content.append(content)
                        success_count += 1
                        print(f"[Fetch] Success: {len(content)} chars")
                    else:
                        print(f"[Fetch] Failed: {url[:60]}")

                if all_content:
                    combined = "".join(all_content)
                    print(f"[Fetch] Combined {len(all_content)} pieces, total {len(combined)} chars")
                    print(f"[Fetch] Combined preview: {combined[:200]}...")
                    def update_ui():
                        self.textbox.delete("0.0", "end")
                        self.textbox.insert("0.0", combined)
                        print(f"[Fetch] Inserted {len(combined)} chars into textbox")
                        self._placeholder.place_forget()
                        dialog.destroy()
                        self.label_status.configure(
                            text=f"Fetched {success_count} article(s) ({len(combined)} chars). Click Generate to convert to audio.",
                            text_color="green"
                        )
                    self.after(0, update_ui)
                else:
                    self.after(0, lambda: status_label.configure(
                        text="Failed to fetch any articles. Check URLs and try again.",
                        text_color="red"
                    ))

            threading.Thread(target=fetch_thread, daemon=True).start()

        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", command=dialog.destroy).grid(
            row=0, column=0, padx=5, sticky="ew"
        )
        ctk.CTkButton(btn_frame, text="Fetch All", fg_color="green", command=fetch_articles).grid(
            row=0, column=1, padx=5, sticky="ew"
        )

    def _detect_content_type(self, text: str) -> dict:
        """Analyze text content and detect URLs by type.

        Returns dict with:
            - youtube_urls: list of YouTube video URLs
            - article_urls: list of non-YouTube URLs
            - plain_text: text content excluding URLs
            - is_pure_urls: True if content is only URLs (no surrounding text)
            - has_embedded_urls: True if URLs are embedded in text content
        """
        import re

        # URL patterns
        url_pattern = r'https?://[^\s<>"\')(\]\[}]+'
        youtube_pattern = r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w-]+'

        # Find all URLs
        all_urls = re.findall(url_pattern, text)

        # Categorize URLs
        youtube_urls = []
        article_urls = []

        for url in all_urls:
            # Clean up URL (remove trailing punctuation)
            url = re.sub(r'[.,;:!?]+$', '', url)
            if re.search(youtube_pattern, url):
                youtube_urls.append(url)
            else:
                article_urls.append(url)

        # Remove duplicates while preserving order
        youtube_urls = list(dict.fromkeys(youtube_urls))
        article_urls = list(dict.fromkeys(article_urls))

        # Get plain text by removing URLs
        plain_text = re.sub(url_pattern, '', text).strip()
        # Clean up multiple spaces/newlines
        plain_text = re.sub(r'\n\s*\n+', '\n\n', plain_text)
        plain_text = re.sub(r' +', ' ', plain_text)

        # Determine if content is "pure URLs" (just URLs, maybe with whitespace)
        # vs "embedded URLs" (URLs within substantive text)
        text_without_urls = plain_text.strip()
        is_pure_urls = len(text_without_urls) < 50  # Less than 50 chars of non-URL text
        has_embedded_urls = (youtube_urls or article_urls) and len(text_without_urls) >= 50

        return {
            'youtube_urls': youtube_urls,
            'article_urls': article_urls,
            'plain_text': plain_text,
            'is_pure_urls': is_pure_urls,
            'has_embedded_urls': has_embedded_urls,
            'total_urls': len(youtube_urls) + len(article_urls)
        }

    def _load_extraction_configs(self) -> list:
        """Load all extraction configs from extraction_instructions/ folder.

        Returns list of dicts with config info:
            - name: config display name
            - filename: config filename (without .json)
            - source_domains: list of domains this config handles
            - config: full config dict
        """
        configs = []
        instructions_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extraction_instructions')

        if not os.path.exists(instructions_dir):
            return configs

        for filename in os.listdir(instructions_dir):
            if not filename.endswith('.json') or filename.startswith('_'):
                continue

            config_path = os.path.join(instructions_dir, filename)
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # Determine which domains this config should handle
                # Look for source_url_patterns first, then infer from config name
                source_domains = config.get('source_url_patterns', [])

                # If no explicit patterns, try to infer from config name
                if not source_domains:
                    config_name = filename.replace('.json', '').lower()
                    # Common newsletter domain patterns based on config names
                    domain_map = {
                        'execsum': ['execsum.co'],
                        'cryptosum': ['cryptosum.beehiiv.com', 'crypto-sum.beehiiv.com'],
                        'rwa': ['rwaxyz.com', 'rwanews.com'],
                    }
                    source_domains = domain_map.get(config_name, [])

                if source_domains:
                    configs.append({
                        'name': config.get('name', filename.replace('.json', '')),
                        'filename': filename.replace('.json', ''),
                        'source_domains': source_domains,
                        'config': config
                    })
            except Exception as e:
                print(f"[Config] Error loading {filename}: {e}")

        return configs

    def _match_url_to_config(self, url: str, configs: list = None) -> dict:
        """Check if a URL matches any extraction config's source domains.

        Returns dict with:
            - matched: bool
            - config_name: name of matching config (if matched)
            - config_filename: filename of matching config (if matched)
            - config: full config dict (if matched)
        """
        from urllib.parse import urlparse

        if configs is None:
            configs = self._load_extraction_configs()

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace('www.', '')

            for config_info in configs:
                for source_domain in config_info['source_domains']:
                    if source_domain.lower() in domain or domain in source_domain.lower():
                        return {
                            'matched': True,
                            'config_name': config_info['name'],
                            'config_filename': config_info['filename'],
                            'config': config_info['config']
                        }
        except Exception:
            pass

        return {'matched': False}

    def _categorize_urls_by_config(self, article_urls: list) -> dict:
        """Categorize article URLs by whether they match extraction configs.

        Returns dict with:
            - config_urls: dict mapping config_filename -> list of URLs
            - regular_urls: list of URLs that don't match any config
        """
        configs = self._load_extraction_configs()
        config_urls = {}  # config_filename -> [urls]
        regular_urls = []

        for url in article_urls:
            match = self._match_url_to_config(url, configs)
            if match['matched']:
                config_name = match['config_filename']
                if config_name not in config_urls:
                    config_urls[config_name] = {
                        'urls': [],
                        'display_name': match['config_name']
                    }
                config_urls[config_name]['urls'].append(url)
            else:
                regular_urls.append(url)

        return {
            'config_urls': config_urls,
            'regular_urls': regular_urls
        }

    def _fetch_youtube_transcript(self, url: str) -> dict:
        """Fetch YouTube video transcript and metadata.

        Returns dict with:
            - success: bool
            - title: video title
            - transcript: transcript text
            - url: original URL
            - error: error message if failed
        """
        import re
        import yt_dlp

        # Extract video ID
        video_id_match = re.search(r'(?:v=|youtu\.be/|shorts/)([a-zA-Z0-9_-]{11})', url)
        if not video_id_match:
            return {'success': False, 'url': url, 'error': 'Invalid YouTube URL'}

        video_id = video_id_match.group(1)
        temp_prefix = f"temp_sub_{video_id}"

        # Clean up any existing temp files
        import glob
        for f in glob.glob(f"{temp_prefix}*"):
            try:
                os.remove(f)
            except:
                pass

        # Get video info first
        title = "Unknown Video"
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown Video')
        except Exception as e:
            print(f"[YouTube] Could not get video info: {e}")

        # Download subtitles
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en"],
            "outtmpl": temp_prefix,
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            return {'success': False, 'url': url, 'title': title, 'error': f'Download error: {e}'}

        # Find subtitle file
        files = glob.glob(f"{temp_prefix}*.vtt")
        if not files:
            files = glob.glob(f"{temp_prefix}*")
            files = [f for f in files if f.endswith((".vtt", ".ttml", ".srv1", ".srt"))]

        if not files:
            return {'success': False, 'url': url, 'title': title, 'error': 'No transcript available'}

        # Read and clean transcript
        filename = files[0]
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {'success': False, 'url': url, 'title': title, 'error': f'Read error: {e}'}

        # Clean up temp files
        for f in files:
            try:
                os.remove(f)
            except:
                pass

        # Clean VTT content (remove timestamps, duplicates)
        transcript = self._clean_vtt_transcript(content)

        return {
            'success': True,
            'url': url,
            'title': title,
            'transcript': transcript,
            'video_id': video_id
        }

    def _clean_vtt_transcript(self, content: str) -> str:
        """Clean VTT subtitle content to plain text."""
        import re
        lines = content.split("\n")
        cleaned = []
        last_line = ""

        for line in lines:
            line = line.strip()
            # Skip VTT header, timestamps, and metadata
            if not line or line.startswith("WEBVTT") or line.startswith("Kind:"):
                continue
            if re.match(r"^\d+$", line):  # Line numbers
                continue
            if re.match(r"^[\d:.,\->]+\s*$", line):  # Timestamps
                continue
            if "-->" in line:
                continue

            # Remove HTML tags and timestamp tags
            line = re.sub(r"<[^>]+>", "", line)
            line = re.sub(r"\[.*?\]", "", line)

            # Skip duplicates (auto-generated subs often repeat)
            if line and line != last_line:
                cleaned.append(line)
                last_line = line

        return "\n".join(cleaned)

    def _process_mixed_content(self, text: str, api_key: str, progress_callback=None) -> str:
        """Process mixed content (YouTube URLs, article URLs, plain text).

        Returns combined content organized by source and date.
        """
        import datetime

        detection = self._detect_content_type(text)
        results = []
        today = datetime.date.today().strftime("%Y-%m-%d")

        total_items = detection['total_urls']
        processed = 0

        # Process YouTube URLs
        if detection['youtube_urls']:
            if progress_callback:
                progress_callback(f"Processing {len(detection['youtube_urls'])} YouTube video(s)...", "orange")

            for url in detection['youtube_urls']:
                processed += 1
                if progress_callback:
                    progress_callback(f"Fetching YouTube {processed}/{total_items}...", "orange")

                result = self._fetch_youtube_transcript(url)
                if result['success']:
                    # Summarize the transcript
                    summary = self._summarize_youtube_transcript(result, api_key)
                    if summary:
                        results.append({
                            'type': 'youtube',
                            'title': result['title'],
                            'url': url,
                            'content': summary,
                            'date': today
                        })
                else:
                    print(f"[Process] YouTube failed: {result.get('error', 'Unknown error')}")

        # Process Article URLs
        if detection['article_urls']:
            if progress_callback:
                progress_callback(f"Processing {len(detection['article_urls'])} article(s)...", "orange")

            for url in detection['article_urls']:
                processed += 1
                if progress_callback:
                    progress_callback(f"Fetching article {processed}/{total_items}...", "orange")

                raw_content = self._fetch_article_content(url)
                if raw_content and len(raw_content) > 100:
                    # Extract domain for source attribution
                    import re
                    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
                    source = domain_match.group(1) if domain_match else 'Unknown'

                    # Clean and summarize the article using AI
                    if progress_callback:
                        progress_callback(f"Cleaning article {processed}/{total_items}...", "orange")

                    cleaned_content = self._clean_article_content(raw_content, url, api_key)

                    results.append({
                        'type': 'article',
                        'title': source,
                        'url': url,
                        'content': cleaned_content,
                        'raw_content': raw_content,  # Store raw for toggle
                        'date': today
                    })

        # Include plain text if substantial
        if detection['plain_text'] and len(detection['plain_text']) > 100:
            results.append({
                'type': 'text',
                'title': 'Pasted Text',
                'url': None,
                'content': detection['plain_text'],
                'date': today
            })

        # Format output with clear separation
        output_parts = []
        for item in results:
            header = f"=== {item['title']} ({item['date']}) ==="
            if item['url']:
                header += f"\nSource: {item['url']}"
            output_parts.append(f"{header}\n\n{item['content']}")

        return "\n\n" + "\n\n---\n\n".join(output_parts) if output_parts else ""

    def _clean_article_content(self, raw_content: str, url: str, api_key: str) -> str:
        """Clean and summarize article content using Gemini with custom instructions."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)

            model_name = self.model_var.get().split(" (")[0]
            model = genai.GenerativeModel(model_name)

            # Get custom instructions from active profile
            custom_instructions = self._get_active_youtube_instructions()  # Reuse same instructions

            # Base prompt for article cleaning
            base_prompt = """Clean and summarize this article content for an audio news briefing.

IMPORTANT CLEANING RULES:
1. REMOVE all marketing, ads, CTAs, sponsored content, newsletter signup prompts
2. REMOVE social media share buttons, related article links, author bios with social links
3. REMOVE any "Subscribe", "Sign up", "Follow us", "Click here" type content
4. REMOVE navigation elements, footer content, sidebar content that got captured
5. KEEP only the actual article content - the main story/information

FORMAT FOR AUDIO:
- Write in flowing sentences suitable for listening (no bullet points unless essential)
- Keep it concise but comprehensive - focus on key points and insights
- Maintain the article's core message and important details
- Start directly with the content (no "This article discusses..." intros)"""

            # Add custom instructions if present
            if custom_instructions:
                prompt = f"""{base_prompt}

USER PREFERENCES:
{custom_instructions}

ARTICLE URL: {url}

RAW CONTENT:
{raw_content[:20000]}"""  # Limit content length
            else:
                prompt = f"""{base_prompt}

ARTICLE URL: {url}

RAW CONTENT:
{raw_content[:20000]}"""  # Limit content length

            from api_usage_tracker import get_tracker, APILimitExceeded, BudgetExceeded
            response = get_tracker().tracked_generate(model, prompt, "gui._clean_article")
            cleaned = response.text.strip()

            # Ensure we got meaningful content back
            if len(cleaned) > 50:
                return cleaned
            else:
                print(f"[Clean Article] AI returned too short response, using original")
                return raw_content[:5000]

        except (APILimitExceeded, BudgetExceeded) as e:
            print(f"[Clean Article] {e}")
            return raw_content[:5000]
        except Exception as e:
            print(f"[Clean Article] Error: {e}")
            return raw_content[:5000]  # Return truncated raw content as fallback

    def _summarize_youtube_transcript(self, video_result: dict, api_key: str) -> str:
        """Summarize a YouTube transcript using Gemini with optional custom instructions."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)

            model_name = self.model_var.get().split(" (")[0]
            model = genai.GenerativeModel(model_name)

            # Get custom YouTube instructions from active profile
            custom_instructions = self._get_active_youtube_instructions()

            # Base prompt for YouTube summarization
            base_prompt = f"""Summarize this YouTube video transcript for an audio news briefing.
Keep it concise but comprehensive. Focus on the key points and insights.
Format for listening (no bullet points, write in flowing sentences).

Video: {video_result['title']}"""

            # Add custom instructions if present
            if custom_instructions:
                prompt = f"""{base_prompt}

USER PREFERENCES:
{custom_instructions}

Transcript:
{video_result['transcript'][:15000]}"""  # Limit transcript length
            else:
                prompt = f"""{base_prompt}

Transcript:
{video_result['transcript'][:15000]}"""  # Limit transcript length

            from api_usage_tracker import get_tracker, APILimitExceeded, BudgetExceeded
            response = get_tracker().tracked_generate(model, prompt, "gui._summarize_yt")
            return response.text.strip()
        except (APILimitExceeded, BudgetExceeded) as e:
            print(f"[Summarize] {e}")
            return f"API limit reached: {e.limit_type} ({e.current}/{e.maximum}). Try again tomorrow or increase limits in Settings."
        except Exception as e:
            print(f"[Summarize] Error: {e}")
            return video_result['transcript'][:2000]  # Return truncated transcript as fallback

    def _fetch_article_content(self, url: str) -> str:
        """Fetch and extract article body from URL."""
        try:
            import requests
            from bs4 import BeautifulSoup
            import re

            # Browser headers - NOTE: Don't set Accept-Encoding, let requests handle decompression
            # Setting it explicitly causes compressed content to not be decoded properly
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            html = None
            fetch_error = None
            content_type = None

            # Try with requests session (handles cookies)
            try:
                session = requests.Session()
                response = session.get(url, headers=headers, timeout=20, allow_redirects=True)
                response.raise_for_status()
                content_type = response.headers.get('content-type', '').lower()

                # Check for non-HTML content
                if content_type and not any(ct in content_type for ct in ['text/html', 'text/plain', 'application/xhtml']):
                    print(f"       [Fetch] Skipping non-HTML content-type: {content_type}")
                    return ""

                # Use proper encoding
                if response.encoding:
                    html = response.text
                else:
                    html = response.content.decode('utf-8', errors='ignore')
                print(f"       [Fetch] HTTP {response.status_code}, {len(html)} bytes")

                # Check if HTML looks valid (should start with < or whitespace then <)
                html_stripped = html.strip()
                if not html_stripped.startswith('<') and not html_stripped.startswith('<!'):
                    print(f"       [Fetch] HTML looks malformed, retrying with SSL verify=False...")
                    html = None  # Force retry
            except Exception as e:
                fetch_error = str(e)
                print(f"       [Fetch] requests failed: {e}")

            # Retry with SSL verification disabled if first attempt failed or returned bad HTML
            if not html:
                try:
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    session = requests.Session()
                    response = session.get(url, headers=headers, timeout=20, allow_redirects=True, verify=False)
                    response.raise_for_status()
                    if response.encoding:
                        html = response.text
                    else:
                        html = response.content.decode('utf-8', errors='ignore')
                    print(f"       [Fetch] SSL-disabled retry: HTTP {response.status_code}, {len(html)} bytes")
                except Exception as e:
                    print(f"       [Fetch] SSL-disabled retry failed: {e}")

            # Fallback to urllib with SSL context
            if not html:
                try:
                    import urllib.request
                    import ssl
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=20, context=ctx) as response:
                        html = response.read().decode('utf-8', errors='ignore')
                    print(f"       [Fetch] urllib success: {len(html)} bytes")
                except Exception as e:
                    print(f"       [Fetch] urllib failed: {e}")

            if not html:
                print(f"       [Fetch] All fetch methods failed")
                return ""

            # Try lxml first, fallback to html.parser
            # Debug: show HTML preview to check if content is valid
            html_preview = html[:200].replace('\n', ' ')
            print(f"       [Fetch] HTML preview: {html_preview}...")

            soup = None
            try:
                soup = BeautifulSoup(html, 'lxml')
            except Exception as e:
                print(f"       [Fetch] lxml parse error: {e}, trying html.parser")
                try:
                    soup = BeautifulSoup(html, 'html.parser')
                except Exception as e2:
                    print(f"       [Fetch] html.parser also failed: {e2}")
                    return ""

            if soup is None:
                print(f"       [Fetch] BeautifulSoup parsing failed")
                return ""

            # Debug: check soup structure
            has_body = soup.body is not None
            body_children = len(list(soup.body.children)) if has_body else 0
            print(f"       [Fetch] Soup parsed: body={has_body}, children={body_children}")

            # Extract article metadata (title, author, date)
            article_title = None
            article_author = None
            article_date = None

            try:
                # Title: try multiple sources
                title_sources = [
                    soup.find('meta', {'property': 'og:title'}),
                    soup.find('meta', {'name': 'title'}),
                    soup.find('h1'),
                    soup.find('title')
                ]
                for src in title_sources:
                    if src:
                        title_text = src.get('content') if src.name == 'meta' else src.get_text(strip=True)
                        if title_text and len(title_text) > 5:
                            article_title = title_text[:200]  # Limit length
                            break

                # Author: try multiple sources
                author_sources = [
                    soup.find('meta', {'name': 'author'}),
                    soup.find('meta', {'property': 'article:author'}),
                    soup.find('a', {'rel': 'author'}),
                    soup.find(class_=lambda x: x and 'author' in str(x).lower()),
                    soup.find('span', {'itemprop': 'author'}),
                ]
                for src in author_sources:
                    if src:
                        author_text = src.get('content') if src.name == 'meta' else src.get_text(strip=True)
                        if author_text and len(author_text) > 2 and len(author_text) < 100:
                            article_author = author_text
                            break

                # Date: try multiple sources
                date_sources = [
                    soup.find('meta', {'property': 'article:published_time'}),
                    soup.find('meta', {'name': 'date'}),
                    soup.find('time', {'datetime': True}),
                    soup.find('time'),
                    soup.find(class_=lambda x: x and 'date' in str(x).lower() and 'update' not in str(x).lower()),
                ]
                for src in date_sources:
                    if src:
                        if src.name == 'meta':
                            date_text = src.get('content', '')
                        elif src.name == 'time':
                            date_text = src.get('datetime', src.get_text(strip=True))
                        else:
                            date_text = src.get_text(strip=True)
                        if date_text:
                            # Clean up date format (take first 10-20 chars for date part)
                            article_date = date_text[:25].strip()
                            break

                if article_title:
                    print(f"       [Fetch] Metadata - Title: {article_title[:50]}...")
                if article_author:
                    print(f"       [Fetch] Metadata - Author: {article_author}")
                if article_date:
                    print(f"       [Fetch] Metadata - Date: {article_date}")

            except Exception as e:
                print(f"       [Fetch] Metadata extraction error: {e}")

            article_text = None

            # CRITICAL: Extract article content BEFORE any tag removal
            # Check common article selectors and extract immediately if found
            try:
                content_selectors = [
                    # Substack
                    'div.body.markup', 'div.body-markup', 'div.available-content',
                    # WordPress
                    'div.entry-content', 'article .entry-content', 'main .entry-content',
                    'div.post-content', 'article.post', 'main article',
                    # Generic
                    'article', 'main', '[role="main"]', '[role="article"]'
                ]
                for sel in content_selectors:
                    elem = soup.select_one(sel)
                    if elem:
                        text = elem.get_text(separator='\n', strip=True)
                        if len(text) > 200:
                            article_text = text
                            print(f"       [Fetch] Early extraction: '{sel}' found {len(text)} chars")
                            preview = text[:100].replace('\n', ' ')
                            print(f"       [Fetch] Preview: {preview}...")
                            break
                        else:
                            print(f"       [Fetch] '{sel}' exists but only {len(text)} chars")

                if not article_text:
                    print(f"       [Fetch] No content found in early selectors")
            except Exception as e:
                print(f"       [Fetch] Early extraction error: {e}")

            # Check for paywall or login-required indicators
            try:
                page_text = soup.get_text().lower()
                if 'subscribe to read' in page_text or 'sign in to read' in page_text:
                    print(f"       [Fetch] Possible paywall detected")
            except Exception as e:
                print(f"       [Fetch] Paywall check error: {e}")

            # Skip JSON extraction if early extraction already got content
            if article_text and len(article_text) > 200:
                print(f"       [Fetch] Skipping JSON extraction - already have {len(article_text)} chars")
            else:
                # IMPORTANT: Extract Substack/Next.js content BEFORE removing scripts (if early extraction didn't work)
                # Substack uses Next.js which embeds article content in __NEXT_DATA__ script
                try:
                    next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
                    all_scripts = soup.find_all('script')

                    if not next_data_script:
                        # Debug: show what script tags exist
                        script_ids = [s.get('id', 'no-id') for s in all_scripts[:5]]
                        print(f"       [Fetch] No __NEXT_DATA__, {len(all_scripts)} scripts found, IDs: {script_ids}")

                    if next_data_script:
                        script_content = next_data_script.string or next_data_script.get_text()
                        print(f"       [Fetch] Found __NEXT_DATA__ script: {len(script_content) if script_content else 0} chars")
                        if script_content:
                            try:
                                next_data = json.loads(script_content)
                                post = None
                                if 'props' in next_data and 'pageProps' in next_data['props']:
                                    page_props = next_data['props']['pageProps']
                                    if 'post' in page_props:
                                        post = page_props['post']
                                    elif 'initialPost' in page_props:
                                        post = page_props['initialPost']

                                if post:
                                    body_html = post.get('body_html', '')
                                    if body_html:
                                        body_soup = BeautifulSoup(body_html, 'html.parser')
                                        text = body_soup.get_text(separator='\n', strip=True)
                                        if len(text) > 200:
                                            article_text = text
                                            print(f"       [Fetch] Next.js JSON: found {len(text)} chars")
                            except json.JSONDecodeError as je:
                                print(f"       [Fetch] Next.js JSON parse error: {je}")
                except Exception as e:
                    print(f"       [Fetch] Next.js extraction error: {e}")

            # Only do tag removal and fallback extraction if we don't already have content
            if article_text and len(article_text) > 200:
                print(f"       [Fetch] Already have {len(article_text)} chars, skipping fallback extraction")
            else:
                # Remove elements that are definitely not article content
                try:
                    for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header',
                                               'aside', 'iframe', 'noscript', 'form', 'button', 'svg']):
                        tag.decompose()
                except Exception as e:
                    print(f"       [Fetch] Tag removal error: {e}")

                # Remove common non-content patterns by class/id
                try:
                    remove_patterns = [
                        'subscribe', 'newsletter', 'sidebar', 'comment', 'share',
                        'social', 'related', 'recommended', 'footer', 'header',
                        'navigation', 'nav-', 'menu', 'ad-', 'advertisement',
                        'signup', 'sign-up', 'login', 'paywall', 'premium', 'popup',
                        'modal', 'cookie', 'banner', 'promo'
                    ]
                    for pattern in remove_patterns:
                        for tag in soup.find_all(class_=lambda x: x and pattern in str(x).lower()):
                            tag.decompose()
                        for tag in soup.find_all(id=lambda x: x and pattern in str(x).lower()):
                            tag.decompose()
                except Exception as e:
                    print(f"       [Fetch] Pattern removal error: {e}")

            # Platform-specific extraction (if we still don't have content)
            # Substack (multiple variations) - includes custom domains
            if not article_text or len(article_text) < 200:
                try:
                    is_substack = 'substack.com' in url or 'experimental-history.com' in url
                    if not is_substack:
                        # Check for Substack-like structure in HTML
                        is_substack = (
                            soup.find('div', class_='available-content') is not None or
                            soup.find('div', class_='body markup') is not None or
                            soup.find('meta', {'property': 'og:site_name', 'content': lambda x: x and 'Substack' in str(x)}) is not None or
                            'substack' in str(soup.find('script', {'src': True}) or '').lower()
                        )

                    if is_substack:
                        print(f"       [Fetch] Trying Substack extraction...")
                        # More comprehensive Substack selectors
                        substack_selectors = [
                            'div.body.markup',
                            'div.body-markup',
                            'div.available-content',
                            'div.post-content',
                            'div.post-content-final',
                            'div.body',
                            'div.markup',
                            'article.post',
                            'article',
                            '.post-content',
                            '.body.markup',
                            '[data-testid="post-content"]',
                        ]
                        for selector in substack_selectors:
                            try:
                                content = soup.select_one(selector)
                                if content:
                                    text = content.get_text(separator='\n', strip=True)
                                    if len(text) > 200:
                                        article_text = text
                                        print(f"       [Fetch] Substack: found {len(text)} chars with {selector}")
                                        break
                            except Exception as sel_err:
                                continue
                except Exception as e:
                    print(f"       [Fetch] Substack extraction error: {e}")

            # Generic article selectors (priority order)
            if not article_text or len(article_text) < 200:
                try:
                    selectors = [
                        'article',
                        'div.article-content',
                        'div.article-body',
                        'div.post-content',
                        'div.entry-content',
                        'div.content-body',
                        'div.story-body',
                        'div.post-body',
                        'div.article',
                        'main',
                        '[role="main"]',
                        '[role="article"]',
                        'div.content',
                        'div.post',
                    ]

                    for selector in selectors:
                        content = soup.select_one(selector)
                        if content:
                            text = content.get_text(separator='\n', strip=True)
                            if len(text) > 200:
                                article_text = text
                                print(f"       [Fetch] Generic: found {len(text)} chars with {selector}")
                                break
                except Exception as e:
                    print(f"       [Fetch] Generic extraction error: {e}")

            # Fallback: get largest text block with paragraphs
            if not article_text or len(article_text) < 200:
                try:
                    print(f"       [Fetch] Trying fallback paragraph extraction...")
                    all_divs = soup.find_all(['div', 'article', 'section', 'main'])
                    best_text = ""
                    best_source = ""
                    for div in all_divs:
                        paragraphs = div.find_all('p')
                        if len(paragraphs) >= 2:  # At least 2 paragraphs
                            text = div.get_text(separator='\n', strip=True)
                            if len(text) > len(best_text):
                                best_text = text
                                best_source = div.name
                    if best_text and len(best_text) > 200:
                        article_text = best_text
                        print(f"       [Fetch] Fallback: found {len(best_text)} chars from {best_source}")
                except Exception as e:
                    print(f"       [Fetch] Fallback extraction error: {e}")

            # Last resort: just get body text
            if not article_text or len(article_text) < 200:
                try:
                    if soup.body:
                        body_text = soup.body.get_text(separator='\n', strip=True)
                        print(f"       [Fetch] Body text length: {len(body_text)} chars")
                        if len(body_text) > 500:
                            article_text = body_text
                            print(f"       [Fetch] Last resort: using body text ({len(body_text)} chars)")
                        else:
                            print(f"       [Fetch] Body text too short: {len(body_text)} chars")
                            # Debug: show first 200 chars of body
                            preview = body_text[:200].replace('\n', ' ')
                            print(f"       [Fetch] Body preview: {preview}")
                    else:
                        print(f"       [Fetch] No body element found in soup")
                except Exception as e:
                    print(f"       [Fetch] Body text error: {e}")

            # Clean up the text
            if article_text:
                try:
                    # First, aggressively remove non-printable/binary characters
                    # Keep only ASCII printable + common unicode letters
                    cleaned = []
                    for char in article_text:
                        if char.isprintable() or char in '\n\t\r':
                            cleaned.append(char)
                        elif ord(char) > 127:
                            # Replace non-ASCII with space (might be unicode)
                            cleaned.append(' ')
                    article_text = ''.join(cleaned)

                    # Remove multiple newlines
                    article_text = re.sub(r'\n{3,}', '\n\n', article_text)
                    article_text = re.sub(r' {3,}', ' ', article_text)

                    # Remove common junk phrases
                    junk_phrases = [
                        r'Subscribe.*?newsletter',
                        r'Sign up.*?free',
                        r'Click here to.*',
                        r'Share this.*',
                        r'Follow us on.*',
                        r'Read more:.*',
                        r'Related:.*',
                        r'Comments.*',
                        r'Leave a comment.*',
                    ]
                    for phrase in junk_phrases:
                        article_text = re.sub(phrase, '', article_text, flags=re.IGNORECASE)

                    # Check content quality - must have real words
                    # Split into words and check that most are actual words (letters only)
                    words = article_text.split()
                    if words:
                        # Count words that are mostly alphabetic (allowing some punctuation)
                        real_words = sum(1 for w in words if sum(c.isalpha() for c in w) > len(w) * 0.5)
                        word_ratio = real_words / len(words)
                        if word_ratio < 0.5:
                            print(f"       [Fetch] Low word quality ({word_ratio:.1%} real words), filtering lines...")
                            # Filter line by line
                            clean_lines = []
                            for line in article_text.split('\n'):
                                line = line.strip()
                                if len(line) < 10:
                                    continue
                                # Check if line has mostly real words
                                line_words = line.split()
                                if line_words:
                                    line_real = sum(1 for w in line_words if sum(c.isalpha() for c in w) > len(w) * 0.5)
                                    if line_real / len(line_words) > 0.6:
                                        clean_lines.append(line)
                            if clean_lines:
                                article_text = '\n'.join(clean_lines)
                                print(f"       [Fetch] Filtered to {len(article_text)} clean chars")
                            else:
                                print(f"       [Fetch] No readable content after word filtering")
                                article_text = ""

                    # Final cleanup
                    article_text = re.sub(r'\n{3,}', '\n\n', article_text)
                    article_text = re.sub(r' {2,}', ' ', article_text)

                except Exception as e:
                    print(f"       [Fetch] Cleanup error: {e}")

                final_text = article_text.strip()
                if len(final_text) > 100:
                    # Final sanity check - sample the text
                    sample = final_text[:500]
                    sample_words = sample.split()
                    if sample_words:
                        alpha_words = sum(1 for w in sample_words if any(c.isalpha() for c in w))
                        if alpha_words / len(sample_words) < 0.3:
                            print(f"       [Fetch] Final check failed - content appears to be garbage")
                            return ""

                    # Prepend article metadata header for clear segmentation
                    header_parts = []
                    if article_title:
                        header_parts.append(f"Title: {article_title}")
                    if article_author:
                        header_parts.append(f"Author: {article_author}")
                    if article_date:
                        header_parts.append(f"Date: {article_date}")

                    if header_parts:
                        header = "=== ARTICLE ===\n" + "\n".join(header_parts) + "\n\n"
                        final_text = header + final_text

                    return final_text
                else:
                    print(f"       [Fetch] Text too short after cleanup: {len(final_text)} chars")

            print(f"       [Fetch] No usable content found")
            return ""

        except Exception as e:
            print(f"       [Fetch] Error: {e}")
            return ""

    def open_sources_editor(self):
        """Open the sources editor dialog with type badges and multi-source support."""
        from source_fetcher import SourceConfig, SourceType

        editor = ctk.CTkToplevel(self)
        editor.title("Edit Content Sources")
        editor.geometry("850x650")
        editor.minsize(850, 550)
        editor.transient(self)
        editor.lift()

        # Header with legend
        header_frame = ctk.CTkFrame(editor, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            header_frame,
            text="Manage your content sources (YouTube, RSS, Article Archives):",
            font=ctk.CTkFont(weight="bold")
        ).pack(side="left")

        # Legend for type badges
        legend_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        legend_frame.pack(side="right")
        ctk.CTkLabel(legend_frame, text="YT", fg_color="#FF0000", text_color="white",
                    corner_radius=4, width=30, font=ctk.CTkFont(size=10)).pack(side="left", padx=2)
        ctk.CTkLabel(legend_frame, text="YouTube", font=ctk.CTkFont(size=10)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(legend_frame, text="NL", fg_color="#9932CC", text_color="white",
                    corner_radius=4, width=30, font=ctk.CTkFont(size=10)).pack(side="left", padx=2)
        ctk.CTkLabel(legend_frame, text="Newsletter", font=ctk.CTkFont(size=10)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(legend_frame, text="RSS", fg_color="#FF8C00", text_color="white",
                    corner_radius=4, width=30, font=ctk.CTkFont(size=10)).pack(side="left", padx=2)
        ctk.CTkLabel(legend_frame, text="Feed", font=ctk.CTkFont(size=10)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(legend_frame, text="ARC", fg_color="#4169E1", text_color="white",
                    corner_radius=4, width=30, font=ctk.CTkFont(size=10)).pack(side="left", padx=2)
        ctk.CTkLabel(legend_frame, text="Archive", font=ctk.CTkFont(size=10)).pack(side="left")

        container = ctk.CTkScrollableFrame(editor, width=800, height=400)
        container.pack(padx=10, pady=(5, 5), fill="both", expand=True)
        container.grid_columnconfigure(1, weight=1)

        # Check user data directory first, then bundled resources
        data_dir = get_data_directory()
        sources_json_user = os.path.join(data_dir, "sources.json")
        sources_json_bundled = get_resource_path("sources.json")
        channels_file_user = os.path.join(data_dir, "channels.txt")
        channels_file_bundled = get_resource_path("channels.txt")
        import json
        sources = []

        # Try user's customized sources first
        if os.path.exists(sources_json_user):
            try:
                data = json.load(open(sources_json_user))
                sources = data.get("sources", [])
            except Exception:
                sources = []

        # Fall back to bundled sources.json
        if not sources and os.path.exists(sources_json_bundled):
            try:
                data = json.load(open(sources_json_bundled))
                sources = data.get("sources", [])
            except Exception:
                sources = []

        # Fall back to user's channels.txt
        if not sources and os.path.exists(channels_file_user):
            with open(channels_file_user, "r", encoding="utf-8") as f:
                sources = [{"url": ln.strip(), "enabled": True} for ln in f if ln.strip()]

        # Fall back to bundled channels.txt
        if not sources and os.path.exists(channels_file_bundled):
            with open(channels_file_bundled, "r", encoding="utf-8") as f:
                sources = [{"url": ln.strip(), "enabled": True} for ln in f if ln.strip()]

        def get_type_badge_config(url: str, explicit_type: str = None):
            """Get badge text, color for a source type."""
            # Handle newsletter type explicitly (not in SourceType enum)
            if explicit_type == "newsletter":
                return ("NL", "#9932CC", "white")

            if explicit_type:
                try:
                    src_type = SourceType(explicit_type)
                except ValueError:
                    src_type = SourceConfig._infer_type(url)
            else:
                src_type = SourceConfig._infer_type(url)

            if src_type == SourceType.YOUTUBE:
                return ("YT", "#FF0000", "white")
            elif src_type == SourceType.RSS:
                return ("RSS", "#FF8C00", "white")
            else:
                return ("ARC", "#4169E1", "white")

        widgets = []
        # Store original source data to preserve extra fields like 'config', 'name'
        original_sources = {src.get("url", ""): src for src in sources}

        # Load available extraction configs for newsletter dropdown
        config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extraction_instructions")
        available_configs = ["(none)"]
        if os.path.exists(config_dir):
            for f in os.listdir(config_dir):
                if f.endswith('.json'):
                    available_configs.append(f.replace('.json', ''))

        # Type options with display names
        type_options = ["YouTube", "Newsletter", "RSS", "Archive"]
        type_to_value = {"YouTube": "youtube", "Newsletter": "newsletter", "RSS": "rss", "Archive": "article_archive"}
        value_to_type = {v: k for k, v in type_to_value.items()}

        def add_source_row(idx, url="", enabled=True, source_type=None, config=None, name=None):
            """Add a row for editing a source."""
            row_frame = ctk.CTkFrame(container, fg_color="transparent")
            row_frame.grid(row=idx, column=0, columnspan=4, sticky="ew", pady=2)
            row_frame.grid_columnconfigure(1, weight=1)

            # Type dropdown (replaces static badge)
            current_type = value_to_type.get(source_type, "Archive") if source_type else "Archive"
            # Auto-detect type from URL if not specified
            if not source_type and url:
                if "youtube.com" in url.lower() or "youtu.be" in url.lower():
                    current_type = "YouTube"
                elif any(p in url.lower() for p in ['.rss', '.xml', '/feed', '/rss']):
                    current_type = "RSS"

            type_var = ctk.StringVar(value=current_type)
            type_dropdown = ctk.CTkOptionMenu(
                row_frame, values=type_options, variable=type_var,
                width=90, height=28, font=ctk.CTkFont(size=11),
                dynamic_resizing=False
            )
            type_dropdown.grid(row=0, column=0, padx=(5, 5), pady=3)

            # Config dropdown (for newsletters) - initially hidden
            config_var = ctk.StringVar(value=config if config else "(none)")
            config_dropdown = ctk.CTkOptionMenu(
                row_frame, values=available_configs, variable=config_var,
                width=80, height=28, font=ctk.CTkFont(size=11),
                dynamic_resizing=False
            )

            # URL entry
            entry = ctk.CTkEntry(row_frame)
            entry.insert(0, url)
            entry.grid(row=0, column=1, sticky="ew", padx=(0, 5), pady=3)

            # Store extra metadata on the entry widget
            entry._source_name = name

            # Show/hide config dropdown based on type
            def on_type_change(choice):
                if choice == "Newsletter":
                    config_dropdown.grid(row=0, column=2, padx=(0, 5), pady=3)
                else:
                    config_dropdown.grid_forget()
                    config_var.set("(none)")

            type_dropdown.configure(command=on_type_change)

            # Initial visibility
            if current_type == "Newsletter":
                config_dropdown.grid(row=0, column=2, padx=(0, 5), pady=3)

            # Enabled checkbox
            var_enabled = ctk.BooleanVar(value=enabled)
            chk = ctk.CTkCheckBox(row_frame, text="", variable=var_enabled, width=24)
            chk.grid(row=0, column=3, padx=(0, 5), pady=3)

            widgets.append((entry, var_enabled, type_var, config_var))
            return row_frame

        for idx, src in enumerate(sources):
            add_source_row(
                idx,
                src.get("url", ""),
                src.get("enabled", True),
                src.get("type"),
                src.get("config"),
                src.get("name")
            )

        def add_source():
            idx = len(widgets)
            add_source_row(idx)

        def bulk_import():
            dlg = ctk.CTkToplevel(editor)
            dlg.title("Bulk Import Sources")
            dlg.geometry("500x400")
            dlg.transient(editor)
            dlg.lift()
            ctk.CTkLabel(dlg, text="Paste one URL per line (type auto-detected):").pack(pady=10)
            txt = ctk.CTkTextbox(dlg, width=460, height=280)
            txt.pack(padx=10, pady=10, fill="both", expand=True)

            def apply_import():
                lines = [ln.strip() for ln in txt.get("0.0", "end-1c").splitlines()]
                for ln in lines:
                    if not ln:
                        continue
                    idx = len(widgets)
                    add_source_row(idx, ln, True)
                dlg.destroy()

            ctk.CTkButton(dlg, text="Import", command=apply_import).pack(pady=10)

        def select_all():
            for entry, var_enabled, type_var, config_var in widgets:
                var_enabled.set(True)

        def deselect_all():
            for entry, var_enabled, type_var, config_var in widgets:
                var_enabled.set(False)

        def save_sources():
            new_sources = []
            for entry, var_enabled, type_var, config_var in widgets:
                url = entry.get().strip()
                if url:
                    # Get type from dropdown
                    type_display = type_var.get()
                    source_type = type_to_value.get(type_display, "article_archive")

                    # Build source dict
                    source_dict = {
                        "url": url,
                        "enabled": bool(var_enabled.get()),
                        "type": source_type,
                    }

                    # Add config for newsletter sources
                    if source_type == "newsletter":
                        config_name = config_var.get()
                        if config_name and config_name != "(none)":
                            source_dict["config"] = config_name

                    # Preserve name if available
                    if hasattr(entry, '_source_name') and entry._source_name:
                        source_dict["name"] = entry._source_name

                    new_sources.append(source_dict)
            try:
                # Save to user data directory (not bundled resources)
                json.dump({"sources": new_sources}, open(sources_json_user, "w"), indent=2)
                # also write channels.txt for compatibility
                with open(channels_file_user, "w", encoding="utf-8") as f:
                    f.write("\n".join([s["url"] for s in new_sources]))
                editor.destroy()
                self.label_status.configure(text="Sources updated.", text_color="green")
            except Exception as e:
                self.label_status.configure(text=f"Error saving sources: {e}", text_color="red")

        def export_csv():
            """Export sources to a CSV file for backup."""
            from tkinter import filedialog
            import csv

            # Gather current sources from widgets
            current_sources = []
            for entry, var_enabled, type_var, config_var in widgets:
                url = entry.get().strip()
                if url:
                    type_display = type_var.get()
                    source_type = type_to_value.get(type_display, "article_archive")
                    config_name = config_var.get() if source_type == "newsletter" else ""
                    current_sources.append({
                        "url": url,
                        "type": source_type,
                        "config": config_name if config_name != "(none)" else "",
                        "enabled": "Yes" if var_enabled.get() else "No"
                    })

            if not current_sources:
                self.label_status.configure(text="No sources to export.", text_color="orange")
                return

            # Ask user for save location
            filepath = filedialog.asksaveasfilename(
                parent=editor,
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile="news_sources_backup.csv"
            )

            if not filepath:
                return  # User cancelled

            try:
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=["url", "type", "config", "enabled"])
                    writer.writeheader()
                    writer.writerows(current_sources)
                self.label_status.configure(text=f"Exported {len(current_sources)} sources to CSV.", text_color="green")
            except Exception as e:
                self.label_status.configure(text=f"Export error: {e}", text_color="red")

        # Button row - always visible at bottom, stacked in two rows if needed
        btn_row = ctk.CTkFrame(editor, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(5, 15), side="bottom")

        # First row of buttons
        btn_row1 = ctk.CTkFrame(btn_row, fg_color="transparent")
        btn_row1.pack(fill="x", pady=(0, 5))

        ctk.CTkButton(btn_row1, text="Add Source", command=add_source, width=100).pack(side="left", padx=4)
        ctk.CTkButton(btn_row1, text="Bulk Import", command=bulk_import, width=100).pack(side="left", padx=4)
        ctk.CTkButton(btn_row1, text="Export CSV", command=export_csv, fg_color="#2E86AB", width=100).pack(side="left", padx=4)
        ctk.CTkButton(btn_row1, text="Select All", command=select_all, fg_color="green", width=90).pack(side="left", padx=4)
        ctk.CTkButton(btn_row1, text="Deselect All", command=deselect_all, fg_color="gray", width=100).pack(side="left", padx=4)

        # Second row with Save button prominently placed
        btn_row2 = ctk.CTkFrame(btn_row, fg_color="transparent")
        btn_row2.pack(fill="x")

        ctk.CTkButton(btn_row2, text="Save Changes", command=save_sources, width=200, height=35,
                     font=ctk.CTkFont(size=14, weight="bold")).pack(side="right", padx=5)

    def open_config_manager(self):
        """Open the extraction config manager dialog."""
        import json

        config_dir = os.path.join(os.path.dirname(__file__), "extraction_instructions")
        os.makedirs(config_dir, exist_ok=True)

        manager = ctk.CTkToplevel(self)
        manager.title("Manage Extraction Configs")
        manager.geometry("900x650")
        manager.minsize(800, 550)
        manager.transient(self)
        manager.lift()

        # Main container with two panes
        main_frame = ctk.CTkFrame(manager, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        # Left pane - config list
        left_frame = ctk.CTkFrame(main_frame, width=200)
        left_frame.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        left_frame.grid_propagate(False)

        ctk.CTkLabel(left_frame, text="Configs", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))

        # Scrollable list of configs
        config_list_frame = ctk.CTkScrollableFrame(left_frame, width=180)
        config_list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Right pane - config editor
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)

        # Editor header
        editor_header = ctk.CTkFrame(right_frame, fg_color="transparent")
        editor_header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        editor_header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(editor_header, text="Name:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        name_entry = ctk.CTkEntry(editor_header, width=300)
        name_entry.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(editor_header, text="Description:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(10, 0))
        desc_entry = ctk.CTkEntry(editor_header, width=500)
        desc_entry.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(10, 0))

        # Editor content - scrollable
        editor_scroll = ctk.CTkScrollableFrame(right_frame)
        editor_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        editor_scroll.grid_columnconfigure(0, weight=1)

        # Include Patterns
        ctk.CTkLabel(editor_scroll, text="Include Patterns (one per line):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", pady=(5, 2))
        ctk.CTkLabel(editor_scroll, text="Items must match at least one pattern to be included. Leave empty to include all.", text_color="gray").grid(row=1, column=0, sticky="w")
        include_text = ctk.CTkTextbox(editor_scroll, height=80)
        include_text.grid(row=2, column=0, sticky="ew", pady=(2, 10))

        # Exclude Patterns
        ctk.CTkLabel(editor_scroll, text="Exclude Patterns (one per line):", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, sticky="w", pady=(5, 2))
        ctk.CTkLabel(editor_scroll, text="Items matching any pattern are excluded, even if they match include patterns.", text_color="gray").grid(row=4, column=0, sticky="w")
        exclude_text = ctk.CTkTextbox(editor_scroll, height=80)
        exclude_text.grid(row=5, column=0, sticky="ew", pady=(2, 10))

        # Blocked Domains
        ctk.CTkLabel(editor_scroll, text="Blocked Domains (one per line):", font=ctk.CTkFont(weight="bold")).grid(row=6, column=0, sticky="w", pady=(5, 2))
        ctk.CTkLabel(editor_scroll, text="Links to these domains are never extracted.", text_color="gray").grid(row=7, column=0, sticky="w")
        blocked_text = ctk.CTkTextbox(editor_scroll, height=60)
        blocked_text.grid(row=8, column=0, sticky="ew", pady=(2, 10))

        # Allowed Domains
        ctk.CTkLabel(editor_scroll, text="Allowed Domains (one per line, optional):", font=ctk.CTkFont(weight="bold")).grid(row=9, column=0, sticky="w", pady=(5, 2))
        ctk.CTkLabel(editor_scroll, text="If specified, only links to these domains are extracted. Leave empty to allow all.", text_color="gray").grid(row=10, column=0, sticky="w")
        allowed_text = ctk.CTkTextbox(editor_scroll, height=60)
        allowed_text.grid(row=11, column=0, sticky="ew", pady=(2, 10))

        # Exclude Sections
        ctk.CTkLabel(editor_scroll, text="Exclude Sections (one per line):", font=ctk.CTkFont(weight="bold")).grid(row=12, column=0, sticky="w", pady=(5, 2))
        ctk.CTkLabel(editor_scroll, text="Section headers to skip entirely (e.g., 'Sponsored', 'Ads').", text_color="gray").grid(row=13, column=0, sticky="w")
        exclude_sections_text = ctk.CTkTextbox(editor_scroll, height=60)
        exclude_sections_text.grid(row=14, column=0, sticky="ew", pady=(2, 10))

        # Source URL Patterns (for URL detection in Audio Content section)
        ctk.CTkLabel(editor_scroll, text="Source URL Patterns (one per line):", font=ctk.CTkFont(weight="bold")).grid(row=15, column=0, sticky="w", pady=(5, 2))
        ctk.CTkLabel(editor_scroll, text="Domains that match this config for URL detection (e.g., 'execsum.co', 'newsletter.example.com').", text_color="gray").grid(row=16, column=0, sticky="w")
        source_url_text = ctk.CTkTextbox(editor_scroll, height=60)
        source_url_text.grid(row=17, column=0, sticky="ew", pady=(2, 10))

        # CSV Columns (for Google Sheets export)
        ctk.CTkLabel(editor_scroll, text="CSV Columns (one per line):", font=ctk.CTkFont(weight="bold")).grid(row=18, column=0, sticky="w", pady=(5, 2))
        ctk.CTkLabel(editor_scroll, text="Column headers for Sheets export (e.g., 'title', 'url', 'date_published'). Order determines column order.", text_color="gray").grid(row=19, column=0, sticky="w")
        csv_columns_text = ctk.CTkTextbox(editor_scroll, height=60)
        csv_columns_text.grid(row=20, column=0, sticky="ew", pady=(2, 10))

        # State tracking
        current_config = {"filename": None}
        config_buttons = {}

        def load_configs():
            """Load all config files and populate the list."""
            # Clear existing buttons
            for widget in config_list_frame.winfo_children():
                widget.destroy()
            config_buttons.clear()

            configs = []
            if os.path.exists(config_dir):
                for f in os.listdir(config_dir):
                    if f.endswith(".json") and not f.startswith("_"):
                        configs.append(f)

            configs.sort()

            for cfg_file in configs:
                display_name = cfg_file.replace(".json", "").replace("_", " ").title()
                btn = ctk.CTkButton(
                    config_list_frame,
                    text=display_name,
                    fg_color="transparent",
                    text_color=("gray10", "gray90"),
                    hover_color=("gray70", "gray30"),
                    anchor="w",
                    command=lambda f=cfg_file: select_config(f)
                )
                btn.pack(fill="x", pady=2)
                config_buttons[cfg_file] = btn

            # Add "New Config" button at the bottom
            ctk.CTkButton(
                config_list_frame,
                text="+ New Config",
                fg_color="green",
                command=create_new_config
            ).pack(fill="x", pady=(10, 2))

        def select_config(filename):
            """Load a config into the editor."""
            # Update button highlighting
            for f, btn in config_buttons.items():
                if f == filename:
                    btn.configure(fg_color=("gray75", "gray25"))
                else:
                    btn.configure(fg_color="transparent")

            current_config["filename"] = filename
            filepath = os.path.join(config_dir, filename)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception as e:
                self.label_status.configure(text=f"Error loading config: {e}", text_color="red")
                return

            # Populate editor fields
            name_entry.delete(0, "end")
            name_entry.insert(0, config.get("name", ""))

            desc_entry.delete(0, "end")
            desc_entry.insert(0, config.get("description", ""))

            include_text.delete("0.0", "end")
            include_patterns = config.get("include_patterns", [])
            if include_patterns:
                include_text.insert("0.0", "\n".join(include_patterns))

            exclude_text.delete("0.0", "end")
            exclude_patterns = config.get("exclude_patterns", [])
            if exclude_patterns:
                exclude_text.insert("0.0", "\n".join(exclude_patterns))

            blocked_text.delete("0.0", "end")
            blocked_domains = config.get("blocked_domains", [])
            if blocked_domains:
                blocked_text.insert("0.0", "\n".join(blocked_domains))

            allowed_text.delete("0.0", "end")
            allowed_domains = config.get("allowed_domains", [])
            if allowed_domains:
                allowed_text.insert("0.0", "\n".join(allowed_domains))

            exclude_sections_text.delete("0.0", "end")
            exclude_sections = config.get("exclude_sections", [])
            if exclude_sections:
                exclude_sections_text.insert("0.0", "\n".join(exclude_sections))

            source_url_text.delete("0.0", "end")
            source_url_patterns = config.get("source_url_patterns", [])
            if source_url_patterns:
                source_url_text.insert("0.0", "\n".join(source_url_patterns))

            csv_columns_text.delete("0.0", "end")
            csv_columns = config.get("csv_columns", [])
            if csv_columns:
                csv_columns_text.insert("0.0", "\n".join(csv_columns))

        def create_new_config():
            """Create a new config from template."""
            # Dialog for config name
            dialog = ctk.CTkToplevel(manager)
            dialog.title("New Config")
            dialog.geometry("400x150")
            dialog.transient(manager)
            dialog.lift()

            ctk.CTkLabel(dialog, text="Config Name:").pack(pady=(20, 5))
            new_name_entry = ctk.CTkEntry(dialog, width=300)
            new_name_entry.pack(pady=5)
            new_name_entry.focus()

            def create():
                name = new_name_entry.get().strip()
                if not name:
                    return

                # Create filename from name
                filename = name.lower().replace(" ", "_").replace("-", "_") + ".json"
                filepath = os.path.join(config_dir, filename)

                if os.path.exists(filepath):
                    self.label_status.configure(text=f"Config '{name}' already exists!", text_color="red")
                    dialog.destroy()
                    return

                # Create new config with template structure
                new_config = {
                    "name": name,
                    "description": f"Custom extraction config for {name}",
                    "include_patterns": [],
                    "exclude_patterns": ["subscribe", "unsubscribe", "advertisement", "sponsored"],
                    "exclude_sections": [],
                    "allowed_domains": [],
                    "blocked_domains": ["twitter.com", "x.com", "facebook.com", "linkedin.com"],
                    "source_url_patterns": [],
                    "csv_columns": ["title", "url", "date_published"],
                    "require_url": False,
                    "require_include_pattern": False,
                    "notes": ""
                }

                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(new_config, f, indent=2)
                    dialog.destroy()
                    load_configs()
                    select_config(filename)
                    self.refresh_config_dropdown()
                    self.label_status.configure(text=f"Created config: {name}", text_color="green")
                except Exception as e:
                    self.label_status.configure(text=f"Error creating config: {e}", text_color="red")

            ctk.CTkButton(dialog, text="Create", command=create).pack(pady=20)

        def save_current_config():
            """Save the current config."""
            if not current_config["filename"]:
                self.label_status.configure(text="No config selected", text_color="orange")
                return

            filepath = os.path.join(config_dir, current_config["filename"])

            # Read existing config to preserve extra fields
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception:
                config = {}

            # Update with editor values
            config["name"] = name_entry.get().strip()
            config["description"] = desc_entry.get().strip()

            # Parse text areas into lists
            def text_to_list(textbox):
                content = textbox.get("0.0", "end-1c").strip()
                if not content:
                    return []
                return [line.strip() for line in content.split("\n") if line.strip()]

            config["include_patterns"] = text_to_list(include_text)
            config["exclude_patterns"] = text_to_list(exclude_text)
            config["blocked_domains"] = text_to_list(blocked_text)
            config["allowed_domains"] = text_to_list(allowed_text)
            config["exclude_sections"] = text_to_list(exclude_sections_text)
            config["source_url_patterns"] = text_to_list(source_url_text)
            config["csv_columns"] = text_to_list(csv_columns_text)

            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
                self.label_status.configure(text=f"Saved: {current_config['filename']}", text_color="green")
            except Exception as e:
                self.label_status.configure(text=f"Error saving: {e}", text_color="red")

        def duplicate_config():
            """Duplicate the current config."""
            if not current_config["filename"]:
                return

            # Dialog for new name
            dialog = ctk.CTkToplevel(manager)
            dialog.title("Duplicate Config")
            dialog.geometry("400x150")
            dialog.transient(manager)
            dialog.lift()

            original_name = current_config["filename"].replace(".json", "").replace("_", " ").title()
            ctk.CTkLabel(dialog, text=f"Duplicating: {original_name}").pack(pady=(10, 5))
            ctk.CTkLabel(dialog, text="New Config Name:").pack(pady=5)
            new_name_entry = ctk.CTkEntry(dialog, width=300)
            new_name_entry.pack(pady=5)
            new_name_entry.insert(0, f"{original_name} Copy")
            new_name_entry.focus()

            def duplicate():
                name = new_name_entry.get().strip()
                if not name:
                    return

                new_filename = name.lower().replace(" ", "_").replace("-", "_") + ".json"
                new_filepath = os.path.join(config_dir, new_filename)

                if os.path.exists(new_filepath):
                    self.label_status.configure(text=f"Config '{name}' already exists!", text_color="red")
                    dialog.destroy()
                    return

                # Read original
                original_path = os.path.join(config_dir, current_config["filename"])
                try:
                    with open(original_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    config["name"] = name
                    with open(new_filepath, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2)
                    dialog.destroy()
                    load_configs()
                    select_config(new_filename)
                    self.refresh_config_dropdown()
                    self.label_status.configure(text=f"Duplicated as: {name}", text_color="green")
                except Exception as e:
                    self.label_status.configure(text=f"Error duplicating: {e}", text_color="red")

            ctk.CTkButton(dialog, text="Duplicate", command=duplicate).pack(pady=15)

        def delete_config():
            """Delete the current config."""
            if not current_config["filename"]:
                return

            # Confirmation dialog
            dialog = ctk.CTkToplevel(manager)
            dialog.title("Delete Config")
            dialog.geometry("400x150")
            dialog.transient(manager)
            dialog.lift()

            config_name = current_config["filename"].replace(".json", "").replace("_", " ").title()
            ctk.CTkLabel(dialog, text=f"Delete '{config_name}'?", font=ctk.CTkFont(weight="bold")).pack(pady=(20, 10))
            ctk.CTkLabel(dialog, text="This cannot be undone.", text_color="red").pack()

            btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            btn_frame.pack(pady=20)

            def confirm_delete():
                filepath = os.path.join(config_dir, current_config["filename"])
                try:
                    os.remove(filepath)
                    dialog.destroy()
                    current_config["filename"] = None
                    load_configs()
                    # Clear editor
                    name_entry.delete(0, "end")
                    desc_entry.delete(0, "end")
                    include_text.delete("0.0", "end")
                    exclude_text.delete("0.0", "end")
                    blocked_text.delete("0.0", "end")
                    allowed_text.delete("0.0", "end")
                    exclude_sections_text.delete("0.0", "end")
                    self.refresh_config_dropdown()
                    self.label_status.configure(text=f"Deleted: {config_name}", text_color="green")
                except Exception as e:
                    self.label_status.configure(text=f"Error deleting: {e}", text_color="red")

            ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", command=dialog.destroy).pack(side="left", padx=10)
            ctk.CTkButton(btn_frame, text="Delete", fg_color="red", command=confirm_delete).pack(side="left", padx=10)

        # Bottom button row
        btn_row = ctk.CTkFrame(right_frame, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        ctk.CTkButton(btn_row, text="Save", width=100, command=save_current_config).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="Duplicate", width=100, fg_color="gray", command=duplicate_config).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="Delete", width=100, fg_color="red", command=delete_config).pack(side="left", padx=5)

        # Load initial configs
        load_configs()

    def refresh_config_dropdown(self):
        """Refresh the extraction config dropdown with current configs."""
        config_values = self._get_extraction_configs()
        self.extract_config_combo.configure(values=config_values)

    # Default instructions template for YouTube summarization
    DEFAULT_INSTRUCTIONS_TEMPLATE = """# Custom Instructions Template (YouTube)
# These instructions are added to the AI summarization prompt under "USER PROFILE & PREFERENCES"
# The system already includes rules for deduplication, audio formatting, comprehensive coverage, etc.
# Use this section to add your personal preferences and focus areas.

# Example custom instructions (uncomment and modify as needed):

# FOCUS AREAS:
# - Prioritize coverage of: [your topics, e.g., "AI/ML developments", "crypto market analysis"]
# - De-emphasize or skip: [topics you don't care about]

# STYLE PREFERENCES:
# - Keep summaries [concise/detailed]
# - Include specific price levels and technical analysis when available
# - Highlight contrarian or unique perspectives

# PERSONAL CONTEXT:
# - I am a [role, e.g., "software engineer", "trader", "analyst"]
# - I'm particularly interested in [specific interests]
# - I prefer [any formatting preferences]"""

    # Default instructions template for Article cleaning/summarization
    DEFAULT_ARTICLE_INSTRUCTIONS_TEMPLATE = """# Article Processing Instructions
# These instructions customize how articles are cleaned and prepared for audio.
# The system already handles removing ads, navigation, and formatting for speech.
# Use this section to add your personal preferences.

# CONTENT FOCUS:
# - Prioritize sections about: [your topics]
# - Skip or minimize: [sections you don't need, e.g., "author bios", "related articles"]

# SUMMARIZATION STYLE:
# - Level of detail: [full article / key points only / executive summary]
# - Preserve: [quotes, statistics, specific data points]
# - Expand abbreviations: [yes/no, or specific ones]

# OUTPUT FORMAT:
# - Length preference: [concise / moderate / comprehensive]
# - Include source attribution: [yes/no]
# - Separate multiple articles with: [clear breaks / transitions]

# PERSONAL CONTEXT:
# - I'm reading for: [research, news briefing, learning, entertainment]
# - My background: [helps AI calibrate technical depth]"""

    def _load_instruction_profiles(self):
        """Load instruction profiles from JSON file in persistent data directory."""
        data_dir = get_data_directory()
        profiles_file = os.path.join(data_dir, "instruction_profiles.json")

        default_profiles = {
            "active_profile": "Default",
            "profiles": {
                "Default": {
                    "name": "Default",
                    "description": "Default profile with template",
                    "instructions": self.DEFAULT_INSTRUCTIONS_TEMPLATE,
                    "article_instructions": self.DEFAULT_ARTICLE_INSTRUCTIONS_TEMPLATE
                }
            }
        }

        # Try to load existing profiles from user data directory
        if os.path.exists(profiles_file):
            try:
                with open(profiles_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Ensure all profiles have article_instructions (migration for existing profiles)
                    for profile_name, profile_data in loaded.get("profiles", {}).items():
                        if not profile_data.get("article_instructions", "").strip():
                            profile_data["article_instructions"] = self.DEFAULT_ARTICLE_INSTRUCTIONS_TEMPLATE
                        # Also ensure YouTube instructions have template if empty
                        if profile_name == "Default" and not profile_data.get("instructions", "").strip():
                            profile_data["instructions"] = self.DEFAULT_INSTRUCTIONS_TEMPLATE
                    return loaded
            except Exception:
                pass

        # Try to migrate from old location (bundled app directory) - one-time migration
        old_profiles_file = os.path.join(os.path.dirname(__file__), "instruction_profiles.json")
        if os.path.exists(old_profiles_file):
            try:
                with open(old_profiles_file, "r", encoding="utf-8") as f:
                    migrated = json.load(f)
                # Save to new location
                self._save_instruction_profiles(migrated)
                return migrated
            except Exception:
                pass

        # Try to migrate from custom_instructions.txt (old or new location)
        for instructions_file in [
            os.path.join(data_dir, "custom_instructions.txt"),
            os.path.join(os.path.dirname(__file__), "custom_instructions.txt")
        ]:
            if os.path.exists(instructions_file):
                try:
                    with open(instructions_file, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    if content:
                        default_profiles["profiles"]["Default"]["instructions"] = content
                        break
                except Exception:
                    pass

        return default_profiles

    def _save_instruction_profiles(self, profiles_data):
        """Save instruction profiles to JSON file in persistent data directory."""
        data_dir = get_data_directory()
        profiles_file = os.path.join(data_dir, "instruction_profiles.json")
        try:
            with open(profiles_file, "w", encoding="utf-8") as f:
                json.dump(profiles_data, f, indent=2)
            return True
        except Exception as e:
            self.label_status.configure(text=f"Error saving profiles: {e}", text_color="red")
            return False

    def _sync_active_instructions(self, profiles_data):
        """Sync the active profile's instructions to custom_instructions.txt for compatibility."""
        # Save to both data directory and script directory for compatibility
        data_dir = get_data_directory()
        instructions_files = [
            os.path.join(data_dir, "custom_instructions.txt"),
            os.path.join(os.path.dirname(__file__), "custom_instructions.txt")
        ]
        active_name = profiles_data.get("active_profile", "Default")
        profiles = profiles_data.get("profiles", {})

        if active_name in profiles:
            instructions = profiles[active_name].get("instructions", "")
            for instructions_file in instructions_files:
                try:
                    with open(instructions_file, "w", encoding="utf-8") as f:
                        f.write(instructions)
                except Exception:
                    pass  # May fail for bundled location, which is fine

    def _get_active_article_instructions(self):
        """Get the article instructions from the active profile."""
        profiles_data = self._load_instruction_profiles()
        active_name = profiles_data.get("active_profile", "Default")
        profiles = profiles_data.get("profiles", {})

        if active_name in profiles:
            instructions = profiles[active_name].get("article_instructions", "")
            # Filter out comment lines (starting with #) and empty lines
            if instructions:
                lines = instructions.split('\n')
                content_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
                return '\n'.join(content_lines).strip()
        return ""

    def _get_active_youtube_instructions(self):
        """Get the YouTube instructions from the active profile."""
        profiles_data = self._load_instruction_profiles()
        active_name = profiles_data.get("active_profile", "Default")
        profiles = profiles_data.get("profiles", {})

        if active_name in profiles:
            instructions = profiles[active_name].get("instructions", "")
            # Filter out comment lines (starting with #) and empty lines
            if instructions:
                lines = instructions.split('\n')
                content_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
                return '\n'.join(content_lines).strip()
        return ""

    def open_instructions_editor(self):
        """Open editor for custom summarization instructions with profile management."""
        editor = ctk.CTkToplevel(self)
        editor.title("Custom Instructions")
        editor.geometry("850x720")
        editor.minsize(750, 600)
        editor.transient(self)
        editor.lift()

        # Load profiles
        profiles_data = self._load_instruction_profiles()
        current_profile = [profiles_data.get("active_profile", "Default")]  # Use list for closure mutability

        # Header
        header_frame = ctk.CTkFrame(editor, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 5))

        lbl = ctk.CTkLabel(
            header_frame,
            text="Custom Instructions",
            font=ctk.CTkFont(weight="bold", size=16)
        )
        lbl.pack(side="left")

        # Profile selector row
        profile_frame = ctk.CTkFrame(editor, fg_color="transparent")
        profile_frame.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(profile_frame, text="Profile:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 10))

        profile_names = list(profiles_data.get("profiles", {}).keys())
        if not profile_names:
            profile_names = ["Default"]

        profile_var = ctk.StringVar(value=current_profile[0])
        profile_dropdown = ctk.CTkComboBox(
            profile_frame,
            variable=profile_var,
            values=profile_names,
            width=200,
            state="readonly"
        )
        profile_dropdown.pack(side="left", padx=(0, 10))

        # Profile action buttons
        btn_new = ctk.CTkButton(profile_frame, text="New", width=70, fg_color="gray")
        btn_new.pack(side="left", padx=2)

        btn_duplicate = ctk.CTkButton(profile_frame, text="Duplicate", width=80, fg_color="gray")
        btn_duplicate.pack(side="left", padx=2)

        btn_rename = ctk.CTkButton(profile_frame, text="Rename", width=80, fg_color="gray")
        btn_rename.pack(side="left", padx=2)

        btn_delete = ctk.CTkButton(profile_frame, text="Delete", width=70, fg_color="#8B0000")
        btn_delete.pack(side="left", padx=2)

        # Active indicator
        active_label = ctk.CTkLabel(
            profile_frame,
            text="✓ Active" if current_profile[0] == profiles_data.get("active_profile") else "",
            text_color="green",
            font=ctk.CTkFont(size=12)
        )
        active_label.pack(side="right", padx=10)

        # Description row
        desc_frame = ctk.CTkFrame(editor, fg_color="transparent")
        desc_frame.pack(fill="x", padx=15, pady=(5, 5))

        ctk.CTkLabel(desc_frame, text="Description:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))

        desc_entry = ctk.CTkEntry(desc_frame, width=600, placeholder_text="Brief description of this profile...")
        desc_entry.pack(side="left", fill="x", expand=True)

        # Load initial description
        if current_profile[0] in profiles_data.get("profiles", {}):
            desc = profiles_data["profiles"][current_profile[0]].get("description", "")
            if desc:
                desc_entry.insert(0, desc)

        # Help text
        help_text = ctk.CTkLabel(
            editor,
            text="Define your interests and preferences to customize how AI summaries are generated.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=800
        )
        help_text.pack(pady=(5, 5), padx=15, anchor="w")

        # Tabview for YouTube vs Article instructions
        tabview = ctk.CTkTabview(editor, height=400)
        tabview.pack(padx=15, pady=10, fill="both", expand=True)

        # Create tabs
        tab_youtube = tabview.add("📺 YouTube")
        tab_article = tabview.add("📄 Articles")

        # YouTube instructions tab
        youtube_help = ctk.CTkLabel(
            tab_youtube,
            text="Instructions for summarizing YouTube video transcripts. Applied when processing videos from channels or pasted YouTube URLs.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=780
        )
        youtube_help.pack(pady=(5, 5), padx=10, anchor="w")

        instructions_text = ctk.CTkTextbox(tab_youtube, width=780, height=300, font=ctk.CTkFont(size=13))
        instructions_text.pack(padx=10, pady=5, fill="both", expand=True)

        # Article instructions tab
        article_help = ctk.CTkLabel(
            tab_article,
            text="Instructions for cleaning and processing articles. Applied when generating audio from article URLs or text content.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=780
        )
        article_help.pack(pady=(5, 5), padx=10, anchor="w")

        article_instructions_text = ctk.CTkTextbox(tab_article, width=780, height=300, font=ctk.CTkFont(size=13))
        article_instructions_text.pack(padx=10, pady=5, fill="both", expand=True)

        # Load initial instructions for both tabs
        if current_profile[0] in profiles_data.get("profiles", {}):
            profile = profiles_data["profiles"][current_profile[0]]
            youtube_content = profile.get("instructions", "")
            if youtube_content:
                instructions_text.insert("1.0", youtube_content)
            article_content = profile.get("article_instructions", "")
            if article_content:
                article_instructions_text.insert("1.0", article_content)

        def refresh_dropdown():
            """Refresh the profile dropdown with current profiles."""
            names = list(profiles_data.get("profiles", {}).keys())
            profile_dropdown.configure(values=names)

        def load_profile(name):
            """Load a profile into the editor."""
            instructions_text.delete("1.0", "end")
            article_instructions_text.delete("1.0", "end")
            desc_entry.delete(0, "end")

            if name in profiles_data.get("profiles", {}):
                profile = profiles_data["profiles"][name]
                # Load YouTube instructions
                youtube_content = profile.get("instructions", "")
                if youtube_content:
                    instructions_text.insert("1.0", youtube_content)
                # Load Article instructions
                article_content = profile.get("article_instructions", "")
                if article_content:
                    article_instructions_text.insert("1.0", article_content)
                # Load description
                desc = profile.get("description", "")
                if desc:
                    desc_entry.insert(0, desc)

            current_profile[0] = name

            # Update active indicator
            if name == profiles_data.get("active_profile"):
                active_label.configure(text="✓ Active")
            else:
                active_label.configure(text="")

        def on_profile_change(choice):
            """Handle profile dropdown change."""
            # Save current profile first
            save_current_to_memory()
            # Load new profile
            load_profile(choice)

        profile_dropdown.configure(command=on_profile_change)

        def save_current_to_memory():
            """Save current editor state to profiles_data in memory."""
            name = current_profile[0]
            if name not in profiles_data["profiles"]:
                profiles_data["profiles"][name] = {"name": name}

            profiles_data["profiles"][name]["instructions"] = instructions_text.get("1.0", "end-1c")
            profiles_data["profiles"][name]["article_instructions"] = article_instructions_text.get("1.0", "end-1c")
            profiles_data["profiles"][name]["description"] = desc_entry.get()

        def create_new_profile():
            """Create a new profile."""
            dialog = ctk.CTkInputDialog(
                text="Enter name for new profile:",
                title="New Profile"
            )
            name = dialog.get_input()

            if name and name.strip():
                name = name.strip()
                if name in profiles_data["profiles"]:
                    self.label_status.configure(text=f"Profile '{name}' already exists.", text_color="orange")
                    return

                # Save current first
                save_current_to_memory()

                # Create new profile with default templates
                profiles_data["profiles"][name] = {
                    "name": name,
                    "description": "",
                    "instructions": "",
                    "article_instructions": self.DEFAULT_ARTICLE_INSTRUCTIONS_TEMPLATE
                }

                refresh_dropdown()
                profile_var.set(name)
                load_profile(name)
                self.label_status.configure(text=f"Profile '{name}' created.", text_color="green")

        def duplicate_profile():
            """Duplicate the current profile."""
            dialog = ctk.CTkInputDialog(
                text=f"Enter name for duplicate of '{current_profile[0]}':",
                title="Duplicate Profile"
            )
            name = dialog.get_input()

            if name and name.strip():
                name = name.strip()
                if name in profiles_data["profiles"]:
                    self.label_status.configure(text=f"Profile '{name}' already exists.", text_color="orange")
                    return

                # Save current first
                save_current_to_memory()

                # Duplicate (include article_instructions)
                source = profiles_data["profiles"].get(current_profile[0], {})
                profiles_data["profiles"][name] = {
                    "name": name,
                    "description": source.get("description", "") + " (copy)",
                    "instructions": source.get("instructions", ""),
                    "article_instructions": source.get("article_instructions", self.DEFAULT_ARTICLE_INSTRUCTIONS_TEMPLATE)
                }

                refresh_dropdown()
                profile_var.set(name)
                load_profile(name)
                self.label_status.configure(text=f"Profile '{name}' created from '{current_profile[0]}'.", text_color="green")

        def rename_profile():
            """Rename the current profile."""
            if current_profile[0] == "Default":
                self.label_status.configure(text="Cannot rename the Default profile.", text_color="orange")
                return

            dialog = ctk.CTkInputDialog(
                text=f"Enter new name for '{current_profile[0]}':",
                title="Rename Profile"
            )
            name = dialog.get_input()

            if name and name.strip():
                name = name.strip()
                if name in profiles_data["profiles"]:
                    self.label_status.configure(text=f"Profile '{name}' already exists.", text_color="orange")
                    return

                # Save current first
                save_current_to_memory()

                old_name = current_profile[0]

                # Rename
                profiles_data["profiles"][name] = profiles_data["profiles"].pop(old_name)
                profiles_data["profiles"][name]["name"] = name

                # Update active if needed
                if profiles_data.get("active_profile") == old_name:
                    profiles_data["active_profile"] = name

                refresh_dropdown()
                profile_var.set(name)
                current_profile[0] = name

                # Update active indicator
                if name == profiles_data.get("active_profile"):
                    active_label.configure(text="✓ Active")

                self.label_status.configure(text=f"Profile renamed to '{name}'.", text_color="green")

        def delete_profile():
            """Delete the current profile."""
            if current_profile[0] == "Default":
                self.label_status.configure(text="Cannot delete the Default profile.", text_color="orange")
                return

            if len(profiles_data["profiles"]) <= 1:
                self.label_status.configure(text="Cannot delete the last profile.", text_color="orange")
                return

            # Confirm deletion
            confirm = ctk.CTkInputDialog(
                text=f"Type 'DELETE' to confirm deletion of '{current_profile[0]}':",
                title="Confirm Delete"
            )
            response = confirm.get_input()

            if response and response.strip().upper() == "DELETE":
                old_name = current_profile[0]
                del profiles_data["profiles"][old_name]

                # If deleted profile was active, switch to Default or first available
                if profiles_data.get("active_profile") == old_name:
                    if "Default" in profiles_data["profiles"]:
                        profiles_data["active_profile"] = "Default"
                    else:
                        profiles_data["active_profile"] = list(profiles_data["profiles"].keys())[0]

                refresh_dropdown()
                new_profile = profiles_data.get("active_profile", list(profiles_data["profiles"].keys())[0])
                profile_var.set(new_profile)
                load_profile(new_profile)
                self.label_status.configure(text=f"Profile '{old_name}' deleted.", text_color="green")

        # Wire up buttons
        btn_new.configure(command=create_new_profile)
        btn_duplicate.configure(command=duplicate_profile)
        btn_rename.configure(command=rename_profile)
        btn_delete.configure(command=delete_profile)

        def clear_instructions():
            """Clear the instructions text area for the current tab."""
            current_tab = tabview.get()
            if "YouTube" in current_tab:
                instructions_text.delete("1.0", "end")
            else:
                article_instructions_text.delete("1.0", "end")

        def reset_to_template():
            """Reset instructions to the default template for the current tab."""
            current_tab = tabview.get()
            if "YouTube" in current_tab:
                instructions_text.delete("1.0", "end")
                instructions_text.insert("1.0", self.DEFAULT_INSTRUCTIONS_TEMPLATE)
                self.label_status.configure(text="YouTube instructions reset to template.", text_color="green")
            else:
                article_instructions_text.delete("1.0", "end")
                article_instructions_text.insert("1.0", self.DEFAULT_ARTICLE_INSTRUCTIONS_TEMPLATE)
                self.label_status.configure(text="Article instructions reset to template.", text_color="green")

        def save_and_close():
            """Save all profiles and close the editor."""
            save_current_to_memory()

            if self._save_instruction_profiles(profiles_data):
                # Sync active profile to custom_instructions.txt for compatibility
                self._sync_active_instructions(profiles_data)
                editor.destroy()
                self.label_status.configure(
                    text=f"Profiles saved. Active: {profiles_data.get('active_profile', 'Default')}",
                    text_color="green"
                )

        def set_as_active():
            """Set the current profile as the active profile."""
            save_current_to_memory()
            profiles_data["active_profile"] = current_profile[0]
            active_label.configure(text="✓ Active")
            self.label_status.configure(text=f"'{current_profile[0]}' is now the active profile.", text_color="green")

        # Button row
        btn_frame = ctk.CTkFrame(editor, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(5, 15), side="bottom")

        ctk.CTkButton(btn_frame, text="Clear", command=clear_instructions, fg_color="gray", width=70).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="Reset to Template", command=reset_to_template, fg_color="#8B4513", width=130).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="Set as Active", command=set_as_active, fg_color="#1f538d", width=110).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="Save & Close", command=save_and_close, width=180, height=35,
                     font=ctk.CTkFont(size=14, weight="bold")).pack(side="right", padx=5)

    def _clear_selected_file(self):
        self.selected_file_paths = []
        if hasattr(self, "btn_transcribe"):
            self.btn_transcribe.configure(state="disabled")
        if hasattr(self, "files_combo"):
            self.files_combo.configure(values=["No files selected"])
            self.files_combo.set("No files selected")

    def upload_text_file(self):
        """Open file dialog and upload a text file to load into the News Summary textbox."""
        data_dir = get_data_directory()
        file_path = filedialog.askopenfilename(
            initialdir=data_dir,
            filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Load content into the main textbox
            self.textbox.delete("0.0", "end")
            self.textbox.insert("0.0", content)
            self._placeholder.place_forget()

            filename = os.path.basename(file_path)
            self.label_status.configure(text=f"Loaded: {filename}", text_color="green")
        except Exception as e:
            self.label_status.configure(text=f"Error loading file: {e}", text_color="red")

    def upload_audio_file(self):
        """Open file dialog and upload audio/video files for transcription (Advanced section)."""
        data_dir = get_data_directory()
        file_paths = filedialog.askopenfilenames(
            initialdir=data_dir,
            filetypes=(("Audio files", "*.mp3 *.wav *.m4a"), ("All files", "*.*"))
        )

        if not file_paths:
            return

        self.selected_file_paths = list(file_paths)

        # Update combo in Advanced section
        count = len(file_paths)
        filenames = [os.path.basename(fp) for fp in file_paths]

        if count == 1:
            self.files_combo.configure(values=filenames)
            self.files_combo.set(filenames[0])
            self.label_status.configure(text="1 audio file selected. Press Transcribe.", text_color="blue")
        else:
            header = f"{count} files selected"
            self.files_combo.configure(values=[header] + filenames)
            self.files_combo.set(header)
            self.label_status.configure(text=f"{count} audio files selected. Press Transcribe.", text_color="blue")

        # Enable transcribe button
        self.btn_transcribe.configure(state="normal")

    def start_transcription(self):
        """Process selected files: transcribe audio and save to Transcriptions folder."""
        if not self.selected_file_paths:
            self.label_status.configure(text="No files selected.", text_color="orange")
            return

        # Check if transcription service is available
        has_audio = any(os.path.splitext(fp)[1].lower() in {".mp3", ".wav", ".m4a"} for fp in self.selected_file_paths)
        if has_audio:
            if not self.transcription_service.is_available():
                self.label_status.configure(text="Transcription not available.", text_color="red")
                self.show_transcription_guide()
                return

        self.btn_transcribe.configure(state="disabled")
        if hasattr(self, "btn_upload_audio"):
            self.btn_upload_audio.configure(state="disabled")
        
        # Create output directory
        out_dir = os.path.join(os.path.dirname(__file__), "Transcriptions")
        os.makedirs(out_dir, exist_ok=True)

        def process_thread():
            processed_count = 0
            total = len(self.selected_file_paths)
            
            for i, file_path in enumerate(self.selected_file_paths, 1):
                ext = os.path.splitext(file_path)[1].lower()
                filename = os.path.basename(file_path)
                
                # Generate output filename with timestamp
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                out_name = f"{timestamp}_{filename}.txt"
                out_path = os.path.join(out_dir, out_name)
                
                try:
                    result_text = ""
                    if ext == ".txt":
                        # Just copy/save text file content
                        with open(file_path, 'r', encoding='utf-8') as f:
                            result_text = f.read()
                        self.after(0, lambda f=filename: self.label_status.configure(text=f"[{i}/{total}] Saving text: {f}...", text_color="blue"))
                    
                    elif ext in {".mp3", ".wav", ".m4a"}:
                        self.after(0, lambda f=filename: self.label_status.configure(text=f"[{i}/{total}] Transcribing: {f}...", text_color="orange"))
                        # Use transcription service (supports local and future cloud backends)
                        transcript = self.transcription_service.transcribe(file_path, model_size="base")
                        if transcript:
                            result_text = transcript
                        else:
                            result_text = "(No speech detected)"
                    
                    # Write to file
                    if result_text:
                        with open(out_path, "w", encoding="utf-8") as f:
                            f.write(result_text)
                        processed_count += 1
                        
                except Exception as e:
                    self.after(0, lambda f=filename, err=str(e): self.label_status.configure(text=f"Error {f}: {err}", text_color="red"))
            
            def finish():
                self.btn_transcribe.configure(state="normal")
                if hasattr(self, "btn_upload_audio"):
                    self.btn_upload_audio.configure(state="normal")
                if processed_count > 0:
                    self.label_status.configure(text=f"Done! {processed_count} files saved to 'Transcriptions/'", text_color="green")
                    # Optionally open the folder?
                    # if sys.platform == "darwin": subprocess.run(["open", out_dir])
                else:
                    self.label_status.configure(text="Processing complete. No output generated.", text_color="orange")

            self.after(0, finish)

        threading.Thread(target=process_thread, daemon=True).start()
    def show_transcription_guide(self):
        """Show transcription setup guide based on current service status."""
        from transcription_service import check_ffmpeg, check_system_whisper

        dlg = ctk.CTkToplevel(self)
        dlg.title("Transcription Setup Guide")
        dlg.geometry("600x480")
        dlg.minsize(600, 480)
        frame = ctk.CTkScrollableFrame(dlg)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        title = ctk.CTkLabel(frame, text="Enable Transcription", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(anchor="w", pady=(0,8))

        # Check current status
        has_ffmpeg = _cached_check_ffmpeg()
        has_whisper, _ = check_system_whisper()
        is_frozen = getattr(sys, 'frozen', False)

        info = []
        info.append("This app uses faster-whisper (OpenAI Whisper) for speech-to-text.")
        info.append("")

        if self.transcription_service.is_available():
            backend = self.transcription_service.get_backend()
            info.append(f"✓ Transcription is ready! (Backend: {backend.value})")
        else:
            info.append("Current status:")
            if not has_ffmpeg:
                info.append("  ✗ ffmpeg: NOT FOUND")
            else:
                info.append("  ✓ ffmpeg: installed")

            if not has_whisper:
                info.append("  ✗ faster-whisper: NOT FOUND")
            else:
                info.append("  ✓ faster-whisper: installed")

            info.append("")
            info.append("Install steps:")
            info.append("")
            info.append("1) Install ffmpeg:")
            info.append("   • macOS: brew install ffmpeg")
            info.append("   • Windows: choco install ffmpeg (or ffmpeg.org)")
            info.append("   • Linux: sudo apt install ffmpeg")
            info.append("")
            info.append("2) Install faster-whisper:")
            info.append("   pip install faster-whisper")

            if is_frozen:
                info.append("")
                info.append("Note: This is a packaged app. faster-whisper must be")
                info.append("installed in your SYSTEM Python, not a virtual env.")
                info.append("")
                info.append("After installing, restart the app to detect it.")

        text = ctk.CTkTextbox(frame, width=560, height=320)
        text.pack(fill="both", expand=True)
        text.insert("0.0", "\n".join(info))
        text.configure(state="disabled")
        ctk.CTkButton(dlg, text="Close", fg_color="gray", command=dlg.destroy).pack(pady=8)
    def toggle_http_server(self):
        """Placeholder for removed HTTP server feature."""
        self.label_status.configure(text="Local server feature removed", text_color="orange")

    def play_sample(self):
        """Play a voice sample using the audio generator."""
        voice = self.voice_var.get()
        self.audio_generator.play_sample(voice)

    def _play_voice_sample(self, voice_id: str):
        """Play a sample for a specific voice and select it."""
        self.voice_var.set(voice_id)
        self.audio_generator.play_sample(voice_id)

    def play_gtts_sample(self):
        """Play a gTTS sample to demonstrate the fast voice quality."""
        self.audio_generator.play_gtts_sample()

    def run_script(self, script_name, output_name, extra_args=None, env_vars=None):
        """Run a script using the audio generator.
        
        Args:
            script_name: Name of script to run
            output_name: Description of expected output
            extra_args: Additional command line arguments
            env_vars: Additional environment variables
        """
        extra_args = extra_args or []
        
        # Disable buttons during execution
        self.btn_fast.configure(state="disabled")
        self.btn_quality.configure(state="disabled")
        self.btn_get_summaries.configure(state="disabled")
        self.btn_edit_sources.configure(state="disabled")
        self.btn_upload_file.configure(state="disabled")
        self.label_status.configure(text=f"Running {script_name}...", text_color="orange")
        if self.label_audio_status:
            self.label_audio_status.configure(text=f"Running {script_name}...", text_color="orange")
        
        # Save summary before running (except for get_youtube_news)
        if script_name != "get_youtube_news.py" and not self.save_summary():
            self.enable_buttons()
            return
        
        def completion_handler(success):
            """Handle completion of script execution."""
            if success and script_name == "get_youtube_news.py":
                self.load_current_summary()
            self.enable_buttons()
            # Auto-upload to Drive if enabled and this was audio generation
            if success and script_name in ("make_audio_fast.py", "make_audio_quality.py"):
                self._upload_to_drive_after_generation(output_name)
        
        self.audio_generator.run_script(
            script_name, 
            output_name, 
            extra_args=extra_args,
            env_vars=env_vars,
            completion_callback=completion_handler
        )

    # Note: open_url_input_dialog and open_specific_urls_dialog removed
    # YouTube URL processing is now handled directly in the News Summary textbox
    # via smart content detection in show_direct_audio_dialog

    def enable_buttons(self):
        """Re-enable all control buttons and reset status."""
        self.btn_fast.configure(state="normal")
        self.btn_quality.configure(state="normal")
        self.btn_get_summaries.configure(state="normal")
        self.btn_edit_sources.configure(state="normal")
        self.btn_upload_file.configure(state="normal")
        self.label_status.configure(text="Ready", text_color="green")
        if self.label_audio_status:
            self.label_audio_status.configure(text="Ready", text_color="green")

    def start_fast_generation(self):
        """Generate fast audio with inline cleaning."""
        text = self.textbox.get("0.0", "end-1c").strip()
        if not text:
            self._update_status("No text to convert", "red")
            return

        api_key = self.gemini_key_entry.get().strip()

        # Check cache first
        raw_hash = hash(text)
        if (self._cleaned_text_cache is not None and
            self._cleaned_text_cache.get("raw_hash") == raw_hash):
            # Cache hit - use cached cleaned text
            cleaned_text = self._cleaned_text_cache["cleaned_text"]
            self._start_audio_generation_fast(cleaned_text)
            return

        # Need to clean - do it inline
        if api_key:
            self._clean_and_generate_inline(text, api_key, "fast")
        else:
            # No API key - use raw text directly
            self._start_audio_generation_fast(text)

    def start_quality_generation(self):
        """Generate quality audio with inline cleaning."""
        text = self.textbox.get("0.0", "end-1c").strip()
        if not text:
            self._update_status("No text to convert", "red")
            return

        api_key = self.gemini_key_entry.get().strip()

        # Check cache first
        raw_hash = hash(text)
        if (self._cleaned_text_cache is not None and
            self._cleaned_text_cache.get("raw_hash") == raw_hash):
            # Cache hit - use cached cleaned text
            cleaned_text = self._cleaned_text_cache["cleaned_text"]
            self._start_audio_generation_quality(cleaned_text)
            return

        # Need to clean - do it inline
        if api_key:
            self._clean_and_generate_inline(text, api_key, "quality")
        else:
            # No API key - use raw text directly
            self._start_audio_generation_quality(text)

    def _clean_and_generate_inline(self, raw_text: str, api_key: str, gen_type: str):
        """Clean text inline (no popup) and then generate audio."""
        # Show inline status
        self.inline_status_label.configure(
            text="Cleaning text for audio...",
            text_color="orange"
        )
        self.btn_toggle_view.configure(state="disabled")

        # Disable generate buttons during processing
        self.btn_fast.configure(state="disabled")
        self.btn_quality.configure(state="disabled")

        def clean_async():
            # Check for URLs and fetch if needed
            detection = self._detect_content_type(raw_text)

            if detection['total_urls'] > 0:
                self.after(0, lambda: self.inline_status_label.configure(
                    text=f"Fetching {detection['total_urls']} URL(s)...",
                    text_color="orange"
                ))
                processed = self._process_mixed_content(raw_text, api_key)
                text_to_clean = processed if processed else raw_text
            else:
                text_to_clean = raw_text

            # Clean the text
            self.after(0, lambda: self.inline_status_label.configure(
                text="Cleaning text...",
                text_color="orange"
            ))
            cleaned = self.clean_text_for_listening(text_to_clean, api_key)

            # Update cache
            raw_hash = hash(raw_text)
            self._cleaned_text_cache = {
                "raw_hash": raw_hash,
                "cleaned_text": cleaned
            }

            # Store for toggle
            self._raw_text_backup = raw_text
            self._cleaned_text_backup = cleaned

            def update_ui_and_generate():
                # Update textbox with cleaned text
                self.textbox.delete("0.0", "end")
                self.textbox.insert("0.0", cleaned)
                self._placeholder.place_forget()
                self._placeholder_visible = False
                self._editor_showing_raw = False

                # Reset URL banner to inactive
                self._set_url_banner_inactive("Content processed")

                # Enable toggle
                self.btn_toggle_view.configure(
                    state="normal",
                    text="Show Raw",
                    fg_color="orange"
                )
                self.inline_status_label.configure(
                    text="Text cleaned - generating audio...",
                    text_color="green"
                )

                # Re-enable buttons
                self.btn_fast.configure(state="normal")
                self.btn_quality.configure(state="normal")

                # Start audio generation
                if gen_type == "fast":
                    self._start_audio_generation_fast(cleaned)
                else:
                    self._start_audio_generation_quality(cleaned)

            self.after(0, update_ui_and_generate)

        threading.Thread(target=clean_async, daemon=True).start()

    def _start_audio_generation_fast(self, cleaned_text: str):
        """Start fast audio generation with the given cleaned text."""
        # Save to textbox (in case it's not already there)
        current = self.textbox.get("0.0", "end-1c").strip()
        if current != cleaned_text:
            self.textbox.delete("0.0", "end")
            self.textbox.insert("0.0", cleaned_text)

        filename = self.generate_audio_filename(cleaned_text, "mp3")
        self.run_script("make_audio_fast.py", filename, extra_args=["--output", filename])

    def _start_audio_generation_quality(self, cleaned_text: str):
        """Start quality audio generation with the given cleaned text."""
        # Save to textbox (in case it's not already there)
        current = self.textbox.get("0.0", "end-1c").strip()
        if current != cleaned_text:
            self.textbox.delete("0.0", "end")
            self.textbox.insert("0.0", cleaned_text)

        filename = self.generate_audio_filename(cleaned_text, "wav")
        voice = self.voice_var.get()
        self.run_script("make_audio_quality.py", filename, extra_args=["--voice", voice, "--output", filename])

    # ========== DEPRECATED METHODS (popup-based flow replaced by inline editor) ==========
    # These methods are kept for backward compatibility but are no longer called.
    # The new flow uses _clean_and_generate_inline() and inline status/toggle instead.

    def _show_url_processing_for_non_direct(self, generation_type: str, text: str, detection: dict):
        """DEPRECATED: Show URL processing confirmation when Direct Audio is unchecked but URLs are present."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("URLs Detected")
        dialog.geometry("500x300")
        dialog.transient(self)
        dialog.lift()
        dialog.grab_set()

        dialog.grid_columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(
            dialog,
            text="URLs Found in Text",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(20, 10))

        # Build description
        parts = []
        if detection['youtube_urls']:
            parts.append(f"{len(detection['youtube_urls'])} YouTube video(s)")
        if detection['article_urls']:
            parts.append(f"{len(detection['article_urls'])} article URL(s)")

        desc_text = f"Found {' and '.join(parts)}.\n\nURLs will be read as text unless you fetch them.\nFetch article/video content for audio?"

        ctk.CTkLabel(
            dialog,
            text=desc_text,
            font=ctk.CTkFont(size=13),
            wraplength=450,
            justify="center"
        ).grid(row=1, column=0, padx=20, pady=20)

        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        def generate_as_is():
            """Generate audio with URLs as literal text."""
            dialog.destroy()
            if generation_type == "fast":
                filename = self.generate_audio_filename(text, "mp3")
                self.run_script("make_audio_fast.py", filename, extra_args=["--output", filename])
            else:
                filename = self.generate_audio_filename(text, "wav")
                voice = self.voice_var.get()
                self.run_script("make_audio_quality.py", filename, extra_args=["--voice", voice, "--output", filename])

        def fetch_and_generate():
            """Fetch URLs and generate audio (uses Direct Audio flow)."""
            dialog.destroy()
            # Use Direct Audio flow which handles URL fetching
            self.show_direct_audio_dialog(generation_type)

        def cancel():
            dialog.destroy()

        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", command=cancel).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="Generate As-Is", fg_color="orange", command=generate_as_is).grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="Fetch & Generate", fg_color="green", command=fetch_and_generate).grid(row=0, column=2, padx=5, sticky="ew")

    def show_direct_audio_dialog(self, generation_type):
        """Show dialog to preview and edit cleaned text before audio generation.

        Smart detection flow:
        1. Check cache FIRST - if valid cache exists, skip URL confirmation
        2. Pure URLs (no surrounding text) → Process directly
        3. Embedded URLs (URLs within text) → Show confirmation dialog first
        4. Plain text → Process directly
        """
        raw_text = self.textbox.get("0.0", "end-1c").strip()
        if not raw_text:
            self.label_status.configure(text="No text to convert", text_color="red")
            return

        # FIRST: Check if we have valid cache for this text
        # If cache exists, skip the URL confirmation dialog entirely
        raw_hash = hash(raw_text)
        has_cache = (self._cleaned_text_cache is not None and
                     self._cleaned_text_cache.get("raw_hash") == raw_hash)

        if has_cache:
            # Cache hit - go directly to preview dialog (skip URL confirmation)
            detection = self._detect_content_type(raw_text)
            self._process_and_show_preview(raw_text, detection, generation_type)
            return

        # No cache - detect content type and handle accordingly
        detection = self._detect_content_type(raw_text)

        # If embedded URLs detected, show confirmation dialog
        if detection['has_embedded_urls'] and detection['total_urls'] > 0:
            self._show_embedded_url_confirmation(raw_text, detection, generation_type)
            return

        # If pure URLs or plain text, process directly
        self._process_and_show_preview(raw_text, detection, generation_type)

    def _show_embedded_url_confirmation(self, raw_text: str, detection: dict, generation_type: str):
        """Show confirmation dialog when URLs are detected embedded in text."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("URLs Detected in Text")
        dialog.geometry("500x350")
        dialog.transient(self)
        dialog.lift()
        dialog.grab_set()

        dialog.grid_columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(
            dialog,
            text="URLs Detected",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(20, 10))

        # Build description
        parts = []
        if detection['youtube_urls']:
            parts.append(f"{len(detection['youtube_urls'])} YouTube video(s)")
        if detection['article_urls']:
            parts.append(f"{len(detection['article_urls'])} article URL(s)")

        desc_text = f"Found {' and '.join(parts)} embedded in your text.\n\nWould you like to fetch and process these as well?"

        ctk.CTkLabel(
            dialog,
            text=desc_text,
            font=ctk.CTkFont(size=13),
            wraplength=450,
            justify="center"
        ).grid(row=1, column=0, padx=20, pady=10)

        # Show detected URLs in a small preview
        url_preview = ctk.CTkTextbox(dialog, height=120, font=ctk.CTkFont(size=11))
        url_preview.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        preview_text = ""
        if detection['youtube_urls']:
            preview_text += "YouTube:\n" + "\n".join(f"  • {url[:60]}..." if len(url) > 60 else f"  • {url}" for url in detection['youtube_urls'][:5])
            if len(detection['youtube_urls']) > 5:
                preview_text += f"\n  ... and {len(detection['youtube_urls']) - 5} more"
        if detection['article_urls']:
            if preview_text:
                preview_text += "\n\n"
            preview_text += "Articles:\n" + "\n".join(f"  • {url[:60]}..." if len(url) > 60 else f"  • {url}" for url in detection['article_urls'][:5])
            if len(detection['article_urls']) > 5:
                preview_text += f"\n  ... and {len(detection['article_urls']) - 5} more"

        url_preview.insert("0.0", preview_text)
        url_preview.configure(state="disabled")

        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        def process_all():
            dialog.destroy()
            # Process with URL fetching enabled
            self._process_and_show_preview(raw_text, detection, generation_type, fetch_urls=True)

        def text_only():
            dialog.destroy()
            # Process text only, ignore URLs - but keep original raw_text for cache lookup
            text_only_detection = {
                'youtube_urls': [],
                'article_urls': [],
                'plain_text': detection['plain_text'],
                'is_pure_urls': False,
                'has_embedded_urls': False,
                'total_urls': 0
            }
            # Pass original raw_text to preserve cache, but don't fetch URLs
            self._process_and_show_preview(raw_text, text_only_detection, generation_type, fetch_urls=False)

        def cancel():
            dialog.destroy()
            self.label_status.configure(text="Ready", text_color="gray")

        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", command=cancel).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="Text Only", fg_color="orange", command=text_only).grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="Process All", fg_color="green", command=process_all).grid(row=0, column=2, padx=5, sticky="ew")

    def _process_and_show_preview(self, raw_text: str, detection: dict, generation_type: str, fetch_urls: bool = True):
        """Process content and show the preview dialog."""
        # Clear status when opening dialog
        self.label_status.configure(text="Ready", text_color="gray")

        # Check if we have cached cleaned text for this raw text
        raw_hash = hash(raw_text)
        has_cache = (self._cleaned_text_cache is not None and
                     self._cleaned_text_cache.get("raw_hash") == raw_hash)

        # Create dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Direct Audio - Preview & Edit")
        dialog.geometry("800x600")
        dialog.transient(self)
        dialog.minsize(600, 400)
        dialog.lift()
        dialog.grab_set()

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header_frame, text="Preview Text for Audio", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w")

        # Status label
        if has_cache:
            status_label = ctk.CTkLabel(header_frame, text="Loaded from cache (edit or re-clean)", text_color="green")
        else:
            status_label = ctk.CTkLabel(header_frame, text="Cleaning text for listening...", text_color="orange")
        status_label.grid(row=0, column=1, padx=20, sticky="e")

        # Text editor
        text_editor = ctk.CTkTextbox(dialog, font=ctk.CTkFont(size=13))
        text_editor.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        # If cached, show cached text immediately; otherwise show loading message
        if has_cache:
            text_editor.insert("0.0", self._cleaned_text_cache["cleaned_text"])
        else:
            text_editor.insert("0.0", "Cleaning text for audio... please wait...")
            text_editor.configure(state="disabled")

        # Button frame - 4 buttons now
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def on_convert():
            """Convert the edited text to audio."""
            cleaned_text = text_editor.get("0.0", "end-1c").strip()
            if not cleaned_text:
                status_label.configure(text="No text to convert", text_color="red")
                return

            # Save the cleaned text to the main textbox for audio generation
            self.textbox.delete("0.0", "end")
            self.textbox.insert("0.0", cleaned_text)

            # Update cache with any edits the user made
            self._cleaned_text_cache = {
                "raw_hash": raw_hash,
                "cleaned_text": cleaned_text
            }

            dialog.destroy()

            # Generate smart filename based on content
            if generation_type == "fast":
                filename = self.generate_audio_filename(cleaned_text, "mp3")
                self.run_script("make_audio_fast.py", filename, extra_args=["--output", filename])
            else:
                filename = self.generate_audio_filename(cleaned_text, "wav")
                voice = self.voice_var.get()
                self.run_script("make_audio_quality.py", filename, extra_args=["--voice", voice, "--output", filename])

        def on_cancel():
            # Save current text to cache before closing (in case user edited it)
            current_text = text_editor.get("0.0", "end-1c").strip()
            if current_text and current_text != "Cleaning text for audio... please wait...":
                self._cleaned_text_cache = {
                    "raw_hash": raw_hash,
                    "cleaned_text": current_text
                }
            self.label_status.configure(text="Ready", text_color="gray")
            dialog.destroy()

        # Track whether we're showing raw or cleaned text (for toggle)
        showing_raw = [False]  # Use list for mutability in nested function
        # Initialize with cached cleaned text if available (so toggle works immediately)
        saved_cleaned_text = [self._cleaned_text_cache["cleaned_text"] if has_cache else None]

        def toggle_raw_cleaned():
            """Toggle between raw text and cleaned text."""
            text_editor.configure(state="normal")
            current_text = text_editor.get("0.0", "end-1c").strip()

            if showing_raw[0]:
                # Currently showing raw, switch to cleaned
                if saved_cleaned_text[0]:
                    text_editor.delete("0.0", "end")
                    text_editor.insert("0.0", saved_cleaned_text[0])
                    status_label.configure(text="Showing cleaned text", text_color="green")
                    btn_toggle_raw.configure(text="Use Raw Text", fg_color="orange")
                    showing_raw[0] = False
                else:
                    status_label.configure(text="No cleaned text available yet", text_color="red")
            else:
                # Currently showing cleaned, switch to raw
                # Save current cleaned text before switching
                if current_text and current_text != "Cleaning text for audio... please wait...":
                    saved_cleaned_text[0] = current_text
                text_editor.delete("0.0", "end")
                text_editor.insert("0.0", raw_text)
                status_label.configure(text="Showing raw text (toggle to return to cleaned)", text_color="orange")
                btn_toggle_raw.configure(text="Use Cleaned", fg_color="green")
                showing_raw[0] = True

            btn_convert.configure(state="normal")
            btn_reclean.configure(state="normal")

        def reclean_text():
            """Re-run AI cleaning on the current textbox content."""
            # Get text from main textbox (in case user updated it)
            current_raw = self.textbox.get("0.0", "end-1c").strip()
            if not current_raw:
                status_label.configure(text="No text to clean", text_color="red")
                return

            # Disable buttons and show loading
            text_editor.configure(state="normal")
            text_editor.delete("0.0", "end")
            text_editor.insert("0.0", "Re-cleaning text for audio... please wait...")
            text_editor.configure(state="disabled")
            status_label.configure(text="Re-cleaning text...", text_color="orange")
            btn_convert.configure(state="disabled")
            btn_reclean.configure(state="disabled")

            def reclean_async():
                api_key = self.gemini_key_entry.get().strip()
                if not api_key:
                    def show_raw_no_key():
                        text_editor.configure(state="normal")
                        text_editor.delete("0.0", "end")
                        text_editor.insert("0.0", raw_text)
                        status_label.configure(text="No API key - using raw text", text_color="orange")
                        btn_toggle_raw.configure(text="Use Cleaned", fg_color="green")
                        showing_raw[0] = True
                        btn_convert.configure(state="normal")
                        btn_reclean.configure(state="normal")
                    dialog.after(0, show_raw_no_key)
                    return

                cleaned = self.clean_text_for_listening(current_raw, api_key)

                # Update cache with new hash for current raw text
                new_hash = hash(current_raw)
                self._cleaned_text_cache = {
                    "raw_hash": new_hash,
                    "cleaned_text": cleaned
                }

                def update_ui():
                    text_editor.configure(state="normal")
                    text_editor.delete("0.0", "end")
                    text_editor.insert("0.0", cleaned)
                    # Also update the saved_cleaned_text for toggle
                    saved_cleaned_text[0] = cleaned
                    showing_raw[0] = False
                    btn_toggle_raw.configure(text="Use Raw Text", fg_color="orange")
                    status_label.configure(text="Text re-cleaned and ready for review", text_color="green")
                    btn_convert.configure(state="normal")
                    btn_reclean.configure(state="normal")

                dialog.after(0, update_ui)

            threading.Thread(target=reclean_async, daemon=True).start()

        btn_cancel = ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", command=on_cancel)
        btn_cancel.grid(row=0, column=0, padx=5, sticky="ew")

        btn_toggle_raw = ctk.CTkButton(btn_frame, text="Use Raw Text", fg_color="orange", command=toggle_raw_cleaned)
        btn_toggle_raw.grid(row=0, column=1, padx=5, sticky="ew")

        btn_reclean = ctk.CTkButton(btn_frame, text="Re-clean", fg_color="#5a5a5a", command=reclean_text)
        btn_reclean.grid(row=0, column=2, padx=5, sticky="ew")
        if has_cache:
            btn_reclean.configure(state="normal")
        else:
            btn_reclean.configure(state="disabled")

        btn_convert = ctk.CTkButton(btn_frame, text="Convert to Audio", fg_color="green", command=on_convert)
        btn_convert.grid(row=0, column=3, padx=5, sticky="ew")
        if has_cache:
            btn_convert.configure(state="normal")
        else:
            btn_convert.configure(state="disabled")

        # If no cache, start processing in background
        if not has_cache:
            def process_async():
                api_key = self.gemini_key_entry.get().strip()
                if not api_key:
                    def show_raw_no_key():
                        text_editor.configure(state="normal")
                        text_editor.delete("0.0", "end")
                        text_editor.insert("0.0", raw_text)
                        status_label.configure(text="No API key - using raw text", text_color="orange")
                        btn_toggle_raw.configure(text="Use Cleaned", fg_color="green")
                        showing_raw[0] = True
                        btn_convert.configure(state="normal")
                        btn_reclean.configure(state="normal")
                    dialog.after(0, show_raw_no_key)
                    return

                # Check if we need to fetch URLs
                needs_url_fetch = fetch_urls and detection['total_urls'] > 0

                if needs_url_fetch:
                    # Update status to show we're fetching
                    def update_fetching():
                        text_editor.configure(state="normal")
                        text_editor.delete("0.0", "end")
                        text_editor.insert("0.0", "Fetching and processing content... please wait...")
                        text_editor.configure(state="disabled")
                        status_label.configure(text=f"Processing {detection['total_urls']} URL(s)...", text_color="orange")
                    dialog.after(0, update_fetching)

                    # Process all content (YouTube, articles, text)
                    def progress_cb(msg, color):
                        dialog.after(0, lambda m=msg, c=color: status_label.configure(text=m, text_color=c))

                    processed_content = self._process_mixed_content(raw_text, api_key, progress_callback=progress_cb)

                    if processed_content:
                        # Update textbox with fetched content
                        def update_textbox():
                            self.textbox.delete("0.0", "end")
                            self.textbox.insert("0.0", processed_content)
                            self._placeholder.place_forget()
                        dialog.after(0, update_textbox)

                        # Now clean the processed content for audio
                        dialog.after(0, lambda: status_label.configure(text="Cleaning text for audio...", text_color="orange"))
                        cleaned = self.clean_text_for_listening(processed_content, api_key)
                    else:
                        # Fall back to raw text if fetching failed
                        cleaned = self.clean_text_for_listening(raw_text, api_key)
                else:
                    # No URLs to fetch, just clean the text
                    cleaned = self.clean_text_for_listening(raw_text, api_key)

                # Cache the cleaned text
                self._cleaned_text_cache = {
                    "raw_hash": raw_hash,
                    "cleaned_text": cleaned
                }

                def update_ui():
                    text_editor.configure(state="normal")
                    text_editor.delete("0.0", "end")
                    text_editor.insert("0.0", cleaned)
                    # Also update the saved_cleaned_text for toggle
                    saved_cleaned_text[0] = cleaned
                    showing_raw[0] = False
                    btn_toggle_raw.configure(text="Use Raw Text", fg_color="orange")
                    status_label.configure(text="Text cleaned and ready for review", text_color="green")
                    btn_convert.configure(state="normal")
                    btn_reclean.configure(state="normal")

                dialog.after(0, update_ui)

            threading.Thread(target=process_async, daemon=True).start()

    def clean_text_for_listening(self, text, api_key):
        """Use Gemini to clean and format text for audio listening."""
        import google.generativeai as genai

        try:
            genai.configure(api_key=api_key)

            # Extract model name from dropdown (format: "gemini-2.0-flash (Fast)")
            model_name = self.model_var.get().split(" (")[0]

            model = genai.GenerativeModel(model_name)

            # If text contains multiple articles (separated by ---), clean each separately
            # to avoid hitting Gemini output token limits
            separator = "\n\n---\n\n"
            if separator in text:
                articles = text.split(separator)
                print(f"[Clean] Found {len(articles)} articles, cleaning each separately...")
                cleaned_articles = []
                for i, article in enumerate(articles):
                    if len(article.strip()) < 100:
                        continue
                    print(f"[Clean] Cleaning article {i+1}/{len(articles)} ({len(article)} chars)...")
                    cleaned = self._clean_single_article(model, article)
                    if cleaned:
                        cleaned_articles.append(cleaned)
                        print(f"[Clean] Article {i+1} cleaned: {len(cleaned)} chars")

                # Join with clear separator for audio
                result = "\n\n".join(cleaned_articles)
                print(f"[Clean] Total cleaned text: {len(result)} chars from {len(cleaned_articles)} articles")
                return result
            else:
                # Single article - clean directly
                return self._clean_single_article(model, text)

        except Exception as e:
            print(f"Error cleaning text: {e}")
            return text  # Return original text on error

    def _clean_single_article(self, model, text):
        """Clean a single article using Gemini with optional custom instructions."""
        # Get custom article instructions from active profile
        custom_instructions = self._get_active_article_instructions()

        # Base prompt for article cleaning
        base_prompt = """Clean and format this text for audio listening. Your task:

1. EXTRACT only the main article/content body
2. REMOVE all of the following:
   - URLs, links, and email addresses
   - Asterisks (*), bullet point markers, markdown formatting
   - "Subscribe", "Click here", "Read more", "Share", "Follow us" and similar CTAs
   - Author bios, bylines, and "About the author" sections
   - "Related articles", "You might also like" sections
   - Advertisements and promotional content
   - Social media handles and hashtags
   - Navigation elements, headers/footers
   - Image captions and alt text descriptions
   - Any text that wouldn't make sense when read aloud

3. PRESERVE the original wording and structure of the actual content
4. FORMAT for natural speech:
   - Expand common abbreviations (e.g., "approx." → "approximately")
   - Keep paragraph breaks for natural pauses
   - Ensure sentences flow naturally when spoken"""

        # Add custom instructions if present
        if custom_instructions:
            prompt = f"""{base_prompt}

5. ADDITIONAL USER PREFERENCES:
{custom_instructions}

Return ONLY the cleaned text, nothing else.

TEXT TO CLEAN:
\"\"\"
{text}
\"\"\"
"""
        else:
            prompt = f"""{base_prompt}

Return ONLY the cleaned text, nothing else.

TEXT TO CLEAN:
\"\"\"
{text}
\"\"\"
"""

        try:
            from api_usage_tracker import get_tracker, APILimitExceeded, BudgetExceeded
            response = get_tracker().tracked_generate(model, prompt, "gui._process_audio")
            return response.text.strip()
        except (APILimitExceeded, BudgetExceeded) as e:
            print(f"[Clean] {e}")
            return text  # Return original when limit hit
        except Exception as e:
            print(f"[Clean] Error cleaning article: {e}")
            return text  # Return original on error

    def generate_audio_filename(self, text, extension="wav"):
        """Generate a smart filename based on date and content topics.

        Args:
            text: The text content to analyze for topics
            extension: File extension (wav or mp3)

        Returns:
            Filename like '2025-12-28_bitcoin-etf-approval.wav'
        """
        import re

        date_str = datetime.datetime.now().strftime("%Y-%m-%d")

        if not text or len(text.strip()) < 10:
            return f"{date_str}_audio.{extension}"

        # Try to extract a title from the first line/sentence
        lines = text.strip().split('\n')
        first_line = lines[0].strip() if lines else ""

        # Check if first line looks like a title (short, no period at end)
        if first_line and len(first_line) < 100 and not first_line.endswith('.'):
            topic_source = first_line
        else:
            # Use first sentence or chunk
            sentences = re.split(r'[.!?]', text[:500])
            topic_source = sentences[0] if sentences else text[:100]

        # Extract key words (remove common words)
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'this', 'that', 'these',
            'those', 'it', 'its', 'they', 'their', 'we', 'our', 'you', 'your',
            'he', 'she', 'him', 'her', 'his', 'i', 'my', 'me', 'what', 'which',
            'who', 'how', 'when', 'where', 'why', 'all', 'each', 'every', 'both',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not', 'only',
            'own', 'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now',
            'new', 'says', 'said', 'according', 'report', 'reports', 'today'
        }

        # Clean and tokenize
        words = re.findall(r'\b[a-zA-Z]{3,}\b', topic_source.lower())
        key_words = [w for w in words if w not in stop_words][:5]

        if not key_words:
            # Fallback: just use first few words
            key_words = words[:3] if words else ['audio']

        # Create topic slug
        topic_slug = '-'.join(key_words[:4])  # Max 4 words

        # Sanitize for filename
        topic_slug = re.sub(r'[^a-z0-9\-]', '', topic_slug)
        topic_slug = re.sub(r'-+', '-', topic_slug).strip('-')

        # Limit length
        if len(topic_slug) > 40:
            topic_slug = topic_slug[:40].rsplit('-', 1)[0]

        if not topic_slug:
            topic_slug = "audio"

        filename = f"{date_str}_{topic_slug}.{extension}"
        print(f"[Audio] Generated filename: {filename}")
        return filename

    def estimate_api_usage(self):
        """Estimate API requests and cost based on current settings."""
        # Count enabled channels - check user data dir first, then bundled
        import json
        data_dir = get_data_directory()
        sources_json_user = os.path.join(data_dir, "sources.json")
        sources_json_bundled = get_resource_path("sources.json")
        enabled_channels = 0

        # Try user's customized sources first
        if os.path.exists(sources_json_user):
            try:
                data = json.load(open(sources_json_user))
                enabled_channels = sum(1 for s in data.get("sources", []) if s.get("enabled", True))
            except:
                enabled_channels = 0

        # Fall back to bundled sources
        if enabled_channels == 0 and os.path.exists(sources_json_bundled):
            try:
                data = json.load(open(sources_json_bundled))
                enabled_channels = sum(1 for s in data.get("sources", []) if s.get("enabled", True))
            except:
                enabled_channels = 1

        # Fall back to channels.txt
        if enabled_channels == 0:
            channels_file_user = os.path.join(data_dir, "channels.txt")
            channels_file_bundled = get_resource_path("channels.txt")
            if os.path.exists(channels_file_user):
                with open(channels_file_user, "r") as f:
                    enabled_channels = sum(1 for line in f if line.strip())
            elif os.path.exists(channels_file_bundled):
                with open(channels_file_bundled, "r") as f:
                    enabled_channels = sum(1 for line in f if line.strip())
        
        # Calculate days based on mode
        days = 1
        mode = self.mode_var.get()
        
        if self.range_var.get():
            start = self.start_date_entry.get().strip()
            end = self.end_date_entry.get().strip()
            if start and end:
                try:
                    start_dt = datetime.datetime.strptime(start, "%Y-%m-%d")
                    end_dt = datetime.datetime.strptime(end, "%Y-%m-%d")
                    days = abs((end_dt - start_dt).days) + 1
                except:
                    days = 1
        else:
            value = self.entry_value.get().strip()
            if mode == "Hours":
                # Convert hours to fractional days for estimation
                hours = int(value) if value.isdigit() else 24
                days = hours / 24.0
            else:
                days = int(value) if value.isdigit() else 1
        
        # Estimate: ~3-5 videos per channel per day (use 4 as average)
        avg_videos_per_channel_per_day = 4
        estimated_requests = int(enabled_channels * days * avg_videos_per_channel_per_day)
        
        # Get model limits and costs
        model_choice = self.model_var.get()
        if "gemini-1.5-pro" in model_choice:  # Pro model
            free_limit = 50
            cost_per_1k = 1.25  # $1.25 per 1000 requests for Pro
        else:  # Flash models
            free_limit = 1500
            cost_per_1k = 0.075  # $0.075 per 1000 requests for Flash
        
        estimated_cost = 0
        if estimated_requests > free_limit:
            paid_requests = estimated_requests - free_limit
            estimated_cost = (paid_requests / 1000) * cost_per_1k
        
        return {
            "channels": enabled_channels,
            "days": days,
            "estimated_requests": estimated_requests,
            "free_limit": free_limit,
            "estimated_cost": estimated_cost,
            "model": model_name
        }
    
    def get_summaries_from_sources(self):
        """Get summaries from all configured sources (YouTube, RSS, Article Archives).

        This is the new unified method that replaces get_youtube_news_from_channels.
        It uses source_fetcher.py to handle multiple source types.
        """
        api_key = self.gemini_key_entry.get().strip()
        if not api_key:
            self.label_status.configure(text="Error: Gemini API Key is required.", text_color="red")
            return

        mode = self.mode_var.get()
        value = self.entry_value.get().strip()

        # Handle Hours/Days/Videos modes
        if not value.isdigit():
            value = "7"

        self.save_api_key(api_key)

        # Calculate cutoff date (start) and end_date
        from datetime import datetime, timedelta
        end_date = None  # None means "up to now"
        if self.range_var.get():
            start = self.start_date_entry.get().strip()
            end = self.end_date_entry.get().strip()
            if start:
                try:
                    cutoff_date = datetime.strptime(start, "%Y-%m-%d")
                except ValueError:
                    cutoff_date = datetime.now() - timedelta(days=7)
            else:
                cutoff_date = datetime.now() - timedelta(days=7)
            # Parse end date if provided
            if end:
                try:
                    end_date = datetime.strptime(end, "%Y-%m-%d")
                except ValueError:
                    end_date = None  # Invalid end date, don't filter
        else:
            if mode == "Hours":
                hours = int(value) if value.isdigit() else 24
                cutoff_date = datetime.now() - timedelta(hours=hours)
            else:
                days = int(value) if value.isdigit() else 7
                cutoff_date = datetime.now() - timedelta(days=days)

        # Import source fetcher
        try:
            from source_fetcher import (
                load_sources, SourceFetcher, SourceType,
                format_items_for_audio, FetchedItem
            )
        except ImportError as e:
            self.label_status.configure(text=f"Error importing source_fetcher: {e}", text_color="red")
            return

        # Load sources
        data_dir = get_data_directory()
        sources_json = os.path.join(data_dir, "sources.json")
        channels_txt = os.path.join(data_dir, "channels.txt")

        # Fall back to bundled files if user files don't exist
        if not os.path.exists(sources_json):
            sources_json = get_resource_path("sources.json")
        if not os.path.exists(channels_txt):
            channels_txt = get_resource_path("channels.txt")

        sources = load_sources(sources_json, channels_txt)

        if not sources:
            self.label_status.configure(text="No sources configured. Click 'Edit Sources' to add some.", text_color="orange")
            return

        enabled_sources = [s for s in sources if s.enabled]
        if not enabled_sources:
            self.label_status.configure(text="All sources are disabled. Enable at least one.", text_color="orange")
            return

        # Check for article archives that need selection
        archive_sources = [s for s in enabled_sources if s.source_type == SourceType.ARTICLE_ARCHIVE]
        other_sources = [s for s in enabled_sources if s.source_type != SourceType.ARTICLE_ARCHIVE]

        # Load custom instructions
        youtube_instructions = self._load_custom_instructions("youtube")
        article_instructions = self._load_custom_instructions("article")

        # If there are article archives, process them first with selection dialogs
        if archive_sources:
            self._process_sources_with_archives(
                archive_sources, other_sources, cutoff_date, api_key,
                youtube_instructions, article_instructions, end_date
            )
        else:
            # No archives, just fetch everything directly
            self._fetch_and_display_sources(
                other_sources, [], cutoff_date, api_key,
                youtube_instructions, article_instructions, end_date
            )

    def _load_custom_instructions(self, instruction_type: str) -> str:
        """Load custom instructions for a given type (youtube or article)."""
        try:
            data_dir = get_data_directory()
            if instruction_type == "youtube":
                path = os.path.join(data_dir, "custom_instructions.txt")
            else:
                path = os.path.join(data_dir, "article_instructions.txt")

            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    # Filter out comment lines
                    lines = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
                    return '\n'.join(lines)
        except Exception as e:
            print(f"Error loading {instruction_type} instructions: {e}")
        return ""

    def _process_sources_with_archives(self, archive_sources, other_sources, cutoff_date,
                                       api_key, youtube_instructions, article_instructions,
                                       end_date=None):
        """Process sources, showing selection dialogs for article archives."""
        from source_fetcher import SourceFetcher, FetchedItem

        fetcher = SourceFetcher(api_key)
        selected_articles = []  # Accumulate selected articles from all archives
        remaining_archives = list(archive_sources)

        def process_next_archive():
            if not remaining_archives:
                # All archives processed, now fetch everything
                self._fetch_and_display_sources(
                    other_sources, selected_articles, cutoff_date, api_key,
                    youtube_instructions, article_instructions, end_date
                )
                return

            source = remaining_archives.pop(0)
            self.label_status.configure(
                text=f"Extracting links from {source.name or source.url[:40]}...",
                text_color="orange"
            )

            def extract_and_show():
                try:
                    links = fetcher.extract_archive_links(source.url, source.selector)

                    if not links:
                        self.after(0, lambda: self.label_status.configure(
                            text=f"No articles found at {source.url[:40]}",
                            text_color="orange"
                        ))
                        self.after(0, process_next_archive)
                        return

                    def on_selection(selected_links):
                        # Add selected links to our list
                        for link in selected_links:
                            selected_articles.append({
                                'url': link.url,
                                'title': link.title,
                                'source_name': source.name or source.url[:30],
                                'date': link.date
                            })
                        # Process next archive
                        process_next_archive()

                    # Show selection dialog on main thread
                    self.after(0, lambda: self._show_article_selector(
                        source.name or source.url[:30],
                        links,
                        cutoff_date,
                        on_selection
                    ))

                except Exception as e:
                    print(f"Error extracting links from {source.url}: {e}")
                    self.after(0, lambda: self.label_status.configure(
                        text=f"Error extracting links: {str(e)[:40]}",
                        text_color="red"
                    ))
                    self.after(0, process_next_archive)

            threading.Thread(target=extract_and_show, daemon=True).start()

        process_next_archive()

    def _fetch_and_display_sources(self, sources, selected_articles, cutoff_date,
                                   api_key, youtube_instructions, article_instructions,
                                   end_date=None):
        """Fetch content from sources and display in text area, and save to file."""
        from source_fetcher import SourceFetcher, SourceType, FetchedItem, format_items_for_audio
        from datetime import datetime
        import traceback

        self.label_status.configure(text="Fetching content from sources...", text_color="orange")
        self.btn_get_summaries.configure(state="disabled")

        print(f"[Get Summaries] Starting fetch: {len(sources)} sources, {len(selected_articles)} selected articles")

        def fetch_thread():
            try:
                fetcher = SourceFetcher(api_key)
                all_items = []

                # Fetch from YouTube and RSS sources
                if sources:
                    print(f"[Get Summaries] Fetching from {len(sources)} YouTube/RSS sources...")
                    def progress_cb(msg, color):
                        self.after(0, lambda: self.label_status.configure(text=msg, text_color=color))

                    items = fetcher.fetch_all_sources(
                        sources=sources,
                        cutoff_date=cutoff_date,
                        max_items_per_source=10,
                        progress_callback=progress_cb,
                        youtube_instructions=youtube_instructions,
                        article_instructions=article_instructions,
                        end_date=end_date
                    )
                    all_items.extend(items)
                    print(f"[Get Summaries] Got {len(items)} items from YouTube/RSS sources")

                # Fetch selected articles from archives
                print(f"[Get Summaries] Fetching {len(selected_articles)} selected articles...")
                for i, article in enumerate(selected_articles):
                    try:
                        self.after(0, lambda a=article, idx=i: self.label_status.configure(
                            text=f"Fetching article {idx+1}/{len(selected_articles)}: {a['title'][:35]}...",
                            text_color="orange"
                        ))

                        print(f"[Get Summaries] Fetching article: {article['url']}")
                        title, content = fetcher.fetch_article_content(article['url'])
                        print(f"[Get Summaries] Got title='{title[:50] if title else 'None'}', content length={len(content) if content else 0}")

                        if content:
                            # Summarize the article content (like YouTube does)
                            self.after(0, lambda a=article: self.label_status.configure(
                                text=f"Summarizing: {a['title'][:40]}...",
                                text_color="orange"
                            ))
                            summary = fetcher.summarize_article_content(
                                title or article['title'],
                                content,
                                article_instructions
                            )
                            print(f"[Get Summaries] Article summarized: {len(content)} -> {len(summary) if summary else 0} chars")

                            all_items.append(FetchedItem(
                                title=title or article['title'],
                                url=article['url'],
                                content=content,
                                source_name=article['source_name'],
                                source_type=SourceType.ARTICLE_ARCHIVE,
                                published_date=article.get('date'),
                                summary=summary
                            ))
                    except Exception as e:
                        print(f"[Get Summaries] Error fetching article {article['url']}: {e}")
                        traceback.print_exc()

                # Format output
                print(f"[Get Summaries] Total items collected: {len(all_items)}")
                if all_items:
                    output = format_items_for_audio(all_items)
                    print(f"[Get Summaries] Formatted output length: {len(output)}")

                    # Save to file (like old get_youtube_news.py did)
                    saved_file = None
                    try:
                        data_dir = get_data_directory()
                        today = datetime.now().strftime("%Y-%m-%d")

                        # Create week folder
                        week_num = datetime.now().isocalendar()[1]
                        year = datetime.now().year
                        week_folder = os.path.join(data_dir, f"Week_{week_num}_{year}")
                        os.makedirs(week_folder, exist_ok=True)

                        # Save summary file
                        filename = f"summary_{today}.txt"
                        filepath = os.path.join(week_folder, filename)

                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(output)

                        saved_file = filepath
                        print(f"[Get Summaries] Saved to: {filepath}")
                    except Exception as save_err:
                        print(f"[Get Summaries] Error saving file: {save_err}")

                    # Count items by type for status message
                    yt_count = sum(1 for i in all_items if i.source_type == SourceType.YOUTUBE)
                    arc_count = sum(1 for i in all_items if i.source_type == SourceType.ARTICLE_ARCHIVE)
                    rss_count = sum(1 for i in all_items if i.source_type == SourceType.RSS)

                    def update_ui():
                        self.textbox.delete("0.0", "end")
                        self.textbox.insert("0.0", output)
                        self._placeholder.place_forget()
                        self._reset_editor_state()

                        # Build detailed status message
                        parts = []
                        if yt_count > 0:
                            parts.append(f"{yt_count} videos")
                        if arc_count > 0:
                            parts.append(f"{arc_count} articles")
                        if rss_count > 0:
                            parts.append(f"{rss_count} RSS items")

                        detail = ", ".join(parts) if parts else "0 items"

                        if saved_file:
                            filename = os.path.basename(saved_file)
                            self.label_status.configure(
                                text=f"Loaded {detail} → saved to {filename}",
                                text_color="green"
                            )
                        else:
                            self.label_status.configure(
                                text=f"Loaded {detail} from sources",
                                text_color="green"
                            )
                        self.btn_get_summaries.configure(state="normal")
                        print(f"[Get Summaries] UI updated with {len(all_items)} items ({yt_count} YouTube, {arc_count} articles, {rss_count} RSS)")

                    self.after(0, update_ui)
                else:
                    def show_empty():
                        self.label_status.configure(
                            text="No content found for the selected date range",
                            text_color="orange"
                        )
                        self.btn_get_summaries.configure(state="normal")
                        print("[Get Summaries] No items found")

                    self.after(0, show_empty)

            except Exception as e:
                print(f"[Get Summaries] Fatal error: {e}")
                traceback.print_exc()
                def show_error():
                    self.label_status.configure(
                        text=f"Error fetching sources: {str(e)[:50]}",
                        text_color="red"
                    )
                    self.btn_get_summaries.configure(state="normal")

                self.after(0, show_error)

        threading.Thread(target=fetch_thread, daemon=True).start()

    def get_youtube_news_from_channels(self):
        """Legacy method - redirects to get_summaries_from_sources for backward compatibility."""
        return self.get_summaries_from_sources()
    
    def show_usage_confirmation(self, usage, extra_args, output_desc, api_key, selected_model):
        """Show confirmation dialog with API usage estimate."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirm API Usage")
        dialog.geometry("550x400")
        dialog.transient(self)
        dialog.lift()
        dialog.grab_set()  # Make modal
        
        # Header
        header = ctk.CTkLabel(
            dialog, 
            text="📊 API Usage Estimate", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        header.pack(pady=(20, 10))
        
        # Info frame
        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        # Display estimates
        info_text = f"""
Configuration:
  • Enabled channels: {usage['channels']}
  • Days to process: {usage['days']}
  • Model: {usage['model']}

Estimated Usage:
  • API requests: ~{usage['estimated_requests']} calls
  • Free tier limit: {usage['free_limit']} requests/day
  
"""
        
        if usage['estimated_requests'] > usage['free_limit']:
            paid_requests = usage['estimated_requests'] - usage['free_limit']
            info_text += f"""⚠️ WARNING: Exceeds Free Tier
  • Requests beyond free tier: ~{paid_requests}
  • Estimated cost: ${usage['estimated_cost']:.2f}

This will incur charges to your Google Cloud account!
"""
            warning_color = "orange"
        else:
            remaining = usage['free_limit'] - usage['estimated_requests']
            info_text += f"""✓ Within Free Tier
  • Remaining free requests: ~{remaining}
  • Estimated cost: $0.00
"""
            warning_color = "green"
        
        info_label = ctk.CTkLabel(
            info_frame, 
            text=info_text,
            font=ctk.CTkFont(size=12),
            justify="left"
        )
        info_label.pack(padx=15, pady=15)
        
        # Note
        note_text = "Note: This is an estimate based on ~4 videos per channel per day.\nActual usage may vary."
        note_label = ctk.CTkLabel(
            dialog,
            text=note_text,
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        note_label.pack(pady=(0, 10))
        
        # Buttons
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=(0, 20))
        
        def proceed():
            dialog.destroy()
            # Run script with the provided arguments
            self.run_script("get_youtube_news.py", output_desc, extra_args=extra_args, 
                          env_vars={"GEMINI_API_KEY": api_key, "PYTHONUNBUFFERED": "1"})
        
        def cancel():
            dialog.destroy()
            self.label_status.configure(text="Operation cancelled", text_color="gray")
        
        # Different button text based on whether it will cost money
        if usage['estimated_requests'] > usage['free_limit']:
            proceed_text = f"Proceed (will cost ~${usage['estimated_cost']:.2f})"
            proceed_color = "orange"
        else:
            proceed_text = "Proceed (Free)"
            proceed_color = "green"
        
        proceed_btn = ctk.CTkButton(
            button_frame,
            text=proceed_text,
            command=proceed,
            fg_color=proceed_color,
            width=200
        )
        proceed_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=cancel,
            fg_color="gray",
            width=120
        )
        cancel_btn.pack(side="left", padx=10)


    def open_output_folder(self):
        """Open the output folder in file browser."""
        self.audio_generator.open_folder()

    def start_tutorial(self):
        """Start an interactive tutorial walkthrough of the app features with widget highlighting."""
        # Define tutorial steps with widget references for highlighting
        # Using specific small widgets instead of large frames for better focus
        tutorial_steps = [
            {
                "title": "Welcome to Daily Audio Briefing!",
                "content": """Don't worry - this app is simpler than it looks!

This tutorial will guide you through everything step-by-step. By the end, you'll know exactly how to turn articles and news into audio you can listen to anywhere.

**What This App Does:**

• Takes articles, blog posts, or YouTube videos
• Uses AI to summarize them (optional)
• Converts everything to audio files you can listen to

**Two Ways to Use It:**

1. **Get Summaries** - Batch process from your configured sources
2. **Paste & Generate** - Paste any text, URLs, or articles and convert to audio

Let's start with the basics. Click 'Next' to continue.""",
                "highlight": None  # No highlight for welcome
            },
            {
                "title": "Step 1: Your API Key (Required First Step)",
                "content": """**Look at the highlighted field** - this is where your API key goes.

**What is an API key?**
It's like a password that lets this app talk to Google's AI. Without it, the app can't summarize or process anything.

**How to get one (it's free!):**

1. Go to: aistudio.google.com/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key (it looks like a long string of letters and numbers)
5. Paste it in the highlighted field
6. Click the 💾 button to save it

**The buttons next to the field:**
• **💾** = Save your key (turns green ✓ when saved)
• **👁** = Show/hide your key (for privacy)
• **⚙** = Open key manager (to copy or delete your key)

Once saved, you won't need to enter it again!""",
                "highlight": "gemini_key_entry"
            },
            {
                "title": "Step 2: Choose Your AI Model",
                "content": """**The Model Dropdown** (next to your API key)

This controls which AI model processes your content. Think of it like choosing between different assistants.

**Available Models:**

• **Flash** - Fastest, good for most tasks
• **Pro** - More thorough, takes longer
• **Flash 8B** - Lightweight, very fast
• **Flash Thinking** - Best for complex analysis

**Which should you pick?**

For everyday use, **Flash** is recommended. It's fast and handles most content well.

If you're summarizing very complex or technical content, try **Pro** for better results.

You can change this anytime - just pick from the dropdown!""",
                "highlight": None
            },
            {
                "title": "Step 3: Get Summaries",
                "content": """**The 'Get Summaries' Button** (highlighted)

Fetch and summarize content from multiple source types.

**Supported Sources:**

• **YouTube Channels** - Auto-fetches transcripts and summarizes
• **RSS Feeds** - Pulls recent articles from any RSS/Atom feed
• **Article Archives** - Extracts links from author/archive pages

**How it works:**

1. **Edit Sources** - Add your content sources (YouTube, RSS, or article pages)

2. **Set the timeframe** - Use the number field and dropdown:
   • "7 Days" = content from the past week
   • "24 Hours" = just today's content
   • "10 Videos" = most recent items

3. **Click 'Get Summaries'** - The AI will:
   • Fetch content from all your sources
   • For article archives, let you select which articles to include
   • Summarize everything into one briefing

4. The summary appears in the text area below

**Tip:** Start with just 1-2 sources and a few days to test it out.""",
                "highlight": "btn_get_summaries"
            },
            {
                "title": "Step 4: The Text Area",
                "content": """**The Main Text Area** (highlighted)

This is your universal input area - paste anything and it will be processed intelligently!

**What you can paste here:**

• **YouTube URLs** - Auto-detected and transcripts fetched
• **Article URLs** - Content fetched automatically
• **Mixed URLs** - YouTube + articles processed together
• **Plain text** - Used as-is for audio
• **Text with embedded links** - Yellow banner appears to fetch them

**Smart Detection:**
When you paste content:
• URLs detected → Yellow banner offers to fetch content
• Click "Fetch Content" → Articles/videos are fetched
• Click "Keep as Text" → URLs are kept as literal text
• Generate → Text is auto-cleaned for audio

**The buttons above:**
• **Fetch Article** - Alternative way to fetch article URLs
• **Settings** - Configure app options
• **Collapse** - Hide the text area to save space""",
                "highlight": "textbox"
            },
            {
                "title": "Step 5: Smart Audio Content Editor",
                "content": """**The Unified Content Editor**

The text area is now a smart editor that handles everything!

**How it works:**

1. Paste ANYTHING in the text area:
   • YouTube URLs (one or more)
   • Article URLs (one or more)
   • Mixed URLs (YouTube + articles together)
   • Plain text
   • Text with embedded links
2. URLs are **auto-detected** with a yellow banner
3. Click **"Fetch Content"** to pull in articles/videos, or ignore
4. Click either audio button - text is auto-cleaned for listening!

**Smart Features:**

• **URL Detection** - Yellow banner appears when URLs are detected
• **Toggle View** - Switch between raw and cleaned text
• **Auto-Clean** - Text is automatically cleaned when you Generate
• **Cached Results** - Cleaning is cached for instant regeneration

**The Toggle Button:**

After generating, a toggle button lets you:
• View the raw (original) text
• View the cleaned (audio-ready) text
• Switch back and forth to compare

**When to use 'Get Summaries':**

• Batch processing from configured sources
• Catching up on multiple channels/feeds at once""",
                "highlight": None
            },
            {
                "title": "Step 6: Generate Fast Audio",
                "content": """**The 'Generate Fast' Button** (highlighted)

This creates audio quickly using Google's text-to-speech (gTTS).

**Pros:**
• Very fast - usually under a minute
• Works reliably
• Good for testing or quick previews

**Cons:**
• Robotic-sounding voice
• Less natural than quality option

**When to use Fast:**

• You want to quickly test if content sounds right
• You're in a hurry
• You don't mind a computer-sounding voice

**Output:**
Audio files are saved in the output folder. Click 'Open Folder' to find them.""",
                "highlight": "btn_fast"
            },
            {
                "title": "Step 7: Generate Quality Audio",
                "content": """**The 'Generate Quality' Button** (highlighted)

This creates natural-sounding audio using Kokoro TTS.

**Before clicking:**

1. **Choose a voice** from the dropdown above the button
2. Click **'Play Sample'** to preview how the voice sounds
3. Then click **'Generate Quality'**

**Voice options include:**
• Male and female voices
• Different accents and speaking styles
• Various speeds and tones

**Pros:**
• Much more natural sounding
• Multiple voice choices
• Great for longer content

**Cons:**
• Takes longer to generate
• Requires more processing power

**Tip:** Try different voices to find one you like!""",
                "highlight": "btn_quality"
            },
            {
                "title": "Step 8: Finding Your Audio Files",
                "content": """**Where do your audio files go?**

Click the **'Open Folder'** button (at the bottom) to see your audio files.

**File naming:**

Audio files are automatically named with:
• The date (e.g., 2024-12-28)
• A topic from the content (e.g., "bitcoin-analysis")
• The format (e.g., .wav)

Example: `2024-12-28_bitcoin-market-analysis.wav`

**Playing your files:**

• Double-click any .wav file to play it
• Transfer to your phone or music player
• Upload to podcast apps or cloud storage

**Tip:** The output folder is in the same location as the app.""",
                "highlight": None
            },
            {
                "title": "You're All Set!",
                "content": """**Congratulations! You know the basics.**

**Quick Start Recipe:**

1. Paste your API key and click Save
2. Paste an article URL in the text area
3. Click "Fetch Content" when the yellow banner appears
4. Click 'Generate Fast' or 'Generate Quality'
5. Click 'Open Folder' to find your audio file

**Keyboard shortcuts:**
• The app remembers your API key
• Your last settings are preserved

**Getting Help:**
• Click **Settings** → **'? Start Tutorial'** to restart this guide
• Check the terminal/console window for detailed logs
• See README.md for full documentation

**Need to see this again?**
Open Settings and click '? Start Tutorial'!""",
                "highlight": None
            }
        ]

        self.current_tutorial_step = 0
        self._tutorial_original_borders = {}  # Store original border colors as (color, width) tuples
        self._tutorial_dialog = None  # Track current dialog for cleanup

        def clear_all_highlights():
            """Clear all tutorial highlights and restore original borders."""
            for name, original in self._tutorial_original_borders.items():
                try:
                    widget = getattr(self, name, None)
                    if widget:
                        if isinstance(original, tuple) and len(original) == 2:
                            widget.configure(border_color=original[0], border_width=original[1])
                        else:
                            widget.configure(border_color="gray50", border_width=1)
                except Exception:
                    pass
            self._tutorial_original_borders.clear()

        def highlight_widget(widget_name):
            """Highlight a widget by changing its border color and scroll to show it."""
            # Clear previous highlights
            clear_all_highlights()

            if not widget_name:
                return

            # Highlight new widget
            try:
                widget = getattr(self, widget_name, None)
                if widget:
                    # Store original border
                    try:
                        orig_color = widget.cget("border_color")
                        orig_width = widget.cget("border_width")
                        self._tutorial_original_borders[widget_name] = (orig_color, orig_width)
                    except Exception:
                        self._tutorial_original_borders[widget_name] = ("gray50", 1)

                    # Apply highlight - using bright yellow for visibility
                    widget.configure(border_color="#FFD700", border_width=3)

                    # Scroll to make widget visible in the main scrollable area
                    try:
                        widget.update_idletasks()
                        self.update_idletasks()

                        # Get the canvas and its scrollable region
                        # Find the page scroll frame this widget belongs to
                        current_page = self.pages.get(self._current_page, self.pages.get("summarize"))
                        canvas = current_page._parent_canvas

                        # Get widget position relative to the scrollable content
                        widget_y = widget.winfo_y()
                        widget_height = widget.winfo_height()

                        # Get the parent frames to calculate total offset
                        parent = widget.master
                        while parent and parent != current_page:
                            widget_y += parent.winfo_y()
                            parent = parent.master

                        # Get canvas visible area
                        canvas_height = canvas.winfo_height()
                        scroll_region = canvas.cget("scrollregion")
                        if scroll_region:
                            total_height = int(scroll_region.split()[-1])
                        else:
                            total_height = canvas_height

                        # Calculate scroll position to center the widget
                        if total_height > canvas_height:
                            # Target: put widget in upper third of visible area
                            target_y = max(0, widget_y - canvas_height // 3)
                            scroll_fraction = target_y / total_height
                            scroll_fraction = min(1.0, max(0.0, scroll_fraction))
                            canvas.yview_moveto(scroll_fraction)
                    except Exception as e:
                        # Fallback: try simple scroll to top for top widgets
                        try:
                            current_page._parent_canvas.yview_moveto(0)
                        except Exception:
                            pass
            except Exception as e:
                print(f"[Tutorial] Highlight error: {e}")

        def show_step(step_index):
            if step_index >= len(tutorial_steps):
                clear_all_highlights()  # Clear highlights when done
                return

            step = tutorial_steps[step_index]

            # Highlight the relevant widget
            highlight_widget(step.get("highlight"))

            dialog = ctk.CTkToplevel(self)
            self._tutorial_dialog = dialog  # Track for cleanup
            dialog.title(f"Tutorial ({step_index + 1}/{len(tutorial_steps)})")
            dialog.geometry("550x380")
            dialog.transient(self)
            # Don't use grab_set() - allow user to scroll main window to see highlights
            dialog.lift()
            dialog.attributes('-topmost', True)  # Keep dialog on top

            # Handle dialog close via X button or escape
            def on_close():
                clear_all_highlights()
                self._tutorial_dialog = None
                dialog.destroy()
                self.label_status.configure(text="Tutorial closed", text_color="gray")

            dialog.protocol("WM_DELETE_WINDOW", on_close)

            # Center dialog
            dialog.update_idletasks()
            x = self.winfo_x() + (self.winfo_width() // 2) - 275
            y = self.winfo_y() + (self.winfo_height() // 2) - 190
            dialog.geometry(f"550x380+{x}+{y}")

            dialog.grid_columnconfigure(0, weight=1)
            dialog.grid_rowconfigure(1, weight=1)

            # Title
            ctk.CTkLabel(
                dialog, text=step["title"],
                font=ctk.CTkFont(size=18, weight="bold")
            ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

            # Content
            content_frame = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
            content_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

            # Render content with basic markdown
            self._render_tutorial_content(content_frame, step["content"])

            # Buttons
            btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            btn_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")
            btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

            def go_prev():
                self._tutorial_dialog = None
                dialog.destroy()
                show_step(step_index - 1)

            def go_next():
                self._tutorial_dialog = None
                dialog.destroy()
                if step_index < len(tutorial_steps) - 1:
                    show_step(step_index + 1)
                else:
                    clear_all_highlights()

            def skip():
                clear_all_highlights()  # Clear highlights
                self._tutorial_dialog = None
                dialog.destroy()
                self.label_status.configure(text="Tutorial skipped", text_color="gray")

            def finish():
                clear_all_highlights()  # Clear highlights
                self._tutorial_dialog = None
                dialog.destroy()
                self.label_status.configure(text="Tutorial complete!", text_color="green")

            if step_index > 0:
                ctk.CTkButton(btn_frame, text="← Back", fg_color="gray", command=go_prev).grid(row=0, column=0, padx=5, sticky="ew")
            else:
                ctk.CTkLabel(btn_frame, text="").grid(row=0, column=0)

            ctk.CTkButton(btn_frame, text="Skip Tutorial", fg_color="gray", command=skip).grid(row=0, column=1, padx=5, sticky="ew")

            if step_index < len(tutorial_steps) - 1:
                ctk.CTkButton(btn_frame, text="Next →", fg_color="green", command=go_next).grid(row=0, column=2, padx=5, sticky="ew")
            else:
                ctk.CTkButton(btn_frame, text="Finish", fg_color="green", command=finish).grid(row=0, column=2, padx=5, sticky="ew")

        show_step(0)

    def _render_tutorial_content(self, parent, content):
        """Render tutorial content with basic markdown formatting."""
        lines = content.strip().split('\n')
        for line in lines:
            if line.startswith('**') and line.endswith('**'):
                # Bold header
                text = line.strip('*')
                ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(weight="bold"), wraplength=480, justify="left").pack(anchor="w", pady=(5, 2))
            elif line.startswith('• '):
                # Bullet point
                text = line[2:]
                # Handle inline bold
                if '**' in text:
                    text = text.replace('**', '')
                ctk.CTkLabel(parent, text=f"  • {text}", wraplength=480, justify="left").pack(anchor="w")
            elif line.strip() == '':
                # Empty line
                ctk.CTkLabel(parent, text="", height=5).pack()
            else:
                # Regular text - handle inline bold
                text = line.replace('**', '')
                ctk.CTkLabel(parent, text=text, wraplength=480, justify="left").pack(anchor="w")

    def show_compression_guide(self):
        """Show the audio compression installation guide in a popup window."""
        guide_window = ctk.CTkToplevel(self)
        guide_window.title("Audio Compression Guide")
        guide_window.geometry("900x700")
        guide_window.transient(self)
        guide_window.lift()
        
        # Header with icon
        header_frame = ctk.CTkFrame(guide_window, fg_color=("gray85", "gray25"))
        header_frame.pack(fill="x", padx=0, pady=0)
        
        header_label = ctk.CTkLabel(
            header_frame,
            text="🎵 Audio Compression Installation Guide",
            font=ctk.CTkFont(size=20, weight="bold"),
            pady=20
        )
        header_label.pack()
        
        # Load the markdown content
        guide_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "AUDIO_COMPRESSION_GUIDE.md")
        guide_content = ""
        
        try:
            with open(guide_path, "r", encoding="utf-8") as f:
                guide_content = f.read()
        except Exception as e:
            guide_content = f"Error loading guide: {e}\n\nPlease check AUDIO_COMPRESSION_GUIDE.md in the project root."
        
        # Create scrollable frame for content
        scroll_frame = ctk.CTkScrollableFrame(guide_window, width=860, height=540)
        scroll_frame.pack(padx=20, pady=(10, 10), fill="both", expand=True)
        
        # Parse and format markdown content
        self._render_markdown(scroll_frame, guide_content)
        
        # Close button - always visible at bottom
        button_frame = ctk.CTkFrame(guide_window, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        close_btn = ctk.CTkButton(
            button_frame,
            text="Close",
            command=guide_window.destroy,
            width=200,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        close_btn.pack(pady=10)
    
    def _render_markdown(self, parent, markdown_text):
        """Render markdown text with formatted styling."""
        lines = markdown_text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Skip empty lines
            if not line.strip():
                i += 1
                continue
            
            # H1 Headers
            if line.startswith('# '):
                text = line[2:].strip()
                label = ctk.CTkLabel(
                    parent,
                    text=text,
                    font=ctk.CTkFont(size=24, weight="bold"),
                    anchor="w",
                    justify="left"
                )
                label.pack(fill="x", padx=10, pady=(20, 10))
            
            # H2 Headers
            elif line.startswith('## '):
                text = line[3:].strip()
                label = ctk.CTkLabel(
                    parent,
                    text=text,
                    font=ctk.CTkFont(size=18, weight="bold"),
                    anchor="w",
                    justify="left",
                    text_color=("gray10", "#3b8ed0")
                )
                label.pack(fill="x", padx=10, pady=(15, 8))
            
            # H3 Headers
            elif line.startswith('### '):
                text = line[4:].strip()
                label = ctk.CTkLabel(
                    parent,
                    text=text,
                    font=ctk.CTkFont(size=14, weight="bold"),
                    anchor="w",
                    justify="left"
                )
                label.pack(fill="x", padx=10, pady=(10, 5))
            
            # Code blocks
            elif line.startswith('```'):
                i += 1
                code_lines = []
                while i < len(lines) and not lines[i].startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                
                code_frame = ctk.CTkFrame(parent, fg_color=("gray90", "gray20"))
                code_frame.pack(fill="x", padx=15, pady=8)
                
                code_text = '\n'.join(code_lines)
                code_label = ctk.CTkLabel(
                    code_frame,
                    text=code_text,
                    font=ctk.CTkFont(family="Courier", size=12),
                    anchor="w",
                    justify="left"
                )
                code_label.pack(fill="x", padx=15, pady=10)
            
            # Bullet points
            elif line.startswith('- ') or line.startswith('* '):
                text = line[2:].strip()
                # Handle bold text
                text = text.replace('**', '')
                
                bullet_frame = ctk.CTkFrame(parent, fg_color="transparent")
                bullet_frame.pack(fill="x", padx=20, pady=2)
                
                bullet = ctk.CTkLabel(
                    bullet_frame,
                    text="•",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    width=20
                )
                bullet.pack(side="left", anchor="n")
                
                content = ctk.CTkLabel(
                    bullet_frame,
                    text=text,
                    font=ctk.CTkFont(size=13),
                    anchor="w",
                    justify="left",
                    wraplength=800
                )
                content.pack(side="left", fill="x", expand=True)
            
            # Regular paragraphs
            else:
                # Skip lines that look like metadata or separators
                if not line.strip() or line.strip() == '---':
                    i += 1
                    continue
                
                # Handle bold text
                text = line.replace('**', '')
                
                label = ctk.CTkLabel(
                    parent,
                    text=text,
                    font=ctk.CTkFont(size=13),
                    anchor="w",
                    justify="left",
                    wraplength=850
                )
                label.pack(fill="x", padx=15, pady=3)
            
            i += 1

    def select_dates_to_audio(self):
        """Show dialog to select dates for audio conversion with archive options."""
        data_dir = get_data_directory()
        archive_dir = os.path.join(data_dir, "Archive")

        # Find all summary files in Week_* folders (excluding Archive)
        files = []
        for week_folder in sorted(glob.glob(os.path.join(data_dir, "Week_*"))):
            if os.path.isdir(week_folder):
                week_summaries = sorted([
                    os.path.join(week_folder, f)
                    for f in os.listdir(week_folder)
                    if f.startswith("summary_") and f.endswith(".txt")
                ])
                files.extend(week_summaries)

        if not files:
            # Check if there are archived items
            has_archive = os.path.exists(archive_dir) and any(
                f.startswith("Week_") and os.path.isdir(os.path.join(archive_dir, f))
                for f in os.listdir(archive_dir)
            ) if os.path.exists(archive_dir) else False

            if has_archive:
                # Show dialog with option to view archive
                dlg = ctk.CTkToplevel(self)
                dlg.title("No Summaries Found")
                dlg.geometry("400x150")
                dlg.minsize(350, 130)
                ctk.CTkLabel(dlg, text="No per-date summaries found in Week folders.",
                            font=ctk.CTkFont(size=14)).pack(pady=20)
                ctk.CTkLabel(dlg, text="You have archived items that can be restored.",
                            font=ctk.CTkFont(size=12), text_color="gray").pack()
                btn_frame = ctk.CTkFrame(dlg)
                btn_frame.pack(pady=15)
                ctk.CTkButton(btn_frame, text="View Archive", command=lambda: [dlg.destroy(), self.view_archive()],
                             fg_color="#5a5a5a", width=120).pack(side="left", padx=5)
                ctk.CTkButton(btn_frame, text="Close", command=dlg.destroy, fg_color="gray", width=100).pack(side="left", padx=5)
            else:
                self.label_status.configure(text="No per-date summaries found in Week folders.", text_color="orange")
            return

        dlg = ctk.CTkToplevel(self)
        dlg.title("Select Dates to Convert")
        dlg.geometry("550x550")
        dlg.minsize(450, 350)  # Set minimum size to ensure buttons visible

        # Configure grid layout for proper resizing
        dlg.grid_columnconfigure(0, weight=1)
        dlg.grid_rowconfigure(0, weight=1)  # Scrollable frame row expands

        # Main scrollable frame for checkboxes - row 0 (expands)
        frame = ctk.CTkScrollableFrame(dlg, width=510, height=350)
        frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        checks = []
        for i, filepath in enumerate(files):
            filename = os.path.basename(filepath)
            date_label = filename.replace("summary_", "").replace(".txt", "")
            week_folder_name = os.path.basename(os.path.dirname(filepath))
            var = ctk.BooleanVar(value=False)  # Default to unchecked for safety
            ctk.CTkCheckBox(frame, text=f"{date_label} ({week_folder_name})", variable=var).grid(row=i, column=0, sticky="w", padx=8, pady=4)
            checks.append((filepath, var))

        # Selection buttons frame - row 1 (fixed)
        select_btn_frame = ctk.CTkFrame(dlg)
        select_btn_frame.grid(row=1, column=0, pady=5)

        def select_all():
            for filepath, var in checks:
                var.set(True)

        def deselect_all():
            for filepath, var in checks:
                var.set(False)

        ctk.CTkButton(select_btn_frame, text="Select All", command=select_all, fg_color="green", width=100).pack(side="left", padx=5)
        ctk.CTkButton(select_btn_frame, text="Deselect All", command=deselect_all, fg_color="gray", width=100).pack(side="left", padx=5)

        # Action buttons frame - row 2 (fixed)
        action_btn_frame = ctk.CTkFrame(dlg)
        action_btn_frame.grid(row=2, column=0, pady=10)

        def do_archive():
            selected = [filepath for filepath, v in checks if v.get()]
            if not selected:
                return

            # Confirmation dialog
            confirm = ctk.CTkToplevel(dlg)
            confirm.title("Confirm Archive")
            confirm.geometry("400x200")
            confirm.minsize(400, 200)
            confirm.transient(dlg)
            confirm.grab_set()

            file_names = [os.path.basename(f).replace("summary_", "").replace(".txt", "") for f in selected]
            ctk.CTkLabel(confirm, text=f"Are you sure you want to archive {len(selected)} file(s)?",
                        font=ctk.CTkFont(size=14)).pack(pady=(20, 10))
            display_names = ", ".join(file_names[:5]) + ("..." if len(file_names) > 5 else "")
            ctk.CTkLabel(confirm, text=f"Dates: {display_names}",
                        font=ctk.CTkFont(size=11), text_color="gray", wraplength=350).pack(pady=5)
            ctk.CTkLabel(confirm, text="Archived files can be restored from the Archive.",
                        font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 10))

            btn_confirm_frame = ctk.CTkFrame(confirm)
            btn_confirm_frame.pack(pady=(10, 25))

            def confirm_archive():
                confirm.destroy()
                # Create archive directory if needed
                os.makedirs(archive_dir, exist_ok=True)

                archived_count = 0
                for filepath in selected:
                    try:
                        # Get the week folder name to preserve structure
                        week_folder_name = os.path.basename(os.path.dirname(filepath))
                        filename = os.path.basename(filepath)
                        dest_week_folder = os.path.join(archive_dir, week_folder_name)

                        # Create week folder in archive if needed
                        os.makedirs(dest_week_folder, exist_ok=True)

                        # Move individual file to archive
                        dest_path = os.path.join(dest_week_folder, filename)
                        if os.path.exists(filepath):
                            shutil.move(filepath, dest_path)
                            archived_count += 1

                            # Also move associated audio file if exists
                            date_str = filename.replace("summary_", "").replace(".txt", "")
                            audio_file = os.path.join(os.path.dirname(filepath), f"audio_quality_{date_str}.wav")
                            if os.path.exists(audio_file):
                                shutil.move(audio_file, os.path.join(dest_week_folder, os.path.basename(audio_file)))

                    except Exception as e:
                        print(f"Error archiving {filepath}: {e}")

                # Clean up empty week folders in main directory
                for week_folder in glob.glob(os.path.join(data_dir, "Week_*")):
                    if os.path.isdir(week_folder) and not os.listdir(week_folder):
                        os.rmdir(week_folder)

                dlg.destroy()
                self.label_status.configure(text=f"Archived {archived_count} file(s).", text_color="green")

            ctk.CTkButton(btn_confirm_frame, text="Yes, Archive", command=confirm_archive, fg_color="orange", width=120).pack(side="left", padx=10)
            ctk.CTkButton(btn_confirm_frame, text="Cancel", command=confirm.destroy, fg_color="gray", width=100).pack(side="left", padx=10)

        def do_convert():
            selected = [filepath for filepath, v in checks if v.get()]
            if not selected:
                dlg.destroy()
                return
            dlg.destroy()

            # Convert each selected file in SEQUENTIAL queue (one at a time to avoid CPU overload)
            voice = self.voice_var.get()

            def task():
                import time
                import importlib
                data_dir = get_data_directory()
                log_path = os.path.join(data_dir, "gui_log.txt")

                # Set flag to prevent scheduler from overwriting our status updates
                self._long_operation_in_progress = True

                total = len(selected)
                try:
                    for idx, filepath in enumerate(selected, 1):
                        try:
                            filename = os.path.basename(filepath)
                            date_str = filename.replace("summary_", "").replace(".txt", "")
                            week_folder = os.path.dirname(filepath)
                            output_file = os.path.join(week_folder, f"audio_quality_{date_str}.wav")

                            # Update GUI frequently
                            self.after(0, lambda d=date_str, i=idx, t=total: self.label_status.configure(
                                text=f"Converting {i}/{t}: {d}...", text_color=("gray10", "#DCE4EE")))

                            # Enhanced logging for debugging
                            with open(log_path, "a", encoding="utf-8") as log:
                                log.write(f"\n{'='*60}\n")
                                log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Converting {idx}/{total}: {date_str}\n")
                                log.write(f"Input: {filepath}\n")
                                log.write(f"Output: {output_file}\n")
                                log.flush()

                            start_time = time.time()

                            if getattr(sys, "frozen", False):
                                # FROZEN MODE: Run in-process with output capture
                                import io
                                from contextlib import redirect_stdout, redirect_stderr

                                old_argv = sys.argv
                                old_cwd = os.getcwd()
                                stdout_capture = io.StringIO()
                                stderr_capture = io.StringIO()

                                sys.argv = ["make_audio_quality.py", "--input", filepath,
                                           "--voice", voice, "--output", output_file]

                                # Change to data directory for proper file access
                                os.chdir(data_dir)

                                try:
                                    import make_audio_quality
                                    importlib.reload(make_audio_quality)
                                    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                                        make_audio_quality.main()
                                    return_code = 0
                                    stdout_text = stdout_capture.getvalue()
                                    stderr_text = stderr_capture.getvalue()
                                except SystemExit as e:
                                    return_code = e.code if e.code else 0
                                    stdout_text = stdout_capture.getvalue()
                                    stderr_text = stderr_capture.getvalue()
                                except Exception as e:
                                    return_code = 1
                                    stdout_text = stdout_capture.getvalue()
                                    stderr_text = stderr_capture.getvalue() + f"\nException: {e}\n"
                                    import traceback
                                    stderr_text += traceback.format_exc()
                                finally:
                                    sys.argv = old_argv
                                    os.chdir(old_cwd)
                            else:
                                # DEVELOPMENT MODE: Use subprocess
                                script_dir = os.path.dirname(__file__)
                                python_exe = sys.executable
                                cmd = [python_exe, os.path.join(script_dir, "make_audio_quality.py"),
                                       "--input", filepath, "--voice", voice, "--output", output_file]
                                with open(log_path, "a", encoding="utf-8") as log:
                                    log.write(f"Command: {' '.join(cmd)}\n")
                                    log.flush()
                                result = subprocess.run(cmd, capture_output=True, text=True, cwd=script_dir, timeout=3600)
                                return_code = result.returncode
                                stdout_text = result.stdout
                                stderr_text = result.stderr
                            elapsed = time.time() - start_time

                            # Log result details
                            # Check for both .wav and .mp3 (script converts to mp3 and deletes wav)
                            mp3_output = os.path.splitext(output_file)[0] + ".mp3"
                            actual_output = mp3_output if os.path.exists(mp3_output) else output_file

                            with open(log_path, "a", encoding="utf-8") as log:
                                log.write(f"Return code: {return_code}\n")
                                log.write(f"Elapsed time: {elapsed:.1f}s\n")
                                if stdout_text:
                                    log.write(f"STDOUT:\n{stdout_text}\n")
                                if stderr_text:
                                    log.write(f"STDERR:\n{stderr_text}\n")
                                log.write(f"Output file exists: {os.path.exists(actual_output)}\n")
                                if os.path.exists(actual_output):
                                    file_size_mb = os.path.getsize(actual_output) / (1024*1024)
                                    log.write(f"Output file: {actual_output} ({file_size_mb:.1f}MB)\n")
                                log.flush()

                            if return_code != 0:
                                error_msg = f"Error converting {date_str}: {stderr_text[:100] if stderr_text else 'Unknown error'}"
                                self.after(0, lambda m=error_msg: self.label_status.configure(
                                    text=m, text_color="red"))
                                with open(log_path, "a", encoding="utf-8") as log:
                                    log.write(f"ERROR: Conversion failed\n")
                                continue  # Continue with next file instead of stopping

                            # Success message
                            with open(log_path, "a", encoding="utf-8") as log:
                                log.write(f"SUCCESS: {date_str} converted in {elapsed:.1f}s\n")

                        except subprocess.TimeoutExpired:
                            # Check if file was actually created despite timeout
                            # Also check for MP3 (script converts to mp3 and deletes wav)
                            mp3_output = os.path.splitext(output_file)[0] + ".mp3"
                            timeout_output = mp3_output if os.path.exists(mp3_output) else output_file

                            if os.path.exists(timeout_output) and os.path.getsize(timeout_output) > 0:
                                file_size_mb = os.path.getsize(timeout_output) / (1024*1024)
                                with open(log_path, "a", encoding="utf-8") as log:
                                    log.write(f"TIMEOUT but file created: {timeout_output} ({file_size_mb:.1f}MB)\n")
                                success_msg = f"✓ {date_str} completed (took >1hr)"
                                self.after(0, lambda m=success_msg: self.label_status.configure(
                                    text=m, text_color="green"))
                            else:
                                error_msg = f"✗ Timeout on {date_str} - no output file"
                                self.after(0, lambda m=error_msg: self.label_status.configure(
                                    text=m, text_color="red"))
                                with open(log_path, "a", encoding="utf-8") as log:
                                    log.write(f"ERROR: Timeout after 3600s, no output file\n")
                            continue  # Move to next file
                        except Exception as e:
                            self.after(0, lambda err=str(e): self.label_status.configure(
                                text=f"Error: {err}", text_color="red"))
                            with open(log_path, "a", encoding="utf-8") as log:
                                log.write(f"EXCEPTION: {e}\n")
                            continue  # Move to next file

                    # All conversions completed
                    self.after(0, lambda t=total: self.label_status.configure(
                        text=f"✓ Converted {t} audio files! Check Week folders.", text_color="green"))
                finally:
                    # Clear the flag so scheduler can update status again
                    self._long_operation_in_progress = False

            threading.Thread(target=task, daemon=True).start()

        ctk.CTkButton(action_btn_frame, text="Convert", command=do_convert, width=100).pack(side="left", padx=5)
        ctk.CTkButton(action_btn_frame, text="Archive Selected", command=do_archive, fg_color="orange", width=120).pack(side="left", padx=5)
        ctk.CTkButton(action_btn_frame, text="View Archive", command=lambda: self.view_archive(dlg), fg_color="#5a5a5a", width=100).pack(side="left", padx=5)
        ctk.CTkButton(action_btn_frame, text="Cancel", fg_color="gray", command=dlg.destroy, width=100).pack(side="left", padx=5)

    def view_archive(self, parent_dlg=None):
        """Show dialog to view and unarchive files from the Archive."""
        data_dir = get_data_directory()
        archive_dir = os.path.join(data_dir, "Archive")

        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir, exist_ok=True)

        # Find all summary files in archived Week_* folders
        archived_files = []
        for week_folder in sorted(glob.glob(os.path.join(archive_dir, "Week_*"))):
            if os.path.isdir(week_folder):
                week_summaries = sorted([
                    os.path.join(week_folder, f)
                    for f in os.listdir(week_folder)
                    if f.startswith("summary_") and f.endswith(".txt")
                ])
                archived_files.extend(week_summaries)

        dlg = ctk.CTkToplevel(self)
        dlg.title("Archive")
        dlg.geometry("550x450")
        dlg.minsize(450, 350)  # Set minimum size to ensure buttons visible
        if parent_dlg:
            dlg.transient(parent_dlg)

        # Configure grid layout for proper resizing
        dlg.grid_columnconfigure(0, weight=1)
        dlg.grid_rowconfigure(1, weight=1)  # Scrollable frame row expands

        if not archived_files:
            ctk.CTkLabel(dlg, text="Archive is empty.", font=ctk.CTkFont(size=14)).grid(row=0, column=0, pady=50)
            ctk.CTkButton(dlg, text="Close", command=dlg.destroy, width=100).grid(row=1, column=0, pady=20)
            return

        # Header label - row 0
        ctk.CTkLabel(dlg, text="Archived Files", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, pady=10)

        # Scrollable frame - row 1 (expands)
        frame = ctk.CTkScrollableFrame(dlg, width=510, height=250)
        frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        checks = []
        for i, filepath in enumerate(archived_files):
            filename = os.path.basename(filepath)
            date_label = filename.replace("summary_", "").replace(".txt", "")
            week_folder_name = os.path.basename(os.path.dirname(filepath))
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(frame, text=f"{date_label} ({week_folder_name})", variable=var).grid(row=i, column=0, sticky="w", padx=8, pady=4)
            checks.append((filepath, var))

        # Selection buttons - row 2 (fixed)
        select_btn_frame = ctk.CTkFrame(dlg)
        select_btn_frame.grid(row=2, column=0, pady=5)

        def select_all():
            for path, var in checks:
                var.set(True)

        def deselect_all():
            for path, var in checks:
                var.set(False)

        ctk.CTkButton(select_btn_frame, text="Select All", command=select_all, fg_color="green", width=100).pack(side="left", padx=5)
        ctk.CTkButton(select_btn_frame, text="Deselect All", command=deselect_all, fg_color="gray", width=100).pack(side="left", padx=5)

        # Action buttons - row 3 (fixed)
        action_btn_frame = ctk.CTkFrame(dlg)
        action_btn_frame.grid(row=3, column=0, pady=10)

        def do_unarchive():
            selected = [path for path, v in checks if v.get()]
            if not selected:
                return

            # Confirmation dialog
            confirm = ctk.CTkToplevel(dlg)
            confirm.title("Confirm Restore")
            confirm.geometry("400x180")
            confirm.minsize(400, 180)
            confirm.transient(dlg)
            confirm.grab_set()

            ctk.CTkLabel(confirm, text=f"Are you sure you want to restore {len(selected)} file(s)?",
                        font=ctk.CTkFont(size=14)).pack(pady=(25, 10))
            ctk.CTkLabel(confirm, text="Files will be moved back to their Week folders.",
                        font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 15))

            btn_confirm_frame = ctk.CTkFrame(confirm)
            btn_confirm_frame.pack(pady=(10, 25))

            def confirm_unarchive():
                confirm.destroy()
                restored_count = 0
                for filepath in selected:
                    try:
                        # Get the week folder name to preserve structure
                        week_folder_name = os.path.basename(os.path.dirname(filepath))
                        filename = os.path.basename(filepath)
                        dest_week_folder = os.path.join(data_dir, week_folder_name)

                        # Create week folder if needed
                        os.makedirs(dest_week_folder, exist_ok=True)

                        # Move file back to main directory
                        dest_path = os.path.join(dest_week_folder, filename)
                        if os.path.exists(filepath):
                            shutil.move(filepath, dest_path)
                            restored_count += 1

                            # Also move associated audio file if exists
                            date_str = filename.replace("summary_", "").replace(".txt", "")
                            audio_file = os.path.join(os.path.dirname(filepath), f"audio_quality_{date_str}.wav")
                            if os.path.exists(audio_file):
                                shutil.move(audio_file, os.path.join(dest_week_folder, os.path.basename(audio_file)))

                    except Exception as e:
                        print(f"Error restoring {filepath}: {e}")

                # Clean up empty week folders in archive
                for week_folder in glob.glob(os.path.join(archive_dir, "Week_*")):
                    if os.path.isdir(week_folder) and not os.listdir(week_folder):
                        os.rmdir(week_folder)

                dlg.destroy()
                if parent_dlg:
                    parent_dlg.destroy()
                self.label_status.configure(text=f"Restored {restored_count} file(s) from archive.", text_color="green")

            ctk.CTkButton(btn_confirm_frame, text="Yes, Restore", command=confirm_unarchive, fg_color="green", width=120).pack(side="left", padx=10)
            ctk.CTkButton(btn_confirm_frame, text="Cancel", command=confirm.destroy, fg_color="gray", width=100).pack(side="left", padx=10)

        ctk.CTkButton(action_btn_frame, text="Restore Selected", command=do_unarchive, fg_color="green", width=120).pack(side="left", padx=5)
        ctk.CTkButton(action_btn_frame, text="Close", command=dlg.destroy, fg_color="gray", width=100).pack(side="left", padx=5)
    def convert_summaries_to_audio(self, files):
        voice = self.voice_var.get()
        def task():
            try:
                import importlib
                data_dir = get_data_directory()
                for f in files:
                    date = os.path.basename(f).split("_")[1].replace(".txt", "")
                    out = os.path.join(data_dir, f"daily_{date}.wav")

                    if getattr(sys, "frozen", False):
                        # FROZEN MODE: Run in-process
                        old_argv = sys.argv
                        sys.argv = ["make_audio_quality.py", "--voice", voice, "--input", f, "--output", out]
                        try:
                            import make_audio_quality
                            importlib.reload(make_audio_quality)
                            make_audio_quality.main()
                        finally:
                            sys.argv = old_argv
                    else:
                        # DEVELOPMENT MODE: Use subprocess
                        script_dir = os.path.dirname(__file__)
                        python_exe = sys.executable
                        subprocess.run([python_exe, os.path.join(script_dir, "make_audio_quality.py"),
                                       "--voice", voice, "--input", f, "--output", out],
                                      capture_output=True, text=True, cwd=script_dir)
                self.after(0, lambda: self.label_status.configure(text="Audio conversion complete.", text_color="green"))
            except Exception as e:
                self.after(0, lambda: self.label_status.configure(text=f"Error converting: {e}", text_color="red"))
        threading.Thread(target=task, daemon=True).start()

        data_dir = get_data_directory()
        if sys.platform == "darwin": subprocess.run(["open", data_dir])
        elif sys.platform == "win32": os.startfile(data_dir)
        else: subprocess.run(["xdg-open", data_dir])

    # =========================================================================
    # DATA EXTRACTION METHODS
    # =========================================================================

    def _get_extraction_configs(self):
        """Get list of available extraction config files."""
        configs = ["Default"]
        config_dir = os.path.join(os.path.dirname(__file__), "extraction_instructions")
        if os.path.exists(config_dir):
            for f in os.listdir(config_dir):
                if f.endswith(".json") and not f.startswith("_"):
                    name = f.replace(".json", "").replace("_", " ").title()
                    configs.append(name)
        return configs

    def toggle_text_section(self):
        """Toggle the news summary text area visibility (legacy — text always visible now)."""
        pass  # No-op: text area is always visible on its own page

    # toggle_extract_section, toggle_advanced_section, toggle_transcription_section,
    # toggle_scheduler_section — REMOVED: pages have their own navigation now

    # ========== Scheduler Methods ==========

    def _init_scheduler(self):
        """Initialize the scheduler backend and restore persisted active state."""
        try:
            from scheduler import get_scheduler
            self._scheduler = get_scheduler(
                on_task_complete=self._on_scheduler_task_complete,
                on_progress=self._on_scheduler_progress,
                on_task_start=self._on_scheduler_task_start
            )
            self._refresh_scheduler_tasks()

            # Restore scheduler active state from settings
            if self.settings.get("scheduler_active", False):
                self._scheduler.start()
                self.scheduler_enabled_var.set(True)
                self.scheduler_status_label.configure(text="● Running", text_color="green")
        except Exception as e:
            print(f"[Scheduler] Init error: {e}")
            self._scheduler = None

    def _toggle_scheduler(self):
        """Toggle scheduler on/off."""
        if not self._scheduler:
            self._init_scheduler()
            if not self._scheduler:
                self.scheduler_enabled_var.set(False)
                if self.label_status:
                    self.label_status.configure(text="Scheduler initialization failed", text_color="red")
                return

        if self.scheduler_enabled_var.get():
            self._scheduler.start()
            self.scheduler_status_label.configure(text="● Running", text_color="green")
            if self.label_status:
                self.label_status.configure(text="Scheduler started", text_color="green")
        else:
            self._scheduler.stop()
            self.scheduler_status_label.configure(text="● Stopped", text_color="gray")
            if self.label_status:
                self.label_status.configure(text="Scheduler stopped", text_color="gray")

        # Persist state so scheduler auto-starts on next launch
        self.settings["scheduler_active"] = self.scheduler_enabled_var.get()
        self._save_settings()

    def _on_scheduler_task_start(self, task):
        """Callback when a scheduled task begins executing."""
        task_type = getattr(task, 'task_type', 'extraction')
        type_label = "pipeline" if task_type == "briefing_pipeline" else "extraction"

        # Show animated status on Scheduler page
        self._task_running_id = task.id
        self.after(0, lambda: self._show_scheduler_status(
            f"⏳ Running: {task.name}...", "orange"))
        self.after(0, lambda: self._animate_task_status(task.name, 0))

        # Update Summarize page status bar (visible from any page)
        if self.label_status:
            self.after(0, lambda: self.label_status.configure(
                text=f"⏳ {task.name} {type_label} running...", text_color="orange"))

        # macOS desktop notification
        try:
            import subprocess as sp
            sp.Popen([
                "osascript", "-e",
                f'display notification "{task.name} {type_label} started" '
                f'with title "Daily Audio Briefing"'
            ], stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        except Exception:
            pass

    def _on_scheduler_task_complete(self, task, success, message):
        """Callback when a scheduled task completes."""
        color = "green" if success else "red"
        icon = "✅" if success else "❌"

        # Stop the running animation
        self._task_running_id = None

        # Hide stop button if visible
        if hasattr(self, '_task_log_stop'):
            self.after(0, lambda: self._task_log_stop.grid_remove())

        # Show result on Scheduler page
        self.after(0, lambda: self._show_scheduler_status(
            f"{icon} {task.name}: {message}", color))

        # Auto-collapse log and hide panel after success (keep visible on error)
        if success:
            self.after(10000, lambda: self._hide_scheduler_status())

        # Also update Summarize page status if visible
        if not self._long_operation_in_progress and self.label_status:
            self.after(0, lambda: self.label_status.configure(
                text=f"Task '{task.name}': {message}", text_color=color))
            # Clear the status bar after 15 seconds so it doesn't persist
            if success:
                self.after(15000, lambda: self.label_status.configure(
                    text="Ready", text_color="gray") if not self._long_operation_in_progress else None)

        # macOS desktop notification
        try:
            import subprocess as sp
            status = "complete" if success else "failed"
            # Truncate message for notification
            short_msg = message[:80] if len(message) > 80 else message
            sp.Popen([
                "osascript", "-e",
                f'display notification "{short_msg}" '
                f'with title "Daily Audio Briefing" '
                f'subtitle "{task.name} {status}"'
            ], stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        except Exception:
            pass

        self.after(0, self._refresh_scheduler_tasks)

    def _hide_scheduler_status(self):
        """Hide the scheduler run status panel (but keep log if expanded)."""
        if self._task_running_id is not None:
            return  # Don't hide while task is running
        if hasattr(self, '_task_log_frame') and not self._task_log_expanded:
            # Only fully hide if log is collapsed
            self._task_log_frame.grid_remove()

    # ========== Background Scheduler Methods ==========

    def _init_background_scheduler_state(self):
        """Initialize the background scheduler UI state based on current daemon status."""
        try:
            from scheduler_daemon import is_background_scheduler_running, is_launch_on_login_enabled

            # Check if daemon is running
            if is_background_scheduler_running():
                self.bg_scheduler_var.set(True)
                self.bg_scheduler_status.configure(text="● Running", text_color="green")
            else:
                self.bg_scheduler_var.set(False)
                self.bg_scheduler_status.configure(text="● Not running", text_color="gray")

            # Check launch on login status
            if is_launch_on_login_enabled():
                self.launch_on_login_var.set(True)
            else:
                self.launch_on_login_var.set(False)

        except Exception as e:
            print(f"[BackgroundScheduler] Init state error: {e}")

    def _toggle_background_scheduler(self):
        """Toggle the background scheduler daemon on/off."""
        try:
            from scheduler_daemon import start_background_scheduler, stop_background_scheduler, is_background_scheduler_running

            if self.bg_scheduler_var.get():
                # Start the daemon
                success = start_background_scheduler()
                if success:
                    self.bg_scheduler_status.configure(text="● Running", text_color="green")
                    self.label_status.configure(text="Background scheduler started", text_color="green")
                else:
                    self.bg_scheduler_var.set(False)
                    self.bg_scheduler_status.configure(text="● Failed to start", text_color="red")
                    self.label_status.configure(text="Failed to start background scheduler", text_color="red")
            else:
                # Stop the daemon
                success = stop_background_scheduler()
                if success:
                    self.bg_scheduler_status.configure(text="● Not running", text_color="gray")
                    self.label_status.configure(text="Background scheduler stopped", text_color="gray")
                else:
                    # Check if it's actually still running
                    if is_background_scheduler_running():
                        self.bg_scheduler_var.set(True)
                        self.label_status.configure(text="Failed to stop background scheduler", text_color="red")

        except Exception as e:
            print(f"[BackgroundScheduler] Toggle error: {e}")
            self.label_status.configure(text=f"Background scheduler error: {str(e)[:50]}", text_color="red")

    def _toggle_launch_on_login(self):
        """Toggle whether the scheduler starts on system login."""
        try:
            from scheduler_daemon import enable_launch_on_login, disable_launch_on_login

            if self.launch_on_login_var.get():
                success = enable_launch_on_login()
                if success:
                    self.label_status.configure(text="Scheduler will start on login", text_color="green")
                else:
                    self.launch_on_login_var.set(False)
                    self.label_status.configure(text="Failed to enable launch on login", text_color="red")
            else:
                success = disable_launch_on_login()
                if success:
                    self.label_status.configure(text="Scheduler will not start on login", text_color="gray")
                else:
                    self.launch_on_login_var.set(True)
                    self.label_status.configure(text="Failed to disable launch on login", text_color="red")

        except Exception as e:
            print(f"[BackgroundScheduler] Launch on login error: {e}")
            self.label_status.configure(text=f"Launch on login error: {str(e)[:50]}", text_color="red")

    def _refresh_scheduler_tasks(self):
        """Refresh the scheduler tasks list display."""
        scheduler = self._get_active_scheduler()

        # For cloud mode, refresh from server in background
        if self._scheduler_mode == "cloud" and self._cloud_client:
            def _fetch():
                self._cloud_client.refresh_tasks()
                self.after(0, self._render_scheduler_tasks)
            threading.Thread(target=_fetch, daemon=True).start()
            return

        self._render_scheduler_tasks()

    def _render_scheduler_tasks(self):
        """Render the scheduler tasks list (called on main thread)."""
        scheduler = self._get_active_scheduler()

        # Clear existing widgets
        for widget in self.scheduler_tasks_list.winfo_children():
            widget.destroy()

        if not scheduler or not scheduler.tasks:
            mode_text = "cloud server" if self._scheduler_mode == "cloud" else "local scheduler"
            self.scheduler_empty_label = ctk.CTkLabel(
                self.scheduler_tasks_list,
                text=f"No scheduled tasks on {mode_text}. Click '+ Add Task' to create one.",
                text_color="gray",
                font=("Arial", 11)
            )
            self.scheduler_empty_label.grid(row=0, column=0, pady=20)
            return

        for i, task in enumerate(scheduler.tasks):
            self._create_task_row(i, task)

    def _create_task_row(self, row: int, task):
        """Create a row for a scheduled task."""
        row_frame = ctk.CTkFrame(self.scheduler_tasks_list, fg_color=("gray90", "gray20"))
        row_frame.grid(row=row, column=0, sticky="ew", pady=2, padx=2)
        row_frame.grid_columnconfigure(1, weight=1)

        # Enable/disable checkbox
        enabled_var = ctk.BooleanVar(value=task.enabled)
        chk = ctk.CTkCheckBox(
            row_frame, text="", variable=enabled_var, width=24,
            command=lambda t=task, v=enabled_var: self._toggle_task_enabled(t.id, v.get())
        )
        chk.grid(row=0, column=0, padx=(5, 0), pady=5)

        # Task name and next run
        info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # Build name with capability badges
        task_display_name = task.name
        badges = []
        if getattr(task, 'task_type', 'extraction') == 'briefing_pipeline':
            badges.append("Pipeline")
        if getattr(task, 'enrich_with_grid', False):
            badges.append("Grid")
        if getattr(task, 'research_articles', False):
            badges.append("Research")
        if badges:
            task_display_name += f"  [{' + '.join(badges)}]"

        name_label = ctk.CTkLabel(info_frame, text=task_display_name, font=ctk.CTkFont(weight="bold"))
        name_label.pack(anchor="w")

        # Format next run time
        next_run_text = ""
        if task.next_run:
            try:
                from datetime import datetime
                next_dt = datetime.fromisoformat(task.next_run)
                next_run_text = f"Next: {next_dt.strftime('%b %d, %H:%M')}"
            except:
                next_run_text = "Next: --"
        else:
            next_run_text = "Next: --"

        status_text = f"{task.interval} • {next_run_text}"
        if task.last_result:
            status_text += f" • {task.last_result[:30]}"

        status_label = ctk.CTkLabel(info_frame, text=status_text, font=("Arial", 10), text_color="gray")
        status_label.pack(anchor="w")

        # Action buttons
        btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=5, pady=5)

        btn_run = ctk.CTkButton(
            btn_frame, text="▶", width=30, fg_color="green",
            command=lambda t=task: self._run_task_now(t.id)
        )
        btn_run.pack(side="left", padx=2)
        add_tooltip(btn_run, "Run this task now (single extraction)")

        btn_backfill = ctk.CTkButton(
            btn_frame, text="⏪", width=30, fg_color="#0d6efd",
            command=lambda t=task: self._backfill_task(t.id)
        )
        btn_backfill.pack(side="left", padx=2)
        add_tooltip(btn_backfill, "Backfill: Crawl the archive and fill in all missing dates")

        # Sheet link button (only if task exports to Sheets)
        if getattr(task, 'export_to_sheets', False) and getattr(task, 'spreadsheet_id', ''):
            sheet_id = task.spreadsheet_id
            sheet_name = getattr(task, 'sheet_name', '')
            btn_sheet = ctk.CTkButton(
                btn_frame, text="📊", width=30, fg_color="#0f9d58",
                command=lambda sid=sheet_id, sn=sheet_name: self._open_sheet(sid, sn)
            )
            btn_sheet.pack(side="left", padx=2)
            sheet_tip = f"Open Google Sheet"
            if sheet_name:
                sheet_tip += f" ({sheet_name})"
            add_tooltip(btn_sheet, sheet_tip)

        # Drive folder link button (only for pipeline tasks with Drive upload configured)
        if getattr(task, 'task_type', 'extraction') == 'briefing_pipeline' and getattr(task, 'drive_folder_id', ''):
            drive_fid = task.drive_folder_id
            btn_drive = ctk.CTkButton(
                btn_frame, text="📁", width=30, fg_color="#4285f4",
                command=lambda fid=drive_fid: self._open_drive_folder(fid)
            )
            btn_drive.pack(side="left", padx=2)
            add_tooltip(btn_drive, "Open Google Drive folder")

        # Re-title button (for Telegram tasks — re-fetches full titles)
        source_url = getattr(task, 'source_url', '')
        if 't.me' in source_url and getattr(task, 'export_to_sheets', False):
            btn_retitle = ctk.CTkButton(
                btn_frame, text="✏️", width=30, fg_color="#fd7e14",
                command=lambda t=task: self._retitle_task(t.id)
            )
            btn_retitle.pack(side="left", padx=2)
            add_tooltip(btn_retitle, "Re-title: Re-fetch all posts and fix truncated titles in the sheet")

        # Re-enrich button (only if task has Grid enrichment enabled)
        if getattr(task, 'enrich_with_grid', False):
            btn_reenrich = ctk.CTkButton(
                btn_frame, text="🔄", width=30, fg_color="#6f42c1",
                command=lambda t=task: self._reenrich_task(t.id)
            )
            btn_reenrich.pack(side="left", padx=2)
            add_tooltip(btn_reenrich, "Re-enrich: Run Grid matching on rows missing enrichment data")

        btn_edit = ctk.CTkButton(
            btn_frame, text="✎", width=30, fg_color="gray",
            command=lambda t=task: self._open_task_editor(t.id)
        )
        btn_edit.pack(side="left", padx=2)
        add_tooltip(btn_edit, "Edit task settings")

        btn_delete = ctk.CTkButton(
            btn_frame, text="✕", width=30, fg_color="#dc3545",
            command=lambda t=task: self._delete_task(t.id)
        )
        btn_delete.pack(side="left", padx=2)
        add_tooltip(btn_delete, "Delete this task")

    def _open_sheet(self, spreadsheet_id: str, sheet_name: str = ''):
        """Open the associated Google Sheet in the default browser."""
        import webbrowser
        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        if sheet_name:
            import urllib.parse
            url += f"/edit#gid=0"  # Default to first tab; gid varies but this opens the sheet
        else:
            url += "/edit"
        webbrowser.open(url)

    def _open_drive_folder(self, folder_id: str):
        """Open a Google Drive folder in the default browser."""
        import webbrowser
        try:
            from drive_manager import extract_folder_id_from_url
            clean_id = extract_folder_id_from_url(folder_id)
        except Exception:
            clean_id = folder_id
        webbrowser.open(f"https://drive.google.com/drive/folders/{clean_id}")

    def _toggle_task_enabled(self, task_id: str, enabled: bool):
        """Toggle a task's enabled state."""
        scheduler = self._get_active_scheduler()
        if scheduler:
            scheduler.update_task(task_id, {"enabled": enabled})
            self._refresh_scheduler_tasks()

    def _run_task_now(self, task_id: str):
        """Run a task immediately with visual feedback on Scheduler page."""
        scheduler = self._get_active_scheduler()
        if scheduler:
            task = scheduler.get_task(task_id)
            if task:
                # Clear previous log and show running status
                self._clear_task_log()
                self._show_scheduler_status(f"⏳ Running: {task.name}...", "orange")
                # Auto-expand the log so user sees progress
                if not self._task_log_expanded:
                    self._toggle_task_log()
                # Start animated progress indicator
                self._task_running_id = task_id
                self._animate_task_status(task.name, 0)
                scheduler.run_task_now(task_id)

    def _backfill_task(self, task_id: str):
        """Open the backfill dialog for a task, then run backfill with selected options."""
        scheduler = self._get_active_scheduler()
        if not scheduler:
            return

        task = scheduler.get_task(task_id)
        if not task:
            return

        # Build backfill options dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Backfill: {task.name}")
        dialog.geometry("480x420")
        dialog.transient(self)
        dialog.grab_set()
        dialog.lift()
        dialog.attributes("-topmost", True)
        dialog.after(100, lambda: dialog.attributes("-topmost", False))

        # Header
        ctk.CTkLabel(
            dialog, text=f"Backfill: {task.name}",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=20, pady=(16, 4))

        ctk.CTkLabel(
            dialog, text="Choose how far back to fetch historical data.",
            font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"]
        ).pack(padx=20, pady=(0, 12))

        # Date range options
        range_var = ctk.StringVar(value="auto")

        options_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        options_frame.pack(fill="x", padx=20, pady=(0, 8))

        range_options = [
            ("auto", "Auto-detect", "Finds gaps since earliest entry in sheet"),
            ("7d", "Last 7 days", "Quick fill of the past week"),
            ("30d", "Last 30 days", "Fill the past month"),
            ("90d", "Last 90 days", "Fill the past 3 months"),
            ("all", "Since beginning", "Fetch the entire archive — may be slow"),
            ("custom", "Custom date", "Pick a specific start date"),
        ]

        for value, label, desc in range_options:
            row = ctk.CTkFrame(options_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            rb = ctk.CTkRadioButton(
                row, text=label, variable=range_var, value=value,
                font=ctk.CTkFont(size=13)
            )
            rb.pack(side="left")
            ctk.CTkLabel(
                row, text=f"  — {desc}",
                font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]
            ).pack(side="left")

        # Custom date entry (shown only when "custom" is selected)
        custom_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        custom_frame.pack(fill="x", padx=40, pady=(0, 8))

        ctk.CTkLabel(custom_frame, text="Start date (YYYY-MM-DD):",
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        custom_date_entry = ctk.CTkEntry(custom_frame, width=140,
                                          placeholder_text="2025-01-01")
        custom_date_entry.pack(side="left")

        def _on_range_change(*args):
            if range_var.get() == "custom":
                custom_frame.pack(fill="x", padx=40, pady=(0, 8))
            else:
                custom_frame.pack_forget()
        range_var.trace_add("write", _on_range_change)
        custom_frame.pack_forget()  # Hidden initially

        # Warning banner for potentially long operations
        warning_frame = ctk.CTkFrame(dialog, fg_color="#fff3cd", corner_radius=8)
        warning_label = ctk.CTkLabel(
            warning_frame, text="",
            font=ctk.CTkFont(size=11), text_color="#856404",
            wraplength=400, justify="left"
        )
        warning_label.pack(padx=12, pady=8)

        def _update_warning(*args):
            val = range_var.get()
            if val == "all":
                warning_frame.pack(fill="x", padx=20, pady=(0, 8))
                warning_label.configure(
                    text="⚠️ Fetching the entire archive can take a long time and "
                         "use significant API credits. Large YouTube channel archives "
                         "may time out or hit rate limits. Consider using a shorter "
                         "range if possible."
                )
            elif val in ("90d", "custom"):
                warning_frame.pack(fill="x", padx=20, pady=(0, 8))
                warning_label.configure(
                    text="⚠️ Larger date ranges may take several minutes and use "
                         "more API credits. You can stop the backfill at any time."
                )
            else:
                warning_frame.pack_forget()
        range_var.trace_add("write", _update_warning)
        warning_frame.pack_forget()  # Hidden initially

        # Action buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(8, 16))

        def _start_backfill():
            import datetime as dt_mod
            val = range_var.get()
            since = None  # None = auto-detect from sheet

            if val == "7d":
                since = (dt_mod.date.today() - dt_mod.timedelta(days=7)).isoformat()
            elif val == "30d":
                since = (dt_mod.date.today() - dt_mod.timedelta(days=30)).isoformat()
            elif val == "90d":
                since = (dt_mod.date.today() - dt_mod.timedelta(days=90)).isoformat()
            elif val == "all":
                since = ""  # Empty string = full archive
            elif val == "custom":
                since = custom_date_entry.get().strip()
                if not since:
                    custom_date_entry.configure(border_color="red")
                    return
                # Validate date format
                try:
                    dt_mod.date.fromisoformat(since)
                except ValueError:
                    custom_date_entry.configure(border_color="red")
                    return

            dialog.destroy()
            self._execute_backfill(task_id, since_date=since)

        ctk.CTkButton(
            btn_frame, text="Start Backfill", fg_color=COLORS["accent"],
            hover_color="#2563eb", width=140,
            command=_start_backfill
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_frame, text="Cancel", fg_color="gray", width=100,
            command=dialog.destroy
        ).pack(side="right")

    def _execute_backfill(self, task_id: str, since_date=None):
        """Run the backfill with the selected date range."""
        scheduler = self._get_active_scheduler()
        if not scheduler:
            return

        task = scheduler.get_task(task_id)
        if not task:
            return

        # Clear previous log and show running status
        self._clear_task_log()
        self._show_scheduler_status(f"⏪ Backfilling: {task.name}...", "#0d6efd")
        # Auto-expand the log so user sees progress
        if not self._task_log_expanded:
            self._toggle_task_log()

        # Stop flag — set to True to cancel mid-backfill
        self._backfill_stop = False

        # Show stop button
        if hasattr(self, '_task_log_stop'):
            self._task_log_stop.grid(row=0, column=2, sticky="e", padx=(4, 0))

        # Start animated progress indicator
        self._task_running_id = task_id
        self._animate_task_status(task.name, 0, prefix="⏪ Backfilling")

        scheduler.backfill_task(task_id, stop_flag=lambda: self._backfill_stop,
                                since_date=since_date)

    def _stop_backfill(self):
        """Signal the running backfill to stop."""
        self._backfill_stop = True
        self._append_task_log("[Backfill] Stop requested — finishing current post...")

    def _reenrich_task(self, task_id: str):
        """Re-enrich existing sheet rows with Grid data."""
        scheduler = self._get_active_scheduler()
        if not scheduler:
            return

        task = scheduler.get_task(task_id)
        if not task:
            return

        # Clear previous log and show running status
        self._clear_task_log()
        self._show_scheduler_status(f"🔄 Re-enriching: {task.name}...", "#6f42c1")
        # Auto-expand the log so user sees progress
        if not self._task_log_expanded:
            self._toggle_task_log()

        # Stop flag
        self._backfill_stop = False

        # Show stop button
        if hasattr(self, '_task_log_stop'):
            self._task_log_stop.grid(row=0, column=2, sticky="e", padx=(4, 0))

        # Start animated progress indicator
        self._task_running_id = task_id
        self._animate_task_status(task.name, 0, prefix="🔄 Re-enriching")

        scheduler.reenrich_task(task_id, stop_flag=lambda: self._backfill_stop)

    def _retitle_task(self, task_id: str):
        """Re-fetch source posts and update truncated titles in the sheet."""
        scheduler = self._get_active_scheduler()
        if not scheduler:
            return

        task = scheduler.get_task(task_id)
        if not task:
            return

        # Clear previous log and show running status
        self._clear_task_log()
        self._show_scheduler_status(f"✏️ Re-titling: {task.name}...", "#fd7e14")
        if not self._task_log_expanded:
            self._toggle_task_log()

        self._backfill_stop = False

        if hasattr(self, '_task_log_stop'):
            self._task_log_stop.grid(row=0, column=2, sticky="e", padx=(4, 0))

        self._task_running_id = task_id
        self._animate_task_status(task.name, 0, prefix="✏️ Re-titling")

        scheduler.retitle_task(task_id, stop_flag=lambda: self._backfill_stop)

    def _build_task_log_panel(self):
        """Build the collapsible task execution log panel on the Scheduler page."""
        # Container frame for the log section
        self._task_log_frame = ctk.CTkFrame(self.scheduler_content, fg_color="transparent")
        self._task_log_frame.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        self._task_log_frame.grid_columnconfigure(0, weight=1)

        # Header row: status label + toggle button
        log_header = ctk.CTkFrame(self._task_log_frame, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=20)
        log_header.grid_columnconfigure(0, weight=1)

        # Status label (⏳ Running / ✅ Done / ❌ Error)
        self._scheduler_run_status = ctk.CTkLabel(
            log_header,
            text="",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        self._scheduler_run_status.grid(row=0, column=0, sticky="w")

        # Toggle button for expanding/collapsing the log
        self._task_log_expanded = False
        self._task_log_toggle = ctk.CTkButton(
            log_header,
            text="▶ Log",
            width=60,
            height=22,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=COLORS.get("bg_tertiary", "gray30"),
            text_color="gray",
            command=self._toggle_task_log
        )
        self._task_log_toggle.grid(row=0, column=1, sticky="e")

        # Stop button (hidden by default, shown during backfill)
        self._task_log_stop = ctk.CTkButton(
            log_header,
            text="Stop",
            width=50,
            height=22,
            font=ctk.CTkFont(size=11),
            fg_color="#dc3545",
            hover_color="#a71d2a",
            text_color="white",
            command=self._stop_backfill
        )
        # Don't grid yet — only shown during backfill (uses column 2)

        # Copy button
        self._task_log_copy = ctk.CTkButton(
            log_header,
            text="Copy",
            width=50,
            height=22,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=COLORS.get("bg_tertiary", "gray30"),
            text_color="gray",
            command=self._copy_task_log
        )
        self._task_log_copy.grid(row=0, column=3, sticky="e", padx=(4, 0))

        # Clear button
        self._task_log_clear = ctk.CTkButton(
            log_header,
            text="Clear",
            width=50,
            height=22,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=COLORS.get("bg_tertiary", "gray30"),
            text_color="gray",
            command=self._clear_task_log
        )
        self._task_log_clear.grid(row=0, column=4, sticky="e", padx=(4, 0))

        # Collapsible log textbox (hidden by default)
        self._task_log_textbox = ctk.CTkTextbox(
            self._task_log_frame,
            height=150,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=COLORS.get("bg_tertiary", "gray20"),
            text_color=COLORS.get("text_secondary", "gray70"),
            corner_radius=6,
            wrap="word",
            state="disabled"
        )
        # Don't grid it yet — collapsed by default

        # Internal log lines buffer
        self._task_log_lines = []

        # Initially hide the whole frame until a task starts
        self._task_log_frame.grid_remove()

    def _toggle_task_log(self):
        """Toggle the log textbox visibility."""
        self._task_log_expanded = not self._task_log_expanded
        if self._task_log_expanded:
            self._task_log_textbox.grid(row=1, column=0, sticky="ew", padx=20, pady=(4, 4))
            self._task_log_toggle.configure(text="▼ Log")
        else:
            self._task_log_textbox.grid_remove()
            self._task_log_toggle.configure(text="▶ Log")

    def _append_task_log(self, message: str):
        """Append a line to the task execution log (thread-safe via after())."""
        self._task_log_lines.append(message)
        # Trim buffer to prevent memory leak
        if len(self._task_log_lines) > 200:
            self._task_log_lines = self._task_log_lines[-200:]

        # Update textbox on main thread
        def _update():
            if not hasattr(self, '_task_log_textbox'):
                return
            self._task_log_textbox.configure(state="normal")
            self._task_log_textbox.insert("end", message + "\n")
            self._task_log_textbox.see("end")  # Auto-scroll to bottom
            self._task_log_textbox.configure(state="disabled")
        self.after(0, _update)

    def _copy_task_log(self):
        """Copy the task execution log to clipboard."""
        text = "\n".join(self._task_log_lines)
        if text.strip():
            self.clipboard_clear()
            self.clipboard_append(text)
            # Brief visual feedback on the button
            self._task_log_copy.configure(text="Copied!")
            self.after(1500, lambda: self._task_log_copy.configure(text="Copy"))

    def _clear_task_log(self):
        """Clear the task execution log."""
        self._task_log_lines.clear()
        if hasattr(self, '_task_log_textbox'):
            self._task_log_textbox.configure(state="normal")
            self._task_log_textbox.delete("1.0", "end")
            self._task_log_textbox.configure(state="disabled")

    def _on_scheduler_progress(self, task_id: str, message: str):
        """Callback from scheduler with progress log lines. Called from background thread."""
        self._append_task_log(message)

    def _show_scheduler_status(self, text: str, color: str = "gray"):
        """Show a status message on the Scheduler page."""
        # Make sure the log panel is visible
        if hasattr(self, '_task_log_frame'):
            self._task_log_frame.grid()
        self._scheduler_run_status.configure(text=text, text_color=color)

    def _animate_task_status(self, task_name: str, dots: int, prefix: str = "⏳ Running"):
        """Animate the running status with dots to show it's alive."""
        if self._task_running_id is None:
            return
        dot_str = "." * (dots % 4)
        color = "#0d6efd" if "Backfill" in prefix else "orange"
        self._show_scheduler_status(f"{prefix}: {task_name}{dot_str}", color)
        self.after(600, lambda: self._animate_task_status(task_name, dots + 1, prefix))

    def _delete_task(self, task_id: str):
        """Delete a scheduled task."""
        scheduler = self._get_active_scheduler()
        if scheduler:
            task = scheduler.get_task(task_id)
            if task:
                # Confirm deletion
                if scheduler.delete_task(task_id):
                    self.label_status.configure(text=f"Deleted task: {task.name}", text_color="gray")
                    self._refresh_scheduler_tasks()

    def _open_task_editor(self, task_id: str = None):
        """Open the task editor dialog."""
        from scheduler import ScheduledTask

        # Get existing task or create new
        task = None
        if task_id and self._scheduler:
            task = self._scheduler.get_task(task_id)

        is_new = task is None
        if is_new:
            task = ScheduledTask(id="", name="New Task")

        # Create dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Scheduled Task" if not is_new else "Add Scheduled Task")
        dialog.geometry("550x750")
        dialog.minsize(500, 700)
        dialog.transient(self)
        dialog.grab_set()

        # Main scrollable frame
        main_frame = ctk.CTkScrollableFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        main_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Task Name
        ctk.CTkLabel(main_frame, text="Task Name:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1
        name_entry = ctk.CTkEntry(main_frame, width=400)
        name_entry.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        name_entry.insert(0, task.name)
        row += 1

        # Task Type Selector
        ctk.CTkLabel(main_frame, text="Task Type:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1
        type_var = ctk.StringVar(value="Audio Briefing" if task.task_type == "briefing_pipeline" else "Data Extraction")
        type_selector = ctk.CTkSegmentedButton(
            main_frame, values=["Data Extraction", "Audio Briefing"],
            variable=type_var, width=350
        )
        type_selector.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 15))
        row += 1

        # --- Extraction-specific fields frame ---
        extraction_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        extraction_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        extraction_frame.grid_columnconfigure(1, weight=1)
        extraction_row_idx = row
        row += 1

        # --- Pipeline-specific fields frame ---
        pipeline_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        pipeline_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        pipeline_frame.grid_columnconfigure(1, weight=1)
        pipeline_row_idx = row
        row += 1

        # ========== PIPELINE FIELDS ==========
        p_row = 0

        # Audio Quality
        ctk.CTkLabel(pipeline_frame, text="Audio Quality:", font=ctk.CTkFont(weight="bold")).grid(row=p_row, column=0, sticky="w", pady=(0, 5))
        p_row += 1

        audio_quality_var = ctk.StringVar(value=task.audio_quality)
        quality_frame = ctk.CTkFrame(pipeline_frame, fg_color="transparent")
        quality_frame.grid(row=p_row, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ctk.CTkRadioButton(quality_frame, text="Fast (gTTS)", variable=audio_quality_var, value="fast").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(quality_frame, text="Quality (Kokoro)", variable=audio_quality_var, value="quality").pack(side="left")
        p_row += 1

        # Voice Selector (only for quality)
        voice_label = ctk.CTkLabel(pipeline_frame, text="Voice:", font=ctk.CTkFont(weight="bold"))
        voice_label.grid(row=p_row, column=0, sticky="w", pady=(0, 5))
        p_row += 1

        KOKORO_VOICES = [
            "af_heart", "af_sarah", "af_nova", "af_sky", "af_bella",
            "am_adam", "am_michael", "am_echo",
            "bf_emma", "bf_isabella",
            "bm_george", "bm_lewis",
        ]
        voice_var = ctk.StringVar(value=task.audio_voice if task.audio_voice in KOKORO_VOICES else "af_heart")
        voice_combo = ctk.CTkComboBox(pipeline_frame, variable=voice_var, values=KOKORO_VOICES, width=180, state="readonly")
        voice_combo.grid(row=p_row, column=0, columnspan=2, sticky="w", pady=(0, 15))
        p_row += 1

        def _on_audio_quality_change(*args):
            if audio_quality_var.get() == "quality":
                voice_label.grid()
                voice_combo.grid()
            else:
                voice_label.grid_remove()
                voice_combo.grid_remove()
        audio_quality_var.trace_add("write", _on_audio_quality_change)
        _on_audio_quality_change()  # Apply initial state

        # Source Filter
        ctk.CTkLabel(pipeline_frame, text="Sources:", font=ctk.CTkFont(weight="bold")).grid(row=p_row, column=0, sticky="w", pady=(0, 5))
        p_row += 1

        use_all_sources_var = ctk.BooleanVar(value=task.source_filter is None)
        ctk.CTkCheckBox(pipeline_frame, text="Use all enabled sources", variable=use_all_sources_var).grid(row=p_row, column=0, columnspan=2, sticky="w", pady=(0, 5))
        p_row += 1

        # Source checkboxes (loaded from sources.json)
        source_filter_frame = ctk.CTkFrame(pipeline_frame, fg_color="transparent")
        source_filter_frame.grid(row=p_row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        p_row += 1

        source_check_vars = {}
        try:
            from source_fetcher import load_sources as _load_sources
            data_dir = os.path.dirname(os.path.abspath(__file__))
            if getattr(sys, "frozen", False):
                if sys.platform == "darwin":
                    data_dir = os.path.expanduser("~/Library/Application Support/Daily Audio Briefing")
                elif sys.platform == "win32":
                    data_dir = os.path.join(os.environ.get("APPDATA", ""), "Daily Audio Briefing")
                else:
                    data_dir = os.path.expanduser("~/.daily-audio-briefing")

            _sj = os.path.join(data_dir, "sources.json")
            _ct = os.path.join(data_dir, "channels.txt")
            if not os.path.exists(_sj):
                _sj = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources.json")
                if getattr(sys, "frozen", False):
                    _sj = os.path.join(sys._MEIPASS, "sources.json")
            if not os.path.exists(_ct):
                _ct = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channels.txt")

            all_sources = _load_sources(_sj, _ct)
            filter_set = set(task.source_filter) if task.source_filter else set()

            for s_idx, src in enumerate(all_sources):
                var = ctk.BooleanVar(value=(task.source_filter is None or src.name in filter_set))
                source_check_vars[src.name] = var
                ctk.CTkCheckBox(source_filter_frame, text=src.name, variable=var, font=("Arial", 11)).grid(
                    row=s_idx // 2, column=s_idx % 2, sticky="w", padx=5, pady=2
                )
        except Exception:
            ctk.CTkLabel(source_filter_frame, text="Could not load sources", text_color="gray").grid(row=0, column=0)

        def _on_all_sources_change(*args):
            if use_all_sources_var.get():
                source_filter_frame.grid_remove()
            else:
                source_filter_frame.grid()
        use_all_sources_var.trace_add("write", _on_all_sources_change)
        _on_all_sources_change()  # Apply initial state

        # Drive Upload
        ctk.CTkLabel(pipeline_frame, text="Google Drive Upload:", font=ctk.CTkFont(weight="bold")).grid(row=p_row, column=0, sticky="w", pady=(5, 5))
        p_row += 1

        drive_upload_var = ctk.BooleanVar(value=task.upload_to_drive)
        ctk.CTkCheckBox(pipeline_frame, text="Upload audio to Google Drive", variable=drive_upload_var).grid(row=p_row, column=0, columnspan=2, sticky="w", pady=(0, 5))
        p_row += 1

        ctk.CTkLabel(pipeline_frame, text="Drive Folder ID or URL:").grid(row=p_row, column=0, sticky="w", pady=(0, 5))
        p_row += 1

        # Drive folder entry with pre-fill from Settings
        drive_folder_row = ctk.CTkFrame(pipeline_frame, fg_color="transparent")
        drive_folder_row.grid(row=p_row, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        drive_folder_row.grid_columnconfigure(0, weight=1)

        drive_folder_entry = ctk.CTkEntry(drive_folder_row, placeholder_text="https://drive.google.com/drive/folders/... or folder ID")
        drive_folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        drive_folder_entry.insert(0, task.drive_folder_id)

        # Show "Use from Settings" button if Settings has a folder configured and task field is empty
        settings_folder = self.settings.get("drive_folder_id", "")
        if settings_folder and not task.drive_folder_id:
            def _use_settings_folder(entry=drive_folder_entry, fid=settings_folder, btn_ref=[None]):
                entry.delete(0, "end")
                entry.insert(0, fid)
                if btn_ref[0]:
                    btn_ref[0].grid_remove()
            use_btn = ctk.CTkButton(
                drive_folder_row, text="Use from Settings", width=130,
                fg_color=COLORS["accent"], hover_color="#2563eb",
                font=ctk.CTkFont(size=11),
                command=_use_settings_folder
            )
            use_btn.grid(row=0, column=1)
            _use_settings_folder.__defaults__ = (drive_folder_entry, settings_folder, [use_btn])
        elif settings_folder and task.drive_folder_id == settings_folder:
            # Already using Settings folder — show subtle indicator
            ctk.CTkLabel(
                drive_folder_row, text="(from Settings)",
                font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]
            ).grid(row=0, column=1, padx=(0, 4))
        p_row += 1

        # ========== EXTRACTION FIELDS (moved into extraction_frame) ==========
        e_row = 0

        # Source URL
        ctk.CTkLabel(extraction_frame, text="Source URL:", font=ctk.CTkFont(weight="bold")).grid(row=e_row, column=0, sticky="w", pady=(0, 5))
        e_row += 1
        ctk.CTkLabel(extraction_frame, text="Telegram channel, newsletter, RSS feed, or article archive URL", font=("Arial", 10), text_color="gray").grid(row=e_row, column=0, columnspan=2, sticky="w")
        e_row += 1
        source_entry = ctk.CTkEntry(extraction_frame, width=400, placeholder_text="https://t.me/s/YourChannel or https://newsletter.example.com/archive")
        source_entry.grid(row=e_row, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        source_entry.insert(0, task.source_url)
        e_row += 1

        # Extraction Config
        ctk.CTkLabel(extraction_frame, text="Extraction Config:", font=ctk.CTkFont(weight="bold")).grid(row=e_row, column=0, sticky="w", pady=(0, 5))
        e_row += 1
        config_var = ctk.StringVar(value=task.config_name)
        config_values = self._get_extraction_configs()
        config_combo = ctk.CTkComboBox(extraction_frame, variable=config_var, values=config_values, width=200, state="readonly")
        config_combo.grid(row=e_row, column=0, columnspan=2, sticky="w", pady=(0, 15))
        e_row += 1

        # ========== SHARED FIELDS (Schedule) — back in main_frame ==========

        # Schedule Section
        ctk.CTkLabel(main_frame, text="Schedule:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1

        schedule_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        schedule_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        row += 1

        interval_var = ctk.StringVar(value=task.interval)
        intervals = [
            ("Hourly", "hourly"),
            ("Every 6 Hours", "every_6_hours"),
            ("Every 12 Hours", "every_12_hours"),
            ("Daily", "daily"),
            ("Weekly", "weekly"),
        ]

        for i, (label, value) in enumerate(intervals):
            ctk.CTkRadioButton(schedule_frame, text=label, variable=interval_var, value=value).grid(row=i // 3, column=i % 3, sticky="w", padx=10, pady=3)

        # Time picker (for daily/weekly)
        time_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        time_frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 15))
        row += 1

        ctk.CTkLabel(time_frame, text="Run at:").pack(side="left", padx=(0, 5))
        time_entry = ctk.CTkEntry(time_frame, width=70, placeholder_text="09:00")
        time_entry.pack(side="left", padx=(0, 10))
        time_entry.insert(0, task.run_at_time)

        ctk.CTkLabel(time_frame, text="(HH:MM, 24-hour format)", font=("Arial", 10), text_color="gray").pack(side="left")

        # Google Sheets Export Section (extraction only)
        ctk.CTkLabel(extraction_frame, text="Google Sheets Export:", font=ctk.CTkFont(weight="bold")).grid(row=e_row, column=0, sticky="w", pady=(10, 5))
        e_row += 1

        sheets_var = ctk.BooleanVar(value=task.export_to_sheets)
        sheets_check = ctk.CTkCheckBox(extraction_frame, text="Export to Google Sheets", variable=sheets_var)
        sheets_check.grid(row=e_row, column=0, columnspan=2, sticky="w", pady=(0, 10))
        e_row += 1

        ctk.CTkLabel(extraction_frame, text="Spreadsheet ID or URL:").grid(row=e_row, column=0, sticky="w", pady=(0, 5))
        e_row += 1
        sheet_id_entry = ctk.CTkEntry(extraction_frame, width=400, placeholder_text="https://docs.google.com/spreadsheets/d/... or just the ID")
        sheet_id_entry.grid(row=e_row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        sheet_id_entry.insert(0, task.spreadsheet_id)
        e_row += 1

        ctk.CTkLabel(extraction_frame, text="Sheet Tab Name:").grid(row=e_row, column=0, sticky="w", pady=(0, 5))
        e_row += 1
        sheet_name_entry = ctk.CTkEntry(extraction_frame, width=200, placeholder_text="Sheet1")
        sheet_name_entry.grid(row=e_row, column=0, sticky="w", pady=(0, 10))
        sheet_name_entry.insert(0, task.sheet_name)
        e_row += 1

        headers_var = ctk.BooleanVar(value=task.include_headers)
        headers_check = ctk.CTkCheckBox(extraction_frame, text="Include headers (only needed once for new sheets)", variable=headers_var)
        headers_check.grid(row=e_row, column=0, columnspan=2, sticky="w", pady=(0, 10))
        e_row += 1

        # Column Headers Editor
        ctk.CTkLabel(extraction_frame, text="Column Headers:", font=ctk.CTkFont(weight="bold")).grid(row=e_row, column=0, sticky="w", pady=(5, 3))
        e_row += 1

        col_desc = ctk.CTkLabel(extraction_frame, text="Comma-separated list. Leave blank to use config default.", font=("Arial", 10), text_color="gray")
        col_desc.grid(row=e_row, column=0, columnspan=2, sticky="w")
        e_row += 1

        # Populate with: task custom_columns > config csv_columns > empty
        initial_columns = ""
        if task.custom_columns:
            initial_columns = ", ".join(task.custom_columns)
        elif task.config_name and task.config_name != "Default":
            try:
                import json as _json
                _cfg_file = task.config_name.lower().replace(" ", "_") + ".json"
                _cfg_path = os.path.join(os.path.dirname(__file__), "extraction_instructions", _cfg_file)
                if getattr(sys, 'frozen', False):
                    _cfg_path = os.path.join(sys._MEIPASS, "extraction_instructions", _cfg_file)
                if os.path.exists(_cfg_path):
                    with open(_cfg_path) as _f:
                        _cfg_data = _json.load(_f)
                    _default_cols = _cfg_data.get("csv_columns", [])
                    if _default_cols:
                        initial_columns = ", ".join(_default_cols)
            except Exception:
                pass

        columns_entry = ctk.CTkEntry(extraction_frame, width=400, placeholder_text="url, description, source_name, date_published, comments")
        columns_entry.grid(row=e_row, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        if initial_columns:
            columns_entry.insert(0, initial_columns)
        e_row += 1

        # Auto-detect + format info row
        detect_frame = ctk.CTkFrame(extraction_frame, fg_color="transparent")
        detect_frame.grid(row=e_row, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        detect_frame.grid_columnconfigure(1, weight=1)

        detect_status = ctk.CTkLabel(detect_frame, text="", font=("Arial", 10), text_color="gray")
        detect_status.grid(row=0, column=1, sticky="w", padx=(8, 0))

        def _auto_detect_columns():
            """Read headers from the actual Google Sheet."""
            sid = sheet_id_entry.get().strip()
            sname = sheet_name_entry.get().strip() or "Sheet1"
            if not sid:
                detect_status.configure(text="Enter a Spreadsheet ID first", text_color="orange")
                return
            # Extract ID from URL if needed
            if '/spreadsheets/d/' in sid:
                try:
                    from sheets_manager import extract_sheet_id
                    sid = extract_sheet_id(sid)
                except Exception:
                    pass

            detect_status.configure(text="Reading sheet...", text_color="gray")
            dialog.update_idletasks()

            def _do_detect():
                try:
                    from sheets_manager import get_sheet_headers_with_format, is_sheets_available
                    if not is_sheets_available():
                        return None, "Sheets not configured (no credentials)"
                    cols = get_sheet_headers_with_format(sid, sname)
                    return cols, None
                except Exception as e:
                    return None, str(e)[:80]

            def _apply_result(cols, err):
                if err:
                    detect_status.configure(text=f"Error: {err}", text_color="red")
                    return
                if not cols:
                    detect_status.configure(text="No headers found in sheet", text_color="orange")
                    return
                # Build display string and format info
                names = [c["name"] for c in cols]
                format_parts = []
                for c in cols:
                    if c["format"] == "checkbox":
                        format_parts.append(f'{c["name"]} [checkbox]')
                    else:
                        format_parts.append(c["name"])

                columns_entry.delete(0, "end")
                columns_entry.insert(0, ", ".join(names))
                detect_status.configure(
                    text=f"Detected {len(cols)} columns: " + ", ".join(format_parts),
                    text_color="green"
                )

            import threading
            def _thread():
                cols, err = _do_detect()
                dialog.after(0, lambda: _apply_result(cols, err))
            threading.Thread(target=_thread, daemon=True).start()

        detect_btn = ctk.CTkButton(detect_frame, text="Auto-detect from Sheet", width=160, height=26,
                                   font=ctk.CTkFont(size=11), fg_color=COLORS.get("accent", "#3B82F6"),
                                   command=_auto_detect_columns)
        detect_btn.grid(row=0, column=0, sticky="w")

        e_row += 1

        # Capabilities Section
        ctk.CTkLabel(extraction_frame, text="Capabilities:", font=ctk.CTkFont(weight="bold")).grid(row=e_row, column=0, sticky="w", pady=(10, 5))
        e_row += 1

        grid_enrich_var = ctk.BooleanVar(value=task.enrich_with_grid)
        grid_enrich_check = ctk.CTkCheckBox(extraction_frame, text="Enrich with Grid (match entities against The Grid database)", variable=grid_enrich_var)
        grid_enrich_check.grid(row=e_row, column=0, columnspan=2, sticky="w", pady=(0, 5))
        e_row += 1

        research_var = ctk.BooleanVar(value=task.research_articles)
        research_check = ctk.CTkCheckBox(extraction_frame, text="Research Articles (find ecosystem mentions in articles)", variable=research_var)
        research_check.grid(row=e_row, column=0, columnspan=2, sticky="w", pady=(0, 5))
        e_row += 1

        ctk.CTkLabel(extraction_frame, text="These use free APIs — no Gemini costs.", font=("Arial", 10), text_color="gray").grid(row=e_row, column=0, columnspan=2, sticky="w", pady=(0, 15))
        e_row += 1

        # Enable/disable capabilities based on config selection
        def on_config_change(choice):
            disabled_configs = ["default", "execsum"]
            if choice.lower() in disabled_configs:
                grid_enrich_var.set(False)
                research_var.set(False)
                grid_enrich_check.configure(state="disabled")
                research_check.configure(state="disabled")
            else:
                grid_enrich_check.configure(state="normal")
                research_check.configure(state="normal")

        config_combo.configure(command=on_config_change)
        # Apply initial state
        on_config_change(config_var.get())

        # --- Type toggle: show/hide extraction vs pipeline fields ---
        def _on_type_change(*args):
            selected = type_var.get()
            if selected == "Audio Briefing":
                extraction_frame.grid_remove()
                pipeline_frame.grid()
            else:
                pipeline_frame.grid_remove()
                extraction_frame.grid()
        type_selector.configure(command=lambda val: _on_type_change())
        _on_type_change()  # Apply initial state

        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=15)

        def save_task():
            # Gather common values
            new_name = name_entry.get().strip() or "Untitled Task"
            new_interval = interval_var.get()
            new_time = time_entry.get().strip() or "09:00"

            # Determine task type
            new_task_type = "briefing_pipeline" if type_var.get() == "Audio Briefing" else "extraction"

            # Extraction-specific values
            new_source = source_entry.get().strip()
            new_config = config_var.get()
            new_sheets = sheets_var.get()
            new_sheet_id = sheet_id_entry.get().strip()
            new_sheet_name = sheet_name_entry.get().strip() or "Sheet1"
            new_headers = headers_var.get()

            # Extract sheet ID from URL if needed
            if new_sheet_id and '/spreadsheets/d/' in new_sheet_id:
                try:
                    from sheets_manager import extract_sheet_id
                    new_sheet_id = extract_sheet_id(new_sheet_id)
                except:
                    pass

            new_grid_enrich = grid_enrich_var.get()
            new_research = research_var.get()

            # Parse custom columns from comma-separated string
            cols_text = columns_entry.get().strip()
            new_custom_columns = None
            if cols_text:
                new_custom_columns = [c.strip() for c in cols_text.split(",") if c.strip()]

            # Pipeline-specific values
            new_audio_quality = audio_quality_var.get()
            new_audio_voice = voice_var.get()
            new_upload_to_drive = drive_upload_var.get()
            new_drive_folder_id = drive_folder_entry.get().strip()
            new_source_filter = None
            if not use_all_sources_var.get():
                new_source_filter = [name for name, var in source_check_vars.items() if var.get()]

            if is_new:
                new_task = ScheduledTask(
                    id="",
                    name=new_name,
                    enabled=True,
                    source_url=new_source,
                    config_name=new_config,
                    interval=new_interval,
                    run_at_time=new_time,
                    export_to_sheets=new_sheets,
                    spreadsheet_id=new_sheet_id,
                    sheet_name=new_sheet_name,
                    include_headers=new_headers,
                    enrich_with_grid=new_grid_enrich,
                    research_articles=new_research,
                    custom_columns=new_custom_columns,
                    task_type=new_task_type,
                    audio_quality=new_audio_quality,
                    audio_voice=new_audio_voice,
                    upload_to_drive=new_upload_to_drive,
                    drive_folder_id=new_drive_folder_id,
                    source_filter=new_source_filter,
                )
                self._get_active_scheduler().add_task(new_task)
                self.label_status.configure(text=f"Created task: {new_name}", text_color="green")
            else:
                self._get_active_scheduler().update_task(task.id, {
                    "name": new_name,
                    "source_url": new_source,
                    "config_name": new_config,
                    "interval": new_interval,
                    "run_at_time": new_time,
                    "export_to_sheets": new_sheets,
                    "spreadsheet_id": new_sheet_id,
                    "sheet_name": new_sheet_name,
                    "include_headers": new_headers,
                    "enrich_with_grid": new_grid_enrich,
                    "research_articles": new_research,
                    "custom_columns": new_custom_columns,
                    "task_type": new_task_type,
                    "audio_quality": new_audio_quality,
                    "audio_voice": new_audio_voice,
                    "upload_to_drive": new_upload_to_drive,
                    "drive_folder_id": new_drive_folder_id,
                    "source_filter": new_source_filter,
                })
                self.label_status.configure(text=f"Updated task: {new_name}", text_color="green")

            self._refresh_scheduler_tasks()
            dialog.destroy()

        ctk.CTkButton(btn_frame, text="Save", fg_color="green", width=100, command=save_task).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", width=100, command=dialog.destroy).pack(side="right", padx=5)

    def show_scheduler_guide(self):
        """Show the scheduler setup guide."""
        guide = ctk.CTkToplevel(self)
        guide.title("Scheduler Setup Guide")
        guide.geometry("700x600")
        guide.minsize(600, 500)
        guide.transient(self)
        guide.grab_set()

        # Header
        header = ctk.CTkFrame(guide, fg_color=("gray85", "gray25"))
        header.pack(fill="x")
        ctk.CTkLabel(header, text="📅 Scheduler Setup Guide", font=ctk.CTkFont(size=20, weight="bold"), pady=20).pack()

        # Content
        content = ctk.CTkScrollableFrame(guide)
        content.pack(fill="both", expand=True, padx=20, pady=10)

        guide_text = """
## How the Scheduler Works

The scheduler automatically extracts data from your configured sources and exports it to Google Sheets on a regular schedule.

---

## Quick Start

1. **Add a Task** — Click "+ Add Task" in the Scheduler section
2. **Set the Source URL** — Paste your newsletter archive, Telegram channel, or RSS feed URL
3. **Choose a Config** — Select an extraction config (e.g., CryptoSum, RWA, ExecSum)
4. **Set the Schedule** — Choose frequency and time (e.g., daily at 09:00)
5. **Enable Sheets Export** — Paste your Google Sheet URL and sheet tab name
6. **Save and Enable** — Toggle "Scheduler Active" to start

---

## Task Row Buttons

Each task in the list has action buttons:

- **▶ Run** — Execute the task immediately (one-time manual run)
- **⏪ Backfill** — Crawl the source archive and fill in all missing dates (see below)
- **📊 Sheet** — Open the associated Google Sheet in your browser (only shown if Sheets export is configured)
- **✏️ Re-title** — Re-fetch all posts from source and fix truncated titles in the sheet (Telegram tasks only)
- **🔄 Re-enrich** — Run Grid entity matching on rows that are missing enrichment data (only shown if Grid enrichment is enabled)
- **✎ Edit** — Open the task editor to change settings
- **✕ Delete** — Remove the task

---

## Backfill (Gap Detection)

The ⏪ button launches the backfill system, which automatically catches up your sheet by filling in missing dates.

**How it works:**
1. Reads all dates currently in your sheet
2. Crawls the source archive to find every published post
3. Identifies posts from dates NOT already in your sheet
4. Processes and exports them one at a time, oldest first
5. Applies Grid enrichment and article research if enabled

**Key features:**
- **Gap-aware** — Detects and fills gaps anywhere in the date range, not just after the last entry
- **Deduplication** — Skips posts whose URLs already exist in the sheet
- **Chunked processing** — One post at a time with pauses to avoid rate limits
- **Stoppable** — Click the red "Stop" button to halt after the current post finishes

Use backfill when you've fallen behind on updates or need to populate historical data.

---

## Advanced Capabilities

Tasks can optionally enable two advanced features (set in the task editor):

- **Grid Enrichment** — Cross-references extracted items against The Grid database for additional metadata (token info, asset details, etc.)
- **Research Articles** — Fetches full article content for items that mention ecosystem projects, adding deeper context to the extraction

These appear as capability badges (e.g., `[Grid + Research]`) on the task row.

---

## Task Log

The collapsible log panel below the task list shows real-time output from task runs and backfills.

- **Toggle** — Expand/collapse the log panel
- **Copy** — Copy the full log to your clipboard
- **Clear** — Clear the log contents
- **Stop** — Halt a running backfill (appears only during backfill)

---

## Supported Source Types

### Newsletter Archives (Beehiiv, Substack)
```
https://newsletter.example.com/archive
https://cryptosum.beehiiv.com
```
The scheduler fetches the latest posts. Backfill crawls paginated archives.

### Telegram Channels
```
https://t.me/YourChannel
https://t.me/s/YourChannel
```
Fetches recent messages and extracts article links.

### RSS Feeds
```
https://example.com/feed.xml
https://example.com/rss
```
Standard RSS/Atom feeds are supported.

---

## Google Sheets Setup

To export to Google Sheets, you need:

1. **Google Cloud Console Setup**
   - Go to console.cloud.google.com
   - Create a new project (or use existing)
   - Enable "Google Sheets API"

2. **Service Account**
   - Go to IAM & Admin → Service Accounts
   - Create a new service account
   - Download the JSON key file
   - Save it as `google_credentials.json` in the app folder

3. **Share Your Sheet**
   - Open your Google Sheet
   - Click "Share"
   - Add the service account email (found in the JSON file)
   - Give it "Editor" access

**Sheet Notes:** The system can read cell notes on column headers. Use column W for feedback notes (e.g., "Feedback for Bots") and column X for skip flags.

---

## Scheduler Modes

- **Local** — Runs on your machine while the app is open
- **Cloud** — Connects to a remote server that runs tasks 24/7 (requires server setup)

Switch modes using the segmented button at the top of the Scheduler page.

---

## Tips

- **Test First**: Use ▶ to run a task manually before relying on the schedule
- **Backfill First**: For new sheets, use ⏪ to populate historical data, then let the schedule maintain it
- **Headers**: Only check "Include headers" for new/empty sheets
- **Time Format**: Use 24-hour format (e.g., 09:00, 14:30, 22:00)
- **Keep Running**: The local scheduler only runs while the app is open

---

## Troubleshooting

**Task not running?**
- Make sure "Scheduler Active" is toggled ON
- Check that the task is enabled (checkbox checked)
- Verify the source URL is accessible

**Sheets export failing?**
- Confirm google_credentials.json exists in the app folder
- Make sure you shared the sheet with the service account email
- Check the sheet ID and tab name are correct

**Backfill finding 0 posts?**
- The archive may be empty or the source doesn't support pagination
- Check if the source URL points to a valid archive page

**0 rows exported after a run?**
- This usually means deduplication is working — all extracted items already exist in the sheet
- Check the log for "X items → 0 rows to Sheets" confirmation
"""

        # Render the guide text with basic markdown
        self._render_markdown(content, guide_text)

        # Close button
        btn_frame = ctk.CTkFrame(guide, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)
        ctk.CTkButton(btn_frame, text="Close", width=100, command=guide.destroy).pack()

    # ========== Unified Content Editor Methods ==========

    def _on_textbox_change(self, event=None):
        """Handle textbox content changes - detect URLs, update placeholder and banner."""
        try:
            # Only process when user is on a page with the textbox
            if self._current_page not in ("summarize", "audio"):
                return

            # Safety check - ensure widgets are initialized
            if not hasattr(self, 'inline_status_label') or not hasattr(self, 'url_banner_frame'):
                return

            text = self.textbox.get("0.0", "end-1c").strip()

            # Update placeholder visibility
            if hasattr(self, '_update_placeholder'):
                self._update_placeholder()

            if not text:
                self._set_url_banner_inactive()
                self.inline_status_label.configure(text="")
                self._current_config_urls = None
                return

            # Detect content type for URL banner
            detection = self._detect_content_type(text)

            if detection['total_urls'] > 0:
                # Check if any article URLs match extraction configs
                config_categorization = None
                if detection['article_urls']:
                    try:
                        config_categorization = self._categorize_urls_by_config(detection['article_urls'])
                        self._current_config_urls = config_categorization
                    except Exception as e:
                        print(f"[DEBUG] Error categorizing URLs: {e}")
                        config_categorization = None
                        self._current_config_urls = None
                else:
                    self._current_config_urls = None

                # Build description of detected URLs
                parts = []
                if detection['youtube_urls']:
                    count = len(detection['youtube_urls'])
                    parts.append(f"{count} YouTube video{'s' if count > 1 else ''}")

                # Check for config-matched URLs
                config_parts = []
                if config_categorization and config_categorization.get('config_urls'):
                    for config_name, config_data in config_categorization['config_urls'].items():
                        count = len(config_data['urls'])
                        config_parts.append(f"{count} {config_data['display_name']}")

                # Regular articles (non-config-matched)
                if config_categorization and config_categorization.get('regular_urls'):
                    count = len(config_categorization['regular_urls'])
                    parts.append(f"{count} article{'s' if count > 1 else ''}")
                elif detection['article_urls'] and not config_categorization:
                    count = len(detection['article_urls'])
                    parts.append(f"{count} article{'s' if count > 1 else ''}")

                # Combine parts
                all_parts = parts + config_parts
                banner_text = f"Detected: {' and '.join(all_parts)}" if all_parts else "URLs detected"

                # If there are config-matched URLs, add a note
                if config_parts:
                    self._set_url_banner_active_with_config(banner_text, config_categorization)
                else:
                    self._set_url_banner_active(banner_text)

                # Store detection for later use
                self._current_url_detection = detection
            else:
                self._set_url_banner_inactive()
                self._current_url_detection = None
                self._current_config_urls = None
        except Exception as e:
            print(f"[DEBUG] Error in _on_textbox_change: {e}")
            import traceback
            traceback.print_exc()

    def _set_url_banner_active(self, message: str):
        """Set URL banner to active state with detection message."""
        self._url_banner_active = True
        self.url_banner_frame.configure(fg_color=("#fef3c7", "#4a3f1f"))
        self.url_banner_label.configure(text=message, text_color=("gray10", "gray90"))
        self.btn_fetch_urls.configure(state="normal", fg_color="green")
        self.btn_ignore_urls.configure(state="normal", fg_color="gray50")
        # Keep Extract Data button visible but greyed (no config matches for this URL)
        if hasattr(self, 'btn_extract_data'):
            self.btn_extract_data.configure(state="disabled", fg_color="gray")

    def _set_url_banner_inactive(self, message: str = "Paste URLs to fetch article content or extract newsletter data"):
        """Set URL banner to inactive/greyed state with explainer text."""
        self._url_banner_active = False
        self.url_banner_frame.configure(fg_color=("gray85", "gray20"))
        self.url_banner_label.configure(text=message, text_color="gray")
        self.btn_fetch_urls.configure(state="disabled", fg_color="gray")
        self.btn_ignore_urls.configure(state="disabled", fg_color="gray")
        # Keep Extract Data button visible but greyed out (as explainer)
        if hasattr(self, 'btn_extract_data'):
            self.btn_extract_data.grid()
            self.btn_extract_data.configure(state="disabled", fg_color="gray")

    def _set_url_banner_active_with_config(self, message: str, config_categorization: dict):
        """Set URL banner to active state with config-matched URL options."""
        self._url_banner_active = True
        # Use a slightly different color to indicate config match (blue tint)
        self.url_banner_frame.configure(fg_color=("#dbeafe", "#1e3a5f"))
        self.url_banner_label.configure(text=message, text_color=("gray10", "gray90"))
        self.btn_fetch_urls.configure(state="normal", fg_color="green")
        self.btn_ignore_urls.configure(state="normal", fg_color="gray50")

        # Show and enable Extract Data button
        self.btn_extract_data.grid()
        self.btn_extract_data.configure(state="normal", fg_color="#3b82f6")  # Blue color

    def _extract_config_urls(self):
        """Extract data from config-matched URLs using Data Extractor logic."""
        if not hasattr(self, '_current_config_urls') or not self._current_config_urls:
            return

        config_urls = self._current_config_urls.get('config_urls', {})
        if not config_urls:
            self.inline_status_label.configure(
                text="No config-matched URLs to extract",
                text_color="orange"
            )
            return

        # Collect all URLs to process
        all_urls = []
        config_names = []
        for config_name, config_data in config_urls.items():
            all_urls.extend(config_data['urls'])
            config_names.append(config_data['display_name'])

        # Update banner to show processing
        self._set_url_banner_inactive(f"Extracting from {len(all_urls)} URL(s)...")
        self.label_status.configure(
            text=f"Extracting data using {', '.join(config_names)} config(s)...",
            text_color="orange"
        )

        def do_extraction():
            try:
                # Use the Data Extractor logic
                from data_csv_processor import DataCSVProcessor, ExtractionConfig

                all_results = []

                for config_name, config_data in config_urls.items():
                    urls = config_data['urls']

                    # Load the config
                    config_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        'extraction_instructions',
                        f'{config_name}.json'
                    )

                    if os.path.exists(config_path):
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config_dict = json.load(f)
                        config = ExtractionConfig.from_dict(config_dict)
                    else:
                        config = ExtractionConfig()

                    processor = DataCSVProcessor(config)

                    for url in urls:
                        try:
                            self.after(0, lambda u=url: self.label_status.configure(
                                text=f"Extracting: {u[:50]}...",
                                text_color="orange"
                            ))

                            items = processor.process_url(url)
                            if items:
                                all_results.extend(items)
                        except Exception as e:
                            print(f"[Extract] Error processing {url}: {e}")

                # Format results as text for the textbox
                if all_results:
                    formatted_text = self._format_extraction_results(all_results)

                    def update_ui():
                        # Get current text
                        current_text = self.textbox.get("0.0", "end-1c").strip()

                        # Remove the extracted URLs from text
                        for config_name, config_data in config_urls.items():
                            for url in config_data['urls']:
                                current_text = current_text.replace(url, '')

                        # Clean up multiple newlines
                        import re
                        current_text = re.sub(r'\n\s*\n+', '\n\n', current_text).strip()

                        # Append extraction results
                        if current_text:
                            new_text = current_text + "\n\n" + formatted_text
                        else:
                            new_text = formatted_text

                        # Update textbox
                        self.textbox.delete("0.0", "end")
                        self.textbox.insert("0.0", new_text)

                        # Store for raw/cleaned toggle
                        self._raw_text_backup = new_text
                        self._cleaned_text_backup = ""
                        self._editor_showing_raw = True
                        self.btn_toggle_view.configure(text="Show Cleaned", fg_color="green", state="normal")

                        # Update status
                        self.label_status.configure(
                            text=f"Extracted {len(all_results)} items from {len(all_urls)} URL(s)",
                            text_color="green"
                        )
                        self.inline_status_label.configure(
                            text=f"Extracted {len(all_results)} items - ready for audio or further editing",
                            text_color="green"
                        )

                        # Re-detect URLs in updated text
                        self._on_textbox_change()

                    self.after(0, update_ui)
                else:
                    self.after(0, lambda: self.label_status.configure(
                        text="No items extracted from URLs",
                        text_color="orange"
                    ))
                    self.after(0, lambda: self._set_url_banner_inactive("No items found"))

            except Exception as e:
                self.after(0, lambda err=str(e): self.label_status.configure(
                    text=f"Extraction error: {err}",
                    text_color="red"
                ))
                self.after(0, lambda: self._set_url_banner_inactive("Extraction failed"))

        # Run in background thread
        threading.Thread(target=do_extraction, daemon=True).start()

    def _format_extraction_results(self, items: list) -> str:
        """Format extraction results as readable text for the textbox."""
        lines = []
        lines.append("=== Extracted Content ===\n")

        for item in items:
            # Handle both dict and ExtractedItem objects
            if hasattr(item, 'to_dict'):
                item = item.to_dict()
            elif hasattr(item, 'title'):
                # It's an ExtractedItem dataclass, access attributes directly
                item = {
                    'title': getattr(item, 'title', ''),
                    'description': getattr(item, 'description', ''),
                    'source_name': getattr(item, 'source_name', ''),
                    'url': getattr(item, 'url', ''),
                }

            title = item.get('title', item.get('headline', ''))
            description = item.get('description', item.get('summary', ''))
            source = item.get('source', item.get('source_name', ''))
            url = item.get('url', '')

            if title:
                lines.append(f"• {title}")
                if source:
                    lines.append(f"  Source: {source}")
                if description:
                    lines.append(f"  {description}")
                if url:
                    lines.append(f"  {url}")
                lines.append("")

        return "\n".join(lines)

    def _toggle_editor_view(self):
        """Toggle between raw and cleaned text views in the editor."""
        current_text = self.textbox.get("0.0", "end-1c").strip()

        if self._editor_showing_raw:
            # Currently showing raw, switch to cleaned
            if self._cleaned_text_backup:
                self._raw_text_backup = current_text
                self.textbox.delete("0.0", "end")
                self.textbox.insert("0.0", self._cleaned_text_backup)
                self.btn_toggle_view.configure(text="Show Raw", fg_color="orange")
                self.inline_status_label.configure(
                    text="Showing cleaned text (ready for audio)",
                    text_color="green"
                )
                self._editor_showing_raw = False
            else:
                self.inline_status_label.configure(
                    text="No cleaned text yet - click Generate to clean",
                    text_color="orange"
                )
        else:
            # Currently showing cleaned, switch to raw
            self._cleaned_text_backup = current_text
            self.textbox.delete("0.0", "end")
            self.textbox.insert("0.0", self._raw_text_backup)
            self.btn_toggle_view.configure(text="Show Cleaned", fg_color="green")
            self.inline_status_label.configure(
                text="Showing raw text",
                text_color="gray"
            )
            self._editor_showing_raw = True

    def _fetch_detected_urls(self):
        """Fetch content from detected URLs and replace in textbox."""
        if not hasattr(self, '_current_url_detection') or not self._current_url_detection:
            return

        detection = self._current_url_detection
        raw_text = self.textbox.get("0.0", "end-1c").strip()
        api_key = self.gemini_key_entry.get().strip()

        if not api_key:
            self.inline_status_label.configure(
                text="API key required to fetch URL content",
                text_color="red"
            )
            return

        # Set banner to processing state and show progress
        self._set_url_banner_inactive(f"Fetching {detection['total_urls']} URL(s)...")
        self.inline_status_label.configure(
            text=f"Fetching {detection['total_urls']} URL(s)...",
            text_color="orange"
        )

        def fetch_async():
            def progress_cb(msg, color):
                self.after(0, lambda: self.inline_status_label.configure(text=msg, text_color=color))

            # Process mixed content (YouTube + articles + plain text)
            processed = self._process_mixed_content(raw_text, api_key, progress_callback=progress_cb)

            def update_ui():
                if processed:
                    # Store raw text for toggle, update with cleaned/processed content
                    self._raw_text_backup = raw_text
                    self._cleaned_text_backup = processed
                    self._editor_showing_raw = False  # Now showing cleaned content

                    self.textbox.delete("0.0", "end")
                    self.textbox.insert("0.0", processed)
                    self._placeholder.place_forget()

                    # Enable the Show Raw toggle button
                    self.btn_toggle_view.configure(
                        text="Show Raw",
                        fg_color="green",
                        state="normal"
                    )

                    self.inline_status_label.configure(
                        text="Content cleaned - ready for audio generation",
                        text_color="green"
                    )

                    # Hide the URL banner since we've processed the URLs
                    self._set_url_banner_inactive("Content fetched and cleaned")
                    self._current_url_detection = None
                else:
                    self.inline_status_label.configure(
                        text="Failed to fetch content",
                        text_color="red"
                    )

            self.after(0, update_ui)

        threading.Thread(target=fetch_async, daemon=True).start()

    def _dismiss_url_banner(self):
        """Dismiss the URL detection banner (keep URLs as text)."""
        self._set_url_banner_inactive("URLs kept as text")
        self._current_url_detection = None
        self.inline_status_label.configure(
            text="URLs kept as text",
            text_color="gray"
        )

    def _reset_editor_state(self):
        """Reset the editor to initial state (raw mode, no backups)."""
        self._editor_showing_raw = True
        self._raw_text_backup = ""
        self._cleaned_text_backup = ""
        self._current_url_detection = None
        self.btn_toggle_view.configure(text="Show Cleaned", fg_color="gray", state="disabled")
        self.inline_status_label.configure(text="", text_color="gray")
        self._set_url_banner_inactive()

    def _show_article_selector(self, source_name: str, links: list, cutoff_date, callback):
        """Show inline selector for article archive pages.

        Args:
            source_name: Name of the source for display
            links: List of ArchiveLink objects from source_fetcher
            cutoff_date: Date to compare for pre-selection
            callback: Function to call with selected links when user accepts
        """
        from datetime import datetime
        from urllib.parse import urlparse

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Select Articles - {source_name}")
        dialog.geometry("800x600")
        dialog.minsize(700, 450)
        dialog.transient(self)
        dialog.lift()
        dialog.grab_set()  # Make modal

        # Header
        header_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            header_frame,
            text=f"Found {len(links)} articles from {source_name}",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")

        # Info text
        ctk.CTkLabel(
            dialog,
            text="Select which articles to fetch and process (showing title and URL path):",
            text_color="gray"
        ).pack(padx=15, anchor="w")

        # Scrollable container for article checkboxes
        container = ctk.CTkScrollableFrame(dialog, width=750, height=400)
        container.pack(padx=15, pady=10, fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)

        # Track checkbox variables
        checkbox_vars = []

        for idx, link in enumerate(links):
            row_frame = ctk.CTkFrame(container, fg_color="transparent")
            row_frame.grid(row=idx, column=0, sticky="ew", pady=3)
            row_frame.grid_columnconfigure(1, weight=1)

            # Determine if within date range (pre-select if so)
            within_range = True
            if link.date and cutoff_date:
                within_range = link.date.date() >= cutoff_date.date()

            var = ctk.BooleanVar(value=within_range)
            checkbox_vars.append((var, link))

            # Checkbox
            chk = ctk.CTkCheckBox(
                row_frame,
                text="",
                variable=var,
                width=24
            )
            chk.grid(row=0, column=0, rowspan=2, padx=(5, 10), sticky="n", pady=3)

            # Title - show meaningful text or extract from URL
            title_text = link.title.strip() if link.title.strip() else "Untitled"
            # If title looks like it's just a fragment or very short, use URL path
            if len(title_text) < 10 or title_text.lower() in ['home', 'article', 'post', 'page']:
                # Extract meaningful part from URL
                parsed = urlparse(link.url)
                path_parts = [p for p in parsed.path.split('/') if p]
                if path_parts:
                    title_text = path_parts[-1].replace('-', ' ').replace('_', ' ').title()[:60]
                else:
                    title_text = parsed.netloc

            title_text = title_text[:70] + "..." if len(title_text) > 70 else title_text
            title_label = ctk.CTkLabel(
                row_frame,
                text=title_text,
                anchor="w",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            title_label.grid(row=0, column=1, sticky="w")

            # URL path preview (second row, smaller text)
            parsed_url = urlparse(link.url)
            url_preview = parsed_url.path[:60] + "..." if len(parsed_url.path) > 60 else parsed_url.path
            if not url_preview or url_preview == "/":
                url_preview = link.url[:60]
            url_label = ctk.CTkLabel(
                row_frame,
                text=url_preview,
                anchor="w",
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            url_label.grid(row=1, column=1, sticky="w")

            # Date (if available)
            if link.date_str or link.date:
                date_text = link.date_str if link.date_str else link.date.strftime("%b %d, %Y")
                date_color = "gray" if within_range else "orange"
                date_label = ctk.CTkLabel(
                    row_frame,
                    text=date_text,
                    text_color=date_color,
                    font=ctk.CTkFont(size=11)
                )
                date_label.grid(row=0, column=2, rowspan=2, padx=(10, 5), sticky="e")

        # Button row
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(5, 15))

        # Selection count label
        count_label = ctk.CTkLabel(btn_frame, text="", font=ctk.CTkFont(size=11))
        count_label.pack(side="left")

        def update_count(*args):
            selected = sum(1 for var, _ in checkbox_vars if var.get())
            count_label.configure(text=f"{selected} of {len(links)} selected")

        # Initial count
        update_count()

        # Bind count update to checkbox changes
        for var, _ in checkbox_vars:
            var.trace_add("write", update_count)

        def select_all():
            for var, _ in checkbox_vars:
                var.set(True)

        def select_none():
            for var, _ in checkbox_vars:
                var.set(False)

        def select_in_range():
            for var, link in checkbox_vars:
                if link.date and cutoff_date:
                    var.set(link.date.date() >= cutoff_date.date())
                else:
                    var.set(True)  # Select if no date info

        def accept():
            selected_links = [link for var, link in checkbox_vars if var.get()]
            dialog.destroy()
            if callback:
                callback(selected_links)

        def cancel():
            dialog.destroy()
            if callback:
                callback([])  # Empty list indicates cancellation

        # Helper buttons
        ctk.CTkButton(
            btn_frame, text="Select All", width=90,
            fg_color="gray", command=select_all
        ).pack(side="right", padx=3)

        ctk.CTkButton(
            btn_frame, text="Select None", width=90,
            fg_color="gray", command=select_none
        ).pack(side="right", padx=3)

        ctk.CTkButton(
            btn_frame, text="In Date Range", width=100,
            fg_color="gray", command=select_in_range
        ).pack(side="right", padx=3)

        # Main action buttons
        action_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        action_frame.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkButton(
            action_frame, text="Accept", width=140,
            fg_color="green", command=accept,
            font=ctk.CTkFont(weight="bold")
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            action_frame, text="Cancel", width=100,
            fg_color="gray", command=cancel
        ).pack(side="right", padx=5)

    def set_extract_mode(self, mode):
        """Switch between URL and HTML extraction modes."""
        self.extract_mode_var.set(mode)
        # Active tab: blue with border, inactive: gray and flat
        active_color = ("#3B8ED0", "#1F6AA5")  # Default blue
        inactive_color = ("gray70", "gray30")
        if mode == "url":
            self.btn_tab_url.configure(fg_color=active_color, border_width=2, border_color=("gray40", "gray60"), text="● From URL(s)")
            self.btn_tab_html.configure(fg_color=inactive_color, border_width=0, text="○ Paste HTML")
            self.url_input_frame.grid()
            self.html_input_frame.grid_remove()
        else:
            self.btn_tab_url.configure(fg_color=inactive_color, border_width=0, text="○ From URL(s)")
            self.btn_tab_html.configure(fg_color=active_color, border_width=2, border_color=("gray40", "gray60"), text="● Paste HTML")
            self.url_input_frame.grid_remove()
            self.html_input_frame.grid()

    def _get_data_processor(self):
        """Get or create the data processor (lazy initialization)."""
        if self.data_processor is None:
            config = ExtractionConfig(
                resolve_redirects=False,  # Speed up by disabling redirect resolution
                strip_tracking_params=True
            )
            self.data_processor = DataCSVProcessor(config)
        return self.data_processor

    def start_extraction(self):
        """Start the data extraction process in a background thread."""
        mode = self.extract_mode_var.get()

        if mode == "url":
            # Get URLs from multi-line text area - flexible parsing
            url_text = self.extract_url_text.get("1.0", "end-1c").strip()
            if not url_text:
                self.label_status.configure(text="Please enter at least one URL to extract.", text_color="orange")
                return

            # Extract URLs using regex - finds http/https URLs anywhere in the text
            import re
            url_pattern = r'https?://[^\s<>"\'`,\)\]]+[^\s<>"\'`,\.\)\]]'
            found_urls = re.findall(url_pattern, url_text)

            # If no URLs found with http, try to find domain-like patterns
            if not found_urls:
                # Split by whitespace, newlines, commas and check each piece
                pieces = re.split(r'[\s,]+', url_text)
                for piece in pieces:
                    piece = piece.strip().strip(',').strip()
                    if piece and ('.' in piece) and len(piece) > 5:
                        # Looks like it could be a URL
                        if not piece.startswith('http'):
                            piece = 'https://' + piece
                        found_urls.append(piece)

            # Deduplicate while preserving order
            seen = set()
            urls = []
            for url in found_urls:
                # Clean up any trailing punctuation that might have been captured
                url = url.rstrip('.,;:')
                if url not in seen:
                    seen.add(url)
                    urls.append(url)

            if not urls:
                self.label_status.configure(text="No valid URLs found. Paste URLs starting with http:// or https://", text_color="orange")
                return
        else:
            html = self.extract_html_text.get("1.0", "end-1c").strip()
            if not html:
                self.label_status.configure(text="Please paste HTML content to extract.", text_color="orange")
                return
            urls = []  # Not used in HTML mode

        # Get config
        config_name = self.extract_config_var.get()
        enrich_grid = self.grid_enrich_var.get()
        research_articles = self.research_articles_var.get()
        api_key = self.gemini_key_entry.get().strip()  # For LLM analysis

        # Disable button during extraction
        self.btn_extract.configure(state="disabled", text="Extracting...")
        url_count = len(urls) if mode == "url" else 1
        self.label_status.configure(text=f"Extracting from {url_count} source(s)...", text_color="orange")

        def extract_thread():
            try:
                processor = self._get_data_processor()

                # Load custom instructions if not default
                custom_instructions = None
                if config_name != "Default":
                    config_file = config_name.lower().replace(" ", "_") + ".json"
                    config_path = os.path.join(os.path.dirname(__file__), "extraction_instructions", config_file)
                    if os.path.exists(config_path):
                        custom_instructions = load_custom_instructions(config_path)

                # Extract items
                if mode == "url":
                    all_items = []
                    for i, url in enumerate(urls):
                        self.after(0, lambda i=i, total=len(urls): self.label_status.configure(
                            text=f"Extracting URL {i+1}/{total}...", text_color="orange"))
                        try:
                            items = processor.process_url(url, custom_instructions)
                            all_items.extend(items)
                        except Exception as url_error:
                            print(f"Error processing {url}: {url_error}")
                    items = all_items
                else:
                    source_url = self.extract_source_url.get().strip()
                    items = processor.process_html(html, source_url, custom_instructions)

                # Enrich with Grid if requested
                if enrich_grid and items:
                    self.after(0, lambda: self.label_status.configure(text="Enriching with Grid data...", text_color="orange"))
                    items = processor.enrich_with_grid(items)

                # Research articles if requested - research ALL items for Grid matching
                if research_articles and items:
                    self.after(0, lambda: self.label_status.configure(text="Researching articles...", text_color="orange"))
                    items = processor.research_articles(items, all_items=True, api_key=api_key)

                # Store and display results
                self.extracted_items = items
                self.after(0, lambda: self._display_extraction_results(items))

            except Exception as e:
                error_msg = str(e)[:50]
                self.after(0, lambda msg=error_msg: self.label_status.configure(text=f"Extraction error: {msg}", text_color="red"))
            finally:
                self.after(0, lambda: self.btn_extract.configure(state="normal", text="Extract Links"))

        threading.Thread(target=extract_thread, daemon=True).start()

    def _display_extraction_results(self, items):
        """Display extracted items in the results list."""
        # Clear previous results
        for widget in self.extract_results_list.winfo_children():
            widget.destroy()

        if not items:
            self.label_status.configure(text="No links found.", text_color="orange")
            self.extract_results_frame.grid_remove()
            return

        # Update count
        matched_count = sum(1 for item in items if item.custom_fields.get("grid_matched"))
        if matched_count > 0:
            self.extract_count_label.configure(text=f"Extracted Links ({len(items)}) - {matched_count} Grid matches")
        else:
            self.extract_count_label.configure(text=f"Extracted Links ({len(items)})")

        # Show results frame
        self.extract_results_frame.grid()

        # Add items to list (limit to 50 for performance)
        for i, item in enumerate(items[:50]):
            item_frame = ctk.CTkFrame(self.extract_results_list, fg_color=("gray90", "gray25"))
            item_frame.grid(row=i, column=0, sticky="ew", pady=2, padx=2)
            item_frame.grid_columnconfigure(0, weight=1)

            # Title with optional Grid badge
            title_text = item.title[:60] + "..." if len(item.title) > 60 else item.title
            if item.custom_fields.get("grid_matched"):
                title_text = f"[Grid] {title_text}"

            title_label = ctk.CTkLabel(item_frame, text=title_text, anchor="w", font=ctk.CTkFont(size=12))
            title_label.grid(row=0, column=0, sticky="w", padx=8, pady=(4, 0))

            # URL (truncated)
            url_text = item.url[:70] + "..." if len(item.url) > 70 else item.url
            url_label = ctk.CTkLabel(item_frame, text=url_text, anchor="w", text_color="gray", font=ctk.CTkFont(size=10))
            url_label.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 4))

            # Category if available
            if item.category:
                cat_label = ctk.CTkLabel(item_frame, text=item.category, text_color=("gray40", "gray70"), font=ctk.CTkFont(size=9))
                cat_label.grid(row=0, column=1, sticky="e", padx=8)

        # Show remaining count if truncated
        if len(items) > 50:
            more_label = ctk.CTkLabel(self.extract_results_list, text=f"... and {len(items) - 50} more items", text_color="gray")
            more_label.grid(row=50, column=0, pady=5)

        self.label_status.configure(text=f"Extracted {len(items)} links.", text_color="green")

    def export_extracted_csv(self):
        """Export extracted items to a CSV file."""
        if not self.extracted_items:
            self.label_status.configure(text="No items to export.", text_color="orange")
            return

        # Ask for save location
        default_name = f"extracted_{datetime.datetime.now().strftime('%Y-%m-%d')}.csv"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=default_name
        )

        if not file_path:
            return

        try:
            processor = self._get_data_processor()
            processor.save_to_csv(self.extracted_items, file_path)
            self.label_status.configure(text=f"Saved {len(self.extracted_items)} items to CSV.", text_color="green")
        except Exception as e:
            self.label_status.configure(text=f"Error saving CSV: {e}", text_color="red")

    def copy_extracted_text(self):
        """Copy extracted links to clipboard as formatted text."""
        if not self.extracted_items:
            self.label_status.configure(text="No items to copy.", text_color="orange")
            return

        # Format as text
        lines = []
        for item in self.extracted_items:
            line = f"{item.title}"
            if item.category:
                line += f" [{item.category}]"
            line += f"\n  {item.url}"
            if item.custom_fields.get("grid_matched"):
                grid_name = item.custom_fields.get("grid_entity_name", "")
                line += f"\n  Grid: {grid_name}"
            lines.append(line)

        text = "\n\n".join(lines)

        # Copy to clipboard
        self.clipboard_clear()
        self.clipboard_append(text)

        self.label_status.configure(text=f"Copied {len(self.extracted_items)} items to clipboard.", text_color="green")

    def export_to_google_sheets(self):
        """Export extracted items to Google Sheets."""
        if not self.extracted_items:
            self.label_status.configure(text="No items to export.", text_color="orange")
            return

        # Check if sheets integration is available
        try:
            from sheets_manager import is_sheets_available, get_missing_requirements, export_items_to_sheet, extract_sheet_id
        except ImportError:
            self.label_status.configure(text="Sheets module not found.", text_color="red")
            return

        if not is_sheets_available():
            missing = get_missing_requirements()
            # Show setup dialog
            self._show_sheets_setup_dialog(missing)
            return

        # Get sheet config from current extractor config
        config = self._get_current_extraction_config()
        sheets_config = config.get("google_sheets", {}) if config else {}

        spreadsheet_id = sheets_config.get("spreadsheet_id", "")
        sheet_name = sheets_config.get("sheet_name", "Sheet1")
        columns = sheets_config.get("columns", None)

        if not spreadsheet_id:
            # Ask user for sheet URL/ID
            self._show_sheet_id_dialog(sheet_name, columns)
            return

        # Export to sheet
        self._do_sheets_export(spreadsheet_id, sheet_name, columns)

    def _show_sheets_setup_dialog(self, missing_info: str):
        """Show dialog explaining how to set up Google Sheets integration."""
        dlg = ctk.CTkToplevel(self)
        dlg.title("Google Sheets Setup Required")
        dlg.geometry("500x350")
        dlg.minsize(450, 300)

        ctk.CTkLabel(dlg, text="Google Sheets Setup", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))

        info_text = """To use Google Sheets export:

1. Go to Google Cloud Console
2. Create a project and enable Google Sheets API
3. Create a Service Account (IAM & Admin > Service Accounts)
4. Download the JSON key file
5. Save it as 'google_credentials.json' in the app folder
6. Share your Google Sheet with the service account email

Missing requirements:
""" + missing_info

        text_frame = ctk.CTkFrame(dlg)
        text_frame.pack(padx=20, pady=10, fill="both", expand=True)

        text_box = ctk.CTkTextbox(text_frame, wrap="word")
        text_box.pack(fill="both", expand=True)
        text_box.insert("1.0", info_text)
        text_box.configure(state="disabled")

        ctk.CTkButton(dlg, text="Close", command=dlg.destroy, width=100).pack(pady=15)

    def _show_sheet_id_dialog(self, default_sheet_name: str, columns: list):
        """Show dialog to enter Google Sheet ID/URL."""
        dlg = ctk.CTkToplevel(self)
        dlg.title("Export to Google Sheets")
        dlg.geometry("500x200")
        dlg.minsize(450, 180)

        ctk.CTkLabel(dlg, text="Enter Google Sheet URL or ID:", font=ctk.CTkFont(size=14)).pack(pady=(20, 5))

        entry_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        entry_frame.pack(fill="x", padx=20, pady=10)

        sheet_entry = ctk.CTkEntry(entry_frame, width=400, placeholder_text="https://docs.google.com/spreadsheets/d/... or sheet ID")
        sheet_entry.pack(fill="x")

        ctk.CTkLabel(dlg, text=f"Sheet tab name: {default_sheet_name}", font=ctk.CTkFont(size=12), text_color="gray").pack()

        btn_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_frame.pack(pady=20)

        def do_export():
            sheet_input = sheet_entry.get().strip()
            if not sheet_input:
                self.label_status.configure(text="Please enter a Sheet URL or ID.", text_color="orange")
                return
            dlg.destroy()
            from sheets_manager import extract_sheet_id
            spreadsheet_id = extract_sheet_id(sheet_input)
            self._do_sheets_export(spreadsheet_id, default_sheet_name, columns)

        ctk.CTkButton(btn_frame, text="Export", command=do_export, fg_color="#0F9D58", width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=dlg.destroy, fg_color="gray", width=100).pack(side="left", padx=5)

    def _do_sheets_export(self, spreadsheet_id: str, sheet_name: str, columns: list):
        """Perform the actual export to Google Sheets."""
        self.label_status.configure(text="Exporting to Google Sheets...", text_color=("gray10", "#DCE4EE"))
        self.update()

        def export_task():
            try:
                from sheets_manager import export_items_to_sheet
                result = export_items_to_sheet(
                    items=self.extracted_items,
                    spreadsheet_id=spreadsheet_id,
                    sheet_name=sheet_name,
                    columns=columns
                )
                updated_rows = result.get('updates', {}).get('updatedRows', len(self.extracted_items))
                self.after(0, lambda: self.label_status.configure(
                    text=f"Exported {updated_rows} rows to Google Sheets!", text_color="green"))
            except Exception as e:
                error_msg = str(e)
                if "403" in error_msg:
                    error_msg = "Permission denied. Share the sheet with the service account email."
                elif "404" in error_msg:
                    error_msg = "Sheet not found. Check the spreadsheet ID."
                self.after(0, lambda: self.label_status.configure(
                    text=f"Sheets error: {error_msg[:80]}", text_color="red"))

        threading.Thread(target=export_task, daemon=True).start()

    def _get_current_extraction_config(self) -> dict:
        """Get the current extraction config based on selected extractor."""
        try:
            extractor_name = self.extractor_var.get() if hasattr(self, 'extractor_var') else None
            if not extractor_name or extractor_name == "Auto-detect":
                return {}

            config_path = os.path.join(os.path.dirname(__file__), "extraction_instructions", f"{extractor_name}.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

if __name__ == "__main__":
    # On macOS frozen apps, ensure we are the foreground application.
    # Without this, macOS may not deliver mouse events to the window.
    if sys.platform == 'darwin' and getattr(sys, 'frozen', False):
        try:
            # Modern Cocoa approach — works on macOS 10.14+
            from Foundation import NSBundle
            bundle = NSBundle.mainBundle()
            info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
            if info and not info.get('LSUIElement'):
                # Ensure this is recognized as a regular app
                pass
        except ImportError:
            pass
        try:
            # Activate as foreground app via Cocoa (PyObjC)
            from AppKit import NSApplication
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except ImportError:
            # PyObjC not available — use osascript as fallback
            try:
                import subprocess
                subprocess.Popen(
                    ['osascript', '-e',
                     'tell application "System Events" to set frontmost of '
                     'the first process whose unix id is '
                     f'{os.getpid()} to true'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception:
                pass  # Continue anyway — _activate_window() will retry via Tk

    # Check sys.argv for a dailybriefing:// URL (passed by macOS on app launch via URL scheme)
    launch_url = None
    for arg in sys.argv[1:]:
        if arg.startswith('dailybriefing://'):
            launch_url = arg
            break

    app = AudioBriefingApp(launch_url=launch_url)
    app.mainloop()

