# Source Generated with Decompyle++
# File: transcriber.pyc (Python 3.12)

import os
import subprocess

def check_ffmpeg():
    subprocess.run([
        'ffmpeg',
        '-version'], capture_output = True, text = True, check = False)
    return True
# WARNING: Decompyle incomplete


def transcribe_audio(input_path = None, model_size = None, device = None):
    '''Transcribe an audio file to text using faster-whisper.
    Auto-downloads model on first use and caches it.
    '''
    WhisperModel = WhisperModel
    import faster_whisper
    if not os.path.exists(input_path):
        raise FileNotFoundError(input_path)
    if not check_ffmpeg():
        raise RuntimeError('ffmpeg not found. Install ffmpeg to enable transcription.')
    model = WhisperModel(model_size, device = device)
    (segments, info) = model.transcribe(input_path, vad_filter = True)
    lines = []
    for seg in segments:
        lines.append(seg.text.strip())
    return '\n'.join(lines).strip()
# WARNING: Decompyle incomplete

