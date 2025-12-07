
import os

code = r"""import os
import sys
import datetime
import dateparser
import google.generativeai as genai
import scrapetube
import yt_dlp
import glob
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

OUTPUT_FILE = "summary.txt"
CHANNELS_FILE = "channels.txt"

def log(msg):
    print(f"[DEBUG] {msg}")
    sys.stdout.flush()

def setup_gemini():
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        log("Using GEMINI_API_KEY from environment variable.")
        genai.configure(api_key=env_key)
        return genai.GenerativeModel("models/gemini-flash-latest")

    if not GEMINI_API_KEY:
         log("Error: GEMINI_API_KEY not found in .env file or environment.")
         sys.exit(1)
             
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel("models/gemini-flash-latest")

def clean_vtt(text):
    lines = text.splitlines()
    cleaned = []
    last_line = ""
    for line in lines:
        line = line.strip()
        if not line: continue
        if "-->" in line: continue
        if line.isdigit(): continue
        if line.startswith("WEBVTT"): continue
        if line.startswith("Kind:"): continue
        if line.startswith("Language:"): continue
        if line == last_line: continue
        if "<" in line and ">" in line:
            import re
            line = re.sub(r"<[^>]+>", "", line)
        cleaned.append(line)
        last_line = line
    return "
".join(cleaned)

def get_transcript_text(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    temp_prefix = f"temp_sub_{video_id}"
    for f in glob.glob(f"{temp_prefix}*"):
        try: os.remove(f)
        except: pass

    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "outtmpl": temp_prefix,
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        log(f"  -> yt-dlp download error: {e}")
        return None
    
    files = glob.glob(f"{temp_prefix}*.vtt")
    if not files:
        files = glob.glob(f"{temp_prefix}*")
        files = [f for f in files if f.endswith((".vtt", ".ttml", ".srv1", ".srt"))]
    
    if not files:
        log("  -> No subtitle file downloaded by yt-dlp.")
        return None
        
    filename = files[0]
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        log(f"  -> Error reading file: {e}")
        return None
    for f in files:
        try: os.remove(f)
        except: pass
    return clean_vtt(content)

def summarize_text(model, text, previous_context=""):
    try:
        # Estimate duration: 150 words/min. 
        word_count = len(text.split())
        duration_mins = word_count / 150
        
        length_instruction = ""
        if duration_mins > 30:
            length_instruction = "Video is OVER 30 mins: Identify 3-5 primary themes. Synthesize findings into a single comprehensive summary organized by these themes as subheadings."
        else:
            length_instruction = "Video is UNDER 30 mins: Perform a standard, single-pass summary."

        prompt = (
            "You are an expert news analyst. Use the following rules to summarize the provided video transcript.

"
            
            "CONTEXT (Summaries processed so far):
"
            f"{previous_context}

"
            
            "RULES:
"
            "1. Cross-Message Deduplication: If core topics are substantively identical to CONTEXT, output ONLY: Skipped