import os
import urllib.request
import re
import numpy as np
import soundfile as sf
import datetime
import argparse
import sys
from kokoro_onnx import Kokoro


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


MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"
TEXT_FILE = "summary.txt"


def get_model_file():
    """Get the path to the ONNX model file."""
    bundled = get_resource_path("kokoro-v1.0.onnx")
    if os.path.exists(bundled):
        return bundled
    # Fall back to current directory (will be downloaded if needed)
    return "kokoro-v1.0.onnx"


def get_voices_file():
    """Get the path to the voices.bin file."""
    bundled = get_resource_path("voices.bin")
    if os.path.exists(bundled):
        return bundled
    # Fall back to current directory (will be downloaded if needed)
    return "voices.bin"

def download_file(url, filename):
    if not os.path.exists(filename):
        print(f"Downloading {filename}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response, open(filename, "wb") as out_file:
                out_file.write(response.read())
            print("Download complete.")
        except Exception as e:
            print(f"Error downloading {filename}: {e}")
            raise
    # No else print to reduce noise

def split_sentences(text):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]

def get_output_path(filename):
    # If filename is just a name, put it in the weekly folder.
    # If it is a full path or we are in sample mode, just use it.
    if os.path.dirname(filename):
        return filename
        
    today = datetime.date.today()
    year, week, _ = today.isocalendar()
    folder_name = f"Week_{week}_{year}"
    
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        
    return os.path.join(folder_name, filename)

def convert_to_mp3(wav_file, bitrate='128k'):
    """Convert WAV file to MP3 using ffmpeg.
    
    Args:
        wav_file: Path to WAV file
        bitrate: MP3 bitrate (default: 128k)
        
    Returns:
        str: Path to MP3 file if successful, None otherwise
    """
    try:
        import subprocess
        mp3_file = os.path.splitext(wav_file)[0] + '.mp3'
        
        cmd = [
            'ffmpeg',
            '-i', wav_file,
            '-codec:a', 'libmp3lame',
            '-b:a', bitrate,
            '-y',  # Overwrite output file
            mp3_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Delete WAV file after successful conversion
            os.remove(wav_file)
            
            # Show file size info
            mp3_size = os.path.getsize(mp3_file) / (1024 * 1024)
            print(f"Converted to MP3: {mp3_size:.1f}MB")
            return mp3_file
        else:
            print(f"Warning: Could not convert to MP3. Keeping WAV file.")
            return wav_file
            
    except FileNotFoundError:
        print("Note: ffmpeg not found. Install with 'brew install ffmpeg' for automatic MP3 conversion.")
        return wav_file
    except Exception as e:
        print(f"Warning: MP3 conversion failed ({e}). Keeping WAV file.")
        return wav_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", default="af_sarah", help="Voice ID to use")
    parser.add_argument("--text", default=None, help="Text to speak (overrides summary.txt)")
    parser.add_argument("--input", default=None, help="Input text file path (overrides summary.txt)")
    parser.add_argument("--output", default="daily_quality.wav", help="Output filename")
    parser.add_argument("--format", choices=['wav', 'mp3'], default='mp3', 
                        help="Output format (default: mp3)")
    parser.add_argument("--bitrate", default='128k', 
                        help="MP3 bitrate (default: 128k). Use 192k or 256k for higher quality")
    args = parser.parse_args()

    # Get model file paths (bundled or downloaded)
    model_file = get_model_file()
    voices_file = get_voices_file()

    try:
        # Only download if using non-bundled paths
        if model_file == "kokoro-v1.0.onnx":
            download_file(MODEL_URL, model_file)
        if voices_file == "voices.bin":
            download_file(VOICES_URL, voices_file)
    except Exception as e:
        print(f"Failed to setup models: {e}")
        return

    text = args.text
    if not text:
        # Use --input if provided, otherwise fallback to summary.txt
        input_file = args.input if args.input else TEXT_FILE
        if not os.path.exists(input_file):
            print(f"Error: {input_file} not found.")
            return

        with open(input_file, "r", encoding="utf-8") as f:
            text = f.read().strip()

    if not text:
        print("Warning: Text input is empty. No audio generated.")
        return

    # If explicit output path is provided (like for samples), use it directly
    # Otherwise use the weekly folder logic
    if args.output == "daily_quality.wav" or not os.path.dirname(args.output):
         output_file = get_output_path(args.output)
    else:
         output_file = args.output

    print(f"Initializing Kokoro with voice: {args.voice}...")
    try:
        kokoro = Kokoro(model_file, voices_file)
        
        # Check if voice exists by trying to access it or just relying on error
        # kokoro-onnx doesnt easily list voices via API in all versions, 
        # but the voices/ folder exists.
        
        sentences = split_sentences(text)
        print(f"Processing {len(sentences)} sentences...")

        audio_chunks = []
        sample_rate = 24000 
        
        for i, sentence in enumerate(sentences):
            if (i + 1) % 50 == 0 or i == 0:
                print(f"[TTS] {i+1}/{len(sentences)} sentences...")
            samples, sr = kokoro.create(sentence, voice=args.voice, speed=1.0, lang="en-us")
            audio_chunks.append(samples)
            sample_rate = sr
        
        if audio_chunks:
            final_audio = np.concatenate(audio_chunks)
            print(f"Saving to {output_file}...")
            sf.write(output_file, final_audio, sample_rate)
            
            # Convert to MP3 if requested
            if args.format == 'mp3':
                print("Converting to MP3...")
                final_file = convert_to_mp3(output_file, args.bitrate)
                print(f"Done! Saved to {final_file}")
            else:
                print("Done!")
        else:
            print("No audio generated.")
    except Exception as e:
        print(f"Error during generation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
