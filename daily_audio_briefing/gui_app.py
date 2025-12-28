import customtkinter as ctk
import subprocess
import threading
import os
import sys
import glob
import datetime
import json
import tkinter.filedialog as filedialog
import qrcode
from PIL import Image # PIL is imported by qrcode, but explicit import helps CTkImage

from podcast_manager import PodcastServer # Import your podcast manager
from file_manager import FileManager
from audio_generator import AudioGenerator
from voice_manager import VoiceManager
from convert_to_mp3 import check_ffmpeg

# Data extraction imports
from data_csv_processor import DataCSVProcessor, ExtractionConfig, load_custom_instructions

# Helper functions for transcription dependency checks
def check_faster_whisper_installed():
    try:
        import faster_whisper
        return True
    except ImportError:
        return False

# Re-use check_ffmpeg from transcriber.py for consistency
from transcriber import check_ffmpeg
try:
    from tkcalendar import DateEntry
except Exception:
    DateEntry = None

# Google Drive sign-in and sync removed
# from drive_manager import DriveManager

# Configuration - Dark theme to match web interface
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AudioBriefingApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Daily Audio Briefing")
        self.geometry("950x900") # Wider default width to fit controls

        # Main window grid - single scrollable container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create scrollable main container with wider scrollbar
        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.main_scroll.grid_columnconfigure(0, weight=1)

        # Widen the scrollbar for easier interaction
        try:
            # Access the internal scrollbar and make it wider
            self.main_scroll._scrollbar.configure(width=16)
        except:
            pass  # Fallback if internal structure changes

        # Initialize managers
        self.file_manager = FileManager()
        self.selected_file_paths = []
        self.audio_generator = AudioGenerator(status_callback=self._update_status)
        self.voice_manager = VoiceManager()

        # Data extraction
        self.extracted_items = []
        self.data_processor = None  # Lazy init to avoid slow startup

        # App settings
        self.settings = self._load_settings()

        # self.podcast_server = PodcastServer()  # Disabled
        # self.drive_manager = None  # Google Drive features removed

        # Header
        self.label_header = ctk.CTkLabel(self.main_scroll, text="Daily News Summary & YouTube Integration", font=ctk.CTkFont(size=20, weight="bold"))
        self.label_header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        # Text Area Section (collapsible)
        self.frame_text = ctk.CTkFrame(self.main_scroll)
        self.frame_text.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.frame_text.grid_columnconfigure(0, weight=1)

        # Header with expand/collapse toggle and fetch button
        text_header = ctk.CTkFrame(self.frame_text, fg_color="transparent")
        text_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 0))
        text_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(text_header, text="News Summary", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w")

        # Fetch Article button - for loading article content from URL
        self.btn_fetch_article = ctk.CTkButton(text_header, text="Fetch Article", width=100, fg_color="green", command=self.open_fetch_article_dialog)
        self.btn_fetch_article.grid(row=0, column=1, padx=(10, 5))

        # Settings button
        self.btn_settings = ctk.CTkButton(text_header, text="Settings", width=70, fg_color="gray", command=self.open_settings_dialog)
        self.btn_settings.grid(row=0, column=2, padx=(0, 5))

        self.text_toggle_btn = ctk.CTkButton(text_header, text="Collapse", width=70, fg_color="gray", command=self.toggle_text_section)
        self.text_toggle_btn.grid(row=0, column=3, padx=(0, 0))

        # Text content frame (collapsible)
        self.text_content = ctk.CTkFrame(self.frame_text, fg_color="transparent")
        self.text_content.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.text_content.grid_columnconfigure(0, weight=1)
        self.text_expanded = True  # Track expansion state

        # Textbox with fixed height (scrollable container handles overflow)
        self.textbox = ctk.CTkTextbox(self.text_content, height=150, font=ctk.CTkFont(size=14))
        self.textbox.grid(row=0, column=0, sticky="ew")

        # Non-textual placeholder overlay
        self._placeholder = ctk.CTkLabel(self.textbox, text="Paste or edit the news summary here. You can also load it via Get YouTube News or Upload File.", text_color="gray")
        self._placeholder.place(relx=0.02, rely=0.02, anchor="nw")
        def _toggle_placeholder(event=None):
            has_text = bool(self.textbox.get("0.0", "end-1c").strip())
            if has_text:
                self._placeholder.place_forget()
            else:
                self._placeholder.place(relx=0.02, rely=0.02, anchor="nw")
        self.textbox.bind("<KeyRelease>", _toggle_placeholder)
        self.textbox.bind("<FocusIn>", _toggle_placeholder)
        self.textbox.bind("<FocusOut>", _toggle_placeholder)

        self.frame_yt_api = ctk.CTkFrame(self.main_scroll)
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
        
        self.model_var = ctk.StringVar(value="Fast (FREE)")
        self.model_combo = ctk.CTkComboBox(
            frame_row0,
            variable=self.model_var,
            values=["Fast (FREE)", "Balanced (FREE)", "Best (FREE, 50/day)"],
            width=180,
            state="readonly"
        )
        self.model_combo.grid(row=0, column=6, sticky="w")
        
        # Row 1: Help text
        help_text = "💡 Fast: 4000/min | Balanced: 1500/day | Best: 50/day (highest quality)"
        ctk.CTkLabel(self.frame_yt_api, text=help_text, font=ctk.CTkFont(size=10), text_color="gray").grid(
            row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w"
        )
        
        # Row 2: Get YouTube News & Edit Sources
        frame_row2 = ctk.CTkFrame(self.frame_yt_api, fg_color="transparent")
        frame_row2.grid(row=2, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")
        frame_row2.grid_columnconfigure(0, weight=1)
        frame_row2.grid_columnconfigure(1, weight=1)
        frame_row2.grid_columnconfigure(2, weight=1)
        
        self.btn_get_yt_news = ctk.CTkButton(frame_row2, text="Get YouTube News", command=self.get_youtube_news_from_channels)
        self.btn_get_yt_news.grid(row=0, column=0, padx=(0, 5), sticky="ew")

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

        # Row 4: Upload File
        self.btn_upload_file = ctk.CTkButton(self.frame_yt_api, text="Upload File (.txt, .mp3, .wav, .m4a)", command=self.upload_text_file)
        self.btn_upload_file.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        # Selected files panel
        self.selected_panel = ctk.CTkFrame(self.frame_yt_api, fg_color=("gray90", "gray20"))
        self.selected_panel.grid(row=5, column=0, columnspan=2, padx=10, pady=(0,10), sticky="ew")
        self.selected_panel.grid_columnconfigure(0, weight=1)
        self.files_combo = ctk.CTkComboBox(self.selected_panel, values=["No files selected"], width=250, state="readonly")
        self.files_combo.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.files_combo.set("No files selected")
        self.btn_clear_selected = ctk.CTkButton(self.selected_panel, text="Clear", width=80, command=self._clear_selected_file)
        self.btn_clear_selected.grid(row=0, column=1, padx=(10,10), pady=5)
        self.btn_transcribe = ctk.CTkButton(self.selected_panel, text="Transcribe", width=100, command=self.start_transcription, state="disabled", fg_color="green")
        self.btn_transcribe.grid(row=0, column=2, padx=(0,10), pady=5)

        # Button: Specific URLs
        self.btn_specific_urls = ctk.CTkButton(self.frame_yt_api, text="Specific URLs", command=self.open_specific_urls_dialog)
        self.btn_specific_urls.grid(row=6, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        # Audio Controls Frame
        self.frame_audio_controls = ctk.CTkFrame(self.main_scroll)
        self.frame_audio_controls.grid(row=3, column=0, padx=20, pady=(5, 20), sticky="ew")
        self.frame_audio_controls.grid_columnconfigure((0, 1), weight=1)

        # Row 0: Fast Generation
        self.btn_fast = ctk.CTkButton(self.frame_audio_controls, text="Generate Fast (gTTS)", command=self.start_fast_generation)
        self.btn_fast.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Row 1: Quality Generation Options
        self.label_voice = ctk.CTkLabel(self.frame_audio_controls, text="Quality Voice:")
        self.label_voice.grid(row=1, column=0, padx=10, pady=(10, 0), sticky="w")
        # Ensure distinct rows to avoid overlap
        self.frame_audio_controls.grid_rowconfigure(2, weight=0)
        self.frame_audio_controls.grid_rowconfigure(3, weight=0)
        # Reserve dedicated rows to prevent covering other controls
        for r in (2,3,4,5):
            self.frame_audio_controls.grid_rowconfigure(r, weight=0)



        self.voice_var = ctk.StringVar(value="af_sarah")
        self.combo_voices = ctk.CTkComboBox(self.frame_audio_controls, variable=self.voice_var, values=self.voice_manager.get_available_voices())
        self.combo_voices.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="ew")
        self.btn_sample = ctk.CTkButton(self.frame_audio_controls, text="Play Sample", width=120, fg_color="gray", command=self.play_sample)
        self.btn_sample.grid(row=2, column=1, padx=10, pady=(0, 5), sticky="e")

        # Convert summaries by date
        self.btn_convert_dates = ctk.CTkButton(self.frame_audio_controls, text="Convert Selected Dates to Audio", command=self.select_dates_to_audio)
        self.btn_convert_dates.grid(row=3, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")

        # Direct Audio option (skip summary, clean text for listening)
        self.direct_audio_var = ctk.BooleanVar(value=False)
        self.chk_direct_audio = ctk.CTkCheckBox(
            self.frame_audio_controls,
            text="Direct Audio (clean text for listening, no summary)",
            variable=self.direct_audio_var
        )
        self.chk_direct_audio.grid(row=4, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="w")

        self.btn_quality = ctk.CTkButton(self.frame_audio_controls, text="Generate Quality (Kokoro)", command=self.start_quality_generation)
        self.btn_quality.grid(row=5, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")

        # Data Extraction Section
        self.frame_extract = ctk.CTkFrame(self.main_scroll)
        self.frame_extract.grid(row=4, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.frame_extract.grid_columnconfigure(0, weight=1)

        # Header with expand/collapse toggle
        extract_header = ctk.CTkFrame(self.frame_extract, fg_color="transparent")
        extract_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        extract_header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(extract_header, text="Data Extractor", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w")
        self.extract_toggle_btn = ctk.CTkButton(extract_header, text="Expand", width=70, fg_color="gray", command=self.toggle_extract_section)
        self.extract_toggle_btn.grid(row=0, column=2, padx=(10, 0))

        # Collapsible content
        self.extract_content = ctk.CTkFrame(self.frame_extract, fg_color="transparent")
        self.extract_content.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.extract_content.grid_columnconfigure(0, weight=1)
        self.extract_content.grid_remove()  # Start collapsed

        # Mode tabs (URL vs HTML)
        tab_frame = ctk.CTkFrame(self.extract_content, fg_color="transparent")
        tab_frame.grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.extract_mode_var = ctk.StringVar(value="url")
        self.btn_tab_url = ctk.CTkButton(tab_frame, text="Extract from URL", width=140, command=lambda: self.set_extract_mode("url"))
        self.btn_tab_url.pack(side="left", padx=(0, 5))
        self.btn_tab_html = ctk.CTkButton(tab_frame, text="Paste HTML", width=120, fg_color="gray", command=lambda: self.set_extract_mode("html"))
        self.btn_tab_html.pack(side="left")

        # URL input section
        self.url_input_frame = ctk.CTkFrame(self.extract_content, fg_color="transparent")
        self.url_input_frame.grid(row=1, column=0, sticky="ew", pady=5)
        self.url_input_frame.grid_columnconfigure(0, weight=1)

        self.extract_url_entry = ctk.CTkEntry(self.url_input_frame, placeholder_text="https://cryptosum.beehiiv.com/p/...")
        self.extract_url_entry.grid(row=0, column=0, sticky="ew")

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

        # Load available extraction configs
        self.extract_config_var = ctk.StringVar(value="Default")
        config_values = self._get_extraction_configs()
        self.extract_config_combo = ctk.CTkComboBox(options_frame, variable=self.extract_config_var, values=config_values, width=150, state="readonly")
        self.extract_config_combo.pack(side="left", padx=(0, 15))

        self.grid_enrich_var = ctk.BooleanVar(value=False)
        self.chk_grid_enrich = ctk.CTkCheckBox(options_frame, text="Enrich with Grid", variable=self.grid_enrich_var)
        self.chk_grid_enrich.pack(side="left")

        self.research_articles_var = ctk.BooleanVar(value=False)
        self.chk_research_articles = ctk.CTkCheckBox(options_frame, text="Research Articles", variable=self.research_articles_var)
        self.chk_research_articles.pack(side="left", padx=(15, 0))

        # Extract button
        self.btn_extract = ctk.CTkButton(self.extract_content, text="Extract Links", command=self.start_extraction, fg_color="green")
        self.btn_extract.grid(row=3, column=0, sticky="ew", pady=(10, 5))

        # Results section (hidden until extraction)
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

        self.btn_copy_text = ctk.CTkButton(export_btns, text="Copy", width=60, fg_color="gray", command=self.copy_extracted_text)
        self.btn_copy_text.pack(side="left")

        # Results list
        self.extract_results_list = ctk.CTkScrollableFrame(self.extract_results_frame, height=150)
        self.extract_results_list.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.extract_results_list.grid_columnconfigure(0, weight=1)

        # Row 3: Broadcast Button (disabled)
        # self.btn_broadcast = ctk.CTkButton(self.frame_audio_controls, text="Broadcast to Phone", fg_color="green", command=self.toggle_podcast_server)
        # Row 3: Local HTTP Server (removed)
        # self.btn_http_server = ctk.CTkButton(self.frame_audio_controls, text="Start Local Server", fg_color="green", command=self.toggle_http_server)
        # self.btn_http_server.grid(row=4, column=0, columnspan=2, padx=10, pady=15, sticky="ew")
        # self.btn_broadcast.grid(row=4, column=0, columnspan=2, padx=10, pady=15, sticky="ew")
        
        # Row 4: Drive Sync Button
        # Google Drive sync button removed
        # self.btn_sync_drive = ctk.CTkButton(self.frame_audio_controls, text="Sync to Google Drive", fg_color="blue", command=self.sync_drive_action)
        # (button removed)

        # Status Label
        self.label_status = ctk.CTkLabel(self.main_scroll, text="Ready", text_color=("gray10", "#DCE4EE"), font=("Arial", 14, "bold"))
        self.label_status.grid(row=6, column=0, padx=20, pady=(0, 10)) # Row 6

        # Compression Status Indicator
        self.compression_enabled = check_ffmpeg()
        compression_text = "✓ Compression enabled" if self.compression_enabled else "⚠ Compression disabled - see installation guide"
        compression_color = "green" if self.compression_enabled else "orange"
        
        self.label_compression = ctk.CTkLabel(
            self.main_scroll,
            text=compression_text,
            text_color=compression_color,
            font=("Arial", 11),
            cursor="hand2"  # Show clickable cursor
        )
        self.label_compression.grid(row=7, column=0, padx=20, pady=(0, 10))
        self.label_compression.bind("<Button-1>", lambda e: self.show_compression_guide())
        # Transcription Status Indicator
        self.transcription_ffmpeg_enabled = check_ffmpeg()
        self.transcription_whisper_installed = check_faster_whisper_installed()

        transcription_text = ""
        transcription_color = ""
        cursor_type = "arrow"

        if self.transcription_ffmpeg_enabled and self.transcription_whisper_installed:
            transcription_text = "✓ Transcription ready"
            transcription_color = "green"
        elif not self.transcription_ffmpeg_enabled and not self.transcription_whisper_installed:
            transcription_text = "⚠ Transcription disabled - Install ffmpeg & faster-whisper"
            transcription_color = "orange"
            cursor_type = "hand2"
        elif not self.transcription_ffmpeg_enabled:
            transcription_text = "⚠ Transcription disabled - Install ffmpeg"
            transcription_color = "orange"
            cursor_type = "hand2"
        elif not self.transcription_whisper_installed:
            transcription_text = "⚠ Transcription disabled - Install faster-whisper"
            transcription_color = "orange"
            cursor_type = "hand2"

        self.label_transcription = ctk.CTkLabel(
            self.main_scroll,
            text=transcription_text,
            text_color=transcription_color,
            font=("Arial", 11),
            cursor=cursor_type
        )
        self.label_transcription.grid(row=8, column=0, padx=20, pady=(0, 10))
        self.label_transcription.bind("<Button-1>", lambda e: self.show_transcription_guide(
            missing_ffmpeg=not self.transcription_ffmpeg_enabled,
            missing_whisper=not self.transcription_whisper_installed
        ))
        # Open Folder Button
        self.btn_open = ctk.CTkButton(self.main_scroll, text="Open Output Folder", fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"), command=self.open_output_folder)
        self.btn_open.grid(row=9, column=0, padx=20, pady=(0, 20)) # Row 9

        # Load data

    def _update_status(self, message, color="gray"):
        """Callback for status updates from managers.
        
        Args:
            message: Status message to display
            color: Text color for the message
        """
        self.after(0, lambda: self.label_status.configure(text=message, text_color=color))
    
    def on_mode_changed(self, *args):
        """Handle mode dropdown changes (Days/Videos/Specific URLs)."""
        mode = self.mode_var.get()
        
        if mode == "Specific URLs":
            # Disable date range controls for Specific URLs mode
            self.range_var.set(False)
            self.chk_range.configure(state="disabled")
            self.start_date_entry.configure(state="disabled")
            self.end_date_entry.configure(state="disabled")
            self.btn_start_cal.configure(state="disabled")
            self.btn_end_cal.configure(state="disabled")
            
            # Change entry placeholder to indicate URL input
            self.entry_value.delete(0, "end")
            self.entry_value.configure(placeholder_text="Enter video URLs, one per line (or click to expand)")
        else:
            # Re-enable date range controls for Days/Videos modes
            self.chk_range.configure(state="normal")
            if not self.range_var.get():
                self.entry_value.configure(state="normal")
                self.combo_mode.configure(state="normal")
            
            # Restore normal placeholder
            self.entry_value.configure(placeholder_text="")
            if not self.entry_value.get():
                self.entry_value.insert(0, "7")
    
    def on_toggle_range(self):
        use_range = bool(self.range_var.get())
        state = "disabled" if use_range else "normal"
        try:
            self.entry_value.configure(state=state)
            self.combo_mode.configure(state=state)
        except Exception:
            pass

        self.load_current_summary()
        self.load_api_key()

    def _open_calendar_for(self, target_entry):
        import calendar as _cal
        dlg = ctk.CTkToplevel(self)
        dlg.title("Select Date")
        dlg.geometry("360x340")
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
        ctk.CTkButton(bar, text="Prev", command=lambda: (ent_m.delete(0,"end"), ent_m.insert(0,str((int(ent_m.get())-2)%12+1)), render())).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Next", command=lambda: (ent_m.delete(0,"end"), ent_m.insert(0,str((int(ent_m.get())%12)+1)), render())).pack(side="left", padx=4)
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
        if self.file_manager.save_summary(text):
            return True
        else:
            self.label_status.configure(text="Error saving file", text_color="red")
            return False

    def _load_settings(self) -> dict:
        """Load app settings from settings.json."""
        settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        default_settings = {
            "auto_fetch_urls": False,  # Auto-fetch URLs in Direct Audio mode
        }
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    saved = json.load(f)
                    # Merge with defaults to handle new settings
                    return {**default_settings, **saved}
        except Exception:
            pass
        return default_settings

    def _save_settings(self):
        """Save app settings to settings.json."""
        settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        try:
            with open(settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def open_settings_dialog(self):
        """Open the settings dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Settings")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.lift()
        dialog.grab_set()

        dialog.grid_columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(dialog, text="App Settings", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(20, 10), sticky="w"
        )

        # Settings frame
        settings_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        settings_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        settings_frame.grid_columnconfigure(0, weight=1)

        # Auto-fetch URLs toggle
        auto_fetch_var = ctk.BooleanVar(value=self.settings.get("auto_fetch_urls", False))
        chk_auto_fetch = ctk.CTkCheckBox(
            settings_frame,
            text="Auto-fetch URLs in Direct Audio mode",
            variable=auto_fetch_var
        )
        chk_auto_fetch.grid(row=0, column=0, pady=5, sticky="w")

        ctk.CTkLabel(
            settings_frame,
            text="When enabled, if the textbox contains just a URL,\nDirect Audio will automatically fetch the article.",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).grid(row=1, column=0, pady=(0, 15), sticky="w")

        # Save button
        def save_and_close():
            self.settings["auto_fetch_urls"] = auto_fetch_var.get()
            self._save_settings()
            dialog.destroy()
            self.label_status.configure(text="Settings saved", text_color="green")

        ctk.CTkButton(dialog, text="Save", command=save_and_close, fg_color="green").grid(
            row=2, column=0, padx=20, pady=20
        )

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
                    def update_ui():
                        self.textbox.delete("0.0", "end")
                        self.textbox.insert("0.0", combined)
                        self._placeholder.place_forget()
                        dialog.destroy()
                        self.label_status.configure(
                            text=f"Fetched {success_count} article(s) ({len(combined)} chars). Use Direct Audio to clean and convert.",
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

    def _fetch_article_content(self, url: str) -> str:
        """Fetch and extract article body from URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }

            # Try requests first
            try:
                import requests
                response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                response.raise_for_status()
                html = response.text
            except Exception:
                # Fallback to urllib
                import urllib.request
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    html = response.read().decode('utf-8', errors='ignore')

            from bs4 import BeautifulSoup
            import re

            soup = BeautifulSoup(html, 'lxml')

            # Remove elements that are definitely not article content
            for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header',
                                       'aside', 'iframe', 'noscript', 'form', 'button']):
                tag.decompose()

            # Remove common non-content patterns by class/id
            remove_patterns = [
                'subscribe', 'newsletter', 'sidebar', 'comment', 'share',
                'social', 'related', 'recommended', 'footer', 'header',
                'navigation', 'nav-', 'menu', 'ad-', 'advertisement',
                'signup', 'sign-up', 'login', 'paywall', 'premium'
            ]
            for pattern in remove_patterns:
                for tag in soup.find_all(class_=lambda x: x and pattern in str(x).lower()):
                    tag.decompose()
                for tag in soup.find_all(id=lambda x: x and pattern in str(x).lower()):
                    tag.decompose()

            article_text = None

            # Platform-specific extraction
            # Substack
            if 'substack.com' in url or soup.find('div', class_='post-content'):
                content = soup.find('div', class_='body')
                if not content:
                    content = soup.find('div', class_='post-content')
                if not content:
                    content = soup.find('div', class_='available-content')
                if content:
                    article_text = content.get_text(separator='\n', strip=True)

            # Generic article selectors (priority order)
            if not article_text or len(article_text) < 200:
                selectors = [
                    ('article', {}),
                    ('div', {'class_': 'article-content'}),
                    ('div', {'class_': 'article-body'}),
                    ('div', {'class_': 'post-content'}),
                    ('div', {'class_': 'entry-content'}),
                    ('div', {'class_': 'content-body'}),
                    ('div', {'class_': 'story-body'}),
                    ('main', {}),
                    ('div', {'role': 'main'}),
                    ('div', {'class_': 'content'}),
                ]

                for tag, attrs in selectors:
                    if attrs:
                        content = soup.find(tag, **attrs)
                    else:
                        content = soup.find(tag)
                    if content:
                        text = content.get_text(separator='\n', strip=True)
                        if len(text) > 200:
                            article_text = text
                            break

            # Fallback: get largest text block
            if not article_text or len(article_text) < 200:
                # Find all paragraph containers
                all_divs = soup.find_all(['div', 'article', 'section'])
                best_text = ""
                for div in all_divs:
                    paragraphs = div.find_all('p')
                    if len(paragraphs) >= 3:  # At least 3 paragraphs
                        text = div.get_text(separator='\n', strip=True)
                        if len(text) > len(best_text):
                            best_text = text
                if best_text:
                    article_text = best_text

            # Clean up the text
            if article_text:
                # Remove multiple newlines
                article_text = re.sub(r'\n{3,}', '\n\n', article_text)
                # Remove common junk phrases
                junk_phrases = [
                    r'Subscribe.*?newsletter',
                    r'Sign up.*?free',
                    r'Click here to.*',
                    r'Share this.*',
                    r'Follow us on.*',
                    r'Read more:.*',
                    r'Related:.*',
                ]
                for phrase in junk_phrases:
                    article_text = re.sub(phrase, '', article_text, flags=re.IGNORECASE)

                return article_text.strip()

            return ""

        except Exception as e:
            print(f"Error fetching article: {e}")
            return ""

    def open_sources_editor(self):
        editor = ctk.CTkToplevel(self)
        editor.title("Edit News Sources")
        editor.geometry("750x600")
        editor.minsize(750, 520)
        editor.transient(self)
        editor.lift()
        
        lbl = ctk.CTkLabel(editor, text="Enable/disable sources and edit URLs:", font=ctk.CTkFont(weight="bold"))
        lbl.pack(pady=10, padx=10, anchor="w")

        container = ctk.CTkScrollableFrame(editor, width=700, height=350)
        container.pack(padx=10, pady=(10, 5), fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)

        sources_json = os.path.join(os.path.dirname(__file__), "sources.json")
        channels_file = os.path.join(os.path.dirname(__file__), "channels.txt")
        import json
        sources = []
        if os.path.exists(sources_json):
            try:
                data = json.load(open(sources_json))
                sources = data.get("sources", [])
            except Exception:
                sources = []
        if not sources:
            # fallback to channels.txt
            if os.path.exists(channels_file):
                with open(channels_file, "r", encoding="utf-8") as f:
                    sources = [{"url": ln.strip(), "enabled": True} for ln in f if ln.strip()]

        widgets = []
        for idx, src in enumerate(sources):
            var_enabled = ctk.BooleanVar(value=src.get("enabled", True))
            entry = ctk.CTkEntry(container)
            entry.insert(0, src.get("url", ""))
            chk = ctk.CTkCheckBox(container, text="Enabled", variable=var_enabled)
            entry.grid(row=idx, column=0, padx=5, pady=5, sticky="ew")
            chk.grid(row=idx, column=1, padx=5, pady=5)
            widgets.append((entry, var_enabled))

        def add_source():
            idx = len(widgets)
            var_enabled = ctk.BooleanVar(value=True)
            entry = ctk.CTkEntry(container)
            chk = ctk.CTkCheckBox(container, text="Enabled", variable=var_enabled)
            entry.grid(row=idx, column=0, padx=5, pady=5, sticky="ew")
            chk.grid(row=idx, column=1, padx=5, pady=5)
            widgets.append((entry, var_enabled))

        def bulk_import():
            dlg = ctk.CTkToplevel(editor)
            dlg.title("Bulk Import Sources")
            dlg.geometry("500x400")
            ctk.CTkLabel(dlg, text="Paste one URL per line:").pack(pady=10)
            txt = ctk.CTkTextbox(dlg, width=460, height=280)
            txt.pack(padx=10, pady=10, fill="both", expand=True)
            def apply_import():
                lines = [ln.strip() for ln in txt.get("0.0", "end-1c").splitlines()]
                for ln in lines:
                    if not ln: continue
                    idx = len(widgets)
                    var_enabled = ctk.BooleanVar(value=True)
                    entry = ctk.CTkEntry(container)
                    entry.insert(0, ln)
                    chk = ctk.CTkCheckBox(container, text="Enabled", variable=var_enabled)
                    entry.grid(row=idx, column=0, padx=5, pady=5, sticky="ew")
                    chk.grid(row=idx, column=1, padx=5, pady=5)
                    widgets.append((entry, var_enabled))
                dlg.destroy()
            ctk.CTkButton(dlg, text="Import", command=apply_import).pack(pady=10)

        def select_all():
            for entry, var_enabled in widgets:
                var_enabled.set(True)
        
        def deselect_all():
            for entry, var_enabled in widgets:
                var_enabled.set(False)
        
        def save_sources():
            new_sources = []
            for entry, var_enabled in widgets:
                url = entry.get().strip()
                if url:
                    new_sources.append({"url": url, "enabled": bool(var_enabled.get())})
            try:
                json.dump({"sources": new_sources}, open(sources_json, "w"), indent=2)
                # also write channels.txt for compatibility
                with open(channels_file, "w", encoding="utf-8") as f:
                    f.write("\n".join([s["url"] for s in new_sources]))
                editor.destroy()
                self.label_status.configure(text="Sources updated.", text_color="green")
            except Exception as e:
                self.label_status.configure(text=f"Error saving sources: {e}", text_color="red")

        # Button row - always visible at bottom, stacked in two rows if needed
        btn_row = ctk.CTkFrame(editor, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(5, 15), side="bottom")
        
        # First row of buttons
        btn_row1 = ctk.CTkFrame(btn_row, fg_color="transparent")
        btn_row1.pack(fill="x", pady=(0, 5))
        
        ctk.CTkButton(btn_row1, text="Add Source", command=add_source, width=110).pack(side="left", padx=5)
        ctk.CTkButton(btn_row1, text="Bulk Import", command=bulk_import, width=110).pack(side="left", padx=5)
        ctk.CTkButton(btn_row1, text="Select All", command=select_all, fg_color="green", width=110).pack(side="left", padx=5)
        ctk.CTkButton(btn_row1, text="Deselect All", command=deselect_all, fg_color="gray", width=110).pack(side="left", padx=5)
        
        # Second row with Save button prominently placed
        btn_row2 = ctk.CTkFrame(btn_row, fg_color="transparent")
        btn_row2.pack(fill="x")
        
        ctk.CTkButton(btn_row2, text="Save Changes", command=save_sources, width=200, height=35, 
                     font=ctk.CTkFont(size=14, weight="bold")).pack(side="right", padx=5)

    def open_instructions_editor(self):
        """Open editor for custom summarization instructions."""
        editor = ctk.CTkToplevel(self)
        editor.title("Edit Custom Instructions")
        editor.geometry("800x650")
        editor.minsize(700, 500)
        editor.transient(self)
        editor.lift()
        
        lbl = ctk.CTkLabel(
            editor, 
            text="Customize how summaries are generated:", 
            font=ctk.CTkFont(weight="bold", size=14)
        )
        lbl.pack(pady=(15, 5), padx=15, anchor="w")
        
        help_text = ctk.CTkLabel(
            editor,
            text="Example: \"I'm a crypto trader interested in Bitcoin, DeFi, and AI. Include all price levels, technical indicators, and alpha.\"",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=750
        )
        help_text.pack(pady=(0, 10), padx=15, anchor="w")
        
        # Text area for custom instructions
        txt_frame = ctk.CTkFrame(editor)
        txt_frame.pack(padx=15, pady=10, fill="both", expand=True)
        
        instructions_text = ctk.CTkTextbox(txt_frame, width=750, height=400, font=ctk.CTkFont(size=13))
        instructions_text.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Load existing instructions
        instructions_file = os.path.join(os.path.dirname(__file__), "custom_instructions.txt")
        if os.path.exists(instructions_file):
            try:
                with open(instructions_file, "r", encoding="utf-8") as f:
                    instructions_text.insert("1.0", f.read())
            except Exception as e:
                self.label_status.configure(text=f"Error loading instructions: {e}", text_color="red")
        
        def save_instructions():
            content = instructions_text.get("1.0", "end-1c")
            try:
                with open(instructions_file, "w", encoding="utf-8") as f:
                    f.write(content)
                editor.destroy()
                self.label_status.configure(text="Custom instructions saved.", text_color="green")
            except Exception as e:
                self.label_status.configure(text=f"Error saving instructions: {e}", text_color="red")
        
        def clear_instructions():
            instructions_text.delete("1.0", "end")
        
        # Button row
        btn_frame = ctk.CTkFrame(editor, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(5, 15), side="bottom")
        
        ctk.CTkButton(btn_frame, text="Clear", command=clear_instructions, fg_color="gray", width=120).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Save Instructions", command=save_instructions, width=200, height=35,
                     font=ctk.CTkFont(size=14, weight="bold")).pack(side="right", padx=5)

    def _clear_selected_file(self):
        self.selected_file_paths = []
        if hasattr(self, "btn_transcribe"):
            self.btn_transcribe.configure(state="disabled")
        if hasattr(self, "files_combo"):
            self.files_combo.configure(values=["No files selected"])
            self.files_combo.set("No files selected")

    def upload_text_file(self):
        """Open file dialog and upload one or more text/audio files."""
        script_dir = os.path.dirname(__file__)
        file_paths = filedialog.askopenfilenames(
            initialdir=script_dir,
            filetypes=(("Supported files", "*.txt *.mp3 *.wav *.m4a"), ("Text files", "*.txt"), ("Audio files", "*.mp3 *.wav *.m4a"), ("All files", "*.*"))
        )

        if not file_paths:
            return

        self.selected_file_paths = list(file_paths)
        
        # Update combo
        count = len(file_paths)
        filenames = [os.path.basename(fp) for fp in file_paths]
        
        if count == 1:
            self.files_combo.configure(values=filenames)
            self.files_combo.set(filenames[0])
            self.label_status.configure(text="1 file selected. Press Transcribe.", text_color="blue")
        else:
            header = f"{count} files selected"
            self.files_combo.configure(values=[header] + filenames)
            self.files_combo.set(header)
            self.label_status.configure(text=f"{count} files selected. Press Transcribe.", text_color="blue")
            
        # Enable transcribe button
        self.btn_transcribe.configure(state="normal")

    def start_transcription(self):
        """Process selected files: transcribe audio and save to Transcriptions folder."""
        if not self.selected_file_paths:
            self.label_status.configure(text="No files selected.", text_color="orange")
            return

        # Check dependencies once
        has_audio = any(os.path.splitext(fp)[1].lower() in {".mp3", ".wav", ".m4a"} for fp in self.selected_file_paths)
        if has_audio:
            if not self.transcription_ffmpeg_enabled or not self.transcription_whisper_installed:
                self.label_status.configure(text="Transcription dependencies missing.", text_color="red")
                self.show_transcription_guide(
                    missing_ffmpeg=not self.transcription_ffmpeg_enabled,
                    missing_whisper=not self.transcription_whisper_installed
                )
                return

        self.btn_transcribe.configure(state="disabled")
        self.btn_upload_file.configure(state="disabled")
        
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
                        from transcriber import transcribe_audio
                        transcript = transcribe_audio(file_path, model_size="base")
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
                self.btn_upload_file.configure(state="normal")
                if processed_count > 0:
                    self.label_status.configure(text=f"Done! {processed_count} files saved to 'Transcriptions/'", text_color="green")
                    # Optionally open the folder?
                    # if sys.platform == "darwin": subprocess.run(["open", out_dir])
                else:
                    self.label_status.configure(text="Processing complete. No output generated.", text_color="orange")

            self.after(0, finish)

        threading.Thread(target=process_thread, daemon=True).start()
    def show_transcription_guide(self, missing_ffmpeg=False, missing_whisper=False):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Transcription Setup Guide")
        dlg.geometry("600x420")
        dlg.minsize(600, 420)
        frame = ctk.CTkScrollableFrame(dlg)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        title = ctk.CTkLabel(frame, text="Enable Local Transcription (Whisper)", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(anchor="w", pady=(0,8))
        info = []
        info.append("This app uses faster-whisper (OpenAI Whisper) for offline speech-to-text.")
        if missing_whisper:
            info.append("• Python package missing: faster-whisper")
        if missing_ffmpeg:
            info.append("• System dependency missing: ffmpeg")
        info.append("")
        info.append("Install steps:")
        info.append("1) Python deps: pip install faster-whisper")
        info.append("2) ffmpeg:")
        info.append("   • macOS: brew install ffmpeg")
        info.append("   • Windows: choco install ffmpeg (or download from ffmpeg.org)")
        info.append("   • Linux: sudo apt install ffmpeg")
        info.append("")
        info.append("After installation, restart the app and try Upload File again.")
        text = ctk.CTkTextbox(frame, width=560, height=300)
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
        self.btn_get_yt_news.configure(state="disabled")
        self.btn_edit_sources.configure(state="disabled")
        self.btn_upload_file.configure(state="disabled")
        self.label_status.configure(text=f"Running {script_name}...", text_color="orange")
        
        # Save summary before running (except for get_youtube_news)
        if script_name != "get_youtube_news.py" and not self.save_summary():
            self.enable_buttons()
            return
        
        def completion_handler(success):
            """Handle completion of script execution."""
            if success and script_name == "get_youtube_news.py":
                self.load_current_summary()
            self.enable_buttons()
        
        self.audio_generator.run_script(
            script_name, 
            output_name, 
            extra_args=extra_args,
            env_vars=env_vars,
            completion_callback=completion_handler
        )

    def open_url_input_dialog(self, api_key):
        """Open dialog for entering specific video URLs."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Summarize Specific Videos")
        dialog.geometry("700x500")
        dialog.transient(self)
        dialog.geometry("800x600")
        dialog.minsize(800, 600)

        dialog.lift()
        dialog.grab_set()
        
        # Header
        header = ctk.CTkLabel(
            dialog, 
            text="📹 Enter YouTube Video URLs", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        header.pack(pady=(20, 10))
        
        # Instructions
        instructions = ctk.CTkLabel(
            dialog,
            text="Enter one or more YouTube video URLs (one per line):",
            font=ctk.CTkFont(size=12)
        )
        instructions.pack(pady=(0, 10))
        
        # URL text area
        url_frame = ctk.CTkFrame(dialog)
        url_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        url_textbox = ctk.CTkTextbox(url_frame, width=650, height=300, font=ctk.CTkFont(size=12))
        url_textbox.pack(padx=10, pady=10, fill="both", expand=True)
        url_textbox.insert("0.0", "https://www.youtube.com/watch?v=")
        
        # Info label
        info_text = "Each video will be summarized using the selected AI model. Videos without transcripts will be skipped."
        info_label = ctk.CTkLabel(dialog, text=info_text, font=ctk.CTkFont(size=10), text_color="gray", wraplength=650)
        info_label.pack(pady=(0, 10))
        
        # Button frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        def process_urls():
            urls_text = url_textbox.get("0.0", "end").strip()
            if not urls_text:
                return
            
            # Parse URLs (one per line)
            urls = [line.strip() for line in urls_text.split('\n') if line.strip() and ('youtube.com' in line or 'youtu.be' in line)]
            
            if not urls:
                self.label_status.configure(text="Error: No valid YouTube URLs found.", text_color="red")
                dialog.destroy()
                return
            
            # Map user-friendly model name to API model name
            model_mapping = {
                "Fast (FREE)": "gemini-2.5-flash",
                "Balanced (FREE)": "gemini-2.5-flash",
                "Best (FREE, 50/day)": "gemini-2.5-pro"
            }
            selected_model = model_mapping.get(self.model_var.get(), "gemini-2.5-flash")
            
            # Save API key
            self.save_api_key(api_key)
            
            # Build args for get_youtube_news.py with --urls
            extra = ["--urls"] + urls + ["--model", selected_model]
            output_desc = f"specific video list for {len(urls)} URL(s)"
            
            dialog.destroy()
            
            # Run the script
            env_vars = {"GEMINI_API_KEY": api_key}
            self.run_script("get_youtube_news.py", "specific-video-list.txt", extra_args=extra, env_vars=env_vars)
        
        def cancel():
            dialog.destroy()
        
        btn_cancel = ctk.CTkButton(btn_frame, text="Cancel", command=cancel, fg_color="gray", width=120)
        btn_cancel.pack(side="left", padx=10)
        
        btn_process = ctk.CTkButton(btn_frame, text="Summarize Videos", command=process_urls, width=150)
        btn_process.pack(side="left", padx=10)
    
    def enable_buttons(self):
        """Re-enable all control buttons."""
        self.btn_fast.configure(state="normal")
        self.btn_quality.configure(state="normal")
    def open_specific_urls_dialog(self):
        api_key = self.gemini_key_entry.get().strip()
        if not api_key:
            self.label_status.configure(text="Error: Gemini API Key is required.", text_color="red")
            return
        self.open_url_input_dialog(api_key)

        self.btn_get_yt_news.configure(state="normal")
        self.btn_edit_sources.configure(state="normal")
        self.btn_upload_file.configure(state="normal")

    def start_fast_generation(self):
        if self.direct_audio_var.get():
            self.show_direct_audio_dialog("fast")
        else:
            text = self.textbox.get("0.0", "end-1c").strip()
            filename = self.generate_audio_filename(text, "mp3")
            self.run_script("make_audio_fast.py", filename, extra_args=["--output", filename])

    def start_quality_generation(self):
        if self.direct_audio_var.get():
            self.show_direct_audio_dialog("quality")
        else:
            text = self.textbox.get("0.0", "end-1c").strip()
            filename = self.generate_audio_filename(text, "wav")
            voice = self.voice_var.get()
            self.run_script("make_audio_quality.py", filename, extra_args=["--voice", voice, "--output", filename])

    def show_direct_audio_dialog(self, generation_type):
        """Show dialog to preview and edit cleaned text before audio generation."""
        raw_text = self.textbox.get("0.0", "end-1c").strip()
        if not raw_text:
            self.label_status.configure(text="No text to convert", text_color="red")
            return

        # Check if auto-fetch URLs is enabled and text contains URLs
        if self.settings.get("auto_fetch_urls", False):
            # Extract all URLs from the text (one per line or space-separated)
            import re
            url_pattern = r'https?://[^\s]+'
            urls = re.findall(url_pattern, raw_text)

            if urls:
                self.label_status.configure(text=f"Fetching {len(urls)} article(s)...", text_color="orange")
                self.update()

                # Fetch all articles
                all_content = []
                for i, url in enumerate(urls):
                    self.label_status.configure(text=f"Fetching article {i+1}/{len(urls)}...", text_color="orange")
                    self.update()
                    print(f"[Fetch] Fetching URL {i+1}/{len(urls)}: {url[:60]}...")

                    fetched_content = self._fetch_article_content(url)
                    if fetched_content and len(fetched_content) > 100:
                        # Add separator between articles
                        if all_content:
                            all_content.append("\n\n---\n\n")
                        all_content.append(fetched_content)
                        print(f"[Fetch] Success: {len(fetched_content)} chars")
                    else:
                        print(f"[Fetch] Failed to fetch: {url[:60]}")

                if all_content:
                    raw_text = "".join(all_content)
                    self.textbox.delete("0.0", "end")
                    self.textbox.insert("0.0", raw_text)
                    self._placeholder.place_forget()
                    self.label_status.configure(
                        text=f"Fetched {len([c for c in all_content if c != '\n\n---\n\n'])} article(s). Processing...",
                        text_color="green"
                    )
                else:
                    self.label_status.configure(
                        text="Failed to fetch articles. Paste content manually or use Fetch Article button.",
                        text_color="red"
                    )
                    return

        # Clear status when opening dialog
        self.label_status.configure(text="Ready", text_color="gray")

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
        status_label = ctk.CTkLabel(header_frame, text="Cleaning text for listening...", text_color="orange")
        status_label.grid(row=0, column=1, padx=20, sticky="e")

        # Text editor
        text_editor = ctk.CTkTextbox(dialog, font=ctk.CTkFont(size=13))
        text_editor.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        # Insert raw text initially (will be replaced with cleaned version)
        text_editor.insert("0.0", "Cleaning text for audio... please wait...")
        text_editor.configure(state="disabled")

        # Button frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        def on_convert():
            """Convert the edited text to audio."""
            cleaned_text = text_editor.get("0.0", "end-1c").strip()
            if not cleaned_text:
                status_label.configure(text="No text to convert", text_color="red")
                return

            # Save the cleaned text to the main textbox for audio generation
            self.textbox.delete("0.0", "end")
            self.textbox.insert("0.0", cleaned_text)

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
            self.label_status.configure(text="Ready", text_color="gray")
            dialog.destroy()

        btn_cancel = ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", command=on_cancel)
        btn_cancel.grid(row=0, column=0, padx=5, sticky="ew")

        btn_use_raw = ctk.CTkButton(btn_frame, text="Use Raw Text", fg_color="orange", command=lambda: use_raw_text())
        btn_use_raw.grid(row=0, column=1, padx=5, sticky="ew")

        btn_convert = ctk.CTkButton(btn_frame, text="Convert to Audio", fg_color="green", command=on_convert, state="disabled")
        btn_convert.grid(row=0, column=2, padx=5, sticky="ew")

        def use_raw_text():
            """Use the original raw text without cleaning."""
            text_editor.configure(state="normal")
            text_editor.delete("0.0", "end")
            text_editor.insert("0.0", raw_text)
            status_label.configure(text="Using raw text (no cleaning)", text_color="orange")
            btn_convert.configure(state="normal")

        # Start cleaning in background
        def clean_async():
            api_key = self.gemini_key_entry.get().strip()
            if not api_key:
                dialog.after(0, lambda: status_label.configure(text="No API key - using raw text", text_color="orange"))
                dialog.after(0, lambda: use_raw_text())
                return

            cleaned = self.clean_text_for_listening(raw_text, api_key)

            def update_ui():
                text_editor.configure(state="normal")
                text_editor.delete("0.0", "end")
                text_editor.insert("0.0", cleaned)
                status_label.configure(text="Text cleaned and ready for review", text_color="green")
                btn_convert.configure(state="normal")

            dialog.after(0, update_ui)

        threading.Thread(target=clean_async, daemon=True).start()

    def clean_text_for_listening(self, text, api_key):
        """Use Gemini to clean and format text for audio listening."""
        import google.generativeai as genai

        try:
            genai.configure(api_key=api_key)

            # Use the selected model
            model_choice = self.model_var.get()
            if "Best" in model_choice:
                model_name = "gemini-1.5-pro"
            elif "Balanced" in model_choice:
                model_name = "gemini-1.5-flash"
            else:
                model_name = "gemini-2.0-flash-exp"

            model = genai.GenerativeModel(model_name)

            prompt = """Clean and format this text for audio listening. Your task:

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
   - Ensure sentences flow naturally when spoken

Return ONLY the cleaned text, nothing else.

TEXT TO CLEAN:
\"\"\"
{text}
\"\"\"
""".format(text=text)

            response = model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            print(f"Error cleaning text: {e}")
            return text  # Return original text on error

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
        # Count enabled channels
        import json
        sources_json = os.path.join(os.path.dirname(__file__), "sources.json")
        enabled_channels = 0
        
        if os.path.exists(sources_json):
            try:
                data = json.load(open(sources_json))
                enabled_channels = sum(1 for s in data.get("sources", []) if s.get("enabled", True))
            except:
                enabled_channels = 1
        else:
            channels_file = os.path.join(os.path.dirname(__file__), "channels.txt")
            if os.path.exists(channels_file):
                with open(channels_file, "r") as f:
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
        model_name = self.model_var.get()
        if "50/day" in model_name:  # Pro model
            free_limit = 50
            cost_per_1k = 1.25  # $1.25 per 1000 requests for Pro
        else:  # Flash
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
    
    def get_youtube_news_from_channels(self):
        api_key = self.gemini_key_entry.get().strip()
        if not api_key:
            self.label_status.configure(text="Error: Gemini API Key is required.", text_color="red")
            return
        
        mode = self.mode_var.get()
        value = self.entry_value.get().strip()
        
        # Specific URLs moved to dedicated button dialog
        
        # Handle Hours/Days/Videos modes
        if not value.isdigit():
            value = "7"
            
        self.save_api_key(api_key)
        
        # Map user-friendly model name to API model name
        model_mapping = {
            "Fast (FREE)": "gemini-2.5-flash",
            "Balanced (FREE)": "gemini-2.5-flash",
            "Best (FREE, 50/day)": "gemini-2.5-pro"
        }
        selected_model = model_mapping.get(self.model_var.get(), "gemini-2.5-flash")
        
        # Build args based on range checkbox and mode
        extra = []
        output_desc = ""
        if self.range_var.get():
            start = self.start_date_entry.get().strip()
            end = self.end_date_entry.get().strip()
            if start and end:
                extra = ["--start", start, "--end", end, "--model", selected_model]
                output_desc = f"summaries from {start} to {end}"
            else:
                # Fallback to hours/days
                if mode == "Hours":
                    hours = int(value) if value.isdigit() else 24
                    extra = ["--hours", str(hours), "--model", selected_model]
                    output_desc = f"summary for last {hours} hour(s)"
                else:
                    days = int(value) if value.isdigit() else 1
                    extra = ["--days", str(days), "--model", selected_model]
                    output_desc = f"summary for last {days} day(s)"
        else:
            if mode == "Hours":
                hours = int(value) if value.isdigit() else 24
                extra = ["--hours", str(hours), "--model", selected_model]
                output_desc = f"summary for last {hours} hour(s)"
            else:
                days = int(value) if value.isdigit() else 1
                extra = ["--days", str(days), "--model", selected_model]
                output_desc = f"summary for last {days} day(s)"
        
        # Estimate usage and show confirmation dialog
        usage = self.estimate_api_usage()
        
        # Show confirmation dialog with usage estimate
        self.show_usage_confirmation(usage, extra, output_desc, api_key, selected_model)
    
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
        script_dir = os.path.dirname(__file__)
        
        # Find all summary files in Week_* folders
        files = []
        for week_folder in sorted(glob.glob(os.path.join(script_dir, "Week_*"))):
            if os.path.isdir(week_folder):
                week_summaries = sorted([
                    os.path.join(week_folder, f) 
                    for f in os.listdir(week_folder) 
                    if f.startswith("summary_") and f.endswith(".txt")
                ])
                files.extend(week_summaries)
        
        if not files:
            self.label_status.configure(text="No per-date summaries found in Week folders.", text_color="orange")
            return
            
        dlg = ctk.CTkToplevel(self)
        dlg.title("Select Dates to Convert")
        dlg.geometry("500x500")
        frame = ctk.CTkScrollableFrame(dlg, width=460, height=380)
        frame.pack(padx=10, pady=10, fill="both", expand=True)
        checks = []
        for i, filepath in enumerate(files):
            filename = os.path.basename(filepath)
            date_label = filename.replace("summary_", "").replace(".txt", "")
            var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(frame, text=date_label, variable=var).grid(row=i, column=0, sticky="w", padx=8, pady=4)
            checks.append((filepath, var))
            
        btn_frame = ctk.CTkFrame(dlg)
        btn_frame.pack(pady=10)
        
        def select_all():
            for filepath, var in checks:
                var.set(True)
        
        def deselect_all():
            for filepath, var in checks:
                var.set(False)
        
        ctk.CTkButton(btn_frame, text="Select All", command=select_all, fg_color="green", width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Deselect All", command=deselect_all, fg_color="gray", width=100).pack(side="left", padx=5)
        
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
                script_dir = os.path.dirname(__file__)
                python_exe = sys.executable
                log_path = os.path.join(script_dir, "gui_log.txt")
                
                total = len(selected)
                for idx, filepath in enumerate(selected, 1):
                    try:
                        filename = os.path.basename(filepath)
                        date_str = filename.replace("summary_", "").replace(".txt", "")
                        week_folder = os.path.dirname(filepath)
                        output_file = os.path.join(week_folder, f"audio_quality_{date_str}.wav")
                        
                        # Update GUI frequently
                        self.after(0, lambda d=date_str, i=idx, t=total: self.label_status.configure(
                            text=f"Converting {i}/{t}: {d}...", text_color=("gray10", "#DCE4EE")))
                        
                        cmd = [python_exe, os.path.join(script_dir, "make_audio_quality.py"), 
                               "--input", filepath, "--voice", voice, "--output", output_file]
                        
                        # Enhanced logging for debugging
                        with open(log_path, "a", encoding="utf-8") as log:
                            log.write(f"\n{'='*60}\n")
                            log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Converting {idx}/{total}: {date_str}\n")
                            log.write(f"Input: {filepath}\n")
                            log.write(f"Output: {output_file}\n")
                            log.write(f"Command: {' '.join(cmd)}\n")
                            log.flush()
                        
                        start_time = time.time()
                        result = subprocess.run(cmd, capture_output=True, text=True, cwd=script_dir, timeout=3600)
                        elapsed = time.time() - start_time
                        
                        # Log result details
                        with open(log_path, "a", encoding="utf-8") as log:
                            log.write(f"Return code: {result.returncode}\n")
                            log.write(f"Elapsed time: {elapsed:.1f}s\n")
                            if result.stdout:
                                log.write(f"STDOUT:\n{result.stdout}\n")
                            if result.stderr:
                                log.write(f"STDERR:\n{result.stderr}\n")
                            log.write(f"Output file exists: {os.path.exists(output_file)}\n")
                            if os.path.exists(output_file):
                                log.write(f"Output file size: {os.path.getsize(output_file)} bytes\n")
                            log.flush()
                        
                        if result.returncode != 0:
                            error_msg = f"Error converting {date_str}: {result.stderr[:100]}"
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
                        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                            file_size_mb = os.path.getsize(output_file) / (1024*1024)
                            with open(log_path, "a", encoding="utf-8") as log:
                                log.write(f"TIMEOUT but file created: {file_size_mb:.1f}MB\n")
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
            
            threading.Thread(target=task, daemon=True).start()

                
        ctk.CTkButton(btn_frame, text="Convert", command=do_convert, width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", command=dlg.destroy, width=100).pack(side="left", padx=5)
    def convert_summaries_to_audio(self, files):
        voice = self.voice_var.get()
        def task():
            try:
                script_dir = os.path.dirname(__file__)
                python_exe = "/usr/bin/env python3" if getattr(sys, "frozen", False) else sys.executable
                for f in files:
                    date = os.path.basename(f).split("_")[1].replace(".txt", "")
                    out = os.path.join(script_dir, f"daily_{date}.wav")
                    subprocess.run([python_exe, os.path.join(script_dir, "make_audio_quality.py"), "--voice", voice, "--textfile", f, "--output", out], capture_output=True, text=True, cwd=script_dir)
                self.after(0, lambda: self.label_status.configure(text="Audio conversion complete.", text_color="green"))
            except Exception as e:
                self.after(0, lambda: self.label_status.configure(text=f"Error converting: {e}", text_color="red"))
        threading.Thread(target=task, daemon=True).start()

        script_dir = os.path.dirname(__file__)
        if sys.platform == "darwin": subprocess.run(["open", script_dir])
        elif sys.platform == "win32": os.startfile(script_dir)
        else: subprocess.run(["xdg-open", script_dir])

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
        """Toggle the news summary text area visibility."""
        if self.text_expanded:
            # Collapse: hide content
            self.text_content.grid_remove()
            self.text_toggle_btn.configure(text="Expand")
            self.text_expanded = False
        else:
            # Expand: show content
            self.text_content.grid()
            self.text_toggle_btn.configure(text="Collapse")
            self.text_expanded = True

    def toggle_extract_section(self):
        """Toggle the data extraction section visibility."""
        if self.extract_content.winfo_ismapped():
            self.extract_content.grid_remove()
            self.extract_toggle_btn.configure(text="Expand")
        else:
            self.extract_content.grid()
            self.extract_toggle_btn.configure(text="Collapse")

    def set_extract_mode(self, mode):
        """Switch between URL and HTML extraction modes."""
        self.extract_mode_var.set(mode)
        if mode == "url":
            self.btn_tab_url.configure(fg_color=None)  # Use default color
            self.btn_tab_html.configure(fg_color="gray")
            self.url_input_frame.grid()
            self.html_input_frame.grid_remove()
        else:
            self.btn_tab_url.configure(fg_color="gray")
            self.btn_tab_html.configure(fg_color=None)
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
            url = self.extract_url_entry.get().strip()
            if not url:
                self.label_status.configure(text="Please enter a URL to extract.", text_color="orange")
                return
            if not url.startswith("http"):
                url = "https://" + url
        else:
            html = self.extract_html_text.get("1.0", "end-1c").strip()
            if not html:
                self.label_status.configure(text="Please paste HTML content to extract.", text_color="orange")
                return

        # Get config
        config_name = self.extract_config_var.get()
        enrich_grid = self.grid_enrich_var.get()
        research_articles = self.research_articles_var.get()
        api_key = self.gemini_key_entry.get().strip()  # For LLM analysis

        # Disable button during extraction
        self.btn_extract.configure(state="disabled", text="Extracting...")
        self.label_status.configure(text="Extracting links...", text_color="orange")

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
                    items = processor.process_url(url, custom_instructions)
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

if __name__ == "__main__":
    app = AudioBriefingApp()
    app.mainloop()

