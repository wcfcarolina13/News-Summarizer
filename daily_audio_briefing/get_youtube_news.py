import os
import sys
import datetime
import dateparser
import google.generativeai as genai
import scrapetube
import yt_dlp
import glob
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

OUTPUT_FILE = "summary.txt"
CHANNELS_FILE = "channels.txt"
SOURCES_JSON = "sources.json"

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
    return "\n".join(cleaned)

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
        prompt = (
            "You are an expert news analyst producing content for an AUDIO BRIEFING.\n"
            "Use the following rules to summarize the provided video transcript.\n\n"
            
            "CONTEXT (Summaries processed so far):\n"
            f"{previous_context}\n\n"
            
            "RULES:\n"
            "1. Cross-Message Deduplication: If duplicative, output ONLY: \"Skipped [Video Title] as duplicative.\"\n"
            "2. Tutorials/Promotions: If tutorial/promo, output ONLY: \"Skipped [Video Title] as tutorial/promotion.\"\n"
            "3. Technical Analysis: Focus on big picture/sentiment.\n"
            "4. Format Requirements for AUDIO (Text-to-Speech):\n"
            "   - Write in a natural, conversational style suitable for reading aloud.\n"
            "   - DO NOT use symbols like #, *, -, or bullet points.\n"
            "   - Use phrases like First, Additionally, Finally, instead of lists.\n"
            "   - Write out dates (e.g., December fifth).\n"
            "   - NO timestamps.\n"
            "   - Prioritize stats, data, events, reasoning.\n\n"
            
            "TRANSCRIPT:\n"
            f"{text[:30000]}"
        )
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        log(f"  -> Gemini Error: {e}")
        return f"Error summarizing: {e}"

def process_channel(channel_url, model, shared_context, cutoff_date):
    log(f"--- Processing Channel: {channel_url} ---")
    limit = 20
    try:
        video_generator = scrapetube.get_channel(channel_url=channel_url, limit=limit)
        videos = list(video_generator)
        log(f"Fetched {len(videos)} recent videos.")
    except Exception as e:
        log(f"Error fetching videos for {channel_url}: {e}")
        return [], shared_context

    new_summaries = []
    # cutoff_date provided by caller
    
    processed_count = 0
    for video in videos:


        video_id = video["videoId"]
        title = video["title"]["runs"][0]["text"]
        
        date_info = video.get("publishedTimeText", {}).get("simpleText")
        
        pub_date = None
        if date_info:
            pub_date = dateparser.parse(date_info)
        
        if cutoff_date is not None:
            if not pub_date: continue
            # only keep videos published on the target day
            if pub_date.date() != cutoff_date.date():
                continue

        log(f"PROCESSING: {title} ({date_info})")
        transcript = get_transcript_text(video_id)
        if not transcript:
            log("  -> SKIPPING: No transcript found.")
            continue

        log("  -> Transcript retrieved. Summarizing...")
        
        current_context_str = "\n".join(shared_context[-5:])
        summary = summarize_text(model, transcript, current_context_str)
        
        if summary.strip().startswith("Skipped"):
            log(f"  -> Gemini Skipped: {summary.strip()}")
            continue
            
        date_str = pub_date.strftime("%B %d, %Y") if pub_date else "Unknown Date"
        
        entry = f"Regarding the video {title} published on {date_str}:\n{summary}\n"
        
        new_summaries.append(entry)
        shared_context.append(f"Title: {title}\nSummary: {summary}")
        processed_count += 1
        log("  -> Summary generated.")

    return new_summaries, shared_context

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=1, help="Process this many days starting from today")
    args, _ = parser.parse_known_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    model = setup_gemini()

    # Load sources from sources.json if present, else fallback to channels.txt
    channels = []
    if os.path.exists(SOURCES_JSON):
        import json
        try:
            data = json.load(open(SOURCES_JSON))
            channels = [s["url"] for s in data.get("sources", []) if s.get("enabled", True)]
        except Exception as e:
            log(f"Error reading sources.json: {e}")
    if not channels and os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r") as f:
            channels = [line.strip() for line in f if line.strip()]
    if not channels:
        log("Error: No sources configured.")
        return

    shared_context = []
    total_summaries = 0
    for day_offset in range(args.days):
        target_date = datetime.datetime.now() - datetime.timedelta(days=day_offset)
        log(f"=== Processing date: {target_date.date()} ===")
        day_summaries = []
        for channel in channels:
            summaries, shared_context = process_channel(channel, model, shared_context, target_date)
            day_summaries.extend(summaries)
        if day_summaries:
            out_name = f"summary_{target_date.date()}.txt"
            with open(out_name, "w", encoding="utf-8") as f:
                f.write("\n\n".join(day_summaries))
            log(f"SUCCESS: {len(day_summaries)} summaries for {target_date.date()} -> {out_name}")
            total_summaries += len(day_summaries)
        else:
            log(f"No summaries for {target_date.date()}")
    if total_summaries == 0:
        log("FINISHED: No summaries created for selected days.")

if __name__ == "__main__":
    main()
