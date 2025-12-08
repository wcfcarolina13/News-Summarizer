"""Voice management utilities for the Audio Briefing application."""
import os
import glob


class VoiceManager:
    """Manages available voices for high-quality audio generation."""
    
    def __init__(self, base_dir=None):
        """Initialize VoiceManager.
        
        Args:
            base_dir: Base directory containing voices folder
        """
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.voices_dir = os.path.join(self.base_dir, "voices")
    
    def get_available_voices(self):
        """Get list of available voice names.
        
        Returns:
            list: Sorted list of voice names
        """
        voices = []
        
        if os.path.exists(self.voices_dir):
            files = glob.glob(os.path.join(self.voices_dir, "*.npy"))
            voices = [os.path.basename(f).replace(".npy", "") for f in files]
        
        # Fallback to default voices if none found
        if not voices:
            voices = ["af_sarah", "af_bella"]
        
        return sorted(voices)
