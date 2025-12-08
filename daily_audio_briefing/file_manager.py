"""File operations for the Audio Briefing application."""
import os


class FileManager:
    """Handles all file I/O operations for the application."""
    
    def __init__(self, base_dir=None):
        """Initialize FileManager with base directory.
        
        Args:
            base_dir: Base directory for file operations. Defaults to script directory.
        """
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
    
    def load_summary(self):
        """Load the current summary file.
        
        Returns:
            str: Content of summary.txt, or None if not found
        """
        summary_path = os.path.join(self.base_dir, "summary.txt")
        if os.path.exists(summary_path):
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"Error reading summary: {e}")
        return None
    
    def save_summary(self, text):
        """Save text to summary file.
        
        Args:
            text: Text content to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        summary_path = os.path.join(self.base_dir, "summary.txt")
        try:
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(text)
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False
    
    def load_api_key(self):
        """Load Gemini API key from .env file.
        
        Returns:
            str: API key if found, empty string otherwise
        """
        env_path = os.path.join(self.base_dir, ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        if line.strip().startswith("GEMINI_API_KEY="):
                            return line.split("=", 1)[1].strip()
            except Exception as e:
                print(f"Error reading .env: {e}")
        return ""
    
    def save_api_key(self, key):
        """Save Gemini API key to .env file.
        
        Args:
            key: API key to save
        """
        env_path = os.path.join(self.base_dir, ".env")
        lines = []
        
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
        
        # Remove existing GEMINI_API_KEY line
        lines = [line for line in lines if not line.strip().startswith("GEMINI_API_KEY=")]
        lines.append(f"GEMINI_API_KEY={key}\n")
        
        with open(env_path, "w") as f:
            f.writelines(lines)
    
    def load_text_file(self, file_path):
        """Load content from a text file and save to summary.txt.
        
        Args:
            file_path: Path to the text file to load
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            out_file = os.path.join(self.base_dir, "summary.txt")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error loading file: {e}")
            return False
