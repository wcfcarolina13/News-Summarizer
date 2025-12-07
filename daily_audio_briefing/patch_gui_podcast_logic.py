
import os

file_path = "/Users/roti/gemini_projects/audio_briefing/daily_audio_briefing/gui_app.py"

new_method = """    def toggle_podcast_server(self):
        if not self.podcast_server.running:
            root_dir = os.path.dirname(__file__)
            try:
                self.podcast_server.start(root_dir)
                feed_url = f"{self.podcast_server.base_url}/feed.xml"
                self.btn_broadcast.configure(text="Stop Broadcast", fg_color="red")
                self.show_qr_code(feed_url)
                self.label_status.configure(text=f"Podcast broadcasting on {self.podcast_server.base_url}", text_color="green")
            except Exception as e:
                self.label_status.configure(text=f"Error starting broadcast: {e}", text_color="red")
        else:
            self.podcast_server.stop()
            self.btn_broadcast.configure(text="Broadcast to Phone", fg_color="green")
            self.label_status.configure(text="Podcast broadcast stopped.", text_color="gray")
"""

with open(file_path, "r") as f:
    content = f.read()

start_marker = "    def toggle_podcast_server(self):"
end_marker = "    def show_qr_code(self, data):"

start_index = content.find(start_marker)
end_index = content.find(end_marker, start_index)

if start_index != -1 and end_index != -1:
    new_content = content[:start_index] + new_method + "\n\n" + content[end_index:]
    with open(file_path, "w") as f:
        f.write(new_content)
    print("Patched toggle_podcast_server")
else:
    print("Could not find method boundaries")
