# Source Generated with Decompyle++
# File: make_audio_fast.pyc (Python 3.12)

from gtts import gTTS
import os
import datetime
import argparse
TEXT_FILE = 'summary.txt'

def get_output_path(filename):
    today = datetime.date.today()
    (year, week, _) = today.isocalendar()
    folder_name = f'''Week_{week}_{year}'''
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f'''Created new folder: {folder_name}''')
    return os.path.join(folder_name, filename)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default = None, help = 'Input text file path (overrides summary.txt)')
    parser.add_argument('--output', default = 'daily_fast.mp3', help = 'Output filename')
    args = parser.parse_args()
    input_file = args.input if args.input else TEXT_FILE
    if not os.path.exists(input_file):
        print(f'''Error: {input_file} not found.''')
        return None
# WARNING: Decompyle incomplete

if __name__ == '__main__':
    main()
    return None
