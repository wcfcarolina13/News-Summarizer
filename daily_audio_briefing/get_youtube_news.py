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


def get_resource_path(filename):
    """Get the path to a bundled resource file.

    When running as a PyInstaller bundle, resources are in sys._MEIPASS.
    When running normally, they're in the same directory as this script.
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        return os.path.join(sys._MEIPASS, filename)
    else:
        # Running normally - use script directory
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


OUTPUT_FILE = "summary.txt"
SPECIFIC_OUTPUT_DIR = "Specific Video Lists"
# These are config files that may be bundled with the app
CHANNELS_FILE = get_resource_path("channels.txt")
SOURCES_JSON = get_resource_path("sources.json")

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

def get_data_directory():
    """Get the persistent data directory for user files."""
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            data_dir = os.path.expanduser("~/Library/Application Support/Daily Audio Briefing")
        elif sys.platform == "win32":
            data_dir = os.path.join(os.environ.get("APPDATA", ""), "Daily Audio Briefing")
        else:
            data_dir = os.path.expanduser("~/.daily-audio-briefing")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    else:
        return os.path.dirname(os.path.abspath(__file__))

def load_custom_instructions():
    """Load custom instructions from file if it exists. Checks data directory first."""
    # Try data directory first (persistent across reinstalls)
    data_dir = get_data_directory()
    paths_to_try = [
        os.path.join(data_dir, "custom_instructions.txt"),
        "custom_instructions.txt",  # Current working directory
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_instructions.txt")
    ]

    for path in paths_to_try:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return content
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
            # Clean up YouTube-specific prefixes that dateparser can't handle
            clean_date = date_info
            for prefix in ["Streamed ", "Premiered ", "Scheduled for "]:
                if clean_date.startswith(prefix):
                    clean_date = clean_date[len(prefix):]
                    break
            pub_date = dateparser.parse(clean_date)

            # Log parsing details for debugging
            if not pub_date:
                log(f"  [DATE] Failed to parse: '{date_info}' (cleaned: '{clean_date}')")

        if cutoff_time is not None:
            # Hours mode: filter by timestamp
            if not pub_date:
                log(f"  [SKIP] No parseable date for: {title[:50]}... ({date_info})")
                continue
            if pub_date < cutoff_time:
                log(f"  [SKIP] Too old: {title[:50]}... (pub: {pub_date}, cutoff: {cutoff_time})")
                continue
            videos_on_target_date += 1
        elif cutoff_date is not None:
            # Days mode: filter by date
            if not pub_date:
                log(f"  [SKIP] No parseable date for: {title[:50]}... ({date_info})")
                continue
            # only keep videos published on the target day
            if pub_date.date() != cutoff_date.date():
                log(f"  [SKIP] Wrong date: {title[:50]}... (pub: {pub_date.date()}, want: {cutoff_date.date()})")
                continue
            videos_on_target_date += 1

        log(f"  [MATCH] {title[:50]}... ({date_info} -> {pub_date})")
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

def get_data_directory():
    """Get the appropriate data directory for storing output files.

    When running as a frozen app (PyInstaller), uses Application Support.
    When running in development, uses the script directory.
    """
    if getattr(sys, "frozen", False):
        # Frozen app - use Application Support for persistent storage
        if sys.platform == "darwin":
            data_dir = os.path.expanduser("~/Library/Application Support/Daily Audio Briefing")
        elif sys.platform == "win32":
            data_dir = os.path.join(os.environ.get("APPDATA", ""), "Daily Audio Briefing")
        else:
            data_dir = os.path.expanduser("~/.daily-audio-briefing")

        # Create if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

        return data_dir
    else:
        # Development mode - use script directory
        return os.path.dirname(os.path.abspath(__file__))


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

    # Use data directory for output files (persists in user's data folder when frozen)
    data_dir = get_data_directory()
    os.chdir(data_dir)

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
            out_dir = os.path.join(data_dir, SPECIFIC_OUTPUT_DIR)
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

    # Load sources from sources.json with type-aware processing
    sources = []
    youtube_sources = []
    newsletter_sources = []

    if os.path.exists(SOURCES_JSON):
        import json
        try:
            data = json.load(open(SOURCES_JSON))
            for s in data.get("sources", []):
                if not s.get("enabled", True):
                    continue
                source_type = s.get("type", "youtube")  # Default to youtube for backward compatibility
                url = s.get("url", "")

                # Auto-detect type if not specified
                if not source_type or source_type == "auto":
                    if "youtube.com" in url or "youtu.be" in url:
                        source_type = "youtube"
                    else:
                        source_type = "newsletter"

                source_entry = {
                    "url": url,
                    "type": source_type,
                    "config": s.get("config"),
                    "name": s.get("name")
                }

                if source_type == "youtube":
                    youtube_sources.append(source_entry)
                elif source_type == "newsletter":
                    newsletter_sources.append(source_entry)
                sources.append(source_entry)
        except Exception as e:
            log(f"Error reading sources.json: {e}")

    # Fallback to channels.txt for backward compatibility
    if not sources and os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r") as f:
            for line in f:
                url = line.strip()
                if url:
                    youtube_sources.append({"url": url, "type": "youtube"})

    if not youtube_sources and not newsletter_sources:
        log("Error: No sources configured.")
        return

    log(f"Loaded {len(youtube_sources)} YouTube sources, {len(newsletter_sources)} newsletter sources")

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

    shared_context = []
    total_summaries = 0
    log(f"DEBUG: Will save summaries in {os.path.dirname(__file__)}")

    for target_date in dates_to_process:
        if hours_mode:
            log(f"=== Processing videos from last {args.hours} hour(s) ===")
        else:
            log(f"=== Processing date: {target_date.date()} ===")

        day_summaries = []

        # Process YouTube sources
        for source in youtube_sources:
            channel_url = source.get("url", "")
            summaries, shared_context = process_channel(channel_url, model, shared_context, target_date, cutoff_time)
            day_summaries.extend(summaries)

        # Process newsletter sources
        if newsletter_sources:
            try:
                from execsum_processor import (
                    extract_newsletter_content,
                    load_config as load_execsum_config,
                    create_basic_summary,
                    load_api_key
                )

                for source in newsletter_sources:
                    newsletter_url = source.get("url", "")
                    config_name = source.get("config")
                    source_name = source.get("name") or newsletter_url.split("/")[2] if "/" in newsletter_url else "Newsletter"

                    log(f"--- Processing Newsletter: {newsletter_url} ---")

                    # Load extraction config
                    if config_name:
                        config_path = os.path.join(os.path.dirname(__file__), 'extraction_instructions', f'{config_name}.json')
                        if os.path.exists(config_path):
                            import json
                            with open(config_path, 'r') as f:
                                config = json.load(f)
                            log(f"  Using config: {config_name}")
                        else:
                            config = load_execsum_config()
                            log(f"  Config '{config_name}' not found, using default")
                    else:
                        config = load_execsum_config()
                        log(f"  Using default execsum config")

                    # Extract and summarize newsletter content
                    items, newsletter_date = extract_newsletter_content(newsletter_url, config)
                    if items:
                        log(f"  Found {len(items)} items")
                        content = create_basic_summary(items)
                        if content.strip():
                            date_str = newsletter_date or target_date.strftime("%B %d, %Y")
                            entry = f"\n\n=== {source_name} (Articles) ===\n\n\n{content}\n"
                            day_summaries.append(entry)
                            log(f"  -> Newsletter summary added")
                    else:
                        log(f"  No relevant items found")

            except ImportError as e:
                log(f"Warning: Could not import execsum_processor: {e}")
            except Exception as e:
                log(f"Error processing newsletters: {e}")
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
