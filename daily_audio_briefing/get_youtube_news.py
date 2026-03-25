# Source Generated with Decompyle++
# File: get_youtube_news.pyc (Python 3.12)

import os
import sys
import datetime
import dateparser
from google.generativeai import generativeai as genai
import scrapetube
import yt_dlp
import glob
import argparse
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def get_resource_path(filename):
    """Get the path to a bundled resource file.

    When running as a PyInstaller bundle, resources are in sys._MEIPASS.
    When running normally, they're in the same directory as this script.
    """
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, filename)
    return None.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

OUTPUT_FILE = 'summary.txt'
SPECIFIC_OUTPUT_DIR = 'Specific Video Lists'
CHANNELS_FILE = get_resource_path('channels.txt')
SOURCES_JSON = get_resource_path('sources.json')

def log(msg):
    print(f'''[DEBUG] {msg}''')
    sys.stdout.flush()


def get_week_folder(target_date):
    '''Create and return week-based folder path matching audio file organization'''
    (year, week, _) = target_date.isocalendar()
    folder_name = f'''Week_{week}_{year}'''
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        log(f'''Created new folder: {folder_name}''')
    return folder_name


def setup_gemini(model_name = ('gemini-2.5-flash',)):
    env_key = os.environ.get('GEMINI_API_KEY')
    if env_key:
        log('Using GEMINI_API_KEY from environment variable.')
        log(f'''Using model: {model_name}''')
        genai.configure(api_key = env_key)
        return genai.GenerativeModel(model_name)
    if not None:
        log('Error: GEMINI_API_KEY not found in .env file or environment.')
        sys.exit(1)
    genai.configure(api_key = GEMINI_API_KEY)
    log(f'''Using model: {model_name}''')
    return genai.GenerativeModel(model_name)


def clean_vtt(text):
    lines = text.splitlines()
    cleaned = []
    last_line = ''
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if '-->' in line:
            continue
        if line.isdigit():
            continue
        if line.startswith('WEBVTT'):
            continue
        if line.startswith('Kind:'):
            continue
        if line.startswith('Language:'):
            continue
        if line == last_line:
            continue
        if '<' in line and '>' in line:
            import re
            line = re.sub('<[^>]+>', '', line)
        cleaned.append(line)
        last_line = line
    return '\n'.join(cleaned)


def get_transcript_text(video_id):
    url = f'''https://www.youtube.com/watch?v={video_id}'''
    temp_prefix = f'''temp_sub_{video_id}'''
    for f in glob.glob(f'''{temp_prefix}*'''):
        os.remove(f)
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': [
            'en'],
        'outtmpl': temp_prefix,
        'quiet': True,
        'no_warnings': True }
# WARNING: Decompyle incomplete


def get_data_directory():
    '''Get the persistent data directory for user files.'''
    if getattr(sys, 'frozen', False):
        if sys.platform == 'darwin':
            data_dir = os.path.expanduser('~/Library/Application Support/Daily Audio Briefing')
        elif sys.platform == 'win32':
            data_dir = os.path.join(os.environ.get('APPDATA', ''), 'Daily Audio Briefing')
        else:
            data_dir = os.path.expanduser('~/.daily-audio-briefing')
        os.makedirs(data_dir, exist_ok = True)
        return data_dir
    return None.path.dirname(os.path.abspath(__file__))


