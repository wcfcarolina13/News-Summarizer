
import os

code = r"""import os
import sys
import datetime
import dateparser
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import scrapetube
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

OUTPUT_FILE = "summary.txt"
CHANNELS_FILE = "channels.txt"

def setup_gemini():
    # If environment variable is set (passed from GUI), use it preferred
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        genai.configure(api_key=env_key)
        return genai.GenerativeModel("gemini-1.5-flash")

    if not GEMINI_API_KEY:
         print("Error: GEMINI_API_KEY not found in .env file or environment.")
         sys.exit(1)
             
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel("gemini-1.5-flash")

def get_transcript_text(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_transcript(["en"])
        except:
             try:
                transcript = transcript_list.find_generated_transcript(["en"])
             except:
                return None
        
        formatter = TextFormatter()
        return formatter.format_transcript(transcript.fetch())
    except Exception:
        return None

def summarize_text(model, text):
    try:
        safe_text = text[:15000] 
        prompt = (
            "Summarize this video transcript into 3 concise bullet points. "
            "Focus on data, news, and facts. Ignore marketing fluff.

"
            f"Transcript:
{safe_text}"
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error summarizing: {e}"

def process_channel(channel_url, model):
    print(f"Processing channel: {channel_url}")
    try:
        videos = scrapetube.get_channel(channel_url=channel_url, limit=5)
    except Exception as e:
        print(f"Error fetching videos for {channel_url}: {e}")
        return []

    processed_summaries = []
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=7)

    for video in videos:
        video_id = video["videoId"]
        title = video["title"]["runs"][0]["text"]
        
        date_info = video.get("publishedTimeText", {}).get("simpleText")
        if not date_info:
             continue

        pub_date = dateparser.parse(date_info)
        if not pub_date:
            continue
            
        if pub_date < cutoff_date:
            continue

        print(f"  - Found recent video: {title} ({date_info})")
        
        transcript = get_transcript_text(video_id)
        if not transcript:
            print("    -> No transcript available. Skipping.")
            continue

        print("    -> Summarizing...")
        summary = summarize_text(model, transcript)
        
        # Fixed syntax error here: added quotes around date format
        entry = f"## [{pub_date.strftime("