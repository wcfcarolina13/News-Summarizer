
import os

file_path = "/Users/roti/gemini_projects/audio_briefing/daily_audio_briefing/gui_app.py"

with open(file_path, "r") as f:
    content = f.read()

# We need to replace the get_youtube_news_from_channels method
old_method_signature = "def get_youtube_news_from_channels(self):"
new_method_code = """    def get_youtube_news_from_channels(self):
        api_key = self.gemini_key_entry.get().strip()
        if not api_key:
            self.label_status.configure(text="Error: Gemini API Key is required.", text_color="red")
            return
        
        mode = self.mode_var.get().lower()
        value = self.entry_value.get().strip()
        if not value.isdigit():
            value = "7"
            
        self.save_api_key(api_key)
        self.run_script("get_youtube_news.py", "summary.txt", extra_args=["--mode", mode, "--value", value], env_vars={"GEMINI_API_KEY": api_key})
"""

# Finding the method block is tricky with simple replace if indentation varies.
# But since I wrote the file, I know the structure.
# I will replace the old one.

if "mode = self.mode_var.get().lower()" not in content:
    # Find start
    start_idx = content.find(old_method_signature)
    if start_idx != -1:
        # Find end (start of open_output_folder)
        end_idx = content.find("def open_output_folder(self):")
        
        if end_idx != -1:
            new_content = content[:start_idx] + new_method_code + "
    " + content[end_idx:]
            with open(file_path, "w") as f:
                f.write(new_content)
            print("Updated get_youtube_news_from_channels in gui_app.py")
        else:
            print("Could not find end of method.")
    else:
        print("Could not find start of method.")