def load_custom_instructions():
    '''Load custom instructions from file if it exists. Checks data directory first.'''
    data_dir = get_data_directory()
    paths_to_try = [
        os.path.join(data_dir, 'custom_instructions.txt'),
        'custom_instructions.txt',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom_instructions.txt')]
# WARNING: Decompyle incomplete


def summarize_text(model, text, previous_context = ('',)):
    custom_instructions = load_custom_instructions()
    custom_section = f'''\n\nUSER PROFILE & PREFERENCES:\n{custom_instructions}\n''' if custom_instructions else ''
    prompt = f'''You are an expert news analyst producing content for an AUDIO BRIEFING.\nUse the following rules to summarize the provided video transcript.\n\nCONTEXT (Summaries processed so far):\n{previous_context}\n\nRULES:\n1. Cross-Message Deduplication: If duplicative, output ONLY: "Skipped [Video Title] as duplicative."\n2. Tutorials/Promotions: If tutorial/promo, output ONLY: "Skipped [Video Title] as tutorial/promotion."\n3. Comprehensive Coverage: Extract ALL key insights, unique perspectives, and actionable information. Don\'t skip important details, data points, analysis, or unique angles that provide value or \'alpha\'.\n4. Technical Analysis: Include both big picture/sentiment AND specific technical details, price levels, indicators, or trading insights when mentioned.\n5. Key Points to Capture:\n   - All significant data, statistics, and metrics\n   - Unique insights, contrarian views, or novel analysis\n   - Actionable information and specific recommendations\n   - Important context, reasoning, and causal relationships\n   - Notable predictions, forecasts, or forward-looking statements\n6. Format Requirements for AUDIO (Text-to-Speech):\n   - Write in a natural, conversational style suitable for reading aloud.\n   - DO NOT use symbols like #, *, -, or bullet points.\n   - Use phrases like First, Additionally, Furthermore, Moreover, Finally, instead of lists.\n   - Write out dates (e.g., December fifth).\n   - NO timestamps.\n   - Organize into coherent paragraphs with smooth transitions.\n7. Transcript Cleanup: The source is a raw video transcript. Remove ALL speech disfluencies (um, uh, like, you know, I mean, sort of, kind of, right, okay so). Remove verbal tics, false starts, self-corrections, and direct-address phrases (hey guys, what\'s up everyone). Paraphrase conversational/rambling sections into clean prose. The output should read as polished writing, not a transcription.\n{custom_section}\nTRANSCRIPT:\n{text[:50000]}'''
    get_tracker = get_tracker
    import api_usage_tracker
    response = get_tracker().tracked_generate(model, prompt, 'yt_news.summarize')
    return response.text
# WARNING: Decompyle incomplete


def process_channel(channel_url, model, shared_context, cutoff_date, cutoff_time = (None,)):
    log(f'''--- Processing Channel: {channel_url} ---''')
    limit = 20
    video_generator = scrapetube.get_channel(channel_url = channel_url, limit = limit)
    videos = list(video_generator)
    log(f'''Fetched {len(videos)} recent videos.''')
    new_summaries = []
    processed_count = 0
    videos_on_target_date = 0
# WARNING: Decompyle incomplete


def get_data_directory():
    '''Get the appropriate data directory for storing output files.

    When running as a frozen app (PyInstaller), uses Application Support.
    When running in development, uses the script directory.
    '''
    if getattr(sys, 'frozen', False):
        if sys.platform == 'darwin':
            data_dir = os.path.expanduser('~/Library/Application Support/Daily Audio Briefing')
        elif sys.platform == 'win32':
            data_dir = os.path.join(os.environ.get('APPDATA', ''), 'Daily Audio Briefing')
        else:
            data_dir = os.path.expanduser('~/.daily-audio-briefing')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok = True)
        return data_dir
    return None.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type = int, default = 1, help = 'Process this many days starting from today')
    parser.add_argument('--hours', type = int, help = 'Process videos from the last N hours')
    parser.add_argument('--start', type = str, help = 'Start date YYYY-MM-DD')
    parser.add_argument('--end', type = str, help = 'End date YYYY-MM-DD')
    parser.add_argument('--model', type = str, default = 'gemini-2.5-flash', help = 'Gemini model to use (gemini-2.5-flash, gemini-2.5-pro)')
    parser.add_argument('--urls', nargs = '+', help = 'Specific YouTube video URLs to summarize')
    args = parser.parse_args()
    data_dir = get_data_directory()
    os.chdir(data_dir)
    model = setup_gemini(args.model)
# WARNING: Decompyle incomplete

if __name__ == '__main__':
    main()
    return None
