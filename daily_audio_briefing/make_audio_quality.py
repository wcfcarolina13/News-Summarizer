import os
import urllib.request
import re
import numpy as np
import soundfile as sf
import datetime
import argparse
import sys
from kokoro_onnx import Kokoro

MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"
MODEL_FILE = "kokoro-v1.0.onnx"
VOICES_FILE = "voices.bin"
TEXT_FILE = "summary.txt"

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", default="af_sarah", help="Voice ID to use")
    parser.add_argument("--text", default=None, help="Text to speak (overrides summary.txt)")
    parser.add_argument("--input", default=None, help="Input text file path (overrides summary.txt)")
    parser.add_argument("--output", default="daily_quality.wav", help="Output filename")
    args = parser.parse_args()

    try:
        download_file(MODEL_URL, MODEL_FILE)
        download_file(VOICES_URL, VOICES_FILE)
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
        kokoro = Kokoro(MODEL_FILE, VOICES_FILE)
        
        # Check if voice exists by trying to access it or just relying on error
        # kokoro-onnx doesnt easily list voices via API in all versions, 
        # but the voices/ folder exists.
        
        sentences = split_sentences(text)
        print(f"Processing {len(sentences)} sentences...")

        audio_chunks = []
        sample_rate = 24000 
        
        for i, sentence in enumerate(sentences):
            # print(f"Generating chunk {i+1}/{len(sentences)}...")
            samples, sr = kokoro.create(sentence, voice=args.voice, speed=1.0, lang="en-us")
            audio_chunks.append(samples)
            sample_rate = sr
        
        if audio_chunks:
            final_audio = np.concatenate(audio_chunks)
            print(f"Saving to {output_file}...")
            sf.write(output_file, final_audio, sample_rate)
            print("Done!")
        else:
            print("No audio generated.")
    except Exception as e:
        print(f"Error during generation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
