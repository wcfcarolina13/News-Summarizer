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

        # Fetch options row (limit and date range) - similar to YouTube section
        fetch_opts_frame = ctk.CTkFrame(self.extract_content, fg_color="transparent")
        fetch_opts_frame.grid(row=3, column=0, sticky="ew", pady=5)

        ctk.CTkLabel(fetch_opts_frame, text="Fetch:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))

        self.extract_limit_entry = ctk.CTkEntry(fetch_opts_frame, width=50, placeholder_text="All")
        self.extract_limit_entry.pack(side="left", padx=(0, 5))

        ctk.CTkLabel(fetch_opts_frame, text="items").pack(side="left", padx=(0, 15))

        # Date range controls
        self.extract_range_var = ctk.BooleanVar(value=False)
        self.chk_extract_range = ctk.CTkCheckBox(fetch_opts_frame, text="Date range", variable=self.extract_range_var, command=self.on_toggle_extract_range)
        self.chk_extract_range.pack(side="left", padx=(0, 10))

        self.extract_start_date = ctk.CTkEntry(fetch_opts_frame, width=100, placeholder_text="Start YYYY-MM-DD")
        self.extract_start_date.pack(side="left", padx=(0, 2))

        self.btn_extract_start_cal = ctk.CTkButton(fetch_opts_frame, width=28, text="📅", command=self.open_extract_start_calendar)
        self.btn_extract_start_cal.pack(side="left", padx=(0, 10))

        self.extract_end_date = ctk.CTkEntry(fetch_opts_frame, width=100, placeholder_text="End YYYY-MM-DD")
        self.extract_end_date.pack(side="left", padx=(0, 2))

        self.btn_extract_end_cal = ctk.CTkButton(fetch_opts_frame, width=28, text="📅", command=self.open_extract_end_calendar)
        self.btn_extract_end_cal.pack(side="left")

        # Initialize date range state
        self.on_toggle_extract_range()

        # Extract button
        self.btn_extract = ctk.CTkButton(self.extract_content, text="Extract Links", command=self.start_extraction, fg_color="green")
        self.btn_extract.grid(row=4, column=0, sticky="ew", pady=(10, 5))

        # Results section (hidden until extraction)
        self.extract_results_frame = ctk.CTkFrame(self.extract_content)
        self.extract_results_frame.grid(row=5, column=0, sticky="ew", pady=5)
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

        # Status and Tutorial row
        status_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        status_frame.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)

        self.label_status = ctk.CTkLabel(status_frame, text="Ready", text_color=("gray10", "#DCE4EE"), font=("Arial", 14, "bold"))
        self.label_status.grid(row=0, column=0, sticky="w")

        self.btn_tutorial = ctk.CTkButton(
            status_frame, text="? Tutorial", width=80,
            fg_color=("gray70", "gray30"), hover_color=("gray60", "gray40"),
            command=self.start_tutorial
        )
        self.btn_tutorial.grid(row=0, column=1, sticky="e")

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

    def on_toggle_extract_range(self):
        """Toggle date range fields for data extraction."""
        use_range = bool(self.extract_range_var.get())
        state = "normal" if use_range else "disabled"
        try:
            self.extract_start_date.configure(state=state)
            self.extract_end_date.configure(state=state)
            self.btn_extract_start_cal.configure(state=state)
            self.btn_extract_end_cal.configure(state=state)
        except Exception:
            pass

    def open_extract_start_calendar(self):
        """Open calendar for extraction start date."""
        self._open_calendar_for(self.extract_start_date, is_extract=True)

    def open_extract_end_calendar(self):
        """Open calendar for extraction end date."""
        self._open_calendar_for(self.extract_end_date, is_extract=True)

    def _open_calendar_for(self, target_entry, is_extract=False):
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
                # Enable the appropriate date range checkbox
                if is_extract:
                    self.extract_range_var.set(True)
                    self.on_toggle_extract_range()
                else:
                    self.range_var.set(True)
                    self.on_toggle_range()
                dlg.destroy()
            for r,row in enumerate(cal, start=1):
                for c,d in enumerate(row):
                    txt = "" if d==0 else str(d)
                    ctk.CTkButton(grid, text=txt or " ", width=36, command=(lambda dd=d: click_day(dd))).grid(row=r, column=c, padx=2, pady=2)
        render()
        bar = ctk.CTkFrame(body); bar.pack(fill="x", pady=6)

        def go_prev():
            try:
                y, m = int(ent_y.get()), int(ent_m.get())
                m -= 1
                if m < 1:
                    m = 12
                    y -= 1
                ent_y.delete(0, "end"); ent_y.insert(0, str(y))
                ent_m.delete(0, "end"); ent_m.insert(0, str(m))
                render()
            except ValueError:
                pass

        def go_next():
            try:
                y, m = int(ent_y.get()), int(ent_m.get())
                m += 1
                if m > 12:
                    m = 1
                    y += 1
                ent_y.delete(0, "end"); ent_y.insert(0, str(y))
                ent_m.delete(0, "end"); ent_m.insert(0, str(m))
                render()
            except ValueError:
                pass

        ctk.CTkButton(bar, text="Prev", command=go_prev).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Next", command=go_next).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Close", fg_color="gray", command=dlg.destroy).pack(side="right", padx=6)

    def open_start_calendar(self):
        self._open_calendar_for(self.start_date_entry)

    def open_end_calendar(self):
        self._open_calendar_for(self.end_date_entry)

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
                    print(f"[Fetch] Combined {len(all_content)} pieces, total {len(combined)} chars")
                    print(f"[Fetch] Combined preview: {combined[:200]}...")
                    def update_ui():
                        self.textbox.delete("0.0", "end")
                        self.textbox.insert("0.0", combined)
                        print(f"[Fetch] Inserted {len(combined)} chars into textbox")
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
        """Re-enable all control buttons and reset status."""
        self.btn_fast.configure(state="normal")
        self.btn_quality.configure(state="normal")
        self.btn_get_yt_news.configure(state="normal")
        self.btn_edit_sources.configure(state="normal")
        self.btn_upload_file.configure(state="normal")
        self.label_status.configure(text="Ready", text_color="green")

    def open_specific_urls_dialog(self):
        api_key = self.gemini_key_entry.get().strip()
        if not api_key:
            self.label_status.configure(text="Error: Gemini API Key is required.", text_color="red")
            return
        self.open_url_input_dialog(api_key)

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
                    separator = "\n\n---\n\n"
                    article_count = len([c for c in all_content if c != separator])
                    self.label_status.configure(
                        text=f"Fetched {article_count} article(s). Processing...",
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
        """Clean a single article using Gemini."""
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

        try:
            response = model.generate_content(prompt)
            return response.text.strip()
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

1. **YouTube Mode** - Summarize videos from channels you follow
2. **Direct Audio Mode** - Convert any text or article to audio

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
                "title": "Step 3: YouTube News Mode",
                "content": """**The 'Get YouTube News' Button** (highlighted)

This is the traditional workflow for summarizing YouTube videos.

**How it works:**

1. **Edit Sources** - Click this first to add YouTube channels you want to follow

2. **Set the timeframe** - Use the number field and dropdown:
   • "7 Days" = videos from the past week
   • "24 Hours" = just today's videos
   • "10 Videos" = the 10 most recent videos

3. **Click 'Get YouTube News'** - The AI will:
   • Find recent videos from your channels
   • Fetch their transcripts
   • Create a summary of all the content

4. The summary appears in the text area below

**Tip:** Start with just 1-2 channels and a few days to test it out.""",
                "highlight": "btn_get_yt_news"
            },
            {
                "title": "Step 4: The Text Area",
                "content": """**The Main Text Area** (highlighted)

This is where all your content lives - summaries, articles, or text you paste in.

**What you can do here:**

• **View** summaries generated by the AI
• **Edit** content before converting to audio
• **Paste** your own text or article URLs
• **Type** anything you want to convert to audio

**The buttons above the text area:**

• **Fetch Article** - Opens a window to fetch multiple article URLs at once
• **Settings** - Configure options like auto-fetch for URLs
• **Collapse** - Hide the text area to save space

**Pro Tip:** You can paste multiple URLs in the Fetch Article dialog - one per line - and it will fetch all of them!""",
                "highlight": "textbox"
            },
            {
                "title": "Step 5: Direct Audio Mode (Easiest Way!)",
                "content": """**The 'Direct Audio' Checkbox**

This is the simplest way to use the app!

**How Direct Audio works:**

1. Check the **'Direct Audio'** checkbox (below the audio buttons)
2. Paste text OR article URLs in the text area
3. Click either audio button - done!

**What's different from YouTube mode?**

• No summarization - converts exactly what's in the text area
• Perfect for articles you want to listen to in full
• Works with plain text or fetched article content

**When to use Direct Audio:**

• You have an article you want to listen to
• You pasted text from somewhere
• You want the full content, not a summary

**When to use YouTube mode:**

• You want AI to summarize multiple videos
• You're catching up on channel content""",
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

1. Paste your API key and click 💾 to save
2. Check the 'Direct Audio' checkbox
3. Click 'Fetch Article' and paste an article URL
4. Click 'Fetch All'
5. Click 'Generate Fast' or 'Generate Quality'
6. Click 'Open Folder' to find your audio file

**Keyboard shortcuts:**
• The app remembers your API key
• Your last settings are preserved

**Getting Help:**
• Click **'? Tutorial'** anytime to restart this guide
• Check the terminal/console window for detailed logs
• See README.md for full documentation

**Need to see this again?**
Click the '? Tutorial' button next to the status bar!""",
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
                        canvas = self.main_scroll._parent_canvas

                        # Get widget position relative to the scrollable content
                        widget_y = widget.winfo_y()
                        widget_height = widget.winfo_height()

                        # Get the parent frames to calculate total offset
                        parent = widget.master
                        while parent and parent != self.main_scroll:
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
                            self.main_scroll._parent_canvas.yview_moveto(0)
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
        script_dir = os.path.dirname(__file__)
        archive_dir = os.path.join(script_dir, "Archive")

        # Find all summary files in Week_* folders (excluding Archive)
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
        dlg.geometry("550x550")

        # Main scrollable frame for checkboxes
        frame = ctk.CTkScrollableFrame(dlg, width=510, height=380)
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        checks = []
        for i, filepath in enumerate(files):
            filename = os.path.basename(filepath)
            date_label = filename.replace("summary_", "").replace(".txt", "")
            week_folder_name = os.path.basename(os.path.dirname(filepath))
            var = ctk.BooleanVar(value=False)  # Default to unchecked for safety
            ctk.CTkCheckBox(frame, text=f"{date_label} ({week_folder_name})", variable=var).grid(row=i, column=0, sticky="w", padx=8, pady=4)
            checks.append((filepath, var))

        # Selection buttons frame
        select_btn_frame = ctk.CTkFrame(dlg)
        select_btn_frame.pack(pady=5)

        def select_all():
            for filepath, var in checks:
                var.set(True)

        def deselect_all():
            for filepath, var in checks:
                var.set(False)

        ctk.CTkButton(select_btn_frame, text="Select All", command=select_all, fg_color="green", width=100).pack(side="left", padx=5)
        ctk.CTkButton(select_btn_frame, text="Deselect All", command=deselect_all, fg_color="gray", width=100).pack(side="left", padx=5)

        # Action buttons frame
        action_btn_frame = ctk.CTkFrame(dlg)
        action_btn_frame.pack(pady=10)

        def do_archive():
            selected = [filepath for filepath, v in checks if v.get()]
            if not selected:
                return

            # Confirmation dialog
            confirm = ctk.CTkToplevel(dlg)
            confirm.title("Confirm Archive")
            confirm.geometry("400x150")
            confirm.transient(dlg)
            confirm.grab_set()

            ctk.CTkLabel(confirm, text=f"Are you sure you want to archive {len(selected)} folder(s)?",
                        font=ctk.CTkFont(size=14)).pack(pady=20)
            ctk.CTkLabel(confirm, text="Archived folders can be restored from the Archive.",
                        font=ctk.CTkFont(size=12), text_color="gray").pack()

            btn_confirm_frame = ctk.CTkFrame(confirm)
            btn_confirm_frame.pack(pady=20)

            def confirm_archive():
                confirm.destroy()
                # Create archive directory if needed
                os.makedirs(archive_dir, exist_ok=True)

                archived_count = 0
                for filepath in selected:
                    try:
                        week_folder = os.path.dirname(filepath)
                        week_folder_name = os.path.basename(week_folder)
                        dest_folder = os.path.join(archive_dir, week_folder_name)

                        # Move entire week folder to archive
                        if os.path.exists(week_folder) and not os.path.exists(dest_folder):
                            shutil.move(week_folder, dest_folder)
                            archived_count += 1
                    except Exception as e:
                        print(f"Error archiving {filepath}: {e}")

                dlg.destroy()
                self.label_status.configure(text=f"Archived {archived_count} folder(s).", text_color="green")

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

        ctk.CTkButton(action_btn_frame, text="Convert", command=do_convert, width=100).pack(side="left", padx=5)
        ctk.CTkButton(action_btn_frame, text="Archive Selected", command=do_archive, fg_color="orange", width=120).pack(side="left", padx=5)
        ctk.CTkButton(action_btn_frame, text="View Archive", command=lambda: self.view_archive(dlg), fg_color="#5a5a5a", width=100).pack(side="left", padx=5)
        ctk.CTkButton(action_btn_frame, text="Cancel", fg_color="gray", command=dlg.destroy, width=100).pack(side="left", padx=5)

    def view_archive(self, parent_dlg=None):
        """Show dialog to view and unarchive folders from the Archive."""
        script_dir = os.path.dirname(__file__)
        archive_dir = os.path.join(script_dir, "Archive")

        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir, exist_ok=True)

        # Find all Week_* folders in Archive
        archived_folders = sorted([
            os.path.join(archive_dir, f)
            for f in os.listdir(archive_dir)
            if f.startswith("Week_") and os.path.isdir(os.path.join(archive_dir, f))
        ])

        dlg = ctk.CTkToplevel(self)
        dlg.title("Archive")
        dlg.geometry("500x450")
        if parent_dlg:
            dlg.transient(parent_dlg)

        if not archived_folders:
            ctk.CTkLabel(dlg, text="Archive is empty.", font=ctk.CTkFont(size=14)).pack(pady=50)
            ctk.CTkButton(dlg, text="Close", command=dlg.destroy, width=100).pack(pady=20)
            return

        ctk.CTkLabel(dlg, text="Archived Folders", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        frame = ctk.CTkScrollableFrame(dlg, width=460, height=280)
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        checks = []
        for i, folder_path in enumerate(archived_folders):
            folder_name = os.path.basename(folder_path)
            # Count files in folder
            file_count = len([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))])
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(frame, text=f"{folder_name} ({file_count} files)", variable=var).grid(row=i, column=0, sticky="w", padx=8, pady=4)
            checks.append((folder_path, var))

        # Selection buttons
        select_btn_frame = ctk.CTkFrame(dlg)
        select_btn_frame.pack(pady=5)

        def select_all():
            for path, var in checks:
                var.set(True)

        def deselect_all():
            for path, var in checks:
                var.set(False)

        ctk.CTkButton(select_btn_frame, text="Select All", command=select_all, fg_color="green", width=100).pack(side="left", padx=5)
        ctk.CTkButton(select_btn_frame, text="Deselect All", command=deselect_all, fg_color="gray", width=100).pack(side="left", padx=5)

        # Action buttons
        action_btn_frame = ctk.CTkFrame(dlg)
        action_btn_frame.pack(pady=10)

        def do_unarchive():
            selected = [path for path, v in checks if v.get()]
            if not selected:
                return

            # Confirmation dialog
            confirm = ctk.CTkToplevel(dlg)
            confirm.title("Confirm Unarchive")
            confirm.geometry("400x150")
            confirm.transient(dlg)
            confirm.grab_set()

            ctk.CTkLabel(confirm, text=f"Are you sure you want to restore {len(selected)} folder(s)?",
                        font=ctk.CTkFont(size=14)).pack(pady=20)
            ctk.CTkLabel(confirm, text="Folders will be moved back to the main directory.",
                        font=ctk.CTkFont(size=12), text_color="gray").pack()

            btn_confirm_frame = ctk.CTkFrame(confirm)
            btn_confirm_frame.pack(pady=20)

            def confirm_unarchive():
                confirm.destroy()
                restored_count = 0
                for folder_path in selected:
                    try:
                        folder_name = os.path.basename(folder_path)
                        dest_folder = os.path.join(script_dir, folder_name)

                        # Move folder back to main directory
                        if os.path.exists(folder_path) and not os.path.exists(dest_folder):
                            shutil.move(folder_path, dest_folder)
                            restored_count += 1
                    except Exception as e:
                        print(f"Error restoring {folder_path}: {e}")

                dlg.destroy()
                if parent_dlg:
                    parent_dlg.destroy()
                self.label_status.configure(text=f"Restored {restored_count} folder(s) from archive.", text_color="green")

            ctk.CTkButton(btn_confirm_frame, text="Yes, Restore", command=confirm_unarchive, fg_color="green", width=120).pack(side="left", padx=10)
            ctk.CTkButton(btn_confirm_frame, text="Cancel", command=confirm.destroy, fg_color="gray", width=100).pack(side="left", padx=10)

        ctk.CTkButton(action_btn_frame, text="Restore Selected", command=do_unarchive, fg_color="green", width=120).pack(side="left", padx=5)
        ctk.CTkButton(action_btn_frame, text="Close", command=dlg.destroy, fg_color="gray", width=100).pack(side="left", padx=5)
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
            # Refresh config list when expanding
            self._refresh_extraction_configs()

    def _refresh_extraction_configs(self):
        """Refresh the extraction config dropdown with current files."""
        configs = self._get_extraction_configs()
        current = self.extract_config_var.get()
        self.extract_config_combo.configure(values=configs)
        # Keep current selection if still valid
        if current in configs:
            self.extract_config_var.set(current)
        else:
            self.extract_config_var.set("Default")

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

    def _get_data_processor(self, fetch_limit=0, start_date="", end_date=""):
        """Get or create the data processor with updated config."""
        config = ExtractionConfig(
            resolve_redirects=False,  # Speed up by disabling redirect resolution
            strip_tracking_params=True,
            fetch_limit=fetch_limit,
            start_date=start_date,
            end_date=end_date
        )
        # Always create a new processor with the current config
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

        # Get fetch limit
        try:
            fetch_limit = int(self.extract_limit_entry.get().strip() or "0")
        except ValueError:
            fetch_limit = 0

        # Get date range if enabled
        start_date = ""
        end_date = ""
        if self.extract_range_var.get():
            start_date = self.extract_start_date.get().strip()
            end_date = self.extract_end_date.get().strip()

        # Disable button during extraction
        self.btn_extract.configure(state="disabled", text="Extracting...")
        self.label_status.configure(text="Extracting links...", text_color="orange")

        def extract_thread():
            try:
                processor = self._get_data_processor(fetch_limit, start_date, end_date)

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

        # Check if using RWA config for hyperlink format
        config_name = self.extract_config_var.get()
        use_hyperlink = config_name.lower() == "rwa"

        # Format as text
        lines = []
        for item in self.extracted_items:
            if use_hyperlink:
                # Hyperlink format for Google Docs: [Title](URL)
                lines.append(f"[{item.title}]({item.url})")
            else:
                line = f"{item.title}"
                if item.category:
                    line += f" [{item.category}]"
                line += f"\n  {item.url}"
                if item.custom_fields.get("grid_matched"):
                    grid_name = item.custom_fields.get("grid_entity_name", "")
                    line += f"\n  Grid: {grid_name}"
                lines.append(line)

        text = "\n\n".join(lines) if not use_hyperlink else "\n".join(lines)

        # Copy to clipboard
        self.clipboard_clear()
        self.clipboard_append(text)

        format_note = " (hyperlink format)" if use_hyperlink else ""
        self.label_status.configure(text=f"Copied {len(self.extracted_items)} items to clipboard{format_note}.", text_color="green")

if __name__ == "__main__":
    app = AudioBriefingApp()
    app.mainloop()

