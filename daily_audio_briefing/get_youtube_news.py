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
SPECIFIC_OUTPUT_DIR = "Specific Video Lists"
CHANNELS_FILE = "channels.txt"
SOURCES_JSON = "sources.json"

def log(msg):
    print(f"[DEBUG] {msg}")
    sys.stdout.flush()

def get_week_folder(target_date):
    """Create and return week-based folder path matching audio file organization"""
    year, week, _ = target_date.isocalendar()
    folder_name = f"Week_{week}_{year}"
    
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        log(f"Created new folder: {folder_name}")
        
    return folder_name

def setup_gemini(model_name="gemini-2.5-flash"):
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        log(f"Using GEMINI_API_KEY from environment variable.")
        log(f"Using model: {model_name}")
        genai.configure(api_key=env_key)
        return genai.GenerativeModel(model_name)

    if not GEMINI_API_KEY:
         log("Error: GEMINI_API_KEY not found in .env file or environment.")
         sys.exit(1)
             
    genai.configure(api_key=GEMINI_API_KEY)
    log(f"Using model: {model_name}")
    return genai.GenerativeModel(model_name)

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

def load_custom_instructions():
    """Load custom instructions from file if it exists."""
    try:
        if os.path.exists("custom_instructions.txt"):
            with open("custom_instructions.txt", "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""

def summarize_text(model, text, previous_context=""):
    try:
        custom_instructions = load_custom_instructions()
        custom_section = f"\n\nUSER PROFILE & PREFERENCES:\n{custom_instructions}\n" if custom_instructions else ""
        
        prompt = (
            "You are an expert news analyst producing content for an AUDIO BRIEFING.\n"
            "Use the following rules to summarize the provided video transcript.\n\n"
            
            "CONTEXT (Summaries processed so far):\n"
            f"{previous_context}\n\n"
            
            "RULES:\n"
            "1. Cross-Message Deduplication: If duplicative, output ONLY: \"Skipped [Video Title] as duplicative.\"\n"
            "2. Tutorials/Promotions: If tutorial/promo, output ONLY: \"Skipped [Video Title] as tutorial/promotion.\"\n"
            "3. Comprehensive Coverage: Extract ALL key insights, unique perspectives, and actionable information. "
            "Don't skip important details, data points, analysis, or unique angles that provide value or 'alpha'.\n"
            "4. Technical Analysis: Include both big picture/sentiment AND specific technical details, price levels, "
            "indicators, or trading insights when mentioned.\n"
            "5. Key Points to Capture:\n"
            "   - All significant data, statistics, and metrics\n"
            "   - Unique insights, contrarian views, or novel analysis\n"
            "   - Actionable information and specific recommendations\n"
            "   - Important context, reasoning, and causal relationships\n"
            "   - Notable predictions, forecasts, or forward-looking statements\n"
            "6. Format Requirements for AUDIO (Text-to-Speech):\n"
            "   - Write in a natural, conversational style suitable for reading aloud.\n"
            "   - DO NOT use symbols like #, *, -, or bullet points.\n"
            "   - Use phrases like First, Additionally, Furthermore, Moreover, Finally, instead of lists.\n"
            "   - Write out dates (e.g., December fifth).\n"
            "   - NO timestamps.\n"
            "   - Organize into coherent paragraphs with smooth transitions.\n"
            f"{custom_section}\n"
            
            "TRANSCRIPT:\n"
            f"{text[:50000]}"
        )
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        log(f"  -> Gemini Error: {e}")
        return f"Error summarizing: {e}"

def process_channel(channel_url, model, shared_context, cutoff_date, cutoff_time=None):
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
    # cutoff_date provided by caller; cutoff_time for hours mode
    
    processed_count = 0
    videos_on_target_date = 0
    for video in videos:


        video_id = video["videoId"]
        title = video["title"]["runs"][0]["text"]
        
        date_info = video.get("publishedTimeText", {}).get("simpleText")
        
        pub_date = None
        if date_info:
            pub_date = dateparser.parse(date_info)
        
        if cutoff_time is not None:
            # Hours mode: filter by timestamp
            if not pub_date: continue
            if pub_date < cutoff_time:
                continue
            videos_on_target_date += 1
        elif cutoff_date is not None:
            # Days mode: filter by date
            if not pub_date: continue
            # only keep videos published on the target day
            if pub_date.date() != cutoff_date.date():
                continue
            videos_on_target_date += 1

        log(f"DEBUG: Video matches filter: {title} ({date_info})")
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
    
    if cutoff_time:
        log(f"DEBUG: Found {videos_on_target_date} videos since {cutoff_time}, created {len(new_summaries)} summaries")
    elif videos_on_target_date > 0:
        log(f"DEBUG: Found {videos_on_target_date} videos on {cutoff_date.date()}, created {len(new_summaries)} summaries")
    else:
        log(f"DEBUG: No videos found matching filter from this channel")

    return new_summaries, shared_context

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=1, help="Process this many days starting from today")
    parser.add_argument("--hours", type=int, help="Process videos from the last N hours")
    parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="End date YYYY-MM-DD")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", 
                        help="Gemini model to use (gemini-2.5-flash, gemini-2.5-pro)")
    parser.add_argument("--urls", nargs="+", help="Specific YouTube video URLs to summarize")
    args = parser.parse_args()


    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    model = setup_gemini(args.model)

    # If specific URLs provided, process them directly and write summary.txt
    if args.urls:
        summaries = []
        for url in args.urls:
            vid = None
            try:
                # Extract video ID from full URL
                if "watch?v=" in url:
                    vid = url.split("watch?v=")[-1].split("&")[0].split("?")[0]
                elif "/shorts/" in url:
                    vid = url.split("/shorts/")[-1].split("?")[0]
                elif "/live/" in url:
                    vid = url.split("/live/")[-1].split("?")[0]
                elif "youtu.be/" in url:
                    vid = url.split("youtu.be/")[-1].split("?")[0]
            except Exception:
                vid = None
            if not vid:
                log(f"Skipping invalid URL: {url}")
                continue
            log(f"=== Processing specific video: {url} ===")
            transcript = get_transcript_text(vid)
            if not transcript:
                log("  -> SKIPPING: No transcript found.")
                continue
            summary = summarize_text(model, transcript, "")
            if summary.strip().startswith("Skipped"):
                log(f"  -> Gemini Skipped: {summary.strip()}")
                continue
            entry = f"Summary for {url}:\n{summary}\n"
            summaries.append(entry)
        if summaries:
            # Ensure output directory exists
            out_dir = os.path.join(script_dir, SPECIFIC_OUTPUT_DIR)
            os.makedirs(out_dir, exist_ok=True)
            # Timestamped filename
            ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"specific-video-list_{ts}.txt"
            save_path = os.path.join(out_dir, filename)
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write("\n\n".join(summaries))
                log(f"SUCCESS: Wrote {len(summaries)} specific video summaries -> {save_path}")
            except Exception as e:
                log(f"ERROR: Failed to write {save_path}: {e}")
            return
        else:
            log("WARNING: No summaries created for provided URLs.")
            return

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

    # Build date list
    dates_to_process = []
    hours_mode = False
    cutoff_time = None
    
    if args.hours:
        # Hours mode: process all videos from the last N hours (single processing pass)
        hours_mode = True
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=args.hours)
        log(f"Hours mode: Processing videos from the last {args.hours} hour(s) (since {cutoff_time})")
        # Use current date as the target for saving
        dates_to_process.append(datetime.datetime.now())
    elif args.start and args.end:
        try:
            start_dt = datetime.datetime.strptime(args.start, "%Y-%m-%d")
            end_dt = datetime.datetime.strptime(args.end, "%Y-%m-%d")
            if start_dt > end_dt:
                start_dt, end_dt = end_dt, start_dt
            cur = start_dt
            while cur <= end_dt:
                dates_to_process.append(cur)
                cur += datetime.timedelta(days=1)
        except Exception as e:
            log(f"Invalid date range: {e}. Falling back to --days.")

    if not dates_to_process:
        for day_offset in range(args.days):
            dates_to_process.append(datetime.datetime.now() - datetime.timedelta(days=day_offset))

    for target_date in dates_to_process:

        pass
        # placeholder to satisfy indentation; actual processing happens below
    shared_context = []
    total_summaries = 0
    log(f"DEBUG: Will save summaries in {os.path.dirname(__file__)}")
    for target_date in dates_to_process:
        if hours_mode:
            log(f"=== Processing videos from last {args.hours} hour(s) ===")
        else:
            log(f"=== Processing date: {target_date.date()} ===")
        day_summaries = []
        for channel in channels:
            summaries, shared_context = process_channel(channel, model, shared_context, target_date, cutoff_time)
            day_summaries.extend(summaries)
        if day_summaries:
            if hours_mode:
                out_name = f"summary_last_{args.hours}h.txt"
            else:
                out_name = f"summary_{target_date.date()}.txt"
            week_folder = get_week_folder(target_date)
            save_path = os.path.join(week_folder, out_name)
            log(f"DEBUG: Attempting to write {len(day_summaries)} summaries to: {save_path}")
            log(f"DEBUG: Week folder: {week_folder}")
            log(f"DEBUG: Week folder exists: {os.path.exists(week_folder)}")
            log(f"DEBUG: Week folder writable: {os.access(week_folder, os.W_OK)}")
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write("\n\n".join(day_summaries))
                log(f"DEBUG: File write completed. Verifying...")
                if os.path.exists(save_path):
                    file_size = os.path.getsize(save_path)
                    if hours_mode:
                        log(f"SUCCESS: {len(day_summaries)} summaries for last {args.hours} hour(s) -> {save_path} ({file_size} bytes)")
                    else:
                        log(f"SUCCESS: {len(day_summaries)} summaries for {target_date.date()} -> {save_path} ({file_size} bytes)")
                else:
                    log(f"ERROR: File was written but does not exist at {save_path}")
            except Exception as e:
                log(f"ERROR: Failed to write {save_path}: {e}")
                import traceback
                log(f"ERROR: Traceback: {traceback.format_exc()}")
            total_summaries += len(day_summaries)
        else:
            if hours_mode:
                log(f"WARNING: No summaries found for last {args.hours} hour(s) - no videos published in this time range from configured channels")
            else:
                log(f"WARNING: No summaries found for {target_date.date()} - no videos published on this date from configured channels")
    if total_summaries == 0:
        if hours_mode:
            log(f"FINISHED: No summaries created for last {args.hours} hour(s).")
        else:
            log("FINISHED: No summaries created for selected days.")

if __name__ == "__main__":
    main()
