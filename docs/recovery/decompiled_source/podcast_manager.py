# Source Generated with Decompyle++
# File: podcast_manager.pyc (Python 3.12)

import os
import glob
import sys
import socket
import threading
import http.server as http
import socketserver
from datetime import datetime

ElementTree
from email.utils import formatdate
import xml.etree.ElementTree, etree

def log(msg):
    print(f'''[DEBUG-PODCAST] {msg}''')
    sys.stdout.flush()


class PodcastServer:
    
    def __init__(self, port = (8080,)):
        self.default_port = port
        self.port = port
        self.ip = self.get_local_ip()
        self.server = None
        self.thread = None
        self.running = False

    base_url = (lambda self: f'''http://{self.ip}:{self.port}''')()
    
    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        log(f'''Detected local IP: {ip}''')
        return ip
    # WARNING: Decompyle incomplete

    
    def generate_feed(self, root_dir):
        rss = ET.Element('rss', version = '2.0')
        channel = ET.SubElement(rss, 'channel')
        ET.SubElement(channel, 'title').text = 'Daily Audio Briefing'
        ET.SubElement(channel, 'description').text = 'Your AI-generated daily news summary.'
        audio_files = []
        for ext in ('*.mp3', '*.wav'):
            audio_files.extend(glob.glob(os.path.join(root_dir, '**', ext), recursive = True))
        audio_files.sort(key = os.path.getmtime, reverse = True)
        if not audio_files:
            log('No audio files found to generate feed.')
        for file_path in audio_files:
            rel_path = os.path.relpath(file_path, root_dir)
            url_path = rel_path.replace('\\', '/').replace(' ', '%20')
            url = f'''{self.base_url}/{url_path}'''
            item = ET.SubElement(channel, 'item')
            folder = os.path.basename(os.path.dirname(file_path))
            name = os.path.basename(file_path)
            ET.SubElement(item, 'title').text = f'''{folder}: {name}'''
            ET.SubElement(item, 'enclosure', url = url, type = 'audio/mpeg' if file_path.endswith('.mp3') else 'audio/wav', length = str(os.path.getsize(file_path)))
            ET.SubElement(item, 'guid').text = url
            ET.SubElement(item, 'pubDate').text = formatdate(os.path.getmtime(file_path))
        tree = ET.ElementTree(rss)
        feed_path = os.path.join(root_dir, 'feed.xml')
        tree.write(feed_path, encoding = 'UTF-8', xml_declaration = True)
        return f'''{self.base_url}/feed.xml'''

    
    def start(self, root_dir):
        if self.running:
            return None
        current_dir = os.getcwd()
        os.chdir(root_dir)
        handler = http.server.SimpleHTTPRequestHandler
        self.server = None
        for port in range(self.default_port, self.default_port + 10):
            self.server = socketserver.TCPServer(('', port), handler)
            self.port = port
            log(f'''Found free port: {self.port}''')
            range(self.default_port, self.default_port + 10)
        if not self.server:
            raise Exception('No free port found in range')
        self.server.allow_reuse_address = True
        self.thread = threading.Thread(target = self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        self.running = True
        log(f'''Server started successfully at {self.base_url}''')
        self.generate_feed(root_dir)
        log(f'''Feed generated at {self.base_url}/feed.xml''')
        os.chdir(current_dir)
        return None
    # WARNING: Decompyle incomplete

    
    def stop(self):
        if self.server:
            log(f'''Stopping server at {self.base_url}''')
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            self.running = False
            return None


