from gtts import gTTS
import os
import datetime

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
    if not os.path.exists(TEXT_FILE):
        print(f"Error: {TEXT_FILE} not found.")
        return

    with open(TEXT_FILE, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        print("Warning: summary.txt is empty. No audio generated.")
        return

    output_file = get_output_path("daily_fast.mp3")

    print("Generating audio using gTTS...")
    tts = gTTS(text=text, lang="en", tld="com")
    tts.save(output_file)
    print(f"Done! Audio saved to {output_file}")

if __name__ == "__main__":
    main()
