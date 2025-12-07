import customtkinter as ctk
import subprocess
import threading
import os
import sys
import glob
import datetime
import tkinter.filedialog as filedialog
import qrcode
from PIL import Image # PIL is imported by qrcode, but explicit import helps CTkImage

from podcast_manager import PodcastServer # Import your podcast manager
try:
    from tkcalendar import DateEntry
except Exception:
    DateEntry = None

# Google Drive sign-in and sync removed
# from drive_manager import DriveManager

# Configuration
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class AudioBriefingApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Daily Audio Briefing")
        self.geometry("950x900") # Wider default width to fit controls

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # self.podcast_server = PodcastServer()  # Disabled
        # self.drive_manager = None  # Google Drive features removed

        # Header
        self.label_header = ctk.CTkLabel(self, text="Daily News Summary & YouTube Integration", font=ctk.CTkFont(size=20, weight="bold"))
        self.label_header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        # Text Area
        self.textbox = ctk.CTkTextbox(self, width=600, font=ctk.CTkFont(size=14))
        self.textbox.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        # Controls
        self.frame_yt_api = ctk.CTkFrame(self)
        self.frame_yt_api.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="ew")
        self.frame_yt_api.grid_columnconfigure(0, weight=1)
        self.frame_yt_api.grid_columnconfigure(1, weight=1)

        # Row 0: API Key
        self.label_gemini_key = ctk.CTkLabel(self.frame_yt_api, text="Gemini API Key:")
        self.label_gemini_key.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        self.gemini_key_entry = ctk.CTkEntry(self.frame_yt_api, show="*")
        self.gemini_key_entry.grid(row=0, column=1, padx=10, pady=(10, 0), sticky="ew")
        
        # Row 1: Get YouTube News & Edit Sources
        self.btn_get_yt_news = ctk.CTkButton(self.frame_yt_api, text="Get YouTube News", command=self.get_youtube_news_from_channels)
        # Google Sign-In removed
        self.btn_get_yt_news.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.btn_edit_sources = ctk.CTkButton(self.frame_yt_api, text="Edit Sources", fg_color="gray", command=self.open_sources_editor)
        self.btn_edit_sources.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # Row 2: Fetch Options
        self.label_mode = ctk.CTkLabel(self.frame_yt_api, text="Fetch Limit:")
        self.label_mode.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="e") # Align right next to input
        
        self.frame_fetch_opts = ctk.CTkFrame(self.frame_yt_api, fg_color="transparent")
        self.frame_fetch_opts.grid(row=2, column=1, padx=10, pady=(0, 10), sticky="w")
        
        self.entry_value = ctk.CTkEntry(self.frame_fetch_opts, width=50)
        self.entry_value.pack(side="left", padx=(0, 5))
        self.entry_value.insert(0, "7") # Default to 7
        
        self.mode_var = ctk.StringVar(value="Days")
        self.combo_mode = ctk.CTkComboBox(self.frame_fetch_opts, variable=self.mode_var, values=["Days", "Videos"], width=100)
        self.combo_mode.pack(side="left")


        # Date range controls
        self.range_var = ctk.BooleanVar(value=False)
        self.chk_range = ctk.CTkCheckBox(self.frame_fetch_opts, text="Use date range", variable=self.range_var)
        self.chk_range.pack(side="left", padx=(10, 5))
        # Grey out Fetch Limit when using date range
        self.chk_range.configure(command=self.on_toggle_range)

        self.start_date_entry = ctk.CTkEntry(self.frame_fetch_opts, width=120, placeholder_text="Start YYYY-MM-DD")
        # Calendar buttons beside entries (better UX)
        self.btn_start_cal = ctk.CTkButton(self.frame_fetch_opts, width=28, text="📅", command=self.open_start_calendar)
        self.btn_start_cal.pack(side="left", padx=(5, 5))
        self.btn_end_cal = ctk.CTkButton(self.frame_fetch_opts, width=28, text="📅", command=self.open_end_calendar)
        self.btn_end_cal.pack(side="left", padx=(5, 5))

        self.start_date_entry.pack(side="left", padx=(0, 5))
        # Initialize state
        self.on_toggle_range()

        self.end_date_entry = ctk.CTkEntry(self.frame_fetch_opts, width=120, placeholder_text="End YYYY-MM-DD")
        self.end_date_entry.pack(side="left")

        # Row 3: Upload File
        self.btn_upload_file = ctk.CTkButton(self.frame_yt_api, text="Upload Text File", command=self.upload_text_file)  # Google Drive sync removed
        self.btn_upload_file.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Audio Controls Frame
        self.frame_audio_controls = ctk.CTkFrame(self)
        self.frame_audio_controls.grid(row=3, column=0, padx=20, pady=(5, 20), sticky="ew")
        self.frame_audio_controls.grid_columnconfigure((0, 1), weight=1)

        # Row 0: Fast Generation
        self.btn_fast = ctk.CTkButton(self.frame_audio_controls, text="Generate Fast (gTTS)", command=self.start_fast_generation)
        self.btn_fast.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Row 1: Quality Generation Options
        self.label_voice = ctk.CTkLabel(self.frame_audio_controls, text="Quality Voice:")
        self.label_voice.grid(row=1, column=0, padx=10, pady=(10, 0), sticky="w")

        self.voice_var = ctk.StringVar(value="af_sarah")
        self.combo_voices = ctk.CTkComboBox(self.frame_audio_controls, variable=self.voice_var, values=self.get_available_voices())
        self.combo_voices.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="ew")

        # Convert summaries by date
        self.btn_convert_dates = ctk.CTkButton(self.frame_audio_controls, text="Convert Selected Dates to Audio", command=self.select_dates_to_audio)
        self.btn_convert_dates.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        self.btn_sample = ctk.CTkButton(self.frame_audio_controls, text="Play Sample", width=100, fg_color="gray", command=self.play_sample)
        self.btn_sample.grid(row=2, column=1, padx=10, pady=(0, 10), sticky="w")

        self.btn_quality = ctk.CTkButton(self.frame_audio_controls, text="Generate Quality (Kokoro)", command=self.start_quality_generation)
        self.btn_quality.grid(row=5, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")
        
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
        self.label_status = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.label_status.grid(row=6, column=0, padx=20, pady=(0, 10)) # Row 6

        # Open Folder Button
        self.btn_open = ctk.CTkButton(self, text="Open Output Folder", fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"), command=self.open_output_folder)
        self.btn_open.grid(row=7, column=0, padx=20, pady=(0, 20)) # Row 7

        # Load data

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
    def get_available_voices(self):
        voices_dir = os.path.join(os.path.dirname(__file__), "voices")
        voices = []
        if os.path.exists(voices_dir):
            files = glob.glob(os.path.join(voices_dir, "*.npy"))
            voices = [os.path.basename(f).replace(".npy", "") for f in files]
        if not voices:
            voices = ["af_sarah", "af_bella"]
        return sorted(voices)

    def load_current_summary(self):
        summary_path = os.path.join(os.path.dirname(__file__), "summary.txt")
        if os.path.exists(summary_path):
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.textbox.delete("0.0", "end")
                    self.textbox.insert("0.0", content)
            except Exception as e:
                print(f"Error reading summary: {e}")

    def load_api_key(self):
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        if line.strip().startswith("GEMINI_API_KEY="):
                            key = line.split("=", 1)[1].strip()
                            self.gemini_key_entry.delete(0, "end")
                            self.gemini_key_entry.insert(0, key)
                            break
            except Exception as e:
                print(f"Error reading .env: {e}")

    def save_api_key(self, key):
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
        
        lines = [line for line in lines if not line.strip().startswith("GEMINI_API_KEY=")]
        lines.append("GEMINI_API_KEY=" + key + "\n") # Use \n for literal newline in file.
        
        with open(env_path, "w") as f:
            f.writelines(lines)

    def save_summary(self):
        text = self.textbox.get("0.0", "end-1c")
        summary_path = os.path.join(os.path.dirname(__file__), "summary.txt")
        try:
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(text)
            return True
        except Exception as e:
            self.label_status.configure(text=f"Error saving file: {e}", text_color="red")
            return False

    # Google Drive sync removed
    # def sync_drive_action(self):
    #     pass
            file_name = os.path.basename(local_file)
            query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
            file = self.drive_manager.service.files().list(q=query, fields="files(id, webViewLink, webContentLink)").execute().get('files', [])
            link = None
            if file:
                file_id = file[0]['id']
                try:
                    self.drive_manager.service.permissions().create(fileId=file_id, body={"type":"anyone","role":"reader"}).execute()
                except Exception:
                    pass
                link = file[0].get('webContentLink') or file[0].get('webViewLink')
            self.label_status.configure(text=msg, text_color="green")
            if link:
                self.show_qr_code(link)
        except Exception as e:
            self.label_status.configure(text=f"Drive sync error: {e}", text_color="red")


    def open_sources_editor(self):
        editor = ctk.CTkToplevel(self)
        editor.title("Edit News Sources")
        editor.geometry("500x400")
        editor.transient(self)
        editor.lift()
        
        lbl = ctk.CTkLabel(editor, text="Enable/disable sources and edit URLs:", font=ctk.CTkFont(weight="bold"))
        lbl.pack(pady=10, padx=10, anchor="w")

        container = ctk.CTkScrollableFrame(editor, width=460, height=360)
        container.pack(padx=10, pady=10, fill="both", expand=True)
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

        btn_row = ctk.CTkFrame(editor)
        btn_row.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(btn_row, text="Add Source", command=add_source).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="Bulk Import", command=bulk_import).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="Save Changes", command=save_sources).pack(side="right", padx=5)

    def upload_text_file(self):
        script_dir = os.path.dirname(__file__)
        file_path = filedialog.askopenfilename(initialdir=script_dir, filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                out_file = os.path.join(script_dir, "summary.txt")
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(content)

            except Exception as e:
                self.label_status.configure(text=f"Error loading file: {e}", text_color="red")
    # Google Drive prompt removed
    # def prompt_credentials_json(self):
    #     return False

    # Local HTTP Server removed
    def toggle_http_server(self):
        self.label_status.configure(text="Local server feature removed", text_color="orange")

    # Local IP helper removed

    # QR code display removed

    # Broadcast/QR features disabled
    def play_sample(self):
        voice = self.voice_var.get()
        self.label_status.configure(text=f"Generating sample for {voice}...", text_color="orange")
        def task():
            try:
                script_dir = os.path.dirname(__file__)
                python_exe = "/usr/bin/env python3" if getattr(sys, "frozen", False) else sys.executable
                sample_file = os.path.join(script_dir, "sample_temp.wav")
                if os.path.exists(sample_file): os.remove(sample_file)
                cmd = [python_exe, os.path.join(script_dir, "make_audio_quality.py"), "--voice", voice, "--text", "This is a sample.", "--output", sample_file]
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=script_dir)
                if result.returncode == 0 and os.path.exists(sample_file):
                    self.after(0, lambda: self.label_status.configure(text="Playing sample...", text_color="green"))
                    if sys.platform == "darwin": subprocess.run(["afplay", sample_file])
                    elif sys.platform == "win32":
                        import winsound
                        winsound.PlaySound(sample_file, winsound.SND_FILENAME)
                    else: subprocess.run(["aplay", sample_file])
                    self.after(0, lambda: self.label_status.configure(text="Ready", text_color="gray"))
                else:
                    self.after(0, lambda: self.label_status.configure(text="Sample Error", text_color="red"))
            except Exception as e:
                self.after(0, lambda: self.label_status.configure(text=f"Exception: {e}", text_color="red"))
        threading.Thread(target=task, daemon=True).start()

    def run_script(self, script_name, output_name, extra_args=[], env_vars=None):
        self.btn_fast.configure(state="disabled")
        self.btn_quality.configure(state="disabled")
        self.btn_get_yt_news.configure(state="disabled")
        self.btn_edit_sources.configure(state="disabled")
        self.btn_upload_file.configure(state="disabled")
        self.label_status.configure(text=f"Running {script_name}...", text_color="orange")
        
        if script_name != "get_youtube_news.py" and not self.save_summary():
            self.enable_buttons()
            return

        def task():
            try:
                script_dir = os.path.dirname(__file__)
                python_exe = "/usr/bin/env python3" if getattr(sys, "frozen", False) else sys.executable
                log_path = os.path.join(script_dir, "gui_log.txt")
                cmd = [python_exe, os.path.join(script_dir, script_name)] + extra_args
                process_env = os.environ.copy()
                if env_vars: process_env.update(env_vars)
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, cwd=script_dir, env=process_env, timeout=900)
                except subprocess.TimeoutExpired as tex:
                    with open(log_path, "w", encoding="utf-8") as log:
                        log.write("--- Timeout running " + script_name + " ---\n")
                        log.write("Args: " + str(extra_args) + "\n")
                        log.write("Env keys: " + str(list(env_vars.keys()) if env_vars else "None") + "\n")
                        log.write("Timeout after: " + str(tex.timeout) + "s\n")
                    self.after(0, lambda: self.label_status.configure(text="Task timed out. See gui_log.txt", text_color="red"))
                    return
                
                with open(log_path, "w", encoding="utf-8") as log:
                    log.write("--- Running " + script_name + " ---\n")
                    log.write("Args: " + str(extra_args) + "\n")
                    log.write("Env keys: " + str(list(env_vars.keys()) if env_vars else "None") + "\n")
                    log.write("Return Code: " + str(result.returncode) + "\n")
                    log.write("STDOUT:\n")
                    log.write(result.stdout)
                    log.write("\nSTDERR:\n")
                    log.write(result.stderr)


                if result.returncode == 0:
                    self.after(0, lambda: self.label_status.configure(text=f"Done! Saved {output_name}", text_color="green"))
                    if script_name == "get_youtube_news.py":
                        self.after(0, self.load_current_summary)
                else:
                    last_err = result.stderr.splitlines()[-1] if result.stderr else "(no stderr)"
                    self.after(0, lambda: self.label_status.configure(text=f"Error. See gui_log.txt: {last_err[:120]}", text_color="red"))
            except Exception as e:
                 self.after(0, lambda: self.label_status.configure(text=f"Exception: {e}", text_color="red"))
            finally:
                 self.after(0, self.enable_buttons)

        threading.Thread(target=task, daemon=True).start()

    # Google Sign-In fully removed


    def enable_buttons(self):
        self.btn_fast.configure(state="normal")
        self.btn_quality.configure(state="normal")
        self.btn_get_yt_news.configure(state="normal")
        self.btn_edit_sources.configure(state="normal")
        self.btn_upload_file.configure(state="normal")

    # Google Drive sync removed
    # def sync_drive_action(self):
    #     pass

    def start_fast_generation(self):
        self.run_script("make_audio_fast.py", "daily_fast.mp3")

    def start_quality_generation(self):
        voice = self.voice_var.get()
        self.run_script("make_audio_quality.py", "daily_quality.wav", extra_args=["--voice", voice])
        
    def get_youtube_news_from_channels(self):
        api_key = self.gemini_key_entry.get().strip()
        if not api_key:
            self.label_status.configure(text="Error: Gemini API Key is required.", text_color="red")
            return
        
        mode = self.mode_var.get().lower()
        value = self.entry_value.get().strip()
        if not value.isdigit():
            value = "7"
            
        self.save_api_key(api_key)
        days = int(value) if value.isdigit() else 1
        self.run_script("get_youtube_news.py", f"summary_{datetime.datetime.now().date()}.txt", extra_args=["--days", str(days)], env_vars={"GEMINI_API_KEY": api_key, "PYTHONUNBUFFERED": "1"})
        extra = ["--days", str(days)]
        if self.range_var.get():
            start = self.start_date_entry.get().strip()
            end = self.end_date_entry.get().strip()
            if start and end:
                extra = ["--start", start, "--end", end]
        # Run with either days or date range
        self.run_script("get_youtube_news.py", f"summary_{datetime.datetime.now().date()}.txt", extra_args=extra, env_vars={"GEMINI_API_KEY": api_key, "PYTHONUNBUFFERED": "1"})

        self.run_script("get_youtube_news.py", f"summary_{datetime.datetime.now().date()}.txt", extra_args=extra, env_vars={"GEMINI_API_KEY": api_key, "PYTHONUNBUFFERED": "1"})


    def open_output_folder(self):
        try:
            script_dir = os.path.dirname(__file__)
            if sys.platform == "darwin": subprocess.run(["open", script_dir])
            elif sys.platform == "win32": os.startfile(script_dir)
            else: subprocess.run(["xdg-open", script_dir])
        except Exception:
            pass

    def select_dates_to_audio(self):
        script_dir = os.path.dirname(__file__)
        files = sorted([f for f in os.listdir(script_dir) if f.startswith("summary_") and f.endswith(".txt")])
        if not files:
            self.label_status.configure(text="No per-date summaries found.", text_color="orange")
            return
        dlg = ctk.CTkToplevel(self)
        dlg.title("Select Dates to Convert")
        dlg.geometry("500x500")
        frame = ctk.CTkScrollableFrame(dlg, width=460, height=380)
        frame.pack(padx=10, pady=10, fill="both", expand=True)
        checks = []
        for i, f in enumerate(files):
            var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(frame, text=f.replace("summary_", "").replace(".txt", ""), variable=var).grid(row=i, column=0, sticky="w", padx=8, pady=4)
            checks.append((f, var))
        def start_conversion():
            selected = [os.path.join(script_dir, f) for f, var in checks if var.get()]
            if not selected:
                self.label_status.configure(text="No dates selected.", text_color="red")
                return
        btn_frame = ctk.CTkFrame(dlg)
        btn_frame.pack(pady=10)
        def do_convert():
            selected = [f for f, v in checks if v.get()]
            if not selected:
                dlg.destroy()
                return
            # Generate unique names with dates
            for f in selected:
                date_str = f.replace("summary_", "").replace(".txt", "")
                # Fast
                self.run_script("make_audio_fast.py", f"audio_fast_{date_str}.mp3", extra_args=["--input", f])
                # Quality with selected voice
                voice = self.voice_var.get()
                self.run_script("make_audio_quality.py", f"audio_quality_{date_str}.wav", extra_args=["--input", f, "--voice", voice])
        ctk.CTkButton(btn_frame, text="Convert", command=do_convert).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", command=dlg.destroy).pack(side="left", padx=6)

        # Remove legacy block below to fix indentation
        # Cleanup stray legacy code
        # (start_conversion section removed)



        # strip invalid legacy lines

        # remove vestigial lines

        # Removed legacy start_conversion block

        
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

if __name__ == "__main__":
    app = AudioBriefingApp()
    app.mainloop()
