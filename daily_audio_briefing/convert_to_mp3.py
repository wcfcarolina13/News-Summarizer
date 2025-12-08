"""Audio format conversion utility."""
import os
import subprocess
import argparse


def check_ffmpeg():
    """Check if ffmpeg is available."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def convert_wav_to_mp3(input_file, output_file=None, bitrate='128k'):
    """Convert WAV file to MP3 using ffmpeg.
    
    Args:
        input_file: Path to input WAV file
        output_file: Path to output MP3 file (default: same name with .mp3 extension)
        bitrate: MP3 bitrate (default: 128k for good quality/size balance)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not check_ffmpeg():
        print("Error: ffmpeg not found. Install with: brew install ffmpeg")
        return False
    
    if output_file is None:
        output_file = os.path.splitext(input_file)[0] + '.mp3'
    
    try:
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-codec:a', 'libmp3lame',
            '-b:a', bitrate,
            '-y',  # Overwrite output file
            output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Show file size comparison
            input_size = os.path.getsize(input_file) / (1024 * 1024)
            output_size = os.path.getsize(output_file) / (1024 * 1024)
            compression = ((input_size - output_size) / input_size) * 100
            
            print(f"✓ Converted: {os.path.basename(input_file)}")
            print(f"  WAV: {input_size:.1f}MB → MP3: {output_size:.1f}MB ({compression:.1f}% reduction)")
            return True
        else:
            print(f"✗ Error converting {input_file}")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False


def convert_folder(folder_path, bitrate='128k', delete_wav=False):
    """Convert all WAV files in a folder to MP3.
    
    Args:
        folder_path: Path to folder containing WAV files
        bitrate: MP3 bitrate
        delete_wav: Whether to delete original WAV files after conversion
    """
    wav_files = []
    
    # Find all WAV files recursively
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.wav'):
                wav_files.append(os.path.join(root, file))
    
    if not wav_files:
        print(f"No WAV files found in {folder_path}")
        return
    
    print(f"Found {len(wav_files)} WAV files")
    print()
    
    converted = 0
    total_saved = 0
    
    for wav_file in wav_files:
        input_size = os.path.getsize(wav_file) / (1024 * 1024)
        
        if convert_wav_to_mp3(wav_file, bitrate=bitrate):
            output_file = os.path.splitext(wav_file)[0] + '.mp3'
            output_size = os.path.getsize(output_file) / (1024 * 1024)
            saved = input_size - output_size
            total_saved += saved
            converted += 1
            
            if delete_wav:
                os.remove(wav_file)
                print(f"  Deleted: {os.path.basename(wav_file)}")
        
        print()
    
    print(f"Summary: {converted}/{len(wav_files)} files converted")
    print(f"Total space saved: {total_saved:.1f}MB")


def main():
    parser = argparse.ArgumentParser(description='Convert WAV audio files to MP3')
    parser.add_argument('input', help='Input WAV file or folder')
    parser.add_argument('-o', '--output', help='Output MP3 file (for single file conversion)')
    parser.add_argument('-b', '--bitrate', default='128k', 
                        help='MP3 bitrate (default: 128k). Higher = better quality but larger file')
    parser.add_argument('--delete-wav', action='store_true',
                        help='Delete original WAV files after conversion')
    
    args = parser.parse_args()
    
    if not check_ffmpeg():
        print("ffmpeg is required but not installed.")
        print("\nInstall ffmpeg:")
        print("  macOS: brew install ffmpeg")
        print("  Linux: sudo apt install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/download.html")
        return 1
    
    if os.path.isfile(args.input):
        # Convert single file
        success = convert_wav_to_mp3(args.input, args.output, args.bitrate)
        if success and args.delete_wav:
            os.remove(args.input)
            print(f"Deleted: {args.input}")
        return 0 if success else 1
    elif os.path.isdir(args.input):
        # Convert entire folder
        convert_folder(args.input, args.bitrate, args.delete_wav)
        return 0
    else:
        print(f"Error: {args.input} is not a valid file or directory")
        return 1


if __name__ == '__main__':
    exit(main())
