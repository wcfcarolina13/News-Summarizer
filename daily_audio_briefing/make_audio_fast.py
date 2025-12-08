from gtts import gTTS
import os
import datetime
import argparse

TEXT_FILE = "summary.txt"

def get_output_path(filename):
    today = datetime.date.today()
    year, week, _ = today.isocalendar()
    folder_name = f"Week_{week}_{year}"
    
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"Created new folder: {folder_name}")
        
    return os.path.join(folder_name, filename)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=None, help="Input text file path (overrides summary.txt)")
    parser.add_argument("--output", default="daily_fast.mp3", help="Output filename")
    args = parser.parse_args()
    
    # Use --input if provided, otherwise fallback to summary.txt
    input_file = args.input if args.input else TEXT_FILE
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        print(f"Warning: {input_file} is empty. No audio generated.")
        return

    output_file = get_output_path(args.output)

    print("Generating audio using gTTS...")
    tts = gTTS(text=text, lang="en", tld="com")
    tts.save(output_file)
    print(f"Done! Audio saved to {output_file}")

if __name__ == "__main__":
    main()
