
import os
import re

file_path = "/Users/roti/gemini_projects/audio_briefing/daily_audio_briefing/gui_app.py"

with open(file_path, "r") as f:
    content = f.read()

# Define patterns to extract
# Escaped \n for literal newline in regex
sync_method_pattern = r"(\s+def sync_to_drive\(self\):.*?)(?=\n\s+def show_upload_log\(self\):)"
show_upload_log_pattern = r"(\s+def show_upload_log\(self\):.*?)(?=\n\s+def show_drive_auth_instructions\(self\):)"
show_drive_auth_pattern = r"(\s+def show_drive_auth_instructions\(self\):.*?)(?=\n\s+def get_available_voices\(self\):|\n\s+def [a-zA-Z_]+\(self\):|\Z)" # Added \Z for end of file match


# Extract methods
sync_method_match = re.search(sync_method_pattern, content, re.DOTALL)
show_upload_match = re.search(show_upload_log_pattern, content, re.DOTALL)
show_drive_auth_match = re.search(show_drive_auth_pattern, content, re.DOTALL)

if not (sync_method_match and show_upload_match and show_drive_auth_match):
    print("Could not find all drive related methods. Manual intervention might be needed.")
    exit()

sync_method_code = sync_method_match.group(1)
show_upload_code = show_upload_match.group(1)
show_drive_auth_code = show_drive_auth_match.group(1)


# Remove from original content
content = re.sub(sync_method_pattern, "", content, flags=re.DOTALL)
content = re.sub(show_upload_log_pattern, "", content, flags=re.DOTALL)
content = re.sub(show_drive_auth_pattern, "", content, flags=re.DOTALL)


# Find insertion point (e.g., after save_summary)
insert_marker = "    def save_summary(self):"
insert_index = content.find(insert_marker)
if insert_index == -1:
    print("Could not find insertion marker. Manual intervention needed.")
    exit()

# Find the end of save_summary method definition
insert_index = content.find("\n\n", insert_index) # Find first blank line after definition
if insert_index == -1:
    insert_index = len(content) # If no blank line, append to end of file

if insert_index != -1:
    # Insert extracted methods
    new_methods_block = "\n\n" + sync_method_code + "\n" + show_upload_code + "\n" + show_drive_auth_code + "\n"
    content = content[:insert_index] + new_methods_block + content[insert_index:]
else:
    print("Could not find proper insertion point. Manual intervention needed.")
    exit()


with open(file_path, "w") as f:
    f.write(content)

print("Successfully reordered drive related methods in gui_app.py")
