import os
import subprocess

def check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=False)
        return True
    except Exception:
        return False


def transcribe_audio(input_path: str, model_size: str = "base", device: str = "auto") -> str:
    """Transcribe an audio file to text using faster-whisper.
    Auto-downloads model on first use and caches it.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError("faster_whisper not installed. Run 'pip install faster-whisper'")

    if not os.path.exists(input_path):
        raise FileNotFoundError(input_path)
    if not check_ffmpeg():
        raise RuntimeError("ffmpeg not found. Install ffmpeg to enable transcription.")

    # Initialize model (downloads on first run to ~/.cache)
    model = WhisperModel(model_size, device=device)

    segments, info = model.transcribe(input_path, vad_filter=True)
    lines = []
    for seg in segments:
        lines.append(seg.text.strip())
    return "\n".join(lines).strip()
