import os

file_path = "/Users/roti/gemini_projects/audio_briefing/daily_audio_briefing/gui_app.py"

new_methods_code = """
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
        lines.append(f"GEMINI_API_KEY={key}\n") # Use \n to be literal in string
        
        with open(env_path, "w") as f:
            f.writelines(lines)
"""

with open(file_path, "r") as f:
    content = f.read()

# 1. Add call to load_api_key in __init__
if "self.load_api_key()" not in content:
    content = content.replace(
        "        self.load_current_summary()",
        "        self.load_current_summary()
        self.load_api_key()"
    )

# 2. Inject new methods
if "def save_api_key(self):" not in content and "def load_api_key(self):" not in content: # Check for both
    # Find a good injection point (e.g., before get_available_voices)
    content = content.replace(
        "    def get_available_voices(self):",
        new_methods_code + "

    def get_available_voices(self):"
    )

# 3. Modify get_youtube_news_from_channels to call save_api_key
if "self.save_api_key(api_key)" not in content:
    content = content.replace(
        """        self.run_script("get_youtube_news.py", "summary.txt", env_vars={"GEMINI_API_KEY": api_key})""",
        """        self.save_api_key(api_key)
        self.run_script("get_youtube_news.py", "summary.txt", env_vars={"GEMINI_API_KEY": api_key})"""
    )
    # This might fail if the original line has slightly different indentation or spaces.

with open(file_path, "w") as f:
    f.write(content)

print(f"Patched {file_path}")
