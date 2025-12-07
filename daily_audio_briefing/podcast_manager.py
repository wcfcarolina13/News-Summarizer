import os
import glob
import sys
import socket
import threading
import http.server
import socketserver
from datetime import datetime
import xml.etree.ElementTree as ET
from email.utils import formatdate

def log(msg): # Add log function here too for internal errors
    print(f"[DEBUG-PODCAST] {msg}")
    sys.stdout.flush()

class PodcastServer:
    def __init__(self, port=8080):
        self.default_port = port
        self.port = port
        self.ip = self.get_local_ip()
        self.server = None
        self.thread = None
        self.running = False

    @property
    def base_url(self):
        return f"http://{self.ip}:{self.port}"

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            log(f"Detected local IP: {ip}")
            return ip
        except Exception as e:
            log(f"Error detecting local IP, falling back to 127.0.0.1: {e}")
            return "127.0.0.1"

    def generate_feed(self, root_dir):
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = "Daily Audio Briefing"
        ET.SubElement(channel, "description").text = "Your AI-generated daily news summary."
        
        audio_files = []
        for ext in ["*.mp3", "*.wav"]:
            audio_files.extend(glob.glob(os.path.join(root_dir, "**", ext), recursive=True))
            
        audio_files.sort(key=os.path.getmtime, reverse=True)
        
        if not audio_files:
            log("No audio files found to generate feed.")
            # Still write an empty feed
            
        for file_path in audio_files:
            rel_path = os.path.relpath(file_path, root_dir)
            url_path = rel_path.replace("\\", "/").replace(" ", "%20")
            url = f"{self.base_url}/{url_path}"
            
            item = ET.SubElement(channel, "item")
            folder = os.path.basename(os.path.dirname(file_path))
            name = os.path.basename(file_path)
            ET.SubElement(item, "title").text = f"{folder}: {name}"
            ET.SubElement(item, "enclosure", url=url, type="audio/mpeg" if file_path.endswith(".mp3") else "audio/wav", length=str(os.path.getsize(file_path)))
            ET.SubElement(item, "guid").text = url
            ET.SubElement(item, "pubDate").text = formatdate(os.path.getmtime(file_path))

        tree = ET.ElementTree(rss)
        feed_path = os.path.join(root_dir, "feed.xml")
        tree.write(feed_path, encoding="UTF-8", xml_declaration=True)
        return f"{self.base_url}/feed.xml"

    def start(self, root_dir):
        if self.running: return
        
        current_dir = os.getcwd()
        try:
            os.chdir(root_dir)
            handler = http.server.SimpleHTTPRequestHandler
            
            self.server = None
            for port in range(self.default_port, self.default_port + 10): # Try 10 ports
                try:
                    self.server = socketserver.TCPServer(("", port), handler)
                    self.port = port
                    log(f"Found free port: {self.port}")
                    break
                except OSError as e:
                    log(f"Port {port} in use: {e}")
                    continue
            
            if not self.server:
                raise Exception("No free port found in range")

            self.server.allow_reuse_address = True
            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.daemon = True
            self.thread.start()
            self.running = True
            log(f"Server started successfully at {self.base_url}")
            
            self.generate_feed(root_dir) # Generate feed NOW that port is known
            log(f"Feed generated at {self.base_url}/feed.xml")
            
        except Exception as e:
            log(f"Error within podcast server start: {e}")
            self.stop()
            raise # Re-raise for GUI
        finally:
            os.chdir(current_dir)

    def stop(self):
        if self.server:
            log(f"Stopping server at {self.base_url}")
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            self.running = False
