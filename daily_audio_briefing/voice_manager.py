"""Voice management utilities for the Audio Briefing application."""
import os
import glob


class VoiceManager:
    """Manages available voices for high-quality audio generation."""
    
    def __init__(self, base_dir=None):
        """Initialize VoiceManager.
        
        Args:
            base_dir: Base directory containing voices.bin
        """
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.voices_bin = os.path.join(self.base_dir, "voices.bin")
        self.model_file = os.path.join(self.base_dir, "kokoro-v1.0.onnx")
    
    def get_available_voices(self):
        """Get list of available voice names from Kokoro.
        
        Returns:
            list: Sorted list of voice names
        """
        voices = []
        
        # Try to get voices from Kokoro if model and voices.bin exist
        if os.path.exists(self.model_file) and os.path.exists(self.voices_bin):
            try:
                from kokoro_onnx import Kokoro
                kokoro = Kokoro(self.model_file, self.voices_bin)
                voices = kokoro.get_voices()
            except Exception as e:
                print(f"Warning: Could not load voices from Kokoro: {e}")
        
        # Fallback to default voices if none found
        if not voices:
            voices = ["af_sarah", "af_bella"]
        
        return sorted(voices)
