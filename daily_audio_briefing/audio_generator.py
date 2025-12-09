"""Audio generation utilities for the Audio Briefing application."""
import os
import sys
import subprocess
import threading


class AudioGenerator:
    """Handles audio generation subprocess calls."""
    
    def __init__(self, base_dir=None, status_callback=None):
        """Initialize AudioGenerator.
        
        Args:
            base_dir: Base directory for scripts. Defaults to script directory.
            status_callback: Function to call with status updates (msg, color)
        """
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.status_callback = status_callback or self._default_callback
    
    def _default_callback(self, message, color="gray"):
        """Default status callback that prints to console."""
        print(f"[{color}] {message}")
    
    def get_python_executable(self):
        """Get the appropriate Python executable path."""
        if getattr(sys, "frozen", False):
            return "/usr/bin/env python3"
        return sys.executable
    
    def run_script(self, script_name, output_name, extra_args=None, env_vars=None, completion_callback=None):
        """Run a Python script asynchronously.
        
        Args:
            script_name: Name of the script to run
            output_name: Description of expected output
            extra_args: Additional command line arguments
            env_vars: Additional environment variables
            completion_callback: Function to call when complete (success: bool)
        """
        extra_args = extra_args or []
        
        def task():
            try:
                python_exe = self.get_python_executable()
                log_path = os.path.join(self.base_dir, "gui_log.txt")
                cmd = [python_exe, os.path.join(self.base_dir, script_name)] + extra_args
                
                process_env = os.environ.copy()
                if env_vars:
                    process_env.update(env_vars)
                
                try:
                    result = subprocess.run(
                        cmd, 
                        capture_output=True, 
                        text=True, 
                        cwd=self.base_dir, 
                        env=process_env, 
                        timeout=3600
                    )
                except subprocess.TimeoutExpired as tex:
                    with open(log_path, "w", encoding="utf-8") as log:
                        log.write(f"--- Timeout running {script_name} ---\n")
                        log.write(f"Args: {extra_args}\n")
                        log.write(f"Env keys: {list(env_vars.keys()) if env_vars else 'None'}\n")
                        log.write(f"Timeout after: {tex.timeout}s\n")
                    self.status_callback("Task timed out. See gui_log.txt", "red")
                    if completion_callback:
                        completion_callback(False)
                    return
                
                # Log the execution
                with open(log_path, "w", encoding="utf-8") as log:
                    log.write(f"--- Running {script_name} ---\n")
                    log.write(f"Args: {extra_args}\n")
                    log.write(f"Env keys: {list(env_vars.keys()) if env_vars else 'None'}\n")
                    log.write(f"Expected output: {output_name}\n")
                    log.write(f"Script directory: {self.base_dir}\n")
                    log.write(f"Return Code: {result.returncode}\n")
                    log.write("STDOUT:\n")
                    log.write(result.stdout)
                    log.write("\nSTDERR:\n")
                    log.write(result.stderr)
                
                if result.returncode == 0:
                    self.status_callback(f"Done! Generated {output_name}", "green")
                    if completion_callback:
                        completion_callback(True)
                else:
                    last_err = result.stderr.splitlines()[-1] if result.stderr else "(no stderr)"
                    self.status_callback(f"Error. See gui_log.txt: {last_err[:120]}", "red")
                    if completion_callback:
                        completion_callback(False)
                        
            except Exception as e:
                self.status_callback(f"Exception: {e}", "red")
                if completion_callback:
                    completion_callback(False)
        
        threading.Thread(target=task, daemon=True).start()
    
    def play_sample(self, voice):
        """Generate and play a voice sample.
        
        Args:
            voice: Voice name to use for sample
        """
        self.status_callback(f"Generating sample for {voice}...", "orange")
        
        def task():
            try:
                python_exe = self.get_python_executable()
                sample_file = os.path.join(self.base_dir, "sample_temp.wav")
                
                if os.path.exists(sample_file):
                    os.remove(sample_file)
                
                cmd = [
                    python_exe, 
                    os.path.join(self.base_dir, "make_audio_quality.py"),
                    "--voice", voice,
                    "--text", "This is a sample of the selected voice.",
                    "--output", sample_file,
                    "--format", "wav"  # Always use WAV for samples (faster, no ffmpeg needed)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.base_dir)
                
                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or "Unknown error"
                    self.status_callback(f"Sample Error: {error_msg[:50]}", "red")
                    return
                
                if os.path.exists(sample_file):
                    self.status_callback("Playing sample...", "green")
                    
                    # Play audio based on platform
                    if sys.platform == "darwin":
                        subprocess.run(["afplay", sample_file])
                    elif sys.platform == "win32":
                        import winsound
                        winsound.PlaySound(sample_file, winsound.SND_FILENAME)
                    else:
                        subprocess.run(["aplay", sample_file])
                    
                    # Clean up sample file
                    try:
                        os.remove(sample_file)
                    except:
                        pass
                    
                    self.status_callback("Ready", "gray")
                else:
                    self.status_callback("Sample Error: File not created", "red")
                    
            except Exception as e:
                self.status_callback(f"Sample Error: {str(e)[:50]}", "red")
        
        threading.Thread(target=task, daemon=True).start()
    
    def open_folder(self):
        """Open the output folder in the system file browser."""
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", self.base_dir])
            elif sys.platform == "win32":
                os.startfile(self.base_dir)
            else:
                subprocess.run(["xdg-open", self.base_dir])
        except Exception:
            pass
