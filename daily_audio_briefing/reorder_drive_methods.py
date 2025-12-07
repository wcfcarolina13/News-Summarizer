
import os
import re

file_path = "/Users/roti/gemini_projects/audio_briefing/daily_audio_briefing/gui_app.py"

with open(file_path, "r") as f:
    content = f.read()

# Define patterns to extract the methods. Using non-greedy match and explicit end markers.
sync_method_pattern = r"(\n\s+def sync_to_drive\(self\):.*?(?=\n\s+def show_upload_log\(self, upload_log\):))"
show_upload_log_pattern = r"(\n\s+def show_upload_log\(self, upload_log\):.*?(?=\n\s+def show_drive_auth_instructions\(self\):))"
show_drive_auth_pattern = r"(\n\s+def show_drive_auth_instructions\(self\):.*?(?=\n\s+def toggle_podcast_server\(self\):|\n\s+def get_available_voices\(self\):|\n\s+def [a-zA-Z_]+\(self\):|\Z))" # Match until next def or end of file


# Extract methods
sync_method_match = re.search(sync_method_pattern, content, re.DOTALL)
show_upload_match = re.search(show_upload_log_pattern, content, re.DOTALL)
show_drive_auth_match = re.search(show_drive_auth_pattern, content, re.DOTALL)

if not (sync_method_match and show_upload_match and show_drive_auth_match):
    print("Error: Could not find all drive related methods for reordering. Manual intervention might be needed.")
    exit(1)

sync_method_code = sync_method_match.group(1)
show_upload_code = show_upload_match.group(1)
show_drive_auth_code = show_drive_auth_match.group(1)

# Remove extracted methods from content
content = re.sub(re.escape(sync_method_code), "", content, flags=re.DOTALL)
content = re.sub(re.escape(show_upload_code), "", content, flags=re.DOTALL)
content = re.sub(re.escape(auth_instructions_code), "", content, flags=re.DOTALL)


# Find insertion point (after save_api_key)
insert_marker = "    def save_api_key(self, key):"
insert_index = content.find(insert_marker)
if insert_index == -1:
    print("Error: Could not find save_api_key insertion marker.")
    exit(1)

# Find the end of save_api_key method block (assuming 2 blank lines after it)
insert_index = content.find("\n\n", insert_index) 

if insert_index == -1: # Fallback if no 2 blank lines found
    # Try to find the next method definition
    insert_index = content.find("\n    def ", insert_index)
    if insert_index == -1:
         insert_index = len(content) # As a last resort, append to end
    else:
         insert_index -= 1 # Insert before the next method

# Insert extracted methods
new_methods_block = "\n" + sync_method_code + "\n" + show_upload_code + "\n" + show_drive_auth_code + "\n"
content = content[:insert_index] + new_methods_block + content[insert_index:]

with open(file_path, "w") as f:
    f.write(content)

print("Successfully reordered drive related methods in gui_app.py")
